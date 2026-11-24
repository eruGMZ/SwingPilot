"""Conciliación del conteo de pruebas para el evaluador (FEAT-017; CR-020 §C.4; DEC-021;
REQ-G-P17, REQ-G-103; TC-ML-022, TC-ML-024).

Determinista, sin LLM ni juicio no reproducible: todo sale del registro de experimentos, del
preregistro congelado vinculado por su SHA-256 y del archivo de resultados de Train+Val de X
(`selection_inputs`, verificado por `selection_inputs_sha256`).

Formato del archivo de resultados (JSON): {"experiment_id": X, "results": {config_id: {métrica: valor}}};
debe contener exactamente los pares evaluados de X.

Resultado: {"ok": bool, "reasons": [...], "N_pre", "N_eval", "breakdown", "trials_live",
"trials_after_freeze", "relevant", "undetermined"}. Cualquier evidencia ausente, incoherente o
insuficiente → ok = False (el evaluador devuelve INCONCLUSIVE). La ausencia de registros de
decisión no prueba que no hubiera decisiones relevantes (B.4.4): las decisiones tomadas fuera
del registro no son detectables por medios deterministas (riesgo residual de ORQ-017-01).
"""
import hashlib
import json

from .experiments import ExperimentRegistry, accounting_shape_error
from .preregistration import PreregistrationError, apply_selection_rule, confirmatory_status, parse_selection_rule

TRIALS_COUNT_INCONSISTENT = "TRIALS_COUNT_INCONSISTENT"
SUBSEQUENT_UNDETERMINED = "SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED"


def _fail(out: dict, code: str, msg: str) -> dict:
    out["ok"] = False
    out["reasons"].append(f"{code}: {msg} (Fail-Closed, CR-020)")
    return out


def reconcile(registry, frozen, selection_inputs: bytes | None) -> dict:
    out = {"ok": True, "reasons": [], "N_pre": None, "N_eval": None, "breakdown": None, "trials_live": None,
           "trials_after_freeze": [], "relevant": [], "undetermined": []}
    if not isinstance(registry, ExperimentRegistry):
        return _fail(out, "REGISTRY_MISSING", "se requiere el registro de experimentos")
    try:
        records = registry.records()
    except Exception as exc:
        return _fail(out, "REGISTRY_UNREADABLE", f"registro ilegible o corrupto: {exc!r}")
    try:
        frozen.verify()
        eid = frozen.experiment_id
    except Exception as exc:
        return _fail(out, "PREREGISTRATION_ALTERED", f"preregistro alterado o ausente: {exc!r}")

    # 1. Conteo congelado (C.4.1)
    pre_idx = [i for i, r in enumerate(records) if r.get("kind") == "TRANSITION" and r.get("experiment_id") == eid
               and r.get("to") == "PREREGISTERED"]
    if len(pre_idx) != 1:
        return _fail(out, TRIALS_COUNT_INCONSISTENT, f"{eid} no tiene exactamente una congelación")
    ev_pre = records[pre_idx[0]].get("evidence") or {}
    if ev_pre.get("preregistration_sha256") != frozen.sha256:
        return _fail(out, "PREREGISTRATION_HASH_MISMATCH", "el SHA-256 no coincide con el de PREREGISTERED")
    acc = ev_pre.get("trials_accounting")
    if accounting_shape_error(acc):
        return _fail(out, TRIALS_COUNT_INCONSISTENT, f"trials_accounting ausente o mal formado: {accounting_shape_error(acc)}")
    if frozen.content.get("trials_count") != acc:
        return _fail(out, TRIALS_COUNT_INCONSISTENT, "trials_count del preregistro ≠ trials_accounting congelado")
    try:
        rebuilt = registry.trials_accounting(eid, acc["planned_config_ids"], upto=pre_idx[0], records=records)
        full = registry.accounting(records=records)
    except Exception as exc:
        return _fail(out, TRIALS_COUNT_INCONSISTENT, f"conteo no reconstruible: {exc!r}")
    if rebuilt != acc:
        return _fail(out, TRIALS_COUNT_INCONSISTENT, f"conteo congelado {acc} ≠ reconstruido {rebuilt}")
    out["N_pre"] = acc["N_pre"]
    out["breakdown"] = {k: acc[k] for k in ("H_doc", "H_bound", "E", "planned_new")}
    out["breakdown"]["H_bound_is_bound"] = True                   # la cota se informa como cota
    out["trials_live"] = full["H_doc"] + full["H_bound"] + full["E"]

    # 2. Carácter confirmatorio (desviaciones, reglas vigentes + REQ-G-103 v1.8)
    try:
        st = confirmatory_status(registry, eid)
    except PreregistrationError as exc:
        return _fail(out, "DEVIATIONS_INCOHERENT", str(exc))
    if not st["confirmatory"]:
        return _fail(out, "NOT_CONFIRMATORY", f"desviaciones de diseño tras la exposición: "
                                              f"{st['design_deviations_after_oos']}")
    planned = set(acc["planned_config_ids"])
    x_pairs = {c for (e, c) in full["pairs"] if e == eid}
    unplanned = sorted(x_pairs - planned)
    if unplanned:
        return _fail(out, "UNPLANNED_CONFIGURATION", f"configuraciones no planificadas evaluadas {unplanned}: "
                                                     "el experimento dejó de ser confirmatorio")

    # 3. Selección de candidata reproducible (C.3.4; evidencia 3)
    oos = [(i, r) for i, r in enumerate(records) if r.get("kind") == "TRANSITION" and r.get("experiment_id") == eid
           and r.get("to") == "OOS_EVALUATION"]
    if len(oos) != 1:
        return _fail(out, "SELECTION_MISSING", "falta el registro de selección de candidata")
    sel_idx, sel = oos[0]
    sev = sel.get("evidence") or {}
    selected, sha_in, ib = sev.get("selected_config_id"), sev.get("selection_inputs_sha256"), sev.get("informed_by")
    if not isinstance(selected, str) or not isinstance(sha_in, str) or not isinstance(ib, list):
        return _fail(out, "SELECTION_MISSING", "selección sin config, hash de resultados o informed_by")
    if registry.informed_by_error(ib, records[:sel_idx]):
        return _fail(out, "INFORMED_BY_UNVERIFIABLE", "informed_by de la selección no verificable")
    if not isinstance(selection_inputs, (bytes, bytearray)) or hashlib.sha256(selection_inputs).hexdigest() != sha_in:
        return _fail(out, "SELECTION_INPUTS_UNVERIFIABLE", "archivo de resultados ausente o con hash distinto")
    try:
        doc = json.loads(bytes(selection_inputs).decode("utf-8"))
        results = doc["results"]
        if doc.get("experiment_id") != eid or not isinstance(results, dict) or set(results) != x_pairs:
            raise ValueError("los resultados no corresponden exactamente a los pares evaluados de X")
        rule = parse_selection_rule(frozen.content["candidate_selection_rule"], acc["planned_config_ids"],
                                    frozen.content.get("metrics"))
        expected = apply_selection_rule(rule, results)
    except Exception as exc:
        return _fail(out, "SELECTION_NOT_REPRODUCIBLE", f"{exc!r}")
    if expected != selected:
        return _fail(out, "SELECTION_RULE_VIOLATION", f"seleccionada {selected}, la regla congelada da {expected}: "
                                                     "desviación; el experimento dejó de ser confirmatorio")

    # 4. Pruebas posteriores a la congelación (C.4.2)
    points = [(sel_idx, "SELECTION", ib)]
    for i, r in enumerate(records):
        if r.get("kind") == "DEVIATION" and r.get("experiment_id") == eid:
            points.append((i, "DEVIATION", r.get("informed_by") if "informed_by" in r else None))
    relevant = set()
    for (e, c), t_idx in sorted(full["pairs"].items(), key=lambda kv: kv[1]):
        if e == eid or t_idx < pre_idx[0]:
            continue
        out["trials_after_freeze"].append({"experiment_id": e, "config_id": c})
        later = [p for p in points if p[0] > t_idx]
        ref = {"experiment_id": e, "config_id": c}
        if any(p[2] is None for p in later):
            out["undetermined"].append(ref)                       # informed_by ausente (histórico o no)
        elif any(p[1] == "DEVIATION" and ref not in p[2] for p in later):
            out["undetermined"].append(ref)                       # decisión no reproducible que no cita T
        elif any(ref in p[2] for p in later):
            relevant.add((e, c))
    if out["undetermined"]:
        return _fail(out, SUBSEQUENT_UNDETERMINED, f"influencia indeterminable de {out['undetermined']}")
    out["relevant"] = [{"experiment_id": e, "config_id": c} for e, c in sorted(relevant)]
    out["N_eval"] = out["N_pre"] + len(relevant)                  # N_pre se conserva y se informa
    return out
