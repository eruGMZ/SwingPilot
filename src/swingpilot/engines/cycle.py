"""Ciclo de decisión Fase 1 → Fase 4 hasta E9 (FEAT-022; data_flow.md §1 y §5; architecture.md §7 fila 3).

E1 ANALYSIS_REQUESTED → E2 REGIME_CLASSIFIED → E3 ML_INFERENCE_COMPLETED → E4 STRATEGY_CANDIDATE |
NO_SETUP (+ STRATEGY_EXIT_SIGNAL / STOP_ADJUSTMENT_REQUESTED) → [Fase 3: E5..E7] → [Fase 4: E8]
→ E9 TRADE_PROPOSAL normalizada, o PROPOSAL_NORMALIZATION_REJECTED si la síntesis es inconsistente
con el candidato o la propuesta queda fuera de §4.1 (B.10; CR-019). El ciclo termina en E9: sin Risk Manager, sin autorizaciones ni
órdenes (DEC-017 condición 6; IMPL-4/IMPL-5).

- Todos los eventos comparten `correlation_id` y se registran en el EventStore.
- La Fase 3/4 la ejecuta el AI Orchestrator existente; en pruebas, con un adaptador de fixtures
  (sin costo). Las corridas reales con LLM solo se hacen a petición del propietario (DEC-017 Q47).
- El contexto del Market Analyst se arma con las velas cerradas del `MarketInput`; los
  indicadores los entrega quien llama (no hay indicadores aprobados por contrato para §3.1). El
  contexto macro llega vacío hasta resolver CR-017.
"""
from dataclasses import dataclass, field
from typing import Callable

from swingpilot.ai.orchestrator import AIOrchestrator
from swingpilot.audit import EventStore
from swingpilot.contracts import new_message
from swingpilot.market_data.candles import ms_to_iso

from .common import MarketInput
from .ml import MLEngine
from .normalizer import NormalizationResult, normalize
from .regime import RegimeEngine, RegimeState
from .strategy import OpenPosition, StrategyEngine


@dataclass
class CycleReport:
    correlation_id: str
    events: list[dict] = field(default_factory=list)
    outcome: str = "NOT_RUN"           # NO_SETUP | STRATEGY_ENGINE_ERROR | AI_* | PROPOSAL_EMITTED | PROPOSAL_REJECTED | NO_PROPOSAL
    normalization: NormalizationResult | None = None
    regime_state: RegimeState | None = None
    llm_calls: int = 0

    def types(self) -> list[str]:
        return [m["message_type"] for m in self.events]


def market_context(market: MarketInput, *, bars_per_timeframe: int,
                   indicators: Callable[[MarketInput], dict] | None = None) -> dict:
    """api_contracts.md §3.1: solo velas cerradas; `bars_per_timeframe` lo fija quien llama."""
    ohlcv = {tf: [{"timestamp": ms_to_iso(c.open_time), "open": c.open, "high": c.high, "low": c.low,
                   "close": c.close, "volume": c.volume} for c in market.bars(tf)[-bars_per_timeframe:]]
             for tf in ("D1", "H4", "H1")}
    return {"asset": "BTC/USDT", "timeframes": ["D1", "H4", "H1"], "ohlcv": ohlcv,
            "indicators": indicators(market) if indicators else {"D1": {}, "H4": {}, "H1": {}},
            "data_source": "binance"}


class DecisionCycle:
    def __init__(self, regime: RegimeEngine, ml: MLEngine, strategy: StrategyEngine,
                 orchestrator: AIOrchestrator, store: EventStore, *, bars_per_timeframe: int,
                 indicators: Callable[[MarketInput], dict] | None = None):
        if orchestrator._store is not store:
            raise ValueError("el orquestador debe registrar en el mismo EventStore que el ciclo")
        self.regime, self.ml, self.strategy, self.orch, self.store = regime, ml, strategy, orchestrator, store
        self.bars_per_timeframe = bars_per_timeframe
        self.indicators = indicators

    def _record(self, rep: CycleReport, *msgs: dict) -> None:
        for m in msgs:
            self.store.append(m)
            rep.events.append(m)

    def run(self, market: MarketInput, *, mode: str, block: str | None = None,
            position: OpenPosition | None = None, regime_state: RegimeState = RegimeState(),
            macro_context: dict | None = None) -> CycleReport:
        tf = self.strategy.signal_timeframe
        e1 = new_message(source="trading_engine", destination="ai_orchestrator", message_type="ANALYSIS_REQUESTED",
                         data_timestamp_utc=market.data_timestamp(tf), timeframe=tf, status="COMPLETED",
                         payload={"market_context": market_context(market, bars_per_timeframe=self.bars_per_timeframe,
                                                                   indicators=self.indicators),
                                  "macro_context": macro_context or {"news_sources": [], "macro_data": {},
                                                                     "time_window": None}})
        rep = CycleReport(e1["correlation_id"])
        self._record(rep, e1)
        e2, rep.regime_state = self.regime.run(e1, market, regime_state)
        e3 = self.ml.run(e1, market)
        self._record(rep, e2, e3)
        phase2 = self.strategy.run(e2, e3, market, mode=mode, block=block, position=position)
        self._record(rep, *phase2)
        e4 = phase2[-1]
        if e4["message_type"] == "NO_SETUP":
            rep.outcome = "NO_SETUP"
            return rep
        if e4["status"] != "COMPLETED":
            rep.outcome = "STRATEGY_ENGINE_ERROR"
            return rep
        res = self.orch.run_cycle(e1, [e2, e3, e4])   # el orquestador registra E5..E8 en el mismo store
        rep.llm_calls = len(res.outputs)                 # una salida por agente invocado
        rep.events.extend(res.events)
        if res.outcome != "COMPLETED":
            rep.outcome = f"AI_{res.outcome}"
            return rep
        e8 = next(m for m in res.events if m["message_type"] == "DECISION_SYNTHESIS_COMPLETED")
        rep.normalization = normalize(e4, e8)
        if rep.normalization.proposal_message is not None:
            self._record(rep, rep.normalization.proposal_message)
            rep.outcome = "PROPOSAL_EMITTED"
        elif rep.normalization.rejection_message is not None:      # B.10 (CR-019): rechazo registrado en E9
            self._record(rep, rep.normalization.rejection_message)
            rep.outcome = "PROPOSAL_REJECTED"
        else:
            rep.outcome = "NO_PROPOSAL"
        return rep
