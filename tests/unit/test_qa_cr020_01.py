"""QA-CR020-01 (FEAT-017; CR-020 §C.3.2, B.4.1, R2; REQ-G-103/104 v1.8; TC-ML-023).

Una configuración no planificada solo se registra como evaluada si su DEVIATION obligatoria es
válida; la validación ocurre ANTES de escribir `CONFIGURATION_EVALUATED`. Una solicitud rechazada no
escribe nada, no cuenta y no da acceso a datos. Si la persistencia queda a medias (evaluación
escrita, DEVIATION ausente), el historial append-only y el conteo conservador se conservan, pero el
cargador de Train+Val deniega el acceso hasta conciliar la evidencia. El reintento no duplica nada.

Solo registros temporales y datos sintéticos (sin registro real, particiones ni decisiones reales).
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research.experiments import (EvaluationRequestRejected, ExperimentError,  # noqa: E402
                                             ExperimentRegistry)
from swingpilot.research.partitions import PartitionAccessError, PartitionLoader  # noqa: E402
from swingpilot.research.preregistration import EvaluationPersistenceUncertain, freeze  # noqa: E402
from test_cr023_b3_preregistration import cr023_fields, freeze_in_registry, store_for  # noqa: E402  (CR-023)

WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}
EID = "EXP-0101"


@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def frozen(reg, planned=("A",)):
    """Experimento sintético congelado y en VALIDATION (estado que permite evaluar)."""
    reg.create(EID, "x", actor="orquestador")
    reg.transition(EID, "DESIGN", actor="orquestador")
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "model_config", "data_split",
                               "costs", "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id=EID, timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             antecedents=["-"], statistical_tests={"dsr_min_probability": 0.95},
             metrics=["sharpe"], trials_count=reg.trials_accounting(EID, list(planned)),
             candidate_selection_rule=f"PRIMARY {planned[0]}")
    p.update(cr023_fields(planned))                                # CR-023 §C.5
    fz = freeze(p)
    freeze_in_registry(reg, fz)                                    # CR-023: almacén + clase + freeze_check
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        reg.transition(EID, st, actor="orquestador", evidence=ev)
    return fz


def loader_for(reg, tmp_path):
    """Solo la puerta del cargador: `_read` sintético que anota cada lectura."""
    loader = PartitionLoader.__new__(PartitionLoader)
    loader.registry, loader.access_log = reg, tmp_path / "access.jsonl"
    loader.prereg_store = store_for(reg)                           # CR-023 §C.3.3: el cargador exige el almacén
    loader.manifest = {"snapshot_id": "SNAP-TEST", "kind": "development"}
    loader.reads = []
    loader._read = lambda part: loader.reads.append(part) or pd.DataFrame({"interval": ["1d"]})
    return loader


def kinds(reg, cfg="Z"):
    return [r["kind"] for r in reg.records() if r.get("config_id") == cfg]


# --- solicitudes inválidas: nada escrito, nada contado, sin acceso -----------------------------

@pytest.mark.parametrize("bad", [
    [{"experiment_id": "EXP-0199", "config_id": "Q"}],            # par inexistente (sonda P1)
    [{"provenance_id": "a" * 32}],                                # procedencia inexistente
    ["EXP-0101"],                                                 # referencia mal formada
    [{"experiment_id": EID}],                                     # referencia incompleta
    [{"experiment_id": EID, "config_id": "A"}] * 2,               # referencia repetida
])
def test_invalid_unplanned_request_appends_nothing_counts_nothing_grants_nothing(reg, tmp_path, bad):
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)                        # par planificado previo (referencia válida)
    before, count = reg.path.read_bytes(), reg.trials_count()
    with pytest.raises(Exception) as rejected:
        fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=bad)
    assert reg.path.read_bytes() == before and reg.trials_count() == count          # comportamiento primero
    assert isinstance(rejected.value, EvaluationRequestRejected) and "informed_by" in str(rejected.value)
    loader = loader_for(reg, tmp_path)
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration(EID, "Z")
    assert loader.reads == [] and loader.access_history()[-1]["allowed"] is False


def test_builder_returning_a_wrong_record_is_rejected_before_writing(reg):
    frozen(reg)
    before = reg.path.read_bytes()
    with pytest.raises(Exception) as rejected:
        reg.begin_configuration_evaluation(EID, "Z", actor="orquestador",
                                           deviation_builder=lambda: {"kind": "DEVIATION", "config_id": "OTHER"})
    assert reg.path.read_bytes() == before                                             # comportamiento primero
    assert isinstance(rejected.value, EvaluationRequestRejected)


# --- configuración no planificada válida --------------------------------------------------------

def test_valid_unplanned_configuration_is_recorded_with_its_deviation_and_unlocks_data(reg, tmp_path):
    fz = frozen(reg)
    fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    # CR-021 §D.3: el marcador certifica la evaluación y la DEVIATION obligatoria
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "DEVIATION", "EVALUATION_PERSISTED"] and reg.trials_count() == 1
    dev = [r for r in reg.records() if r["kind"] == "DEVIATION"][0]
    assert dev["field"] == "trials_count" and dev["preregistration_sha256"] == fz.sha256
    loader = loader_for(reg, tmp_path)
    assert len(loader.load_train_val_for_configuration(EID, "Z")) == 1 and loader.reads == ["train_val"]


def test_retry_after_success_duplicates_neither_count_nor_deviation(reg):
    fz = frozen(reg)
    fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    before = reg.path.read_bytes()
    fz.begin_evaluation("Z", registry=reg, justification="reintento", informed_by=[])
    assert reg.path.read_bytes() == before and reg.trials_count() == 1


# --- persistencia parcial -------------------------------------------------------------------------

def _fail_deviation_writes(monkeypatch):
    """Persistencia parcial: la evaluación llega al archivo y la escritura de la DEVIATION falla.
    CR-021 §D.4 escribe la evidencia con `_write_lines` (antes, `_write` por registro): se simula
    que solo llega la primera línea y la operación falla."""
    real = ExperimentRegistry._write_lines

    def write(self, lines):
        is_dev = [json.loads(ln)["kind"] == "DEVIATION" for ln in lines]
        if any(is_dev):
            real(self, [ln for ln, d in zip(lines, is_dev) if not d])
            raise OSError("fallo simulado al escribir la DEVIATION")
        return real(self, lines)
    monkeypatch.setattr(ExperimentRegistry, "_write_lines", write)


def test_partial_persistence_counts_conservatively_and_denies_data_until_reconciled(reg, tmp_path, monkeypatch):
    fz = frozen(reg)
    _fail_deviation_writes(monkeypatch)
    with pytest.raises(EvaluationPersistenceUncertain):
        fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    monkeypatch.undo()
    assert kinds(reg) == ["CONFIGURATION_EVALUATED"] and reg.trials_count() == 1      # conservador
    loader = loader_for(reg, tmp_path)
    with pytest.raises(PartitionAccessError, match="DEVIATION"):
        loader.load_train_val_for_configuration(EID, "Z")
    assert loader.reads == [] and loader.access_history()[-1]["allowed"] is False
    # reintento inválido: rechazado, nada escrito, sigue denegado
    before = reg.path.read_bytes()
    with pytest.raises(EvaluationRequestRejected):
        fz.begin_evaluation("Z", registry=reg, justification="x", informed_by=[{"experiment_id": "EXP-0199",
                                                                                 "config_id": "Q"}])
    assert reg.path.read_bytes() == before
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration(EID, "Z")
    # reintento válido: completa la DEVIATION sin duplicar la evaluación lógica; el acceso se concede.
    # CR-021 §D.4: la evaluación se reescribe como copia byte a byte idéntica y se añade el marcador.
    fz.begin_evaluation("Z", registry=reg, justification="conciliación", informed_by=[])
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "CONFIGURATION_EVALUATED", "DEVIATION",
                          "EVALUATION_PERSISTED"] and reg.trials_count() == 1
    assert len(loader.load_train_val_for_configuration(EID, "Z")) == 1


def test_malformed_deviation_does_not_unlock_unplanned_pair(reg, tmp_path, monkeypatch):
    fz = frozen(reg)
    _fail_deviation_writes(monkeypatch)
    with pytest.raises(EvaluationPersistenceUncertain):
        fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    monkeypatch.undo()
    with open(reg.path, "a") as fh:                                # edición manual: DEVIATION sin campos
        fh.write(json.dumps({"kind": "DEVIATION", "experiment_id": EID, "config_id": "Z"}) + "\n")
    loader = loader_for(reg, tmp_path)
    with pytest.raises(PartitionAccessError):
        loader.load_train_val_for_configuration(EID, "Z")
    assert loader.reads == []


# --- comportamiento planificado conservado ---------------------------------------------------------

def test_planned_configuration_behavior_is_unchanged(reg, tmp_path):
    fz = frozen(reg, planned=("A", "B"))
    fz.begin_evaluation("A", registry=reg)
    assert kinds(reg, "A") == ["CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"] and reg.trials_count() == 1  # CR-021
    assert not any(r["kind"] == "DEVIATION" for r in reg.records())
    loader = loader_for(reg, tmp_path)
    assert len(loader.load_train_val_for_configuration(EID, "A")) == 1
    with pytest.raises(EvaluationRequestRejected, match="no está planificada"):        # sin desviación
        reg.begin_configuration_evaluation(EID, "Z", actor="orquestador")
    with pytest.raises(ExperimentError):
        reg.begin_configuration_evaluation(EID, "Z", actor="orquestador", deviation_builder=lambda: None)
    assert kinds(reg) == []
