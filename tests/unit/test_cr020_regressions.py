"""CR-020 (DEC-021) — regresiones de comportamiento ejecutables también sobre la base congelada
`d372e28`: solo usan interfaces que ya existían (create, transition, register_antecedent,
trials_count, freeze, record_deviation). Con la base deben fallar por comportamiento
(aserción o «DID NOT RAISE»), no por una interfaz ausente. Registros temporales y datos sintéticos.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research.experiments import ExperimentError, ExperimentRegistry  # noqa: E402
from swingpilot.research.preregistration import PreregistrationError, freeze  # noqa: E402
from test_cr023_b3_preregistration import cr023_fields  # noqa: E402  (CR-023: campos nuevos del preregistro)

WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}


@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-900_ok.md").write_text("AUTORIZA: EXP-0101 OOS_EVALUATION\n")
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def _legacy_prereg():
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "model_config", "data_split",
                               "metrics", "costs", "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id="EXP-0101", timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             antecedents=["EXP-0001"], trials_count=3,
             statistical_tests={"dsr_min_probability": "<pre>"})
    p.update(cr023_fields(["A"]))      # CR-023: sin esto fallaría por campos ausentes y no por el conteo escalar
    return p


def test_regression_ideas_are_not_trials(reg):
    """REQ-G-P17 v1.8: experimentos en IDEA/DESIGN sin configuraciones evaluadas no cuentan."""
    reg.create("EXP-0101", "idea", actor="orquestador")
    reg.create("EXP-0102", "idea", actor="orquestador")
    assert reg.trials_count() == 0


def test_regression_antecedent_without_provenance_is_not_counted_as_one(reg):
    """CR-020 §C.3.1: sin procedencia el conteo es indeterminado, nunca 1 por identificador."""
    reg.register_antecedent("EXP-0001", "TF H4", "PENDING_DOCUMENTATION", source="s", note="n")
    with pytest.raises(ExperimentError):
        reg.trials_count()


def test_regression_freeze_without_accounting_is_rejected(reg):
    """REQ-G-103 v1.8: la congelación exige el desglose del conteo de pruebas."""
    reg.create("EXP-0101", "x", actor="orquestador")
    reg.transition("EXP-0101", "DESIGN", actor="orquestador")
    with pytest.raises(ExperimentError):
        reg.transition("EXP-0101", "PREREGISTERED", actor="orquestador",
                       evidence={"preregistration_sha256": "a" * 64, "min_history_ok": True})
    assert reg.state("EXP-0101") == "DESIGN"


def test_regression_preregistration_with_scalar_count_and_no_rule_is_rejected():
    """REQ-G-103 v1.8: `trials_count` escalar y sin `candidate_selection_rule` no se congela."""
    with pytest.raises(PreregistrationError):
        freeze(_legacy_prereg())
