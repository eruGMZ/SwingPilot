"""FEAT-019 — TC-ML-008, TC-ML-009; REQ-G-092, REQ-G-P21..P23; DEC-017 Q44 (solo infraestructura).
Incluye las pruebas de QA3-03, QA3-14 y QA3-18.

Los «modelos» aquí son registros de prueba: no hay entrenamiento (DEC-018).
"""
import ast
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest
from historical_approval import legacy_promotion_check, seed_historical_approval  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.ml import ModelRegistry, ModelRegistryError, model_hash, psi  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "src" / "swingpilot"
D, C = "d" * 64, "c" * 64


@pytest.fixture
def env(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-901_ok.md").write_text("Decisiones de prueba\n" + "".join(f"AUTORIZA: {e} {s}\n" for e in ("EXP-0201", "EXP-0202") for s in ("OOS_EVALUATION", "APPROVED")))
    exps = ExperimentRegistry(tmp_path / "registry.jsonl", dec)
    reg = ModelRegistry(tmp_path / "models.db", exps)
    yield reg, exps
    reg.close()


def legacy_freeze_check():
    """Solo pruebas heredadas (CR-020/CR-021): congelación sin las comprobaciones de ET-1, construida
    deliberadamente con la credencial privada (B3-01: el registro ya no acepta un invocable arbitrario)."""
    from swingpilot.research.experiments import _FREEZE_CHECK_KEY, FreezeCheck
    return FreezeCheck(_FREEZE_CHECK_KEY, lambda records, experiment_id, evidence: None)


def approve(exps, eid):
    exps.create(eid, "x", actor="orquestador")
    for to, ev in [("DESIGN", {}), ("PREREGISTERED", None),
                   ("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})]:
        exps.transition(eid, to, actor="orquestador", evidence=_cr020_freeze_ev(exps, eid) if ev is None else ev,
                        **({"freeze_check": legacy_freeze_check()} if to == "PREREGISTERED" else {}))  # CR-023 ET-1
    exps.transition(eid, "OOS_EVALUATION", actor="propietario", evidence=_cr020_oos_ev(exps, eid, "DEC-901_ok.md"))
    exps.transition(eid, "AUDIT", actor="orquestador")
    exps.transition(eid, "HUMAN_REVIEW", actor="orquestador")
    seed_historical_approval(exps, eid, "DEC-901_ok.md")   # B8.2: histórico sembrado


def reg_model(reg, mid="M1", ver="1.0.0", eid="EXP-0203", data=D, code=C):
    return reg.register(mid, ver, data_hash=data, code_hash=code, params={"depth": 3}, experiment_id=eid)


def active(reg, exps):
    approve(exps, "EXP-0201")
    reg_model(reg, "M2", "1.0.0", "EXP-0201")
    reg.promote("M2", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))


def test_identity_and_hash_of_data_code_params(env):
    reg, exps = env
    exps.create("EXP-0203", "x", actor="orquestador")
    h = reg_model(reg)
    assert h == model_hash(D, C, {"depth": 3}) != model_hash(D, C, {"depth": 4})
    with pytest.raises(ModelRegistryError, match="no se reutiliza"):
        reg_model(reg)
    with pytest.raises(ModelRegistryError, match="no registrado"):
        reg_model(reg, ver="2.0.0", eid="EXP-0404")
    with pytest.raises(sqlite3.DatabaseError):
        reg._db.execute("UPDATE models SET params_json='{}'")
    with pytest.raises(sqlite3.DatabaseError):
        reg._db.execute("DELETE FROM model_events")


@pytest.mark.parametrize("data,code", [("abc", C), (D, "C" * 64), (D, ""), (D, "g" * 64)])
def test_qa3_18_hashes_must_be_sha256(env, data, code):
    reg, exps = env
    exps.create("EXP-0203", "x", actor="orquestador")
    with pytest.raises(ModelRegistryError, match="SHA-256"):
        reg_model(reg, data=data, code=code)


def test_tc_ml_009_promotion_only_after_human_review_approved(env):
    reg, exps = env
    exps.create("EXP-0203", "x", actor="orquestador")
    reg_model(reg)
    with pytest.raises(ModelRegistryError, match="APPROVED"):
        reg.promote("M1", "1.0.0", requested_by="orquestador")
    assert reg.active_model() is None and reg.state("M1", "1.0.0") == "REGISTERED"
    assert [e[2] for e in reg.events("M1")] == ["REGISTERED", "PROMOTION_REJECTED"]
    active(reg, exps)
    am = reg.active_model()
    assert am["model_id"] == "M2" and am["model_hash"] == model_hash(D, C, {"depth": 3})
    approve(exps, "EXP-0202")
    reg_model(reg, "M3", "1.0.0", "EXP-0202")
    with pytest.raises(ModelRegistryError, match="ACTIVE"):
        reg.promote("M3", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))


def test_qa3_03_antecedent_cannot_back_a_model(env):
    reg, exps = env
    exps.register_antecedent("EXP-ANT", "antecedente", "REJECTED", source="s", note="n")
    with pytest.raises(ModelRegistryError, match="antecedentes"):
        reg_model(reg, eid="EXP-ANT")


def test_tc_ml_008_degradation_suspends_without_retraining(env):
    reg, exps = env
    active(reg, exps)
    ok = reg.check_degradation("M2", "1.0.0", last_trades_net_r=[0.3] * 20, ic_lower_bound_oos=0.1,
                               psi_by_feature={"f1": 0.05})
    assert not ok["suspended"] and reg.state("M2", "1.0.0") == "ACTIVE"
    few = reg.check_degradation("M2", "1.0.0", last_trades_net_r=[-1.0] * 5, ic_lower_bound_oos=0.1,
                                psi_by_feature={"f1": 0.05})
    assert few["expectancy_last20"] is None and not few["suspended"]
    bad = reg.check_degradation("M2", "1.0.0", last_trades_net_r=[0.3] * 10 + [-0.5] * 20,
                                ic_lower_bound_oos=0.1, psi_by_feature={"f1": 0.05})
    assert bad["suspended"] and reg.state("M2", "1.0.0") == "SUSPENDED" and reg.active_model() is None
    with pytest.raises(ModelRegistryError):
        reg.promote("M2", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))


@pytest.mark.parametrize("trades,ic", [([0.3] * 20, float("nan")), ([float("nan")] * 20, 0.1),
                                       ([0.3] * 19 + [float("inf")], 0.1), ([0.3] * 20, None)])
def test_qa3_14_non_finite_inputs_suspend(env, trades, ic):
    reg, exps = env
    active(reg, exps)
    d = reg.check_degradation("M2", "1.0.0", last_trades_net_r=trades, ic_lower_bound_oos=ic,
                              psi_by_feature={"f1": 0.05})
    assert d["suspended"] and reg.state("M2", "1.0.0") == "SUSPENDED"


def test_psi_trigger(env):
    reg, exps = env
    active(reg, exps)
    d = reg.check_degradation("M2", "1.0.0", last_trades_net_r=[0.3] * 20, ic_lower_bound_oos=0.1,
                              psi_by_feature={"f1": 0.05, "f2": 0.26})
    assert d["suspended"] and "f2" in d["reasons"][0]


def test_psi_values():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    assert psi(ref, rng.normal(0, 1, 5000)) < 0.05
    assert psi(ref, rng.normal(1.5, 1, 5000)) > 0.25


def test_no_training_code_in_ml_package():
    """DEC-017 Q44: sin modelo entrenado. El paquete ml/ no importa librerías de entrenamiento."""
    for py in (SRC / "ml").glob("*.py"):
        tree = ast.parse(py.read_text())
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not mods & {"sklearn", "xgboost", "torch"}, py


def _cr020_freeze_ev(exps, eid, sha="a" * 64):
    """CR-020: la congelación exige el «trials_accounting» recalculado desde el registro."""
    # CR-023 (B3): la congelación declara su clase de independencia (ET-1).
    return {"preregistration_sha256": sha, "min_history_ok": True, "independence_class": "CONFIRMATORY",
            "trials_accounting": exps.trials_accounting(eid, ["A"])}


def _cr020_oos_ev(exps, eid, ref):
    """CR-020: inicio duradero de la evaluación de «A» y registro de la selección de candidata."""
    import hashlib
    exps.begin_configuration_evaluation(eid, "A", actor="orquestador")
    inputs = ('{"experiment_id":"%s","results":{"A":{"sharpe":1.0}}}' % eid).encode()
    return {"decision_ref": ref, "selected_config_id": "A",
            "selection_inputs_sha256": hashlib.sha256(inputs).hexdigest(), "informed_by": []}
