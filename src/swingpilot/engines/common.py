"""Base común de los motores de la Fase 2 (api_contracts.md §3.8 B.0; CR-018; REQ-G-057, REQ-G-070).

Los motores son deterministas y no llaman a la API de Claude (REQ-G-057, TC-AC-07). Su
entrada es un `MarketInput` con velas cerradas por temporalidad; cada evento se construye
con el sobre universal (§1), se valida contra su esquema (§3.8) y se registra.
"""
from dataclasses import dataclass, field

from swingpilot.contracts import derive_message
from swingpilot.market_data.candles import Candle, interval_ms, last_closed_open_time, ms_to_iso

from .schemas import validate_engine_payload

TF_INTERVAL = {"D1": "1d", "H4": "4h", "H1": "1h"}


@dataclass(frozen=True)
class MarketInput:
    """Velas cerradas por temporalidad (orden creciente), fuente y hora del servidor de Binance."""
    candles: dict[str, list[Candle]]
    source: str                         # binance_ws | binance_rest | snapshot
    server_time_ms: int
    snapshot_id: str | None = None

    def bars(self, tf: str) -> list[Candle]:
        return self.candles.get(tf, [])

    def has_last_closed(self, tf: str) -> bool:
        """REQ-G-070: la última vela cerrada esperada a la hora del servidor está disponible."""
        b = self.bars(tf)
        return bool(b) and b[-1].open_time == last_closed_open_time(TF_INTERVAL[tf], self.server_time_ms)

    def data_ref(self, tf: str) -> dict:
        b = self.bars(tf)
        return {"last_closed_open_time_utc": ms_to_iso(b[-1].open_time) if b else None,
                "bars_used": len(b), "source": self.source, "snapshot_id": self.snapshot_id}

    def data_timestamp(self, tf: str) -> str:
        """Cierre (según Binance) de la última vela usada: tiempo de mercado (B.0.2)."""
        b = self.bars(tf)
        if not b:
            return ms_to_iso(last_closed_open_time(TF_INTERVAL[tf], self.server_time_ms) + interval_ms(TF_INTERVAL[tf]))
        return ms_to_iso(b[-1].close_time + 1)


def base_payload(engine: str, engine_version: str, spec_version: str | None, result_status: str,
                 data_refs: dict, missing_data: list[str] | None = None, error: dict | None = None) -> dict:
    return {"engine": engine, "engine_version": engine_version, "spec_version": spec_version,
            "result_status": result_status, "data_refs": data_refs, "missing_data": list(missing_data or []),
            "error": error}


def engine_message(cause: dict, *, source: str, message_type: str, payload: dict, data_timestamp_utc: str,
                   timeframe: str | None, destination: str = "ai_orchestrator") -> dict:
    """Valida el payload (TC-MSG-004) y deriva el mensaje de `cause` (correlation/causation).
    Sobre FAILED si result_status = ERROR (B.7.1 punto 1)."""
    validate_engine_payload(message_type, payload)
    return derive_message(cause, source=source, destination=destination, message_type=message_type,
                          data_timestamp_utc=data_timestamp_utc, timeframe=timeframe, payload=payload,
                          status="FAILED" if payload["result_status"] == "ERROR" else "COMPLETED")


@dataclass
class EmitLog:
    messages: list[dict] = field(default_factory=list)
