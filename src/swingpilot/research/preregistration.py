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

CR-023 (bloque B3): el preregistro declara además `independence_boundary` (piloto de tasa o frontera
confirmatoria; ver `boundary.py`), `conditioning_components` y la `snapshot` de desarrollo
(`snapshot_id`, `train_val_sha256`, `d_dev`). `freeze` valida todo de forma pura; `preregister` (ET-1)
verifica la snapshot de desarrollo (I2), escribe el contenido en el almacén recuperable ANTES de la
transición y pasa al registro un `FreezeCheck` que se ejecuta dentro del bloqueo (vinculación con el
experimento y la evidencia, I2, V2, ventanas anteriores, V7 mecánico, piloto de tasa). B3-01: el registro
solo acepta un `FreezeCheck` de `build_freeze_check`, nunca un invocable de quien llama. Un `DEVIATION` de `independence_boundary` se valida antes de
escribir y en cada reproducción (D.2). NO implementados aquí (bloques posteriores): `independence_status`,
la regla endurecida de cualquier `DEVIATION`, V1, V3–V6, V8 y el acceso final.
"""
import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from . import boundary as B
from .experiments import (_FREEZE_CHECK_KEY, REGISTRY_ORIGIN, ExperimentError, ExperimentRegistry, FreezeCheck,
                          PersistenceUncertainError, accounting_shape_error, valid_config_id, valid_experiment_id)
from .prereg_store import PreregistrationStore, PreregStoreError
from .snapshot import KIND_DEVELOPMENT, SEALED, SnapshotError, load_manifest, verify_snapshot

# Campos obligatorios (REQ-G-103 + CR-011 + REQ-G-109)
REQUIRED_FIELDS = (
    "experiment_id", "research_question", "hypothesis", "null_hypothesis", "justification",
    "universe", "timeframes", "period", "variables", "entry_rules", "exit_rules", "model_config",
    "data_split", "metrics", "costs", "acceptance_criteria", "rejection_criteria", "limitations",
    "wf_design", "label_horizon_months", "snapshot", "observed_trade_rate_per_month",
    "trade_rate_source", "execution_model", "regime_declaration", "sharpe_definition",
    "antecedents", "trials_count", "min_history", "statistical_tests",
    "candidate_selection_rule",                                   # CR-020 §C.3.4 (R1)
    "independence_boundary", "conditioning_components",           # CR-023 §C.5 (D.2: campo conocido)
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


def min_history_months(trade_rate_per_month: float, wf: dict | None = None) -> float:
    """H_dev,min = max(38 ; 100/r) meses (CR-023 §C.8; REQ-G-106, REQ-G-103). `wf` se conserva por
    compatibilidad de firma: los 38 meses son 24 + 2 + 6 + 6 del diseño WF contractual."""
    try:
        return B.dev_min_history_months(trade_rate_per_month)
    except B.BoundaryError as exc:
        raise PreregistrationError(str(exc)) from exc


def check_min_history(trade_rate_per_month: float, rate_source: str, available_months: float,
                      wf: dict | None = None, *, k: float | None = None) -> dict:
    """TC-ML-014: la tasa debe venir solo de Train; si no alcanza, queda en DESIGN con la limitación.
    Con `k` añade `window_min_months` = k·30/r (CR-023 §C.8)."""
    if rate_source != "train_only":
        raise PreregistrationError("la tasa de trades del piloto debe estimarse solo con Train")
    need = min_history_months(trade_rate_per_month)
    ok = available_months >= need
    out = {"required_months": round(need, 2), "available_months": round(available_months, 2), "ok": ok,
           "limitation": None if ok else
           "histórico insuficiente para el diseño WF + OOS + LOCKBOX: el experimento no pasa de DESIGN; "
           "el ajuste lo decide el propietario"}
    if k is not None:
        try:
            out["window_min_months"] = round(B.window_min_months(trade_rate_per_month, k), 2)
        except B.BoundaryError as exc:
            raise PreregistrationError(str(exc)) from exc
    return out


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

    def record_independence_deviation(self, window_ids: list, cls: str, evidence: list,
                                      exposure_started_at: str, justification: str, *, registry,
                                      informed_by: list, actor: str = "orquestador") -> dict:
        """`DEVIATION` de independencia (CR-023 §D.2): `field = "independence_boundary"` y `new` con
        exactamente `contaminated_window_ids`, `class`, `evidence` y `exposure_started_at`. Se admite
        en cualquier estado posterior a PREREGISTERED, también terminal (sin puerta de estado). Se
        valida antes de escribir (forma, ventanas calculadas desde el valor congelado `old`); un
        piloto de tasa, que no reserva ventanas, se rechaza. Append-only: no se retira ni corrige."""
        new = {"contaminated_window_ids": list(window_ids) if isinstance(window_ids, (list, tuple)) else window_ids,
               "class": cls, "evidence": list(evidence) if isinstance(evidence, (list, tuple)) else evidence,
               "exposure_started_at": exposure_started_at}
        return self.record_deviation("independence_boundary", new, justification, registry=registry,
                                     informed_by=informed_by, actor=actor)

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
            if field_name == "independence_boundary":     # D.2: validación previa a la escritura (como N-1)
                why_shape = _deviation_shape_error(rec)
                if why_shape:
                    raise PreregistrationError(f"desviación de independencia no válida ({why_shape}); "
                                               "nada escrito (CR-023 D.2)")
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


def _manifest_binding_error(content: dict, manifest: dict) -> str | None:
    """La snapshot declarada en el preregistro debe ser la verificada (I2): id, SHA-256 de `train_val`
    y `d_dev`. None = coincide."""
    snap = content["snapshot"]
    if manifest.get("kind") != KIND_DEVELOPMENT:
        return f"la snapshot citada no es de desarrollo (kind={manifest.get('kind')!r})"
    if snap["snapshot_id"] != manifest.get("snapshot_id"):
        return "snapshot_id del preregistro distinto del de la snapshot verificada"
    if snap["train_val_sha256"] != (manifest.get("files") or {}).get("train_val", {}).get("sha256"):
        return "train_val_sha256 del preregistro distinto del de la snapshot verificada"
    if snap["d_dev"] != manifest.get("d_dev"):
        return "d_dev del preregistro distinto del de la snapshot verificada"
    return None


def freeze_evidence(frozen: "FrozenPreregistration") -> dict:
    """Evidencia exacta de la transición a PREREGISTERED que implica el preregistro congelado (B3-01):
    SHA-256, `trials_accounting`, clase de independencia y histórico mínimo o exención del piloto."""
    c = frozen.content
    cls = B.boundary_class(c.get("independence_boundary"))
    ev = {"preregistration_sha256": frozen.sha256, "trials_accounting": c["trials_count"], "independence_class": cls}
    if cls == B.CONFIRMATORY:
        ev["min_history_ok"] = True
    else:
        ev["min_history_exempt"] = B.TRADE_RATE_PILOT
    return ev


def _development_snapshot_error(content: dict, dev_manifest_path, data_root) -> str | None:
    """I2 y comprobaciones de ET-1 que dependen de la snapshot de desarrollo: verificada (SHA-256 de
    `train_val`), coincidente con la declarada y, si es confirmatorio, `available_months` recalculado igual
    al declarado y suficiente, y `D_dev < B`. None = conforme; si no, el motivo."""
    try:
        verify_snapshot(dev_manifest_path, data_root)
        manifest = load_manifest(dev_manifest_path)
    except (SnapshotError, OSError, ValueError, TypeError) as exc:
        return f"snapshot de desarrollo no verificable (I2): {exc}"
    why = _manifest_binding_error(content, manifest)
    if why:
        return f"snapshot de desarrollo: {why}"
    if B.boundary_class(content.get("independence_boundary")) == B.CONFIRMATORY:
        mh, ib = content["min_history"], content["independence_boundary"]
        avail = round(B.available_months(manifest["d_dev_ms"], manifest["range"]["start_ms"]), 2)
        if avail != mh["available_months"]:
            return (f"available_months declarado ({mh['available_months']}) distinto del recalculado desde la "
                    f"snapshot ({avail})")
        if avail < mh["required_months"]:
            return "histórico mínimo no alcanzado: no se congela (queda en DESIGN)"
        if manifest["d_dev_ms"] >= B.to_ms(B.parse_midnight(ib["B"])):
            return "D_dev debe ser anterior a B"
    return None


def build_freeze_check(frozen: "FrozenPreregistration", store: PreregistrationStore, *, dev_manifest_path,
                       data_root) -> FreezeCheck:
    """`FreezeCheck` de ET-1 (CR-023 §C.9, C.4.2): lo ejecuta `ExperimentRegistry.transition` DENTRO del
    bloqueo con los registros vigentes, el experimento y la evidencia de la transición. Devuelve None o el
    motivo del rechazo. Todas las comprobaciones de ET-1 están aquí (B3-01), no solo en `preregister`:
    - vinculación: el experimento es el del preregistro y la evidencia es exactamente `freeze_evidence`
      (la clase, el SHA-256 y el histórico mínimo no los declara quien llama);
    - I2 y snapshot de desarrollo (`_development_snapshot_error`);
    - V2: el contenido citado se recupera del almacén, su SHA-256 coincide y es el congelado.
    - Piloto de tasa: nada más (no reserva ventanas).
    - Confirmatorio: `B` ≥ mayor `b_not_before` del inventario; `B` ≥ fin del LOCKBOX de todo otro
      experimento nativo congelado, sea cual sea su estado (C.4.2.3, C.4.2.4, C.7.4); un congelado sin
      clase de independencia o con contenido irrecuperable se rechaza (Fail-Closed); V7 mecánico:
      `independence_deviation_ids` = DEVIATION de independencia del registro; el piloto citado en
      `trade_rate_source` es un experimento nativo congelado como piloto, con contenido verificable."""
    frozen.verify()
    content, eid = frozen.content, frozen.experiment_id
    cls = B.boundary_class(content.get("independence_boundary"))
    expected = freeze_evidence(frozen)

    def check(records: list[dict], experiment_id: str, evidence: dict) -> str | None:
        if experiment_id != eid:
            return f"la comprobación de congelación es de {eid}, no de {experiment_id!r}"
        if evidence != expected:
            return "la evidencia de la transición no coincide con la que implica el preregistro congelado (B3-01)"
        why = _development_snapshot_error(content, dev_manifest_path, data_root)
        if why:
            return why
        try:
            loaded = store.verify_cited(eid, frozen.sha256, frozen.sha256)
        except PreregStoreError as exc:
            return f"V2: contenido del preregistro no recuperable del almacén: {exc}"
        if loaded != frozen.content:
            return "V2: el contenido del almacén difiere del preregistro congelado"
        if cls == B.TRADE_RATE_PILOT:
            return None
        if cls != B.CONFIRMATORY:
            return "independence_boundary no válido"
        ib = content["independence_boundary"]
        b = B.parse_midnight(ib["B"])
        floor = B.max_b_not_before(ib["exposure_inventory"])
        if b < floor:
            return f"B ({ib['B']}) anterior al fin de la exposición inventariada ({B.format_instant(floor)})"
        exps = ExperimentRegistry._experiments_from(records)
        for oid, e in exps.items():
            if oid == eid or e.get("origin") != REGISTRY_ORIGIN:
                continue
            pre = [h for h in e["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
            if not pre:
                continue
            ev = pre[0].get("evidence") or {}
            if len(pre) != 1 or ev.get("independence_class") not in (B.CONFIRMATORY, B.TRADE_RATE_PILOT):
                return f"{oid}: congelado sin clase de independencia válida; no se puede comprobar su ventana (Fail-Closed)"
            if ev["independence_class"] == B.TRADE_RATE_PILOT:
                continue
            why = _prior_window_error(store, oid, ev.get("preregistration_sha256"), b)
            if why:
                return why
        return _v7_and_pilot_error(store, records, exps, content)
    return FreezeCheck(_FREEZE_CHECK_KEY, check)


def _prior_window_error(store, oid: str, sha, new_b) -> str | None:
    """`B` nueva ≥ fin del LOCKBOX de un confirmatorio anterior (cualquier estado; C.4.2.3, C.7.4)."""
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        return f"{oid}: PREREGISTERED sin SHA-256 válido"
    try:
        other = store.verify_cited(oid, sha)
    except PreregStoreError as exc:
        return f"{oid}: contenido congelado no recuperable ({exc}); no se puede comprobar su ventana"
    ib = other.get("independence_boundary")
    if B.boundary_class(ib) != B.CONFIRMATORY or B.boundary_error(ib):
        return f"{oid}: frontera confirmatoria congelada no válida; no se puede comprobar su ventana"
    end = B.lockbox_end(ib, oid)
    if new_b < end:
        return (f"B anterior al fin del LOCKBOX de {oid} ({B.format_instant(end)}): una frontera nueva es posterior "
                "a toda ventana anterior (C.7.4)")
    return None


def _v7_and_pilot_error(store, records, exps, content) -> str | None:
    ib = content["independence_boundary"]
    recorded = set()
    for r in records:
        if isinstance(r, dict) and r.get("kind") == "DEVIATION" and r.get("field") == "independence_boundary":
            why = _deviation_shape_error(r)
            if why:
                return f"registro DEVIATION de independencia incoherente ({why}): {r.get('deviation_id')}"
            recorded.add(r["deviation_id"])
    declared = set(ib["exposure_inventory"]["independence_deviation_ids"])
    if declared != recorded:
        return (f"V7: independence_deviation_ids {sorted(declared)} no coincide con los DEVIATION de independencia "
                f"del registro {sorted(recorded)}")
    pid = content["trade_rate_source"]["pilot_experiment_id"]
    pilot = exps.get(pid)
    if pilot is None or pilot.get("origin") != REGISTRY_ORIGIN:
        return f"el piloto de tasa {pid} no es un experimento nativo registrado"
    pre = [h for h in pilot["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
    ev = (pre[0].get("evidence") or {}) if len(pre) == 1 else {}
    if ev.get("independence_class") != B.TRADE_RATE_PILOT or not isinstance(ev.get("preregistration_sha256"), str) \
            or not _SHA256.fullmatch(ev["preregistration_sha256"]):
        return f"{pid} no fue congelado como piloto de tasa"
    try:
        pc = store.verify_cited(pid, ev["preregistration_sha256"])
    except PreregStoreError as exc:
        return f"contenido del piloto {pid} no recuperable del almacén: {exc}"
    if B.boundary_class(pc.get("independence_boundary")) != B.TRADE_RATE_PILOT \
            or B.boundary_error(pc.get("independence_boundary")):
        return f"el contenido almacenado de {pid} no es un piloto de tasa"
    return None


def preregister(registry, frozen: "FrozenPreregistration", *, store: PreregistrationStore, dev_manifest_path,
                data_root, actor: str = "orquestador") -> dict:
    """ET-1 (CR-023 §C.9): congela en el registro (DESIGN → PREREGISTERED).
    Orden: (1) snapshot de desarrollo verificada (I2) y coincidente con la declarada; confirmatorio:
    `available_months` recalculado igual al declarado y suficiente, y `D_dev < B`; (2) contenido escrito
    en el almacén (si falla, no hay transición y el archivo huérfano se conserva); (3) transición con
    el SHA-256, el `trials_accounting` declarado (el registro lo recalcula dentro del bloqueo, CR-020
    §C.3.3) y un `freeze_check` ejecutado dentro del bloqueo (V2, ventanas anteriores, V7, piloto)."""
    if not isinstance(registry, ExperimentRegistry):
        raise PreregistrationError("se requiere un ExperimentRegistry válido")
    if not isinstance(store, PreregistrationStore):
        raise PreregistrationError("se requiere un PreregistrationStore (CR-023 §C.4.1)")
    frozen.verify()
    c = frozen.content
    why = B.independence_error(c, c["trials_count"]["planned_config_ids"]) \
        if not accounting_shape_error(c.get("trials_count")) else "trials_count no válido"
    if why:
        raise PreregistrationError(f"preregistro no válido para ET-1: {why}")
    why = _development_snapshot_error(c, dev_manifest_path, data_root)   # comprobación anticipada (sin escribir)
    if why:
        raise PreregistrationError(why)
    store.write_frozen(frozen)           # antes de PREREGISTERED; un fallo del almacén no transita (C.4.1.2)
    return registry.transition(frozen.experiment_id, "PREREGISTERED", actor=actor, evidence=freeze_evidence(frozen),
                               freeze_check=build_freeze_check(frozen, store, dev_manifest_path=dev_manifest_path,
                                                               data_root=data_root))


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
    if r["field"] == "independence_boundary":       # CR-023 §D.2: forma exacta; antes y después de escribir
        return B.independence_deviation_error(r)
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
    """Congela un preregistro tras validarlo de forma pura, sin E/S (CR-023 §C.5, C.8). Un preregistro
    incompleto o con una forma de independencia no válida no se congela (queda en DESIGN)."""
    missing = [k for k in REQUIRED_FIELDS if k not in prereg or prereg[k] in (None, "", [], {})]
    if missing:
        raise PreregistrationError(f"preregistro incompleto: {missing}")
    validate_wf_design(prereg["wf_design"], prereg["label_horizon_months"])
    why = accounting_shape_error(prereg["trials_count"])               # CR-020 §C.3.3
    if why:
        raise PreregistrationError(f"trials_count debe declarar el desglose de la contabilidad de pruebas: {why}")
    why = B.independence_error(prereg, prereg["trials_count"]["planned_config_ids"])   # CR-023 §C.3, C.5, C.8
    if why:
        raise PreregistrationError(why)
    parse_selection_rule(prereg["candidate_selection_rule"], prereg["trials_count"]["planned_config_ids"],
                         prereg["metrics"])                           # CR-020 §C.3.4
    content = json.loads(canonical_json(prereg))
    return FrozenPreregistration(content, hashlib.sha256(canonical_json(content).encode()).hexdigest(),
                                 datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
