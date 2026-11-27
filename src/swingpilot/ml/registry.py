"""Registro de modelos ML: versionado, promoción y degradación (FEAT-019; REQ-G-092, REQ-G-105;
REQ-G-P21..P23; DEC-005; DEC-017 Q44; TC-ML-008, TC-ML-009).

Solo infraestructura: no hay entrenamiento ni inferencia productiva en este módulo.

- Identidad: (model_id, version) único; nunca se reutiliza para otro modelo. model_hash =
  SHA-256 de datos + código + parámetros (P23).
- Estados: REGISTERED → ACTIVE (solo por promoción) → SUSPENDED | RETIRED.
- Promoción solo si el experimento del modelo está en APPROVED en el registro de experimentos
  (al que solo se llega por HUMAN_REVIEW → APPROVED con decisión del propietario). Todo intento
  rechazado queda registrado (TC-ML-009). A lo sumo un modelo ACTIVE.
- Degradación (P22): expectancy de los últimos 20 trades bajo el límite inferior del IC OOS,
  o PSI > 0.25 en alguna variable de entrada → SUSPENDED (Fail-Closed). Sin reentrenamiento
  automático (P21): un modelo suspendido no vuelve a ACTIVE; solo otro modelo/versión promovido.
- Registro de eventos append-only en SQLite (triggers impiden UPDATE/DELETE).
"""
import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PSI_MAX = 0.25
LAST_N_TRADES = 20
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_DDL = """
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT NOT NULL, version TEXT NOT NULL, model_hash TEXT NOT NULL,
    data_hash TEXT NOT NULL, code_hash TEXT NOT NULL, params_json TEXT NOT NULL,
    experiment_id TEXT NOT NULL, registered_at_utc TEXT NOT NULL,
    PRIMARY KEY (model_id, version));
CREATE TABLE IF NOT EXISTS model_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, model_id TEXT, version TEXT, event TEXT NOT NULL,
    detail_json TEXT NOT NULL, at_utc TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS models_no_update BEFORE UPDATE ON models
BEGIN SELECT RAISE(ABORT, 'models es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS models_no_delete BEFORE DELETE ON models
BEGIN SELECT RAISE(ABORT, 'models es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS model_events_no_update BEFORE UPDATE ON model_events
BEGIN SELECT RAISE(ABORT, 'model_events es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS model_events_no_delete BEFORE DELETE ON model_events
BEGIN SELECT RAISE(ABORT, 'model_events es inmutable'); END;
"""

STATE_EVENTS = {"REGISTERED": "REGISTERED", "PROMOTED": "ACTIVE", "SUSPENDED": "SUSPENDED", "RETIRED": "RETIRED"}


class ModelRegistryError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def model_hash(data_hash: str, code_hash: str, params: dict) -> str:
    payload = json.dumps({"data": data_hash, "code": code_hash, "params": params},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def psi(expected: list[float], actual: list[float], bins: int = 10, eps: float = 1e-6) -> float:
    """Population Stability Index con cortes por cuantiles de la distribución de referencia."""
    e = np.asarray(expected, dtype=float)
    a = np.asarray(actual, dtype=float)
    e, a = e[~np.isnan(e)], a[~np.isnan(a)]
    if len(e) < bins or len(a) == 0:
        raise ValueError("datos insuficientes para PSI")
    edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    pe = np.histogram(e, edges)[0] / len(e) + eps
    pa = np.histogram(a, edges)[0] / len(a) + eps
    return float(np.sum((pa - pe) * np.log(pa / pe)))


class ModelRegistry:
    def __init__(self, path: str | Path, experiments, now=_now):
        self._db = sqlite3.connect(str(path))
        self._db.executescript(_DDL)
        self.experiments = experiments
        self._now = now

    def close(self) -> None:
        self._db.close()

    def _event(self, model_id, version, event, detail: dict) -> None:
        with self._db:
            self._db.execute("INSERT INTO model_events(model_id, version, event, detail_json, at_utc) VALUES (?,?,?,?,?)",
                             (model_id, version, event, json.dumps(detail, sort_keys=True, ensure_ascii=False), self._now()))

    def events(self, model_id: str | None = None) -> list[tuple]:
        q = "SELECT model_id, version, event, detail_json FROM model_events"
        args = ()
        if model_id:
            q += " WHERE model_id=?"
            args = (model_id,)
        return self._db.execute(q + " ORDER BY seq", args).fetchall()

    def register(self, model_id: str, version: str, *, data_hash: str, code_hash: str, params: dict,
                 experiment_id: str) -> str:
        if self._db.execute("SELECT 1 FROM models WHERE model_id=? AND version=?", (model_id, version)).fetchone():
            raise ModelRegistryError(f"{model_id} {version} ya existe: un ID+versión no se reutiliza")
        for name, h in (("data_hash", data_hash), ("code_hash", code_hash)):
            if not isinstance(h, str) or not _SHA256.match(h):
                raise ModelRegistryError(f"{name} debe ser un SHA-256 hexadecimal en minúsculas (QA3-18)")
        if self.experiments.eligible_state(experiment_id) is None:
            raise ModelRegistryError(f"experimento {experiment_id} no registrado (los antecedentes no son elegibles)")
        h = model_hash(data_hash, code_hash, params)
        with self._db:
            self._db.execute("INSERT INTO models VALUES (?,?,?,?,?,?,?,?)",
                             (model_id, version, h, data_hash, code_hash,
                              json.dumps(params, sort_keys=True), experiment_id, self._now()))
        self._event(model_id, version, "REGISTERED", {"model_hash": h, "experiment_id": experiment_id})
        return h

    def state(self, model_id: str, version: str) -> str | None:
        st = None
        for _, _, ev, _ in self._db.execute(
                "SELECT model_id, version, event, detail_json FROM model_events WHERE model_id=? AND version=? ORDER BY seq",
                (model_id, version)):
            st = STATE_EVENTS.get(ev, st)
        return st

    def model_record(self, model_id: str, version: str) -> dict | None:
        row = self._db.execute("SELECT model_hash, experiment_id FROM models WHERE model_id=? AND version=?",
                               (model_id, version)).fetchone()
        return {"model_id": model_id, "version": version, "model_hash": row[0], "experiment_id": row[1]} if row else None

    def active_model(self) -> dict | None:
        """El modelo ACTIVE o None (→ NO_ACTIVE_MODEL cuando CR-018 se apruebe)."""
        for mid, ver, *_ in self._db.execute("SELECT model_id, version FROM models ORDER BY registered_at_utc").fetchall():
            if self.state(mid, ver) == "ACTIVE":
                row = self._db.execute("SELECT model_hash, experiment_id FROM models WHERE model_id=? AND version=?",
                                       (mid, ver)).fetchone()
                return {"model_id": mid, "version": ver, "model_hash": row[0], "experiment_id": row[1]}
        return None

    def promote(self, model_id: str, version: str, *, requested_by: str, promotion_check=None) -> None:
        """P23 + ET-9/U1: exige APPROVED y elegibilidad ET-9 ELIGIBLE recalculada, DENTRO del bloqueo del registro
        de experimentos (misma sección crítica que la escritura del evento PROMOTED). Sin `PromotionCheck` de este
        registro, o ante cualquier fallo/corrupción/no verificable → rechazo registrado (Fail-Closed). Los APPROVED
        históricos se conservan, pero no promueven sin ET-9."""
        from swingpilot.research.experiments import ExperimentRegistry, PromotionCheck
        row = self._db.execute("SELECT experiment_id FROM models WHERE model_id=? AND version=?",
                               (model_id, version)).fetchone()
        eid = row[0] if row else None

        def gate(records):
            if row is None:
                raise ModelRegistryError("modelo no registrado")
            if self.state(model_id, version) != "REGISTERED":
                raise ModelRegistryError(f"estado {self.state(model_id, version)}: solo se promueve un modelo REGISTERED")
            exp = ExperimentRegistry._experiments_from(records).get(eid)
            if exp is None or exp["origin"] != "REGISTRY" or exp["state"] != "APPROVED":   # QA3-03
                raise ModelRegistryError(f"el experimento {eid} no está en APPROVED (HUMAN_REVIEW → APPROVED, P23)")
            if self.active_model() is not None:
                raise ModelRegistryError("ya hay un modelo ACTIVE: retirarlo antes")
            if type(promotion_check) is not PromotionCheck or promotion_check.registry is not self.experiments:
                raise ModelRegistryError("la promoción exige un «promotion_check» PromotionCheck de este registro "
                                         "(independence.build_promotion_check; ET-9, sin anulaciones)")
            try:
                why = promotion_check(records, eid)
            except Exception as exc:
                raise ModelRegistryError(f"ET-9 no pudo comprobarse (Fail-Closed): {exc!r}") from exc
            if why:
                raise ModelRegistryError(f"promoción rechazada por ET-9: {why}")

        def publish():
            self._event(model_id, version, "PROMOTED", {"requested_by": requested_by, "experiment_id": eid})

        try:
            self.experiments.publish_under_lock(gate, publish)
        except ModelRegistryError as exc:
            reason = str(exc)
        except Exception as exc:                       # registro corrupto / ilegible: no verificable
            reason = f"elegibilidad no verificable (Fail-Closed): {exc!r}"
        else:
            return
        self._event(model_id, version, "PROMOTION_REJECTED", {"reason": reason, "requested_by": requested_by})
        raise ModelRegistryError(reason)

    def retire(self, model_id: str, version: str, *, reason: str) -> None:
        if self.state(model_id, version) not in ("ACTIVE", "SUSPENDED", "REGISTERED"):
            raise ModelRegistryError("no se puede retirar")
        self._event(model_id, version, "RETIRED", {"reason": reason})

    def check_degradation(self, model_id: str, version: str, *, last_trades_net_r: list[float],
                          ic_lower_bound_oos: float, psi_by_feature: dict[str, float]) -> dict:
        """P22. Devuelve el diagnóstico; si se dispara, suspende (sin reentrenar, P21)."""
        if self.state(model_id, version) != "ACTIVE":
            raise ModelRegistryError("solo se vigila un modelo ACTIVE")
        reasons = []
        recent = last_trades_net_r[-LAST_N_TRADES:]
        # QA3-14: Fail-Closed ante valores no finitos (un NaN no puede evitar la suspensión)
        if not isinstance(ic_lower_bound_oos, (int, float)) or not math.isfinite(ic_lower_bound_oos):
            reasons.append("límite inferior del IC OOS no finito")
        if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in recent):
            reasons.append("trades recientes con valores no finitos")
        exp20 = float(np.mean(recent)) if len(recent) == LAST_N_TRADES and not reasons else None
        if exp20 is not None and exp20 < ic_lower_bound_oos:
            reasons.append(f"expectancy últimos {LAST_N_TRADES} trades {exp20:.3f} < IC OOS inferior {ic_lower_bound_oos:.3f}")
        bad = {k: v for k, v in psi_by_feature.items() if (v is None or math.isnan(v) or v > PSI_MAX)}
        if bad:
            reasons.append(f"PSI > {PSI_MAX} o no calculable en {sorted(bad)}")
        diag = {"expectancy_last20": exp20, "ic_lower_bound_oos": ic_lower_bound_oos,
                "psi": psi_by_feature, "suspended": bool(reasons), "reasons": reasons}
        if reasons:
            self._event(model_id, version, "SUSPENDED", diag)
        return diag
