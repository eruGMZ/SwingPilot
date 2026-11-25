"""N-1 (reverificación independiente de CR-020; FEAT-017; CR-020 §C.3.2; CR-021 §D.3, §D.4 paso 1, §D.5).

`ExperimentRegistry.begin_configuration_evaluation` debe validar COMPLETAMENTE la DEVIATION obligatoria
que devuelve `deviation_builder` antes de escribir nada, bajo el bloqueo exclusivo existente: identidad
de la solicitud, identidad de la desviación, `field`, SHA-256 del preregistro, `informed_by`, forma y
cronología (`after_oos`). Salida inválida → `EvaluationRequestRejected` sin escribir, sin contar, sin
marcador y sin acceso a datos. La vía sancionada (`FrozenPreregistration.begin_evaluation`), los
reintentos idempotentes y el comportamiento con una DEVIATION ya existente no cambian.

Solo registros temporales y datos sintéticos (sin registro real, particiones ni decisiones reales).
"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research.experiments import (EvaluationRequestRejected, ExperimentRegistry,  # noqa: E402
                                             PersistenceUncertainError)
from swingpilot.research.partitions import PartitionAccessError  # noqa: E402
from test_qa_cr020_01 import EID, frozen, kinds, loader_for, reg  # noqa: E402,F401  (fixtures y ayudas)

ACTOR = "orquestador"


def valid_record(fz, reg, cfg="Z"):
    """Salida válida del constructor sancionado (se ejecuta fuera del bloqueo: solo lee)."""
    return fz._deviation_builder(reg, "trials_count", {"unplanned_config_id": cfg}, "exploración", [], None,
                                 ACTOR, extra={"config_id": cfg})()


def call(reg, record, cfg="Z"):
    return reg.begin_configuration_evaluation(EID, cfg, actor=ACTOR, deviation_builder=lambda: copy.deepcopy(record))


# Cada caso: (nombre, mutación del registro válido). Los cinco primeros son los reproducidos por la sonda
# `p_builder.py` de la reverificación independiente; el resto son defectos estructurales y contextuales
# adicionales de la misma clase.
PROBE = {
    "foreign_experiment_id": lambda r: r.update(experiment_id="EXP-0999"),
    "field_not_trials_count": lambda r: r.update(field="metrics"),
    "deviation_id_missing": lambda r: r.pop("deviation_id"),
    "wrong_preregistration_sha256": lambda r: r.update(preregistration_sha256="0" * 64),
    "informed_by_unverifiable": lambda r: r.update(informed_by=[{"experiment_id": "EXP-0199", "config_id": "Q"}]),
}
EXTRA = {
    "deviation_id_not_hex32": lambda r: r.update(deviation_id="xyz"),
    "deviation_id_none": lambda r: r.update(deviation_id=None),
    "sha256_malformed": lambda r: r.update(preregistration_sha256="abc"),
    "sha256_missing": lambda r: r.pop("preregistration_sha256"),
    "experiment_id_missing": lambda r: r.pop("experiment_id"),
    "config_id_other": lambda r: r.update(config_id="OTHER"),
    "config_id_missing": lambda r: r.pop("config_id"),
    "field_unknown": lambda r: r.update(field="no_existe"),
    "justification_blank": lambda r: r.update(justification="  "),
    "justification_not_str": lambda r: r.update(justification=7),
    "actor_blank": lambda r: r.update(actor=""),
    "authorizes_change_true": lambda r: r.update(authorizes_change=True),
    "after_oos_not_bool": lambda r: r.update(after_oos="no"),
    "after_oos_true_without_exposure": lambda r: r.update(after_oos=True),               # cronología
    "after_oos_false_with_exposure": lambda r: r.update(                                # cronología
        after_oos=False, access_log_evidence=[{"allowed": True, "partition": "oos", "experiment_id": EID}]),
    "access_log_evidence_not_list": lambda r: r.update(access_log_evidence="x"),
    "access_log_evidence_foreign": lambda r: r.update(
        access_log_evidence=[{"allowed": True, "partition": "oos", "experiment_id": "EXP-0999"}]),
    "required_key_missing": lambda r: r.pop("old"),
    "informed_by_absent": lambda r: r.pop("informed_by"),                                # R2: obligatorio
    "informed_by_not_list": lambda r: r.update(informed_by="x"),
    "informed_by_malformed_ref": lambda r: r.update(informed_by=["EXP-0101"]),
    "informed_by_repeated": lambda r: r.update(informed_by=[{"experiment_id": EID, "config_id": "A"}] * 2),
    "informed_by_unknown_provenance": lambda r: r.update(informed_by=[{"provenance_id": "a" * 32}]),
    "kind_other": lambda r: r.update(kind="CREATED"),
    "not_serializable": lambda r: r.update(new={"x": object()}),
    "not_serializable_nan_key": lambda r: r.update(new={(1, 2): "tuple key"}),
}
CASES = {**PROBE, **EXTRA}


def assert_rejected_clean(reg, tmp_path, before, count, exc):
    assert reg.path.read_bytes() == before                           # comportamiento primero: nada escrito
    assert reg.trials_count() == count and reg.records() is not None  # sin conteo; registro legible
    assert isinstance(exc.value, EvaluationRequestRejected)
    loader = loader_for(reg, tmp_path)
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration(EID, "Z")
    assert loader.reads == [] and loader.access_history()[-1]["allowed"] is False


@pytest.mark.parametrize("name", list(CASES))
def test_invalid_builder_output_is_rejected_before_any_write(reg, tmp_path, name):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)                             # par planificado previo (referencia válida)
    rec = valid_record(fz, reg)
    CASES[name](rec)
    before, count = reg.path.read_bytes(), reg.trials_count()
    with pytest.raises(Exception) as exc:
        call(reg, rec)
    assert_rejected_clean(reg, tmp_path, before, count, exc)
    assert not any(k == "EVALUATION_PERSISTED" for k in kinds(reg, "Z"))   # sin marcador


@pytest.mark.parametrize("bad", [None, "texto", ["x"], 7])
def test_non_dict_builder_output_is_rejected(reg, tmp_path, bad):
    frozen(reg)
    before = reg.path.read_bytes()
    with pytest.raises(Exception) as exc:
        reg.begin_configuration_evaluation(EID, "Z", actor=ACTOR, deviation_builder=lambda: bad)
    assert_rejected_clean(reg, tmp_path, before, 0, exc)


def test_builder_that_raises_is_rejected(reg, tmp_path):
    frozen(reg)
    before = reg.path.read_bytes()

    def boom():
        raise ValueError("fallo del constructor")
    with pytest.raises(Exception) as exc:
        reg.begin_configuration_evaluation(EID, "Z", actor=ACTOR, deviation_builder=boom)
    assert_rejected_clean(reg, tmp_path, before, 0, exc)


def test_duplicate_deviation_id_of_an_existing_record_is_rejected(reg, tmp_path):
    fz = frozen(reg)
    fz.begin_evaluation("Y", registry=reg, justification="primera", informed_by=[])
    existing = [r for r in reg.records() if r["kind"] == "DEVIATION"][0]
    rec = valid_record(fz, reg)
    rec["deviation_id"] = existing["deviation_id"]
    before, count = reg.path.read_bytes(), reg.trials_count()
    with pytest.raises(Exception) as exc:
        call(reg, rec)
    assert reg.path.read_bytes() == before and reg.trials_count() == count
    assert isinstance(exc.value, EvaluationRequestRejected)
    reg.records()                                                      # el registro sigue legible (no corrupto)


# --- comportamiento conservado --------------------------------------------------------------------

def test_valid_builder_output_through_the_registry_api_is_accepted(reg, tmp_path):
    fz = frozen(reg)
    rec = valid_record(fz, reg)
    out = call(reg, rec)
    assert out["config_id"] == "Z" and reg.trials_count() == 1
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "DEVIATION", "EVALUATION_PERSISTED"]
    assert len(loader_for(reg, tmp_path).load_train_val_for_configuration(EID, "Z")) == 1


def test_valid_builder_output_with_valid_informed_by_pair_is_accepted(reg):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    rec = valid_record(fz, reg)
    rec["informed_by"] = [{"experiment_id": EID, "config_id": "A"}]
    call(reg, rec)
    assert reg.trials_count() == 2 and kinds(reg)[-1] == "EVALUATION_PERSISTED"


def test_sanctioned_caller_planned_and_unplanned_unchanged(reg, tmp_path):
    fz = frozen(reg, planned=("A", "B"))
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    assert kinds(reg, "A") == ["CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"]
    assert kinds(reg, "Z") == ["CONFIGURATION_EVALUATED", "DEVIATION", "EVALUATION_PERSISTED"]
    assert reg.trials_count() == 2
    loader = loader_for(reg, tmp_path)
    assert len(loader.load_train_val_for_configuration(EID, "A")) == 1
    assert len(loader.load_train_val_for_configuration(EID, "Z")) == 1


def test_idempotent_retry_does_not_call_the_builder_nor_write(reg):
    fz = frozen(reg)
    call(reg, valid_record(fz, reg))
    before = reg.path.read_bytes()
    calls = []

    def spy():
        calls.append(1)
        return {"kind": "DEVIATION", "config_id": "Z", "experiment_id": "EXP-0999"}   # inválido a propósito
    reg.begin_configuration_evaluation(EID, "Z", actor=ACTOR, deviation_builder=spy)
    assert calls == [] and reg.path.read_bytes() == before and reg.trials_count() == 1


def test_existing_deviation_without_marker_recovers_with_identical_copies_and_no_builder_call(reg, monkeypatch):
    fz = frozen(reg)
    real = ExperimentRegistry._write_lines

    def fail_marker(self, lines):
        if any(json.loads(ln)["kind"] == "EVALUATION_PERSISTED" for ln in lines):
            raise OSError("fallo simulado del marcador")
        return real(self, lines)
    monkeypatch.setattr(ExperimentRegistry, "_write_lines", fail_marker)
    with pytest.raises(PersistenceUncertainError):
        call(reg, valid_record(fz, reg))
    monkeypatch.undo()
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "DEVIATION"] and reg.trials_count() == 1
    calls = []

    def spy():
        calls.append(1)
        return None
    reg.begin_configuration_evaluation(EID, "Z", actor=ACTOR, deviation_builder=spy)
    assert calls == [] and reg.trials_count() == 1
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "DEVIATION", "CONFIGURATION_EVALUATED", "DEVIATION",
                          "EVALUATION_PERSISTED"]
    raw = reg.path.read_bytes().split(b"\n")[:-1]
    ce = [ln for ln in raw if json.loads(ln)["kind"] == "CONFIGURATION_EVALUATED"]
    dv = [ln for ln in raw if json.loads(ln)["kind"] == "DEVIATION"]
    assert len(set(ce)) == 1 and len(set(dv)) == 1                      # copias byte a byte idénticas


def test_rejection_then_valid_retry_succeeds_once(reg):
    fz = frozen(reg)
    bad = valid_record(fz, reg)
    bad["preregistration_sha256"] = "0" * 64
    before = reg.path.read_bytes()
    with pytest.raises(EvaluationRequestRejected):
        call(reg, bad)
    assert reg.path.read_bytes() == before
    call(reg, valid_record(fz, reg))
    assert reg.trials_count() == 1 and kinds(reg).count("DEVIATION") == 1
