"""Evaluador de aceptación por ventana final (CR-023 B7.2; ET-7; C.2, C.8; AC-017-6; P15).

Integra `FinalEvaluationData` (B6.5b) con el backtest en modo ventana (B7.1). OOS y LOCKBOX se evalúan
por separado, cada uno con su `context`, su muestra mínima P15 (los cierres forzados cuentan como
operaciones y se informan aparte) y su comprobación ET-7.

- LOCKBOX solo se carga (y por tanto se consume) si el veredicto OOS es ELIGIBLE_FOR_HUMAN_REVIEW: tras un
  OOS desfavorable o INCONCLUSIVE el cargador del LOCKBOX no se invoca.
- ET-7 (`independence.eligibility`): condición técnica ⇒ UNDETERMINABLE (naturaleza TECHNICAL);
  metodológica ⇒ NOT_ELIGIBLE (METHODOLOGICAL). Ambas dan INCONCLUSIVE sin métricas; la técnica nunca se
  presenta como determinación metodológica.
- `InvalidFinalWindowCandle` → UNDETERMINABLE técnico / INCONCLUSIVE, sin métricas parciales. Este módulo
  nunca escribe en el registro: no revierte el consumo (la partición sigue consumida) ni autoriza reintento
  (`retry_allowed` es siempre False).
- Nunca devuelve APPROVED y no autoriza ninguna evaluación real (O3/O4 siguen siendo del propietario; la
  grant y el consumo los gestiona `load_final`, no este módulo).
"""
import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from . import acceptance as A
from . import independence as I
from . import partitions as P
from . import preregistration as PR
from . import result_serialization as RS
from . import result_store as RST
from .experiments import PersistenceUncertainError
from . import snapshot as S
from .backtest import ExecutionModel, InvalidFinalWindowCandle, run_backtest

FAVORABLE = "ELIGIBLE_FOR_HUMAN_REVIEW"


@dataclass(frozen=True)
class EvidenceParams:
    """Campos que `ExperimentEvidence` exige y no se derivan de la serie. NUNCA los aporta quien llama:
    solo `derive_evidence_params` los construye, desde el preregistro congelado verificado (B7.4a)."""
    risk_fraction: float
    periods_per_year: float
    sr_variance_across_trials: float
    buy_and_hold_report: dict
    baseline_beaten: bool
    dsr_min_probability: float
    bootstrap: dict


class EvidenceParamsError(ValueError):
    """Valor ausente, inválido o incoherente con el preregistro congelado (Fail-Closed, técnico)."""


# Claves de `statistical_tests` del preregistro congelado. Sin valores por defecto: la ausencia de cualquiera
# deniega. Sus VALORES siguen diferidos (D6): este módulo no los fija ni los infiere.
_STAT_KEYS = ("dsr_min_probability", "periods_per_year", "sr_variance_across_trials", "risk_fraction",
              "bootstrap", "baseline")
_BASELINES = ("BUY_AND_HOLD",)


def _num(st: dict, key: str) -> float:
    v = st.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise EvidenceParamsError(f"statistical_tests.{key} ausente o no numérico: {v!r}")
    return float(v)


def derive_evidence_params(preregistration, registry, experiment_id: str, window: pd.DataFrame,
                           equity_fn: Callable[[float], list[float]]) -> EvidenceParams:
    """Deriva los parámetros del preregistro congelado y verificado (hash, experimento y SHA-256 de
    PREREGISTERED en el registro) y de evidencia reproducible de la propia ventana (comprar y mantener sobre
    sus velas H4). Cualquier ausencia o incoherencia → `EvidenceParamsError`."""
    if preregistration is None:
        raise EvidenceParamsError("sin preregistro congelado: los parámetros no pueden derivarse")
    try:
        preregistration.verify()
        bound = PR._preregistered_sha(registry, experiment_id)
    except Exception as exc:
        raise EvidenceParamsError(f"preregistro no verificable: {exc}") from exc
    if preregistration.experiment_id != experiment_id or preregistration.sha256 != bound:
        raise EvidenceParamsError("el preregistro no corresponde al experimento o a su SHA-256 registrado")
    st = (preregistration.content or {}).get("statistical_tests")
    if not isinstance(st, dict):
        raise EvidenceParamsError("statistical_tests ausente en el preregistro congelado")
    missing = [k for k in _STAT_KEYS if k not in st]
    if missing:
        raise EvidenceParamsError(f"statistical_tests sin {missing} (sin valores por defecto; D6 diferido)")
    dsr = _num(st, "dsr_min_probability")
    if not 0 < dsr < 1:
        raise EvidenceParamsError(f"dsr_min_probability fuera de (0, 1): {dsr}")
    boot = st["bootstrap"]
    if not isinstance(boot, dict) or set(boot) != {"n_resamples", "seed", "block_size"} or any(
            isinstance(v, bool) or not isinstance(v, int) for v in boot.values()):
        raise EvidenceParamsError(f"bootstrap debe ser {{n_resamples, seed, block_size}} enteros: {boot!r}")
    if st["baseline"] not in _BASELINES:
        raise EvidenceParamsError(f"línea base no soportada o no declarada: {st['baseline']!r}")
    try:
        first_open, last_close = float(window["open"].iloc[0]), float(window["close"].iloc[-1])
    except Exception as exc:
        raise EvidenceParamsError(f"ventana sin velas utilizables para comprar y mantener: {exc!r}") from exc
    if not (math.isfinite(first_open) and math.isfinite(last_close) and first_open > 0 and last_close > 0):
        raise EvidenceParamsError("velas de la ventana no válidas para comprar y mantener")
    bh = last_close / first_open - 1
    risk = _num(st, "risk_fraction")
    eq = equity_fn(risk)                       # ValueError si risk ∉ (0, 0.015] (INV-001): también deniega
    strategy = eq[-1] / eq[0] - 1
    return EvidenceParams(
        risk_fraction=risk, periods_per_year=_num(st, "periods_per_year"),
        sr_variance_across_trials=_num(st, "sr_variance_across_trials"),
        buy_and_hold_report={"return": bh, "first_open": first_open, "last_close": last_close,
                             "candles": len(window), "source": "window_candles"},
        baseline_beaten=strategy > bh, dsr_min_probability=dsr, bootstrap=dict(boot))


@dataclass
class WindowOutcome:
    partition: str
    verdict: str                      # INCONCLUSIVE | REJECTED | ELIGIBLE_FOR_HUMAN_REVIEW
    nature: str | None                # None | TECHNICAL | METHODOLOGICAL
    eligibility: str | None           # ET-7: ELIGIBLE | NOT_ELIGIBLE | UNDETERMINABLE (None si no se llegó)
    reasons: list[str]
    metrics: dict | None              # None ante fallo técnico/metodológico previo al veredicto
    trades: int = 0
    forced_window_close_trades: int = 0
    consumption_reversed: bool = False
    retry_allowed: bool = False


@dataclass
class FinalWindowsResult:
    oos: WindowOutcome
    lockbox: WindowOutcome | None     # None = no iniciado (LOCKBOX no cargado ni consumido)
    lockbox_progression: str          # "NOT_ATTEMPTED" | "ATTEMPTED"
    notes: list[str] = field(default_factory=list)


def _fail(part, verdict_reasons, nature, elig, **kw) -> WindowOutcome:
    return WindowOutcome(part, "INCONCLUSIVE", nature, elig, verdict_reasons, None, **kw)


class ProvenanceError(ValueError):
    """Las velas o el contexto evaluados no son los de la snapshot sellada y consumida (Fail-Closed, técnico)."""


def _check_evidence(data, manifest: dict, registry) -> None:
    """B7.4d: la evidencia debe ser la emitida por `load_final` (credencial en proceso, inmutable) y estar ligada
    a la partición, snapshot, ventana, digests entregados y al consumo vigente en el registro."""
    ev = getattr(data, "provenance", None)
    if type(ev) is not P.FinalWindowProvenance:
        raise ProvenanceError("sin evidencia de procedencia emitida por load_final")
    part, wid = data.partition, str(manifest.get("window_id") or "")
    exp, gpart, gsnap, ref, _by = ev.grant
    if gpart != part or ev.window_id != wid or gsnap != manifest.get("snapshot_id"):
        raise ProvenanceError("la evidencia no corresponde a la partición, ventana o snapshot evaluadas")
    digests = json.loads(ev.digests)
    for name, frame in (("context", data.context), (part, data.data)):
        if digests.get(name) != S.canonical_content_digest(frame) or digests[name] != manifest["files"][name]["canonical_digest"]:
            raise ProvenanceError(f"{name}: los datos evaluados no son los entregados por load_final")
    rec = json.loads(ev.consumption)
    if (rec.get("snapshot_id"), rec.get("partition"), rec.get("experiment_id"), rec.get("decision_ref")) != (
            gsnap, part, exp, ref):
        raise ProvenanceError("el registro de consumo no corresponde a la grant")
    if registry is None or rec not in registry.consumed_partitions():
        raise ProvenanceError("el consumo ligado no consta en el registro")


def verify_provenance(data, manifest: dict, registry=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """B7.4b: ata lo que se evalúa a la snapshot autorizada. El digest canónico (§C.6.5) de la partición y del
    `context` COMPLETOS —tal como los entregó `load_final`— debe coincidir con el del manifiesto; después, y solo
    después, se deriva la serie H4. Quien llama no puede aportar velas filtradas, recortadas ni sintéticas:
    cualquier fila añadida, quitada o alterada rompe el digest. Devuelve (ventana H4, `context` H4) verificadas."""
    try:
        _check_evidence(data, manifest, registry)
        part = data.partition
        files = manifest["files"]
        wid = str(manifest.get("window_id") or "")
        if part not in files or wid.rsplit("/", 1)[-1].lower() != part:
            raise ProvenanceError(f"la partición {part!r} no corresponde a la ventana {wid!r} del manifiesto")
        for name, frame in (("context", data.context), (part, data.data)):
            if S.canonical_content_digest(frame) != files[name]["canonical_digest"]:
                raise ProvenanceError(f"{name}: el contenido evaluado no coincide con la snapshot sellada")
    except ProvenanceError:
        raise
    except Exception as exc:
        raise ProvenanceError(f"procedencia no verificable: {exc!r}") from exc
    h4 = lambda f: f[f["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)   # noqa: E731
    return h4(data.data), h4(data.context)


def _evaluate_outcome(data, logic, model: ExecutionModel, registry, store, experiment_id: str, *,
                    manifest: dict, preregistration=None, selection_inputs=None, **et7_ctx) -> WindowOutcome:
    """Evalúa UNA ventana ya cargada (`FinalEvaluationData`). No relee datos ni toca el consumo."""
    part = data.partition
    try:                  # B7.4b: procedencia ANTES de cualquier cálculo; sin métricas ni backtest si falla
        window, ctx4 = verify_provenance(data, manifest, registry)
    except ProvenanceError as exc:
        return _fail(part, [f"TECNICA (UNDETERMINABLE): procedencia de los datos: {exc}"], "TECHNICAL",
                     I.UNDETERMINABLE)
    try:
        res = run_backtest(window, logic, model, context=ctx4)
    except InvalidFinalWindowCandle as exc:
        return _fail(part, [f"TECNICA (UNDETERMINABLE): vela final de la ventana inválida: {exc}"], "TECHNICAL",
                     I.UNDETERMINABLE)
    except Exception as exc:       # cualquier otro fallo del motor es técnico y Fail-Closed
        return _fail(part, [f"TECNICA (UNDETERMINABLE): fallo del backtest de ventana: {exc!r}"], "TECHNICAL",
                     I.UNDETERMINABLE)
    forced = sum(1 for t in res.trades if t.forced_window_close)
    counts = dict(trades=len(res.trades), forced_window_close_trades=forced)
    el = I.eligibility(registry, store, experiment_id, "ET-7", preregistration=preregistration,
                       selection_inputs=selection_inputs, manifest=manifest, window_id=manifest.get("window_id"),
                       **et7_ctx)
    if el["result"] != I.ELIGIBLE:
        why = [f"{k}: {w}" for k, w in el["causes"].items()]
        tag = "TECNICA (UNDETERMINABLE)" if el["result"] == I.UNDETERMINABLE else "METODOLOGICA (NOT_ELIGIBLE)"
        return _fail(part, [f"{tag}: ET-7 {'; '.join(why)}"], el["nature"], el["result"], **counts)
    net = [t.net_r for t in res.trades]
    try:                  # B7.4a: parámetros del preregistro congelado; fallo → técnico, sin métricas
        params = derive_evidence_params(preregistration, registry, experiment_id, window, res.equity_curve)
        eq = res.equity_curve(params.risk_fraction)
    except (EvidenceParamsError, ValueError) as exc:
        return _fail(part, [f"TECNICA (UNDETERMINABLE): parámetros de evidencia no derivables: {exc}"],
                     "TECHNICAL", I.UNDETERMINABLE, **counts)
    rets = [eq[i + 1] / eq[i] - 1 for i in range(len(eq) - 1)]
    ev = A.ExperimentEvidence(
        trades={"oos": len(net)}, oos_net_r=net, oos_equity=eq, oos_period_returns=rets,
        periods_per_year=params.periods_per_year, sr_variance_across_trials=params.sr_variance_across_trials,
        buy_and_hold_report=params.buy_and_hold_report, baseline_beaten=params.baseline_beaten,
        dsr_min_probability=params.dsr_min_probability, bootstrap=params.bootstrap)
    v = A.evaluate(ev, registry, preregistration=preregistration, selection_inputs=selection_inputs,
                   p15_part=part)
    v.metrics.update(window=part, window_summary=res.summary())      # forzados y señales finales, por separado
    return WindowOutcome(part, v.outcome, None, I.ELIGIBLE, list(v.reasons), v.metrics, **counts)


def evaluate_final_windows(load_oos: Callable, resolve_lockbox: Callable, logic, model: ExecutionModel,
                           registry, store, experiment_id: str, *, oos_manifest: dict,
                           preregistration=None, selection_inputs=None, result_store=None, actor=None,
                           **et7_ctx) -> FinalWindowsResult:
    """`load_oos` es una llamada sin argumentos que invoca `load_final` (consumo y lectura). `resolve_lockbox`
    (B7.4d) se invoca SOLO tras un OOS favorable y devuelve `(manifest_lockbox, load_lockbox)`: ni el manifiesto
    ni el cargador del LOCKBOX existen antes, y la grant humana la aporta quien la construye dentro de
    `load_lockbox`. Un error de acceso se propaga (no se interpreta como resultado).

    CR-024 B.5/B.7: todo resultado emitido (`IssuedWindowResult`) se persiste con `persist_window_result` ANTES
    de informarse como acreditado o de progresar; un fallo propaga `PersistenceUncertainError` (sin éxito, sin
    reevaluación). Un resultado no emitido (sin procedencia B7) no es acreditado y nunca progresa. El LOCKBOX
    solo se resuelve si el OOS RELEÍDO del registro y de la evidencia es favorable autoritativo."""
    from .experiments import OWNER
    kw = dict(preregistration=preregistration, selection_inputs=selection_inputs, **et7_ctx)
    rstore = None
    if registry is not None:
        rstore = result_store if result_store is not None else RST.for_registry(registry)

    def run(data, manifest):
        oc, issued = evaluate_window_issued(data, logic, model, registry, store, experiment_id,
                                            manifest=manifest, **kw)
        if issued is None:
            return oc, False
        registry.persist_window_result(rstore, issued, manifest_dir=et7_ctx.get("manifest_dir"),
                                       actor=actor or OWNER)
        state = registry.window_result_state(rstore, experiment_id, oc.partition)
        if state != "RESULT_VALID":
            raise PersistenceUncertainError(f"{experiment_id}/{oc.partition}: estado {state} tras persistir")
        return oc, True

    oos, persisted = run(load_oos(), oos_manifest)
    if not persisted:
        return FinalWindowsResult(oos, None, "NOT_ATTEMPTED",
                                  [f"LOCKBOX no iniciado: OOS {oos.verdict} no acreditado (resultado no emitido "
                                   "ni persistido)"])
    if not registry.window_result_favorable(rstore, experiment_id, "oos"):
        return FinalWindowsResult(oos, None, "NOT_ATTEMPTED",
                                  [f"LOCKBOX no iniciado: OOS {oos.verdict} no es favorable autoritativo"])
    lockbox_manifest, load_lockbox = resolve_lockbox()
    lock, lpersisted = run(load_lockbox(), lockbox_manifest)
    notes = [] if lpersisted else [f"LOCKBOX {lock.verdict} no acreditado (resultado no emitido ni persistido)"]
    return FinalWindowsResult(oos, lock, "ATTEMPTED", notes)


def _manifest_file_sha(manifest: dict, manifest_dir) -> str:
    """SHA-256 de los bytes REALES del archivo del manifiesto sellado (`<manifest_dir>/<snapshot_id>.json`),
    nunca de JSON reconstruido. El archivo debe cargar y validar exactamente al manifiesto verificado."""
    if manifest_dir is None:
        raise ProvenanceError("sin manifest_dir: los bytes del manifiesto no son accesibles")
    path = Path(manifest_dir) / f"{manifest['snapshot_id']}.json"
    raw = path.read_bytes()
    if S.validate_manifest(json.loads(raw)) != manifest:
        raise ProvenanceError("el archivo del manifiesto no coincide con el manifiesto verificado")
    return RS.evaluation_hash(raw)


def _issue(outcome: WindowOutcome, data, manifest: dict, registry, experiment_id: str, manifest_dir=None):
    """CR-024 B.1/B.2: canonicaliza al emitir, ligado a la procedencia B7 genuina. Un fallo de tipo o de
    ligadura es técnico: el resultado emitido es TECHNICAL/UNDETERMINABLE con `metrics = None`."""
    def technical(msg):
        return _fail(outcome.partition, [f"TECNICA (UNDETERMINABLE): resultado no canonicalizable: {msg}"],
                     "TECHNICAL", I.UNDETERMINABLE, trades=outcome.trades,
                     forced_window_close_trades=outcome.forced_window_close_trades)

    try:                                 # ligadura B7 genuina; sin ella no hay nada que emitir ni persistir
        _check_evidence(data, manifest, registry)
        ev = data.provenance
        rec = json.loads(ev.consumption)
        lines, records = registry._load()
        idx = [i for i, r in enumerate(records) if r == rec and r.get("kind") == "PARTITION_CONSUMED"]
        if len(idx) != 1:
            raise ProvenanceError("el consumo ligado no consta exactamente una vez")
        bind = dict(experiment_id=experiment_id, prereg_sha256=PR._preregistered_sha(registry, experiment_id),
                    snapshot_id=manifest["snapshot_id"], window_id=str(manifest["window_id"]),
                    manifest_sha256=_manifest_file_sha(manifest, manifest_dir),
                    decision_ref=ev.grant[3], consumed_line_sha256=RS.evaluation_hash(lines[idx[0]]))
    except Exception:
        return outcome, None

    def build(oc):
        doc, raw = RS.build_document(oc, **bind)
        return RS.issue(RS._ISSUE_KEY, oc, doc, raw, (experiment_id, oc.partition, bind["snapshot_id"], bind["decision_ref"]))

    try:
        return outcome, build(outcome)
    except Exception as exc:             # fallo de tipo/serialización: resultado técnico canonicalizable
        oc = technical(repr(exc))
        try:
            return oc, build(oc)
        except Exception:
            return oc, None


def evaluate_window_issued(data, logic, model: ExecutionModel, registry, store, experiment_id: str, *,
                           manifest: dict, preregistration=None, selection_inputs=None, **et7_ctx):
    """Como `evaluate_window`, pero devuelve `(WindowOutcome, IssuedWindowResult | None)`. El resultado emitido
    solo existe con procedencia B7 verificada; su `outcome` es el devuelto (técnico si no fue canonicalizable)."""
    oc = _evaluate_outcome(data, logic, model, registry, store, experiment_id, manifest=manifest,
                           preregistration=preregistration, selection_inputs=selection_inputs, **et7_ctx)
    return _issue(oc, data, manifest, registry, experiment_id, et7_ctx.get("manifest_dir"))


def evaluate_window(*a, **kw) -> WindowOutcome:
    """Firma histórica de B7: devuelve solo el `WindowOutcome` (técnico si el resultado no es canonicalizable)."""
    return evaluate_window_issued(*a, **kw)[0]
