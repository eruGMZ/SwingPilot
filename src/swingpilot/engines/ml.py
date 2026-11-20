"""ML Engine — evento ML_INFERENCE_COMPLETED (FEAT-019 AC-019-4; api_contracts.md §3.8 B.3;
DEC-017 Q44; REQ-G-071, REQ-G-105).

- Sin modelo ACTIVE en el registro → `NO_ACTIVE_MODEL` (estado esperado en IMPL-3: no hay
  modelo entrenado). Si el último modelo promovido está SUSPENDED → `MODEL_SUSPENDED` con el
  motivo. Con modelo ACTIVE, la inferencia la produce un `Predictor` inyectado (en IMPL-3 solo
  en pruebas); sin predictor → ERROR `SPEC_NOT_FOUND`.
- `advisory_only = true`: la salida no es decisor ni autorización (REQ-G-071, REQ-G-105).
- Sin dependencia de LLM ni de librerías de entrenamiento.
"""
import json
from typing import Protocol

from swingpilot.ml.registry import ModelRegistry

from .common import MarketInput, base_payload, engine_message

ENGINE = "ml_engine"
ENGINE_VERSION = "0.1.0"


class Predictor(Protocol):
    model_id: str
    model_version: str
    feature_set_version: str
    timeframe: str

    def predict(self, market: MarketInput) -> tuple[dict, str]:
        """Devuelve (prediction según B.3, features_hash)."""


def _null_model() -> dict:
    return {k: None for k in ("model_id", "model_version", "model_hash", "approval_ref",
                              "feature_set_version", "features_hash")}


class MLEngine:
    def __init__(self, registry: ModelRegistry, predictor: Predictor | None = None, *, timeframe: str = "H4"):
        self.registry = registry
        self.predictor = predictor
        self.timeframe = predictor.timeframe if predictor else timeframe

    def _last_suspended(self) -> tuple[dict, str] | None:
        for mid, ver, ev, detail in reversed(self.registry.events()):
            if ev == "PROMOTED":
                return None
            if ev == "SUSPENDED":
                d = json.loads(detail)
                rec = self.registry.model_record(mid, ver)
                return ({"model_id": mid, "model_version": ver, "model_hash": rec["model_hash"],
                         "approval_ref": rec["experiment_id"],
                         "feature_set_version": None, "features_hash": None}, "; ".join(d.get("reasons", [])) or "suspendido")
        return None

    def run(self, cause: dict, market: MarketInput) -> dict:
        tf = self.timeframe
        refs = {tf: market.data_ref(tf)}

        def out(status, inference_status, model, prediction=None, drift=None, missing=None, error=None):
            p = {**base_payload(ENGINE, ENGINE_VERSION, None, status, refs, missing, error),
                 "inference_status": inference_status, **model, "prediction": prediction, "drift": drift,
                 "advisory_only": True}
            return engine_message(cause, source=ENGINE, message_type="ML_INFERENCE_COMPLETED", payload=p,
                                  data_timestamp_utc=market.data_timestamp(tf), timeframe=tf)

        active = self.registry.active_model()
        if active is None:
            susp = self._last_suspended()
            if susp:
                model, reason = susp
                return out("COMPLETED", "MODEL_SUSPENDED", model,
                           drift={"psi_max": None, "expectancy_last20": None, "ic_lower_bound_oos": None,
                                  "suspended_reason": reason})
            return out("COMPLETED", "NO_ACTIVE_MODEL", _null_model())
        if self.predictor is None or (self.predictor.model_id, self.predictor.model_version) != (active["model_id"], active["version"]):
            return out("ERROR", "NO_ACTIVE_MODEL", _null_model(),
                       error={"code": "SPEC_NOT_FOUND", "message": "modelo ACTIVE sin predictor cargado"})
        bad = market.inconsistency(tf)                       # QA3E-03
        if bad:
            return out("ERROR", "NO_ACTIVE_MODEL", _null_model(), error={"code": "DATA_INCONSISTENT", "message": bad})
        if not market.has_last_closed(tf):
            return out("ERROR", "NO_ACTIVE_MODEL", _null_model(),
                       error={"code": "DATA_UNAVAILABLE", "message": f"falta la última vela {tf} cerrada"})
        try:
            prediction, features_hash = self.predictor.predict(market)
        except Exception as exc:   # noqa: BLE001
            return out("ERROR", "NO_ACTIVE_MODEL", _null_model(),
                       error={"code": "INTERNAL_ERROR", "message": f"{type(exc).__name__}: {exc}"})
        model = {"model_id": active["model_id"], "model_version": active["version"], "model_hash": active["model_hash"],
                 "approval_ref": active["experiment_id"], "feature_set_version": self.predictor.feature_set_version,
                 "features_hash": features_hash}
        return out("COMPLETED", "INFERENCE_AVAILABLE", model, prediction=prediction,
                   drift={"psi_max": None, "expectancy_last20": None, "ic_lower_bound_oos": None, "suspended_reason": None})
