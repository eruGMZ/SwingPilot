# SwingPilot — API Contracts v1.9

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** v1.9 (CR-021, DEC-023, 2026-11-24: durabilidad confirmada como condición de acceso a datos; sin cambios en este documento) — v1.8 (CR-020, DEC-021, 2026-11-24: contabilidad de pruebas de REQ-G-P17; sin cambios en este documento) — v1.7 (CR-019, DEC-020, 2026-11-20: evento PROPOSAL_NORMALIZATION_REJECTED) — v1.6 (CR-018, DEC-019, 2026-11-20) — v1.5 — v1.0 APROBADO por el propietario (G3, 2026-11-18: "APRUEBO EL CONTRATO TÉCNICO v1.0"); v1.1 aplicó CR-011 (DEC-011); v1.2 aplicó CR-012 (DEC-012); v1.3 aplicó CR-013 (DEC-013); v1.4 aplicó CR-015 (DEC-014) y v1.5 aplica CR-016 (DEC-015), todas aprobadas el 2026-11-19; incorpora CR-001..CR-013, CR-015 y CR-016. Cambios posteriores solo mediante solicitud de cambio aprobada y versionado

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
| NO_SETUP | Strategy Engine | AI Orchestrator / Audit | Sin STRATEGY_CANDIDATE en el filtro determinista; fin del ciclo sin llamadas a LLM (CR-004). También se emite con 2+ candidatos de entrada en el mismo ciclo (aunque coincidan); el evento registra los candidatos descartados y el motivo (CR-011; motivos estructurados en §3.8 B.7, CR-018) |
| RISK_ANALYSIS_COMPLETED | Risk Analyst | Telegram Bot / Audit | Evaluación consultiva sobre una propuesta con RISK_APPROVED (REQ-G-055, CR-004) |
| HEARTBEAT | Trading Engine | Servicio externo de vigilancia | Latido periódico sin datos sensibles (REQ-G-035) |
| PUBLIC_IP_CHANGED | Trading Engine | Risk Manager / Telegram Bot / Audit | IP pública distinta a la registrada en Binance; dispara Fail-Closed (REQ-G-036) |
| OPERATION_STATE_CHANGED | Execution Engine | Audit | Transición de estado de una operación: estado anterior, nuevo, motivo, `correlation_id` (REQ-G-037, CR-005) |
| AUTHORIZATION_EXPIRED | Backend de Autorización | Telegram Bot / Audit | Autorización sin respuesta dentro de los 30 min; operación en AUTH_EXPIRED (REQ-G-039, CR-005) |
| AI_BUDGET_WARNING | AI Orchestrator | Telegram Bot / Audit | Gasto mensual de IA alcanzó $4 (80% del tope de $5) (REQ-G-096, CR-006) |
| PROTECTIVE_CLOSE_SUBMITTED | Execution Engine | Risk Manager / Telegram Bot / Audit | Venta a mercado por posición sin stop activo con el precio en o bajo el stop; pasa a MANUAL_REVIEW (REQ-G-031, CR-005) |
| STRATEGY_ANALYSIS_COMPLETED | Strategy Analyst | AI Orchestrator | Evaluación de las estrategias candidatas (§3.6); consultiva, no modifica estrategias (REQ-G-054, CR-015) |
| STRATEGY_EXIT_SIGNAL | Strategy Engine | Execution Engine / Portfolio Manager / Audit | Señal de salida por condición de la estrategia; autónoma, sin autorización humana (DEC-011; §3.8 B.5; CR-018) |
| STOP_ADJUSTMENT_REQUESTED | Strategy Engine | Risk Manager / Execution Engine / Audit | Solicitud de subir el stop (trailing); nunca es una modificación ejecutada ni autoriza reducir protecciones; el Risk Manager valida INV-009 (§3.8 B.6; CR-018, DEC-018) |
| PROPOSAL_NORMALIZATION_REJECTED | AI Orchestrator (normalizador determinista, §3.8 B.8) | Audit | La síntesis propuso operar pero no se emite TRADE_PROPOSAL: síntesis inconsistente con el candidato o propuesta normalizada fuera de §4.1. Fin del ciclo; no es una decisión, no llega al Risk Manager ni autoriza nada (§3.8 B.10; CR-019, DEC-020) |

**Identificador de cliente en órdenes (REQ-G-032, CR-003):** toda orden enviada a Binance (compra, venta, stop) incluye un identificador de cliente derivado de forma determinista del `correlation_id` y de la secuencia de la orden dentro del ciclo. Es la clave de idempotencia ante reintentos. No sustituye al `order_id` de Binance registrado en `trades.db`. Formato exacto: PENDING (FASE 2).

**Nota:** Los nombres definitivos de tipos de eventos se confirman al definir el catálogo de producción.

---

## 3. Contratos de Agentes LLM

**Valores de `model_id` (REQ-G-095, CR-006):** `claude-haiku-5-5` para Market Analyst, Macro Analyst, Strategy Analyst y Risk Analyst; `claude-sonnet-5-5` para Decision Synthesis. Cada contrato de salida de esta sección es el esquema de la salida estructurada (`output_config.format`) de su agente; las llamadas no incluyen herramientas.

### 3.0 Campos comunes (D2 de AI_INTEGRATION.md; CR-008)

**Toda entrada de agente** incluye:

```json
{
  "correlation_id": "<uuid>",
  "causation_id": "<uuid>",
  "schema_version": "<semver>",
  "agent": "market_analyst|macro_analyst|strategy_analyst|decision_synthesis|risk_analyst",
  "data_timestamp_utc": "<ISO8601>",
  "context": {}
}
```

**Toda salida de agente** incluye:

```json
{
  "analysis_id": "<uuid>",
  "correlation_id": "<uuid>",
  "causation_id": "<uuid>",
  "schema_version": "<semver>",
  "agent": "<igual que en la entrada>",
  "model_id": "<claude-model-id>",
  "prompt_version": "<semver>",
  "data_timestamp_utc": "<ISO8601>",
  "analysis_timestamp_utc": "<ISO8601>",
  "sources": ["<fuentes y referencias utilizadas>"],
  "missing_data": ["<datos faltantes declarados por el agente o, en Decision Synthesis, propagados desde la Fase 3 (§3.3); nunca inventados>"],
  "status": "COMPLETED|INSUFFICIENT_DATA|ERROR"
}
```

Cada afirmación de una salida lleva `statement_type`: `FACT|INFERENCE|RECOMMENDATION`. Los errores se representan de forma estructurada (`status: ERROR` con `error: {code, message}`). Las secciones 3.1–3.7 muestran solo los campos específicos de cada agente, que se añaden a los comunes.

**Campos comunes fijados por el Orchestrator (CR-016 E.1):** `analysis_id`, `correlation_id`, `causation_id`, `schema_version`, `agent`, `model_id` (modelo efectivo devuelto por la API), `prompt_version`, `data_timestamp_utc` y `analysis_timestamp_utc` los fija el AI Orchestrator, no el LLM. El LLM produce solo el cuerpo de su contrato (campos específicos, `sources`, `missing_data` y `status` COMPLETED o INSUFFICIENT_DATA); `status: ERROR` y `error` también los fija el Orchestrator.

### 3.1 Contrato de Entrada — Market Analyst

**Contexto mínimo (CR-016 E.3):** el AI Orchestrator entrega en `context` solo los campos de este contrato (`asset`, `timeframes`, `ohlcv`, `indicators`, `data_source`); cualquier otro campo se descarta.

```json
{
  "context": {
    "asset": "BTC/USDT",
    "timeframes": ["D1", "H4", "H1"],
    "ohlcv": {
      "D1": [/* array de {timestamp, open, high, low, close, volume}; solo velas cerradas */],
      "H4": [],
      "H1": []
    },
    "indicators": {
      "D1": {/* nombre_indicador: valor */},
      "H4": {},
      "H1": {}
    },
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
  "observations": [
    {
      "timeframe": "H4",
      "observation": "<descripción>",
      "evidence": "<precio/indicador/zona específica>",
      "confidence": "HIGH|MEDIUM|LOW",
      "statement_type": "FACT|INFERENCE|RECOMMENDATION"
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
  "limitations": ["<lista de limitaciones del análisis>"]
}
```

### 3.3 Contrato de Salida — Decision Synthesis

Entrada: las salidas de Fase 2 (REGIME_CLASSIFIED, ML_INFERENCE_COMPLETED, STRATEGY_CANDIDATE) y de Fase 3 (Market, Macro y Strategy Analyst), referenciadas por su `analysis_id` en `context.inputs`. No recibe la salida del Risk Analyst (CR-004).

**Normalización (CR-018, §3.8 B.8):** la TRADE_PROPOSAL de §4.1 la construye un normalizador determinista desde el STRATEGY_CANDIDATE; la `trade_proposal` de esta salida debe ser consistente con él (misma estrategia y versión, stop idéntico, `entry_zone` contenida, `take_profit` nulo o igual) o no se emite propuesta.

**Datos faltantes propagados (CR-016):** el AI Orchestrator añade de forma determinista al `missing_data` de esta salida los datos faltantes declarados por la Fase 3, con el formato `"<agente>: <elemento>"` (`<agente>` ∈ `market_analyst`, `macro_analyst`, `strategy_analyst`). Si un agente respondió `INSUFFICIENT_DATA` sin detallar, se añade `"<agente>: INSUFFICIENT_DATA"`. Los elementos propagados van después de los que declaró la síntesis y sin duplicados. No se inventa ni se elimina nada: solo se copia lo declarado por la Fase 3. La salida ampliada se valida de nuevo contra este contrato; si no valida, la síntesis queda en `ERROR` (`OUT_OF_CONTRACT`).

**Análisis citados (CR-016 E.2):** `input_analysis_ids` debe contener exactamente los `analysis_id` de los tres análisis de la Fase 3 (Market, Macro y Strategy Analyst), en cualquier orden; vacío, incompleto o con identificadores ajenos se trata como fuera de contrato (`ERROR`, `OUT_OF_CONTRACT`).

```json
{
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
    "strategy_analyst": {"key_finding": "<>", "confidence": "HIGH|MEDIUM|LOW"}
  },
  "input_analysis_ids": ["<analysis_id de los tres análisis de la Fase 3 (CR-016 E.2)>"]
}
```

### 3.4 Contrato de Entrada — Macro Analyst

**Contexto mínimo (CR-016 E.3):** el AI Orchestrator entrega en `context` solo `news_sources`, `macro_data` y `time_window`; cualquier otro campo se descarta.

```json
{
  "context": {
    "news_sources": [{"source": "<>", "items": []}],
    "macro_data": {},
    "time_window": {"from_utc": "<ISO8601>", "to_utc": "<ISO8601>"}
  }
}
```

### 3.5 Contrato de Salida — Macro Analyst

Fuente: AI_INTEGRATION.md, «Macro Analyst». No puede convertir una noticia en señal de entrada.

```json
{
  "events": [
    {
      "description": "<evento relevante>",
      "potential_impact": "<impacto potencial>",
      "time_horizon": "<horizonte temporal>",
      "source": "<fuente>",
      "publication_date": "<ISO8601>",
      "confirmation": "CONFIRMED|RUMOR|SPECULATION",
      "uncertainty": "HIGH|MEDIUM|LOW",
      "statement_type": "FACT|INFERENCE|RECOMMENDATION"
    }
  ]
}
```

### 3.6 Contratos de Entrada y Salida — Strategy Analyst

Entrada: `context.strategy_candidates` = STRATEGY_CANDIDATE del Strategy Engine. Fuente: AI_INTEGRATION.md, «Strategy Analyst». No modifica estrategias aprobadas ni ejecuta.

```json
{
  "evaluations": [
    {
      "strategy_id": "<strategy_id>",
      "strategy_version": "<semver>",
      "logic_assessment": "<>",
      "activation_conditions_assessment": "<>",
      "signal_invalidation_coherence": "<>",
      "weakening_conditions": ["<>"],
      "comparison": "<solo con evidencia suficiente; null si no>",
      "discard_reasons": ["<>"],
      "statement_type": "FACT|INFERENCE|RECOMMENDATION"
    }
  ]
}
```

### 3.7 Contratos de Entrada y Salida — Risk Analyst

Entrada: `context.proposal` (propuesta con RISK_APPROVED) y `context.system_state`. Fuente: AI_INTEGRATION.md, «Risk Analyst». Consultivo; no aprueba ni revierte decisiones del Risk Manager.

```json
{
  "hidden_risks": ["<>"],
  "entry_stop_target_inconsistencies": ["<>"],
  "external_event_exposure": ["<>"],
  "operational_data_risks": ["<>"],
  "challenged_assumptions": ["<>"],
  "advisory_only": true
}
```

---


### 3.8 Contratos de los motores de la Fase 2 (CR-018, DEC-018, DEC-019)

Transcripción de las secciones B.0–B.8 aprobadas de `harness/change_requests/CR-018_contratos-motores-cuantitativos.md` rev. 3. Los ejemplos son ilustrativos; los valores marcados PENDING no son parámetros aprobados.

#### B.0 Reglas comunes de los eventos de motores deterministas

Aplican a `REGIME_CLASSIFIED`, `ML_INFERENCE_COMPLETED`, `STRATEGY_CANDIDATE`, `STRATEGY_EXIT_SIGNAL` y `NO_SETUP`.

1. **Sobre:** contrato universal (api_contracts.md §1) sin cambios. `asset` = `BTC/USDT`. `message_type` = el tipo del evento. `status` del sobre: `COMPLETED` si el motor terminó, aunque el resultado sea insuficiencia de datos; `FAILED` solo si el motor no pudo producir un payload válido.
2. **Tiempos:** `data_timestamp_utc` = hora de cierre (según Binance) de la última vela cerrada usada, en la temporalidad de referencia del motor. `timestamp_utc` = hora de emisión. Son distintos por diseño (REQ-G-070: tiempo de mercado frente a tiempo de procesamiento).
3. **Campos comunes del payload:**

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `engine` | enum `regime_engine \| ml_engine \| strategy_engine` | Sí | Debe coincidir con `source` del sobre |
| `engine_version` | semver | Sí | Versión del código del motor |
| `spec_version` | semver \| null | Sí | Versión de la especificación aprobada (clasificador, modelo o conjunto de estrategias); null solo si no hay especificación aprobada |
| `result_status` | enum `COMPLETED \| INSUFFICIENT_DATA \| ERROR` | Sí | Resultado del cálculo |
| `data_refs` | objeto | Sí | Por temporalidad usada (`D1`, `H4`, `H1`): `last_closed_open_time_utc`, `bars_used`, `source` (`binance_ws \| binance_rest \| snapshot`) y `snapshot_id` (null en vivo) |
| `missing_data` | lista de cadenas | Sí | Datos faltantes detectados; vacía si no hay. Nunca se inventan |
| `error` | objeto \| null | Sí | `{code, message}` si `result_status = ERROR`; null en otro caso |

4. **Códigos de error** (`error.code`): `DATA_UNAVAILABLE` (falta la última vela cerrada esperada), `DATA_STALE`, `DATA_INCONSISTENT` (duplicados, huecos o timestamps fuera de orden), `UPSTREAM_ERROR` (un evento previo del ciclo en ERROR), `SPEC_NOT_FOUND`, `INVALID_STOP_REQUEST` (B.6), `INTERNAL_ERROR`.
5. **Insuficiencia:** `INSUFFICIENT_DATA` cuando hay datos válidos pero no alcanzan (p. ej., menos velas que el periodo del indicador más largo). Siempre con `missing_data` no vacío.
6. **Sin puntuación de confianza para decidir** (CR-011). Los valores descriptivos (márgenes, mediciones) son informativos y ningún consumidor los usa para ponderar.
7. **Determinismo:** misma entrada (`data_refs`) y mismas versiones (`engine_version`, `spec_version`) dan el mismo payload, salvo `message_id` y `timestamp_utc` (TC-AC-07).
8. **Versión de esquema:** `schema_version` = `1.0.0` para cada payload nuevo; cambios aditivos → menor; incompatibles → mayor (api_contracts.md §8).

#### B.1 Catálogo de eventos (api_contracts.md §2)

- Productores y consumidores sin cambios para `REGIME_CLASSIFIED`, `ML_INFERENCE_COMPLETED` y `STRATEGY_CANDIDATE`.
- **Nuevo:** `STRATEGY_EXIT_SIGNAL`. Productor: Strategy Engine. Consumidores: Execution Engine (desde IMPL-5), Portfolio Manager y Audit. Es la señal de salida por condición de estrategia, autónoma y sin autorización humana (DEC-011).
- **Nuevo (B.6, DEC-018 decisión 2):** `STOP_ADJUSTMENT_REQUESTED`.
- `NO_SETUP`: se sustituye la nota «nombres definitivos PENDING» por la referencia a B.7.

#### B.2 `REGIME_CLASSIFIED` (E2)

- **Propósito:** clasificar las condiciones de mercado según el clasificador aprobado (DEC-017 Q42). No es decisor (REQ-G-071).
- **Productor:** Regime Engine. **Consumidores:** Strategy Engine (solo si una estrategia aprobada lo declara como condición), AI Orchestrator → Decision Synthesis (contexto), Audit.
- **Sobre:** `causation_id` = E1 (`ANALYSIS_REQUESTED`); `timeframe` = temporalidad de cálculo del clasificador.
- **Payload específico:**

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `classifier_id` | cadena | Sí | Identificador del clasificador aprobado |
| `regime_label` | cadena (enum del clasificador) | Sí | v1 (DEC-018 decisión 1): **tres categorías de volatilidad D1** por percentiles calculados solo con datos pasados; los nombres y cortes los fija la especificación aprobada (PENDING de justificación con Train). Las mediciones de dirección van solo en `measurements`, nunca como categoría. Valores reservados siempre válidos: `UNCLASSIFIED` (sin clasificador aprobado o resultado ≠ COMPLETED) y `TRANSITION` (cambio pendiente de confirmar) |
| `candidate_label` | cadena \| null | Sí | Clase candidata cuando `regime_label = TRANSITION`; null en otro caso |
| `previous_label` | cadena \| null | Sí | Etiqueta del ciclo anterior; null en el primer ciclo |
| `regime_since_utc` | ISO8601 \| null | Sí | Cierre de la vela en que empezó el régimen actual |
| `bars_in_regime` | entero ≥ 0 | Sí | Velas cerradas en el régimen actual |
| `measurements` | objeto `{nombre: número}` | Sí | Valores descriptivos usados por el clasificador (vacío si UNCLASSIFIED sin mediciones) |
| `threshold_margins` | objeto `{nombre: número}` | No | Distancia a cada umbral; solo informativa |

- **Validación:** `regime_label` ∈ enum del clasificador ∪ {UNCLASSIFIED, TRANSITION}; `result_status ≠ COMPLETED` ⇒ `regime_label = UNCLASSIFIED`; `TRANSITION` ⇒ `candidate_label` no nulo.
- **Ejemplo válido** (hasta que se apruebe Q42):

```json
{"engine": "regime_engine", "engine_version": "0.1.0", "spec_version": null,
 "result_status": "COMPLETED",
 "data_refs": {"D1": {"last_closed_open_time_utc": "2026-11-19T00:00:00Z", "bars_used": 400, "source": "binance_ws", "snapshot_id": null}},
 "missing_data": [], "error": null,
 "classifier_id": "none", "regime_label": "UNCLASSIFIED", "candidate_label": null,
 "previous_label": "UNCLASSIFIED", "regime_since_utc": null, "bars_in_regime": 0,
 "measurements": {}}
```

#### B.3 `ML_INFERENCE_COMPLETED` (E3)

- **Propósito:** publicar la inferencia del modelo activo aprobado, o declarar que no la hay. No es decisor paralelo (REQ-G-071); su salida no autoriza nada (REQ-G-105).
- **Productor:** ML Engine. **Consumidores:** Strategy Engine (familia ML-Based), AI Orchestrator → Decision Synthesis (contexto), Audit.
- **Sobre:** `causation_id` = E1.
- **Payload específico:**

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `inference_status` | enum `INFERENCE_AVAILABLE \| NO_ACTIVE_MODEL \| MODEL_SUSPENDED` | Sí | `NO_ACTIVE_MODEL`: ningún modelo en APPROVED (estado de IMPL-3, DEC-017 Q44). `MODEL_SUSPENDED`: degradación (REQ-G-P22) |
| `model_id` | cadena \| null | Sí | null si `NO_ACTIVE_MODEL` |
| `model_version` | cadena \| null | Sí | Nunca se reutiliza un ID para otro modelo (§8) |
| `model_hash` | cadena (SHA-256) \| null | Sí | Hash de datos + código + parámetros (REQ-G-P23) |
| `approval_ref` | cadena \| null | Sí | Experimento y registro HUMAN_REVIEW → APPROVED que permitió la promoción |
| `feature_set_version` | semver \| null | Sí | |
| `features_hash` | cadena \| null | Sí | Hash del vector de entrada usado |
| `prediction` | objeto \| null | Sí | Solo con `INFERENCE_AVAILABLE`: `{target, horizon_bars, timeframe, value, value_type}`. No incluye ninguna orden ni tamaño |
| `drift` | objeto \| null | Sí | `{psi_max, expectancy_last20, ic_lower_bound_oos, suspended_reason}` |
| `advisory_only` | `true` | Sí | Constante |

- **Validación:** `INFERENCE_AVAILABLE` ⇒ todos los campos de modelo y `prediction` no nulos; `NO_ACTIVE_MODEL` ⇒ campos de modelo y `prediction` nulos; `MODEL_SUSPENDED` ⇒ `prediction` nulo y `drift.suspended_reason` no nulo.
- **Regla de flujo:** con `inference_status ≠ INFERENCE_AVAILABLE`, ninguna estrategia de la familia ML-Based es elegible en ese ciclo.
- **Ejemplo válido (IMPL-3):**

```json
{"engine": "ml_engine", "engine_version": "0.1.0", "spec_version": null,
 "result_status": "COMPLETED", "data_refs": {}, "missing_data": [], "error": null,
 "inference_status": "NO_ACTIVE_MODEL", "model_id": null, "model_version": null,
 "model_hash": null, "approval_ref": null, "feature_set_version": null,
 "features_hash": null, "prediction": null, "drift": null, "advisory_only": true}
```

#### B.4 `STRATEGY_CANDIDATE` (E4)

- **Propósito:** un candidato de entrada long de una estrategia elegible, con todo lo necesario para que el Risk Manager evalúe la salida (INV-007).
- **Productor:** Strategy Engine. **Consumidores:** AI Orchestrator → Strategy Analyst (§3.6) y Decision Synthesis (§3.3), normalizador de TRADE_PROPOSAL (B.8), Audit.
- **Causa principal:** `causation_id` = `message_id` de E2 (`REGIME_CLASSIFIED`); `ml_inference_message_id` en el payload referencia E3 (resuelve «E2, E3» de data_flow.md §5).
- **Elegibilidad:** solo se emite para estrategias con `strategy_status = APPROVED` en modo Paper o Live. En modo Research (backtest) se aceptan estrategias en `RESEARCH`, y el evento lo declara.
- **Payload específico:**

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `candidate_id` | uuid | Sí | |
| `candidate_type` | enum `ENTRY_LONG` | Sí | Long-only (INV-005) |
| `strategy_id` | cadena | Sí | |
| `strategy_version` | semver | Sí | Se arrastra a TRADE_PROPOSAL (§8) |
| `strategy_family` | enum `TREND_FOLLOWING \| MOMENTUM \| MEAN_REVERSION \| BREAKOUT \| VOLATILITY_BASED \| ML_BASED` | Sí | |
| `strategy_status` | enum `APPROVED \| RESEARCH` | Sí | `RESEARCH` solo en modo Research |
| `operating_mode` | enum `RESEARCH \| PAPER \| LIVE` | Sí | |
| `experiment_ref` | cadena \| null | Sí | Experimento que aprobó la estrategia; obligatorio si APPROVED |
| `regime_message_id` | uuid | Sí | E2 |
| `ml_inference_message_id` | uuid | Sí | E3 |
| `signal_timeframe` | enum `D1 \| H4 \| H1` | Sí | |
| `signal_bar_close_utc` | ISO8601 | Sí | Cierre de la vela de la señal (vela cerrada, REQ-G-070) |
| `conditions` | lista de `{condition_id, description, timeframe, observed_value, threshold, operator, satisfied}` | Sí, ≥ 1 | Todas con `satisfied = true` (regla binaria) |
| `entry_zone` | `{min, max}` números > 0, `min ≤ max` | Sí | |
| `entry_reference_price` | número > 0 | Sí | Dentro de `entry_zone` |
| `stop_loss` | `{price, method, parameters}` | Sí | `price < entry_zone.min`; `method` p. ej. `ATR_MULTIPLE`; `parameters` con los valores usados |
| `take_profit` | número \| null | Sí | |
| `exit_mechanism` | `{type, trigger_condition, execution_method, failure_procedure}` | Sí | Mismo esquema que §4.1; `type` ∈ `STOP_LOSS \| TRAILING_STOP \| TARGET_PRICE` |
| `invalidation_conditions` | lista de cadenas | Sí, ≥ 1 | |
| `confidence` | — | **Prohibido** | No existe el campo (CR-011) |

- **Validación:** las reglas de la tabla. La ausencia de cualquier campo obligatorio hace el candidato inválido: no se emite como candidato y se registra como error técnico (`result_status = ERROR`, `code = INVALID_CANDIDATE`; B.7.1 punto 6, rev. 3).
- **Ejemplo válido** (modo Research, piloto preregistrado; valores ilustrativos, no parámetros aprobados):

```json
{"engine": "strategy_engine", "engine_version": "0.1.0", "spec_version": "0.1.0",
 "result_status": "COMPLETED",
 "data_refs": {"H4": {"last_closed_open_time_utc": "2026-11-19T12:00:00Z", "bars_used": 400, "source": "snapshot", "snapshot_id": "SNAP-0001"}},
 "missing_data": [], "error": null,
 "candidate_id": "6f1c…", "candidate_type": "ENTRY_LONG",
 "strategy_id": "TF_H4", "strategy_version": "0.1.0", "strategy_family": "TREND_FOLLOWING",
 "strategy_status": "RESEARCH", "operating_mode": "RESEARCH", "experiment_ref": null,
 "regime_message_id": "a1…", "ml_inference_message_id": "b2…",
 "signal_timeframe": "H4", "signal_bar_close_utc": "2026-11-19T16:00:00Z",
 "conditions": [
   {"condition_id": "close_above_ema200", "description": "Cierre H4 sobre EMA200", "timeframe": "H4", "observed_value": 96372.98, "threshold": 90210.5, "operator": ">", "satisfied": true},
   {"condition_id": "adx14_above", "description": "ADX14 H4 sobre el umbral", "timeframe": "H4", "observed_value": 28.4, "threshold": 25, "operator": ">", "satisfied": true}],
 "entry_zone": {"min": 96000.0, "max": 96800.0}, "entry_reference_price": 96372.98,
 "stop_loss": {"price": 93100.0, "method": "ATR_MULTIPLE", "parameters": {"atr_period": "PENDING", "multiple": "PENDING"}},
 "take_profit": null,
 "exit_mechanism": {"type": "TRAILING_STOP", "trigger_condition": "…", "execution_method": "…", "failure_procedure": "…"},
 "invalidation_conditions": ["Cierre H4 bajo EMA200"]}
```

#### B.5 `STRATEGY_EXIT_SIGNAL` (nuevo)

- **Propósito:** señal de salida por condición de la estrategia de la posición abierta. Es autónoma: no requiere autorización humana (DEC-011, TC-FLOW-008). En IMPL-3 solo se produce y se registra; su ejecución es de IMPL-5.
- **Productor:** Strategy Engine. **Consumidores:** Execution Engine (IMPL-5), Portfolio Manager, Audit.
- **Sobre:** `causation_id` = E2 del ciclo; `operation_id` en el payload enlaza con la operación (REQ-G-037).
- **Payload específico:** `exit_id` (uuid); `operation_id` (uuid; null solo en backtest); `strategy_id`; `strategy_version`; `exit_reason` (enum `EXIT_CONDITION \| INVALIDATION \| TIME_EXIT`); `conditions` (mismo formato que B.4); `signal_timeframe`; `signal_bar_close_utc`; `reference_price`; `supersedes_entry_candidates` (lista de `candidate_id` descartados en el mismo ciclo; DEC-011: prevalece la salida).
- **Fuera de su alcance:** la ejecución del stop en Binance (`ORDER_FILLED`) y los cierres protectores (`PROTECTIVE_CLOSE_SUBMITTED`) siguen como en v1.5.

#### B.6 `STOP_ADJUSTMENT_REQUESTED` (nuevo; DEC-018 decisión 2)

El piloto aprobado usa trailing stop por ATR. En vivo, subir el stop es una **modificación de stop** (REQ-G-027, INV-009: `P_stop_nuevo ≥ P_stop_inicial`), no una salida. El catálogo tiene `STOP_ORDER_REPLACED` (Execution Engine), pero no el evento con el que la estrategia pide el ajuste.

- **Naturaleza:** es una **solicitud**. Nunca es una modificación ejecutada ni una autorización para reducir protecciones (DEC-018). La única modificación real es `STOP_ORDER_REPLACED`, tras la validación del Risk Manager.
- **Productor:** Strategy Engine. **Consumidores:** Risk Manager (valida INV-009 y REQ-G-027 y decide), Execution Engine (solo tras esa validación, IMPL-5) y Audit.
- **Payload específico:** `request_id` (uuid); `operation_id` (uuid; null solo en backtest); `strategy_id`; `strategy_version`; `current_stop` (> 0); `requested_stop` (> 0); `method` (p. ej. `ATR_TRAILING`); `parameters`; `signal_timeframe`; `signal_bar_close_utc`.
- **Validación del esquema:** `requested_stop > current_stop`. Una solicitud con `requested_stop ≤ current_stop` es inválida, no se emite y queda registrada como error de la estrategia (`ERROR`, código `INVALID_STOP_REQUEST`). El Risk Manager vuelve a comprobar INV-009 contra el stop inicial aunque el esquema ya lo filtre.
- **En IMPL-3:** solo la producen el Strategy Engine y el backtest; su consumo en vivo es de IMPL-4/IMPL-5.

#### B.7 `NO_SETUP`: motivos estructurados

- **Productor:** Strategy Engine. **Sobre:** `causation_id` = E2. Fin del ciclo sin llamadas a LLM.
- **Payload específico:**

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `reason_code` | enum (abajo) | Sí | Motivo principal |
| `reason_detail` | cadena \| null | Sí | Subcódigo, p. ej. el estado de bloqueo |
| `evaluated_strategies` | lista de `{strategy_id, strategy_version, result, failed_conditions}` | Sí | `result` ∈ `NO_SIGNAL \| CANDIDATE \| DISCARDED \| NOT_ELIGIBLE` |
| `discarded_candidates` | lista de `{candidate_id, strategy_id, strategy_version, discard_reason}` | Sí | Vacía si no hubo |
| `exit_signal_ref` | uuid \| null | Sí | Con `EXIT_SIGNAL_PRIORITY` |
| `llm_calls` | `0` | Sí | Constante (TC-FLOW-001) |

- **`reason_code`:**
  - `NO_CANDIDATE`: ninguna estrategia elegible produjo señal (TC-FLOW-001).
  - `NO_APPROVED_STRATEGY`: no hay estrategias APPROVED para el modo actual (DEC-017 Q43: estado esperado en IMPL-3 en vivo).
  - `MULTIPLE_ENTRY_CANDIDATES`: 2 o más candidatos de entrada, aunque coincidan (CR-011, TC-FLOW-004).
  - `EXIT_SIGNAL_PRIORITY`: hubo señal de salida; el candidato de entrada se re-evalúa en el ciclo siguiente (TC-FLOW-006).
  - `PRE_PHASE3_BLOCK`: control previo a la Fase 3 (REQ-G-096). `reason_detail` ∈ `OPEN_POSITION`, `LOSS_STREAK_LOCK`, `MONTHLY_DRAWDOWN_LOCK`, `MONTHLY_TRADE_LIMIT_LOCK`, `DATA_UNAVAILABLE`, `EXCHANGE_DESYNC`, `MANUAL_REVIEW`, `SAFE_MODE`, `AI_BUDGET_CAP`.
  - `UPSTREAM_INSUFFICIENT_DATA`: E2, E3 o los datos de la Fase 1 en INSUFFICIENT_DATA impiden evaluar.
- **`discard_reason`:** `CONFLICT_MULTIPLE_ENTRIES`, `SUPERSEDED_BY_EXIT`, `NOT_ELIGIBLE_ML_UNAVAILABLE`, `NOT_ELIGIBLE_REGIME` (rev. 3: `INVALID_CANDIDATE` pasa a error técnico, B.7.1 punto 6).
- **Fin de ciclo por REQ-G-096 (3) (DEC-018 decisión 3):** se registra como `NO_SETUP` con `PRE_PHASE3_BLOCK`. Hoy el contrato no nombra el evento; esta CR lo fija.
- **Errores técnicos (DEC-018 decisión 3):** **no** son `NO_SETUP`. Si un evento previo del ciclo terminó en ERROR, o el propio Strategy Engine falla, el Strategy Engine emite su evento con `result_status = ERROR` y `error {code, message}` (B.0.4, `UPSTREAM_ERROR` o `INTERNAL_ERROR`). Ese evento es el tipo de la Fase 2 que corresponda, sin candidato, con el sobre en `FAILED` si no hay payload válido. El ciclo termina sin llamadas a LLM (Fail-Closed). `NO_SETUP` queda reservado para «evaluado sin setup» y para el bloqueo previo a la Fase 3.
- **Pendiente de la aprobación global:** el tipo de evento concreto que transporta el error del Strategy Engine. Propuesta en B.7.1.

#### B.7.1 Transporte de errores técnicos del Strategy Engine (propuesta; rev. 3)

**Propuesta:** el error técnico viaja en el mismo tipo `STRATEGY_CANDIDATE`, con `result_status = ERROR`, sin campos de candidato y con el sobre en `FAILED`.

**Esquema (cambios sobre B.0 y B.4):**

1. **Sobre:** si `result_status = ERROR`, entonces `status = "FAILED"`. Esto precisa B.0.1 para los tres motores: un payload con ERROR es válido, pero el sobre señala el fallo. `causation_id`: E2 si existe; si el error impidió recibir E2, E1.
2. **Payload condicional** (JSON Schema `if/then/else` sobre `result_status`):
   - `COMPLETED` → obligatorios los campos de candidato de B.4; `error = null`.
   - `ERROR` → **prohibidos** los campos de candidato (`candidate_id`, `candidate_type`, `conditions`, `entry_zone`, `entry_reference_price`, `stop_loss`, `take_profit`, `exit_mechanism`, `invalidation_conditions`); obligatorios los comunes de B.0 y `error`.
3. **`error`** (ampliado para este caso):

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `code` | enum B.0.4 + `INVALID_CANDIDATE` | Sí | Ver punto 6 |
| `message` | cadena | Sí | Sin datos sensibles |
| `stage` | enum `INPUT_VALIDATION \| REGIME_INPUT \| ML_INPUT \| STRATEGY_EVALUATION \| CANDIDATE_VALIDATION \| INTERNAL` | Sí | Dónde falló |
| `upstream_message_id` | uuid \| null | Sí | Evento previo en ERROR, si el error viene de él (`UPSTREAM_ERROR`) |
| `strategy_id` / `strategy_version` | cadena \| null | Sí | Estrategia afectada, si la hay |

4. **Trazabilidad que se conserva:** `regime_message_id` y `ml_inference_message_id` (pueden ser null si el evento previo no llegó), `data_refs`, `engine_version`, `spec_version`.
5. **Regla de flujo (Fail-Closed):** un `STRATEGY_CANDIDATE` con ERROR termina el ciclo con **cero llamadas a LLM**. El AI Orchestrator solo acepta como entrada de la Fase 3 los `STRATEGY_CANDIDATE` con `result_status = COMPLETED` y sobre `COMPLETED`; cualquier otro se rechaza y se registra.
6. **Coherencia con DEC-018 (corrección a B.4):** B.4 decía que un candidato mal formado se registraba en `NO_SETUP` como `DISCARDED`/`INVALID_CANDIDATE`. Un candidato mal formado es un defecto técnico de la estrategia, así que con DEC-018 pasa a ser `STRATEGY_CANDIDATE` con `result_status = ERROR`, `code = INVALID_CANDIDATE` y `stage = CANDIDATE_VALIDATION`. `INVALID_CANDIDATE` sale de los `discard_reason` de B.7.
7. **Prueba nueva:** TC-FLOW-011. Un error del Strategy Engine (entrada en ERROR, excepción interna, candidato mal formado) produce `STRATEGY_CANDIDATE` con ERROR y sobre FAILED, sin campos de candidato, con cero llamadas a LLM. Un `STRATEGY_CANDIDATE` con ERROR entregado a la Fase 3 se rechaza.

**Ejemplo válido:**

```json
{"engine": "strategy_engine", "engine_version": "0.1.0", "spec_version": "0.1.0",
 "result_status": "ERROR",
 "data_refs": {"H4": {"last_closed_open_time_utc": "2026-11-19T12:00:00Z", "bars_used": 400, "source": "binance_ws", "snapshot_id": null}},
 "missing_data": [],
 "error": {"code": "UPSTREAM_ERROR", "message": "REGIME_CLASSIFIED en ERROR (DATA_INCONSISTENT)",
           "stage": "REGIME_INPUT", "upstream_message_id": "a1…", "strategy_id": null, "strategy_version": null},
 "regime_message_id": "a1…", "ml_inference_message_id": "b2…"}
```

**Por qué es preferible a un evento independiente** (p. ej. `STRATEGY_ENGINE_FAILED`):

| Criterio | `STRATEGY_CANDIDATE` + ERROR | Evento independiente |
|---|---|---|
| Posición en la cadena (data_flow.md §5) | E4 sigue teniendo un único tipo de resultado positivo y uno de «sin setup» (`NO_SETUP`); el error ocupa la misma posición causal, así que la reconstrucción (TC-AC-04) lo encuentra donde espera E4 | E4 pasa a tener tres tipos posibles; cada consumidor y la reconstrucción deben conocer el tercero |
| Uniformidad con B.0 | Mismo patrón que `REGIME_CLASSIFIED` y `ML_INFERENCE_COMPLETED`, que ya llevan ERROR en `result_status`: un solo validador y una sola regla («solo COMPLETED avanza») para los tres motores | El Strategy Engine sería el único motor de la Fase 2 con un evento de error propio |
| Catálogo (REQ-G-063/064) | Sin tipo nuevo (el catálogo ya crece en 2 con esta CR) | Un tipo más, con su contrato completo según REQ-G-064 |
| Fail-Closed | El esquema condicional prohíbe campos de candidato con ERROR, así que es imposible confundir un error con un candidato que valide | También es seguro, pero exige que todos los consumidores se suscriban al tipo nuevo; uno que no lo haga «no ve» el error y solo nota la ausencia de respuesta |

**Desventajas reconocidas y su mitigación:**
- El nombre `STRATEGY_CANDIDATE` para un error es menos intuitivo, y quien filtre solo por `message_type` podría contar errores como candidatos. Se mitiga con el sobre en `FAILED`, el esquema condicional y TC-FLOW-011. Las métricas de candidatos deben filtrar por `result_status = COMPLETED`.
- Las consultas «todos los errores del motor» deben filtrar por `result_status`, no por tipo. Es el mismo criterio que para los otros dos motores.

**Alternativa descartada por DEC-018:** registrar el error como `NO_SETUP`.

#### B.8 Normalización de TRADE_PROPOSAL (§3.3 → §4.1)

La conversión la hace un componente determinista (la capa de validación del AI Orchestrator), nunca el LLM.

1. **Origen de los campos operativos:** `asset`, `direction`, `strategy_id`, `strategy_version`, `entry_price_target` (= `entry_reference_price` del candidato), `stop_loss_price` (= `stop_loss.price` del candidato) y `exit_mechanism` se copian del `STRATEGY_CANDIDATE` que originó el ciclo. El LLM no fija precios ni mecanismos de salida.
2. **Consistencia exigida a la síntesis** (si `decision = TRADE_PROPOSAL`):
   - `strategy_id` y `strategy_version` iguales a los del candidato;
   - `stop_loss` igual a `stop_loss.price` del candidato (sin tolerancia);
   - `entry_zone` contenida en `entry_zone` del candidato;
   - `take_profit` nulo o igual al del candidato.

   Si alguna falla, **no se emite TRADE_PROPOSAL**. `DECISION_SYNTHESIS_COMPLETED` se conserva y se registra la inconsistencia con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados mediante `PROPOSAL_NORMALIZATION_REJECTED` (B.10; CR-019).
3. **Campos aditivos en §4.1** (versión del esquema 1.0.0 → **1.1.0**, compatible): `source_candidate_id`, `source_candidate_message_id`, `synthesis_analysis_id`, `entry_zone` (copiada del candidato) y `take_profit_price` (número o null).
4. `proposal_id` lo genera el normalizador; `correlation_id` es el del ciclo; `causation_id` es E8 (data_flow.md §5, E9).
5. La TRADE_PROPOSAL normalizada se valida contra §4.1 v1.1.0 antes de emitirse; si no valida, no se emite (`OUT_OF_CONTRACT`) y se registra `PROPOSAL_NORMALIZATION_REJECTED` con `reason_code = OUT_OF_CONTRACT` (B.10; CR-019).

#### B.10 `PROPOSAL_NORMALIZATION_REJECTED` (CR-019, DEC-020)

- **Cuándo se emite:** solo si `DECISION_SYNTHESIS_COMPLETED` (E8) tiene `decision = TRADE_PROPOSAL` y la normalización termina en `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` (B.8 punto 2) o `OUT_OF_CONTRACT` (B.8 punto 5). **No se emite** si la síntesis decide otra cosa o está en ERROR, ni si el candidato está en ERROR: esos casos ya quedan registrados en E8 y E4.
- **Posición en la cadena:** E9, en lugar de TRADE_PROPOSAL (E9 tiene dos tipos excluyentes). El ciclo termina.
- **Sobre:** contrato universal (§1). `source` = `ai_orchestrator`; `destination` = `audit`; `correlation_id` = el del ciclo; `causation_id` = E8; `timeframe` y `data_timestamp_utc` = los de E8; `status` = `COMPLETED` (el normalizador terminó; el resultado es un rechazo, mismo criterio que B.0 punto 1).
- **Payload** (`schema_version` = `1.0.0`; sin propiedades adicionales):

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `reason_code` | enum `PROPOSAL_INCONSISTENT_WITH_CANDIDATE \| OUT_OF_CONTRACT` | Sí | Motivo del rechazo (B.8 puntos 2 y 5) |
| `affected_fields` | lista de `{field, synthesis_value, candidate_value}` | Sí | `field` ∈ `strategy_id`, `strategy_version`, `stop_loss`, `entry_zone`, `take_profit`. Al menos uno si `reason_code = PROPOSAL_INCONSISTENT_WITH_CANDIDATE`; vacía si `OUT_OF_CONTRACT` |
| `validation_errors` | lista de cadenas | Sí | Errores de validación contra §4.1 v1.1.0. Al menos uno si `OUT_OF_CONTRACT`; vacía si `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` |
| `source_candidate_id` | uuid | Sí | `candidate_id` de E4 |
| `source_candidate_message_id` | uuid | Sí | `message_id` de E4 |
| `synthesis_message_id` | uuid | Sí | `message_id` de E8 (también es `causation_id`) |
| `synthesis_analysis_id` | uuid | Sí | `analysis_id` de la síntesis |
| `normalizer_version` | semver | Sí | Versión del normalizador |

- **Prohibido:** cualquier campo operativo de §4.1 (`proposal_id`, `entry_price_target`, `stop_loss_price`, `exit_mechanism`, etc.). El evento no puede confundirse con una propuesta ni usarse como tal.
- **Determinismo:** mismo E4 y mismo E8 → mismo payload (TC-AC-07).

---

## 4. Contratos del Risk Manager

### 4.1 Contrato de Entrada — Risk Manager (TRADE_PROPOSAL)

**v1.1.0 (CR-018 §3.8 B.8):** campos aditivos `source_candidate_id`, `source_candidate_message_id`, `synthesis_analysis_id`, `entry_zone` y `take_profit_price`; los campos operativos se copian del STRATEGY_CANDIDATE por un normalizador determinista. v1.0.0 sigue siendo legible.

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
    "type": "STOP_LOSS|TRAILING_STOP|TARGET_PRICE",
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

**Vigencia (CR-008):** la salida del Risk Manager no fija vigencia. La vigencia de la autorización la fija el backend de autorización al enviar la solicitud por Telegram (REQ-G-039, §5); el Risk Manager re-verifica las condiciones al ejecutar (REQ-G-042).

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

Cada evento de auditoría del Risk Manager contiene, como mínimo, los campos de RISK_POLICY «Información mínima por evento» (ampliado por CR-008):

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
  "policy_version": "<semver — versión de RISK_POLICY vigente al momento del evento>",
  "operation_id": "<uuid de la operación relacionada (REQ-G-037) o null>",
  "equity": 0.0,
  "risk_budget": 0.0,
  "effective_risk": 0.0,
  "position_size": 0.0,
  "decision": "APPROVED|REJECTED|BLOCKED",
  "reason": "<motivo de la decisión>",
  "actor": "<componente responsable>"
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

## 9. Parámetros (estado tras CR-008)

| ID | Campo afectado | Estado |
|---|---|---|
| REQ-G-P01 | `tc_mxn_usd` | RESUELTO (DEC-004): Binance USDT/MXN en tiempo real para sizing; fuente fiscal ligada a P08 |
| REQ-G-P02 | `tc_mxn_usd` | RESUELTO (DEC-004): antigüedad máxima 5 min; excedido = Fail-Closed |
| REQ-G-P03 | `comisiones_mxn` | RESUELTO (DEC-004): comisión real por API, mínimo 0.10% por lado |
| REQ-G-P04 | Fórmula de sizing | RESUELTO (DEC-004): slippage 0.10% |
| REQ-G-P05 | `authorized_quantity_max` | RESUELTO (DEC-004): exchangeInfo dinámico, refresco diario |
| REQ-G-P06 | Autorización humana | RESUELTO (DEC-004): Telegram con botones Aprobar/Rechazar |
| REQ-G-P07 | `tc_mxn_usd` (fiscal) | RESUELTO (DEC-006): API SIE de Banxico |
| REQ-G-P08 | Fiscal Ledger | **PENDING** (diferido por el propietario): validación con contador |

---

*Fin de api_contracts.md*
