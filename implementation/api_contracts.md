# SwingPilot — API Contracts v0.1

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** DRAFT — pendiente de verificación adversarial (G2) y aprobación humana (G3)

---

## 1. Contrato Universal de Mensajes

Todo evento o mensaje intercambiado entre componentes del sistema debe contener los siguientes campos (Principio D3, AI_INTEGRATION.md):

```json
{
  "message_id": "<uuid-v4>",
  "correlation_id": "<uuid-v4>",
  "causation_id": "<uuid-v4 | null>",
  "schema_version": "<semver>",
  "source": "<component_id>",
  "destination": "<component_id>",
  "message_type": "<EVENT_TYPE>",
  "timestamp_utc": "<ISO8601>",
  "data_timestamp_utc": "<ISO8601>",
  "asset": "BTC/USDT",
  "timeframe": "<D1|H4|H1|null>",
  "payload": {},
  "status": "<PENDING|PROCESSING|COMPLETED|FAILED>"
}
```

**Reglas:**
- `correlation_id`: trazabilidad de toda la cadena de un análisis/operación
- `causation_id`: mensaje padre que causó este mensaje (null si es origen)
- `data_timestamp_utc`: cuándo fueron generados los datos en el payload (distinto de `timestamp_utc`)
- `schema_version` sigue semver; cambios incompatibles requieren nueva versión mayor
- Ausencia de respuesta ≠ aprobación

---

## 2. Catálogo de Tipos de Eventos

| Tipo | Productor | Consumidor Principal | Descripción |
|---|---|---|---|
| ANALYSIS_REQUESTED | Trading Engine | AI Orchestrator | Solicitud de análisis con contexto |
| MARKET_ANALYSIS_COMPLETED | Market Analyst | AI Orchestrator | Análisis técnico/estructura del mercado |
| MACRO_ANALYSIS_COMPLETED | Macro Analyst | AI Orchestrator | Contexto macroeconómico y noticias |
| ML_INFERENCE_COMPLETED | ML Engine | AI Orchestrator | Resultado de inferencia ML |
| REGIME_CLASSIFIED | Regime Engine | AI Orchestrator | Clasificación de régimen de mercado |
| STRATEGY_CANDIDATE | Strategy Engine | AI Orchestrator | Estrategia candidata con condiciones versionadas |
| DECISION_SYNTHESIS_COMPLETED | Decision Synthesis | AI Orchestrator | Síntesis final con TRADE_PROPOSAL o descarte |
| TRADE_PROPOSAL | Decision Synthesis | Risk Manager | Propuesta de operación (no es orden) |
| RISK_APPROVED | Risk Manager | Telegram Bot / Autorización humana | Propuesta aprobada técnicamente |
| RISK_REJECTED | Risk Manager | AI Orchestrator / Audit | Propuesta rechazada con motivos |
| RISK_REQUIRES_REVIEW | Risk Manager | Telegram Bot | Requiere intervención humana |
| ORDER_SUBMITTED | Execution Engine | Binance / Audit | Orden enviada al exchange |
| ORDER_PARTIALLY_FILLED | Execution Engine | Portfolio Manager / Audit | Ejecución parcial registrada |
| ORDER_FILLED | Execution Engine | Portfolio Manager / Fiscal Ledger | Ejecución completa |
| ORDER_CANCELLED | Execution Engine | Portfolio Manager / Audit | Orden cancelada |
| ORDER_REJECTED | Execution Engine | Audit | Orden rechazada por Binance |
| STOP_ORDER_PLACED | Execution Engine | Portfolio Manager / Audit | Stop colocado en Binance tras compra ejecutada (REQ-G-031) |
| STOP_ORDER_REPLACED | Execution Engine | Portfolio Manager / Audit | Stop cancelado y reemplazado en Binance por modificación permitida (REQ-G-027) |
| STOP_ORDER_FAILED | Execution Engine | Risk Manager / Telegram Bot / Audit | No se pudo colocar o reemplazar el stop en Binance; dispara Fail-Closed |
| STARTUP_RECONCILIATION_COMPLETED | Execution Engine | Risk Manager / Telegram Bot / Audit | Resultado de la reconciliación de arranque: órdenes adoptadas por identificador de cliente, autorizaciones invalidadas, stops verificados (REQ-G-032) |
| AUTHORIZATION_INVALIDATED | Execution Engine | Audit / Telegram Bot | Autorización humana no enviada invalidada al reiniciar (REQ-G-032) |
| UNAUTHORIZED_APPROVAL_ATTEMPT | Telegram Bot | Audit | Mensaje de aprobación de un remitente distinto al propietario; ignorado (REQ-G-033) |
| NO_SETUP | Strategy Engine | AI Orchestrator / Audit | Sin STRATEGY_CANDIDATE en el filtro determinista; fin del ciclo sin llamadas a LLM (CR-004) |
| RISK_ANALYSIS_COMPLETED | Risk Analyst | Telegram Bot / Audit | Evaluación consultiva sobre una propuesta con RISK_APPROVED (REQ-G-055, CR-004) |
| HEARTBEAT | Trading Engine | Servicio externo de vigilancia | Latido periódico sin datos sensibles (REQ-G-035) |
| PUBLIC_IP_CHANGED | Trading Engine | Risk Manager / Telegram Bot / Audit | IP pública distinta a la registrada en Binance; dispara Fail-Closed (REQ-G-036) |
| OPERATION_STATE_CHANGED | Execution Engine | Audit | Transición de estado de una operación: estado anterior, nuevo, motivo, `correlation_id` (REQ-G-037, CR-005) |
| AUTHORIZATION_EXPIRED | Backend de Autorización | Telegram Bot / Audit | Autorización sin respuesta dentro de los 30 min; operación en AUTH_EXPIRED (REQ-G-039, CR-005) |
| AI_BUDGET_WARNING | AI Orchestrator | Telegram Bot / Audit | Gasto mensual de IA alcanzó $4 (80% del tope de $5) (REQ-G-096, CR-006) |
| PROTECTIVE_CLOSE_SUBMITTED | Execution Engine | Risk Manager / Telegram Bot / Audit | Venta a mercado por posición sin stop activo con el precio en o bajo el stop; pasa a MANUAL_REVIEW (REQ-G-031, CR-005) |

**Identificador de cliente en órdenes (REQ-G-032, CR-003):** toda orden enviada a Binance (compra, venta, stop) incluye un identificador de cliente derivado de forma determinista del `correlation_id` y de la secuencia de la orden dentro del ciclo. Es la clave de idempotencia ante reintentos. No sustituye al `order_id` de Binance registrado en `trades.db`. Formato exacto: PENDING (FASE 2).

**Nota:** Los nombres definitivos de tipos de eventos se confirman al definir el catálogo de producción.

---

## 3. Contratos de Agentes LLM

**Valores de `model_id` (REQ-G-095, CR-006):** `claude-haiku-5-5` para Market Analyst, Macro Analyst, Strategy Analyst y Risk Analyst; `claude-sonnet-5-5` para Decision Synthesis. Cada contrato de salida de esta sección es el esquema de la salida estructurada (`output_config.format`) de su agente; las llamadas no incluyen herramientas.

### 3.1 Contrato de Entrada — Market Analyst

```json
{
  "market_context": {
    "asset": "BTC/USDT",
    "timeframes": ["D1", "H4", "H1"],
    "ohlcv": {
      "D1": [/* array de {timestamp, open, high, low, close, volume} */],
      "H4": [],
      "H1": []
    },
    "indicators": {
      "D1": {/* nombre_indicador: valor */},
      "H4": {},
      "H1": {}
    },
    "data_timestamp_utc": "<ISO8601>",
    "data_source": "<exchange>"
  },
  "analysis_instructions": {
    "focus": ["price_structure", "trend", "support_resistance", "volatility"],
    "prompt_version": "<semver>"
  }
}
```

### 3.2 Contrato de Salida — Market Analyst

```json
{
  "analysis_id": "<uuid>",
  "correlation_id": "<uuid>",
  "analyst": "market_analyst",
  "model_id": "<claude-model-id>",
  "prompt_version": "<semver>",
  "data_timestamp_utc": "<ISO8601>",
  "analysis_timestamp_utc": "<ISO8601>",
  "observations": [
    {
      "timeframe": "H4",
      "observation": "<descripción>",
      "evidence": "<precio/indicador/zona específica>",
      "confidence": "HIGH|MEDIUM|LOW"
    }
  ],
  "key_levels": {
    "support": [],
    "resistance": []
  },
  "trend_assessment": {
    "D1": "BULLISH|BEARISH|NEUTRAL|UNCLEAR",
    "H4": "BULLISH|BEARISH|NEUTRAL|UNCLEAR"
  },
  "limitations": ["<lista de limitaciones del análisis>"],
  "status": "COMPLETED|INSUFFICIENT_DATA|ERROR"
}
```

### 3.3 Contrato de Salida — Decision Synthesis

```json
{
  "synthesis_id": "<uuid>",
  "correlation_id": "<uuid>",
  "model_id": "<claude-model-id>",
  "prompt_version": "<semver>",
  "timestamp_utc": "<ISO8601>",
  "decision": "TRADE_PROPOSAL|INSUFFICIENT_INFO|DISCARD|DISAGREEMENT",
  "trade_proposal": {
    "asset": "BTC/USDT",
    "direction": "LONG",
    "entry_zone": {"min": 0.0, "max": 0.0},
    "stop_loss": 0.0,
    "take_profit": null,
    "strategy_id": "<strategy_id>",
    "strategy_version": "<semver>",
    "rationale": "<justificación basada en evidencia>",
    "conflicting_signals": ["<lista de señales contradictorias>"],
    "uncertainty_notes": "<incertidumbres identificadas>"
  },
  "agent_summaries": {
    "market_analyst": {"key_finding": "<>", "confidence": "HIGH|MEDIUM|LOW"},
    "macro_analyst": {"key_finding": "<>", "confidence": "HIGH|MEDIUM|LOW"},
    "strategy_analyst": {"key_finding": "<>", "confidence": "HIGH|MEDIUM|LOW"},
    "risk_analyst": {"key_finding": "<>", "concerns": []}
  },
  "status": "COMPLETED|ERROR"
}
```

---

## 4. Contratos del Risk Manager

### 4.1 Contrato de Entrada — Risk Manager (TRADE_PROPOSAL)

```json
{
  "proposal_id": "<uuid>",
  "correlation_id": "<uuid>",
  "schema_version": "1.0.0",
  "timestamp_utc": "<ISO8601>",
  "asset": "BTC/USDT",
  "direction": "LONG",
  "entry_price_target": 0.0,
  "stop_loss_price": 0.0,
  "strategy_id": "<strategy_id>",
  "strategy_version": "<semver>",
  "exit_mechanism": {
    "type": "STOP_LOSS|TRAILING_STOP|TARGET_PRICE|MANUAL",
    "trigger_condition": "<condición exacta de activación>",
    "execution_method": "<cómo se envía la orden>",
    "failure_procedure": "<procedimiento ante fallo>"
  }
}
```

### 4.2 Contrato de Salida — Risk Manager (RISK_APPROVED)

```json
{
  "authorization_id": "<uuid>",
  "proposal_id": "<uuid>",
  "correlation_id": "<uuid>",
  "schema_version": "1.0.0",
  "result": "RISK_APPROVED",
  "timestamp_utc": "<ISO8601>",
  "valid_until_utc": "<ISO8601>",
  "authorized_instrument": "BTC/USDT",
  "authorized_direction": "LONG",
  "authorized_quantity_max": 0.0,
  "authorized_entry_price_max": 0.0,
  "authorized_stop_loss_min": 0.0,
  "risk_calculations": {
    "equity_at_evaluation": 0.0,
    "risk_budget": 0.0,
    "calculated_quantity": 0.0,
    "effective_risk": 0.0,
    "risk_percentage": 0.0,
    "monthly_drawdown_at_evaluation": 0.0,
    "monthly_trades_count": 0
  },
  "risk_rules_version": "<semver>",
  "requires_human_approval": true
}
```

### 4.3 Contrato de Salida — Risk Manager (RISK_REJECTED)

```json
{
  "rejection_id": "<uuid>",
  "proposal_id": "<uuid>",
  "correlation_id": "<uuid>",
  "result": "RISK_REJECTED",
  "timestamp_utc": "<ISO8601>",
  "reasons": [
    {
      "invariant": "INV-001|INV-002|...",
      "description": "<descripción del incumplimiento>",
      "values": {
        "limit": 0.0,
        "actual": 0.0
      }
    }
  ],
  "active_locks": ["MONTHLY_DRAWDOWN_LOCK", "LOSS_STREAK_LOCK"]
}
```

---

## 5. Contrato de Autorización Humana

La autorización humana del propietario debe incluir:

```json
{
  "human_authorization_id": "<uuid>",
  "risk_authorization_id": "<uuid>",
  "correlation_id": "<uuid>",
  "authorized_by": "OWNER",
  "authorization_timestamp_utc": "<ISO8601>",
  "valid_until_utc": "<ISO8601>",
  "instrument": "BTC/USDT",
  "direction": "LONG",
  "max_quantity": 0.0,
  "price_limits": {
    "entry_max": 0.0,
    "stop_loss_min": 0.0
  },
  "authorization_channel": "TELEGRAM",
  "authorization_reference": "<id del mensaje Telegram>"
}
```

**Reglas de validación antes de ejecución:**
- `human_authorization_id` debe existir y estar vinculado a `risk_authorization_id`
- `valid_until_utc` no puede estar en el pasado; se fija en el envío de la solicitud por Telegram + 30 min, con la hora del backend (REQ-G-039, CR-005)
- El instrumento y dirección deben coincidir exactamente con la orden a enviar
- El Risk Manager re-verifica condiciones en el momento de ejecución

---

## 6. Contrato de Evento de Auditoría

Cada evento de auditoría del Risk Manager contiene (mínimo 12 campos):

```json
{
  "audit_event_id": "<uuid>",
  "correlation_id": "<uuid>",
  "causation_id": "<uuid>",
  "event_type": "EQUITY_UPDATE|RISK_BUDGET_CALCULATION|POSITION_SIZING|TRADE_VALIDATION|TRADE_REJECTION|HUMAN_AUTHORIZATION|ORDER_EXECUTION|STOP_LOSS_MODIFICATION|POSITION_CLOSE|REALIZED_LOSS|DRAWDOWN_UPDATE|LOCK_ACTIVATED|LOCK_RELEASED|BINANCE_SYNC_ERROR",
  "timestamp_utc": "<ISO8601>",
  "component": "RISK_MANAGER",
  "component_version": "<semver>",
  "inputs": {},
  "formula_applied": "<fórmula exacta>",
  "result": {},
  "risk_manager_state_before": ["<estados activos>"],
  "risk_manager_state_after": ["<estados activos>"],
  "policy_version": "<semver — versión de RISK_POLICY vigente al momento del evento>"
}
```

Alias: `audit_event_id` = `event_id` (REQ-5032). El campo `component_version` registra la versión del Risk Manager; `policy_version` registra la versión de RISK_POLICY aplicada.

**Restricción:** Los registros de auditoría son inmutables. No pueden modificarse retroactivamente.

---

## 7. Contrato del Fiscal Ledger

### 7.1 Inserción en trades.db

Cada inserción debe provenir del Execution Engine tras un ORDER_FILLED confirmado:

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| fecha_utc | TIMESTAMP | Sí | Timestamp de ejecución en Binance (ISO 8601 UTC) |
| fecha_mxn | DATE | Sí | Fecha en zona horaria MX para declaración SAT |
| activo | VARCHAR(10) | Sí | 'BTC/USDT' |
| accion | VARCHAR(4) | Sí | 'BUY' o 'SELL' |
| cantidad | DECIMAL(18,8) | Sí | Cantidad en BTC |
| precio_usdt | DECIMAL(18,6) | Sí | Precio de ejecución en USDT |
| monto_usdt | DECIMAL(18,4) | Sí | cantidad × precio_usdt |
| tc_mxn_usd | DECIMAL(10,6) | Sí | BCI Banxico del día de la operación |
| monto_mxn | DECIMAL(18,4) | Sí | monto_usdt × tc_mxn_usd |
| comisiones_mxn | DECIMAL(10,4) | Sí | Comisiones convertidas a MXN |
| order_id | VARCHAR(64) | Sí | Único; proveniente de Binance |
| metodo_costo | VARCHAR(10) | Sí | Siempre 'FIFO' |
| exchange | VARCHAR(20) | Sí | Siempre 'Binance' |

**PENDING:** `costo_acum_mxn` y `ganancia_mxn` son calculados por el Fiscal Ledger usando FIFO; no se reciben desde fuera. Ver REQ-G-112 (vistas resumen_anual y posicion_abierta) y REQ-G-113 (metodología FIFO + BCI Banxico) en requirements.md para la especificación completa del cálculo.

---

## 8. Versioning de Contratos

| Artefacto | Versioning | Política de cambio |
|---|---|---|
| Contratos JSON | semver | Cambios incompatibles → mayor; additive → menor |
| Prompts LLM | semver | Cualquier cambio funcional → nueva versión |
| Modelos ML | ID + versión | Nunca reutilizar un ID para un modelo diferente |
| Estrategias | ID + versión | La versión de estrategia se incluye en TRADE_PROPOSAL |
| Risk rules | semver | Se registra en cada RISK_APPROVED |

---

## 9. Parámetros PENDING

| ID | Campo afectado | Descripción |
|---|---|---|
| REQ-G-P01 | `tc_mxn_usd` | Fuente de conversión USDT/MXN |
| REQ-G-P02 | `tc_mxn_usd` | Antigüedad máxima aceptable del tipo de cambio |
| REQ-G-P03 | `comisiones_mxn` | Comisión efectiva de Binance |
| REQ-G-P04 | Fórmula sizing | Reserva de slippage |
| REQ-G-P05 | `authorized_quantity_max` | stepSize, minQty, minNotional de Binance |
| REQ-G-P06 | Mecanismo de aprobación | Formato técnico de la autorización Telegram |

---

*Fin de api_contracts.md*
