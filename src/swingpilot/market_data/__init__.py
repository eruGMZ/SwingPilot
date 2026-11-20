"""Datos de mercado de BTC/USDT (FEAT-015/016; REQ-G-070, REQ-G-097, REQ-G-109).

Solo datos públicos de Binance; ningún módulo de este paquete usa credenciales.
"""
from .binance_public import BinancePublicClient, PublicApiError
from .candles import (ASSET, INTERVALS, SYMBOL, Candle, CandleError, IntegrityReport,
                      check_integrity, closed_only, interval_ms, last_closed_open_time,
                      parse_ws_kline, timeframe_of)
from .live import LiveFeed
from .store import CandleStore

__all__ = [
    "ASSET", "INTERVALS", "SYMBOL", "BinancePublicClient", "PublicApiError", "Candle", "CandleError",
    "IntegrityReport", "check_integrity", "closed_only", "interval_ms", "last_closed_open_time",
    "parse_ws_kline", "timeframe_of", "LiveFeed", "CandleStore",
]
