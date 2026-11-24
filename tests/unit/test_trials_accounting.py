"""FEAT-017 — CR-020 (DEC-021; contrato v1.8): TC-ML-006 (integración), TC-ML-020..024.
REQ-G-P17, REQ-G-103, REQ-G-104.

Solo registros temporales aislados y datos sintéticos. Ningún registro real, ninguna partición
real, ninguna decisión real: las decisiones `AUTORIZA: PROCEDENCIA` de estas pruebas viven en un
directorio temporal.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research.experiments import (EvaluationRequestRejected, ExperimentError,  # noqa: E402
                                             ExperimentRegistry, PersistenceUncertainError,
                                             TrialsAccountingError)
from swingpilot.research.preregistration import (EvaluationPersistenceUncertain,  # noqa: E402
                                                 PreregistrationError, freeze, preregister)
from swingpilot.research.trials import reconcile  # noqa: E402

WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}
PROV_DEC = "DEC-950_procedencia.md"
EV_MR = ["trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md",
         "trading-bot@25f0e3f:backtest/REPORTE_FASE0.md"]
EV_TF = ["trading-bot@21c5f25:backtest/experiments/EXP-0001/preregistration.md"]


# --- preparación ----------------------------------------------------------------------------

@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    lines = [f"AUTORIZA: {e} {s}" for e in ("EXP-0101", "EXP-0102", "EXP-0103")
             for s in ("OOS_EVALUATION", "APPROVED")]
    lines += ["AUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=4 COTA=0",
              "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4"]
    (dec / "DEC-900_ok.md").write_text("\n".join(lines[:6]) + "\n")
    (dec / PROV_DEC).write_text("# Procedencia (prueba)\n\n" + "\n".join(lines[6:]) + "\n")
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def _cfgs(ids, cls):
    return [{"config_id": c, "evidence_class": cls} for c in ids]


def historical(reg):
    """Conteo histórico conservador aprobado (DEC-021): 4 documentadas + 4 de cota = 8."""
    reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="s", note="n")
    reg.register_antecedent("ANT-MR-H1", "MR H1", "REJECTED", source="s", note="n")
    mr = reg.register_provenance("ANT-MR-H1", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                                 configurations=_cfgs(["A", "B", "E1", "E2"], "DOCUMENTED_EVALUATED"),
                                 evidence=EV_MR, decision_ref=PROV_DEC, supersedes=None)
    tf = reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                 configurations=_cfgs(["A", "B", "C", "D"], "CONSERVATIVE_BOUND"),
                                 evidence=EV_TF, decision_ref=PROV_DEC, supersedes=None)
    return mr, tf


def content(reg, eid="EXP-0101", planned=("A",), rule="PRIMARY A", metrics=("sharpe",)):
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "model_config", "data_split",
                               "costs", "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id=eid, timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             snapshot={"id": "SNAP-X"}, observed_trade_rate_per_month=3.0, trade_rate_source="train_only",
             antecedents=["EXP-0001", "ANT-MR-H1"], min_history={"ok": True},
             statistical_tests={"dsr_min_probability": 0.95}, metrics=list(metrics),
             trials_count=reg.trials_accounting(eid, list(planned)), candidate_selection_rule=rule)
    return p


def frozen_experiment(reg, eid="EXP-0101", planned=("A",), rule="PRIMARY A", to="VALIDATION"):
    reg.create(eid, "x", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    fz = freeze(content(reg, eid, planned, rule))
    preregister(reg, fz)
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        if reg.state(eid) == to:
            break
        reg.transition(eid, st, actor="orquestador", evidence=ev)
    return fz


def inputs_for(eid, results):
    return json.dumps({"experiment_id": eid, "results": results}, sort_keys=True).encode()


def select(reg, eid, cfg, inputs, informed_by=()):
    reg.transition(eid, "OOS_EVALUATION", actor="propietario",
                   evidence={"decision_ref": "DEC-900_ok.md", "selected_config_id": cfg,
                             "selection_inputs_sha256": hashlib.sha256(inputs).hexdigest(),
                             "informed_by": list(informed_by)})


def evidence(net=None, risk=0.01, **kw):
    if net is None:
        net = list(np.random.default_rng(3).normal(0.6, 1.0, 40))
    eq = list(np.cumprod([1.0] + [1 + risk * x for x in net]))
    rets = list(np.diff(eq) / np.array(eq[:-1]))
    base = dict(trades={"train_val": 120, "oos": len(net), "lockbox": 35}, oos_net_r=net, oos_equity=eq,
                oos_period_returns=rets, periods_per_year=52, sr_variance_across_trials=0.01,
                buy_and_hold_report={"return": 0.3}, baseline_beaten=True, dsr_min_probability=0.95,
                bootstrap={"n_resamples": 2000, "seed": 7, "block_size": 1})
    base.update(kw)
    return A.ExperimentEvidence(**base)


def ready(reg, eid="EXP-0101", planned=("A",), rule="PRIMARY A", results=None, sel="A"):
    """Experimento congelado, configuraciones evaluadas y candidata seleccionada."""
    fz = frozen_experiment(reg, eid, planned, rule)
    results = results or {"A": {"sharpe": 1.0}}
    for c in results:
        fz.begin_evaluation(c, registry=reg)
    inputs = inputs_for(eid, results)
    select(reg, eid, sel, inputs)
    return fz, inputs


def _reason(v, code):
    return any(code in r for r in v.reasons)


# --- TC-ML-020: unidad del conteo y doble conteo ----------------------------------------------

def test_tc_ml_020_ideas_and_unevaluated_experiments_do_not_count(reg):
    reg.create("EXP-0101", "idea", actor="orquestador")
    reg.create("EXP-0102", "otra", actor="orquestador")
    reg.transition("EXP-0102", "DESIGN", actor="orquestador")
    assert reg.trials_count() == 0                                # antes: 2 (contaba identificadores)


def test_tc_ml_020_historical_conservative_count_is_eight_not_eight_executions(reg):
    historical(reg)
    acc = reg.accounting()
    assert (acc["H_doc"], acc["H_bound"], acc["E"]) == (4, 4, 0) and reg.trials_count() == 8
    view = reg.antecedents()
    assert view["EXP-0001"]["execution_status"] == "UNKNOWN"
    assert {c["evidence_class"] for c in view["EXP-0001"]["configurations"]} == {"CONSERVATIVE_BOUND"}


def test_tc_ml_020_rejected_and_abandoned_count_reruns_do_not(reg):
    fz = frozen_experiment(reg, planned=("A", "B"), rule="PRIMARY A")
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("B", registry=reg)                        # empezada y abandonada
    fz.begin_evaluation("A", registry=reg)                        # corrida idéntica: no suma
    reg.transition("EXP-0101", "REJECTED", actor="orquestador", reason="rechazada")
    assert reg.trials_count() == 2
    assert sum(r["kind"] == "CONFIGURATION_EVALUATED" for r in reg.records()) == 2


def test_tc_ml_020_cost_scenario_used_for_selection_is_its_own_configuration(reg):
    fz = frozen_experiment(reg, planned=("A", "A-cost-adverse"), rule="ARGMAX sharpe TIEBREAK A,A-cost-adverse")
    fz.begin_evaluation("A", registry=reg)
    assert reg.trials_count() == 1                                # escenario puro de costes: no se registra
    fz.begin_evaluation("A-cost-adverse", registry=reg)           # usado para seleccionar: configuración propia
    assert reg.trials_count() == 2


def test_tc_ml_020_planned_then_evaluated_counts_once_in_frozen_count(reg):
    historical(reg)
    fz = frozen_experiment(reg, planned=("A", "B"), rule="PRIMARY A")
    n_pre = fz.content["trials_count"]["N_pre"]
    assert n_pre == 8 + 2
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("B", registry=reg)
    assert reg.trials_count() == 10                               # G: 8 + 2 pares evaluados
    pre = [r for r in reg.records() if r.get("to") == "PREREGISTERED"][0]
    assert pre["evidence"]["trials_accounting"]["N_pre"] == n_pre  # N_pre no se suma dos veces


def test_tc_ml_020_pair_evaluated_before_freeze_is_not_double_counted(reg):
    reg.create("EXP-0101", "x", actor="orquestador")
    reg._append({"kind": "CONFIGURATION_EVALUATED", "experiment_id": "EXP-0101", "config_id": "A",
                 "preregistration_sha256": "a" * 64, "partition": "train_val", "actor": "sintético"})
    acc = reg.trials_accounting("EXP-0101", ["A", "B"])
    assert (acc["E"], acc["planned_new"], acc["N_pre"]) == (1, 1, 2)


def test_tc_ml_020_native_retest_of_antecedent_configuration_is_a_new_pair(reg):
    historical(reg)
    fz = frozen_experiment(reg, planned=("A",))                   # «A» también es config de EXP-0001
    fz.begin_evaluation("A", registry=reg)
    assert reg.trials_count() == 9                                # par nuevo (R3), no fusión


# --- TC-ML-021: procedencia de antecedentes -----------------------------------------------------

def test_tc_ml_021_consolidated_view_separates_original_state_from_provenance(reg):
    historical(reg)
    v = reg.antecedents()
    assert v["EXP-0001"]["original_state"] == "PENDING_DOCUMENTATION"
    assert v["EXP-0001"]["documentary_status"] == "DOCUMENTED"
    assert v["ANT-MR-H1"]["original_state"] == "REJECTED" and v["ANT-MR-H1"]["execution_status"] == "DOCUMENTED_EXECUTED"
    assert reg.experiments()["EXP-0001"]["state"] == "PENDING_DOCUMENTATION"       # estado original intacto
    assert reg.eligible_state("EXP-0001") is None


def test_tc_ml_021_reduction_requires_decision_evidence_and_is_prospective(reg, tmp_path):
    _, tf = historical(reg)
    fz_before = frozen_experiment(reg, "EXP-0101", planned=("A",))
    lines_before = reg.path.read_text().splitlines()
    reduced = _cfgs(["A", "B", "C"], "CONSERVATIVE_BOUND") + _cfgs(["D"], "DOCUMENTED_NOT_EVALUATED")
    with pytest.raises(ExperimentError, match="no cita exactamente"):                 # sin línea de decisión
        reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                configurations=reduced, evidence=EV_TF, decision_ref=PROV_DEC,
                                supersedes=tf["provenance_id"])
    with pytest.raises(ExperimentError, match="desaparece"):                          # nada desaparece
        reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                configurations=_cfgs(["A", "B", "C"], "CONSERVATIVE_BOUND"), evidence=EV_TF,
                                decision_ref=PROV_DEC, supersedes=tf["provenance_id"])
    assert reg.path.read_text().splitlines() == lines_before                          # nada escrito
    (tmp_path / "decisions" / "DEC-951_reduccion.md").write_text("AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=3\n")
    new = reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                  configurations=reduced, evidence=EV_TF, decision_ref="DEC-951_reduccion.md",
                                  supersedes=tf["provenance_id"])
    assert reg.trials_count() == 7
    assert [p["provenance_id"] for p in reg.antecedents()["EXP-0001"]["provenance_history"]] == \
        [tf["provenance_id"], new["provenance_id"]]                                    # historial conservado
    # prospectivo: el conteo congelado de EXP-0101 se reconstruye con 8 y sigue coherente
    idx = next(i for i, r in enumerate(reg.records()) if r.get("to") == "PREREGISTERED")
    assert reg.trials_accounting("EXP-0101", ["A"], upto=idx) == fz_before.content["trials_count"]
    assert fz_before.content["trials_count"]["N_pre"] == 9


def test_tc_ml_021_incoherent_supersedes_makes_count_indeterminate(reg):
    _, tf = historical(reg)
    bad = dict(tf, provenance_id="f" * 32, supersedes="e" * 32)
    reg._append(bad)
    with pytest.raises(TrialsAccountingError, match="supersedes"):
        reg.trials_count()


def test_tc_ml_021_first_provenance_cannot_supersede_and_bound_needs_unknown_execution(reg):
    reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="s", note="n")
    with pytest.raises(ExperimentError, match="supersedes"):
        reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                configurations=_cfgs(list("ABCD"), "CONSERVATIVE_BOUND"), evidence=EV_TF,
                                decision_ref=PROV_DEC, supersedes="a" * 32)
    with pytest.raises(ExperimentError, match="cota conservadora"):
        reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                                configurations=_cfgs(list("ABCD"), "CONSERVATIVE_BOUND"), evidence=EV_TF,
                                decision_ref=PROV_DEC, supersedes=None)
    with pytest.raises(TrialsAccountingError, match="sin procedencia"):
        reg.trials_count()


@pytest.mark.parametrize("case, line, kw", [
    ("signo", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=+0 COTA=4", {}),
    ("cero_izquierda", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=00 COTA=4", {}),
    ("no_ascii", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=٤", {}),
    ("conteo_distinto", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=5", {}),
    ("incrustada", "> AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {}),
    ("tokens_de_mas", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4 extra", {}),
    ("minusculas", "autoriza: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {}),
    ("otro_id", "AUTORIZA: PROCEDENCIA EXP-0002 DOCUMENTADAS=0 COTA=4", {}),
    ("evidencia_vacia", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"evidence": []}),
    ("evidencia_commit", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"evidence": ["tb@XYZ1234:a.md"]}),
    ("evidencia_absoluta", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"evidence": ["tb@abc1234:/etc/x"]}),
    ("evidencia_subida", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"evidence": ["tb@abc1234:a/../b"]}),
    ("decision_con_ruta", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"decision_ref": "x/DEC-960_p.md"}),
    ("decision_inexistente", "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4", {"decision_ref": "DEC-999_no.md"}),
])
def test_tc_ml_021_provenance_authorization_grammar_is_strict(reg, tmp_path, case, line, kw):
    reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="s", note="n")
    (tmp_path / "decisions" / "DEC-960_p.md").write_text(line + "\n")
    args = dict(documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                configurations=_cfgs(list("ABCD"), "CONSERVATIVE_BOUND"), evidence=EV_TF,
                decision_ref="DEC-960_p.md", supersedes=None)
    args.update(kw)
    with pytest.raises(ExperimentError):
        reg.register_provenance("EXP-0001", **args)
    assert not any(r["kind"] == "ANTECEDENT_PROVENANCE" for r in reg.records()), case


def test_tc_ml_021_provenance_identifier_and_decision_file_checks(reg, tmp_path):
    (tmp_path / "decisions" / "DEC-961_p.md").write_text("AUTORIZA: PROCEDENCIA ANT-mr-h1 DOCUMENTADAS=1 COTA=0\n")
    reg.register_antecedent("ANT-mr-h1", "id inválido", "REJECTED", source="s", note="n")
    with pytest.raises(ExperimentError, match="identificador"):
        reg.register_provenance("ANT-mr-h1", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                                configurations=_cfgs(["A"], "DOCUMENTED_EVALUATED"), evidence=EV_MR,
                                decision_ref="DEC-961_p.md", supersedes=None)
    with pytest.raises(ExperimentError, match="antecedente declarado"):              # antecedente inexistente
        reg.register_provenance("ANT-NOPE", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                                configurations=_cfgs(["A"], "DOCUMENTED_EVALUATED"), evidence=EV_MR,
                                decision_ref=PROV_DEC, supersedes=None)
    reg.register_antecedent("ANT-MR-H1", "MR H1", "REJECTED", source="s", note="n")
    args = dict(documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                configurations=_cfgs(list("ABCD"), "DOCUMENTED_EVALUATED"), evidence=EV_MR, supersedes=None)
    (tmp_path / "decisions" / "DEC-962_bin.md").write_bytes(b"AUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=4 COTA=0\n\xff")
    with pytest.raises(ExperimentError, match="no se puede leer"):
        reg.register_provenance("ANT-MR-H1", decision_ref="DEC-962_bin.md", **args)
    os.symlink(tmp_path / "decisions" / PROV_DEC, tmp_path / "decisions" / "DEC-963_link.md")
    with pytest.raises(ExperimentError, match="no existe"):
        reg.register_provenance("ANT-MR-H1", decision_ref="DEC-963_link.md", **args)
    reg.register_provenance("ANT-MR-H1", decision_ref=PROV_DEC, **args)              # control válido


# --- TC-ML-022: conteo congelado y regla de selección -------------------------------------------

@pytest.mark.parametrize("bad", [
    3, {"H_doc": 0}, {"H_doc": 0, "H_bound": 0, "E": 0, "planned_config_ids": ["A"], "planned_new": 1, "N_pre": 2,
                      "provenance_ids": []},
    {"H_doc": 0, "H_bound": 0, "E": 0, "planned_config_ids": [], "planned_new": 0, "N_pre": 0, "provenance_ids": []},
    {"H_doc": 0, "H_bound": 0, "E": 0, "planned_config_ids": ["A", "A"], "planned_new": 2, "N_pre": 2,
     "provenance_ids": []},
    {"H_doc": True, "H_bound": 0, "E": 0, "planned_config_ids": ["A"], "planned_new": 1, "N_pre": 2,
     "provenance_ids": []},
])
def test_tc_ml_022_freeze_rejects_malformed_trials_count(reg, bad):
    p = content(reg)
    p["trials_count"] = bad
    with pytest.raises(PreregistrationError):
        freeze(p)


@pytest.mark.parametrize("rule", ["PRIMARY Z", "PRIMARY  A", "primary A", "ARGMAX pf TIEBREAK A,B",
                                  "ARGMAX sharpe TIEBREAK A", "ARGMAX sharpe TIEBREAK A,A,B",
                                  "ARGMAX sharpe TIEBREAK A,B,Z", "ARGMAX sharpe", "A", ""])
def test_tc_ml_022_freeze_rejects_malformed_selection_rule(reg, rule):
    with pytest.raises(PreregistrationError):
        freeze(content(reg, planned=("A", "B"), rule=rule))


def test_tc_ml_022_freeze_rejected_when_declared_count_differs_from_registry(reg):
    reg.create("EXP-0101", "x", actor="orquestador")
    reg.transition("EXP-0101", "DESIGN", actor="orquestador")
    fz = freeze(content(reg))                                     # declarado con G = 0
    historical(reg)                                               # el registro cambia antes de congelar
    with pytest.raises(TrialsAccountingError, match="TRIALS_COUNT_INCONSISTENT"):
        preregister(reg, fz)
    assert reg.state("EXP-0101") == "DESIGN"
    preregister(reg, freeze(content(reg)))                        # con el desglose correcto, congela
    assert reg.state("EXP-0101") == "PREREGISTERED"


def test_tc_ml_022_evaluator_uses_frozen_count_not_live_and_planned_unevaluated_keep_it(reg):
    historical(reg)
    fz, inputs = ready(reg, planned=("A", "B"), rule="PRIMARY A")  # B planificada y nunca evaluada
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    acc = v.metrics["trials_accounting"]
    assert acc["N_pre"] == 10 and acc["N_eval"] == 10 and v.metrics["trials_count"] == 10
    assert acc["trials_live"] == 9                                # vivo: 8 + A; no se usa
    assert acc["breakdown"]["H_bound"] == 4 and acc["breakdown"]["H_bound_is_bound"] is True


def test_tc_ml_022_tampered_frozen_accounting_is_inconclusive(reg):
    fz, inputs = ready(reg)
    lines = reg.path.read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if '"to": "PREREGISTERED"' in ln)
    rec = json.loads(lines[i])
    rec["evidence"]["trials_accounting"]["N_pre"] = 0
    rec["evidence"]["trials_accounting"]["planned_new"] = 0
    lines[i] = json.dumps(rec, sort_keys=True)
    reg.path.write_text("\n".join(lines) + "\n")
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "TRIALS_COUNT_INCONSISTENT")


def test_tc_ml_022_selection_outside_frozen_rule_is_inconclusive(reg):
    results = {"A": {"sharpe": 0.5}, "B": {"sharpe": 1.2}}
    fz, inputs = ready(reg, planned=("A", "B"), rule="ARGMAX sharpe TIEBREAK A,B", results=results, sel="A")
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "SELECTION_RULE_VIOLATION")


def test_tc_ml_022_argmax_tie_uses_tiebreak_order(reg):
    results = {"A": {"sharpe": 1.0}, "B": {"sharpe": 1.0}}
    fz, inputs = ready(reg, planned=("A", "B"), rule="ARGMAX sharpe TIEBREAK B,A", results=results, sel="B")
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "ELIGIBLE_FOR_HUMAN_REVIEW", v.reasons


# --- TC-ML-023: registro duradero del inicio de evaluación ---------------------------------------

@pytest.mark.parametrize("state", ["IDEA", "DESIGN", "PREREGISTERED", "DATA_VALIDATION"])
def test_tc_ml_023_request_rejected_in_states_that_do_not_permit_evaluation(reg, state):
    if state == "IDEA":
        reg.create("EXP-0101", "x", actor="orquestador")
    elif state == "DESIGN":
        reg.create("EXP-0101", "x", actor="orquestador")
        reg.transition("EXP-0101", "DESIGN", actor="orquestador")
    else:
        frozen_experiment(reg, to=state)
    before = reg.path.read_text()
    with pytest.raises(EvaluationRequestRejected, match="solo permite evaluar"):
        reg.begin_configuration_evaluation("EXP-0101", "A", actor="orquestador")
    assert reg.path.read_text() == before and reg.trials_count() == 0


def test_tc_ml_023_non_terminal_state_alone_is_not_authorization(reg):
    fz, _ = ready(reg)                                            # OOS_EVALUATION: no terminal
    with pytest.raises(EvaluationRequestRejected, match="solo permite evaluar"):
        reg.begin_configuration_evaluation("EXP-0101", "A", actor="orquestador")
    reg.transition("EXP-0101", "REJECTED", actor="propietario", evidence={"decision_ref": "DEC-900_ok.md"})
    with pytest.raises(EvaluationRequestRejected):
        reg.begin_configuration_evaluation("EXP-0101", "B", actor="orquestador")


@pytest.mark.parametrize("eid, cfg", [("EXP-0199", "A"), ("EXP-1", "A"), ("EXP-0101", "bad id"),
                                      ("EXP-0101", ""), ("EXP-0101", None), ("EXP-0001", "A")])
def test_tc_ml_023_invalid_requests_write_nothing(reg, eid, cfg):
    historical(reg)
    frozen_experiment(reg)
    before = reg.path.read_text()
    with pytest.raises(EvaluationRequestRejected):
        reg.begin_configuration_evaluation(eid, cfg, actor="orquestador")
    assert reg.path.read_text() == before


def test_tc_ml_023_unreadable_registry_rejects_request(reg):
    frozen_experiment(reg)
    with open(reg.path, "a") as fh:
        fh.write('{"kind": "CONFIG')
    with pytest.raises(EvaluationRequestRejected, match="ilegible"):
        reg.begin_configuration_evaluation("EXP-0101", "A", actor="orquestador")


def test_tc_ml_023_uncertain_write_blocks_start_record_present_counts(reg, monkeypatch):
    frozen_experiment(reg)
    monkeypatch.setattr(X.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("fsync simulado")))
    with pytest.raises(PersistenceUncertainError, match="no empieza"):
        reg.begin_configuration_evaluation("EXP-0101", "A", actor="orquestador")
    monkeypatch.undo()
    assert reg.evaluation_recorded("EXP-0101", "A") and reg.trials_count() == 1     # cuenta aunque no se ejecutó
    reg.begin_configuration_evaluation("EXP-0101", "A", actor="orquestador")         # reintento idempotente
    assert sum(r["kind"] == "CONFIGURATION_EVALUATED" for r in reg.records()) == 1


def test_tc_ml_023_failed_write_before_bytes_is_uncertain_and_does_not_count(reg, monkeypatch):
    fz = frozen_experiment(reg)

    def failing(self, rec):
        raise OSError("disco lleno simulado")
    monkeypatch.setattr(ExperimentRegistry, "_write", failing)
    with pytest.raises(EvaluationPersistenceUncertain):
        fz.begin_evaluation("A", registry=reg)
    monkeypatch.undo()
    assert not reg.evaluation_recorded("EXP-0101", "A") and reg.trials_count() == 0
    fz.begin_evaluation("A", registry=reg)
    assert reg.trials_count() == 1


def test_tc_ml_023_unplanned_configuration_counts_with_deviation_and_is_inconclusive(reg):
    fz = frozen_experiment(reg, planned=("A",))
    with pytest.raises(EvaluationRequestRejected, match="no está planificada"):
        reg.begin_configuration_evaluation("EXP-0101", "Z", actor="orquestador")   # sin desviación: rechazo
    with pytest.raises(PreregistrationError, match="justificar"):
        fz.begin_evaluation("Z", registry=reg, informed_by=[])
    with pytest.raises(PreregistrationError, match="informed_by"):
        fz.begin_evaluation("Z", registry=reg, justification="exploración")
    assert reg.trials_count() == 0
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("Z", registry=reg, justification="exploración no planificada", informed_by=[])
    devs = [r for r in reg.records() if r["kind"] == "DEVIATION"]
    assert reg.trials_count() == 2 and len(devs) == 1 and devs[0]["config_id"] == "Z"
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}, "Z": {"sharpe": 2.0}})
    select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "UNPLANNED_CONFIGURATION")


def test_tc_ml_023_loader_requires_registered_pair(reg, tmp_path):
    from swingpilot.research.partitions import PartitionAccessError, PartitionLoader
    frozen_experiment(reg)
    loader = PartitionLoader.__new__(PartitionLoader)             # sin snapshot: solo la puerta del cargador
    loader.registry, loader.access_log = reg, tmp_path / "access.jsonl"
    loader.manifest = {"snapshot_id": "SNAP-TEST"}
    loader._read = lambda part: (_ for _ in ()).throw(AssertionError("no debía leer datos"))
    with pytest.raises(PartitionAccessError, match="sin inicio de evaluación"):
        loader.load_train_val_for_configuration("EXP-0101", "A")
    assert loader.access_history()[-1]["allowed"] is False


# --- TC-ML-024: pruebas posteriores a la congelación ---------------------------------------------

def _two_experiments(reg):
    """X = EXP-0101 congelado; Y = EXP-0102 congelado después y evaluado (prueba posterior T)."""
    fx = frozen_experiment(reg, "EXP-0101", planned=("A",))
    fx.begin_evaluation("A", registry=reg)
    fy = frozen_experiment(reg, "EXP-0102", planned=("Y1",), rule="PRIMARY Y1")
    fy.begin_evaluation("Y1", registry=reg)
    return fx


def test_tc_ml_024_not_relevant_is_reported_and_keeps_frozen_count(reg):
    fx = _two_experiments(reg)
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    select(reg, "EXP-0101", "A", inputs)                          # posterior a T, reproducible, no cita T
    v = A.evaluate(evidence(), reg, preregistration=fx, selection_inputs=inputs)
    acc = v.metrics["trials_accounting"]
    assert v.outcome == "ELIGIBLE_FOR_HUMAN_REVIEW", v.reasons
    assert acc["trials_after_freeze"] == [{"experiment_id": "EXP-0102", "config_id": "Y1"}]
    assert acc["N_eval"] == acc["N_pre"] == 1 and acc["relevant"] == []


def test_tc_ml_024_relevant_adds_to_evaluation_count_and_keeps_frozen(reg):
    fx = _two_experiments(reg)
    t = {"experiment_id": "EXP-0102", "config_id": "Y1"}
    fx.record_deviation("limitations", "nota", "consultó Y1 antes de OOS", registry=reg, informed_by=[t])
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(evidence(), reg, preregistration=fx, selection_inputs=inputs)
    acc = v.metrics["trials_accounting"]
    assert acc["relevant"] == [t] and acc["N_pre"] == 1 and acc["N_eval"] == 2 and v.metrics["trials_count"] == 2


def test_tc_ml_024_empty_informed_by_on_later_deviation_is_undetermined(reg):
    fx = _two_experiments(reg)
    fx.record_deviation("limitations", "nota", "sin consultas declaradas", registry=reg, informed_by=[])
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(evidence(), reg, preregistration=fx, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED")


def test_tc_ml_024_historical_deviation_without_informed_by_is_kept_and_treated_as_absent(reg):
    fx = _two_experiments(reg)
    reg._append({"kind": "DEVIATION", "deviation_id": "e" * 32, "experiment_id": "EXP-0101",
                 "preregistration_sha256": fx.sha256, "field": "limitations", "old": "a", "new": "b",
                 "justification": "histórico", "after_oos": False, "access_log_evidence": [],
                 "actor": "orquestador", "authorizes_change": False})
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(evidence(), reg, preregistration=fx, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED")
    assert "informed_by" not in [r for r in reg.records() if r["kind"] == "DEVIATION"][0]   # no se reescribe


def test_tc_ml_024_unverifiable_informed_by_is_rejected_at_write(reg):
    fx = _two_experiments(reg)
    for bad in ([{"experiment_id": "EXP-0103", "config_id": "Q"}], [{"provenance_id": "a" * 32}], ["EXP-0102"],
                [{"experiment_id": "EXP-0102"}]):
        with pytest.raises(PreregistrationError, match="informed_by"):
            fx.record_deviation("limitations", "n", "x", registry=reg, informed_by=bad)
        with pytest.raises(ExperimentError, match="informed_by"):
            select(reg, "EXP-0101", "A", inputs_for("EXP-0101", {"A": {"sharpe": 1.0}}), informed_by=bad)
    assert not any(r["kind"] == "DEVIATION" for r in reg.records())


@pytest.mark.parametrize("case", ["missing_inputs", "hash_mismatch", "results_incomplete"])
def test_tc_ml_024_insufficient_selection_evidence_is_inconclusive(reg, case):
    fz, inputs = ready(reg, planned=("A", "B"), results={"A": {"sharpe": 1.0}, "B": {"sharpe": 0.5}})
    given = {"missing_inputs": None, "hash_mismatch": inputs + b" ",
             "results_incomplete": inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})}[case]
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=given)
    assert v.outcome == "INCONCLUSIVE", case


def test_tc_ml_024_missing_selection_record_is_inconclusive(reg):
    fz = frozen_experiment(reg)
    fz.begin_evaluation("A", registry=reg)
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs_for("EXP-0101", {"A": {"sharpe": 1}}))
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "SELECTION_MISSING")


def test_tc_ml_024_larger_n_eval_does_not_restore_confirmatory_status(reg):
    fx = _two_experiments(reg)
    t = {"experiment_id": "EXP-0102", "config_id": "Y1"}
    inputs = inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    select(reg, "EXP-0101", "A", inputs)
    assert reg.claim_partition(snapshot_id="SNAP-TEST1", partition="oos", experiment_id="EXP-0101",
                               snapshot_last_open_time=0, decision_ref="DEC-900_ok.md") is not None
    fx.record_deviation("metrics", ["sharpe", "pf"], "cambio de diseño tras OOS", registry=reg, informed_by=[t])
    v = A.evaluate(evidence(), reg, preregistration=fx, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "NOT_CONFIRMATORY")


def test_tc_ml_024_unreadable_registry_is_inconclusive(reg):
    fz, inputs = ready(reg)
    with open(reg.path, "a") as fh:
        fh.write("{corrupto\n")
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "INCONCLUSIVE" and _reason(v, "REGISTRY_UNREADABLE")


# --- TC-ML-006 (actualizada): corrección por configuraciones con el conteo congelado ------------

def test_tc_ml_006_full_evaluation_uses_reconciled_configuration_count(reg):
    historical(reg)
    fz, inputs = ready(reg)
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "ELIGIBLE_FOR_HUMAN_REVIEW" and v.metrics["trials_count"] == 9       # 8 + 1 planificada
    rec = reconcile(reg, fz, inputs)
    assert rec["ok"] and rec["N_pre"] == 9 and rec["breakdown"]["H_doc"] == 4


def test_tc_ml_006_more_configurations_raise_the_bar_to_rejection(reg, tmp_path):
    reg.register_antecedent("ANT-BIG", "grid histórico", "INCONCLUSIVE", source="s", note="n")
    (tmp_path / "decisions" / "DEC-970_big.md").write_text("AUTORIZA: PROCEDENCIA ANT-BIG DOCUMENTADAS=0 COTA=60\n")
    reg.register_provenance("ANT-BIG", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                            configurations=_cfgs([f"G{i}" for i in range(60)], "CONSERVATIVE_BOUND"),
                            evidence=["otro@abc1234:grid.md"], decision_ref="DEC-970_big.md", supersedes=None)
    fz, inputs = ready(reg)
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
    assert v.outcome == "REJECTED" and any("Deflated Sharpe" in r for r in v.reasons)
    assert v.metrics["trials_count"] == 61


def test_tc_ml_006_inconclusive_verdict_does_not_change_experiment_state(reg):
    fz, inputs = ready(reg)
    before = reg.state("EXP-0101")
    v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=None)
    assert v.outcome == "INCONCLUSIVE" and reg.state("EXP-0101") == before == "OOS_EVALUATION"
