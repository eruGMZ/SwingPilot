# CR-018 — Contratos de los motores cuantitativos (Fase 2 del flujo) y normalización de TRADE_PROPOSAL

**Fecha:** 2026-11-20
**Estado:** APROBADA por el propietario el 2026-11-20 («Apruebo CR-018 rev. 3», DEC-019) y APLICADA (contrato v1.6). Historial: rev. 2 con DEC-018; rev. 3 añadió B.7.1.
**Origen:** DEC-017 Q45 («Preparar CR-018 con los contratos de REGIME_CLASSIFIED, ML_INFERENCE_COMPLETED, STRATEGY_CANDIDATE, señal de salida y motivos estructurados de NO_SETUP…»). Vacíos detectados al registrar FEAT-018..021 (`feature_list.json` → `contract_gaps_pending`).
**Autor:** Orquestador de Desarrollo.

---

## A. Problema

El contrato v1.5 nombra los eventos de la Fase 2 (api_contracts.md §2; data_flow.md §5, E2–E4), pero no define su contenido:

| Elemento | Estado en v1.5 |
|---|---|
| `REGIME_CLASSIFIED` | Solo existe el nombre. Sin payload. |
| `ML_INFERENCE_COMPLETED` | Solo existe el nombre. Sin payload ni comportamiento cuando no hay modelo aprobado (DEC-017 Q44). |
| `STRATEGY_CANDIDATE` | data_flow.md lista 6 campos (`strategy_id`, `strategy_version`, `conditions`, `entry_zone`, `stop_loss`, `invalidation_conditions`) sin tipos, reglas ni errores. |
| Señal de salida | «Esquema PENDING de FASE 2» (DEC-011; data_flow.md §2). No existe el tipo de evento en el catálogo. |
| `NO_SETUP` | «Los nombres definitivos de los motivos son PENDING de FASE 2» (api_contracts.md §2). |
| Fin de ciclo por el control previo a la Fase 3 (REQ-G-096) | El contrato dice que el ciclo termina sin LLM, pero no qué evento lo registra. |
| E4 con dos causas | data_flow.md §5: `causation_id: E2, E3`; la regla general dice «la principal y el resto en el cuerpo», sin decir cuál es la principal. |
| Normalización §3.3 → §4.1 | La síntesis produce `entry_zone {min,max}`, `stop_loss` y `take_profit`; el Risk Manager espera `entry_price_target`, `stop_loss_price` y `exit_mechanism {…}`. No hay regla de conversión ni de consistencia con el candidato (dependencia de FEAT-012 hacia IMPL-3). |

REQ-G-064 exige que cada contrato especializado documente: nombre, versión, propósito, productor y consumidores autorizados, campos obligatorios y opcionales, tipos, enumeraciones, reglas de validación, manejo de errores, ejemplos válidos y compatibilidad. Sin esto no se pueden implementar FEAT-018..021 (DEC-017, condición 5).

## B. Cambio propuesto

### B.0 Reglas comunes de los eventos de motores deterministas

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

### B.1 Catálogo de eventos (api_contracts.md §2)

- Productores y consumidores sin cambios para `REGIME_CLASSIFIED`, `ML_INFERENCE_COMPLETED` y `STRATEGY_CANDIDATE`.
- **Nuevo:** `STRATEGY_EXIT_SIGNAL`. Productor: Strategy Engine. Consumidores: Execution Engine (desde IMPL-5), Portfolio Manager y Audit. Es la señal de salida por condición de estrategia, autónoma y sin autorización humana (DEC-011).
- **Nuevo (B.6, DEC-018 decisión 2):** `STOP_ADJUSTMENT_REQUESTED`.
- `NO_SETUP`: se sustituye la nota «nombres definitivos PENDING» por la referencia a B.7.

### B.2 `REGIME_CLASSIFIED` (E2)

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

### B.3 `ML_INFERENCE_COMPLETED` (E3)

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

### B.4 `STRATEGY_CANDIDATE` (E4)

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

### B.5 `STRATEGY_EXIT_SIGNAL` (nuevo)

- **Propósito:** señal de salida por condición de la estrategia de la posición abierta. Es autónoma: no requiere autorización humana (DEC-011, TC-FLOW-008). En IMPL-3 solo se produce y se registra; su ejecución es de IMPL-5.
- **Productor:** Strategy Engine. **Consumidores:** Execution Engine (IMPL-5), Portfolio Manager, Audit.
- **Sobre:** `causation_id` = E2 del ciclo; `operation_id` en el payload enlaza con la operación (REQ-G-037).
- **Payload específico:** `exit_id` (uuid); `operation_id` (uuid; null solo en backtest); `strategy_id`; `strategy_version`; `exit_reason` (enum `EXIT_CONDITION \| INVALIDATION \| TIME_EXIT`); `conditions` (mismo formato que B.4); `signal_timeframe`; `signal_bar_close_utc`; `reference_price`; `supersedes_entry_candidates` (lista de `candidate_id` descartados en el mismo ciclo; DEC-011: prevalece la salida).
- **Fuera de su alcance:** la ejecución del stop en Binance (`ORDER_FILLED`) y los cierres protectores (`PROTECTIVE_CLOSE_SUBMITTED`) siguen como en v1.5.

### B.6 `STOP_ADJUSTMENT_REQUESTED` (nuevo; DEC-018 decisión 2)

El piloto aprobado usa trailing stop por ATR. En vivo, subir el stop es una **modificación de stop** (REQ-G-027, INV-009: `P_stop_nuevo ≥ P_stop_inicial`), no una salida. El catálogo tiene `STOP_ORDER_REPLACED` (Execution Engine), pero no el evento con el que la estrategia pide el ajuste.

- **Naturaleza:** es una **solicitud**. Nunca es una modificación ejecutada ni una autorización para reducir protecciones (DEC-018). La única modificación real es `STOP_ORDER_REPLACED`, tras la validación del Risk Manager.
- **Productor:** Strategy Engine. **Consumidores:** Risk Manager (valida INV-009 y REQ-G-027 y decide), Execution Engine (solo tras esa validación, IMPL-5) y Audit.
- **Payload específico:** `request_id` (uuid); `operation_id` (uuid; null solo en backtest); `strategy_id`; `strategy_version`; `current_stop` (> 0); `requested_stop` (> 0); `method` (p. ej. `ATR_TRAILING`); `parameters`; `signal_timeframe`; `signal_bar_close_utc`.
- **Validación del esquema:** `requested_stop > current_stop`. Una solicitud con `requested_stop ≤ current_stop` es inválida, no se emite y queda registrada como error de la estrategia (`ERROR`, código `INVALID_STOP_REQUEST`). El Risk Manager vuelve a comprobar INV-009 contra el stop inicial aunque el esquema ya lo filtre.
- **En IMPL-3:** solo la producen el Strategy Engine y el backtest; su consumo en vivo es de IMPL-4/IMPL-5.

### B.7 `NO_SETUP`: motivos estructurados

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

### B.7.1 Transporte de errores técnicos del Strategy Engine (propuesta; rev. 3)

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

### B.8 Normalización de TRADE_PROPOSAL (§3.3 → §4.1)

La conversión la hace un componente determinista (la capa de validación del AI Orchestrator), nunca el LLM.

1. **Origen de los campos operativos:** `asset`, `direction`, `strategy_id`, `strategy_version`, `entry_price_target` (= `entry_reference_price` del candidato), `stop_loss_price` (= `stop_loss.price` del candidato) y `exit_mechanism` se copian del `STRATEGY_CANDIDATE` que originó el ciclo. El LLM no fija precios ni mecanismos de salida.
2. **Consistencia exigida a la síntesis** (si `decision = TRADE_PROPOSAL`):
   - `strategy_id` y `strategy_version` iguales a los del candidato;
   - `stop_loss` igual a `stop_loss.price` del candidato (sin tolerancia);
   - `entry_zone` contenida en `entry_zone` del candidato;
   - `take_profit` nulo o igual al del candidato.

   Si alguna falla, **no se emite TRADE_PROPOSAL**. `DECISION_SYNTHESIS_COMPLETED` se conserva y se registra la inconsistencia con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados.
3. **Campos aditivos en §4.1** (versión del esquema 1.0.0 → **1.1.0**, compatible): `source_candidate_id`, `source_candidate_message_id`, `synthesis_analysis_id`, `entry_zone` (copiada del candidato) y `take_profit_price` (número o null).
4. `proposal_id` lo genera el normalizador; `correlation_id` es el del ciclo; `causation_id` es E8 (data_flow.md §5, E9).
5. La TRADE_PROPOSAL normalizada se valida contra §4.1 v1.1.0 antes de emitirse; si no valida, no se emite (`OUT_OF_CONTRACT`).

### B.9 Cambios en los documentos del contrato (al aprobarse)

- **api_contracts.md:** §2 (B.1, B.6 según decisión, B.7); nueva §3.8 «Contratos de los motores de la Fase 2» (B.0, B.2–B.5, B.7); §4.1 (B.8.3, v1.1.0); nota de normalización en §3.3 (B.8.1–B.8.2).
- **data_flow.md:** §1 Fase 2 (motivos de NO_SETUP, ML sin modelo); §2 (STRATEGY_EXIT_SIGNAL y, si se aprueba, B.6); §5 (E4 con causa principal E2 y E3 en el payload; NO_SETUP; E9 normalizada).
- **requirements.md:** REQ-G-063 (recuento del catálogo); REQ-G-071 (referencia a §3.8 y a los motivos); REQ-G-073 (normalización B.8).
- **test_plan.md**, casos nuevos (más TC-FLOW-011 de B.7.1):
  - TC-MSG-004: los payloads de la Fase 2 validan contra su esquema y un campo obligatorio ausente se rechaza.
  - TC-MSG-005: `data_timestamp_utc` ≠ `timestamp_utc` y `data_refs` coherente.
  - TC-FLOW-009: cada `reason_code` de NO_SETUP con su caso.
  - TC-FLOW-010: ML sin modelo → familia ML-Based no elegible.
  - TC-NORM-001: TRADE_PROPOSAL normalizada toma precios y salida del candidato.
  - TC-NORM-002: síntesis inconsistente → sin TRADE_PROPOSAL.
  - TC-NORM-003: §4.1 v1.1.0 valida y v1.0.0 sigue siendo legible.
- **Versión del contrato:** v1.5 → **v1.6** en los 5 documentos de `implementation/`.

## C. Impacto

- **Riesgo y ejecución:** ninguno directo. B.8 lo **reduce**: los precios y la salida dejan de poder venir del LLM. El Risk Manager (IMPL-4) recibe un §4.1 compatible (cambio aditivo).
- **Arquitectura y autoridad:** sin cambios. Los motores siguen siendo deterministas y no decisores; el LLM sigue siendo consultivo.
- **Código existente:** el AI Orchestrator (FEAT-005/012) gana la normalización de B.8 en IMPL-3 (FEAT-021). Los contratos de agentes (§3.0–§3.7) no cambian.
- **Eventos:** el catálogo pasa de 31 a 33 tipos (`STRATEGY_EXIT_SIGNAL` y `STOP_ADJUSTMENT_REQUESTED`).
- **Compatibilidad:** todos los esquemas nuevos empiezan en 1.0.0; §4.1 sube a 1.1.0 de forma aditiva.

## D. Alternativas consideradas

1. **Payloads mínimos (solo los 6 campos de data_flow.md para el candidato):** más simple, pero no cumple REQ-G-064 ni INV-007 (el Risk Manager necesita `exit_mechanism` completo) y deja sin trazabilidad los datos usados.
2. **Que la síntesis (LLM) fije los precios de la propuesta:** contradice REQ-G-057 (los cálculos críticos no se sustituyen por IA) y obliga al Risk Manager a validar precios de origen no determinista. Descartada.
3. **Evento propio para el fin de ciclo por REQ-G-096** (p. ej. `CYCLE_SKIPPED`) en lugar de `NO_SETUP` + `PRE_PHASE3_BLOCK`. **Descartada** por el propietario (DEC-018 decisión 3).
4. **Campo `confidence` informativo en el candidato:** descartado por CR-011.

## E. Fuera del alcance de esta CR

- Las clases, indicadores y umbrales del Regime Engine (DEC-017 Q42; propuesta en `harness/plans/IMPL-3_Q42_regime_engine_propuesta.md`). Esta CR define el contenedor; la enumeración de `regime_label` la fija la especificación aprobada.
- Los parámetros del piloto Trend Following H4 (preregistro).
- El formato del identificador de cliente de órdenes y el almacenamiento durable de operaciones (REQ-G-032, PENDING de FASE 2, IMPL-5).
- El esquema del mensaje de Telegram (IMPL-4).

## F. Aprobación

Ya decidido (DEC-018): B.6 se incorpora como solicitud; B.7 usa `PRE_PHASE3_BLOCK` y los errores técnicos quedan como `ERROR`; `regime_label` v1 son tres categorías de volatilidad D1.

Requiere todavía aprobación explícita del propietario, indicando:

1. Si aprueba B.0–B.5, B.7 y B.8 (revisión 2) tal cual o con cambios.
2. B.7.1: transporte del error técnico del Strategy Engine en `STRATEGY_CANDIDATE` con `result_status = ERROR` y sobre `FAILED` (y la corrección de B.4 sobre `INVALID_CANDIDATE`).

Al aprobarse: registrar la decisión (DEC-019), aplicar B.9, pasar el contrato a v1.6, actualizar `harness/manifest.json` si procede, desbloquear FEAT-018, FEAT-020, FEAT-021 y FEAT-022 según sus dependencias, retirar los `contract_gaps_pending` resueltos y registrar en `progress.md`.
