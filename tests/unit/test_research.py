"""FEAT-017 — TC-ML-002..007, TC-ML-010..014, TC-ML-018; REQ-G-103, REQ-G-104, REQ-G-107, REQ-G-142.
Incluye las pruebas de QA3-03, 05, 07, 11, 12, 13, 17 y 19.

Infraestructura general con datos sintéticos. Ninguna estrategia ni preregistro del piloto (DEC-018).
"""
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import indicators as I  # noqa: E402
from swingpilot.research.backtest import EntrySignal, ExecutionModel, run_backtest  # noqa: E402
from swingpilot.research.experiments import ExperimentError, ExperimentRegistry  # noqa: E402
from swingpilot.research.preregistration import (PreregistrationError, check_min_history,  # noqa: E402
                                                 freeze, min_history_months, walk_forward_windows,
                                                 validate_wf_design)
from swingpilot.research.scaling import ScalerError, TrainOnlyScaler  # noqa: E402

H4 = 14_400_000
WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}


# --- Registro de experimentos (REQ-G-104, REQ-G-107, TC-ML-010) ----------------------------

@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-900_ok.md").write_text("Decisión de prueba\nAUTORIZA: EXP-0101 OOS_EVALUATION\nAUTORIZA: EXP-0101 APPROVED\n")
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def _preregister(reg, eid="EXP-0101", sha=None):
    # ORQ-017-01: PREREGISTERED cita el SHA-256 real del preregistro de prueba (antes "f"*64),
    # porque las desviaciones se vinculan a ese hash. Solo cambia la preparación.
    reg.create(eid, "x", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    reg.transition(eid, "PREREGISTERED", actor="orquestador",
                   evidence={"preregistration_sha256": sha or freeze(prereg()).sha256, "min_history_ok": True})


def _to_validation(reg, eid="EXP-0101", sha=None):
    _preregister(reg, eid, sha)
    reg.transition(eid, "DATA_VALIDATION", actor="orquestador")
    reg.transition(eid, "DEVELOPMENT", actor="orquestador", evidence={"snapshot_verified": True})
    reg.transition(eid, "VALIDATION", actor="orquestador")


def test_twelve_states_and_forward_only(reg):
    from swingpilot.research.experiments import STATES
    assert len(STATES) == 12
    reg.create("EXP-0101", "x", actor="orquestador")
    with pytest.raises(ExperimentError, match="no permitida"):
        reg.transition("EXP-0101", "DEVELOPMENT", actor="orquestador")
    reg.transition("EXP-0101", "DESIGN", actor="orquestador")
    with pytest.raises(ExperimentError, match="preregistration_sha256"):
        reg.transition("EXP-0101", "PREREGISTERED", actor="orquestador")


def test_tc_ml_014_insufficient_history_stays_in_design(reg):
    reg.create("EXP-0101", "x", actor="orquestador")
    reg.transition("EXP-0101", "DESIGN", actor="orquestador")
    with pytest.raises(ExperimentError, match="DESIGN"):
        reg.transition("EXP-0101", "PREREGISTERED", actor="orquestador",
                       evidence={"preregistration_sha256": "f" * 64, "min_history_ok": False})
    assert reg.state("EXP-0101") == "DESIGN"


def test_req_g_107_ai_cannot_approve_or_open_oos(reg):
    _to_validation(reg)
    with pytest.raises(ExperimentError, match="propietario"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="orquestador", evidence={"decision_ref": "DEC-900_ok.md"})
    with pytest.raises(ExperimentError, match="no existe"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-404_x.md"})
    reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-900_ok.md"})
    reg.transition("EXP-0101", "AUDIT", actor="orquestador")
    reg.transition("EXP-0101", "HUMAN_REVIEW", actor="orquestador")
    with pytest.raises(ExperimentError, match="propietario"):
        reg.transition("EXP-0101", "APPROVED", actor="orquestador", evidence={"decision_ref": "DEC-900_ok.md"})
    reg.transition("EXP-0101", "APPROVED", actor="propietario", evidence={"decision_ref": "DEC-900_ok.md"})
    assert reg.state("EXP-0101") == "APPROVED" and reg.eligible_state("EXP-0101") == "APPROVED"
    with pytest.raises(ExperimentError, match="terminal"):
        reg.transition("EXP-0101", "REJECTED", actor="propietario")


def test_qa3_04_decision_must_cite_the_experiment(reg, tmp_path):
    (tmp_path / "decisions" / "DEC-901_other.md").write_text("AUTORIZA: EXP-0199 OOS_EVALUATION\n")      # autoriza otro experimento
    _to_validation(reg)
    with pytest.raises(ExperimentError, match="no cita"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-901_other.md"})
    with pytest.raises(ExperimentError, match="sin ruta"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario",
                       evidence={"decision_ref": str(tmp_path / "decisions" / "DEC-900_ok.md")})


@pytest.mark.parametrize("bad", ["EXP-1", "EXP-00001", "exp-0001", "EXP-000A", "EXP-0001 ", " EXP-0001",
                                 "EXP-0001\n", "EXP-0001/x", "EXP-٠٠٠١", "EXP-A", "", None, 1])
def test_qa3r2_04_create_rejects_malformed_experiment_id(reg, bad):
    with pytest.raises(ExperimentError, match="EXP-NNNN"):
        reg.create(bad, "x", actor="orquestador")
    assert reg.records() == []                                     # Fail-Closed: nada escrito
    reg.create("EXP-0002", "control", actor="orquestador")
    assert reg.state("EXP-0002") == "IDEA"


@pytest.mark.parametrize("text", [
    "Se autoriza EXP-0101.",                         # mención en prosa, sin línea estructurada
    "Se RECHAZA EXP-0101 y no se autoriza nada.",    # la cita por subcadena lo aceptaba
    "AUTORIZA: EXP-01010",                           # otro experimento que contiene el id
    "AUTORIZA: EXP-0101X",
    "NO AUTORIZA: EXP-0101",                         # la línea no empieza en «AUTORIZA:»
    "> AUTORIZA: EXP-0101",
    "autoriza: EXP-0101",
    "AUTORIZA: exp-0101",
    "AUTORIZA:  EXP-0101",
    "AUTORIZA: EXP-0101 sin más",                    # tokens de más: no sigue la gramática
    "AUTORIZA: EXP-0101 lockbox SNAP-TEST",          # autoriza una partición, no la transición
])
def test_qa3r2_04_transition_requires_exact_authorization_line(reg, tmp_path, text):
    (tmp_path / "decisions" / "DEC-902_sub.md").write_text(text + "\n")
    _to_validation(reg)
    with pytest.raises(ExperimentError, match="no cita exactamente"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-902_sub.md"})
    assert reg.state("EXP-0101") == "VALIDATION"


def test_qa3r2_04_exact_line_still_authorizes(reg, tmp_path):
    (tmp_path / "decisions" / "DEC-903_ok.md").write_text("# Decisión\n\nTexto libre sobre EXP-0101.\n\nAUTORIZA: EXP-0101 OOS_EVALUATION   \n")
    _to_validation(reg)
    reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-903_ok.md"})
    assert reg.state("EXP-0101") == "OOS_EVALUATION"


def test_qa3r2_04_unreadable_decision_fails_closed(reg, tmp_path):
    (tmp_path / "decisions" / "DEC-904_bin.md").write_bytes(b"AUTORIZA: EXP-0101 OOS_EVALUATION\n\xff\xfe")
    _to_validation(reg)
    with pytest.raises(ExperimentError, match="no se puede leer"):
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-904_bin.md"})
    assert reg.state("EXP-0101") == "VALIDATION"


# --- Observación adicional de QA3R2-04 (FEAT-017): la línea de transición nombra el estado destino ---

_SETUP = "DEC-910_setup.md"      # válido con y sin estado destino: solo prepara el experimento


def _to_state_before(reg, tmp_path, target):
    (tmp_path / "decisions" / _SETUP).write_text("AUTORIZA: EXP-0101\nAUTORIZA: EXP-0101 OOS_EVALUATION\n")
    _to_validation(reg)
    if target != "OOS_EVALUATION":
        reg.transition("EXP-0101", "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": _SETUP})
        reg.transition("EXP-0101", "AUDIT", actor="orquestador")
        reg.transition("EXP-0101", "HUMAN_REVIEW", actor="orquestador")
    return reg.state("EXP-0101")


@pytest.mark.parametrize("target", ["OOS_EVALUATION", "APPROVED", "REJECTED", "INCONCLUSIVE"])
def test_qa3r2_04b_bare_line_no_longer_authorizes(reg, tmp_path, target):
    before = _to_state_before(reg, tmp_path, target)
    (tmp_path / "decisions" / "DEC-911_bare.md").write_text("AUTORIZA: EXP-0101\n")
    with pytest.raises(ExperimentError, match=f"no cita exactamente la línea «AUTORIZA: EXP-0101 {target}»"):
        reg.transition("EXP-0101", target, actor="propietario", evidence={"decision_ref": "DEC-911_bare.md"})
    assert reg.state("EXP-0101") == before                          # Fail-Closed: sin transición


@pytest.mark.parametrize("target", ["APPROVED", "REJECTED", "INCONCLUSIVE"])
def test_qa3r2_04b_oos_authorization_is_not_reused_for_other_states(reg, tmp_path, target):
    _to_state_before(reg, tmp_path, target)
    (tmp_path / "decisions" / "DEC-912_oos.md").write_text("AUTORIZA: EXP-0101 OOS_EVALUATION\n")
    with pytest.raises(ExperimentError, match="no cita exactamente"):
        reg.transition("EXP-0101", target, actor="propietario", evidence={"decision_ref": "DEC-912_oos.md"})
    assert reg.state("EXP-0101") == "HUMAN_REVIEW"


@pytest.mark.parametrize("text", [
    "AUTORIZA: EXP-0101 approved",                   # mayúsculas exactas
    "AUTORIZA: EXP-0101 APPROVED extra",             # tokens de más
    "AUTORIZA: EXP-0101  APPROVED",
    "AUTORIZA: EXP-0101 REJECTED",                   # otro estado destino
    "AUTORIZA: EXP-01010 APPROVED",
    "NO AUTORIZA: EXP-0101 APPROVED",
])
def test_qa3r2_04b_malformed_or_other_state_line_does_not_approve(reg, tmp_path, text):
    _to_state_before(reg, tmp_path, "APPROVED")
    (tmp_path / "decisions" / "DEC-913_bad.md").write_text(text + "\n")
    with pytest.raises(ExperimentError, match="no cita exactamente"):
        reg.transition("EXP-0101", "APPROVED", actor="propietario", evidence={"decision_ref": "DEC-913_bad.md"})
    assert reg.state("EXP-0101") == "HUMAN_REVIEW"


@pytest.mark.parametrize("target", ["APPROVED", "REJECTED", "INCONCLUSIVE"])
def test_qa3r2_04b_owner_decision_with_its_exact_line_succeeds(reg, tmp_path, target):
    _to_state_before(reg, tmp_path, target)
    (tmp_path / "decisions" / "DEC-914_ok.md").write_text(f"# Decisión\n\nAUTORIZA: EXP-0101 {target}\n")
    reg.transition("EXP-0101", target, actor="propietario", evidence={"decision_ref": "DEC-914_ok.md"})
    assert reg.state("EXP-0101") == target


def test_qa3r2_04b_decision_ok_request_modes(reg, tmp_path):
    (tmp_path / "decisions" / "DEC-915_all.md").write_text(
        "AUTORIZA: EXP-0101 APPROVED\nAUTORIZA: EXP-0101 lockbox SNAP-TEST\nAUTORIZA: EXP-0101 AUDIT\n")
    ok = reg.decision_ok
    assert ok("DEC-915_all.md", "EXP-0101", target_state="APPROVED") is None
    assert ok("DEC-915_all.md", "EXP-0101", "lockbox", "SNAP-TEST") is None    # gramática de partición intacta
    assert "no ambas" in ok("DEC-915_all.md", "EXP-0101")                      # ni transición ni partición
    assert "no ambas" in ok("DEC-915_all.md", "EXP-0101", "lockbox", "SNAP-TEST", target_state="APPROVED")
    for st in ("AUDIT", "HUMAN_REVIEW", "IDEA", "approved", "", "PENDING_DOCUMENTATION"):
        assert "estado destino no válido" in ok("DEC-915_all.md", "EXP-0101", target_state=st), st


def test_qa3_03_antecedents_restricted_and_not_eligible(reg):
    for bad in ("APPROVED", "OOS_EVALUATION", "IDEA", "VALIDATION"):
        with pytest.raises(ExperimentError, match="no permitido"):
            reg.register_antecedent("EXP-X", "x", bad, source="s", note="n")
    reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="DEC-017", note="n")
    assert reg.state("EXP-0001") == "PENDING_DOCUMENTATION" and reg.eligible_state("EXP-0001") is None


def test_tc_ml_010_rejected_experiments_are_kept_and_counted(reg):
    _to_validation(reg, "EXP-0101")
    reg.transition("EXP-0101", "REJECTED", actor="orquestador", reason="umbrales no cumplidos")
    reg.create("EXP-0102", "y", actor="orquestador")
    reg.register_antecedent("EXP-0001", "Trend Following H4 (antecedente)", "PENDING_DOCUMENTATION",
                            source="DEC-017", note="sin documentación")
    reg.register_antecedent("ANT-MR-H1", "Mean Reversion H1", "REJECTED", source="DEC-017", note="rechazada")
    exps = reg.experiments()
    assert exps["EXP-0101"]["state"] == "REJECTED" and len(exps["EXP-0101"]["history"]) == 7
    assert reg.trials_count() == 4
    with pytest.raises(ExperimentError, match="reutilizan"):
        reg.create("EXP-0101", "otra vez", actor="orquestador")
    with pytest.raises(ExperimentError, match="antecedente"):
        reg.transition("EXP-0001", "DESIGN", actor="propietario")
    assert len(reg.path.read_text().splitlines()) == 10   # append-only


def test_repository_registry_contains_declared_antecedents():
    repo = Path(__file__).resolve().parents[2]
    r = ExperimentRegistry(repo / "research" / "experiments" / "registry.jsonl")
    ex = r.experiments()
    assert ex["EXP-0001"]["state"] == "PENDING_DOCUMENTATION" and ex["ANT-MR-H1"]["state"] == "REJECTED"
    assert r.eligible_state("EXP-0001") is None and r.trials_count() >= 2


# --- Preregistro (REQ-G-103, TC-ML-013, TC-ML-014) ------------------------------------------

def prereg():
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis",
                               "justification", "universe", "period", "variables", "entry_rules",
                               "exit_rules", "model_config", "data_split", "metrics", "costs",
                               "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id="EXP-0101", timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             snapshot={"id": "SNAP-X"}, observed_trade_rate_per_month=3.0, trade_rate_source="train_only",
             antecedents=["EXP-0001"], trials_count=3, min_history={"ok": True},
             statistical_tests={"dsr_min_probability": "<pre>"})
    return p


def test_tc_ml_013_deviation_after_oos_derived_from_access_log(reg):
    # QA3R2-07: se pasa además el registro de experimentos (fuente de verdad); sin consumo
    # registrado, el registro de accesos sigue pudiendo AÑADIR evidencia de exposición.
    _preregister(reg)                                   # ORQ-017-01: vinculación por SHA-256
    fz = freeze(prereg())
    fz.verify()
    log = [{"allowed": True, "partition": "train_val", "experiment_id": None}]
    fz.record_deviation("limitations", "otra", "aclaración antes de ver OOS", registry=reg, access_history=log)
    assert fz.confirmatory
    # un acceso denegado o de otro experimento no cuenta
    log += [{"allowed": False, "partition": "oos", "experiment_id": "EXP-0101"},
            {"allowed": True, "partition": "oos", "experiment_id": "EXP-0199"}]
    fz.record_deviation("limitations", "otra2", "sigue antes de OOS", registry=reg, access_history=log)
    assert fz.confirmatory
    log.append({"allowed": True, "partition": "oos", "experiment_id": "EXP-0101"})
    fz.record_deviation("wf_design", {**WF, "n_windows": 3}, "cambio tras ver OOS", registry=reg, access_history=log)
    assert not fz.confirmatory
    assert fz.content["wf_design"]["n_windows"] == 2
    fz.content["hypothesis"] = "alterada"
    with pytest.raises(PreregistrationError):
        fz.verify()


# --- QA3R2-07: exposición a OOS/LOCKBOX derivada del registro de experimentos ---------------
# El defecto original (daa78d0: registro con consumo y access_history vacío → after_oos False
# y experimento confirmatorio) se reproduce aparte, porque la firma cambia (registry obligatorio).

NEW_WF = {**WF, "n_windows": 3}
CONTRADICTING_LOGS = {
    "none": None,
    "empty": [],
    "stale_train_val": [{"allowed": True, "partition": "train_val", "experiment_id": None}],
    "denied_oos": [{"allowed": False, "partition": "oos", "experiment_id": "EXP-0101"}],
    "other_experiment": [{"allowed": True, "partition": "oos", "experiment_id": "EXP-0199"}],
}


def _oos_ready(reg, eid="EXP-0101"):
    _to_validation(reg, eid)
    reg.transition(eid, "OOS_EVALUATION", actor="propietario", evidence={"decision_ref": "DEC-900_ok.md"})


def _consume(reg, partition="oos", sid="SNAP-TEST1", eid="EXP-0101"):
    assert reg.claim_partition(snapshot_id=sid, partition=partition, experiment_id=eid,
                               snapshot_last_open_time=0, decision_ref="DEC-900_ok.md") is not None


@pytest.mark.parametrize("partition", ["oos", "lockbox"])
@pytest.mark.parametrize("log_name", list(CONTRADICTING_LOGS))
def test_qa3r2_07_registry_consumption_cannot_be_overridden_by_caller_log(reg, partition, log_name):
    _oos_ready(reg)
    _consume(reg, partition)
    fz = freeze(prereg())
    d = fz.record_deviation("wf_design", NEW_WF, "cambio tras OOS", registry=reg,
                            access_history=CONTRADICTING_LOGS[log_name])
    assert d["after_oos"] is True and not fz.confirmatory


def test_qa3r2_07_consumption_on_any_snapshot_counts(reg):
    _oos_ready(reg)
    _consume(reg, "oos", sid="SNAP-TEST9")          # el preregistro cita otra snapshot («SNAP-X»)
    fz = freeze(prereg())
    assert fz.oos_seen(reg, []) is True


@pytest.mark.parametrize("bad", [None, "registry.jsonl", object(), [{"kind": "PARTITION_CONSUMED"}]],
                         ids=["none", "path_str", "object", "list"])
def test_qa3r2_07_invalid_registry_fails_closed(bad):
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="ExperimentRegistry"):
        fz.record_deviation("wf_design", NEW_WF, "x", registry=bad, access_history=[])
    assert fz.deviations == []


def test_qa3r2_07_unregistered_or_antecedent_experiment_fails_closed(reg):
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="nativo"):           # registro vacío
        fz.oos_seen(reg)
    p = prereg()
    p["experiment_id"] = "EXP-0002"
    reg.register_antecedent("EXP-0002", "antecedente", "REJECTED", "DEC-018", "nota")
    with pytest.raises(PreregistrationError, match="nativo"):           # antecedente declarado
        freeze(p).record_deviation("wf_design", NEW_WF, "x", registry=reg)


def test_qa3r2_07_unreadable_or_corrupt_registry_fails_closed(reg, tmp_path):
    reg.create("EXP-0101", "x", actor="orquestador")
    fz = freeze(prereg())
    with open(reg.path, "a") as fh:
        fh.write("{no es json\n")
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    d = tmp_path / "dir_registry.jsonl"
    d.mkdir()                                                            # ilegible como archivo
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        fz.oos_seen(ExperimentRegistry(d, tmp_path / "decisions"))
    orphan = tmp_path / "orphan.jsonl"                                   # TRANSITION sin CREATED
    orphan.write_text('{"kind": "TRANSITION", "experiment_id": "EXP-0101", "to": "DESIGN"}\n')
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        fz.oos_seen(ExperimentRegistry(orphan, tmp_path / "decisions"))
    assert fz.deviations == []


@pytest.mark.parametrize("bad_record", [
    {"kind": "PARTITION_CONSUMED", "partition": "oos", "snapshot_id": "SNAP-TEST1"},                 # sin experimento
    {"kind": "PARTITION_CONSUMED", "experiment_id": "EXP-0101", "partition": "train_val", "snapshot_id": "SNAP-TEST1"},
    {"kind": "PARTITION_CONSUMED", "experiment_id": "EXP-0101", "partition": "oos"},                 # sin snapshot
    {"kind": "PARTITION_CONSUMED", "experiment_id": "EXP-0199", "partition": "OOS", "snapshot_id": "SNAP-TEST1"},
], ids=["no_experiment", "bad_partition", "no_snapshot", "other_exp_bad_partition"])
def test_qa3r2_07_inconsistent_consumption_record_fails_closed(reg, bad_record):
    import json as _json
    _oos_ready(reg)
    with open(reg.path, "a") as fh:
        fh.write(_json.dumps(bad_record) + "\n")
    with pytest.raises(PreregistrationError, match="incoherente"):
        freeze(prereg()).oos_seen(reg)


def test_qa3r2_07_consumption_without_oos_evaluation_is_inconsistent(reg):
    _to_validation(reg)                       # VALIDATION: nunca autorizado para OOS
    _consume(reg, "oos")                      # claim_partition no comprueba el estado (lo hace partitions.py)
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="sin transición a OOS_EVALUATION"):
        fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    assert fz.deviations == []


@pytest.mark.parametrize("bad_log", ["oos", {"allowed": True}, [["oos"]], [None]], ids=["str", "dict", "list_of_list", "list_of_none"])
def test_qa3r2_07_malformed_access_history_fails_closed(reg, bad_log):
    reg.create("EXP-0101", "x", actor="orquestador")
    with pytest.raises(PreregistrationError, match="registro de accesos"):
        freeze(prereg()).oos_seen(reg, bad_log)


def test_qa3r2_07_authorization_without_consumption_is_not_exposure(reg):
    _oos_ready(reg)                           # autorizado (OOS_EVALUATION) pero sin consumo
    fz = freeze(prereg())
    assert fz.oos_seen(reg) is False
    reg.transition("EXP-0101", "AUDIT", actor="orquestador")
    fz.record_deviation("wf_design", NEW_WF, "sin exposición real", registry=reg, access_history=[])
    assert fz.confirmatory


def test_qa3r2_07_other_experiment_consumption_does_not_count(reg):
    _preregister(reg)                                   # ORQ-017-01: vinculación por SHA-256
    with open(reg.decisions_dir / "DEC-900_ok.md", "a") as fh:
        fh.write("AUTORIZA: EXP-0102 OOS_EVALUATION\n")
    _oos_ready(reg, "EXP-0102")
    _consume(reg, "oos", eid="EXP-0102")
    _consume(reg, "lockbox", eid="EXP-0102")
    fz = freeze(prereg())
    fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    assert fz.confirmatory


def test_qa3r2_07_pre_exposure_and_non_design_deviations_preserved(reg):
    _oos_ready(reg)
    fz = freeze(prereg())
    fz.record_deviation("wf_design", NEW_WF, "antes de la exposición", registry=reg)
    _consume(reg, "oos")
    assert fz.confirmatory                                   # la desviación previa no cambia
    d = fz.record_deviation("limitations", "otra", "campo no de diseño tras OOS", registry=reg)
    assert d["after_oos"] is True and fz.confirmatory        # campo fuera de DESIGN_FIELDS
    fz.record_deviation("metrics", "otra", "campo de diseño tras OOS", registry=reg)
    assert not fz.confirmatory
    assert fz.content["wf_design"]["n_windows"] == 2         # el contenido congelado no cambia
    fz.verify()


# --- ORQ-017-01: persistencia duradera de las desviaciones (registros DEVIATION) -------------
# El defecto original (4ad42ed: las desviaciones solo vivían en memoria; un objeto reconstruido o
# otro proceso volvía a ver el experimento como confirmatorio) se reproduce aparte, porque la API
# cambia (confirmatorio derivado del registro).

import json as _json  # noqa: E402
import subprocess as _subprocess  # noqa: E402
import threading as _threading  # noqa: E402
import fcntl as _fcntl  # noqa: E402

from swingpilot.research import experiments as _experiments_mod  # noqa: E402
from swingpilot.research.preregistration import (DeviationPersistenceUncertain,  # noqa: E402
                                                 FrozenPreregistration, confirmatory_status)

SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")


def _rebuild(fz):
    """Objeto nuevo con el mismo contenido congelado (otra sesión)."""
    return FrozenPreregistration(_json.loads(_json.dumps(fz.content)), fz.sha256, fz.frozen_at_utc)


def _fresh_reg(reg):
    return ExperimentRegistry(reg.path, reg.decisions_dir)


def _deviation_records(reg):
    return [r for r in reg.records() if r["kind"] == "DEVIATION"]


def test_orq_017_01_regression_reconstruction_after_exposure_is_not_confirmatory(reg):
    _oos_ready(reg)
    _consume(reg, "oos")
    fz = freeze(prereg())
    rec = fz.record_deviation("wf_design", NEW_WF, "cambio tras OOS", registry=reg)
    assert rec["after_oos"] is True and rec["authorizes_change"] is False
    # otra sesión: registro y preregistro nuevos
    fresh, fz2 = _fresh_reg(reg), _rebuild(fz)
    st = fz2.confirmatory_status(fresh)
    assert st["confirmatory"] is False and st["design_deviations_after_oos"] == [rec["deviation_id"]]
    assert confirmatory_status(fresh, "EXP-0101")["confirmatory"] is False          # consulta HUMAN_REVIEW
    d = st["deviations"][0]
    assert (d["field"], d["old"], d["new"], d["justification"]) == ("wf_design", dict(WF), NEW_WF, "cambio tras OOS")
    assert fz2.content["wf_design"] == dict(WF)                                     # contenido congelado intacto
    fz2.verify()


def test_orq_017_01_regression_separate_process_writes_parent_reconstructs(reg):
    _oos_ready(reg)
    _consume(reg, "oos")
    fz = freeze(prereg())
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]);"
            "from swingpilot.research.experiments import ExperimentRegistry;"
            "from swingpilot.research.preregistration import FrozenPreregistration;"
            "c = json.loads(sys.argv[2]);"
            "r = ExperimentRegistry(c['path'], c['dec']);"
            "f = FrozenPreregistration(c['content'], c['sha'], c['at']);"
            "print(f.record_deviation('wf_design', c['new'], 'cambio en otro proceso', registry=r)['after_oos'])")
    arg = _json.dumps({"path": str(reg.path), "dec": str(reg.decisions_dir), "content": fz.content,
                       "sha": fz.sha256, "at": fz.frozen_at_utc, "new": NEW_WF})
    out = _subprocess.run([sys.executable, "-c", code, SRC_DIR, arg], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "True"
    assert _rebuild(fz).confirmatory_status(_fresh_reg(reg))["confirmatory"] is False


def test_orq_017_01_deterministic_concurrency_exposure_and_append_under_same_lock(reg):
    """Mientras otro titular tiene el bloqueo exclusivo, la desviación espera; el consumo
    escrito antes de liberar queda antes en el archivo y la desviación sale after_oos=True."""
    _oos_ready(reg)
    fz = freeze(prereg())
    started, result = _threading.Event(), {}

    def worker():
        started.set()
        try:
            result["rec"] = fz.record_deviation("wf_design", NEW_WF, "concurrente", registry=reg)
        except BaseException as exc:          # pragma: no cover - se informa en la aserción
            result["exc"] = exc

    lock_path = reg.path.with_name(reg.path.name + ".lock")
    with open(lock_path, "a") as lk:
        _fcntl.flock(lk, _fcntl.LOCK_EX)
        t = _threading.Thread(target=worker)
        t.start()
        assert started.wait(5)
        t.join(0.3)
        assert t.is_alive(), "record_deviation no esperó al bloqueo exclusivo del registro"
        assert _deviation_records(reg) == []
        reg._write({"kind": "PARTITION_CONSUMED", "snapshot_id": "SNAP-TEST1", "partition": "oos",
                    "experiment_id": "EXP-0101", "snapshot_last_open_time": 0,
                    "decision_ref": "DEC-900_ok.md", "actor": "propietario"})
        _fcntl.flock(lk, _fcntl.LOCK_UN)
    t.join(10)
    assert not t.is_alive() and "exc" not in result, result
    assert result["rec"]["after_oos"] is True
    kinds = [r["kind"] for r in reg.records()]
    assert kinds.index("PARTITION_CONSUMED") < kinds.index("DEVIATION")
    assert _rebuild(fz).confirmatory_status(_fresh_reg(reg))["confirmatory"] is False


def test_orq_017_01_exposure_chronology_is_file_order(reg):
    _oos_ready(reg)
    fz = freeze(prereg())
    before = fz.record_deviation("wf_design", NEW_WF, "antes de la exposición", registry=reg)
    _consume(reg, "lockbox")
    after_nd = fz.record_deviation("limitations", "otra", "no de diseño tras exposición", registry=reg)
    assert before["after_oos"] is False and after_nd["after_oos"] is True
    st = _rebuild(fz).confirmatory_status(_fresh_reg(reg))
    assert st["confirmatory"] is True and len(st["deviations"]) == 2
    after_d = fz.record_deviation("metrics", "otra", "de diseño tras exposición", registry=reg)
    st = _rebuild(fz).confirmatory_status(_fresh_reg(reg))
    assert st["confirmatory"] is False and st["design_deviations_after_oos"] == [after_d["deviation_id"]]


def test_orq_017_01_access_log_exposure_is_persisted_and_verifiable(reg):
    _preregister(reg)
    fz = freeze(prereg())
    log = [{"allowed": True, "partition": "oos", "experiment_id": "EXP-0101", "snapshot_id": "SNAP-TEST1",
            "at_utc": "2026-11-24T00:00:00Z", "reason": "x"},
           {"allowed": True, "partition": "train_val", "experiment_id": None}]
    rec = fz.record_deviation("wf_design", NEW_WF, "tras acceso registrado solo en el log", registry=reg,
                              access_history=log)
    assert rec["after_oos"] is True and rec["access_log_evidence"] == [log[0]]
    st = _rebuild(fz).confirmatory_status(_fresh_reg(reg))           # sin pasar el log al reconstruir
    assert st["confirmatory"] is False and st["deviations"][0]["access_log_evidence"] == [log[0]]


def test_orq_017_01_hash_binding(reg):
    _preregister(reg)
    other = prereg()
    other["limitations"] = "contenido distinto"
    with pytest.raises(PreregistrationError, match="SHA-256"):           # preregistro con otro hash
        freeze(other).record_deviation("wf_design", NEW_WF, "x", registry=reg)
    assert _deviation_records(reg) == []
    fz = freeze(prereg())
    fz.record_deviation("limitations", "y", "válida", registry=reg)
    # DEVIATION válida de OTRO experimento con otro hash: se ignora
    reg._append({"kind": "DEVIATION", "deviation_id": "a" * 32, "experiment_id": "EXP-0199",
                 "preregistration_sha256": "b" * 64, "field": "metrics", "old": 1, "new": 2,
                 "justification": "ajena", "after_oos": True, "access_log_evidence": [], "actor": "x",
                 "authorizes_change": False})
    assert _rebuild(fz).confirmatory_status(_fresh_reg(reg))["confirmatory"] is True
    # DEVIATION del MISMO experimento con hash distinto: se rechaza
    reg._append({"kind": "DEVIATION", "deviation_id": "c" * 32, "experiment_id": "EXP-0101",
                 "preregistration_sha256": "d" * 64, "field": "limitations", "old": 1, "new": 2,
                 "justification": "x", "after_oos": False, "access_log_evidence": [], "actor": "x",
                 "authorizes_change": False})
    with pytest.raises(PreregistrationError, match="hash incoherente"):
        confirmatory_status(_fresh_reg(reg), "EXP-0101")


def test_orq_017_01_requires_preregistered_transition(reg):
    reg.create("EXP-0101", "x", actor="orquestador")
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="PREREGISTERED"):
        fz.record_deviation("limitations", "y", "x", registry=reg)
    with pytest.raises(PreregistrationError, match="PREREGISTERED"):
        confirmatory_status(reg, "EXP-0101")


def _valid_deviation(**kw):
    rec = {"kind": "DEVIATION", "deviation_id": "e" * 32, "experiment_id": "EXP-0101",
           "preregistration_sha256": freeze(prereg()).sha256, "field": "limitations", "old": "a", "new": "b",
           "justification": "x", "after_oos": False, "access_log_evidence": [], "actor": "orquestador",
           "authorizes_change": False}
    rec.update(kw)
    return rec


_MALFORMED = {
    "missing_key": lambda: {k: v for k, v in _valid_deviation().items() if k != "old"},
    "bad_deviation_id": lambda: _valid_deviation(deviation_id="xyz"),
    "bad_sha": lambda: _valid_deviation(preregistration_sha256="F" * 64),
    "unknown_field": lambda: _valid_deviation(field="no_existe"),
    "empty_justification": lambda: _valid_deviation(justification="  "),
    "after_oos_not_bool": lambda: _valid_deviation(after_oos=1),
    "authorizes_change": lambda: _valid_deviation(authorizes_change=True),
    "bad_access_evidence": lambda: _valid_deviation(after_oos=True, access_log_evidence=[{"allowed": False,
                                                    "partition": "oos", "experiment_id": "EXP-0101"}]),
    "after_oos_true_without_evidence": lambda: _valid_deviation(after_oos=True),
    "other_experiment_malformed": lambda: _valid_deviation(experiment_id="EXP-0199", field="no_existe"),
}


@pytest.mark.parametrize("case", list(_MALFORMED))
def test_orq_017_01_malformed_deviation_evidence_fails_closed(reg, case):
    _preregister(reg)
    reg._append(_MALFORMED[case]())
    with pytest.raises(PreregistrationError, match="incoherente"):
        confirmatory_status(_fresh_reg(reg), "EXP-0101")
    with pytest.raises(PreregistrationError, match="incoherente"):       # tampoco se puede añadir otra
        freeze(prereg()).record_deviation("limitations", "z", "x", registry=reg)


def test_orq_017_01_chronology_and_duplicate_inconsistencies_fail_closed(reg, tmp_path):
    # after_oos=False guardado, pero el consumo va antes en el archivo
    _oos_ready(reg)
    _consume(reg, "oos")
    reg._append(_valid_deviation(field="wf_design"))
    with pytest.raises(PreregistrationError, match="cronología"):
        confirmatory_status(_fresh_reg(reg), "EXP-0101")
    # deviation_id duplicado
    r2 = ExperimentRegistry(tmp_path / "r2.jsonl", reg.decisions_dir)
    _preregister(r2)
    r2._append(_valid_deviation())
    r2._append(_valid_deviation())
    with pytest.raises(PreregistrationError, match="duplicado"):
        confirmatory_status(r2, "EXP-0101")
    # DEVIATION anterior a PREREGISTERED
    r3 = ExperimentRegistry(tmp_path / "r3.jsonl", reg.decisions_dir)
    r3.create("EXP-0101", "x", actor="orquestador")
    r3._append(_valid_deviation())
    r3.transition("EXP-0101", "DESIGN", actor="orquestador")
    r3.transition("EXP-0101", "PREREGISTERED", actor="orquestador",
                  evidence={"preregistration_sha256": freeze(prereg()).sha256, "min_history_ok": True})
    with pytest.raises(PreregistrationError, match="anterior a PREREGISTERED"):
        confirmatory_status(r3, "EXP-0101")
    # JSON corrupto
    with open(r3.path, "a") as fh:
        fh.write('{"kind": "DEVIATION", "deviation_id"\n')
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        confirmatory_status(ExperimentRegistry(r3.path, reg.decisions_dir), "EXP-0101")


def test_orq_017_01_fsync_failure_is_uncertain_record_present(reg, monkeypatch):
    _oos_ready(reg)
    _consume(reg, "oos")
    fz = freeze(prereg())

    def bad_fsync(fd):
        raise OSError("fsync simulado")
    monkeypatch.setattr(_experiments_mod.os, "fsync", bad_fsync)
    with pytest.raises(DeviationPersistenceUncertain, match="incierta"):
        fz.record_deviation("wf_design", NEW_WF, "tras OOS", registry=reg)
    monkeypatch.undo()
    assert fz.deviations == []                                   # no se informa éxito
    with pytest.raises(PreregistrationError, match="incierta"):
        fz.confirmatory                                          # no certifica nada
    with pytest.raises(PreregistrationError, match="incierta"):
        fz.confirmatory_status(reg)
    with pytest.raises(PreregistrationError, match="incierta"):
        fz.record_deviation("limitations", "y", "x", registry=reg)
    # el registro sí quedó escrito: la reconstrucción lo ve
    assert len(_deviation_records(reg)) == 1
    assert _rebuild(fz).confirmatory_status(_fresh_reg(reg))["confirmatory"] is False


def test_orq_017_01_write_failure_before_bytes_is_still_uncertain(reg, monkeypatch):
    _preregister(reg)
    fz = freeze(prereg())

    def failing_write(self, rec):
        raise OSError("disco lleno simulado")
    monkeypatch.setattr(ExperimentRegistry, "_write", failing_write)
    with pytest.raises(DeviationPersistenceUncertain):
        fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    monkeypatch.undo()
    assert fz.deviations == []
    with pytest.raises(PreregistrationError, match="incierta"):
        fz.confirmatory


def test_orq_017_01_partial_write_fails_closed_for_everyone(reg, monkeypatch):
    _preregister(reg)
    fz = freeze(prereg())

    def half_write(self, rec):
        line = _json.dumps({"at_utc": "t", **rec}, ensure_ascii=False, sort_keys=True)
        with open(self.path, "a") as fh:
            fh.write(line[: len(line) // 2])
        raise OSError("corte a mitad de escritura")
    monkeypatch.setattr(ExperimentRegistry, "_write", half_write)
    with pytest.raises(DeviationPersistenceUncertain):
        fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    monkeypatch.undo()
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        _rebuild(fz).confirmatory_status(_fresh_reg(reg))
    with pytest.raises(PreregistrationError, match="ilegible o corrupto"):
        _rebuild(fz).record_deviation("limitations", "y", "x", registry=_fresh_reg(reg))


def test_orq_017_01_build_failure_writes_nothing_and_is_not_uncertain(reg):
    _preregister(reg)
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="serializable") as ei:
        fz.record_deviation("limitations", object(), "x", registry=reg)
    assert not isinstance(ei.value, DeviationPersistenceUncertain)
    assert _deviation_records(reg) == []
    fz.record_deviation("limitations", "y", "x", registry=reg)       # el objeto sigue utilizable
    assert fz.confirmatory is True


def test_orq_017_01_guards_justification_content_and_no_default_certification(reg):
    _preregister(reg)
    fz = freeze(prereg())
    with pytest.raises(PreregistrationError, match="falta el registro"):
        fz.confirmatory                                          # sin registro: no se certifica
    with pytest.raises(PreregistrationError, match="justificarse"):
        fz.record_deviation("limitations", "y", "   ", registry=reg)
    fz.content["hypothesis"] = "alterada"
    with pytest.raises(PreregistrationError, match="alterado"):
        fz.record_deviation("limitations", "y", "x", registry=reg)
    assert _deviation_records(reg) == []
    with pytest.raises(ExperimentError, match="DEVIATION"):
        reg.append_deviation(lambda: {"kind": "PARTITION_CONSUMED"})


def test_orq_017_01_trials_count_and_transitions_unaffected(reg):
    _oos_ready(reg)
    before = (reg.trials_count(), reg.state("EXP-0101"), reg.experiments()["EXP-0101"]["history"])
    fz = freeze(prereg())
    fz.record_deviation("limitations", "y", "x", registry=reg)
    fz.record_deviation("wf_design", NEW_WF, "x", registry=reg)
    assert (reg.trials_count(), reg.state("EXP-0101"), reg.experiments()["EXP-0101"]["history"]) == before
    reg.transition("EXP-0101", "AUDIT", actor="orquestador")
    reg.transition("EXP-0101", "HUMAN_REVIEW", actor="orquestador")
    assert reg.state("EXP-0101") == "HUMAN_REVIEW" and reg.trials_count() == before[0]


def test_freeze_rejects_incomplete_or_invalid():
    p = prereg()
    del p["null_hypothesis"]
    with pytest.raises(PreregistrationError, match="incompleto"):
        freeze(p)
    p = prereg()
    p["trade_rate_source"] = "train_val"
    with pytest.raises(PreregistrationError, match="Train"):
        freeze(p)
    p = prereg()
    p["min_history"] = {"ok": False}
    with pytest.raises(PreregistrationError, match="DESIGN"):
        freeze(p)


def test_freeze_hash_is_canonical():
    a, b = prereg(), prereg()
    b = dict(reversed(list(b.items())))
    assert freeze(a).sha256 == freeze(b).sha256


def test_tc_ml_014_min_history_formula_and_limitation():
    assert min_history_months(8.0, WF) == pytest.approx(38 / 0.70)
    assert min_history_months(1.0, WF) == pytest.approx(30 / (0.15 * 1.0))
    r = check_min_history(1.0, "train_only", available_months=111, wf=WF)
    assert not r["ok"] and r["limitation"] and r["required_months"] == 200
    # 30/(0.15·1.8) = 111.1 > 111: el «~1.8 trades/mes» de DEC-013 es aproximado
    assert not check_min_history(1.8, "train_only", available_months=111, wf=WF)["ok"]
    assert check_min_history(1.85, "train_only", available_months=111, wf=WF)["ok"]
    with pytest.raises(PreregistrationError):
        check_min_history(3.0, "oos", available_months=111, wf=WF)


def test_tc_ml_011_wf_structure_and_embargo():
    validate_wf_design(WF, label_horizon_months=2)
    with pytest.raises(PreregistrationError, match="embargo"):
        validate_wf_design(WF, label_horizon_months=3)
    with pytest.raises(PreregistrationError, match="ventanas"):
        validate_wf_design({**WF, "n_windows": 1}, 1)
    with pytest.raises(PreregistrationError, match="train_months"):
        validate_wf_design({**WF, "train_months": 12}, 1)
    s, e = pd.Timestamp("2017-09-01"), pd.Timestamp("2024-01-01")
    ws = walk_forward_windows(s, e, WF)
    # Fechas esperadas escritas a mano (no con la aritmética del código; QA3-19)
    expected = [("2017-09-01", "2019-09-01", "2019-11-01", "2020-05-01"),
                ("2018-03-01", "2020-03-01", "2020-05-01", "2020-11-01")]
    got = [tuple(str(x.date()) for x in (w.train_start, w.train_end, w.test_start, w.test_end)) for w in ws]
    assert got == expected
    # Ninguna vela H4 de entrenamiento cae en el embargo o en la prueba de su ventana
    for w in ws:
        train = pd.date_range(w.train_start, w.train_end, freq="4h", inclusive="left")
        test = pd.date_range(w.test_start, w.test_end, freq="4h", inclusive="left")
        assert train.max() < w.test_start and (test.min() - train.max()) > pd.Timedelta(days=59)
    with pytest.raises(PreregistrationError, match="Train\\+Val"):
        walk_forward_windows(s, pd.Timestamp("2020-01-01"), WF)


# --- Indicadores sin look-ahead (TC-ML-002) ---------------------------------------------------

def ohlc(n=400, seed=1, nan_at=()):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
    df = pd.DataFrame({"open_time": np.arange(n) * H4, "open": o, "high": h, "low": lo, "close": c})
    for i in nan_at:
        df.loc[i, ["open", "high", "low", "close"]] = np.nan
    return df


@pytest.mark.parametrize("name", ["ema", "atr", "adx", "rv", "pct"])
def test_tc_ml_002_truncation_invariance(name):
    df = ohlc(nan_at=(150, 151))
    fns = {
        "ema": lambda d: I.ema(d["close"], 20),
        "atr": lambda d: I.atr(d["high"], d["low"], d["close"], 14),
        "adx": lambda d: I.adx(d["high"], d["low"], d["close"], 14),
        "rv": lambda d: I.realized_volatility(d["close"], 20),
        "pct": lambda d: I.expanding_percentile_rank(I.realized_volatility(d["close"], 10), 30),
    }
    full = fns[name](df)
    for t in (60, 149, 152, 260, 399):
        pd.testing.assert_series_equal(full.iloc[: t + 1], fns[name](df.iloc[: t + 1]), check_names=False)


def test_indicators_nan_rows_are_not_interpolated():
    e = I.ema(ohlc(nan_at=(150,))["close"], 20)
    assert math.isnan(e[150]) and not math.isnan(e[151])


def test_expanding_percentile_rank_values_and_speed():
    s = pd.Series([1.0, 2.0, 3.0, 0.5, 10.0, 2.0])
    assert list(I.expanding_percentile_rank(s, 1)) == [1.0, 1.0, 1.0, 0.25, 1.0, 4 / 6]
    big = pd.Series(np.random.default_rng(0).normal(size=80_000))
    t0 = time.perf_counter()
    I.expanding_percentile_rank(big, 30)
    assert time.perf_counter() - t0 < 5.0   # QA3-17: antes ~1 min para 80k


# --- Normalización (TC-ML-003, QA3-13) -----------------------------------------------------

def test_tc_ml_003_scaler_fits_only_on_train_data_once():
    tr = pd.DataFrame({"open_time": [0, 1, 2], "x": [1.0, 2.0, 3.0]})
    oos = pd.DataFrame({"open_time": [10, 11], "x": [10.0, 20.0]})
    mixed = pd.concat([tr, oos])
    sc = TrainOnlyScaler()
    with pytest.raises(ScalerError, match="posteriores"):
        sc.fit(mixed, columns=["x"], train_end_ms=5)          # la etiqueta no basta: se miran los datos
    with pytest.raises(ScalerError, match="temporal"):
        sc.fit(tr[["x"]], columns=["x"], train_end_ms=5)
    sc.fit(tr, columns=["x"], train_end_ms=5)
    sd = np.std([1, 2, 3])
    assert sc.transform(oos)["x"].tolist() == pytest.approx([(10 - 2) / sd, (20 - 2) / sd])
    with pytest.raises(ScalerError, match="reajusta"):
        sc.fit(tr, columns=["x"], train_end_ms=5)


# --- Modelo de ejecución (TC-ML-018, REQ-G-142, QA3-11, QA3-12) ---------------------------

def bars(rows):
    return pd.DataFrame([{"open_time": i * H4, "open": o, "high": h, "low": lo, "close": c}
                         for i, (o, h, lo, c) in enumerate(rows)])


class Script:
    def __init__(self, entries, trail=None, exits=()):
        self.entries, self.trail, self.exits = entries, trail or {}, set(exits)
        self.seen_lengths = []

    def entry_signal(self, b, i):
        self.seen_lengths.append(len(b))
        return self.entries.get(i)

    def exit_signal(self, b, i, pos):
        return i in self.exits

    def trailing_stop(self, b, i, pos):
        return self.trail.get(i)


S, F = 0.001, 0.001


def test_tc_ml_018_d_entry_at_next_open_with_costs():
    b = bars([(100, 101, 99, 100), (102, 103, 101, 102), (102, 103, 101, 102)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)})).trades[0]
    assert t.entry_time == H4 and t.entry_price == pytest.approx(102 * (1 + S))
    assert t.exit_reason == "END_OF_DATA"


def test_tc_ml_018_a_stop_filled_at_stop_and_qa3_12_slippage_separated():
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (99, 100, 94, 96)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)})).trades[0]
    entry = 100 * (1 + S)
    exitp = 95 * (1 - S)
    risk = entry - 95
    assert t.exit_reason == "STOP" and t.exit_price == pytest.approx(exitp)
    assert t.gross_r == pytest.approx((95 - 100) / risk)                       # sin fricciones
    assert t.slippage_r == pytest.approx(((entry - 100) + (95 - exitp)) / risk)
    assert t.commission_r == pytest.approx(F * (entry + exitp) / risk)
    assert t.net_r == pytest.approx((exitp - entry - F * (entry + exitp)) / risk)


def test_tc_ml_018_b_gap_below_stop_filled_at_open():
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (90, 92, 88, 91)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)})).trades[0]
    assert t.exit_reason == "STOP_GAP" and t.exit_price == pytest.approx(90 * (1 - S))


def test_tc_ml_018_c_stop_and_tp_same_candle_assumes_stop_first():
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (100, 120, 90, 110)])
    assert run_backtest(b, Script({0: EntrySignal(95.0, take_profit=115.0)})).trades[0].exit_reason == "STOP"


def test_take_profit_and_tp_gap():
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (101, 116, 100, 112)])
    assert run_backtest(b, Script({0: EntrySignal(95.0, 115.0)})).trades[0].exit_price == pytest.approx(115 * (1 - S))
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (118, 120, 117, 119)])
    t = run_backtest(b, Script({0: EntrySignal(95.0, 115.0)})).trades[0]
    assert t.exit_reason == "TAKE_PROFIT_GAP" and t.exit_price == pytest.approx(118 * (1 - S))


@pytest.mark.parametrize("sig", [EntrySignal(float("nan")), EntrySignal(101.0), EntrySignal(-1.0),
                                 EntrySignal(95.0, take_profit=90.0), EntrySignal(95.0, take_profit=float("inf"))])
def test_qa3_12_invalid_signals_are_rejected(sig):
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)])
    r = run_backtest(b, Script({0: sig}))
    assert r.trades == [] and r.invalid_signals == 1


def test_qa3_11_strategy_only_sees_past_and_future_perturbation_is_irrelevant():
    rows = [(100, 101, 99, 100), (100, 101, 99, 100), (101, 103, 100, 102), (102, 104, 101, 103), (103, 104, 98, 99)]

    class Cheater(Script):
        def entry_signal(self, b, i):
            super().entry_signal(b, i)
            nxt = b.iloc[i + 1] if i + 1 < len(b) else None   # intento de mirar el futuro
            return EntrySignal(95.0) if nxt is not None and nxt["close"] > 101 else None

    c = Cheater({})
    assert run_backtest(bars(rows), c).trades == []
    assert c.seen_lengths == [1, 2, 3, 4, 5]
    # Cambiar el futuro no cambia las decisiones pasadas
    r1 = run_backtest(bars(rows), Script({1: EntrySignal(95.0)}))
    rows2 = rows[:3] + [(102, 104, 101, 103), (103, 200, 98, 150)]
    r2 = run_backtest(bars(rows2), Script({1: EntrySignal(95.0)}))
    assert r1.trades[0].entry_time == r2.trades[0].entry_time == 2 * H4


def test_nan_candles_skip_signals_and_fills():
    b = bars([(100, 101, 99, 100), (np.nan,) * 4, (100, 101, 99, 100)])
    r = run_backtest(b, Script({0: EntrySignal(95.0)}))
    assert r.trades == [] and r.skipped_signals == 1
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (np.nan,) * 4, (93, 94, 92, 93)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)})).trades[0]
    assert t.exit_reason == "STOP_GAP" and t.exit_time == 3 * H4


def test_trailing_stop_only_rises_inv_009():
    b = bars([(100, 101, 99, 100), (100, 105, 99, 104), (104, 108, 103, 107), (107, 107, 97, 98)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)}, trail={1: 90.0, 2: 99.0})).trades[0]
    assert t.exit_reason == "STOP" and t.exit_price == pytest.approx(99 * (1 - S)) and t.initial_stop == 95.0


def test_exit_signal_at_next_open():
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (101, 102, 100, 101), (103, 104, 102, 103)])
    t = run_backtest(b, Script({0: EntrySignal(95.0)}, exits={2})).trades[0]
    assert t.exit_reason == "EXIT_SIGNAL" and t.exit_time == 3 * H4 and t.exit_price == pytest.approx(103 * (1 - S))


def test_execution_model_floors_and_summary_separates_gross_costs_net():
    with pytest.raises(ValueError):
        ExecutionModel(commission_rate=0.0005)
    with pytest.raises(ValueError):
        ExecutionModel(slippage=0.0)
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (99, 100, 94, 96)])
    s = run_backtest(b, Script({0: EntrySignal(95.0)})).summary()
    assert s["costs_r"] == pytest.approx(s["slippage_r"] + s["commission_r"]) and s["slippage_r"] > 0
    assert s["net_r"] == pytest.approx(s["gross_r"] - s["costs_r"])
    with pytest.raises(ValueError):
        run_backtest(b, Script({0: EntrySignal(95.0)})).equity_curve(0.02)


# --- QA3R2-06: dominio de comisión y slippage en ExecutionModel ----------------------------
# Regresiones: valores que c3f526c ACEPTABA (NaN e inf hacen que la comparación con el mínimo
# sea falsa; True vale 1; ≥ 1.0 da precios de ejecución ≤ 0; Decimal se comparaba pero
# fallaba después en el cálculo).
COST_FIELDS = ("commission_rate", "slippage")
QA3R2_06_REGRESSIONS = [
    float("nan"), np.float64("nan"), float("inf"), np.float64("inf"), True, np.bool_(True),
    1.0, 1, 1.5, np.float64(1.0), 10**400, __import__("decimal").Decimal("0.002"),
]
# Ya rechazados con ValueError en c3f526c (comportamiento existente; controles).
QA3R2_06_ALREADY_REJECTED = [float("-inf"), False, 0.0, 0.0005, -1.0, float(np.nextafter(0.001, 0))]
# En c3f526c fallaban con TypeError; ahora ValueError (normalización del tipo de excepción).
QA3R2_06_TYPE_NORMALIZED = [None, "0.002", complex(0.002, 0), [0.002]]
# Límites y entradas válidas: deben seguir aceptándose.
def _qa3r2_06_id(v):
    r = repr(v)
    return r if len(r) <= 24 else f"{type(v).__name__}({r[:8]}…)"


QA3R2_06_VALID = [0.001, float(np.nextafter(1.0, 0)), 0.0015, 0.002, 0.005, 0.01, 0.5,
                  np.float64(0.002), np.float32(0.002), __import__("fractions").Fraction(1, 500)]


@pytest.mark.parametrize("field_name", COST_FIELDS)
@pytest.mark.parametrize("value", QA3R2_06_REGRESSIONS, ids=_qa3r2_06_id)
def test_qa3r2_06_regression_invalid_cost_rejected(field_name, value):
    with pytest.raises(ValueError):
        ExecutionModel(**{field_name: value})


@pytest.mark.parametrize("field_name", COST_FIELDS)
@pytest.mark.parametrize("value", QA3R2_06_ALREADY_REJECTED, ids=_qa3r2_06_id)
def test_qa3r2_06_existing_rejection_preserved(field_name, value):
    with pytest.raises(ValueError):
        ExecutionModel(**{field_name: value})


@pytest.mark.parametrize("field_name", COST_FIELDS)
@pytest.mark.parametrize("value", QA3R2_06_TYPE_NORMALIZED, ids=_qa3r2_06_id)
def test_qa3r2_06_non_numeric_normalized_to_value_error(field_name, value):
    with pytest.raises(ValueError):
        ExecutionModel(**{field_name: value})


@pytest.mark.parametrize("field_name", COST_FIELDS)
@pytest.mark.parametrize("value", QA3R2_06_VALID, ids=_qa3r2_06_id)
def test_qa3r2_06_valid_and_boundary_costs_accepted(field_name, value):
    m = ExecutionModel(**{field_name: value})
    assert getattr(m, field_name) == value


def test_qa3r2_06_slippage_robustness_scenarios_preserved():
    """Escenarios de robustez de slippage (REQ-G-107) por encima del mínimo siguen permitidos
    y producen resultados finitos y monótonos."""
    b = bars([(100, 101, 99, 100), (100, 101, 99, 100), (99, 100, 94, 96)])
    sums = [run_backtest(b, Script({0: EntrySignal(95.0)}), ExecutionModel(commission_rate=c, slippage=s)).summary()
            for c, s in ((0.001, 0.001), (0.001, 0.002), (0.001, 0.005), (0.002, 0.005))]
    for s in sums:
        assert s["trades"] == 1 and all(math.isfinite(s[k]) for k in ("gross_r", "slippage_r", "commission_r", "net_r"))
    assert sums[0]["slippage_r"] < sums[1]["slippage_r"] < sums[2]["slippage_r"]
    assert sums[0]["net_r"] > sums[1]["net_r"] > sums[2]["net_r"] > sums[3]["net_r"]


# --- Evaluador de aceptación (TC-ML-004..006, QA3-05, QA3-07) -----------------------------

class FakeReg:
    def __init__(self, n):
        self.n = n

    def trials_count(self):
        return self.n


def evidence(net=None, risk=0.01, **kw):
    """Evidencia coherente (QA3R2-01): equity y retornos derivados de `net` (riesgo `risk` por R)."""
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


def test_tc_ml_004_small_sample_is_inconclusive():
    v = A.evaluate(evidence(trades={"train_val": 99, "oos": 40, "lockbox": 35}), FakeReg(3))
    assert v.outcome == "INCONCLUSIVE" and "train_val" in v.reasons[0]
    v = A.evaluate(evidence(trades={"train_val": 120, "oos": 40, "lockbox": 29}), FakeReg(3))
    assert v.outcome == "INCONCLUSIVE" and "lockbox" in v.reasons[0]


def _rejects(ev, fragment, trials=3):
    v = A.evaluate(ev, FakeReg(trials))
    assert v.outcome == "REJECTED" and any(fragment in r for r in v.reasons), v.reasons


def test_tc_ml_005_threshold_failures_reject_with_reason():
    # Evidencia coherente (QA3R2-01): equity y retornos derivados de la serie de trades.
    dd_net = list(np.random.default_rng(3).normal(0.6, 1.0, 40))
    dd_net[10:16] = [-1.0] * 6
    _rejects(evidence(dd_net, risk=0.05), "drawdown")              # 6 pérdidas de 5% → DD > 20%
    _rejects(evidence([1.0] * 10 + [-1.0] * 30), "Profit Factor")
    _rejects(evidence([0.05] * 20 + [-0.02] * 20), "expectancy")
    _rejects(evidence([0.01, -0.01] * 20), "Sharpe OOS")


def test_tc_ml_006_statistics_required_and_never_approved():
    assert A.evaluate(evidence(), FakeReg(3)).outcome == "ELIGIBLE_FOR_HUMAN_REVIEW"
    _rejects(evidence(baseline_beaten=False), "línea base")
    _rejects(evidence(), "Deflated Sharpe", trials=10_000)   # QA3-07: más pruebas del registro → rechazo
    with pytest.raises(ValueError, match="comprar y mantener"):
        A.evaluate(evidence(buy_and_hold_report={}), FakeReg(3))
    with pytest.raises(ValueError, match="preregistro"):
        A.evaluate(evidence(dsr_min_probability=0), FakeReg(3))


@pytest.mark.parametrize("kw", [
    dict(oos_equity=[1.0, float("nan"), 1.1]), dict(oos_period_returns=[0.01, float("nan")] * 20),
    dict(oos_net_r=[0.5] * 39 + [float("nan")]), dict(periods_per_year=float("inf")),
    dict(sr_variance_across_trials=float("nan")), dict(oos_equity=[])])
def test_qa3_05_non_finite_inputs_fail_closed(kw):
    v = A.evaluate(evidence(**kw), FakeReg(3))
    assert v.outcome == "INCONCLUSIVE" and "Fail-Closed" in v.reasons[0]


_GOOD = evidence()


@pytest.mark.parametrize("case, kw", [
    # Reproducciones de la ronda 2: equity a cero, negativa y de 1 punto con 40 trades.
    ("equity_cero", dict(oos_equity=[0.0] + _GOOD.oos_equity[1:])),
    ("equity_negativa", dict(oos_equity=[-x for x in _GOOD.oos_equity])),
    ("equity_un_punto", dict(oos_equity=[1.0])),
    # Equity y retornos independientes de oos_net_r.
    ("equity_longitud", dict(oos_equity=_GOOD.oos_equity[:-1])),
    ("equity_signo_invertido", dict(oos_equity=[1.0] + [2.0 - x for x in _GOOD.oos_equity[1:]])),
    ("retornos_de_otra_curva", dict(oos_period_returns=[0.02] * 40)),
    ("retorno_menor_que_menos_uno", dict(oos_period_returns=[-1.5] + _GOOD.oos_period_returns[1:])),
    # Parámetros del bootstrap: antes, excepción en vez de INCONCLUSIVE.
    ("n_resamples_cero", dict(bootstrap={"n_resamples": 0, "seed": 7, "block_size": 1})),
    ("n_resamples_float", dict(bootstrap={"n_resamples": 2000.0, "seed": 7, "block_size": 1})),
    ("block_size_cero", dict(bootstrap={"n_resamples": 2000, "seed": 7, "block_size": 0})),
    ("seed_negativa", dict(bootstrap={"n_resamples": 2000, "seed": -1, "block_size": 1})),
    ("n_resamples_enorme", dict(bootstrap={"n_resamples": 10 ** 30, "seed": 7, "block_size": 1})),
    ("trades_entero_enorme", dict(trades={"train_val": 10 ** 400, "oos": 40, "lockbox": 35})),
    ("trades_float", dict(trades={"train_val": 120.0, "oos": 40, "lockbox": 35})),
])
def test_qa3r2_01_invalid_or_incoherent_inputs_never_eligible(case, kw):
    v = A.evaluate(evidence(**kw), FakeReg(3))
    assert v.outcome == "INCONCLUSIVE", (case, v)
    assert "Fail-Closed" in v.reasons[0], (case, v.reasons)


def test_qa3r2_01_valid_coherent_evidence_still_eligible():
    # Control: la evidencia coherente por defecto sigue siendo ELIGIBLE (sin falsos rechazos).
    assert A.evaluate(evidence(), FakeReg(3)).outcome == "ELIGIBLE_FOR_HUMAN_REVIEW"


def test_qa3_07_declared_oos_count_must_match_series():
    with pytest.raises(ValueError, match="QA3-07"):
        A.evaluate(evidence(trades={"train_val": 120, "oos": 500, "lockbox": 35}), FakeReg(3))


def test_metric_helpers():
    assert A.profit_factor([2, -1, 1, -1]) == pytest.approx(1.5)
    assert A.max_drawdown([1, 1.2, 0.9, 1.3]) == pytest.approx(0.25)
    lo, hi = A.bootstrap_ci_mean([1.0] * 10 + [2.0] * 10, n_resamples=500, seed=1)
    assert 1.0 <= lo <= 1.5 <= hi <= 2.0
    assert A.bootstrap_ci_mean([1.0, 2.0, 3.0], n_resamples=100, seed=4) == \
        A.bootstrap_ci_mean([1.0, 2.0, 3.0], n_resamples=100, seed=4)
    assert A.deflated_sharpe_probability(0.2, 200, 50, 0.01) < A.deflated_sharpe_probability(0.2, 200, 2, 0.01)
    assert A.sharpe([0.01, 0.02, -0.01, 0.015], 365) > 0
