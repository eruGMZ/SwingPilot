"""Esquema y fechas de la frontera prospectiva de independencia (CR-023 §C.3–C.5, §C.8, §D.2; bloque B3).

Módulo puro: sin E/S y sin pandas; solo biblioteca estándar y `.experiments` (que no lo importa,
para evitar ciclos). Lo usan `preregistration.py` (congelación ET-1) y `partitions.py` (clase de
independencia del preregistro almacenado).

- Dos formas exactas de `independence_boundary` (C.3, C.5): piloto de tasa (no confirmatorio, solo
  Train) y confirmatoria (frontera `B`, ventanas OOS y LOCKBOX, regla de parada de calendario, regla
  P5 de posiciones abiertas e inventario de exposición). Cualquier otra forma se rechaza.
- Fórmulas de C.8: `H_dev,min = max(38; 100/r)` y `L ≥ k·30/r` meses.
- Inventario de exposición mínimo obligatorio (decisión 4 del propietario): cada exposición de
  `MANDATORY_EXPOSURES` debe constar por id con la misma clase, periodo y `b_not_before` y con
  evidencia que incluya las referencias obligatorias. La incertidumbre se conserva tal cual: nunca se
  deducen fechas de exposición de las fechas de creación de un fixture.
- Validación de la forma de un `DEVIATION` de independencia (D.2).

No implementa `independence_status`, la regla endurecida de cualquier `DEVIATION`, V1, V3–V6, V8 ni
el acceso final (bloques posteriores).
"""
import math
import re
from calendar import monthrange
from datetime import datetime, timedelta, timezone

from .experiments import _evidence_ref_ok, _valid_snapshot_id, valid_experiment_id

DAY_MS = 86_400_000
MONTH_DAYS = 30.436875                       # días medios por mes (365,2425 / 12)
MIN_DEV_MONTHS = 38                          # 24 + 2 + 6 + 6 (C.8)
MIN_TRADES_DEV = 100                         # ≥ 100 operaciones en Train+Val (REQ-G-P15)

CONFIRMATORY = "CONFIRMATORY"
TRADE_RATE_PILOT = "TRADE_RATE_PILOT"
PILOT_RATE = "ESTIMATED_BY_THIS_EXPERIMENT"
PILOT_BOUNDARY = {"confirmatory_eligible": False, "purpose": TRADE_RATE_PILOT, "access_scope": "TRAIN_ONLY"}
PILOT_MIN_HISTORY = {"exempt": TRADE_RATE_PILOT}
CALENDAR_RULE = "FIXED_CALENDAR_NO_EXTENSION"
OPEN_POSITIONS_RULE = "FORCED_CLOSE_AT_LAST_CLOSED_CANDLE"
SCOPE = "BTC/USDT"
CONFIRMATORY_KEYS = {"confirmatory_eligible", "B", "L_oos_months", "L_lb_months", "k", "calendar_rule",
                     "open_positions_rule", "scope", "exposure_inventory"}
INVENTORY_KEYS = {"entries", "general_familiarity_limitation", "independence_deviation_ids", "scope"}
ENTRY_KEYS = {"id", "class", "period_start", "period_end", "b_not_before", "evidence", "note"}
ENTRY_CLASSES = ("DOCUMENTED", "UNCERTAIN", "UNKNOWN")
UNKNOWN = "UNKNOWN"
DEVIATION_CLASSES = ("UNAUTHORIZED_EXPOSURE", "DEVELOPMENT_INFORMED", "PREMATURE_INSPECTION",
                     "INDEPENDENCE_UNVERIFIABLE")
DEVIATION_NEW_KEYS = {"contaminated_window_ids", "class", "evidence", "exposure_started_at"}

_CR023_REF = "SwingPilot@96bd336:harness/change_requests/CR-023_particiones-prospectivas-frontera-independencia.md"
_PROVENANCE_REF = "SwingPilot@2e13c27:harness/verification/IMPL-3_EXP-0001_procedencia.md"

# Exposiciones inventariadas obligatorias (C.4.2.3, C.4.2.5; decisión 4 del propietario). Las fechas
# son las de la evidencia citada; el fixture de IMPL-2 es DESCONOCIDO: su `b_not_before` sale de la cota
# C.4.2.3 (congelación 2026-11-19) y NO es una fecha de exposición.
MANDATORY_EXPOSURES = (
    {"id": "TRADING_BOT_PHASE0_EXP0001_DESIGN", "class": "DOCUMENTED",
     "period_start": "2023-05-01T00:00:00Z", "period_end": "2025-11-08T19:00:00Z",
     "b_not_before": "2025-11-09T00:00:00Z",
     "evidence": (_PROVENANCE_REF, "trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md",
                  "trading-bot@25f0e3f:backtest/REPORTE_FASE0.md")},
    {"id": "LOCKBOX_OOS_001", "class": "UNCERTAIN",
     "period_start": "2025-11-08T20:00:00Z", "period_end": "2026-11-01T00:00:00Z",
     "b_not_before": "2026-11-01T00:00:00Z",
     "evidence": (_PROVENANCE_REF, "trading-bot@21c5f25:backtest/docs/POLITICA_DATOS_OOS.md",
                  "trading-bot@21c5f25:backtest/docs/REGISTRO_DECISIONES.md")},
    {"id": "PRE_2023_RESEARCH", "class": "UNKNOWN",
     "period_start": "2017-08-17T00:00:00Z", "period_end": "2023-05-01T00:00:00Z",
     "b_not_before": "2023-05-01T00:00:00Z", "evidence": (_CR023_REF,)},
    {"id": "IMPL2_CALIBRATION_FIXTURE", "class": "UNKNOWN",
     "period_start": UNKNOWN, "period_end": UNKNOWN, "b_not_before": "2026-11-20T00:00:00Z",
     "evidence": ("SwingPilot@5e712a4:tests/calibration/fixtures/binance_btcusdt_klines.json", _CR023_REF)},
)

_INSTANT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", re.ASCII)
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_HEX64 = re.compile(r"[0-9a-f]{64}", re.ASCII)
_HEX32 = re.compile(r"[0-9a-f]{32}", re.ASCII)
_WINDOW_ID = re.compile(r"(EXP-[0-9]{4})/(OOS|LOCKBOX)", re.ASCII)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class BoundaryError(ValueError):
    """Valor fuera de dominio en una fórmula o fecha de la frontera."""


# --- números y fechas ---------------------------------------------------------------------------

def _num(v) -> bool:
    """Número finito (int o float), nunca bool."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _pos_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _hex64(v) -> bool:
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


def parse_instant(value) -> datetime | None:
    """Instante UTC `YYYY-MM-DDTHH:MM:SSZ` estricto; None si no lo es."""
    if not isinstance(value, str) or not _INSTANT.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_midnight(value) -> datetime | None:
    """Instante a las 00:00:00 UTC exactas (`B`, `b_not_before`); None si no lo es."""
    dt = parse_instant(value)
    return dt if dt is not None and value.endswith("T00:00:00Z") else None


def parse_date(value) -> datetime | None:
    """`YYYY-MM-DD` como medianoche UTC; None si no es válida."""
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return None
    return parse_midnight(value + "T00:00:00Z")


def to_ms(dt: datetime) -> int:
    return (dt - _EPOCH) // timedelta(milliseconds=1)


def format_instant(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_months(dt: datetime, months: int) -> datetime:
    """Suma de meses de calendario con el día recortado al fin de mes (igual que `pd.DateOffset(months=n)`)."""
    year, m0 = divmod(dt.year * 12 + dt.month - 1 + months, 12)
    try:
        return dt.replace(year=year, month=m0 + 1, day=min(dt.day, monthrange(year, m0 + 1)[1]))
    except ValueError as exc:
        raise BoundaryError(f"fecha fuera de rango al sumar {months} meses a {dt}") from exc


# --- fórmulas de C.8 ------------------------------------------------------------------------------

def _check_rate(r) -> None:
    if not _num(r) or r <= 0:
        raise BoundaryError(f"la tasa de trades debe ser un número finito > 0, no {r!r}")


def dev_min_history_months(r) -> float:
    """`H_dev,min = max(38 ; 100/r)` meses (C.8; 38 = 24 + 2 + 6 + 6)."""
    _check_rate(r)
    return max(float(MIN_DEV_MONTHS), MIN_TRADES_DEV / r)


def window_min_months(r, k) -> float:
    """`L ≥ k·30/r` meses (C.8; `k ≥ 1`)."""
    _check_rate(r)
    if not _num(k) or k < 1:
        raise BoundaryError(f"k debe ser un número finito ≥ 1, no {k!r}")
    return k * 30 / r


def available_months(d_dev_ms: int, start_ms: int) -> float:
    """Meses disponibles de la región de desarrollo: `(D_dev − inicio) / (30,436875 días)`."""
    return (d_dev_ms - start_ms) / (MONTH_DAYS * DAY_MS)


# --- forma de `independence_boundary` ----------------------------------------------------------------

def boundary_class(ib) -> str | None:
    """CONFIRMATORY / TRADE_RATE_PILOT según `confirmatory_eligible` (booleano estricto); None si no
    es ninguna. No valida el resto de la forma: use `boundary_error`."""
    if not isinstance(ib, dict):
        return None
    flag = ib.get("confirmatory_eligible")
    if flag is True:
        return CONFIRMATORY
    if flag is False:
        return TRADE_RATE_PILOT
    return None


def boundary_error(ib) -> str | None:
    """None si `ib` es exactamente una de las dos formas válidas (C.3.1, C.5); si no, el motivo."""
    cls = boundary_class(ib)
    if cls is None:
        return "independence_boundary debe ser el piloto de tasa o una frontera confirmatoria (confirmatory_eligible booleano)"
    if cls == TRADE_RATE_PILOT:
        if set(ib) != set(PILOT_BOUNDARY) or ib["purpose"] != TRADE_RATE_PILOT or ib["access_scope"] != "TRAIN_ONLY":
            return f"el piloto de tasa debe declarar exactamente {PILOT_BOUNDARY}"
        return None
    if set(ib) != CONFIRMATORY_KEYS:
        return f"la frontera confirmatoria debe tener exactamente las claves {sorted(CONFIRMATORY_KEYS)}"
    if parse_midnight(ib["B"]) is None:
        return "B debe ser un instante «YYYY-MM-DDT00:00:00Z»"
    for key in ("L_oos_months", "L_lb_months"):
        if not _pos_int(ib[key]):
            return f"{key} debe ser un entero ≥ 1"
    if not _num(ib["k"]) or ib["k"] < 1:
        return "k debe ser un número finito ≥ 1"
    for key, want in (("calendar_rule", CALENDAR_RULE), ("open_positions_rule", OPEN_POSITIONS_RULE),
                      ("scope", SCOPE)):
        if ib[key] != want:
            return f"{key} debe ser {want!r}"
    try:
        windows(ib, "EXP-0000")
    except BoundaryError as exc:
        return str(exc)
    return inventory_error(ib["exposure_inventory"])


def windows(ib: dict, experiment_id: str) -> dict[str, tuple[datetime, datetime]]:
    """Ventanas `[inicio, fin)` de una frontera confirmatoria: OOS = [B, B+L_oos) y
    LOCKBOX = [B+L_oos, B+L_oos+L_lb), con ids `<experimento>/OOS` y `<experimento>/LOCKBOX`."""
    b = parse_midnight(ib.get("B")) if isinstance(ib, dict) else None
    if b is None or not _pos_int(ib.get("L_oos_months")) or not _pos_int(ib.get("L_lb_months")):
        raise BoundaryError("frontera confirmatoria no válida: sin ventanas")
    oos_end = add_months(b, ib["L_oos_months"])                       # B + L_oos (desde B, sin acumular recortes)
    lb_end = add_months(b, ib["L_oos_months"] + ib["L_lb_months"])    # B + L_oos + L_lb
    return {f"{experiment_id}/OOS": (b, oos_end), f"{experiment_id}/LOCKBOX": (oos_end, lb_end)}


def lockbox_end(ib: dict, experiment_id: str) -> datetime:
    return windows(ib, experiment_id)[f"{experiment_id}/LOCKBOX"][1]


def max_b_not_before(inventory: dict) -> datetime:
    """`B` mínimo admisible por el inventario: el mayor `b_not_before` de sus entradas."""
    dates = [parse_midnight(e["b_not_before"]) for e in inventory["entries"] if e["b_not_before"] is not None]
    if not dates or None in dates:
        raise BoundaryError("el inventario no declara ningún b_not_before válido")
    return max(dates)


# --- inventario de exposición -----------------------------------------------------------------------

def _entry_error(e) -> str | None:
    if not isinstance(e, dict) or set(e) != ENTRY_KEYS:
        return f"cada entrada del inventario debe tener exactamente las claves {sorted(ENTRY_KEYS)}"
    if not isinstance(e["id"], str) or not e["id"].strip():
        return "id de exposición no válido"
    if e["class"] not in ENTRY_CLASSES:
        return f"{e['id']}: class debe ser una de {ENTRY_CLASSES}"
    for key in ("period_start", "period_end"):
        if e[key] != UNKNOWN and parse_instant(e[key]) is None:
            return f"{e['id']}: {key} debe ser un instante ISO UTC o «UNKNOWN»"
    a, b = parse_instant(e["period_start"]), parse_instant(e["period_end"])
    if a is not None and b is not None and a > b:
        return f"{e['id']}: period_start posterior a period_end"
    nb = e["b_not_before"]
    if nb is None:
        if e["class"] in ("DOCUMENTED", "UNCERTAIN"):
            return f"{e['id']}: b_not_before es obligatorio en una exposición documentada o incierta"
    elif parse_midnight(nb) is None:
        return f"{e['id']}: b_not_before debe ser un instante «…T00:00:00Z» o null"
    ev = e["evidence"]
    if not isinstance(ev, list) or not ev or not all(_evidence_ref_ok(x) for x in ev):
        return f"{e['id']}: evidence debe ser una lista no vacía de referencias «repo@commit:ruta»"
    if not isinstance(e["note"], str):
        return f"{e['id']}: note debe ser texto"
    return None


def inventory_error(inv) -> str | None:
    """Forma del inventario (C.4.2.5) y presencia exacta de `MANDATORY_EXPOSURES`. None = válido."""
    if not isinstance(inv, dict) or set(inv) != INVENTORY_KEYS:
        return f"exposure_inventory debe tener exactamente las claves {sorted(INVENTORY_KEYS)}"
    if inv["scope"] != SCOPE:
        return f"exposure_inventory.scope debe ser {SCOPE!r}"
    lim = inv["general_familiarity_limitation"]
    if not isinstance(lim, str) or not lim.strip():
        return "falta la limitación de familiaridad general (D3.4)"
    ids = inv["independence_deviation_ids"]
    if not isinstance(ids, list) or not all(isinstance(i, str) and _HEX32.fullmatch(i) for i in ids) \
            or len(set(ids)) != len(ids):
        return "independence_deviation_ids debe ser una lista de identificadores únicos de 32 hexadecimales"
    entries = inv["entries"]
    if not isinstance(entries, list) or not entries:
        return "el inventario de exposición no puede estar vacío"
    for e in entries:
        why = _entry_error(e)
        if why:
            return why
    by_id = {}
    for e in entries:
        if e["id"] in by_id:
            return f"id de exposición repetido: {e['id']}"
        by_id[e["id"]] = e
    for m in MANDATORY_EXPOSURES:
        got = by_id.get(m["id"])
        if got is None:
            return f"falta la exposición obligatoria {m['id']}"
        for key in ("class", "period_start", "period_end", "b_not_before"):
            if got[key] != m[key]:
                return f"{m['id']}: {key} debe ser {m[key]!r} (inventario mínimo obligatorio)"
        if not set(m["evidence"]) <= set(got["evidence"]):
            return f"{m['id']}: la evidencia debe incluir las referencias obligatorias {list(m['evidence'])}"
    return None


# --- campos restantes de C.5 -------------------------------------------------------------------------

def conditioning_error(cc) -> str | None:
    """`conditioning_components`: `{"declaration": "NONE"}` o `{"components": [{name, version, sha256}, …]}`."""
    if isinstance(cc, dict) and cc == {"declaration": "NONE"}:
        return None
    if isinstance(cc, dict) and set(cc) == {"components"}:
        comps = cc["components"]
        if isinstance(comps, list) and comps and all(
                isinstance(c, dict) and set(c) == {"name", "version", "sha256"}
                and isinstance(c["name"], str) and c["name"].strip()
                and isinstance(c["version"], str) and c["version"].strip() and _hex64(c["sha256"])
                for c in comps):
            return None
    return ("conditioning_components debe ser {'declaration': 'NONE'} o {'components': [{name, version, "
            "sha256}, …]} no vacío")


def snapshot_error(snap) -> str | None:
    """`snapshot`: `{snapshot_id, train_val_sha256, d_dev}` de la snapshot de desarrollo."""
    if not isinstance(snap, dict) or set(snap) != {"snapshot_id", "train_val_sha256", "d_dev"}:
        return "snapshot debe tener exactamente snapshot_id, train_val_sha256 y d_dev"
    if not _valid_snapshot_id(snap["snapshot_id"]) or not _hex64(snap["train_val_sha256"]) \
            or parse_date(snap["d_dev"]) is None:
        return "snapshot con snapshot_id, train_val_sha256 o d_dev no válidos"
    return None


def independence_error(content: dict, planned: list[str]) -> str | None:
    """Validación pura de los campos de independencia de C.5 sobre el contenido del preregistro
    (sin E/S). `planned` = `trials_count.planned_config_ids`. None = válido; si no, el motivo."""
    ib = content.get("independence_boundary")
    why = boundary_error(ib)
    if why:
        return why
    why = conditioning_error(content.get("conditioning_components")) or snapshot_error(content.get("snapshot"))
    if why:
        return why
    rate, source, mh = (content.get("observed_trade_rate_per_month"), content.get("trade_rate_source"),
                        content.get("min_history"))
    if boundary_class(ib) == TRADE_RATE_PILOT:
        if rate != PILOT_RATE:
            return f"el piloto debe declarar observed_trade_rate_per_month = {PILOT_RATE!r}"
        if source != "train_only":
            return "trade_rate_source del piloto debe ser 'train_only': la tasa debe venir solo de Train"
        if mh != PILOT_MIN_HISTORY:
            return f"min_history del piloto debe ser {PILOT_MIN_HISTORY}: no se congela (queda en DESIGN)"
        return None
    # --- confirmatorio ---
    eid = content.get("experiment_id")
    if not _num(rate) or rate <= 0:
        return "observed_trade_rate_per_month debe ser un número finito > 0 (tasa del piloto)"
    if not (isinstance(source, dict) and set(source) == {"scope", "pilot_experiment_id"}
            and source["scope"] == "train_only" and valid_experiment_id(source["pilot_experiment_id"])
            and source["pilot_experiment_id"] != eid):
        return ("trade_rate_source debe ser {'scope': 'train_only', 'pilot_experiment_id': 'EXP-NNNN'} de otro "
                "experimento: la tasa debe venir solo de Train")
    k = ib["k"]
    need, window_need = round(dev_min_history_months(rate), 2), round(window_min_months(rate, k), 2)
    if not (isinstance(mh, dict) and set(mh) == {"required_months", "window_min_months", "available_months", "ok"}
            and mh["ok"] is True and _num(mh["available_months"]) and mh["required_months"] == need
            and mh["window_min_months"] == window_need):
        return (f"min_history debe ser {{required_months: {need}, window_min_months: {window_need}, "
                "available_months: <número>, ok: true}}: no se congela (queda en DESIGN)")
    if mh["available_months"] < need:
        return "histórico mínimo no alcanzado: no se congela (queda en DESIGN)"
    minimum = window_min_months(rate, k)
    if ib["L_oos_months"] < minimum or ib["L_lb_months"] < minimum:
        return f"L_oos_months y L_lb_months deben ser ≥ k·30/r = {minimum:.4f} meses"
    mc = content.get("model_config")
    if not (isinstance(mc, dict) and isinstance(mc.get("strategy_id"), str) and mc["strategy_id"].strip()
            and _hex64(mc.get("strategy_sha256")) and isinstance(mc.get("config_sha256"), dict)
            and set(mc["config_sha256"]) == set(planned) and all(_hex64(v) for v in mc["config_sha256"].values())):
        return ("model_config confirmatorio exige strategy_id, strategy_sha256 y config_sha256 con una entrada "
                "(SHA-256) por cada configuración planificada")
    d_dev = parse_date(content["snapshot"]["d_dev"])
    if d_dev >= parse_midnight(ib["B"]):
        return "D_dev debe ser anterior a B"
    return None


# --- DEVIATION de independencia (D.2) ----------------------------------------------------------------

def independence_deviation_error(r: dict) -> str | None:
    """Forma de un registro DEVIATION con `field = "independence_boundary"` (D.2). Se ejecuta antes de
    escribir y en cada reproducción (Fail-Closed). `r["old"]` debe ser una frontera confirmatoria
    válida: un piloto no reserva ventanas. None = válido."""
    new, eid = r.get("new"), r.get("experiment_id")
    if not isinstance(new, dict) or set(new) != DEVIATION_NEW_KEYS:
        return f"«new» de una desviación de independencia debe tener exactamente {sorted(DEVIATION_NEW_KEYS)}"
    old = r.get("old")
    if boundary_class(old) != CONFIRMATORY or boundary_error(old):
        return "«old» debe ser una frontera confirmatoria válida (un piloto no reserva ventanas)"
    ids = new["contaminated_window_ids"]
    own = windows(old, eid) if isinstance(eid, str) else {}
    if not isinstance(ids, list) or not ids or len(set(map(str, ids))) != len(ids) \
            or not all(isinstance(i, str) and _WINDOW_ID.fullmatch(i) and i in own for i in ids):
        return "contaminated_window_ids debe ser una lista no vacía, sin repetidos, de ventanas del propio experimento"
    if new["class"] not in DEVIATION_CLASSES:
        return f"class debe ser una de {DEVIATION_CLASSES}"
    ev = new["evidence"]
    if not isinstance(ev, list) or not ev or not all(_evidence_ref_ok(x) for x in ev):
        return "evidence debe ser una lista no vacía de referencias «repo@commit:ruta»"
    started = new["exposure_started_at"]
    if started != UNKNOWN:
        at = parse_instant(started)
        if at is None:
            return "exposure_started_at debe ser un instante UTC ISO-8601 o «UNKNOWN»"
        if at < max(own[i][0] for i in ids):
            return "exposure_started_at no puede ser anterior al inicio de una ventana citada"
    if not isinstance(r.get("informed_by"), list):
        return "una desviación de independencia exige «informed_by» (lista, puede estar vacía)"
    return None
