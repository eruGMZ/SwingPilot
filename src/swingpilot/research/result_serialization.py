"""CR-024 v1.12 §B.1–B.2 (CR24-I1): serialización canónica del resultado de ventana, `evaluation_hash` y
`IssuedWindowResult`. Sin persistencia, sin eventos de registro, sin CLI.

Tipos cerrados; `float` ⇒ `{"$f64":"<16 hex>"}` (binary64 big-endian, NaN canónico, ±Inf rechazado); la clave
`$f64` está reservada. Lectura estricta: el documento releído debe reserializarse a los mismos bytes."""
import dataclasses
import hashlib
import json
import math
import platform
import re
import struct

import numpy as np
import pandas as pd
import pyarrow

SCHEMA = 1
CONTRACT_VERSION = "1.12"
F64 = "$f64"
_HEX16 = re.compile(r"[0-9a-f]{16}")
_SHA = re.compile(r"[0-9a-f]{64}")
_CANON_NAN = "7ff8000000000000"


class ResultSerializationError(ValueError):
    """El resultado no es canonicalizable o el documento no cumple la lectura estricta (fallo técnico)."""


def evaluator_version() -> str:
    """Derivado por el sistema (contrato, schema, python, pandas, pyarrow). No es un hash de fuentes."""
    return (f"contract={CONTRACT_VERSION};schema={SCHEMA};python={platform.python_version()};"
            f"pandas={pd.__version__};pyarrow={pyarrow.__version__}")


def _f64(x: float) -> dict:
    if math.isinf(x):
        raise ResultSerializationError("±Infinity no es canonicalizable")
    h = _CANON_NAN if math.isnan(x) else struct.pack(">d", x).hex()
    return {F64: h}


def to_canonical(v):
    """Origen → estructura JSON canónica (tipo exacto; bool nunca como int; subclases no admitidas se rechazan)."""
    t = type(v)
    if v is None or t is str or t is bool:
        return v
    if t is int or isinstance(v, np.integer):
        return int(v)
    if t is float or isinstance(v, np.floating):
        return _f64(float(v))
    if t in (list, tuple):
        return [to_canonical(x) for x in v]
    if t is dict:
        out = {}
        for k, x in v.items():
            if type(k) is not str:
                raise ResultSerializationError(f"clave no str: {k!r}")
            if k == F64:
                raise ResultSerializationError("la clave «$f64» está reservada")
            out[k] = to_canonical(x)
        return out
    raise ResultSerializationError(f"tipo no admitido: {t.__name__}")


def _dump(doc) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def canonical_bytes(value) -> bytes:
    try:
        return _dump(to_canonical(value))
    except ResultSerializationError:
        raise
    except Exception as exc:                      # p. ej. UnicodeEncodeError por sustitutos aislados
        raise ResultSerializationError(f"no serializable: {exc!r}") from exc


def evaluation_hash(doc_bytes: bytes) -> str:
    return hashlib.sha256(doc_bytes).hexdigest()


def _reject_const(c):
    raise ResultSerializationError(f"constante JSON no admitida: {c}")


def _pairs(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ResultSerializationError("clave duplicada")
    if F64 in keys and keys != [F64]:
        raise ResultSerializationError("«$f64» mezclado con otras claves")
    return dict(pairs)


def _float_num(s):
    raise ResultSerializationError(f"número con fracción o exponente: {s}")


def _check_tags(o):
    if isinstance(o, dict):
        if set(o) == {F64}:
            h = o[F64]
            if type(h) is not str or not _HEX16.fullmatch(h):
                raise ResultSerializationError("«$f64» mal formado")
            f = struct.unpack(">d", bytes.fromhex(h))[0]
            if math.isinf(f) or (math.isnan(f) and h != _CANON_NAN):
                raise ResultSerializationError("«$f64» no canónico")
        else:
            for x in o.values():
                _check_tags(x)
    elif isinstance(o, list):
        for x in o:
            _check_tags(x)


def parse_strict(data: bytes) -> dict:
    """Lectura estricta: sin fracción/exponente/NaN/Infinity/duplicados y con round-trip byte a byte."""
    try:
        doc = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_float_num,
                         parse_constant=_reject_const)
        _check_tags(doc)
        if _dump(doc) != data:
            raise ResultSerializationError("el documento no se reserializa a los mismos bytes")
    except ResultSerializationError:
        raise
    except Exception as exc:
        raise ResultSerializationError(f"lectura estricta fallida: {exc!r}") from exc
    return doc


_ISSUE_KEY = object()          # credencial en proceso: solo la usa `window_evaluation` (precedente: FreezeCheck)


class IssuedWindowResult:
    """Resultado inmutable emitido por `evaluate_window`. Un diccionario, `WindowOutcome` suelto, copia o hash
    aportado por el llamador no lo es. Control en proceso (no tamper-evident frente a un proceso comprometido)."""
    __slots__ = ("outcome", "document", "document_bytes", "evaluation_hash", "binding")

    def __init__(self, key, outcome, document: dict, document_bytes: bytes, binding: tuple):
        if key is not _ISSUE_KEY:
            raise ResultSerializationError("IssuedWindowResult solo lo emite evaluate_window (CR-024 B.2)")
        for n, x in (("outcome", outcome), ("document", json.dumps(document)),
                     ("document_bytes", document_bytes), ("evaluation_hash", evaluation_hash(document_bytes)),
                     ("binding", tuple(binding))):
            object.__setattr__(self, n, x)

    def __setattr__(self, n, v):
        raise AttributeError("IssuedWindowResult es inmutable")

    def __delattr__(self, n):
        raise AttributeError("IssuedWindowResult es inmutable")

    def __copy__(self):
        raise ResultSerializationError("IssuedWindowResult no se copia")

    def __deepcopy__(self, memo):
        raise ResultSerializationError("IssuedWindowResult no se copia")

    def __reduce__(self):
        raise ResultSerializationError("IssuedWindowResult no se serializa")


def build_document(outcome, *, experiment_id: str, prereg_sha256: str, snapshot_id: str, window_id: str,
                   manifest_sha256: str, decision_ref: str, consumed_line_sha256: str) -> tuple[dict, bytes]:
    """Documento canónico B.1 (sin `at_utc`/`actor`). Devuelve (documento canónico, bytes) ya validado."""
    for n, s in (("prereg_sha256", prereg_sha256), ("manifest_sha256", manifest_sha256),
                 ("consumed_line_sha256", consumed_line_sha256)):
        if type(s) is not str or not _SHA.fullmatch(s):
            raise ResultSerializationError(f"{n} no es SHA-256 en hexadecimal minúsculo")
    ver = evaluator_version()
    if not ver:
        raise ResultSerializationError("evaluator_version vacía")
    doc = {"schema": SCHEMA, "experiment_id": experiment_id, "partition": outcome.partition,
           "prereg_sha256": prereg_sha256, "snapshot_id": snapshot_id, "window_id": window_id,
           "manifest_sha256": manifest_sha256,
           "consumption": {"decision_ref": decision_ref, "consumed_line_sha256": consumed_line_sha256},
           "evaluator_version": ver, "outcome": dataclasses.asdict(outcome)}
    data = canonical_bytes(doc)
    return parse_strict(data), data


def issue(key, outcome, document: dict, data: bytes, binding: tuple) -> IssuedWindowResult:
    """Solo para `window_evaluation.evaluate_window`: exige la credencial privada de emisión."""
    if key is not _ISSUE_KEY:
        raise ResultSerializationError("issue() exige la credencial de emisión (CR-024 B.2)")
    return IssuedWindowResult(key, outcome, document, data, binding)
