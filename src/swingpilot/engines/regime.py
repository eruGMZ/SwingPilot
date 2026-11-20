"""Regime Engine (FEAT-018; api_contracts.md §3.8 B.2; DEC-018 decisión 1; REQ-G-057, REQ-G-071).

- Determinista, sin LLM; no es decisor: solo condiciona una estrategia si su definición
  aprobada lo declara.
- La clasificación v1 aprobada en DEC-018 (volatilidad D1 en 3 categorías por percentiles solo
  con pasado; dirección como contexto) necesita parámetros justificados con Train y aprobados
  por el propietario. Hasta entonces el motor corre SIN especificación: `regime_label =
  UNCLASSIFIED`, `spec_version = null`, sin mediciones. No se inventan clases ni umbrales.
- Con una `RegimeSpec` (inyectada; en IMPL-3 solo en pruebas), el motor aplica: datos
  suficientes (`min_bars`), clasificación al cierre de vela, persistencia de K velas
  (`TRANSITION` mientras tanto) y registro de transición.
"""
from dataclasses import dataclass, replace
from typing import Callable, Protocol

from swingpilot.market_data.candles import Candle, ms_to_iso

from .common import MarketInput, base_payload, engine_message

ENGINE = "regime_engine"
ENGINE_VERSION = "0.1.0"
UNCLASSIFIED, TRANSITION = "UNCLASSIFIED", "TRANSITION"


class RegimeSpec(Protocol):
    classifier_id: str
    version: str
    timeframe: str
    labels: tuple[str, ...]
    min_bars: int
    persistence_bars: int

    def measure(self, bars: list[Candle]) -> dict[str, float]: ...
    def classify(self, measurements: dict[str, float], current_label: str | None) -> str: ...
    def margins(self, measurements: dict[str, float]) -> dict[str, float]: ...


@dataclass(frozen=True)
class RegimeState:
    """Estado entre ciclos (entrada y salida explícitas: misma entrada + mismo estado → misma salida)."""
    label: str | None = None
    since_close_utc: str | None = None
    bars_in_regime: int = 0
    candidate: str | None = None
    candidate_count: int = 0


class RegimeEngine:
    def __init__(self, spec: RegimeSpec | None = None, *, timeframe: str = "D1"):
        self.spec = spec
        self.timeframe = spec.timeframe if spec else timeframe

    def run(self, cause: dict, market: MarketInput, state: RegimeState = RegimeState()) -> tuple[dict, RegimeState]:
        tf = self.timeframe
        refs = {tf: market.data_ref(tf)}
        spec_v = self.spec.version if self.spec else None
        cid = self.spec.classifier_id if self.spec else "none"
        common = {"classifier_id": cid, "candidate_label": None, "previous_label": state.label,
                  "regime_since_utc": None, "bars_in_regime": 0, "measurements": {}}

        def out(payload_status, label=UNCLASSIFIED, missing=None, error=None, extra=None, new_state=state):
            p = {**base_payload(ENGINE, ENGINE_VERSION, spec_v, payload_status, refs, missing, error),
                 **common, "regime_label": label, **(extra or {})}
            msg = engine_message(cause, source=ENGINE, message_type="REGIME_CLASSIFIED", payload=p,
                                 data_timestamp_utc=market.data_timestamp(tf), timeframe=tf)
            return msg, new_state

        if not market.has_last_closed(tf):
            return out("ERROR", error={"code": "DATA_UNAVAILABLE",
                                       "message": f"falta la última vela {tf} cerrada (REQ-G-070)"})
        if self.spec is None:
            return out("COMPLETED")   # sin especificación aprobada (DEC-018): UNCLASSIFIED
        bars = market.bars(tf)
        if len(bars) < self.spec.min_bars:
            return out("INSUFFICIENT_DATA",
                       missing=[f"{tf}: {len(bars)} velas cerradas < {self.spec.min_bars} requeridas"])
        try:
            m = self.spec.measure(bars)
            raw = self.spec.classify(m, state.label)
            margins = self.spec.margins(m)
        except Exception as exc:   # noqa: BLE001 — error técnico del clasificador
            return out("ERROR", error={"code": "INTERNAL_ERROR", "message": f"{type(exc).__name__}: {exc}"})
        if raw not in self.spec.labels:
            return out("ERROR", error={"code": "INTERNAL_ERROR", "message": f"etiqueta fuera del clasificador: {raw}"})
        close_iso = ms_to_iso(bars[-1].close_time + 1)
        new = _advance(state, raw, close_iso, self.spec.persistence_bars)
        # TRANSITION mientras haya un cambio sin confirmar (o en el primer ciclo sin persistencia)
        label = new.label if (new.candidate is None and new.label is not None) else TRANSITION
        extra = {"measurements": m, "threshold_margins": margins, "previous_label": state.label,
                 "candidate_label": new.candidate if label == TRANSITION else None,
                 "regime_since_utc": new.since_close_utc, "bars_in_regime": new.bars_in_regime}
        return out("COMPLETED", label=label, extra=extra, new_state=new)


def _advance(state: RegimeState, raw: str, close_iso: str, k: int) -> RegimeState:
    """Persistencia mínima de K velas cerradas para confirmar un cambio (propuesta Q42 §4)."""
    if state.label == raw:
        return replace(state, bars_in_regime=state.bars_in_regime + 1, candidate=None, candidate_count=0)
    count = state.candidate_count + 1 if state.candidate == raw else 1
    if count >= k:
        return RegimeState(label=raw, since_close_utc=close_iso, bars_in_regime=1, candidate=None, candidate_count=0)
    return replace(state, bars_in_regime=state.bars_in_regime + (1 if state.label else 0),
                   candidate=raw, candidate_count=count)
