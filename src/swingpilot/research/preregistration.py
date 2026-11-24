"""Preregistro, histórico mínimo y diseño Walk-Forward (FEAT-017; REQ-G-103, REQ-G-106, REQ-G-109;
DEC-005 P15/P16; DEC-011; TC-ML-011, TC-ML-013, TC-ML-014).

El preregistro se congela con un SHA-256 de su JSON canónico antes de cualquier evaluación
confirmatoria. Un cambio posterior en un campo congelado queda como desviación; si ocurre tras
ver resultados OOS en un campo de diseño, el experimento deja de ser confirmatorio.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from .experiments import REGISTRY_ORIGIN, ExperimentRegistry, valid_experiment_id
from .snapshot import SEALED

# Campos obligatorios (REQ-G-103 + CR-011 + REQ-G-109)
REQUIRED_FIELDS = (
    "experiment_id", "research_question", "hypothesis", "null_hypothesis", "justification",
    "universe", "timeframes", "period", "variables", "entry_rules", "exit_rules", "model_config",
    "data_split", "metrics", "costs", "acceptance_criteria", "rejection_criteria", "limitations",
    "wf_design", "label_horizon_months", "snapshot", "observed_trade_rate_per_month",
    "trade_rate_source", "execution_model", "regime_declaration", "sharpe_definition",
    "antecedents", "trials_count", "min_history", "statistical_tests",
)
WF_KEYS = ("train_months", "embargo_months", "test_months", "step_months", "roll_frequency", "n_windows")
# Campos cuyo cambio tras ver OOS invalida el carácter confirmatorio (CR-011, REQ-G-109)
DESIGN_FIELDS = ("wf_design", "label_horizon_months", "execution_model", "acceptance_criteria",
                 "rejection_criteria", "metrics", "costs", "entry_rules", "exit_rules", "data_split")
# DEC-005 / DEC-011 / REQ-G-106
CONTRACT_WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6}
MIN_WF_WINDOWS = 2
MIN_TRADES_TRAIN_VAL, MIN_TRADES_OOS, MIN_TRADES_LOCKBOX = 100, 30, 30
FRAC_TRAIN_VAL, FRAC_OOS = 0.70, 0.15


class PreregistrationError(ValueError):
    pass


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def wf_region_months(wf: dict) -> float:
    """Meses de la región WF: entrenamiento + embargo + prueba + (n-1) pasos (REQ-G-106)."""
    return wf["train_months"] + wf["embargo_months"] + wf["test_months"] + (wf["n_windows"] - 1) * wf["step_months"]


def min_history_months(trade_rate_per_month: float, wf: dict) -> float:
    """H_min = max(WF/0.70; 100/(0.70·r); 30/(0.15·r)) — REQ-G-106 (indicativo) y REQ-G-103."""
    if trade_rate_per_month <= 0:
        raise PreregistrationError("la tasa de trades debe ser > 0")
    r = trade_rate_per_month
    return max(wf_region_months(wf) / FRAC_TRAIN_VAL, MIN_TRADES_TRAIN_VAL / (FRAC_TRAIN_VAL * r),
               max(MIN_TRADES_OOS, MIN_TRADES_LOCKBOX) / (FRAC_OOS * r))


def check_min_history(trade_rate_per_month: float, rate_source: str, available_months: float, wf: dict) -> dict:
    """TC-ML-014: la tasa debe venir solo de Train; si no alcanza, queda en DESIGN con la limitación."""
    if rate_source != "train_only":
        raise PreregistrationError("la tasa de trades del piloto debe estimarse solo con Train")
    need = min_history_months(trade_rate_per_month, wf)
    ok = available_months >= need
    return {"required_months": round(need, 2), "available_months": round(available_months, 2), "ok": ok,
            "limitation": None if ok else
            "histórico insuficiente para 2 ventanas WF + OOS + LOCKBOX: el experimento no pasa de DESIGN; "
            "el ajuste lo decide el propietario"}


def validate_wf_design(wf: dict, label_horizon_months: float) -> None:
    """TC-ML-011: 24 → 2 → 6, paso 6, ≥ 2 ventanas, embargo ≥ horizonte de etiquetas."""
    missing = [k for k in WF_KEYS if k not in wf]
    if missing:
        raise PreregistrationError(f"diseño WF incompleto: {missing}")
    for k, v in CONTRACT_WF.items():
        if wf[k] != v:
            raise PreregistrationError(f"{k}={wf[k]} distinto del contrato ({v})")
    if wf["n_windows"] < MIN_WF_WINDOWS:
        raise PreregistrationError(f"se exigen ≥ {MIN_WF_WINDOWS} ventanas de prueba")
    if label_horizon_months > wf["embargo_months"]:
        raise PreregistrationError("el embargo debe ser ≥ el horizonte máximo de las etiquetas")


@dataclass
class WFWindow:
    index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp      # exclusivo
    test_start: pd.Timestamp     # = train_end + embargo
    test_end: pd.Timestamp       # exclusivo


def walk_forward_windows(train_val_start: pd.Timestamp, train_val_end: pd.Timestamp, wf: dict) -> list[WFWindow]:
    """Ventanas dentro de Train+Val (DEC-011): ninguna prueba pasa de train_val_end."""
    off = pd.DateOffset
    out = []
    for k in range(wf["n_windows"]):
        ts = train_val_start + off(months=k * wf["step_months"])
        te = ts + off(months=wf["train_months"])
        ps = te + off(months=wf["embargo_months"])
        pe = ps + off(months=wf["test_months"])
        if pe > train_val_end:
            raise PreregistrationError(f"la ventana {k + 1} termina después de Train+Val ({pe} > {train_val_end})")
        out.append(WFWindow(k + 1, ts, te, ps, pe))
    return out


@dataclass
class FrozenPreregistration:
    content: dict
    sha256: str
    frozen_at_utc: str
    deviations: list[dict] = field(default_factory=list)

    @property
    def experiment_id(self) -> str:
        return self.content["experiment_id"]

    @property
    def confirmatory(self) -> bool:
        return not any(d["after_oos"] and d["field"] in DESIGN_FIELDS for d in self.deviations)

    def verify(self) -> None:
        if hashlib.sha256(canonical_json(self.content).encode()).hexdigest() != self.sha256:
            raise PreregistrationError("el contenido congelado fue alterado")

    def oos_seen(self, registry, access_history: list[dict] | None = None) -> bool:
        """Exposición a OOS/LOCKBOX de este experimento (QA3-13, QA3R2-07; REQ-G-103).

        - Fuente de verdad: los registros PARTITION_CONSUMED del registro de experimentos para
          este experimento, en cualquier snapshot. El consumo se anota antes de leer, así que
          cuenta aunque la lectura fallara.
        - Autorización ≠ consumo: estar en OOS_EVALUATION (o después) sin consumo registrado
          no es exposición.
        - El registro de accesos opcional solo puede AÑADIR evidencia de exposición; nunca
          anula el consumo registrado.
        - Fail-Closed: sin registro válido, experimento no nativo o no registrado, registro
          ilegible, corrupto o incoherente → PreregistrationError (nunca «no visto» por defecto).
        """
        consumed = _registry_exposure(registry, self.experiment_id)
        return consumed or _access_log_exposure(access_history, self.experiment_id)

    def record_deviation(self, field_name: str, new_value, justification: str, *,
                         registry, access_history: list[dict] | None = None) -> dict:
        """El contenido congelado no cambia: la desviación se documenta aparte (REQ-G-103)."""
        if field_name not in self.content:
            raise PreregistrationError(f"campo desconocido: {field_name}")
        if not justification.strip():
            raise PreregistrationError("toda desviación debe justificarse")
        d = {"field": field_name, "old": self.content[field_name], "new": new_value,
             "after_oos": self.oos_seen(registry, access_history), "justification": justification,
             "at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        self.deviations.append(d)
        return d


def _registry_exposure(registry, experiment_id) -> bool:
    """Consumo de OOS/LOCKBOX según el registro de experimentos (QA3R2-07). Fail-Closed."""
    if not isinstance(registry, ExperimentRegistry):
        raise PreregistrationError("se requiere un ExperimentRegistry válido (QA3R2-07)")
    if not valid_experiment_id(experiment_id):
        raise PreregistrationError(f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)")
    try:
        records = registry.records()
        experiments = registry.experiments()
    except Exception as exc:   # ilegible, JSON corrupto, TRANSITION sin CREATED…
        raise PreregistrationError(f"registro de experimentos ilegible o corrupto (QA3R2-07): {exc!r}") from exc
    exp = experiments.get(experiment_id)
    if exp is None or exp.get("origin") != REGISTRY_ORIGIN:
        raise PreregistrationError(
            f"{experiment_id} no es un experimento nativo registrado (los antecedentes no cuentan) (QA3R2-07)")
    seen = False
    for r in records:
        if not isinstance(r, dict) or r.get("kind") != "PARTITION_CONSUMED":
            continue
        eid, part, sid = r.get("experiment_id"), r.get("partition"), r.get("snapshot_id")
        if not isinstance(eid, str) or part not in SEALED or not isinstance(sid, str) or not sid:
            raise PreregistrationError(f"registro PARTITION_CONSUMED incoherente (QA3R2-07): {r!r}")
        if eid == experiment_id:
            seen = True
    if seen and not any(h.get("kind") == "TRANSITION" and h.get("to") == "OOS_EVALUATION"
                        for h in exp["history"]):
        # solo se consume en OOS_EVALUATION (partitions.py): consumo sin esa transición es incoherente
        raise PreregistrationError(
            f"{experiment_id}: consumo registrado sin transición a OOS_EVALUATION (registro incoherente) (QA3R2-07)")
    return seen


def _access_log_exposure(access_history, experiment_id) -> bool:
    """Evidencia adicional del registro de accesos: solo puede añadir exposición (QA3R2-07)."""
    if access_history is None:
        return False
    if not isinstance(access_history, (list, tuple)) or not all(isinstance(r, dict) for r in access_history):
        raise PreregistrationError("registro de accesos ilegible: se espera una lista de objetos (QA3R2-07)")
    return any(bool(r.get("allowed")) and r.get("partition") in SEALED
               and r.get("experiment_id") == experiment_id for r in access_history)


def freeze(prereg: dict) -> FrozenPreregistration:
    missing = [k for k in REQUIRED_FIELDS if k not in prereg or prereg[k] in (None, "", [], {})]
    if missing:
        raise PreregistrationError(f"preregistro incompleto: {missing}")
    validate_wf_design(prereg["wf_design"], prereg["label_horizon_months"])
    if not prereg["min_history"].get("ok"):
        raise PreregistrationError("histórico mínimo no alcanzado: no se congela (queda en DESIGN)")
    if prereg["trade_rate_source"] != "train_only":
        raise PreregistrationError("la tasa de trades debe venir solo de Train")
    content = json.loads(canonical_json(prereg))
    return FrozenPreregistration(content, hashlib.sha256(canonical_json(content).encode()).hexdigest(),
                                 datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
