"""FEAT-016 — TC-DATA-001..004, REQ-G-070, REQ-G-097 (y cliente REST de FEAT-015).

Sin red: un Binance simulado responde a las URL del cliente público.
"""
import asyncio
import json
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.market_data import (BinancePublicClient, Candle, CandleError, CandleStore,  # noqa: E402
                                    LiveFeed, PublicApiError, check_integrity, closed_only,
                                    interval_ms, last_closed_open_time, parse_ws_kline)
from swingpilot.market_data import live as L  # noqa: E402
from swingpilot.market_data.stream import run_stream, stream_url  # noqa: E402

H = 3_600_000
T0 = 1_700_000_000_000 // (86_400_000) * 86_400_000  # medianoche UTC


def xc(interval, open_time):
    """Vela con el mismo contenido que devuelve FakeBinance."""
    return mk(interval, open_time, 100 + (open_time // interval_ms(interval)) % 7)


def mk(interval, open_time, price=100.0):
    iv = interval_ms(interval)
    return Candle(interval, open_time, open_time + iv - 1, price, price + 2, price - 2, price + 1, 10.0)


class FakeBinance:
    """Serie continua por intervalo; `missing` simula velas que Binance no tiene."""

    def __init__(self, server_time, missing=()):
        self.server_time = server_time
        self.missing = set(missing)
        self.calls = []

    def series(self, interval, start, end):
        iv = interval_ms(interval)
        t = (start + iv - 1) // iv * iv
        out = []
        while t <= end and t <= self.server_time:  # incluye la vela en formación
            if (interval, t) not in self.missing:
                out.append(xc(interval, t))
            t += iv
        return out

    def __call__(self, url):
        self.calls.append(url)
        u = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/api/v3/time":
            return {"serverTime": self.server_time}
        assert u.path == "/api/v3/klines" and q["symbol"] == "BTCUSDT"
        iv, start, limit = q["interval"], int(q["startTime"]), int(q["limit"])
        end = int(q.get("endTime", self.server_time))
        cs = self.series(iv, start, end)[:limit]
        return [[c.open_time, str(c.open), str(c.high), str(c.low), str(c.close), str(c.volume),
                 c.close_time, "0", 0, "0", "0", "0"] for c in cs]


def ws_msg(c, closed):
    return {"stream": f"btcusdt@kline_{c.interval}", "data": {"e": "kline", "s": "BTCUSDT", "k": {
        "t": c.open_time, "T": c.close_time, "s": "BTCUSDT", "i": c.interval, "o": str(c.open),
        "c": str(c.close), "h": str(c.high), "l": str(c.low), "v": str(c.volume), "x": closed}}}


@pytest.fixture
def store(tmp_path):
    s = CandleStore(tmp_path / "md.db")
    yield s
    s.close()


# --- Velas y cierre (REQ-G-070) ---------------------------------------------------------------

def test_candle_closed_uses_binance_server_time():
    c = mk("1h", T0)
    assert not c.is_closed(T0 + H - 1)     # aún en formación
    assert c.is_closed(T0 + H)             # cierre (T0+H-1) anterior a la hora del servidor


def test_tc_data_001_forming_candle_excluded():
    cs = [mk("4h", T0), mk("4h", T0 + 4 * H)]
    assert closed_only(cs, T0 + 5 * H) == [cs[0]]


def test_last_closed_open_time_alignment():
    assert last_closed_open_time("4h", T0 + 4 * H) == T0
    assert last_closed_open_time("4h", T0 + 4 * H + 1) == T0
    assert last_closed_open_time("1d", T0 + 86_400_000 + 5) == T0


def test_candle_validation_rejects_bad_alignment_and_ohlc():
    with pytest.raises(CandleError):
        Candle("1h", T0 + 1, T0 + H, 1, 2, 0.5, 1, 1)
    with pytest.raises(CandleError):
        Candle("1h", T0, T0 + H - 1, 1, 0.9, 0.5, 1, 1)  # high < open
    with pytest.raises(CandleError):
        mk("15m", T0)


def test_integrity_report_detects_gaps_duplicates_conflicts_order():
    a, b, d = mk("1h", T0), mk("1h", T0 + H), mk("1h", T0 + 3 * H)
    b2 = mk("1h", T0 + H, price=200)
    rep = check_integrity("1h", [a, b, b, b2, d, a])
    assert rep.duplicates == [T0 + H, T0]
    assert rep.conflicts == [T0 + H]
    assert T0 in rep.out_of_order
    assert rep.gaps == [(T0 + 2 * H, T0 + 2 * H)] and rep.missing_count == 1 and not rep.ok


def test_ws_parse_rejects_other_symbol():
    m = ws_msg(mk("1h", T0), True)
    m["data"]["k"]["s"] = "ETHUSDT"
    with pytest.raises(CandleError):
        parse_ws_kline(m)


# --- Cliente REST público ---------------------------------------------------------------------

def test_rest_pagination_with_starttime_limit_1000():
    fb = FakeBinance(server_time=T0 + 2500 * H + 10)
    cl = BinancePublicClient(transport=fb)
    cs = cl.klines_range("1h", T0, T0 + 2400 * H)
    assert len(cs) == 2401 and cs[0].open_time == T0 and cs[-1].open_time == T0 + 2400 * H
    starts = [int(dict(urllib.parse.parse_qsl(urllib.parse.urlparse(u).query))["startTime"]) for u in fb.calls]
    assert starts == [T0, T0 + 1000 * H, T0 + 2000 * H]
    assert all("limit=1000" in u for u in fb.calls)


def test_public_client_refuses_auth_params_and_private_paths():
    cl = BinancePublicClient(transport=lambda u: [])
    with pytest.raises(PublicApiError):
        cl._get("/api/v3/account")
    with pytest.raises(PublicApiError):
        cl._get("/api/v3/klines", {"signature": "x"})
    with pytest.raises(PublicApiError):
        BinancePublicClient(base_url="http://insecure")


# --- Almacén ------------------------------------------------------------------------------

def test_store_is_immutable_and_records_conflicts(store):
    c = mk("1h", T0)
    assert store.add(c, "binance_ws") == "INSERTED"
    assert store.add(c, "binance_rest") == "DUPLICATE"
    assert store.add(mk("1h", T0, price=300), "binance_rest") == "CONFLICT"
    assert store.candles("1h") == [c] and store.conflicts() == [("1h", T0, "binance_rest")]
    src, received = store.provenance("1h", T0)
    assert src == "binance_ws" and received.endswith("Z")
    import sqlite3
    with pytest.raises(sqlite3.DatabaseError):
        store._db.execute("UPDATE candles SET close=1")
    with pytest.raises(sqlite3.DatabaseError):
        store._db.execute("DELETE FROM candles")


# --- LiveFeed --------------------------------------------------------------------------------

def feed_for(store, fb, intervals=("1h",), boot=None):
    return LiveFeed(store, BinancePublicClient(transport=fb), intervals=intervals,
                    bootstrap_start_ms=boot if boot is not None else {iv: T0 for iv in intervals})


def test_tc_data_004_only_closed_flag_is_consumed(store):
    fb = FakeBinance(server_time=T0 + 3 * H + 5)
    f = feed_for(store, fb, intervals=("1d", "4h", "1h"),
                 boot={"1d": T0 - 2 * 86_400_000, "4h": T0 - 8 * H, "1h": T0})
    assert f.resync().ok and f.state == L.SYNCED
    for iv in ("1d", "4h", "1h"):
        forming = mk(iv, last_closed_open_time(iv, fb.server_time) + interval_ms(iv))
        assert f.on_ws_message(ws_msg(forming, False)) == L.IGNORED_OPEN
        assert store.last_open_time(iv) == last_closed_open_time(iv, fb.server_time)
    nxt = xc("1h", T0 + 3 * H)
    fb.server_time = T0 + 4 * H
    assert f.on_ws_message(ws_msg(nxt, True)) == L.PERSISTED


def test_tc_data_002_missing_last_closed_candle_is_data_unavailable(store):
    fb = FakeBinance(server_time=T0 + 3 * H + 5)
    f = feed_for(store, fb)
    assert f.resync().ok
    assert f.data_status(fb.server_time) == {"1h": L.OK} and f.can_generate_signals(fb.server_time)
    later = T0 + 4 * H + 5  # cerró la vela T0+3H y no ha llegado
    assert f.data_status(later) == {"1h": L.DATA_UNAVAILABLE}
    assert not f.can_generate_signals(later)


def test_tc_data_003_reconnect_recovers_all_missing_candles_fail_closed(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)
    assert f.resync().ok and store.last_open_time("1h") == T0 + H
    f.on_disconnect()  # desconexión de más de un intervalo
    assert f.state == L.RESYNC_REQUIRED and not f.can_generate_signals(fb.server_time)
    fb.server_time = T0 + 9 * H + 5   # se perdieron 7 velas cerradas
    fb.calls.clear()
    held = xc("1h", T0 + 8 * H)
    assert f.on_ws_message(ws_msg(held, True)) == L.HELD_FOR_RESYNC  # no se aplica antes de resincronizar
    assert store.last_open_time("1h") == T0 + H
    rep = f.resync()
    assert rep.ok and rep.recovered == {"1h": 7}
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(fb.calls[1]).query))
    assert int(q["startTime"]) == T0 + H + 1  # último open_time persistido + 1
    assert [c.open_time for c in store.candles("1h")] == [T0 + k * H for k in range(9)]
    assert store.provenance("1h", T0 + 5 * H)[0] == "binance_rest"
    assert f.state == L.SYNCED and f.can_generate_signals(fb.server_time)


def test_gap_in_ws_stream_forces_resync_and_is_not_persisted(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)
    f.resync()
    skipped = xc("1h", T0 + 3 * H)  # falta T0+2H
    fb.server_time = T0 + 4 * H + 5
    assert f.on_ws_message(ws_msg(skipped, True)) == L.GAP_DETECTED
    assert f.state == L.RESYNC_REQUIRED and store.last_open_time("1h") == T0 + H
    assert f.resync().ok and store.last_open_time("1h") == T0 + 3 * H


def test_resync_fails_closed_when_exchange_misses_a_candle(store):
    fb = FakeBinance(server_time=T0 + 5 * H + 5, missing={("1h", T0 + 2 * H)})
    f = feed_for(store, fb)
    rep = f.resync()
    assert not rep.ok and f.state == L.RESYNC_REQUIRED
    assert store.last_open_time("1h") == T0 + H  # nada después del hueco


def test_resync_fails_closed_without_server_time(store):
    def broken(url):
        raise OSError("sin red")
    f = LiveFeed(store, BinancePublicClient(transport=broken), intervals=("1h",), bootstrap_start_ms={"1h": T0})
    rep = f.resync()
    assert not rep.ok and f.state == L.RESYNC_REQUIRED


def test_conflicting_candle_forces_resync(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)
    f.resync()
    assert f.on_ws_message(ws_msg(mk("1h", T0 + H, price=500), True)) == L.CONFLICT_DETECTED
    assert f.state == L.RESYNC_REQUIRED


# --- Transporte WebSocket (simulado) -----------------------------------------------------------

class FakeWS:
    def __init__(self, msgs):
        self.msgs = msgs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        async def gen():
            for m in self.msgs:
                yield json.dumps(m)
        return gen()


def test_run_stream_resyncs_on_connect_and_on_reconnect(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)
    sessions = [[ws_msg(xc("1h", T0 + 2 * H), False)],
                [ws_msg(xc("1h", T0 + 2 * H), True)]]
    resyncs = []
    orig = f.resync

    def counting():
        resyncs.append(1)
        return orig()
    f.resync = counting

    def connect(url):
        assert url == stream_url(("1h",))
        if not sessions:
            raise AssertionError("reconexión inesperada")
        if len(sessions) == 1:
            fb.server_time = T0 + 3 * H + 5
        return FakeWS(sessions.pop(0))

    n = asyncio.run(asyncio.wait_for(run_stream(f, url=stream_url(("1h",)), reconnect_delay_s=0, max_messages=2, connect=connect), 5))
    assert not [e for e in f.events if e[0] == "WS_ERROR"], f.events
    assert n == 2 and len(resyncs) == 2
    assert store.last_open_time("1h") == T0 + 2 * H
    assert stream_url().endswith("btcusdt@kline_1d/btcusdt@kline_4h/btcusdt@kline_1h")


# --- QA3-01: la resync se reintenta dentro de la conexión ------------------------------------

class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_qa3_01_gap_mid_stream_triggers_resync_without_reconnect(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)
    clock = Clock()
    fb2 = fb

    msgs = [ws_msg(xc("1h", T0 + 3 * H), True)]          # falta T0+2H → hueco
    msgs += [ws_msg(xc("1h", T0 + 4 * H), False)] * 3     # siguen llegando mensajes

    def connect(url):
        return FakeWS(msgs)

    orig = f.on_ws_message

    def on_msg(m):
        fb2.server_time = T0 + 4 * H + 5                  # el mundo avanza: T0+2H y T0+3H ya cerraron
        clock.t += 10
        return orig(m)
    f.on_ws_message = on_msg
    n = asyncio.run(asyncio.wait_for(run_stream(f, connect=connect, reconnect_delay_s=0, resync_backoff_s=1,
                                                max_messages=len(msgs), clock=clock), 5))
    assert n == 4
    resyncs = [e for e in f.events if e[0] == "RESYNC"]
    assert len(resyncs) >= 2 and resyncs[-1][1] == "OK"   # la 2.ª resync se hizo sin reconectar
    assert store.last_open_time("1h") == T0 + 3 * H and f.held_count == 0


def test_qa3_01_failed_initial_resync_is_retried_with_backoff(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    state = {"down": True}

    def transport(url):
        if state["down"]:
            raise OSError("REST caído")
        return fb(url)
    f = LiveFeed(store, BinancePublicClient(transport=transport), intervals=("1h",), bootstrap_start_ms={"1h": T0})
    clock = Clock()
    msgs = [ws_msg(xc("1h", T0 + 2 * H), False)] * 12
    calls = []
    orig = f.resync

    def counting():
        calls.append(clock.t)
        return orig()
    f.resync = counting

    def on_msg_factory(orig_on):
        def on_msg(m):
            clock.t += 1
            if clock.t >= 8:
                state["down"] = False                     # el REST vuelve
            return orig_on(m)
        return on_msg
    f.on_ws_message = on_msg_factory(f.on_ws_message)
    asyncio.run(asyncio.wait_for(run_stream(f, connect=lambda u: FakeWS(msgs), reconnect_delay_s=0,
                                            resync_backoff_s=1, resync_backoff_max_s=4,
                                            max_messages=len(msgs), clock=clock), 5))
    # intentos con espera exponencial (1, 2, 4 s) y recuperación sin reconectar; al terminar el
    # stream, run_stream llama on_disconnect (el estado final vuelve a RESYNC_REQUIRED)
    assert calls[:5] == [0.0, 1.0, 3.0, 7.0, 11.0]
    assert [e[1] for e in f.events if e[0] == "RESYNC"][-1] == "OK"
    assert store.last_open_time("1h") == T0 + H and f.events[-1][0] == "DISCONNECTED"


def test_qa3_01_held_queue_is_bounded(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = LiveFeed(store, BinancePublicClient(transport=fb), intervals=("1h",), bootstrap_start_ms={"1h": T0}, max_held=5)
    for k in range(20):
        f.on_ws_message(ws_msg(xc("1h", T0 + k * H), True))
    assert f.held_count == 5 and f.held_dropped == 15
    fb.server_time = T0 + 20 * H + 5
    assert f.resync().ok and store.last_open_time("1h") == T0 + 19 * H   # lo descartado se recupera por REST


# --- QA3-02: klines_range con require_end -----------------------------------------------------

def test_qa3_02_require_end_detects_truncated_response():
    fb = FakeBinance(server_time=T0 + 10 * H + 5, missing={("1h", T0 + 9 * H)})
    cl = BinancePublicClient(transport=fb)
    assert len(cl.klines_range("1h", T0, T0 + 9 * H)) == 9
    with pytest.raises(PublicApiError, match="incompleta"):
        cl.klines_range("1h", T0, T0 + 9 * H, require_end=True)
    assert cl.klines_range("1h", T0, T0 + 8 * H, require_end=True)[-1].open_time == T0 + 8 * H


# --- QA3-08: concurrencia -------------------------------------------------------------------

def test_qa3_08_store_is_safe_under_concurrent_threads(store):
    import threading
    errors = []

    def writer(offset):
        try:
            for k in range(1500):
                store.add(mk("1h", T0 + (offset + 2 * k) * H), "binance_ws")
                store.last_open_time("1h")
        except Exception as exc:   # noqa: BLE001
            errors.append(exc)
    ts = [threading.Thread(target=writer, args=(o,)) for o in (0, 1)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errors == [] and len(store.candles("1h")) == 3000


def test_qa3_08_disconnect_during_resync_does_not_leave_synced(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)

    def transport(url):
        if "klines" in url:
            f.on_disconnect()       # la conexión cae mientras la resync está en curso (otro hilo)
        return fb(url)
    f.client = BinancePublicClient(transport=transport)
    rep = f.resync()
    assert not rep.ok and f.state == L.RESYNC_REQUIRED
    assert store.last_open_time("1h") is None        # el resultado se descartó


def test_qa3_08_cancellation_calls_on_disconnect(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = feed_for(store, fb)

    class Hanging(FakeWS):
        def __aiter__(self):
            async def gen():
                await asyncio.sleep(10)
                yield "{}"
            return gen()

    async def main():
        task = asyncio.create_task(run_stream(f, connect=lambda u: Hanging([]), reconnect_delay_s=0))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(main())
    assert f.state == L.RESYNC_REQUIRED and f.events[-1][0] == "DISCONNECTED"


# --- QA3-16: mensajes ------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [[], None, 5, "x", {"data": []}, {"data": {"e": "kline", "k": []}}])
def test_qa3_16_non_object_messages_are_rejected(store, bad):
    f = feed_for(store, FakeBinance(server_time=T0 + 2 * H + 5))
    assert f.on_ws_message(bad) == L.REJECTED


@pytest.mark.parametrize("x", ["false", "true", 1, 0, None])
def test_qa3_16_closed_flag_must_be_boolean(store, x):
    f = feed_for(store, FakeBinance(server_time=T0 + 2 * H + 5))
    m = ws_msg(xc("1h", T0), True)
    m["data"]["k"]["x"] = x
    assert f.on_ws_message(m) == L.REJECTED


def test_qa3_16_closed_flag_before_close_per_event_time_is_rejected():
    c = xc("1h", T0)
    m = ws_msg(c, True)
    m["data"]["E"] = c.close_time            # aún no cerró según la hora del evento de Binance
    with pytest.raises(CandleError, match="antes del cierre"):
        parse_ws_kline(m)
    m["data"]["E"] = c.close_time + 1
    assert parse_ws_kline(m) == (c, True)


def test_qa3_16_events_are_bounded(store):
    fb = FakeBinance(server_time=T0 + 2 * H + 5)
    f = LiveFeed(store, BinancePublicClient(transport=fb), intervals=("1h",), max_events=10)
    for _ in range(50):
        f.on_ws_message({"e": "trade"})
    assert len(f.events) == 10
