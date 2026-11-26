"""CR-023 B7.1 — backtest en modo ventana (AC-017-6, TC-ML-018, TC-ML-027). Sintético."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research.backtest import EntrySignal, run_backtest  # noqa: E402

H4 = 4 * 3600 * 1000
S = F = 0.001


def bars(rows, offset=0):
    return pd.DataFrame([{"open_time": (offset + i) * H4, "open": o, "high": h, "low": lo, "close": c}
                         for i, (o, h, lo, c) in enumerate(rows)])


class Script:
    def __init__(self, entries, exits=()):
        self.entries, self.exits = entries, set(exits)
        self.entry_calls, self.lengths = [], []

    def entry_signal(self, b, i):
        self.entry_calls.append(i)
        self.lengths.append(len(b))
        return self.entries.get(i)

    def exit_signal(self, b, i, pos):
        return i in self.exits

    def trailing_stop(self, b, i, pos):
        return None


FLAT = (100, 101, 99, 100)


def test_context_is_visible_but_generates_no_signals_or_trades():
    ctx = bars([FLAT] * 3)
    win = bars([FLAT] * 3, offset=3)
    lg = Script({0: EntrySignal(95.0), 1: EntrySignal(95.0), 5: EntrySignal(95.0)})   # 0, 1: contexto
    r = run_backtest(win, lg, context=ctx)
    assert lg.entry_calls == [3, 4, 5]          # nunca se consulta una vela de contexto
    assert lg.lengths == [4, 5, 6]              # pero la lógica ve el contexto
    assert r.trades == [] and r.window_end_signals == 1   # solo la señal de la última vela


def test_context_signal_does_not_enter_first_window_bar():
    ctx = bars([FLAT] * 2)
    win = bars([FLAT] * 3, offset=2)
    r = run_backtest(win, Script({1: EntrySignal(95.0)}), context=ctx)   # señal en el contexto
    assert r.trades == [] and r.skipped_signals == 0


def test_starts_flat_first_signal_on_first_window_bar_enters_second():
    ctx = bars([FLAT] * 2)
    win = bars([FLAT] * 4, offset=2)
    t = run_backtest(win, Script({2: EntrySignal(95.0)}), context=ctx).trades[0]
    assert t.entry_time == 3 * H4 and t.exit_reason == "forced_window_close"


def test_signal_on_last_window_candle_not_executed():
    win = bars([FLAT] * 3)
    r = run_backtest(win, Script({2: EntrySignal(95.0)}), context=win.iloc[:0])
    assert r.trades == [] and r.window_end_signals == 1 and r.invalid_signals == 0


def test_forced_window_close_costs_and_reporting():
    win = bars([FLAT, FLAT, (100, 104, 99, 103)])
    r = run_backtest(win, Script({0: EntrySignal(95.0)}), context=win.iloc[:0])
    t = r.trades[0]
    entry = 100 * (1 + S)
    exitp = 103 * (1 - S)
    risk = entry - 95
    assert t.exit_reason == "forced_window_close" and t.forced_window_close
    assert t.exit_time == 2 * H4 and t.exit_price == pytest.approx(exitp)
    assert t.gross_r == pytest.approx((103 - 100) / risk)
    assert t.commission_r == pytest.approx(F * (entry + exitp) / risk)
    assert t.slippage_r == pytest.approx(((entry - 100) + (103 - exitp)) / risk)
    s = r.summary()
    assert s["forced_window_close_trades"] == 1 and s["forced_window_close_net_r"] == pytest.approx(t.net_r)


def test_stop_first_on_last_candle_prevails_over_forced_close():
    win = bars([FLAT, FLAT, (100, 120, 94, 110)])   # toca stop y TP; stop primero
    t = run_backtest(win, Script({0: EntrySignal(95.0, 115.0)}), context=win.iloc[:0]).trades[0]
    assert t.exit_reason == "STOP" and t.exit_price == pytest.approx(95 * (1 - S))


def test_tp_on_last_candle_prevails_over_forced_close():
    win = bars([FLAT, FLAT, (100, 116, 99, 110)])
    t = run_backtest(win, Script({0: EntrySignal(95.0, 115.0)}), context=win.iloc[:0]).trades[0]
    assert t.exit_reason == "TAKE_PROFIT" and not t.forced_window_close


def test_pending_exit_on_last_candle_resolved_by_forced_close_no_later_data():
    win = bars([FLAT, FLAT, FLAT])
    t = run_backtest(win, Script({0: EntrySignal(95.0)}, exits={2}), context=win.iloc[:0]).trades[0]
    assert t.exit_reason == "forced_window_close" and t.exit_time == 2 * H4


def test_context_must_precede_window_and_window_non_empty():
    win = bars([FLAT] * 2, offset=1)
    with pytest.raises(ValueError):
        run_backtest(win, Script({}), context=bars([FLAT] * 2))        # solapa
    with pytest.raises(ValueError):
        run_backtest(win.iloc[:0], Script({}), context=bars([FLAT]))


def test_walk_forward_mode_unchanged_end_of_data_and_no_window_keys_effect():
    b = bars([FLAT, FLAT, FLAT])
    r = run_backtest(b, Script({0: EntrySignal(95.0), 2: EntrySignal(95.0)}))
    assert r.trades[0].exit_reason == "END_OF_DATA" and r.window_end_signals == 0


NAN = (float("nan"),) * 4


def test_invalid_final_window_candle_fails_closed_with_open_position():
    from swingpilot.research.backtest import InvalidFinalWindowCandle
    win = bars([FLAT, FLAT, FLAT, NAN])
    with pytest.raises(InvalidFinalWindowCandle):   # no se usa la vela 2 como sustituta
        run_backtest(win, Script({0: EntrySignal(95.0)}), context=win.iloc[:0])


def test_invalid_final_window_candle_fails_closed_even_when_flat():
    from swingpilot.research.backtest import InvalidFinalWindowCandle
    win = bars([FLAT, FLAT, NAN])
    with pytest.raises(InvalidFinalWindowCandle):
        run_backtest(win, Script({}), context=bars([FLAT], offset=-1))
    assert issubclass(InvalidFinalWindowCandle, ValueError)


def test_mid_window_nan_still_allowed_and_forced_close_uses_actual_last():
    win = bars([FLAT, FLAT, NAN, (100, 104, 99, 103)])
    t = run_backtest(win, Script({0: EntrySignal(95.0)}), context=win.iloc[:0]).trades[0]
    assert t.exit_reason == "forced_window_close" and t.exit_time == 3 * H4


def test_classic_end_of_data_still_uses_last_valid_candle_when_final_is_nan():
    win = bars([FLAT, FLAT, (100, 104, 99, 103), NAN])
    t = run_backtest(win, Script({0: EntrySignal(95.0)})).trades[0]
    assert t.exit_reason == "END_OF_DATA" and t.exit_time == 2 * H4
