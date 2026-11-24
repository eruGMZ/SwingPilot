"""Preregistro, histórico mínimo y diseño Walk-Forward (FEAT-017; REQ-G-103, REQ-G-106, REQ-G-109;
DEC-005 P15/P16; DEC-011; TC-ML-011, TC-ML-013, TC-ML-014).

El preregistro se congela con un SHA-256 de su JSON canónico antes de cualquier evaluación
confirmatoria. Un cambio posterior en un campo congelado queda como desviación; si ocurre tras
ver resultados OOS en un campo de diseño, el experimento deja de ser confirmatorio.

CR-020 (DEC-021; contrato v1.8): el preregistro declara `trials_count` con el desglose de
`trials_accounting` (H_doc, H_bound, E, planned_config_ids, planned_new, N_pre, provenance_ids) y
una `candidate_selection_rule` determinista (`PRIMARY <config_id>` o
`ARGMAX <métrica> TIEBREAK <config_id>,…`). `preregister` congela en el registro solo si el
desglose coincide con el recalculado dentro del bloqueo. `begin_evaluation` registra el inicio
duradero de la evaluación de una configuración; una configuración no planificada se registra
igualmente (cuenta) junto con su DEVIATION. Las desviaciones nuevas exigen `informed_by` (R2).
"""
import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from .experiments import (REGISTRY_ORIGIN, ExperimentError, ExperimentRegistry, PersistenceUncertainError,
                          accounting_shape_error, valid_config_id, valid_experiment_id)
from .snapshot import SEALED

# Campos obligatorios (REQ-G-103 + CR-011 + REQ-G-109)
REQUIRED_FIELDS = (
    "experiment_id", "research_question", "hypothesis", "null_hypothesis", "justification",
    "universe", "timeframes", "period", "variables", "entry_rules", "exit_rules", "model_config",
    "data_split", "metrics", "costs", "acceptance_criteria", "rejection_criteria", "limitations",
    "wf_design", "label_horizon_months", "snapshot", "observed_trade_rate_per_month",
    "trade_rate_source", "execution_model", "regime_declaration", "sharpe_definition",
    "antecedents", "trials_count", "min_history", "statistical_tests",
    "candidate_selection_rule",                                   # CR-020 §C.3.4 (R1)
)
WF_KEYS = ("train_months", "embargo_months", "test_months", "step_months", "roll_frequency", "n_windows")
# Campos cuyo cambio tras ver OOS invalida el carácter confirmatorio (CR-011, REQ-G-109)
DESIGN_FIELDS = ("wf_design", "label_horizon_months", "execution_model", "acceptance_criteria",
                 "rejection_criteria", "metrics", "costs", "entry_rules", "exit_rules", "data_split",
                 "candidate_selection_rule")                      # CR-020 §C.3.4
# DEC-005 / DEC-011 / REQ-G-106
CONTRACT_WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6}
MIN_WF_WINDOWS = 2
MIN_TRADES_TRAIN_VAL, MIN_TRADES_OOS, MIN_TRADES_LOCKBOX = 100, 30, 30
FRAC_TRAIN_VAL, FRAC_OOS = 0.70, 0.15


class PreregistrationError(ValueError):
    pass


class DeviationPersistenceUncertain(PreregistrationError):
    """La escritura de una desviación falló después de empezar (ORQ-017-01)."""


class ConfirmatoryStatusUnverifiable(PreregistrationError):
    """No consta ninguna pérdida demostrada del carácter confirmatorio, pero la evidencia no basta
    para certificarlo (QA-CR020-02; opción A del propietario). No equivale a «no confirmatorio»."""


class EvaluationPersistenceUncertain(PreregistrationError):
    """El inicio de evaluación (o su DEVIATION) no consta con certeza: la evaluación no empieza
    (CR-020 §C.3.2)."""


# --- Regla de selección de candidata (CR-020 §C.3.4, R1) --------------------------------------
_RULE_PRIMARY = re.compile(r"PRIMARY (\S+)", re.ASCII)
_RULE_ARGMAX = re.compile(r"ARGMAX ([A-Za-z0-9_.-]+) TIEBREAK (\S+)", re.ASCII)


def _declared_metrics(metrics) -> set:
    if isinstance(metrics, list):
        return {m for m in metrics if isinstance(m, str)}
    if isinstance(metrics, dict):
        return {m for m in metrics if isinstance(m, str)}
    return set()


def parse_selection_rule(rule, planned: list[str], metrics) -> dict:
    """Valida la regla con `fullmatch` contra las configuraciones planificadas y las métricas
    declaradas. Devuelve su forma normalizada; si no es válida → PreregistrationError."""
    if not isinstance(rule, str):
        raise PreregistrationError("candidate_selection_rule debe ser texto")
    m = _RULE_PRIMARY.fullmatch(rule)
    if m:
        cfg = m.group(1)
        if not valid_config_id(cfg) or cfg not in planned:
            raise PreregistrationError(f"PRIMARY cita una configuración no planificada: {cfg!r}")
        return {"form": "PRIMARY", "config_id": cfg}
    m = _RULE_ARGMAX.fullmatch(rule)
    if m:
        metric, order = m.group(1), m.group(2).split(",")
        if metric not in _declared_metrics(metrics):
            raise PreregistrationError(f"ARGMAX usa una métrica no declarada en «metrics»: {metric!r}")
        if not all(valid_config_id(c) for c in order) or len(set(order)) != len(order) \
                or sorted(order) != sorted(planned):
            raise PreregistrationError("TIEBREAK debe enumerar todas las configuraciones planificadas una sola vez")
        return {"form": "ARGMAX", "metric": metric, "tiebreak": order}
    raise PreregistrationError(f"candidate_selection_rule mal formada: {rule!r} "
                               "(formas: «PRIMARY <config_id>», «ARGMAX <métrica> TIEBREAK <config_id>,…»)")


def apply_selection_rule(parsed: dict, results: dict) -> str:
    """Aplica la regla congelada a los resultados de Train+Val {config_id: {métrica: valor}}.
    ARGMAX: mayor valor; empate → primera en TIEBREAK. Valor no numérico o no finito → error."""
    if parsed["form"] == "PRIMARY":
        return parsed["config_id"]
    best, best_val = None, None
    for cfg in parsed["tiebreak"]:
        if cfg not in results:
            continue
        val = results[cfg].get(parsed["metric"]) if isinstance(results[cfg], dict) else None
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            raise PreregistrationError(f"resultado no numérico o no finito para {cfg}: {val!r}")
        if best is None or val > best_val:
            best, best_val = cfg, val
    if best is None:
        raise PreregistrationError("sin resultados a los que aplicar la regla")
    return best


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
    """Preregistro congelado. Las desviaciones se persisten como registros DEVIATION en el
    registro de experimentos (ORQ-017-01); `deviations` es solo la vista local de las que este
    objeto escribió. El carácter confirmatorio se deriva SIEMPRE del registro."""
    content: dict
    sha256: str
    frozen_at_utc: str
    deviations: list[dict] = field(default_factory=list)
    _registry: object = field(default=None, repr=False, compare=False)
    _persistence_uncertain: str | None = field(default=None, repr=False, compare=False)

    @property
    def experiment_id(self) -> str:
        return self.content["experiment_id"]

    @property
    def confirmatory(self) -> bool:
        """Derivado del registro usado en `record_deviation` (ORQ-017-01). Sin registro o con
        una escritura incierta pendiente → PreregistrationError: nunca se certifica por defecto.
        No recibe `selection_inputs`: tras la selección de candidata, sin pérdida demostrada →
        ConfirmatoryStatusUnverifiable; use `confirmatory_status(registry, selection_inputs=…)`
        (QA-CR020-02)."""
        if self._persistence_uncertain:
            raise PreregistrationError(
                f"persistencia incierta de la desviación {self._persistence_uncertain}: reconstruya el estado "
                "desde el registro con un objeto nuevo antes de certificar nada (ORQ-017-01)")
        if self._registry is None:
            raise PreregistrationError("carácter confirmatorio no derivable: falta el registro de experimentos "
                                       "(use confirmatory_status(registry)) (ORQ-017-01)")
        return self.confirmatory_status(self._registry)["confirmatory"]

    def confirmatory_status(self, registry, *, selection_inputs: bytes | None = None) -> dict:
        """Estado reconstruido desde el registro, ligado al SHA-256 de este preregistro. Tras la
        selección de candidata exige `selection_inputs` (QA-CR020-02)."""
        if self._persistence_uncertain:
            raise PreregistrationError(
                f"persistencia incierta de la desviación {self._persistence_uncertain}: reconstruya el estado "
                "desde el registro con un objeto nuevo antes de certificar nada (ORQ-017-01)")
        self.verify()
        status = confirmatory_status(registry, self.experiment_id, preregistration=self,
                                     selection_inputs=selection_inputs)
        if status["preregistration_sha256"] != self.sha256:
            raise PreregistrationError("el SHA-256 de este preregistro no coincide con el de PREREGISTERED en el "
                                       "registro (ORQ-017-01)")
        return status

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
                         registry, informed_by: list, access_history: list[dict] | None = None,
                         actor: str = "orquestador") -> dict:
        """Documenta una desviación de forma duradera (REQ-G-103; ORQ-017-01).

        El contenido congelado no cambia. Registrar NO autoriza el cambio ni da autoridad de
        decisión (REQ-G-107). La exposición se calcula y el registro DEVIATION se escribe bajo
        el mismo bloqueo exclusivo del registro: `after_oos` refleja el orden del archivo. Si el
        registro de accesos aporta exposición, sus entradas se copian al registro DEVIATION para
        que la exposición siga siendo verificable al reconstruir.
        """
        if not isinstance(registry, ExperimentRegistry):
            raise PreregistrationError("se requiere un ExperimentRegistry válido (QA3R2-07)")
        if self._persistence_uncertain:
            raise PreregistrationError(
                f"persistencia incierta de la desviación {self._persistence_uncertain}: reconstruya el estado "
                "desde el registro antes de registrar otra (ORQ-017-01)")
        self.verify()
        if field_name not in self.content:
            raise PreregistrationError(f"campo desconocido: {field_name}")
        if not isinstance(justification, str) or not justification.strip():
            raise PreregistrationError("toda desviación debe justificarse")
        if not isinstance(actor, str) or not actor.strip():
            raise PreregistrationError("la desviación exige un actor")
        build = self._deviation_builder(registry, field_name, new_value, justification, informed_by,
                                        access_history, actor)
        try:
            rec = registry.append_deviation(build)
        except PersistenceUncertainError as exc:
            self._persistence_uncertain = build.deviation_id
            raise DeviationPersistenceUncertain(
                f"persistencia incierta de la desviación {build.deviation_id}; no se da por registrada ni por ausente "
                f"(ORQ-017-01): {exc}") from exc
        except ExperimentError as exc:
            raise PreregistrationError(str(exc)) from exc
        self._registry = registry
        self.deviations.append(rec)
        return rec

    def _deviation_builder(self, registry, field_name, new_value, justification, informed_by, access_history,
                           actor, extra: dict | None = None):
        """Constructor del registro DEVIATION, ejecutado dentro del bloqueo exclusivo (ORQ-017-01).
        `informed_by` es obligatorio en las desviaciones nuevas (R2, CR-020)."""
        if not isinstance(informed_by, list):
            raise PreregistrationError("toda desviación nueva exige «informed_by» (lista, puede estar vacía) (R2)")
        deviation_id = uuid.uuid4().hex
        eid = self.experiment_id

        def build() -> dict:   # dentro del bloqueo exclusivo del registro
            consumed = _registry_exposure(registry, eid)
            evidence = _access_log_evidence(access_history, eid)
            _replay(registry, eid)                       # valida todo lo existente (Fail-Closed)
            if _preregistered_sha(registry, eid) != self.sha256:
                raise PreregistrationError(f"{eid}: el SHA-256 del preregistro no coincide con el de PREREGISTERED "
                                           "en el registro (ORQ-017-01)")
            why = registry.informed_by_error(informed_by, registry.records())
            if why:
                raise PreregistrationError(f"informed_by no verificable (R2): {why}")
            rec = {"kind": "DEVIATION", "deviation_id": deviation_id, "experiment_id": eid,
                   "preregistration_sha256": self.sha256, "field": field_name,
                   "old": self.content[field_name], "new": new_value, "justification": justification,
                   "after_oos": bool(consumed or evidence), "access_log_evidence": evidence,
                   "actor": actor, "authorizes_change": False, "informed_by": list(informed_by), **(extra or {})}
            try:
                json.dumps(rec, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError) as exc:
                raise PreregistrationError(f"desviación no serializable: {exc!r}") from exc
            return rec
        build.deviation_id = deviation_id
        return build

    def planned_config_ids(self) -> list[str]:
        return list(self.content["trials_count"]["planned_config_ids"])

    def begin_evaluation(self, config_id: str, *, registry, actor: str = "orquestador",
                         informed_by: list | None = None, justification: str | None = None,
                         access_history: list[dict] | None = None) -> dict:
        """Inicio duradero de la evaluación de una configuración (CR-020 §C.3.2). Debe llamarse
        ANTES de evaluar. Configuración no planificada: cuenta y se registra su DEVIATION (exige
        justificación e `informed_by`); el experimento deja de ser confirmatorio (REQ-G-103 v1.8).
        Rechazo previo → EvaluationRequestRejected; escritura incierta → EvaluationPersistenceUncertain."""
        if not isinstance(registry, ExperimentRegistry):
            raise PreregistrationError("se requiere un ExperimentRegistry válido")
        self.verify()
        if _preregistered_sha(registry, self.experiment_id) != self.sha256:
            raise PreregistrationError("el SHA-256 de este preregistro no coincide con el de PREREGISTERED")
        builder = None
        if config_id not in self.planned_config_ids():
            if not isinstance(justification, str) or not justification.strip():
                raise PreregistrationError("una configuración no planificada exige justificar la desviación")
            builder = self._deviation_builder(registry, "trials_count", {"unplanned_config_id": config_id},
                                              justification, informed_by, access_history, actor,
                                              extra={"config_id": config_id})
        try:
            rec = registry.begin_configuration_evaluation(self.experiment_id, config_id, actor=actor,
                                                          deviation_builder=builder)
        except PersistenceUncertainError as exc:
            raise EvaluationPersistenceUncertain(str(exc)) from exc
        return rec


def preregister(registry, frozen: "FrozenPreregistration", *, actor: str = "orquestador") -> dict:
    """Congela en el registro (DESIGN → PREREGISTERED) con el SHA-256 y el `trials_accounting`
    declarado en el preregistro; el registro lo recalcula dentro del bloqueo y rechaza la
    transición si no coincide (CR-020 §C.3.3, TC-ML-022)."""
    if not isinstance(registry, ExperimentRegistry):
        raise PreregistrationError("se requiere un ExperimentRegistry válido")
    frozen.verify()
    c = frozen.content
    return registry.transition(frozen.experiment_id, "PREREGISTERED", actor=actor,
                               evidence={"preregistration_sha256": frozen.sha256,
                                         "min_history_ok": c["min_history"].get("ok") is True,
                                         "trials_accounting": c["trials_count"]})


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


def _access_log_evidence(access_history, experiment_id) -> list[dict]:
    """Entradas del registro de accesos que prueban exposición de este experimento (QA3R2-07)."""
    if access_history is None:
        return []
    if not isinstance(access_history, (list, tuple)) or not all(isinstance(r, dict) for r in access_history):
        raise PreregistrationError("registro de accesos ilegible: se espera una lista de objetos (QA3R2-07)")
    return [dict(r) for r in access_history if _is_exposure_entry(r, experiment_id)]


def _is_exposure_entry(r, experiment_id) -> bool:
    return isinstance(r, dict) and bool(r.get("allowed")) and r.get("partition") in SEALED \
        and r.get("experiment_id") == experiment_id


def _access_log_exposure(access_history, experiment_id) -> bool:
    """Evidencia adicional del registro de accesos: solo puede añadir exposición (QA3R2-07)."""
    return bool(_access_log_evidence(access_history, experiment_id))


# --- Persistencia de desviaciones (ORQ-017-01) ----------------------------------------------

_SHA256 = re.compile(r"[0-9a-f]{64}")
_DEVIATION_ID = re.compile(r"[0-9a-f]{32}")
_DEVIATION_KEYS = ("deviation_id", "experiment_id", "preregistration_sha256", "field", "old", "new",
                   "justification", "after_oos", "access_log_evidence", "actor", "authorizes_change")


def _read(registry):
    if not isinstance(registry, ExperimentRegistry):
        raise PreregistrationError("se requiere un ExperimentRegistry válido (QA3R2-07)")
    try:
        return registry.records(), registry.experiments()
    except Exception as exc:
        raise PreregistrationError(f"registro de experimentos ilegible o corrupto (ORQ-017-01): {exc!r}") from exc


def _preregistered_sha(registry, experiment_id) -> str:
    """SHA-256 citado en la transición a PREREGISTERED del experimento (vinculación, O4)."""
    _, experiments = _read(registry)
    exp = experiments.get(experiment_id)
    if exp is None or exp.get("origin") != REGISTRY_ORIGIN:
        raise PreregistrationError(f"{experiment_id} no es un experimento nativo registrado (ORQ-017-01)")
    shas = [(h.get("evidence") or {}).get("preregistration_sha256") for h in exp["history"]
            if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
    if len(shas) != 1 or not isinstance(shas[0], str) or not _SHA256.fullmatch(shas[0]):
        raise PreregistrationError(f"{experiment_id}: sin una transición a PREREGISTERED con un SHA-256 válido "
                                   "(ORQ-017-01)")
    return shas[0]


def _deviation_shape_error(r) -> str | None:
    if any(k not in r for k in _DEVIATION_KEYS):
        return "faltan campos"
    if not isinstance(r["deviation_id"], str) or not _DEVIATION_ID.fullmatch(r["deviation_id"]):
        return "deviation_id no válido"
    if not isinstance(r["experiment_id"], str) or not r["experiment_id"]:
        return "experiment_id no válido"
    if not isinstance(r["preregistration_sha256"], str) or not _SHA256.fullmatch(r["preregistration_sha256"]):
        return "SHA-256 no válido"
    if r["field"] not in REQUIRED_FIELDS:
        return "campo desconocido"
    if not isinstance(r["justification"], str) or not r["justification"].strip():
        return "sin justificación"
    if not isinstance(r["after_oos"], bool):
        return "after_oos no booleano"
    if not isinstance(r["actor"], str) or not r["actor"].strip():
        return "sin actor"
    if r["authorizes_change"] is not False:
        return "un registro DEVIATION no autoriza cambios"
    ev = r["access_log_evidence"]
    if not isinstance(ev, list) or not all(_is_exposure_entry(e, r["experiment_id"]) for e in ev):
        return "evidencia del registro de accesos no válida"
    if "informed_by" in r and not isinstance(r["informed_by"], list):   # R2: ausente = histórico
        return "informed_by no es una lista"
    return None


def _replay(registry, experiment_id) -> list[dict]:
    """Reconstruye y valida, en orden del archivo, las desviaciones del experimento. Las de otros
    experimentos solo se validan en forma; las del mismo experimento exigen el SHA-256 de su
    PREREGISTERED, ir después de esa transición y un `after_oos` igual al derivado (consumo
    anterior en el archivo o evidencia de accesos incluida). Fail-Closed."""
    _registry_exposure(registry, experiment_id)            # valida consumos (QA3R2-07)
    sha = _preregistered_sha(registry, experiment_id)
    records, _ = _read(registry)
    consumed = preregistered = False
    seen_ids, out = set(), []
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            raise PreregistrationError(f"registro no válido: {r!r} (ORQ-017-01)")
        kind, eid = r.get("kind"), r.get("experiment_id")
        if kind == "PARTITION_CONSUMED" and eid == experiment_id:
            consumed = True
        elif kind == "TRANSITION" and eid == experiment_id and r.get("to") == "PREREGISTERED":
            preregistered = True
        elif kind == "DEVIATION":
            if isinstance(r.get("deviation_id"), str) and r["deviation_id"] in seen_ids:
                # CR-021 §D.2 (sustituye la unicidad de ORQ-017-01): el registro ya garantiza al cargar
                # que es una copia byte a byte idéntica; es la misma desviación lógica y conserva la
                # cronología de su primera aparición, ya validada.
                continue
            why = _deviation_shape_error(r)
            if why is None and "informed_by" in r:
                ib = registry.informed_by_error(r["informed_by"], records[:i])
                why = f"informed_by no verificable: {ib}" if ib else None
            if why:
                raise PreregistrationError(f"registro DEVIATION incoherente ({why}) (ORQ-017-01): {r!r}")
            seen_ids.add(r["deviation_id"])
            if eid != experiment_id:
                continue                                   # válida y ajena: se ignora
            if r["preregistration_sha256"] != sha:
                raise PreregistrationError(f"{experiment_id}: DEVIATION con un SHA-256 distinto del de "
                                           f"PREREGISTERED (hash incoherente) (ORQ-017-01): {r['deviation_id']}")
            if not preregistered:
                raise PreregistrationError(f"{experiment_id}: DEVIATION anterior a PREREGISTERED en el registro "
                                           f"(incoherente) (ORQ-017-01): {r['deviation_id']}")
            if r["after_oos"] != (consumed or bool(r["access_log_evidence"])):
                raise PreregistrationError(f"{experiment_id}: after_oos no coincide con la cronología del registro "
                                           f"(incoherente) (ORQ-017-01): {r['deviation_id']}")
            out.append(r)
    return out


def evaluation_evidence_error(registry, experiment_id: str, config_id: str) -> str | None:
    """Evidencia obligatoria para entregar datos de un par ya registrado (QA-CR020-01; CR-020 §C.3.2;
    CR-021 §D.5, DEC-023). Exige un EVALUATION_PERSISTED válido del par (durabilidad confirmada de
    la evidencia, no la del marcador: R2). No planificada → además su DEVIATION (`field` =
    trials_count, `config_id` del par) entre las desviaciones VALIDADAS (`_replay`), certificada
    por ese marcador. Ausente, mal formada o registro corrupto o incoherente → motivo (el cargador
    deniega). Sin efectos: no escribe nada."""
    try:
        _, experiments = _read(registry)
        exp = experiments.get(experiment_id)
        if exp is None or exp.get("origin") != REGISTRY_ORIGIN:
            return f"{experiment_id} no es un experimento nativo registrado"
        pre = [h for h in exp["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
        acc = (pre[0].get("evidence") or {}).get("trials_accounting") if len(pre) == 1 else None
        if len(pre) != 1 or accounting_shape_error(acc):
            return f"{experiment_id}: sin congelación válida con «trials_accounting»"
        markers = registry.certified(experiment_id, config_id)          # validados y vinculados (CR-021)
        devs = [] if config_id in acc["planned_config_ids"] else _replay(registry, experiment_id)
    except Exception as exc:
        return f"registro o evidencia de desviaciones ilegible, corrupto o incoherente: {exc}"
    if config_id in acc["planned_config_ids"]:
        if not markers:
            return (f"sin EVALUATION_PERSISTED para {experiment_id}/{config_id}: la durabilidad de la evidencia no "
                    "está confirmada; datos denegados (CR-021 §D.5)")
        return None
    ids = {d["deviation_id"] for d in devs if d.get("config_id") == config_id and d["field"] == "trials_count"}
    if not ids:
        return (f"{config_id} no está planificada y falta su DEVIATION obligatoria; datos denegados hasta "
                "conciliar la evidencia (QA-CR020-01)")
    if not any(c["kind"] == "DEVIATION" and c["deviation_id"] in ids for m in markers for c in m["certifies"]):
        return (f"sin EVALUATION_PERSISTED que certifique la evaluación y la DEVIATION obligatoria de "
                f"{experiment_id}/{config_id}; datos denegados (CR-021 §D.5)")
    return None


def _selection_finding(records, experiment_id, x_pairs, planned, preregistration, sha, selection_inputs):
    """Selección de candidata frente a la regla congelada (CR-020 §C.3.4; QA-CR020-02). Devuelve
    (selección, violación, motivo_no_verificable). Sin selección registrada → (None, False, None).
    Misma reproducción que el evaluador (trials.py); nunca lanza: lo no verificable es un motivo."""
    sels = [r for r in records if isinstance(r, dict) and r.get("kind") == "TRANSITION"
            and r.get("experiment_id") == experiment_id and r.get("to") == "OOS_EVALUATION"]
    if not sels:
        return None, False, None
    if len(sels) != 1:
        return None, None, "más de un registro de selección de candidata"
    sev = sels[0].get("evidence") or {}
    selected, sha_in = sev.get("selected_config_id"), sev.get("selection_inputs_sha256")
    if not isinstance(selected, str) or not isinstance(sha_in, str):
        return None, None, "selección sin configuración o sin hash del archivo de resultados"
    if not isinstance(preregistration, FrozenPreregistration):
        return None, None, "falta el preregistro congelado con la regla de selección"
    try:
        preregistration.verify()
    except PreregistrationError as exc:
        return None, None, f"preregistro congelado alterado: {exc}"
    if preregistration.sha256 != sha or preregistration.experiment_id != experiment_id:
        return None, None, "el preregistro no es el vinculado a PREREGISTERED"
    if not isinstance(selection_inputs, (bytes, bytearray)) or hashlib.sha256(selection_inputs).hexdigest() != sha_in:
        return None, None, "archivo de resultados de la selección ausente o con hash distinto"
    if x_pairs is None or planned is None:
        return None, None, "pares evaluados o configuraciones planificadas no reconstruibles"
    try:
        doc = json.loads(bytes(selection_inputs).decode("utf-8"))
        results = doc["results"]
        if doc.get("experiment_id") != experiment_id or not isinstance(results, dict) or set(results) != x_pairs:
            raise ValueError("los resultados no corresponden exactamente a los pares evaluados")
        rule = parse_selection_rule(preregistration.content["candidate_selection_rule"], planned,
                                    preregistration.content.get("metrics"))
        expected = apply_selection_rule(rule, results)
    except Exception as exc:
        return None, None, f"selección no reproducible: {exc!r}"
    return {"selected_config_id": selected, "rule_config_id": expected}, expected != selected, None


def confirmatory_findings(registry, experiment_id: str, *, preregistration=None,
                          selection_inputs: bytes | None = None) -> dict:
    """Evidencia del carácter confirmatorio (REQ-G-103 v1.8/v1.9; CR-020 §C.3.2, §C.3.4, §C.4.1;
    QA-CR020-02). Causas DEMOSTRADAS de pérdida, las únicas del contrato:
    - desviación de un campo de diseño tras la exposición a OOS/LOCKBOX (REQ-G-103, CR-011);
    - desviación de `candidate_selection_rule`, en cualquier momento (CR-020 §C.3.4);
    - pares evaluados de X fuera de `planned_config_ids` congelado en PREREGISTERED, conste o no
      su DEVIATION obligatoria (C.3.2, C.4.1.4);
    - candidata seleccionada distinta de la que da la regla congelada (C.3.4, C.4.1.5).
    Lo que no puede comprobarse va a `unverified`: no es pérdida demostrada (los INCONCLUSIVE
    probatorios del evaluador no lo son) ni certifica nada. Registro ilegible, corrupto o
    incoherente → PreregistrationError (como antes). Sin efectos: no escribe nada."""
    devs = _replay(registry, experiment_id)
    sha = _preregistered_sha(registry, experiment_id)
    records, experiments = _read(registry)
    after = [d["deviation_id"] for d in devs if d["after_oos"] and d["field"] in DESIGN_FIELDS]
    rule_changes = [d["deviation_id"] for d in devs if d["field"] == "candidate_selection_rule"]
    unverified, planned, x_pairs, unplanned = [], None, None, None
    pre = [h for h in experiments[experiment_id]["history"]
           if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
    acc = (pre[0].get("evidence") or {}).get("trials_accounting")
    if accounting_shape_error(acc):
        unverified.append(f"«trials_accounting» congelado ausente o mal formado: {accounting_shape_error(acc)}")
    else:
        planned = list(acc["planned_config_ids"])
        try:
            pairs = registry.accounting(records=records, require_complete=False)["pairs"]
        except Exception as exc:
            unverified.append(f"pares evaluados no reconstruibles: {exc}")
        else:
            x_pairs = {c for (e, c) in pairs if e == experiment_id}
            unplanned = sorted(x_pairs - set(planned))
    selection, violation, why = _selection_finding(records, experiment_id, x_pairs, planned, preregistration, sha,
                                                   selection_inputs)
    if why:
        unverified.append(why)
    lost = bool(after or rule_changes or unplanned or violation)
    return {"experiment_id": experiment_id, "preregistration_sha256": sha, "confirmatory": not lost,
            "deviations": devs, "design_deviations_after_oos": after, "selection_rule_changes": rule_changes,
            "unplanned_config_ids": unplanned, "selection": selection, "selection_rule_violation": violation,
            "unverified": unverified}


def confirmatory_status(registry, experiment_id: str, *, preregistration=None,
                        selection_inputs: bytes | None = None) -> dict:
    """Carácter confirmatorio reconstruido desde el registro, consultable en HUMAN_REVIEW
    (ORQ-017-01, O2). No cambia reglas de aprobación ni transiciones. Pérdida demostrada →
    `confirmatory` = False, aunque falte otra evidencia (se informa en `unverified`). Sin pérdida
    demostrada y con evidencia no verificable → ConfirmatoryStatusUnverifiable: nunca se certifica
    por defecto (opción A del propietario, QA-CR020-02). Tras la selección de candidata, verificarlo
    exige el preregistro congelado y `selection_inputs`. Registro ilegible, corrupto o incoherente
    → PreregistrationError."""
    st = confirmatory_findings(registry, experiment_id, preregistration=preregistration,
                               selection_inputs=selection_inputs)
    if st["confirmatory"] and st["unverified"]:
        raise ConfirmatoryStatusUnverifiable(
            f"{experiment_id}: carácter confirmatorio no verificable (QA-CR020-02): {st['unverified']}; "
            "aporte el preregistro congelado y el archivo de resultados de la selección (selection_inputs)")
    return st


def freeze(prereg: dict) -> FrozenPreregistration:
    missing = [k for k in REQUIRED_FIELDS if k not in prereg or prereg[k] in (None, "", [], {})]
    if missing:
        raise PreregistrationError(f"preregistro incompleto: {missing}")
    validate_wf_design(prereg["wf_design"], prereg["label_horizon_months"])
    if not prereg["min_history"].get("ok"):
        raise PreregistrationError("histórico mínimo no alcanzado: no se congela (queda en DESIGN)")
    if prereg["trade_rate_source"] != "train_only":
        raise PreregistrationError("la tasa de trades debe venir solo de Train")
    why = accounting_shape_error(prereg["trials_count"])               # CR-020 §C.3.3
    if why:
        raise PreregistrationError(f"trials_count debe declarar el desglose de la contabilidad de pruebas: {why}")
    parse_selection_rule(prereg["candidate_selection_rule"], prereg["trials_count"]["planned_config_ids"],
                         prereg["metrics"])                           # CR-020 §C.3.4
    content = json.loads(canonical_json(prereg))
    return FrozenPreregistration(content, hashlib.sha256(canonical_json(content).encode()).hexdigest(),
                                 datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
