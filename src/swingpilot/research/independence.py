"""Independencia prospectiva, comprobaciones V1–V8 por etapa y clasificación de elegibilidad
(CR-023 §C.9, §D.3, §D.4, §D.8; bloque B4).

Solo lectura y sin Git: no escribe en el registro ni en el almacén, no lee datos de mercado, no consume
particiones y no abre el acceso final (`_FINAL_ACCESS_BLOCKED_UNTIL_B6` sigue vigente en `partitions.py`).
Clasificación C2: *metodológica* (`METHOD`) frente a *técnica* (`TECH`, Fail-Closed). Cualquier
excepción inesperada es técnica. La parte documental de V6/V7 solo comprueba existencia y sintaxis de
la referencia (§C.9); su validez la acredita el propietario.
"""
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from . import boundary as B
from . import snapshot as S
from .experiments import valid_experiment_id
from .prereg_store import PreregStoreError
from .preregistration import (PreregistrationError, _deviation_shape_error, _preregistered_sha, _read, _replay,
                              confirmatory_status)

INDEPENDENT, CONTAMINATED, INDETERMINATE = "INDEPENDENT_AS_DECLARED", "CONTAMINATED", "INDETERMINATE"
ELIGIBLE, NOT_ELIGIBLE, UNDETERMINABLE = "ELIGIBLE", "NOT_ELIGIBLE", "UNDETERMINABLE"
OK, NA, METHOD, TECH = "OK", "NA", "METHOD", "TECH"

_HEX, _I, _D = r"[0-9a-f]{64}", r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", r"[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00Z"
_FRONTERA = re.compile(rf"AUTORIZA: FRONTERA (EXP-[0-9]{{4}}) SHA256=({_HEX}) B=({_D})", re.ASCII)
_PUBLICACION = re.compile(rf"AUTORIZA: PUBLICACION (EXP-[0-9]{{4}}) SHA256=({_HEX}) B=({_D}) "
                          rf"P=({_I}|NONE) RESULTADO=(VALIDA|INVALIDA)", re.ASCII)
_DEC_REF = re.compile(r"DEC-[0-9]{3}_[A-Za-z0-9_.-]+\.md", re.ASCII)

# Matriz de §C.9 (R = requerida). "V4pre"/"V4post" por etapa (C1); "V1b" = V1 completa (publicación), "V1a" = cita del hash.
STAGES = {
    "ET-1": ("V2", "V7m"),
    "ET-2": ("V1a", "V2", "V3", "V8"),
    "ET-3": ("V1b",),
    "ET-4": ("V1b", "V2", "V3", "V4pre", "V8"),
    "ET-5": ("V1b", "V2", "V3", "V4pre", "V5", "V6", "V7m", "V7d", "V8"),
    "ET-6": ("V2", "V3", "V4pre", "V5", "V8"),
    "ET-7": ("V2", "V3", "V4post", "V5", "V8"),
    "ET-8": ("V1b", "V2", "V3", "V4post", "V5", "V6", "V7m", "V7d", "V8"),
    "ET-9": ("V2", "V3", "V4post", "V5", "V8"),
    "ET-10": ("V2", "V3", "V4post", "V5", "V8"),
}
_LIBERACION = re.compile(rf"AUTORIZA: LIBERACION (EXP-[0-9]{{4}}/(?:OOS|LOCKBOX)) SHA256=({_HEX})", re.ASCII)
_REINTENTO = re.compile(rf"AUTORIZA: REINTENTO (EXP-[0-9]{{4}}/LOCKBOX) EVIDENCIA=({_HEX})", re.ASCII)
_DISPOSICION = re.compile(r"AUTORIZA: DISPOSICION (EXP-[0-9]{4}/LOCKBOX) INCONCLUSIVE", re.ASCII)


class _Fail(Exception):
    def __init__(self, nature: str, why: str):
        super().__init__(why)
        self.nature, self.why = nature, why


def _tech(why):
    raise _Fail(TECH, why)


def _meth(why):
    raise _Fail(METHOD, why)


# --- contexto del experimento (solo lectura) ---------------------------------------------------------

def _context(registry, store, eid) -> dict:
    """PREREGISTERED, contenido verificado en el almacén (V2) y frontera confirmatoria. TECH si falla."""
    try:
        records, exps = _read(registry)
        sha = _preregistered_sha(registry, eid)
        pre = [h for h in exps[eid]["history"] if h.get("kind") == "TRANSITION" and h.get("to") == "PREREGISTERED"][0]
        if store is None:
            _tech("sin almacén de preregistros")
        content = store.verify_cited(eid, sha)
    except _Fail:
        raise
    except PreregStoreError as exc:
        _tech(f"V2: contenido del preregistro no recuperable o con hash distinto: {exc}")
    except Exception as exc:
        _tech(f"registro o almacén ilegible, corrupto o incoherente: {exc!r}")
    ib = content.get("independence_boundary")
    if content.get("experiment_id") != eid or B.boundary_class(ib) != B.CONFIRMATORY or B.boundary_error(ib):
        _tech("independence_boundary ausente, mal formado o no confirmatorio")
    cls = (pre.get("evidence") or {}).get("independence_class")
    if cls != B.CONFIRMATORY:
        _tech("la clase de independencia congelada no es CONFIRMATORY")
    return {"records": records, "sha": sha, "content": content, "ib": ib, "pre_at": pre.get("at_utc")}


def _check_manifest(ctx, eid, manifest, window_id=None) -> None:
    """V5 (parte mecánica, sobre el manifiesto en memoria; la verificación física de archivos es de B6)."""
    if not isinstance(manifest, dict):
        _tech("V5: manifiesto de evaluación ausente")
    try:
        S.validate_manifest(manifest)
    except Exception as exc:
        _tech(f"V5: manifiesto no válido: {exc}")
    wins, wid = B.windows(ctx["ib"], eid), manifest.get("window_id")
    snap = ctx["content"]["snapshot"]
    if manifest.get("kind") != S.KIND_EVALUATION or wid not in wins or (window_id and wid != window_id):
        _tech("V5: kind o window_id del manifiesto incoherentes con el preregistro")
    start, end = wins[wid]
    if (manifest["window"]["start_ms"], manifest["window"]["end_exclusive_ms"]) != (B.to_ms(start), B.to_ms(end)):
        _tech("V5: los límites de la ventana del manifiesto no son los del preregistro")
    dev = manifest["development_snapshot"]
    if (dev["snapshot_id"], dev["train_val_sha256"]) != (snap["snapshot_id"], snap["train_val_sha256"]) \
            or manifest["d_dev"] != snap["d_dev"]:
        _tech("V5: la snapshot de desarrollo o D_dev del manifiesto no coinciden con el preregistro")


# --- independence_status (D.4) -----------------------------------------------------------------------

def independence_assessment(registry, store, experiment_id: str, *, manifest: dict | None = None) -> tuple[str, str]:
    """(estado, motivo). Función común de §D.4; sin efectos. Fail-Closed: todo fallo → INDETERMINATE."""
    try:
        ctx = _context(registry, store, experiment_id)
        _replay(registry, experiment_id)              # valida todas las DEVIATION (forma, cronología, hash)
        if manifest is not None:
            _check_manifest(ctx, experiment_id, manifest)
        own = list(B.windows(ctx["ib"], experiment_id).values())
        for r in ctx["records"]:
            if isinstance(r, dict) and r.get("kind") == "DEVIATION" and r.get("field") == "independence_boundary":
                ws = B.windows(r["old"], r["experiment_id"])
                for wid in r["new"]["contaminated_window_ids"]:
                    s, e = ws[wid]
                    if any(s < oe and os_ < e for os_, oe in own):
                        return CONTAMINATED, f"DEVIATION {r['deviation_id']} contamina {wid}"
        return INDEPENDENT, ""
    except _Fail as f:
        return INDETERMINATE, f.why
    except Exception as exc:
        return INDETERMINATE, f"fallo de evidencia: {exc!r}"


def independence_status(registry, store, experiment_id: str, *, manifest: dict | None = None) -> str:
    return independence_assessment(registry, store, experiment_id, manifest=manifest)[0]


# --- autorizaciones documentales del propietario (B5: C.7.3 y C.6.5) ---------------------------------

def owner_lines(decisions_dir, kind: str, rx, eid: str) -> list[tuple]:
    """Grupos de las líneas `AUTORIZA: <kind> ...` de `DEC-*.md` que nombran al experimento. Gramática
    estricta (`fullmatch`, ASCII); una línea que lo nombra y no la cumple → TECH (sin reparación)."""
    out = []
    try:
        for path in sorted(Path(decisions_dir).glob("DEC-*.md")):
            for line in path.read_bytes().decode("utf-8").split("\n"):
                if not line.strip().startswith(f"AUTORIZA: {kind}"):
                    continue
                m = rx.fullmatch(line)
                if m and m.group(1).split("/")[0] == eid:
                    out.append(m.groups())
                elif not m and eid in line:
                    _tech(f"{kind}: línea mal formada en {path.name}")
    except _Fail:
        raise
    except Exception as exc:
        _tech(f"{kind}: documentos de decisión ilegibles: {exc!r}")
    return out


def released_windows(decisions_dir, eid: str, sha: str) -> set[str]:
    """Ventanas liberadas por el propietario (C.7.3). La línea debe citar el SHA-256 del preregistro
    congelado; una liberación con otro hash → TECH. Una ventana liberada nunca vuelve a evaluarse."""
    rel = owner_lines(decisions_dir, "LIBERACION", _LIBERACION, eid)
    if any(h != sha for _, h in rel):
        _tech("LIBERACION: el SHA-256 citado no es el del preregistro congelado")
    return {w for w, _ in rel}


# --- V1: declaración de frontera y atestación de publicación -----------------------------------------

def _decision_lines(decisions_dir, eid, with_pub=True) -> tuple[list, list]:
    """Líneas FRONTERA/PUBLICACION del experimento en todo `DEC-*.md`. Una línea que lo nombra y no
    cumple la gramática estricta → TECH (sin reparación)."""
    front, pub = [], []
    try:
        for path in sorted(Path(decisions_dir).glob("DEC-*.md")):
            for line in path.read_bytes().decode("utf-8").split("\n"):
                for kind, rx, out in (("FRONTERA", _FRONTERA, front), ("PUBLICACION", _PUBLICACION, pub)):
                    if kind == "PUBLICACION" and not with_pub:    # ET-2 solo exige la cita del SHA-256
                        continue
                    if line.strip().startswith(f"AUTORIZA: {kind}"):
                        m = rx.fullmatch(line)
                        if m:
                            if m.group(1) == eid:
                                out.append(m.groups())
                        elif eid in line:
                            _tech(f"V1: línea {kind} mal formada en {path.name}")
    except _Fail:
        raise
    except Exception as exc:
        _tech(f"V1: documentos de decisión ilegibles: {exc!r}")
    return front, pub


def _v1(ctx, eid, decisions_dir, full) -> None:
    front, pub = _decision_lines(decisions_dir, eid, full)
    if len(front) != 1:
        _tech(f"V1: se exige exactamente una línea FRONTERA de {eid} (hay {len(front)})")
    _, fsha, fb = front[0]
    if fsha != ctx["sha"] or fb != ctx["ib"]["B"]:
        _tech("V1: la declaración de frontera no coincide con el SHA-256 o con B del preregistro")
    if not full:
        return
    if len(pub) != 1:
        _tech(f"V1: se exige exactamente una atestación PUBLICACION de {eid} (hay {len(pub)})")
    _, psha, pb, p, res = pub[0]
    if (psha, pb) != (fsha, fb):
        _tech("V1: la atestación de publicación no coincide con la declaración de frontera")
    b = B.parse_midnight(fb)
    if p == "NONE":
        if res != "INVALIDA":
            _tech("V1: P=NONE con RESULTADO=VALIDA es incoherente")
        _meth("V1: el propietario atestigua que la publicación nunca ocurrió")
    pt = B.parse_instant(p)
    if pt is None or B.parse_instant(ctx["pre_at"]) is None or pt < B.parse_instant(ctx["pre_at"]):
        _tech("V1: P ausente, mal formado o anterior a PREREGISTERED")
    ok = pt + timedelta(hours=24) <= b
    if res == "VALIDA" and not ok or res == "INVALIDA" and ok:
        _tech("V1: RESULTADO incoherente con P + 24 h ≤ B")
    if res == "INVALIDA":
        _meth("V1: publicada con menos de 24 h de antelación a B (frontera inválida)")


# --- V3, V4, V6, V7 ----------------------------------------------------------------------------------

def _no_release(ctx, eid, ddir) -> None:
    if ddir is None:
        _tech("RELEASE: sin directorio de decisiones")
    rel = released_windows(ddir, eid, ctx["sha"])
    if rel:
        _meth(f"C.7.3: ventana(s) liberada(s) por el propietario, inelegible(s) para evaluación: {sorted(rel)}")


def _v3(registry, eid) -> None:
    devs = _replay(registry, eid)
    if devs:
        _meth(f"V3: DEVIATION posterior a PREREGISTERED: {[d['deviation_id'] for d in devs]}")


def _consumed(ctx, snapshot_id, part):
    return [r for r in ctx["records"] if isinstance(r, dict) and r.get("kind") == "PARTITION_CONSUMED"
            and r.get("snapshot_id") == snapshot_id and str(r.get("partition")).lower() == part]


def _v4(ctx, eid, manifest, post, decision_ref) -> None:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("window_id"), str):
        _tech("V4: sin manifiesto de la ventana")
    wid = manifest["window_id"]
    part = wid.rsplit("/", 1)[-1].lower()
    sid = manifest.get("snapshot_id")
    cons = _consumed(ctx, sid, part)
    oos_done = any(r.get("experiment_id") == eid and str(r.get("partition")).lower() == "oos"
                   for r in ctx["records"] if isinstance(r, dict) and r.get("kind") == "PARTITION_CONSUMED")
    if not post:                                       # V4-pre
        if cons:
            _meth("V4-pre: la ventana ya tiene un PARTITION_CONSUMED")
        if part == "lockbox" and not oos_done:
            _meth("V4-pre: la OOS del experimento debe consumirse antes que el LOCKBOX")
        return
    if not cons:
        _tech("V4-post: falta el PARTITION_CONSUMED de la ventana evaluada")
    if len(cons) != 1 or cons[0].get("experiment_id") != eid:
        _meth("V4-post: la ventana tiene más de una consumición o la consumió otro experimento")
    if not (isinstance(decision_ref, str) and decision_ref) or cons[0].get("decision_ref") != decision_ref:
        _tech("V4-post: el decision_ref del consumo no es el de la FinalEvaluationGrant")
    if part == "lockbox" and not oos_done:
        _tech("V4-post: falta el consumo de la OOS del LOCKBOX")


def _v6_v7d(attestations, key, decisions_dir) -> None:
    ref = (attestations or {}).get(key)
    if not (isinstance(ref, str) and _DEC_REF.fullmatch(ref) and (Path(decisions_dir) / ref).is_file()):
        _tech(f"{key}: falta la referencia a un documento DEC-NNN_*.md existente (solo existencia y sintaxis)")


def _v7m(ctx) -> None:
    recorded = []
    for r in ctx["records"]:
        if isinstance(r, dict) and r.get("kind") == "TRANSITION" and r.get("to") == "PREREGISTERED" \
                and r.get("experiment_id") == ctx["content"]["experiment_id"]:
            break
        if isinstance(r, dict) and r.get("kind") == "DEVIATION" and r.get("field") == "independence_boundary":
            why = _deviation_shape_error(r)
            if why:
                _tech(f"V7: DEVIATION de independencia incoherente ({why})")
            recorded.append(r["deviation_id"])
    if set(ctx["ib"]["exposure_inventory"]["independence_deviation_ids"]) != set(recorded):
        _meth("V7: el inventario de exposición no cita todos los DEVIATION de independencia previos")


# --- comprobaciones por etapa y clasificación (D.8) --------------------------------------------------

def stage_checks(registry, store, experiment_id: str, stage: str, *, decisions_dir=None, manifest=None,
                 decision_ref=None, attestations=None) -> dict:
    """Resultado de cada comprobación requerida de `stage` (§C.9): OK | METHOD | TECH. Una evidencia
    faltante es TECH (Fail-Closed). Las no aplicables no se evalúan y nunca bloquean."""
    if stage not in STAGES:
        raise ValueError(f"etapa desconocida: {stage!r}")
    eid = experiment_id
    out: dict[str, tuple[str, str]] = {}

    def run(name, fn):
        try:
            fn()
            out[name] = (OK, "")
        except _Fail as f:
            out[name] = (f.nature, f.why)
        except Exception as exc:
            out[name] = (TECH, f"fallo interno: {exc!r}")

    if not valid_experiment_id(eid):
        return {"V2": (TECH, "experimento no válido")}
    try:
        ctx = _context(registry, store, eid)
    except _Fail as f:
        ctx = None
        out["V2"] = (f.nature, f.why)
    ddir = decisions_dir if decisions_dir is not None else getattr(registry, "decisions_dir", None)
    for name in STAGES[stage]:
        if name == "V2":
            out.setdefault("V2", (OK, ""))
        elif ctx is None:
            out[name] = (TECH, "contexto del preregistro no verificable")
        elif name in ("V1a", "V1b"):
            run(name, lambda n=name: _v1(ctx, eid, ddir, n == "V1b"))
        elif name == "V3":
            run(name, lambda: _v3(registry, eid))
        elif name in ("V4pre", "V4post"):
            run(name, lambda n=name: _v4(ctx, eid, manifest, n == "V4post", decision_ref))
        elif name == "V5":
            run(name, lambda: _check_manifest(ctx, eid, manifest))
        elif name in ("V6", "V7d"):
            run(name, lambda n=name: _v6_v7d(attestations, "V6" if n == "V6" else "V7", ddir))
        elif name == "V7m":
            run(name, lambda: _v7m(ctx))
        elif name == "V8":
            st, why = independence_assessment(registry, store, eid, manifest=manifest if "V5" in STAGES[stage] else None)
            out[name] = ((OK, "") if st == INDEPENDENT else (METHOD if st == CONTAMINATED else TECH, why))
    if ctx is not None and stage in ("ET-4", "ET-5", "ET-6", "ET-7", "ET-8", "ET-9", "ET-10"):
        run("RELEASE", lambda: _no_release(ctx, eid, ddir))
    return out


def eligibility(registry, store, experiment_id: str, stage: str, *, preregistration=None, selection_inputs=None,
                **ctx) -> dict:
    """Clasificación de §D.8 para ET-5..ET-10 (y ET-1..ET-4 como comprobación de etapa). Precedencia:
    cualquier condición técnica ⇒ `UNDETERMINABLE`, sin afirmar una determinación metodológica."""
    checks = stage_checks(registry, store, experiment_id, stage, **ctx)
    tech = {k: w for k, (n, w) in checks.items() if n == TECH}
    meth = {k: w for k, (n, w) in checks.items() if n == METHOD}
    confirmatory = None
    try:
        confirmatory = confirmatory_status(registry, experiment_id, preregistration=preregistration,
                                           selection_inputs=selection_inputs)["confirmatory"]
        if confirmatory is False:
            meth["confirmatory_status"] = "no confirmatorio"
    except PreregistrationError as exc:               # incluye ConfirmatoryStatusUnverifiable (nunca se certifica)
        tech["confirmatory_status"] = str(exc)
    except Exception as exc:
        tech["confirmatory_status"] = f"fallo interno: {exc!r}"
    if tech:
        return {"result": UNDETERMINABLE, "nature": "TECHNICAL", "causes": tech, "checks": checks}
    if meth:
        return {"result": NOT_ELIGIBLE, "nature": "METHODOLOGICAL", "causes": meth, "checks": checks}
    return {"result": ELIGIBLE, "nature": None, "causes": {}, "checks": checks}
