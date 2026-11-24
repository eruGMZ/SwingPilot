"""Registro de experimentos (FEAT-017; REQ-G-104, REQ-G-107, REQ-G-P17; TC-ML-010; DEC-018 decisión 4).

- 12 estados: IDEA → DESIGN → PREREGISTERED → DATA_VALIDATION → DEVELOPMENT → VALIDATION →
  OOS_EVALUATION → AUDIT → HUMAN_REVIEW → APPROVED | REJECTED | INCONCLUSIVE.
- Append-only (JSONL): el estado se obtiene reproduciendo el registro; nada se borra ni se
  reescribe, también los experimentos REJECTED o INCONCLUSIVE (TC-ML-010).
- Ninguna transición a APPROVED (ni la entrada a OOS_EVALUATION, que consume datos de una
  sola evaluación) sin un documento de decisión del propietario existente en docs/decisions.
  La IA no puede aprobar (REQ-G-107).
- Antecedentes declarados por el propietario (EXP-0001, Mean Reversion H1) se registran con
  su origen y cuentan para la corrección por número de experimentos (REQ-G-P17). Solo pueden
  registrarse en PENDING_DOCUMENTATION, REJECTED o INCONCLUSIVE, y no son elegibles para abrir
  particiones ni promover modelos (QA3-03): los consumidores usan `eligible_state()`.
- Identificadores (QA3R2-04): `create()` solo acepta `EXP-NNNN` (cuatro dígitos ASCII, sin
  espacios ni saltos de línea). Los antecedentes declarados conservan el identificador que
  les dio el propietario (p. ej. `ANT-MR-H1`), porque nunca abren particiones ni respaldan
  modelos.
- Decisiones (QA3-04, QA3R2-04): `decision_ref` es un nombre de archivo `DEC-NNN…md` sin ruta,
  dentro de `docs/decisions` del repositorio (el directorio solo se sustituye en pruebas), que
  no sea un enlace simbólico. La autorización no se busca por subcadena en el texto: el
  documento debe contener una línea estructurada, sola en su línea y al inicio de ella, que
  coincida exactamente con lo que se autoriza:
      AUTORIZA: EXP-NNNN <ESTADO_DESTINO>       (transiciones que decide el propietario)
      AUTORIZA: EXP-NNNN <oos|lockbox> SNAP-…   (evaluación final de una partición)
  Cada campo se compara por igualdad exacta (mayúsculas incluidas). Una línea que no siga la
  gramática no autoriza nada. La línea de transición nombra el estado destino (observación
  adicional de QA3R2-04, FEAT-017): una autorización de OOS_EVALUATION no vale para APPROVED
  ni para un estado terminal, y la línea sin estado no autoriza nada. Los estados admitidos
  son exactamente los que hoy decide el propietario (`OWNER_DECIDED`); como la máquina solo
  avanza, cada línea sirve en la práctica una sola vez. Es un control en proceso, no criptográfico: no autentica a una
  persona; deja la autorización trazable a un documento versionado.
- Consumo de OOS/LOCKBOX (QA3-06): se registra aquí (archivo versionado), no solo en el
  registro de accesos.
- Desviaciones del preregistro (ORQ-017-01): registros DEVIATION append-only, escritos con
  `append_deviation` bajo el mismo bloqueo exclusivo que el consumo de particiones. Documentan
  una desviación; no la autorizan, no cambian el preregistro congelado ni dan autoridad de
  decisión a la IA. La validación y el carácter confirmatorio se derivan en
  `preregistration.py`. `experiments()` y `trials_count()` ignoran este tipo de registro.
- Concurrencia (QA3R2-03): toda escritura toma un `flock` exclusivo sobre `<registro>.lock`;
  `claim_partition` comprueba y anota el consumo dentro del mismo bloqueo, de modo que dos
  procesos no pueden consumir a la vez la misma partición. Requiere un sistema POSIX (Linux,
  como los equipos del proyecto) y un sistema de archivos local.
- Contabilidad de pruebas (CR-020, DEC-021; REQ-G-P17, REQ-G-103, REQ-G-104; contrato v1.8):
  - Unidad: par (`experiment_id`, `config_id`) evaluado. `CONFIGURATION_EVALUATED` se escribe
    de forma duradera ANTES de evaluar y es el límite contable conservador de un inicio
    autorizado, no prueba de ejecución. Solo se admite en DEVELOPMENT o VALIDATION (estados a
    los que se llega tras PREREGISTERED y con la snapshot verificada); un estado no terminal no
    basta. Una solicitud rechazada no escribe nada y no cuenta.
  - Antecedentes: `ANTECEDENT_PROVENANCE` append-only, autorizado por la línea exacta
    `AUTORIZA: PROCEDENCIA <id> DOCUMENTADAS=<n> COTA=<m>`; no cambia el estado original del
    registro ANTECEDENT. Un antecedente sin procedencia válida hace el conteo indeterminado.
  - `trials_count()` = H_doc + H_bound + E (conteo global G). La congelación (PREREGISTERED)
    exige `trials_accounting`, recalculado dentro del bloqueo; la selección de candidata
    (OOS_EVALUATION) exige `selected_config_id`, `selection_inputs_sha256` e `informed_by`.
  - Estados y transiciones de REQ-G-104 sin cambios.
"""
import contextlib
import fcntl
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .snapshot import SEALED, SNAPSHOT_ID

REPO_DECISIONS_DIR = Path(__file__).resolve().parents[3] / "docs" / "decisions"
_DECISION_NAME = re.compile(r"DEC-[0-9]{3}[A-Za-z0-9_.-]*\.md")            # siempre con fullmatch
EXPERIMENT_ID = re.compile(r"EXP-[0-9]{4}")                                # siempre con fullmatch
# Transición: «AUTORIZA: EXP-NNNN ESTADO»; partición: «AUTORIZA: EXP-NNNN parte SNAP-…» (fullmatch)
_AUTHORIZATION = re.compile(r"AUTORIZA: (EXP-[0-9]{4})(?: (\S+)(?: (\S+))?)?")


def valid_experiment_id(experiment_id) -> bool:
    return isinstance(experiment_id, str) and EXPERIMENT_ID.fullmatch(experiment_id) is not None


def _valid_snapshot_id(snapshot_id) -> bool:
    return isinstance(snapshot_id, str) and SNAPSHOT_ID.fullmatch(snapshot_id) is not None


def authorizations(text: str) -> set[tuple[str, str | None, str | None]]:
    """Líneas «AUTORIZA: …» como tuplas: (experimento, estado, None) para una transición y
    (experimento, partición, snapshot) para una partición. Una línea sin campos da
    (experimento, None, None), que no autoriza nada."""
    out = set()
    for line in text.splitlines():
        m = _AUTHORIZATION.fullmatch(line.rstrip())
        if m:
            out.add(m.groups())
    return out

STATES = ("IDEA", "DESIGN", "PREREGISTERED", "DATA_VALIDATION", "DEVELOPMENT", "VALIDATION",
          "OOS_EVALUATION", "AUDIT", "HUMAN_REVIEW", "APPROVED", "REJECTED", "INCONCLUSIVE")
TERMINAL = ("APPROVED", "REJECTED", "INCONCLUSIVE")
# Estados destino que hoy decide el propietario con documento de decisión (sin cambiar la máquina)
OWNER_DECIDED = ("OOS_EVALUATION", "APPROVED", "REJECTED", "INCONCLUSIVE")
_FORWARD = {
    "IDEA": "DESIGN", "DESIGN": "PREREGISTERED", "PREREGISTERED": "DATA_VALIDATION",
    "DATA_VALIDATION": "DEVELOPMENT", "DEVELOPMENT": "VALIDATION", "VALIDATION": "OOS_EVALUATION",
    "OOS_EVALUATION": "AUDIT", "AUDIT": "HUMAN_REVIEW",
}
# Requisitos verificables por transición (evidencias que deben acompañarla)
_REQUIRES = {
    "PREREGISTERED": ("preregistration_sha256", "min_history_ok"),
    "DEVELOPMENT": ("snapshot_verified",),
    "OOS_EVALUATION": ("decision_ref",),
    "APPROVED": ("decision_ref",),
}
OWNER = "propietario"
DECLARED_ANTECEDENT = "DECLARED_ANTECEDENT"
REGISTRY_ORIGIN = "REGISTRY"
ANTECEDENT_STATES = ("PENDING_DOCUMENTATION", "REJECTED", "INCONCLUSIVE")

# --- CR-020 (DEC-021) ---------------------------------------------------------------------------
CONFIG_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", re.ASCII)                 # fullmatch
ANTECEDENT_ID = re.compile(r"EXP-[0-9]{4}|ANT-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.ASCII)    # fullmatch (R4)
_PROVENANCE_AUTH = re.compile(r"AUTORIZA: PROCEDENCIA (\S+) DOCUMENTADAS=(0|[1-9][0-9]*) COTA=(0|[1-9][0-9]*)",
                              re.ASCII)                                               # fullmatch (R4)
_EVIDENCE_REF = re.compile(r"[A-Za-z0-9._-]+@[0-9a-f]{7,40}:[A-Za-z0-9._/-]+", re.ASCII)
_HEX32 = re.compile(r"[0-9a-f]{32}", re.ASCII)
_HEX64 = re.compile(r"[0-9a-f]{64}", re.ASCII)
DOCUMENTARY_STATUSES = ("DOCUMENTED", "PENDING_DOCUMENTATION")
EXECUTION_STATUSES = ("DOCUMENTED_EXECUTED", "UNKNOWN", "DOCUMENTED_NOT_EXECUTED")
EVIDENCE_CLASSES = ("DOCUMENTED_EVALUATED", "CONSERVATIVE_BOUND", "DOCUMENTED_NOT_EVALUATED")
# Estados en los que el contrato vigente permite evaluar configuraciones sobre Train+Val: tras
# PREREGISTERED y DATA_VALIDATION, con la snapshot verificada (REQ-G-103/104; condición de DEC-021).
EVALUATION_STATES = ("DEVELOPMENT", "VALIDATION")
ACCOUNTING_KEYS = ("H_doc", "H_bound", "E", "planned_config_ids", "planned_new", "N_pre", "provenance_ids")
_PROVENANCE_KEYS = ("provenance_id", "experiment_id", "documentary_status", "execution_status", "configurations",
                    "evidence", "decision_ref", "supersedes", "actor")


def valid_config_id(config_id) -> bool:
    return isinstance(config_id, str) and CONFIG_ID.fullmatch(config_id) is not None


def _nonneg_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def accounting_shape_error(acc) -> str | None:
    """Forma de `trials_accounting` / `trials_count` del preregistro (CR-020 §C.3.3). None = válida."""
    if not isinstance(acc, dict) or set(acc) != set(ACCOUNTING_KEYS):
        return f"se esperan exactamente las claves {ACCOUNTING_KEYS}"
    for k in ("H_doc", "H_bound", "E", "planned_new", "N_pre"):
        if not _nonneg_int(acc[k]):
            return f"{k} no es un entero ≥ 0"
    planned = acc["planned_config_ids"]
    if not isinstance(planned, list) or not planned or not all(valid_config_id(c) for c in planned):
        return "planned_config_ids debe ser una lista no vacía de config_id válidos"
    if len(set(planned)) != len(planned):
        return "planned_config_ids repite identificadores"
    if acc["planned_new"] > len(planned):
        return "planned_new mayor que el número de configuraciones planificadas"
    pids = acc["provenance_ids"]
    if not isinstance(pids, list) or not all(isinstance(p, str) and _HEX32.fullmatch(p) for p in pids) \
            or len(set(pids)) != len(pids) or pids != sorted(pids):
        return "provenance_ids debe ser una lista ordenada de identificadores únicos"
    if acc["N_pre"] != acc["H_doc"] + acc["H_bound"] + acc["E"] + acc["planned_new"]:
        return "N_pre ≠ H_doc + H_bound + E + planned_new"
    return None


def _evidence_ref_ok(ref) -> bool:
    if not isinstance(ref, str) or not _EVIDENCE_REF.fullmatch(ref):
        return False
    path = ref.split(":", 1)[1]
    parts = path.split("/")
    return not path.startswith("/") and "" not in parts and ".." not in parts and "." not in parts


class ExperimentError(RuntimeError):
    pass


class PersistenceUncertainError(ExperimentError):
    """La escritura falló después de empezar: el registro puede estar presente, ausente o a medias
    (ORQ-017-01). Nunca debe interpretarse como «no se escribió»."""


class TrialsAccountingError(ExperimentError):
    """Conteo de pruebas indeterminado o incoherente (CR-020): nunca se sustituye por un valor."""


class EvaluationRequestRejected(ExperimentError):
    """Solicitud de evaluación rechazada antes de escribir: no hay registro, no cuenta y la
    evaluación no empieza (CR-020 §C.3.2, B.4.1)."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ExperimentRegistry:
    def __init__(self, path: Path, decisions_dir: Path | None = None, now=_now):
        self.path = Path(path)
        self.decisions_dir = Path(decisions_dir) if decisions_dir is not None else REPO_DECISIONS_DIR
        self._now = now

    # --- lectura ---------------------------------------------------------------------------
    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def experiments(self) -> dict[str, dict]:
        return self._experiments_from(self.records())

    @staticmethod
    def _experiments_from(records: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in records:
            if r["kind"] in ("CREATED", "ANTECEDENT"):
                out[r["experiment_id"]] = {"experiment_id": r["experiment_id"], "title": r["title"],
                                           "origin": r.get("origin", REGISTRY_ORIGIN), "state": r["state"],
                                           "history": [r]}
            elif r["kind"] == "TRANSITION":
                e = out[r["experiment_id"]]
                e["state"] = r.get("to", e["state"])
                e["history"].append(r)
        return out

    def state(self, experiment_id: str) -> str | None:
        e = self.experiments().get(experiment_id)
        return e["state"] if e else None

    def eligible_state(self, experiment_id: str) -> str | None:
        """Estado solo para experimentos del propio registro; None para antecedentes (QA3-03)."""
        e = self.experiments().get(experiment_id)
        return e["state"] if e and e["origin"] == REGISTRY_ORIGIN else None

    def consumed_partitions(self) -> list[dict]:
        return [r for r in self.records() if r["kind"] == "PARTITION_CONSUMED"]

    def consumed_lockboxes(self) -> list[dict]:
        return [{"snapshot_id": r["snapshot_id"], "snapshot_last_open_time": r["snapshot_last_open_time"]}
                for r in self.consumed_partitions() if r["partition"] == "lockbox"]

    def is_consumed(self, snapshot_id: str, partition: str, experiment_id: str) -> bool:
        for r in self.consumed_partitions():
            if r["snapshot_id"] == snapshot_id and r["partition"] == partition:
                if partition == "lockbox" or r["experiment_id"] == experiment_id:
                    return True
        return False

    def claim_partition(self, *, snapshot_id: str, partition: str, experiment_id: str,
                        snapshot_last_open_time: int, decision_ref: str) -> dict | None:
        """Comprueba y registra el consumo de forma atómica entre procesos (QA3R2-03).
        Devuelve el registro, o None si la partición ya estaba consumida."""
        if not valid_experiment_id(experiment_id):
            raise ExperimentError(f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)")
        if partition not in SEALED:
            raise ExperimentError(f"partición no válida: {partition!r}")
        if not _valid_snapshot_id(snapshot_id):
            raise ExperimentError(f"snapshot no válida: {snapshot_id!r}")
        with self._locked():
            if self.is_consumed(snapshot_id, partition, experiment_id):
                return None
            return self._write({"kind": "PARTITION_CONSUMED", "snapshot_id": snapshot_id, "partition": partition,
                                "experiment_id": experiment_id, "snapshot_last_open_time": snapshot_last_open_time,
                                "decision_ref": decision_ref, "actor": OWNER})

    def record_partition_consumed(self, **kw) -> dict:
        rec = self.claim_partition(**kw)
        if rec is None:
            raise ExperimentError(f"{kw['partition']} de {kw['snapshot_id']} ya consumido (evaluación única)")
        return rec

    def trials_count(self) -> int:
        """Conteo global de pruebas G = H_doc + H_bound + E (REQ-G-P17, CR-020; DEC-018 decisión 4).
        Cuenta configuraciones evaluadas, no identificadores de experimento. Un antecedente sin
        procedencia válida, o un registro incoherente → TrialsAccountingError (Fail-Closed)."""
        acc = self.accounting()
        return acc["H_doc"] + acc["H_bound"] + acc["E"]

    # --- contabilidad de pruebas (CR-020) -------------------------------------------------------
    def accounting(self, upto: int | None = None, records: list[dict] | None = None, *,
                   require_complete: bool = True) -> dict:
        """Reproduce el registro hasta `upto` (exclusivo; orden del archivo = cronología) y
        devuelve H_doc, H_bound, E, los pares evaluados con su posición, la procedencia vigente
        de cada antecedente y sus ids. Valida cada registro de procedencia y de evaluación."""
        if records is None:
            try:
                records = self.records()
            except Exception as exc:
                raise TrialsAccountingError(f"registro de experimentos ilegible o corrupto: {exc!r}") from exc
        records = records[:upto] if upto is not None else records
        antecedents: set[str] = set()
        natives: set[str] = set()
        effective: dict[str, dict] = {}
        history: dict[str, list[dict]] = {}
        all_pids: set[str] = set()
        pairs: dict[tuple[str, str], int] = {}
        for i, r in enumerate(records):
            if not isinstance(r, dict):
                raise TrialsAccountingError(f"registro no válido en la posición {i}")
            kind = r.get("kind")
            if kind == "ANTECEDENT":
                antecedents.add(r.get("experiment_id"))
            elif kind == "CREATED":
                natives.add(r.get("experiment_id"))
            elif kind == "ANTECEDENT_PROVENANCE":
                why = self._provenance_error(r, antecedents, effective, all_pids)
                if why:
                    raise TrialsAccountingError(f"ANTECEDENT_PROVENANCE incoherente ({why}) en la posición {i}")
                effective[r["experiment_id"]] = r
                history.setdefault(r["experiment_id"], []).append(r)
                all_pids.add(r["provenance_id"])
            elif kind == "CONFIGURATION_EVALUATED":
                why = _evaluation_record_error(r, natives)
                if why:
                    raise TrialsAccountingError(f"CONFIGURATION_EVALUATED incoherente ({why}) en la posición {i}")
                pairs.setdefault((r["experiment_id"], r["config_id"]), i)
        missing = sorted(a for a in antecedents if a not in effective)
        if missing and require_complete:
            raise TrialsAccountingError(f"antecedentes sin procedencia válida: {missing}; conteo indeterminado "
                                        "(CR-020 §C.3.1)")
        h_doc = h_bound = 0
        for rec in effective.values():
            for c in rec["configurations"]:
                h_doc += c["evidence_class"] == "DOCUMENTED_EVALUATED"
                h_bound += c["evidence_class"] == "CONSERVATIVE_BOUND"
        return {"H_doc": h_doc, "H_bound": h_bound, "E": len(pairs), "pairs": pairs,
                "provenance": effective, "provenance_history": history,
                "provenance_ids": sorted(rec["provenance_id"] for rec in effective.values())}

    def trials_accounting(self, experiment_id: str, planned_config_ids: list[str],
                          upto: int | None = None, records: list[dict] | None = None) -> dict:
        """`trials_accounting` que debe declarar el preregistro de `experiment_id` (CR-020 §C.1):
        N_pre = G(t) + │P(X) \\ E_X(t)│. Sin efectos: no escribe nada."""
        acc = self.accounting(upto, records)
        planned = list(planned_config_ids) if isinstance(planned_config_ids, (list, tuple)) else planned_config_ids
        evaluated_x = {c for (e, c) in acc["pairs"] if e == experiment_id}
        new = len([c for c in planned if c not in evaluated_x]) if isinstance(planned, list) else 0
        out = {"H_doc": acc["H_doc"], "H_bound": acc["H_bound"], "E": acc["E"], "planned_config_ids": planned,
               "planned_new": new, "N_pre": acc["H_doc"] + acc["H_bound"] + acc["E"] + new,
               "provenance_ids": acc["provenance_ids"]}
        return out

    def antecedents(self) -> dict[str, dict]:
        """Consulta consolidada de antecedentes (CR-020 §C.3.1; condición de DEC-021 / CONF-009):
        `original_state` es el estado inmutable del registro ANTECEDENT; la procedencia documental
        vigente va en campos separados. Procedencia incoherente → TrialsAccountingError."""
        acc = self.accounting()
        out = {}
        for eid, e in self.experiments().items():
            if e["origin"] != DECLARED_ANTECEDENT:
                continue
            p = acc["provenance"].get(eid)
            out[eid] = {"experiment_id": eid, "title": e["title"], "original_state": e["history"][0]["state"],
                        "documentary_status": p["documentary_status"] if p else None,
                        "execution_status": p["execution_status"] if p else None,
                        "provenance_id": p["provenance_id"] if p else None,
                        "configurations": list(p["configurations"]) if p else [],
                        "provenance_history": list(acc["provenance_history"].get(eid, []))}
        return out

    def _provenance_error(self, r: dict, antecedents: set, effective: dict, all_pids: set) -> str | None:
        if any(k not in r for k in _PROVENANCE_KEYS):
            return "faltan campos"
        if set(r) - set(_PROVENANCE_KEYS) - {"kind", "at_utc"}:
            return "campos no reconocidos"
        if not isinstance(r["provenance_id"], str) or not _HEX32.fullmatch(r["provenance_id"]):
            return "provenance_id no válido"
        if r["provenance_id"] in all_pids:
            return "provenance_id duplicado"
        eid = r["experiment_id"]
        if not isinstance(eid, str) or not ANTECEDENT_ID.fullmatch(eid):
            return "identificador de antecedente no válido"
        if eid not in antecedents:
            return "no es un antecedente declarado anterior en el registro"
        if r["documentary_status"] not in DOCUMENTARY_STATUSES or r["execution_status"] not in EXECUTION_STATUSES:
            return "estado documental o de ejecución no válido"
        if r["actor"] != OWNER:
            return "solo el propietario registra procedencia"
        cfgs = r["configurations"]
        if not isinstance(cfgs, list) or not cfgs:
            return "configurations vacía o no es una lista"
        seen = set()
        for c in cfgs:
            if not isinstance(c, dict) or set(c) != {"config_id", "evidence_class"}:
                return "configuración mal formada"
            if not valid_config_id(c["config_id"]) or c["evidence_class"] not in EVIDENCE_CLASSES:
                return "config_id o clase de evidencia no válidos"
            if c["config_id"] in seen:
                return "config_id repetido"
            seen.add(c["config_id"])
        classes = [c["evidence_class"] for c in cfgs]
        if "CONSERVATIVE_BOUND" in classes and r["execution_status"] != "UNKNOWN":
            return "una cota conservadora exige ejecución desconocida"
        if r["execution_status"] == "DOCUMENTED_NOT_EXECUTED" and any(c != "DOCUMENTED_NOT_EVALUATED" for c in classes):
            return "ejecución documentada como no realizada con configuraciones contadas"
        ev = r["evidence"]
        if not isinstance(ev, list) or not ev or not all(_evidence_ref_ok(x) for x in ev):
            return "evidencia documental vacía o mal formada"
        prev = effective.get(eid)
        if prev is None:
            if r["supersedes"] is not None:
                return "supersedes debe ser null en la primera procedencia"
        else:
            if r["supersedes"] != prev["provenance_id"]:
                return "supersedes no apunta a la procedencia vigente"
            new_cls = {c["config_id"]: c["evidence_class"] for c in cfgs}
            for c in prev["configurations"]:     # una reducción solo pasa a DOCUMENTED_NOT_EVALUATED,
                if c["config_id"] not in new_cls:  # con evidencia y decisión; nada desaparece (B.2.4)
                    return f"la configuración {c['config_id']} desaparece (debe conservarse)"
        n = classes.count("DOCUMENTED_EVALUATED")
        m = classes.count("CONSERVATIVE_BOUND")
        return self._provenance_decision_error(r["decision_ref"], eid, n, m)

    def _provenance_decision_error(self, ref, eid: str, n: int, m: int) -> str | None:
        text, why = self._decision_text(ref)
        if why:
            return why
        wanted = (eid, str(n), str(m))
        for line in text.splitlines():
            mt = _PROVENANCE_AUTH.fullmatch(line.rstrip())
            if mt and mt.groups() == wanted:
                return None
        return f"la decisión no cita exactamente la línea «AUTORIZA: PROCEDENCIA {eid} DOCUMENTADAS={n} COTA={m}»"

    def informed_by_error(self, value, records_before: list[dict]) -> str | None:
        """`informed_by` (R2): lista de referencias verificables y anteriores. None = válido."""
        if not isinstance(value, list):
            return "informed_by debe ser una lista"
        pairs = {(r.get("experiment_id"), r.get("config_id")) for r in records_before
                 if isinstance(r, dict) and r.get("kind") == "CONFIGURATION_EVALUATED"}
        pids = {r.get("provenance_id") for r in records_before
                if isinstance(r, dict) and r.get("kind") == "ANTECEDENT_PROVENANCE"}
        seen = []
        for ref in value:
            if isinstance(ref, dict) and set(ref) == {"experiment_id", "config_id"}:
                if (ref["experiment_id"], ref["config_id"]) not in pairs:
                    return f"referencia inexistente o posterior: {ref!r}"
            elif isinstance(ref, dict) and set(ref) == {"provenance_id"}:
                if ref["provenance_id"] not in pids:
                    return f"procedencia inexistente o posterior: {ref!r}"
            else:
                return f"referencia mal formada: {ref!r}"
            if ref in seen:
                return f"referencia repetida: {ref!r}"
            seen.append(ref)
        return None

    # --- escritura (append-only) -----------------------------------------------------------
    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_name(self.path.name + ".lock"), "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def _write(self, rec: dict) -> dict:
        """Escribe un registro; el llamador debe tener el bloqueo (`_locked`)."""
        rec = {"at_utc": self._now(), **rec}
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return rec

    def _append(self, rec: dict) -> dict:
        with self._locked():
            return self._write(rec)

    def append_deviation(self, build) -> dict:
        """Registro DEVIATION (ORQ-017-01). `build()` se ejecuta DENTRO del bloqueo exclusivo,
        el mismo de `claim_partition`: la exposición y la validación que calcula se basan en el
        estado del registro que precede inmediatamente a la escritura (cronología por orden del
        archivo). Si `build()` falla, no se escribe nada. Si la escritura falla una vez iniciada,
        lanza PersistenceUncertainError: el registro puede haber quedado escrito."""
        with self._locked():
            rec = build()
            if not isinstance(rec, dict) or rec.get("kind") != "DEVIATION":
                raise ExperimentError("append_deviation solo escribe registros DEVIATION")
            try:
                return self._write(rec)
            except BaseException as exc:
                raise PersistenceUncertainError(
                    f"escritura de DEVIATION {rec.get('deviation_id')} incierta: {exc!r}") from exc

    def create(self, experiment_id: str, title: str, actor: str) -> dict:
        if not valid_experiment_id(experiment_id):
            raise ExperimentError(f"identificador no válido: {experiment_id!r} (formato EXP-NNNN)")
        if experiment_id in self.experiments():
            raise ExperimentError(f"{experiment_id} ya existe: los IDs no se reutilizan")
        return self._append({"kind": "CREATED", "experiment_id": experiment_id, "title": title,
                             "state": "IDEA", "actor": actor})

    def register_antecedent(self, experiment_id: str, title: str, state: str, source: str, note: str) -> dict:
        """Antecedente declarado por el propietario fuera del registro (p. ej. EXP-0001)."""
        if experiment_id in self.experiments():
            raise ExperimentError(f"{experiment_id} ya existe")
        if state not in ANTECEDENT_STATES:
            raise ExperimentError(f"estado de antecedente no permitido: {state} (solo {ANTECEDENT_STATES})")
        return self._append({"kind": "ANTECEDENT", "experiment_id": experiment_id, "title": title,
                             "state": state, "origin": DECLARED_ANTECEDENT, "source": source,
                             "note": note, "actor": OWNER})

    def decision_ok(self, ref: str | None, experiment_id: str, partition: str | None = None,
                    snapshot_id: str | None = None, *, target_state: str | None = None) -> str | None:
        """None si la decisión autoriza exactamente lo pedido; si no, el motivo (QA3-04, QA3R2-04).
        Transición: `target_state` y la línea `AUTORIZA: <exp> <estado>`. Partición: `partition`
        y `snapshot_id` y la línea `AUTORIZA: <exp> <partición> <snapshot>`. Uno de los dos, no ambos."""
        if not valid_experiment_id(experiment_id):
            return f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)"
        if (partition is None) != (snapshot_id is None):
            return "la autorización de partición exige partición y snapshot"
        if (target_state is None) == (partition is None):
            return "la autorización es de una transición (estado destino) o de una partición, no ambas"
        if target_state is not None and target_state not in OWNER_DECIDED:
            return f"estado destino no válido para una decisión del propietario: {target_state!r}"
        if partition is not None:
            if partition not in SEALED:
                return f"partición no válida: {partition!r}"
            if not _valid_snapshot_id(snapshot_id):
                return f"snapshot no válida: {snapshot_id!r}"
        text, why = self._decision_text(ref)
        if why:
            return why
        wanted = (experiment_id, target_state, None) if target_state is not None \
            else (experiment_id, partition, snapshot_id)
        if wanted not in authorizations(text):
            line = " ".join(x for x in wanted if x is not None)
            return f"la decisión no cita exactamente la línea «AUTORIZA: {line}»"
        return None

    def _decision_text(self, ref) -> tuple[str | None, str | None]:
        """(texto, None) o (None, motivo). Reglas de QA3-04/QA3R2-04: nombre DEC-NNN…md sin ruta,
        dentro de docs/decisions, sin enlace simbólico, legible en UTF-8."""
        if not isinstance(ref, str) or not _DECISION_NAME.fullmatch(ref):
            return None, "decision_ref debe ser un nombre DEC-NNN…md sin ruta"
        path = self.decisions_dir / ref
        if path.is_symlink() or not path.is_file():
            return None, "la decisión citada no existe en docs/decisions"
        if path.resolve().parent != self.decisions_dir.resolve():
            return None, "la decisión está fuera de docs/decisions"
        try:
            return path.read_text(encoding="utf-8"), None
        except (OSError, UnicodeDecodeError) as exc:
            return None, f"la decisión no se puede leer: {exc!r}"

    def transition(self, experiment_id: str, to: str, *, actor: str, evidence: dict | None = None,
                   reason: str = "") -> dict:
        evidence = evidence or {}
        with self._locked():          # CR-020: la congelación y la selección se validan contra el registro
            records = self.records()  # en el mismo bloqueo en que se escribe la transición
            exps = self._experiments_from(records)
            if experiment_id not in exps:
                raise ExperimentError(f"{experiment_id} no existe")
            e = exps[experiment_id]
            if e["origin"] == DECLARED_ANTECEDENT:
                raise ExperimentError("un antecedente declarado no avanza en el registro")
            cur = e["state"]
            if cur in TERMINAL:
                raise ExperimentError(f"{experiment_id} está en {cur} (terminal)")
            if to not in STATES:
                raise ExperimentError(f"estado desconocido: {to}")
            allowed = {_FORWARD.get(cur)} | {"REJECTED", "INCONCLUSIVE"}
            if cur == "HUMAN_REVIEW":
                allowed |= {"APPROVED"}
            if to not in allowed:
                raise ExperimentError(f"transición no permitida: {cur} → {to}")
            for key in _REQUIRES.get(to, ()):
                if not evidence.get(key):
                    raise ExperimentError(f"{cur} → {to} exige la evidencia «{key}»")
            if to == "PREREGISTERED" and evidence.get("min_history_ok") is not True:
                raise ExperimentError("histórico insuficiente: el experimento no pasa de DESIGN (TC-ML-014)")
            if to in ("APPROVED", "OOS_EVALUATION") or (cur == "HUMAN_REVIEW" and to in TERMINAL):
                if actor != OWNER:
                    raise ExperimentError(f"{to} solo lo decide el propietario (REQ-G-107)")
                why = self.decision_ok(evidence.get("decision_ref"), experiment_id, target_state=to)
                if why:
                    raise ExperimentError(why)
            if to == "PREREGISTERED":
                self._check_freeze_accounting(records, experiment_id, evidence)
            if to == "OOS_EVALUATION":
                self._check_selection(records, experiment_id, evidence)
            return self._write({"kind": "TRANSITION", "experiment_id": experiment_id, "from": cur, "to": to,
                                "actor": actor, "evidence": evidence, "reason": reason})

    def _check_freeze_accounting(self, records: list[dict], experiment_id: str, evidence: dict) -> None:
        """CR-020 §C.3.3: `trials_accounting` debe coincidir con el recalculado en este momento."""
        acc = evidence.get("trials_accounting")
        why = accounting_shape_error(acc)
        if why:
            raise TrialsAccountingError(f"PREREGISTERED exige un «trials_accounting» válido: {why}")
        expected = self.trials_accounting(experiment_id, acc["planned_config_ids"], records=records)
        if expected != acc:
            raise TrialsAccountingError(f"TRIALS_COUNT_INCONSISTENT: el conteo declarado {acc} no coincide con el "
                                        f"reconstruido desde el registro {expected}")

    def _check_selection(self, records: list[dict], experiment_id: str, evidence: dict) -> None:
        """CR-020 §C.3.4, R2: registro de la selección de candidata en la transición a OOS_EVALUATION."""
        cfg = evidence.get("selected_config_id")
        if not valid_config_id(cfg):
            raise ExperimentError("OOS_EVALUATION exige «selected_config_id» válido (CR-020 §C.3.4)")
        acc = self.accounting(records=records)
        if (experiment_id, cfg) not in acc["pairs"]:
            raise ExperimentError(f"la configuración seleccionada {cfg} no tiene un inicio de evaluación registrado")
        sha = evidence.get("selection_inputs_sha256")
        if not isinstance(sha, str) or not _HEX64.fullmatch(sha):
            raise ExperimentError("OOS_EVALUATION exige «selection_inputs_sha256» (SHA-256 en hexadecimal)")
        if "informed_by" not in evidence:
            raise ExperimentError("OOS_EVALUATION exige «informed_by» (R2; puede estar vacío)")
        why = self.informed_by_error(evidence["informed_by"], records)
        if why:
            raise ExperimentError(f"informed_by no verificable: {why}")

    # --- procedencia de antecedentes (CR-020 §C.3.1) -------------------------------------------
    def register_provenance(self, experiment_id: str, *, documentary_status: str, execution_status: str,
                            configurations: list[dict], evidence: list[str], decision_ref: str,
                            supersedes: str | None) -> dict:
        """Registro ANTECEDENT_PROVENANCE append-only, validado dentro del bloqueo. No cambia el
        estado original del antecedente. Solo lo registra el propietario, con su decisión."""
        rec = {"kind": "ANTECEDENT_PROVENANCE", "provenance_id": uuid.uuid4().hex, "experiment_id": experiment_id,
               "documentary_status": documentary_status, "execution_status": execution_status,
               "configurations": configurations, "evidence": evidence, "decision_ref": decision_ref,
               "supersedes": supersedes, "actor": OWNER}
        try:
            json.dumps(rec, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ExperimentError(f"procedencia no serializable: {exc!r}") from exc
        with self._locked():
            acc = self.accounting(require_complete=False)     # valida todo lo existente (Fail-Closed)
            antecedents = {e for e, x in self.experiments().items() if x["origin"] == DECLARED_ANTECEDENT}
            all_pids = {p["provenance_id"] for h in acc["provenance_history"].values() for p in h}
            why = self._provenance_error(rec, antecedents, acc["provenance"], all_pids)
            if why:
                raise ExperimentError(f"procedencia rechazada: {why}")
            return self._write(rec)

    # --- inicio de evaluación de una configuración (CR-020 §C.3.2) ------------------------------
    def begin_configuration_evaluation(self, experiment_id: str, config_id: str, *, actor: str,
                                       deviation_builder=None) -> dict:
        """Registra de forma duradera el inicio autorizado de la evaluación de un par ANTES de
        evaluar. Validaciones previas fallidas → EvaluationRequestRejected (nada escrito, no
        cuenta). Escritura fallida o incierta → PersistenceUncertainError: la evaluación no
        empieza. Idempotente. Una configuración no planificada exige `deviation_builder`, que
        construye el registro DEVIATION (preregistration.begin_evaluation); se escribe en el
        mismo bloqueo, después del registro de evaluación."""
        if not valid_experiment_id(experiment_id):
            raise EvaluationRequestRejected(f"experimento no válido: {experiment_id!r} (formato EXP-NNNN)")
        if not valid_config_id(config_id):
            raise EvaluationRequestRejected(f"config_id no válido: {config_id!r}")
        if not isinstance(actor, str) or not actor.strip():
            raise EvaluationRequestRejected("la solicitud exige un actor")
        with self._locked():
            try:
                records = self.records()
                exps = self._experiments_from(records)
                acc = self.accounting(records=records)
            except Exception as exc:
                raise EvaluationRequestRejected(f"registro ilegible, corrupto o incoherente: {exc!r}") from exc
            e = exps.get(experiment_id)
            if e is None or e["origin"] != REGISTRY_ORIGIN:
                raise EvaluationRequestRejected(f"{experiment_id} no es un experimento nativo registrado")
            if e["state"] not in EVALUATION_STATES:
                raise EvaluationRequestRejected(
                    f"{experiment_id} está en {e['state']}: el contrato vigente solo permite evaluar configuraciones "
                    f"en {EVALUATION_STATES} (un estado no terminal no basta; DEC-021)")
            pre = [h for h in e["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"]
            pacc = (pre[-1].get("evidence") or {}).get("trials_accounting") if len(pre) == 1 else None
            if len(pre) != 1 or accounting_shape_error(pacc):
                raise EvaluationRequestRejected(f"{experiment_id}: sin congelación válida con «trials_accounting»")
            sha = pre[0]["evidence"].get("preregistration_sha256")
            planned = config_id in pacc["planned_config_ids"]
            if not planned and deviation_builder is None:
                raise EvaluationRequestRejected(
                    f"{config_id} no está planificada: solo puede evaluarse registrando la desviación "
                    "(preregistration.begin_evaluation)")
            existing = next((r for r in records if r.get("kind") == "CONFIGURATION_EVALUATED"
                             and r.get("experiment_id") == experiment_id and r.get("config_id") == config_id), None)
            rec = existing
            if existing is None:
                try:
                    rec = self._write({"kind": "CONFIGURATION_EVALUATED", "experiment_id": experiment_id,
                                       "config_id": config_id, "preregistration_sha256": sha,
                                       "partition": "train_val", "actor": actor})
                except BaseException as exc:
                    raise PersistenceUncertainError(
                        f"escritura de CONFIGURATION_EVALUATED {experiment_id}/{config_id} incierta: {exc!r}; "
                        "la evaluación no empieza") from exc
            if not planned and not any(r.get("kind") == "DEVIATION" and r.get("experiment_id") == experiment_id
                                       and r.get("config_id") == config_id for r in records):
                dev = deviation_builder()
                if not isinstance(dev, dict) or dev.get("kind") != "DEVIATION" or dev.get("config_id") != config_id:
                    raise ExperimentError("el constructor no devolvió la DEVIATION de esta configuración; "
                                          "la evaluación no empieza")
                try:
                    self._write(dev)
                except BaseException as exc:
                    raise PersistenceUncertainError(
                        f"escritura de DEVIATION {dev.get('deviation_id')} incierta: {exc!r}; "
                        "la evaluación no empieza") from exc
            try:                                                   # relectura: solo así se confirma
                again = self.records()
            except Exception as exc:
                raise PersistenceUncertainError(f"relectura fallida tras escribir: {exc!r}; "
                                                "la evaluación no empieza") from exc
            if not any(r.get("kind") == "CONFIGURATION_EVALUATED" and r.get("experiment_id") == experiment_id
                       and r.get("config_id") == config_id for r in again):
                raise PersistenceUncertainError(f"{experiment_id}/{config_id} no consta tras escribir; "
                                                "la evaluación no empieza")
            return rec

    def evaluation_recorded(self, experiment_id: str, config_id: str) -> bool:
        """Relectura sin validar: ¿hay una línea de inicio de evaluación del par? Solo diagnóstico;
        no autoriza nada. El acceso a datos exige `accounting()["pairs"]` (A2)."""
        return any(r.get("kind") == "CONFIGURATION_EVALUATED" and r.get("experiment_id") == experiment_id
                   and r.get("config_id") == config_id for r in self.records())


def _evaluation_record_error(r: dict, natives: set) -> str | None:
    for k in ("experiment_id", "config_id", "preregistration_sha256", "partition", "actor"):
        if k not in r:
            return f"falta {k}"
    if not valid_experiment_id(r["experiment_id"]) or r["experiment_id"] not in natives:
        return "experimento no nativo o no registrado antes"
    if not valid_config_id(r["config_id"]):
        return "config_id no válido"
    if not isinstance(r["preregistration_sha256"], str) or not r["preregistration_sha256"]:
        return "preregistration_sha256 no válido"
    if r["partition"] != "train_val":
        return "partición no válida"
    if not isinstance(r["actor"], str) or not r["actor"].strip():
        return "sin actor"
    return None
