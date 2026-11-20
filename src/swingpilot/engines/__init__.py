"""Motores deterministas de la Fase 2 y ciclo hasta E9 (FEAT-018..022; api_contracts.md §3.8; DEC-019).

Sin LLM (REQ-G-057), sin credenciales, sin órdenes. Sin estrategias ni clasificador de régimen
aprobados (DEC-018): el motor de estrategias corre vacío y el régimen publica UNCLASSIFIED.
"""
from .common import MarketInput
from .cycle import CycleReport, DecisionCycle, market_context
from .ml import MLEngine
from .normalizer import NormalizationResult, normalize, validate_trade_proposal
from .regime import RegimeEngine, RegimeState
from .schemas import EnginePayloadError, validate_engine_payload
from .strategy import (EntryEvaluation, EntryProposal, ExitProposal, OpenPosition, StopProposal,
                       StrategyEngine)

__all__ = ["MarketInput", "CycleReport", "DecisionCycle", "market_context", "MLEngine", "NormalizationResult",
           "normalize", "validate_trade_proposal", "RegimeEngine", "RegimeState", "EnginePayloadError",
           "validate_engine_payload", "EntryEvaluation", "EntryProposal", "ExitProposal", "OpenPosition",
           "StopProposal", "StrategyEngine"]
