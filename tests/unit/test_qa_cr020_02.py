"""QA-CR020-02 (FEAT-017; REQ-G-103 v1.8/v1.9; CR-020 §C.3.2, §C.3.4, §C.4.1, §C.4.2; ORQ-017-01 O2).

`confirmatory_status()` aplica las mismas causas contractuales de pérdida del carácter confirmatorio
que el evaluador: desviación de diseño tras la exposición, cambio de `candidate_selection_rule`,
configuración no planificada evaluada (conste o no su DEVIATION) y selección distinta de la regla
congelada. Pérdida demostrada → `confirmatory` = False aunque falte otra evidencia; sin pérdida
demostrada y con evidencia no verificable → ConfirmatoryStatusUnverifiable (opción A del
propietario). Un INCONCLUSIVE probatorio del evaluador no equivale a pérdida demostrada.

Sondas de origen: P2 y P3 de `harness/verification/IMPL-3_CR-020_QA_sondas.py`.
Solo registros temporales y datos sintéticos (sin registro real, particiones ni decisiones reales).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from consumption_helpers import ok_consumption_check  # noqa: E402
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.preregistration import (ConfirmatoryStatusUnverifiable,  # noqa: E402
                                                 PreregistrationError, confirmatory_status, freeze)
from test_cr023_b3_preregistration import cr023_fields, freeze_in_registry  # noqa: E402  (CR-023)

WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}
X = "EXP-0101"
Y = "EXP-0102"


@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-900_ok.md").write_text("".join(f"AUTORIZA: {e} {s}\n" for e in (X, Y)
                                               for s in ("OOS_EVALUATION", "APPROVED")))
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def frozen(reg, eid=X, planned=("A",), rule="PRIMARY A"):
    """Experimento sintético congelado y en VALIDATION (estado que permite evaluar)."""
    reg.create(eid, "x", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "model_config", "data_split",
                               "costs", "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id=eid, timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             antecedents=["-"], statistical_tests={"dsr_min_probability": 0.95},
             metrics=["sharpe"], trials_count=reg.trials_accounting(eid, list(planned)),
             candidate_selection_rule=rule)
    p.update(cr023_fields(planned))                                # CR-023 §C.5
    fz = freeze(p)
    freeze_in_registry(reg, fz)                                    # CR-023: almacén + clase + freeze_check
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        reg.transition(eid, st, actor="orquestador", evidence=ev)
    return fz


def inputs_for(results, eid=X):
    return json.dumps({"experiment_id": eid, "results": results}, sort_keys=True).encode()


def select(reg, cfg, inputs, eid=X):
    reg.transition(eid, "OOS_EVALUATION", actor="propietario",
                   evidence={"decision_ref": "DEC-900_ok.md", "selected_config_id": cfg,
                             "selection_inputs_sha256": hashlib.sha256(inputs).hexdigest(), "informed_by": []})


def consume_oos(reg):
    assert reg.claim_partition(snapshot_id="SNAP-TEST1", partition="oos", experiment_id=X,
                               snapshot_last_open_time=0, decision_ref="DEC-900_ok.md",
                               consumption_check=ok_consumption_check()) is not None


def evidence():
    net = list(np.random.default_rng(3).normal(0.6, 1.0, 40))
    eq = list(np.cumprod([1.0] + [1 + 0.01 * x for x in net]))
    rets = list(np.diff(eq) / np.array(eq[:-1]))
    return A.ExperimentEvidence(trades={"train_val": 120, "oos": len(net), "lockbox": 35}, oos_net_r=net,
                                oos_equity=eq, oos_period_returns=rets, periods_per_year=52,
                                sr_variance_across_trials=0.01, buy_and_hold_report={"return": 0.3},
                                baseline_beaten=True, dsr_min_probability=0.95,
                                bootstrap={"n_resamples": 2000, "seed": 7, "block_size": 1})


def verdict(reg, fz, inputs):
    return A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)


def has(v, code):
    return any(code in r for r in v.reasons)


ARGMAX = "ARGMAX sharpe TIEBREAK A,B"
RES = {"A": {"sharpe": 0.5}, "B": {"sharpe": 1.2}}          # la regla da B


def compliant(reg):
    """Control: dos planificadas, selección conforme a la regla congelada."""
    fz = frozen(reg, planned=("A", "B"), rule=ARGMAX)
    for c in RES:
        fz.begin_evaluation(c, registry=reg)
    inputs = inputs_for(RES)
    select(reg, "B", inputs)
    return fz, inputs


# --- Control ----------------------------------------------------------------------------------

def test_control_compliant_selection_is_confirmatory_and_eligible(reg):
    fz, inputs = compliant(reg)
    st = confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)
    assert st["confirmatory"] is True and st["unverified"] == []
    assert st["selection"] == {"selected_config_id": "B", "rule_config_id": "B"}
    assert st["selection_rule_violation"] is False and st["unplanned_config_ids"] == []
    assert fz.confirmatory_status(reg, selection_inputs=inputs)["confirmatory"] is True
    assert verdict(reg, fz, inputs).outcome == "ELIGIBLE_FOR_HUMAN_REVIEW"


def test_before_selection_status_is_verifiable_from_the_registry_alone(reg):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    st = confirmatory_status(reg, X)
    assert st["confirmatory"] is True and st["selection"] is None and st["unverified"] == []
    assert fz.confirmatory_status(reg)["confirmatory"] is True


# --- P2: configuración no planificada ---------------------------------------------------------

def test_p2_unplanned_configuration_with_deviation_is_not_confirmatory(reg):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
    st = confirmatory_status(reg, X)                                  # antes de la selección
    assert st["confirmatory"] is False and st["unplanned_config_ids"] == ["Z"]
    assert fz.confirmatory_status(reg)["confirmatory"] is False
    inputs = inputs_for({"A": {"sharpe": 1.0}, "Z": {"sharpe": 2.0}})
    select(reg, "A", inputs)
    st = confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)
    assert st["confirmatory"] is False and st["unplanned_config_ids"] == ["Z"]
    v = verdict(reg, fz, inputs)                                     # código y precedencia conservados
    assert v.outcome == "INCONCLUSIVE" and has(v, "UNPLANNED_CONFIGURATION") and not has(v, "NOT_CONFIRMATORY")


def test_p2_unplanned_pair_without_its_deviation_is_still_not_confirmatory(reg):
    """Persistencia parcial (residuo de QA-CR020-01): el par consta y la DEVIATION no."""
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    a = next(r for r in reg.records() if r["kind"] == "CONFIGURATION_EVALUATED")
    reg._append({k: v for k, v in {**a, "config_id": "Z"}.items() if k != "at_utc"})
    assert [d for d in confirmatory_status(reg, X)["deviations"]] == []
    st = confirmatory_status(reg, X)
    assert st["confirmatory"] is False and st["unplanned_config_ids"] == ["Z"]


# --- P3: selección distinta de la regla -------------------------------------------------------

def test_p3_selection_against_frozen_rule_is_not_confirmatory(reg):
    fz = frozen(reg, planned=("A", "B"), rule=ARGMAX)
    for c in RES:
        fz.begin_evaluation(c, registry=reg)
    inputs = inputs_for(RES)
    select(reg, "A", inputs)                                          # la regla da B
    st = confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)
    assert st["confirmatory"] is False and st["selection_rule_violation"] is True
    assert st["selection"] == {"selected_config_id": "A", "rule_config_id": "B"}
    assert fz.confirmatory_status(reg, selection_inputs=inputs)["confirmatory"] is False
    v = verdict(reg, fz, inputs)
    assert v.outcome == "INCONCLUSIVE" and has(v, "SELECTION_RULE_VIOLATION") and not has(v, "NOT_CONFIRMATORY")


# --- Evidencia de selección no verificable: no es pérdida demostrada ---------------------------

def test_unverifiable_selection_evidence_raises_and_is_not_reported_as_false(reg):
    fz, inputs = compliant(reg)
    cases = {
        "sin entradas": dict(preregistration=fz),
        "hash distinto": dict(preregistration=fz, selection_inputs=inputs + b" "),
        "sin preregistro": dict(selection_inputs=inputs),
    }
    for name, kw in cases.items():
        with pytest.raises(ConfirmatoryStatusUnverifiable, match="no verificable"):
            confirmatory_status(reg, X, **kw)
    fz.record_deviation("limitations", "nota", "aclaración", registry=reg, informed_by=[])   # vincula el registro
    with pytest.raises(ConfirmatoryStatusUnverifiable):
        fz.confirmatory                                              # la propiedad no recibe entradas
    assert issubclass(ConfirmatoryStatusUnverifiable, PreregistrationError)
    altered = freeze({**fz.content, "limitations": "otro"})           # no vinculado a PREREGISTERED
    with pytest.raises(ConfirmatoryStatusUnverifiable, match="vinculado"):
        confirmatory_status(reg, X, preregistration=altered, selection_inputs=inputs)
    # el evaluador da INCONCLUSIVE probatorio con las entradas erróneas; con las correctas, ELIGIBLE
    assert has(verdict(reg, fz, inputs + b" "), "SELECTION_INPUTS_UNVERIFIABLE")
    assert confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)["confirmatory"] is True


def test_evidentiary_inconclusive_is_not_loss_of_confirmatory_status(reg):
    """Prueba posterior de Y con influencia indeterminable (C.4.2 caso 3): INCONCLUSIVE, pero X
    sigue siendo confirmatorio (no hay desviación de diseño ni incumplimiento de la regla)."""
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    fy = frozen(reg, eid=Y)
    fy.begin_evaluation("A", registry=reg)                            # T, posterior a la congelación de X
    fz.record_deviation("limitations", "nota", "aclaración", registry=reg, informed_by=[])
    inputs = inputs_for({"A": {"sharpe": 1.0}})
    select(reg, "A", inputs)
    v = verdict(reg, fz, inputs)
    assert v.outcome == "INCONCLUSIVE" and has(v, "SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED")
    assert confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)["confirmatory"] is True


# --- Pérdida demostrada + evidencia ausente ---------------------------------------------------

def test_established_violation_is_not_concealed_by_missing_evidence(reg):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
    select(reg, "A", inputs_for({"A": {"sharpe": 1.0}, "Z": {"sharpe": 2.0}}))
    st = confirmatory_status(reg, X)                                  # sin preregistro ni entradas
    assert st["confirmatory"] is False and st["unplanned_config_ids"] == ["Z"]
    assert st["unverified"] and st["selection_rule_violation"] is None
    assert fz.confirmatory_status(reg)["confirmatory"] is False


def test_design_deviation_after_oos_with_missing_selection_evidence_is_false(reg):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    select(reg, "A", inputs_for({"A": {"sharpe": 1.0}}))
    consume_oos(reg)
    d = fz.record_deviation("metrics", ["sharpe", "pf"], "tras OOS", registry=reg, informed_by=[])
    st = confirmatory_status(reg, X)
    assert st["confirmatory"] is False and st["design_deviations_after_oos"] == [d["deviation_id"]]
    assert st["unverified"]


# --- CR-020 §C.3.4: cambiar la regla congelada ------------------------------------------------

def test_selection_rule_change_before_exposure_is_not_confirmatory(reg):
    fz = frozen(reg, planned=("A", "B"), rule=ARGMAX)
    for c in RES:
        fz.begin_evaluation(c, registry=reg)
    d = fz.record_deviation("candidate_selection_rule", "PRIMARY A", "cambio de regla", registry=reg,
                            informed_by=[])
    assert d["after_oos"] is False
    st = confirmatory_status(reg, X)                                  # sin selección todavía
    assert st["confirmatory"] is False and st["selection_rule_changes"] == [d["deviation_id"]]
    assert st["design_deviations_after_oos"] == []
    inputs = inputs_for(RES)
    select(reg, "B", inputs)                                          # conforme a la regla CONGELADA
    st = confirmatory_status(reg, X)                                  # pérdida demostrada sin entradas
    assert st["confirmatory"] is False and st["unverified"]
    st = confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)
    assert st["confirmatory"] is False and st["selection_rule_violation"] is False
    v = verdict(reg, fz, inputs)
    assert v.outcome == "INCONCLUSIVE" and has(v, "NOT_CONFIRMATORY")


def test_non_selection_design_deviation_before_exposure_keeps_existing_rule(reg):
    """Regla vigente conservada: otra desviación de diseño antes de la exposición no basta."""
    fz, inputs = compliant(reg)
    fz.record_deviation("metrics", ["sharpe", "pf"], "antes de OOS", registry=reg, informed_by=[])
    st = confirmatory_status(reg, X, preregistration=fz, selection_inputs=inputs)
    assert st["confirmatory"] is True and st["selection_rule_changes"] == []


@pytest.fixture(autouse=True)
def _legacy_confirmatory_rule(monkeypatch):
    """Conserva la regla vigente de DESIGN_FIELDS fuera de `confirmatory_eligible = true` (CR-023 §C.5);
    la regla endurecida se prueba en test_cr023_b4_independence.py."""
    monkeypatch.setattr("swingpilot.research.preregistration._HARDENED_CLASS", None)
