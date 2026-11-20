"""Velas OHLCV de BTC/USDT: cierre según Binance e integridad
(REQ-G-070, REQ-G-097, REQ-G-109; DEC-013; TC-DATA-001/002).

Reglas:
- Una vela está cerrada cuando su `close_time` es anterior a la hora del servidor de
  Binance (no del reloj local) — REQ-G-070.
- Las temporalidades del contrato son D1, H4 y H1 (REQ-G-001/002), alineadas a UTC.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

SYMBOL = "BTCUSDT"
ASSET = "BTC/USDT"

# intervalo de Binance -> (milisegundos, temporalidad del contrato)
INTERVALS: dict[str, tuple[int, str]] = {
    "1d": (86_400_000, "D1"),
    "4h": (14_400_000, "H4"),
    "1h": (3_600_000, "H1"),
}


class CandleError(ValueError):
    pass


def interval_ms(interval: str) -> int:
    try:
        return INTERVALS[interval][0]
    except KeyError:
        raise CandleError(f"intervalo no autorizado: {interval!r} (solo {sorted(INTERVALS)})") from None


def timeframe_of(interval: str) -> str:
    interval_ms(interval)
    return INTERVALS[interval][1]


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass(frozen=True)
class Candle:
    interval: str
    open_time: int      # ms UTC (tiempo de mercado)
    close_time: int     # ms UTC, open_time + intervalo - 1
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        iv = interval_ms(self.interval)
        if self.open_time % iv:
            raise CandleError(f"open_time {self.open_time} no alineado a {self.interval}")
        if self.close_time != self.open_time + iv - 1:
            raise CandleError(f"close_time {self.close_time} inconsistente con {self.interval}")
        if not (self.low <= min(self.open, self.close) and self.high >= max(self.open, self.close)
                and self.low <= self.high):
            raise CandleError(f"OHLC inconsistente en open_time {self.open_time}")
        if self.volume < 0 or self.low <= 0:
            raise CandleError(f"precio o volumen inválido en open_time {self.open_time}")

    def is_closed(self, server_time_ms: int) -> bool:
        """REQ-G-070: cerrada si su cierre es anterior a la hora del servidor de Binance."""
        return self.close_time < server_time_ms

    def to_dict(self) -> dict:
        return asdict(self)


def candle_from_rest_row(interval: str, row: list) -> Candle:
    """Fila de GET /api/v3/klines: [open_time, o, h, l, c, v, close_time, ...]."""
    if not isinstance(row, (list, tuple)) or len(row) < 7:
        raise CandleError(f"fila de kline con formato inesperado: {row!r}")
    return Candle(interval, int(row[0]), int(row[6]), float(row[1]), float(row[2]),
                  float(row[3]), float(row[4]), float(row[5]))


def parse_ws_kline(message) -> tuple[Candle, bool]:
    """Mensaje `kline` del WebSocket (directo o envuelto en {"stream","data"}).

    Devuelve (vela, x) donde x es el flag de vela cerrada que envía Binance. QA3-16: el mensaje
    debe ser un objeto, `x` debe ser un booleano JSON (la cadena "false" se rechaza) y una vela
    que se declara cerrada antes de la hora del evento de Binance (`E`) se rechaza.
    """
    if not isinstance(message, dict):
        raise CandleError("el mensaje no es un objeto JSON")
    data = message.get("data", message)
    if not isinstance(data, dict) or data.get("e") != "kline" or not isinstance(data.get("k"), dict):
        raise CandleError("el mensaje no es un evento kline")
    k = data["k"]
    if k.get("s") != SYMBOL:
        raise CandleError(f"símbolo no autorizado: {k.get('s')!r}")
    if not isinstance(k.get("x"), bool):
        raise CandleError(f"flag x no booleano: {k.get('x')!r}")
    try:
        candle = Candle(k["i"], int(k["t"]), int(k["T"]), float(k["o"]), float(k["h"]),
                        float(k["l"]), float(k["c"]), float(k["v"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise CandleError(f"kline incompleto o inválido: {exc}") from exc
    closed = k["x"]
    event_ms = data.get("E")
    if closed and isinstance(event_ms, int) and not candle.is_closed(event_ms):
        raise CandleError("x=true antes del cierre según la hora del evento de Binance")
    return candle, closed


def last_closed_open_time(interval: str, server_time_ms: int) -> int:
    """open_time de la última vela cerrada esperada a la hora del servidor (velas alineadas a UTC)."""
    iv = interval_ms(interval)
    return (server_time_ms // iv) * iv - iv


def closed_only(candles: list[Candle], server_time_ms: int) -> list[Candle]:
    """Descarta la vela en formación (TC-DATA-001)."""
    return [c for c in candles if c.is_closed(server_time_ms)]


@dataclass
class IntegrityReport:
    interval: str
    duplicates: list[int]          # open_time repetidos (con el mismo contenido)
    conflicts: list[int]           # open_time repetidos con contenido distinto
    out_of_order: list[int]        # open_time menor o igual al anterior en el orden recibido
    gaps: list[tuple[int, int]]    # (desde, hasta) open_time faltantes, inclusive

    @property
    def ok(self) -> bool:
        return not (self.duplicates or self.conflicts or self.out_of_order or self.gaps)

    @property
    def missing_count(self) -> int:
        iv = interval_ms(self.interval)
        return sum((b - a) // iv + 1 for a, b in self.gaps)


def check_integrity(interval: str, candles: list[Candle]) -> IntegrityReport:
    """Completitud, duplicados y orden (REQ-G-070). No corrige nada: solo informa."""
    iv = interval_ms(interval)
    seen: dict[int, Candle] = {}
    dups, conflicts, ooo = [], [], []
    prev = None
    for c in candles:
        if c.interval != interval:
            raise CandleError(f"vela de {c.interval} en una serie de {interval}")
        if c.open_time in seen:
            (dups if seen[c.open_time] == c else conflicts).append(c.open_time)
        else:
            seen[c.open_time] = c
        if prev is not None and c.open_time <= prev:
            ooo.append(c.open_time)
        prev = c.open_time
    times = sorted(seen)
    gaps = [(a + iv, b - iv) for a, b in zip(times, times[1:]) if b - a > iv]
    return IntegrityReport(interval, dups, conflicts, ooo, gaps)
