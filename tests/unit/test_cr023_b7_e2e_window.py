"""CR-023 B7.3 — integración extremo a extremo, sintética: grant genuina B6 → `load_final` (consumo real) →
ET-7 real → evaluador por ventana. Sin sustitutos de `eligibility`, `evaluate`, `reconcile` ni `load_final`.

Alcance honesto: la grant, el consumo, ET-5/ET-6 (en `load_final`), ET-7, la conciliación de pruebas y P15 son
reales. La serie de velas que se evalúa es la de la partición genuina filtrada a H4, o —cuando hace falta un
recuento de operaciones controlado— una serie sintética H4 que conserva el `context` genuino de la ventana."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_snapshot import _GENUINE, _decisions, _loader, gdev, ggrant, make_genuine  # noqa: E402,F401
from test_cr023_b6_context_reading import EID, consumed, contaminate  # noqa: E402
from test_cr023_b7_acceptance_window import Logic, MODEL  # noqa: E402
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import FinalEvaluationData, PartitionAccessError  # noqa: E402

SEL = json.dumps({"experiment_id": EID, "results": {"A": {"sharpe": 1.0}}}).encode()
REF = "DEC-999_eval.md"


def advance(reg):
    """Como `_advance_to_oos` genuino, pero con `selection_inputs` reales (hash del archivo de resultados)."""
    fz = _GENUINE[str(reg.path)]
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        reg.transition(EID, st, actor="orquestador", evidence=ev)
    fz.begin_evaluation("A", registry=reg)
    reg.transition(EID, "OOS_EVALUATION", actor="propietario",
                   evidence={"decision_ref": REF, "selected_config_id": "A",
                             "selection_inputs_sha256": hashlib.sha256(SEL).hexdigest(), "informed_by": []})


def ready(tmp, gdev, part):
    res = make_genuine(tmp, gdev, part)
    reg = ExperimentRegistry(tmp / "registry.jsonl", _decisions(tmp))
    advance(reg)
    return res, reg, _loader(res, tmp, reg)


STAT = {"dsr_min_probability": 0.95, "periods_per_year": 2190, "sr_variance_across_trials": 0.01,
        "risk_fraction": 0.01, "bootstrap": {"n_resamples": 500, "seed": 1, "block_size": 1},
        "baseline": "BUY_AND_HOLD"}


@pytest.fixture(autouse=True)
def frozen_statistics(monkeypatch):
    """Valores sintéticos de prueba (D6 sigue diferido): solo viajan dentro del preregistro que se congela."""
    import test_cr023_b3_preregistration as B3
    real = B3.base_content
    monkeypatch.setattr(B3, "base_content", lambda *a, **k: {**real(*a, **k), "statistical_tests": dict(STAT)})


def ctx(reg, loader):
    return dict(preregistration=_GENUINE[str(reg.path)], decisions_dir=reg.decisions_dir,
                manifest_dir=loader.manifest_dir, decision_ref=REF, selection_inputs=SEL)


def evaluate(res, reg, loader, data, prereg=None):
    k = ctx(reg, loader)
    k["preregistration"] = prereg or k["preregistration"]
    return W.evaluate_window(data, Logic(), MODEL, reg, loader.prereg_store, EID, manifest=res.manifest, **k)


def w4(data):
    """Solo lectura: la serie H4 de la ventana ya entregada (el evaluador deriva la suya tras verificar la procedencia)."""
    return data.data[data.data["interval"] == "4h"].reset_index(drop=True)


def test_et7_real_eligible_after_genuine_consumption_and_prereg_bound_params(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    fz = _GENUINE[str(reg.path)]
    data = loader.load_final(ggrant(part="oos"), "oos")
    assert len(consumed(reg)) == 1                                   # consumo real, único
    out = evaluate(res, reg, loader, data)
    assert out.eligibility == I.ELIGIBLE and out.nature is None and out.metrics is not None
    assert out.trades >= A.MIN_TRADES["oos"] and out.forced_window_close_trades <= 1     # P15 de la ventana
    assert out.metrics["window"] == "oos" and out.verdict != "APPROVED"
    assert out.metrics["buy_and_hold"]["source"] == "window_candles"       # derivado de la ventana, no del llamador


def test_p15_insufficient_is_inconclusive_without_nature_and_per_window(tmp_path, gdev, favorable_tape):
    favorable_tape["mode"] = "calm"            # sellada sin operaciones suficientes (P15)
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    out = evaluate(res, reg, loader, data)
    assert (out.verdict, out.nature, out.eligibility) == ("INCONCLUSIVE", None, I.ELIGIBLE)
    assert any("muestra insuficiente en oos" in r for r in out.reasons)


def test_genuine_partition_h4_runs_real_pipeline_fail_closed(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    out = evaluate(res, reg, loader, loader.load_final(ggrant(part="oos"), "oos"))
    assert out.eligibility == I.ELIGIBLE and out.verdict in ("INCONCLUSIVE", "REJECTED", W.FAVORABLE)
    assert out.metrics["window"] == "oos" and out.trades == out.metrics["window_summary"]["trades"]
    assert out.verdict != W.FAVORABLE or out.trades >= A.MIN_TRADES["oos"]


def test_et7_methodological_failure_after_consumption_is_inconclusive_methodological(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    contaminate(reg, "oos")                              # contaminación posterior al consumo: ET-7 la ve (V8)
    out = evaluate(res, reg, loader, data)
    assert (out.verdict, out.nature, out.eligibility) == ("INCONCLUSIVE", "METHODOLOGICAL", I.NOT_ELIGIBLE)
    assert out.metrics is None and "METODOLOGICA (NOT_ELIGIBLE)" in out.reasons[0] and not out.retry_allowed
    assert len(consumed(reg)) == 1                       # la partición sigue consumida: sin reversión


def test_et7_technical_failure_missing_selection_inputs_is_undeterminable(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    k = ctx(reg, loader)
    k.pop("selection_inputs")
    out = W.evaluate_window(data, Logic(), MODEL, reg,
                            loader.prereg_store, EID, manifest=res.manifest, **k)
    assert (out.verdict, out.nature, out.eligibility) == ("INCONCLUSIVE", "TECHNICAL", I.UNDETERMINABLE)
    assert out.metrics is None and "TECNICA (UNDETERMINABLE)" in out.reasons[0]


def test_denials_are_technical_or_methodological_and_consume_nothing(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    with pytest.raises(PartitionAccessError, match="no corresponde"):
        loader.load_final(ggrant(part="lockbox"), "oos")             # grant de otra partición
    contaminate(reg, "oos")
    with pytest.raises(PartitionAccessError, match="METODOLOGICA"):
        loader.load_final(ggrant(part="oos"), "oos")
    assert consumed(reg) == []


def test_oos_to_lockbox_gating_loader_not_called_after_unfavorable_oos(tmp_path, gdev, favorable_tape):
    favorable_tape["mode"] = "calm"            # sellada sin operaciones suficientes (P15)
    res, reg, loader = ready(tmp_path, gdev, "oos")
    fz = _GENUINE[str(reg.path)]
    calls = []

    def load_lockbox():
        calls.append("lockbox")
        raise AssertionError("LOCKBOX resuelto")
    out = W.evaluate_final_windows(
        lambda: loader.load_final(ggrant(part="oos"), "oos"), load_lockbox, Logic(), MODEL,
        reg, loader.prereg_store, EID, oos_manifest=res.manifest, **ctx(reg, loader))
    assert out.oos.verdict == "INCONCLUSIVE" and out.lockbox is None and out.lockbox_progression == "NOT_ATTEMPTED"
    assert calls == [] and [r["partition"] for r in consumed(reg)] == ["oos"]    # el LOCKBOX no se consume


def test_params_are_derived_from_frozen_preregistration_not_from_the_caller(tmp_path, gdev):
    """Regresión del defecto DSR-BINDING-GAP: ya no existe ningún canal por el que el llamador fije parámetros."""
    import inspect
    assert "params" not in inspect.signature(W.evaluate_window).parameters
    assert "params" not in inspect.signature(W.evaluate_final_windows).parameters
    res, reg, loader = ready(tmp_path, gdev, "oos")
    fz = _GENUINE[str(reg.path)]
    data = loader.load_final(ggrant(part="oos"), "oos")
    p = W.derive_evidence_params(fz, reg, EID, w4(data), lambda r: [1.0, 1.0 + r])
    assert (p.dsr_min_probability, p.periods_per_year, p.sr_variance_across_trials, p.risk_fraction) == (
        0.95, 2190.0, 0.01, 0.01) and p.bootstrap == STAT["bootstrap"]
    assert p.buy_and_hold_report["source"] == "window_candles" and p.buy_and_hold_report["candles"] == len(w4(data))
    assert p.baseline_beaten == (0.01 > p.buy_and_hold_report["return"])           # BUY_AND_HOLD: regla congelada
    assert p.buy_and_hold_report["return"] == w4(data)["close"].iloc[-1] / w4(data)["open"].iloc[0] - 1
    out = evaluate(res, reg, loader, data)
    assert out.eligibility == I.ELIGIBLE and out.metrics["buy_and_hold"] == p.buy_and_hold_report
    assert out.metrics["trials_count"] is not None


@pytest.mark.parametrize("key", W._STAT_KEYS)
def test_each_missing_frozen_statistic_fails_closed_technical_without_metrics(tmp_path, gdev, key, monkeypatch):
    import test_cr023_b3_preregistration as B3
    real = B3.base_content
    monkeypatch.setattr(B3, "base_content", lambda *a, **k: {
        **real(*a, **k), "statistical_tests": {x: v for x, v in STAT.items() if x != key}})
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    out = evaluate(res, reg, loader, data)
    assert (out.verdict, out.nature, out.eligibility, out.metrics) == ("INCONCLUSIVE", "TECHNICAL",
                                                                       I.UNDETERMINABLE, None)
    assert key in out.reasons[0] and not out.retry_allowed and len(consumed(reg)) == 1   # sigue consumida


@pytest.mark.parametrize("key,bad", [
    ("dsr_min_probability", 1.5), ("dsr_min_probability", True), ("periods_per_year", float("nan")),
    ("periods_per_year", "2190"), ("sr_variance_across_trials", None), ("risk_fraction", 0.5),
    ("risk_fraction", 0), ("bootstrap", {"n_resamples": 500, "seed": 1}), ("bootstrap", {"n_resamples": 5.0,
     "seed": 1, "block_size": 1}), ("baseline", "NAIVE"), ("baseline", None)])
def test_inconsistent_frozen_statistics_fail_closed(tmp_path, gdev, key, bad, monkeypatch):
    import test_cr023_b3_preregistration as B3
    real = B3.base_content
    monkeypatch.setattr(B3, "base_content", lambda *a, **k: {
        **real(*a, **k), "statistical_tests": {**STAT, key: bad}})
    res, reg, loader = ready(tmp_path, gdev, "oos")
    out = evaluate(res, reg, loader, loader.load_final(ggrant(part="oos"), "oos"))
    assert (out.verdict, out.nature, out.metrics) == ("INCONCLUSIVE", "TECHNICAL", None)
    assert out.eligibility == I.UNDETERMINABLE


def test_unverified_or_foreign_preregistration_fails_closed(tmp_path, gdev):
    import dataclasses
    res, reg, loader = ready(tmp_path, gdev, "oos")
    fz = _GENUINE[str(reg.path)]
    data = loader.load_final(ggrant(part="oos"), "oos")
    tampered = dataclasses.replace(fz, content={**fz.content, "statistical_tests": {**STAT, "dsr_min_probability": 0.5}})
    for bad in (tampered, None):
        out = W.evaluate_window(data, Logic(), MODEL, reg, loader.prereg_store, EID, manifest=res.manifest,
                                **{**ctx(reg, loader), "preregistration": bad})
        assert out.nature == "TECHNICAL" and out.metrics is None and out.verdict == "INCONCLUSIVE"
    with pytest.raises(W.EvidenceParamsError, match="no corresponde|no verificable"):
        W.derive_evidence_params(fz, reg, "EXP-0901", w4(data), lambda r: [1.0, 1.0])
