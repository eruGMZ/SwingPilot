"""Prueba de humo opt-in contra los endpoints PÚBLICOS reales de Binance (FEAT-015/016).

Sin credenciales y sin costo. Se ejecuta solo con RUN_BINANCE_PUBLIC_LIVE=1:

    RUN_BINANCE_PUBLIC_LIVE=1 .venv/bin/pytest -q tests/integration/test_binance_public_live.py
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.market_data import (BinancePublicClient, CandleStore, LiveFeed,  # noqa: E402
                                    check_integrity, closed_only, interval_ms, last_closed_open_time)
from swingpilot.market_data.stream import run_stream  # noqa: E402

pytestmark = pytest.mark.skipif(os.environ.get("RUN_BINANCE_PUBLIC_LIVE") != "1",
                                reason="opt-in: RUN_BINANCE_PUBLIC_LIVE=1")


def test_rest_klines_pagination_and_closed_candles():
    cl = BinancePublicClient()
    now = cl.server_time_ms()
    end = last_closed_open_time("1h", now)
    start = end - 1100 * interval_ms("1h")          # obliga a paginar (limit=1000)
    cs = closed_only(cl.klines_range("1h", start, end), now)
    assert cs[0].open_time == start and cs[-1].open_time == end
    rep = check_integrity("1h", cs)
    assert not rep.duplicates and not rep.conflicts and not rep.out_of_order


def test_live_feed_resync_and_websocket(tmp_path):
    cl = BinancePublicClient()
    now = cl.server_time_ms()
    boot = {iv: last_closed_open_time(iv, now) - 5 * interval_ms(iv) for iv in ("1d", "4h", "1h")}
    store = CandleStore(tmp_path / "md.db")
    feed = LiveFeed(store, cl, bootstrap_start_ms=boot)
    n = asyncio.run(asyncio.wait_for(run_stream(feed, max_messages=3, reconnect_delay_s=1), 60))
    assert n == 3
    assert not [e for e in feed.events if e[0] == "WS_ERROR"], feed.events
    for iv in ("1d", "4h", "1h"):
        assert store.last_open_time(iv) is not None
    store.close()
