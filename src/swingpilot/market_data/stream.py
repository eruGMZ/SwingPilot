"""Transporte WebSocket público de Binance para `LiveFeed` (REQ-G-097; DEC-017 Q41).

Stream combinado de solo datos de mercado: kline_1d, kline_4h y kline_1h de BTC/USDT.
Sin credenciales.

- Al conectar: resync por REST antes de confiar en el flujo.
- Mientras el feed no esté SYNCED (resync fallida, hueco o conflicto detectados en el flujo),
  se reintenta la resync dentro de la misma conexión con espera exponencial (QA3-01), sin
  esperar a que se caiga la conexión.
- Ante desconexión, error o cancelación: `on_disconnect()` (Fail-Closed). Si la tarea se
  cancela durante una resync en otro hilo, la generación del feed impide que esa resync
  huérfana deje el estado en SYNCED (QA3-08).

La puesta en marcha continua en Laptop B no es parte de IMPL-3 (DEC-017 Q41: IMPL-5).
"""
import asyncio
import json
import time

from .candles import INTERVALS, SYMBOL
from .live import SYNCED, LiveFeed

DEFAULT_WS_BASE = "wss://data-stream.binance.vision"


def stream_url(intervals: tuple[str, ...] = tuple(INTERVALS), base: str = DEFAULT_WS_BASE) -> str:
    if not base.startswith("wss://"):
        raise ValueError("solo wss://")
    streams = "/".join(f"{SYMBOL.lower()}@kline_{iv}" for iv in intervals)
    return f"{base.rstrip('/')}/stream?streams={streams}"


class _Backoff:
    def __init__(self, initial: float, maximum: float, clock=time.monotonic):
        self.initial, self.maximum, self.clock = initial, maximum, clock
        self.delay = initial
        self.next_at = 0.0

    def due(self) -> bool:
        return self.clock() >= self.next_at

    def failed(self) -> None:
        self.next_at = self.clock() + self.delay
        self.delay = min(self.delay * 2, self.maximum)

    def reset(self) -> None:
        self.delay = self.initial
        self.next_at = 0.0


async def run_stream(feed: LiveFeed, *, url: str | None = None, stop: asyncio.Event | None = None,
                     reconnect_delay_s: float = 5.0, resync_backoff_s: float = 5.0,
                     resync_backoff_max_s: float = 300.0, max_messages: int | None = None,
                     connect=None, clock=time.monotonic) -> int:
    """Bucle de recepción. Devuelve el número de mensajes procesados."""
    if connect is None:
        from websockets.asyncio.client import connect as ws_connect
        connect = ws_connect
    url = url or stream_url(feed.intervals)
    stop = stop or asyncio.Event()
    processed = 0
    backoff = _Backoff(resync_backoff_s, resync_backoff_max_s, clock)

    async def try_resync():
        rep = await asyncio.to_thread(feed.resync)
        if rep.ok and feed.state == SYNCED:
            backoff.reset()
        else:
            backoff.failed()

    try:
        while not stop.is_set():
            try:
                async with connect(url) as ws:
                    backoff.reset()
                    await try_resync()
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError as exc:
                            feed.events.append(("WS_REJECTED", f"JSON inválido: {exc}"))
                            msg = None
                        if msg is not None:
                            feed.on_ws_message(msg)
                        processed += 1
                        if feed.state != SYNCED and backoff.due():
                            await try_resync()
                        if max_messages is not None and processed >= max_messages:
                            stop.set()
                        if stop.is_set():
                            break
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # red, websockets.ConnectionClosed y similares
                feed.events.append(("WS_ERROR", f"{type(exc).__name__}: {exc}"))
            feed.on_disconnect()
            if not stop.is_set():
                await asyncio.sleep(reconnect_delay_s)
    except asyncio.CancelledError:
        feed.on_disconnect()
        raise
    return processed
