"""Datos de mercado en vivo: solo velas cerradas y resincronización Fail-Closed
(REQ-G-070, REQ-G-097; DEC-013; TC-DATA-001..004; DEC-017 Q41).

Lógica pura (sin red propia): recibe mensajes del WebSocket y usa un cliente REST público
inyectado. El transporte WebSocket y el reintento de resincronización están en `stream.py`.

Estados:
- RESYNC_REQUIRED: al arrancar, tras una desconexión o al detectar un hueco o un conflicto.
  No se generan señales (Fail-Closed). Las velas cerradas que llegan por WebSocket se guardan
  en espera (cola acotada; si se desborda se descartan las más antiguas, que la resync REST
  recupera igualmente) y se aplican tras resincronizar.
- SYNCED: cada intervalo está continuo hasta la última vela cerrada conocida.

Concurrencia (QA3-08): todo el estado se protege con un lock. La resync hace las llamadas de
red sin el lock y aplica el resultado con él. Cada desconexión incrementa una generación: una
resync iniciada antes de la desconexión no puede dejar el feed en SYNCED.

Política pendiente (QA3-18): si Binance no tiene una vela, la resync detecta el hueco en cada
intento y el feed queda en Fail-Closed de forma permanente. Aceptar un hueco del exchange no
está decidido en el contrato (PENDING; decisión del propietario).
"""
import threading
from collections import deque
from dataclasses import dataclass, field

from .binance_public import BinancePublicClient, PublicApiError
from .candles import (INTERVALS, Candle, CandleError, check_integrity, closed_only,
                      interval_ms, last_closed_open_time, parse_ws_kline)
from .store import CONFLICT, INSERTED, CandleStore

RESYNC_REQUIRED, SYNCED = "RESYNC_REQUIRED", "SYNCED"
OK, DATA_UNAVAILABLE, RESYNCING = "OK", "DATA_UNAVAILABLE", "RESYNCING"

IGNORED_OPEN = "IGNORED_OPEN"
PERSISTED = "PERSISTED"
DUPLICATE_IGNORED = "DUPLICATE_IGNORED"
HELD_FOR_RESYNC = "HELD_FOR_RESYNC"
GAP_DETECTED = "GAP_DETECTED"
CONFLICT_DETECTED = "CONFLICT_DETECTED"
REJECTED = "REJECTED"

MAX_HELD = 1_000
MAX_EVENTS = 1_000


@dataclass
class ResyncReport:
    ok: bool
    recovered: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


class LiveFeed:
    def __init__(self, store: CandleStore, client: BinancePublicClient, *,
                 intervals: tuple[str, ...] = tuple(INTERVALS), bootstrap_start_ms: dict[str, int] | None = None,
                 max_held: int = MAX_HELD, max_events: int = MAX_EVENTS):
        for iv in intervals:
            interval_ms(iv)
        self.store = store
        self.client = client
        self.intervals = intervals
        self._bootstrap = bootstrap_start_ms or {}
        self._lock = threading.RLock()
        self.state = RESYNC_REQUIRED
        self._held: deque[Candle] = deque(maxlen=max_held)
        self.held_dropped = 0
        self.generation = 0
        self.events: deque[tuple[str, str]] = deque(maxlen=max_events)

    @property
    def held_count(self) -> int:
        return len(self._held)

    def _event(self, kind: str, detail: str) -> None:
        self.events.append((kind, detail))

    def _hold(self, candle: Candle) -> None:
        if len(self._held) == self._held.maxlen:
            self.held_dropped += 1   # la más antigua sale; la resync REST la recupera
        self._held.append(candle)

    # --- WebSocket -------------------------------------------------------------------------
    def on_disconnect(self) -> None:
        with self._lock:
            self.state = RESYNC_REQUIRED
            self.generation += 1
            self._event("DISCONNECTED", "resincronización obligatoria")

    def on_ws_message(self, message) -> str:
        try:
            candle, closed_flag = parse_ws_kline(message)
        except CandleError as exc:
            with self._lock:
                self._event("WS_REJECTED", str(exc))
            return REJECTED
        if candle.interval not in self.intervals:
            return REJECTED
        if not closed_flag:
            return IGNORED_OPEN
        with self._lock:
            if self.state != SYNCED:
                self._hold(candle)
                return HELD_FOR_RESYNC
            return self._apply_closed(candle, "binance_ws")

    def _apply_closed(self, candle: Candle, source: str) -> str:
        last = self.store.last_open_time(candle.interval)
        iv = interval_ms(candle.interval)
        if last is not None and candle.open_time > last + iv:
            self.state = RESYNC_REQUIRED
            self._event("GAP_DETECTED", f"{candle.interval} {last + iv}..{candle.open_time - iv}")
            self._hold(candle)
            return GAP_DETECTED
        res = self.store.add(candle, source)
        if res == CONFLICT:
            self.state = RESYNC_REQUIRED
            self._event("CONFLICT", f"{candle.interval} {candle.open_time}")
            return CONFLICT_DETECTED
        return PERSISTED if res == INSERTED else DUPLICATE_IGNORED

    # --- REST ------------------------------------------------------------------------------
    def resync(self) -> ResyncReport:
        """REQ-G-097: desde el último open_time persistido + 1, recupera TODAS las velas cerradas
        faltantes hasta la última cerrada según la hora del servidor de Binance."""
        with self._lock:
            gen = self.generation
        report = ResyncReport(ok=True)
        try:
            server_ms = self.client.server_time_ms()
        except PublicApiError as exc:
            return self._finish(gen, ResyncReport(ok=False, problems=[f"hora del servidor no disponible: {exc}"]))
        fetched_by_iv: dict[str, list[Candle]] = {}
        for iv in self.intervals:
            last = self.store.last_open_time(iv)
            if last is None:
                if iv not in self._bootstrap:
                    report.ok = False
                    report.problems.append(f"{iv}: sin historial persistido ni inicio de arranque")
                    continue
                start = self._bootstrap[iv]
            else:
                start = last + 1  # DEC-013 aclaración 3
            end = last_closed_open_time(iv, server_ms)
            if start > end:
                fetched_by_iv[iv] = []
                continue
            try:
                fetched = closed_only(self.client.klines_range(iv, start, end), server_ms)
            except PublicApiError as exc:
                report.ok = False
                report.problems.append(f"{iv}: {exc}")
                continue
            integ = check_integrity(iv, fetched)
            if integ.conflicts or integ.out_of_order:
                report.ok = False
                report.problems.append(f"{iv}: respuesta REST inconsistente")
                continue
            fetched_by_iv[iv] = sorted({c.open_time: c for c in fetched}.values(), key=lambda c: c.open_time)
        with self._lock:
            if gen != self.generation:
                report.ok = False
                report.problems.append("desconexión durante la resync: resultado descartado")
                return self._finish(gen, report)
            for iv, candles in fetched_by_iv.items():
                n = 0
                for c in candles:
                    res = self._apply_closed(c, "binance_rest")
                    if res == PERSISTED:
                        n += 1
                    elif res in (GAP_DETECTED, CONFLICT_DETECTED):
                        report.ok = False
                        report.problems.append(f"{iv}: {res} en {c.open_time}")
                        break
                report.recovered[iv] = n
            if report.ok:
                held = sorted(self._held, key=lambda c: (c.interval, c.open_time))
                self._held.clear()
                for c in held:
                    if self._apply_closed(c, "binance_ws") in (GAP_DETECTED, CONFLICT_DETECTED):
                        report.ok = False
                        report.problems.append(f"{c.interval}: vela en espera inconsistente {c.open_time}")
                        break
            return self._finish(gen, report)

    def _finish(self, gen: int, report: ResyncReport) -> ResyncReport:
        with self._lock:
            # SYNCED solo si la resync terminó bien, tras aplicar las velas en espera, y sin
            # desconexión intermedia (QA3-08).
            self.state = SYNCED if (report.ok and gen == self.generation) else RESYNC_REQUIRED
            self._event("RESYNC", "OK" if self.state == SYNCED else "; ".join(report.problems))
        return report

    # --- Estado para el ciclo de decisión -------------------------------------------------
    def data_status(self, server_time_ms: int) -> dict[str, str]:
        out = {}
        with self._lock:
            for iv in self.intervals:
                if self.state != SYNCED:
                    out[iv] = RESYNCING
                elif self.store.last_open_time(iv) != last_closed_open_time(iv, server_time_ms):
                    out[iv] = DATA_UNAVAILABLE
                else:
                    out[iv] = OK
        return out

    def can_generate_signals(self, server_time_ms: int) -> bool:
        """Fail-Closed: solo con todos los intervalos sincronizados y al día (REQ-G-070/097)."""
        return all(v == OK for v in self.data_status(server_time_ms).values())
