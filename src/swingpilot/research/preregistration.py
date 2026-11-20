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

    def oos_seen(self, access_history: list[dict]) -> bool:
        """QA3-13: se deriva del registro de accesos, no de una marca manual. Cuenta cualquier
        acceso permitido a OOS o LOCKBOX de este experimento."""
        return any(r.get("allowed") and r.get("partition") in ("oos", "lockbox")
                   and r.get("experiment_id") == self.experiment_id for r in access_history)

    def record_deviation(self, field_name: str, new_value, justification: str, *,
                         access_history: list[dict]) -> dict:
        """El contenido congelado no cambia: la desviación se documenta aparte (REQ-G-103)."""
        if field_name not in self.content:
            raise PreregistrationError(f"campo desconocido: {field_name}")
        if not justification.strip():
            raise PreregistrationError("toda desviación debe justificarse")
        d = {"field": field_name, "old": self.content[field_name], "new": new_value,
             "after_oos": self.oos_seen(access_history), "justification": justification,
             "at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        self.deviations.append(d)
        return d


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
