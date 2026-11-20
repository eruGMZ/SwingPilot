"""Cliente REST de datos públicos de mercado de Binance (REQ-G-097, REQ-G-109; DEC-013).

Solo endpoints públicos sin firma: GET /api/v3/klines y GET /api/v3/time. No acepta ni
envía credenciales (DEC-017 Q41, DEC-018: sin credenciales privadas de Binance). La URL
base por defecto es el dominio de solo datos de mercado de Binance, que no admite
endpoints privados.
"""
import json
import urllib.parse
import urllib.request
from typing import Callable

from .candles import SYMBOL, Candle, CandleError, candle_from_rest_row, interval_ms

DEFAULT_BASE_URL = "https://data-api.binance.vision"
KLINES_LIMIT = 1000  # DEC-013: paginación limit=1000 iterando con startTime
_ALLOWED_PATHS = ("/api/v3/klines", "/api/v3/time")

Transport = Callable[[str], object]  # url -> JSON decodificado


class PublicApiError(RuntimeError):
    pass


def _urllib_transport(url: str, timeout: float = 30.0) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "swingpilot-public-data"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL fija https)
        return json.loads(resp.read().decode("utf-8"))


class BinancePublicClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, transport: Transport | None = None):
        if not base_url.startswith("https://"):
            raise PublicApiError("solo https")
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _urllib_transport

    def _get(self, path: str, params: dict | None = None) -> object:
        if path not in _ALLOWED_PATHS:
            raise PublicApiError(f"endpoint no permitido: {path}")
        if params and any(k.lower() in ("signature", "apikey", "api_key", "timestamp") for k in params):
            raise PublicApiError("parámetros de autenticación prohibidos en el cliente público")
        url = self.base_url + path + ("?" + urllib.parse.urlencode(params) if params else "")
        try:
            return self._transport(url)
        except PublicApiError:
            raise
        except Exception as exc:  # red, HTTP, JSON
            raise PublicApiError(f"fallo en {path}: {exc}") from exc

    def server_time_ms(self) -> int:
        data = self._get("/api/v3/time")
        try:
            return int(data["serverTime"])
        except (TypeError, KeyError, ValueError) as exc:
            raise PublicApiError(f"respuesta de /time inesperada: {data!r}") from exc

    def klines_page(self, interval: str, start_time_ms: int, end_time_ms: int | None = None,
                    limit: int = KLINES_LIMIT) -> list[Candle]:
        interval_ms(interval)
        params = {"symbol": SYMBOL, "interval": interval, "startTime": start_time_ms, "limit": limit}
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        rows = self._get("/api/v3/klines", params)
        if not isinstance(rows, list):
            raise PublicApiError(f"respuesta de /klines inesperada: {rows!r}")
        try:
            return [candle_from_rest_row(interval, r) for r in rows]
        except CandleError as exc:
            raise PublicApiError(str(exc)) from exc

    def klines_range(self, interval: str, start_time_ms: int, end_time_ms: int, *,
                     require_end: bool = False) -> list[Candle]:
        """Todas las velas con open_time en [start, end], paginando con startTime (DEC-013).

        No filtra velas en formación: eso lo decide quien llama con la hora del servidor.
        Binance salta los huecos y una página corta significa «no hay más datos». Con
        `require_end=True` (snapshot), falla si la última vela recibida no es la de `end`: una
        respuesta truncada no se confunde con el final de los datos (QA3-02).
        """
        iv = interval_ms(interval)
        out: list[Candle] = []
        cursor = start_time_ms
        while cursor <= end_time_ms:
            page = self.klines_page(interval, cursor, end_time_ms)
            if not page:
                break
            for c in page:
                if c.open_time < cursor:
                    raise PublicApiError("la API devolvió velas anteriores al startTime solicitado")
            out.extend(page)
            nxt = page[-1].open_time + iv
            if nxt <= cursor:
                raise PublicApiError("la paginación no avanza")
            cursor = nxt
            if len(page) < KLINES_LIMIT:  # Binance salta huecos: página corta = no hay más
                break
        out = [c for c in out if c.open_time <= end_time_ms]
        if require_end and (not out or out[-1].open_time != end_time_ms):
            last = out[-1].open_time if out else None
            raise PublicApiError(f"{interval}: descarga incompleta (última vela {last}, esperada {end_time_ms})")
        return out
