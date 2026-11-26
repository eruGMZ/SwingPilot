"""CR-023 B7.2 — evaluador de aceptación por ventana final y ET-7. Sintético (sin datos reales)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402
from swingpilot.research.backtest import EntrySignal, ExecutionModel  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import FinalEvaluationData  # noqa: E402

H4 = 4 * 3600 * 1000
FLAT = (100.0, 101.0, 99.0, 100.0)


def frame(rows, offset=0):
    return pd.DataFrame([{"open_time": (offset + i) * H4, "open": o, "high": h, "low": lo, "close": c}
                         for i, (o, h, lo, c) in enumerate(rows)])


def window_rows(n_trades, *, losers=(), open_tail=False, bad_last=False):
    """Ciclos de 2 velas: señal (plana) y entrada que toca TP (o stop si `i in losers`)."""
    rows = []
    for k in range(n_trades):
        rows += [FLAT, (100.0, 106.0 if k % 2 else 104.0, 94.0 if k in losers else 99.5, 100.0)]
    if open_tail:                                  # señal y entrada sin TP/stop: cierre forzado
        rows += [FLAT, (100.0, 101.0, 99.5, 100.5)]
    if bad_last:
        rows[-1] = (float("nan"),) * 4
    return rows


class Logic:
    def entry_signal(self, b, i):
        return EntrySignal(95.0, 103.0)

    def exit_signal(self, b, i, pos):
        return False

    def trailing_stop(self, b, i, pos):
        return None


PARAMS = W.EvidenceParams(risk_fraction=0.01, periods_per_year=1, sr_variance_across_trials=0.01,
                          buy_and_hold_report={"return": 0.1}, baseline_beaten=True, dsr_min_probability=0.5,
                          bootstrap={"n_resamples": 500, "seed": 1, "block_size": 1})
MODEL = ExecutionModel()


def data(part, rows, ctx_rows=2):
    ctx = frame([FLAT] * ctx_rows)
    return FinalEvaluationData(part, frame(rows, offset=ctx_rows), ctx)


@pytest.fixture(autouse=True)
def _provenance_covered_elsewhere(monkeypatch):
    """Estos tests de unidad usan series sintéticas sin snapshot: la procedencia (B7.4b) se prueba, sin este
    sustituto, en test_cr023_b7_provenance_window.py con snapshots sintéticas selladas reales."""
    monkeypatch.setattr(W, "verify_provenance", lambda d, m, r=None: (d.data, d.context))


@pytest.fixture
def stubs(monkeypatch):
    """ET-7 elegible y conciliación de pruebas fija (3); el resto es el evaluador real."""
    calls = {"et7": [], "eval": []}

    def elig(registry, store, eid, stage, **kw):
        calls["et7"].append((stage, kw["window_id"]))
        return calls["elig_result"]

    def ev(e, registry, *, preregistration, selection_inputs, p15_part=None):
        calls["eval"].append(p15_part)
        return A._evaluate_with_trials(e, 3, p15_part=p15_part)
    calls["elig_result"] = {"result": I.ELIGIBLE, "nature": None, "causes": {}, "checks": {}}
    monkeypatch.setattr(W, "derive_evidence_params", lambda *a, **k: PARAMS)    # B7.4a: se prueba en test_..._b7_e2e
    monkeypatch.setattr(I, "eligibility", elig)
    monkeypatch.setattr(A, "evaluate", ev)
    return calls


def run(d, calls=None, part_manifest=None, **kw):
    return W.evaluate_window(d, Logic(), MODEL, None, None, "EXP-0900",
                             manifest=part_manifest or {"window_id": f"EXP-0900/{d.partition.upper()}"}, **kw)


def test_oos_favorable_forced_close_counts_towards_p15_and_is_reported_separately(stubs):
    out = run(data("oos", window_rows(29, open_tail=True)))       # 29 + 1 cierre forzado = 30
    assert out.trades == 30 and out.forced_window_close_trades == 1
    assert out.verdict == W.FAVORABLE and out.metrics["window_summary"]["forced_window_close_trades"] == 1
    assert stubs["et7"] == [("ET-7", "EXP-0900/OOS")] and stubs["eval"] == ["oos"]


def test_p15_is_per_window_and_without_the_forced_close_it_is_insufficient(stubs):
    out = run(data("oos", window_rows(29)))
    assert out.verdict == "INCONCLUSIVE" and out.nature is None
    assert any("muestra insuficiente en oos: 29 < 30" in r for r in out.reasons)
    # una ventana no hereda la muestra de otra: el LOCKBOX se mide con su propia serie
    lb = run(data("lockbox", window_rows(29)))
    assert any("lockbox: 29 < 30" in r for r in lb.reasons)


def test_default_acceptance_path_unchanged_requires_all_partitions():
    ev = A.ExperimentEvidence(trades={"train_val": 120, "oos": 40, "lockbox": 29}, oos_net_r=[0.5, 0.4],
                              oos_equity=[1, 1.01, 1.02], oos_period_returns=[0.01, 0.0099],
                              periods_per_year=1, sr_variance_across_trials=0.01, buy_and_hold_report={"r": 1},
                              baseline_beaten=True, dsr_min_probability=0.5,
                              bootstrap={"n_resamples": 10, "seed": 1, "block_size": 1})
    ev = A.ExperimentEvidence(**{**ev.__dict__, "trades": {"train_val": 120, "oos": 2, "lockbox": 29}})
    v = A._evaluate_with_trials(ev, 3)
    assert any("lockbox" in r for r in v.reasons)


def test_lockbox_not_loaded_after_unfavorable_or_inconclusive_oos(stubs):
    loaded = []

    def lb():
        loaded.append("lockbox")                                   # resolver: nada del LOCKBOX existe antes
        return {"window_id": "EXP-0900/LOCKBOX"}, lambda: data("lockbox", window_rows(30))
    for rows, verdict in ((window_rows(29), "INCONCLUSIVE"),                       # P15
                          (window_rows(30, losers=range(0, 30, 2)), "REJECTED")):  # desfavorable
        res = W.evaluate_final_windows(lambda r=rows: data("oos", r), lb, Logic(), MODEL, None, None,
                                       "EXP-0900", oos_manifest={"window_id": "EXP-0900/OOS"})
        assert res.oos.verdict == verdict and res.lockbox is None and res.lockbox_progression == "NOT_ATTEMPTED"
    assert loaded == []


def test_lockbox_evaluated_separately_after_favorable_oos(stubs):
    res = W.evaluate_final_windows(lambda: data("oos", window_rows(29, open_tail=True)),
                                   lambda: ({"window_id": "EXP-0900/LOCKBOX"},
                                            lambda: data("lockbox", window_rows(30, open_tail=True))),
                                   Logic(), MODEL, None, None, "EXP-0900",
                                   oos_manifest={"window_id": "EXP-0900/OOS"})
    assert res.oos.verdict == W.FAVORABLE and res.lockbox.verdict == W.FAVORABLE
    assert (res.oos.trades, res.lockbox.trades) == (30, 31) and res.lockbox_progression == "ATTEMPTED"
    assert stubs["et7"] == [("ET-7", "EXP-0900/OOS"), ("ET-7", "EXP-0900/LOCKBOX")]
    assert stubs["eval"] == ["oos", "lockbox"]


@pytest.mark.parametrize("result,nature,tag", [
    (I.UNDETERMINABLE, "TECHNICAL", "TECNICA (UNDETERMINABLE)"),
    (I.NOT_ELIGIBLE, "METHODOLOGICAL", "METODOLOGICA (NOT_ELIGIBLE)")])
def test_et7_failure_distinguishes_technical_from_methodological_and_has_no_metrics(stubs, result, nature, tag):
    stubs["elig_result"] = {"result": result, "nature": nature, "causes": {"V4post": "x"}, "checks": {}}
    out = run(data("oos", window_rows(30)))
    assert (out.verdict, out.nature, out.eligibility, out.metrics) == ("INCONCLUSIVE", nature, result, None)
    assert tag in out.reasons[0] and stubs["eval"] == []


def test_et7_real_eligibility_fails_closed_technical_for_unknown_experiment(tmp_path):
    reg = ExperimentRegistry(tmp_path / "registry.jsonl", tmp_path)
    out = run_real(reg, data("oos", window_rows(30)))
    assert out.verdict == "INCONCLUSIVE" and out.nature == "TECHNICAL" and out.eligibility == I.UNDETERMINABLE
    assert out.metrics is None and not out.retry_allowed


def run_real(reg, d):
    return W.evaluate_window(d, Logic(), MODEL, reg, None, "EXP-0900", manifest={"window_id": "x"})


def test_invalid_final_candle_is_technical_undeterminable_without_metrics_reversal_or_retry(stubs, tmp_path):
    reg = ExperimentRegistry(tmp_path / "registry.jsonl", tmp_path)
    before = reg.path.read_bytes() if reg.path.exists() else b""
    d = data("oos", window_rows(30, bad_last=True))
    out = W.evaluate_window(d, Logic(), MODEL, reg, None, "EXP-0900", manifest={"window_id": "x"})
    assert (out.verdict, out.nature, out.eligibility) == ("INCONCLUSIVE", "TECHNICAL", I.UNDETERMINABLE)
    assert out.metrics is None and out.trades == 0 and not out.consumption_reversed and not out.retry_allowed
    assert "vela final" in out.reasons[0] and stubs["et7"] == [] and stubs["eval"] == []
    assert (reg.path.read_bytes() if reg.path.exists() else b"") == before      # nada escrito en el registro
    # y tampoco progresa el LOCKBOX
    res = W.evaluate_final_windows(lambda: d, lambda: pytest.fail("LOCKBOX cargado"), Logic(), MODEL,
                                   reg, None, "EXP-0900", oos_manifest={"window_id": "x"})
    assert res.lockbox is None and res.lockbox_progression == "NOT_ATTEMPTED"


def test_loader_errors_propagate_and_are_not_results(stubs):
    def boom():
        raise PermissionError("denegado")
    with pytest.raises(PermissionError):
        W.evaluate_final_windows(boom, boom, Logic(), MODEL, None, None, "EXP-0900",
                                 oos_manifest={})


def test_never_approves(stubs):
    out = run(data("oos", window_rows(30)))
    assert out.verdict in ("INCONCLUSIVE", "REJECTED", W.FAVORABLE) and out.verdict != "APPROVED"
