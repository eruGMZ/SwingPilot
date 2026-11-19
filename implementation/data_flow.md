# SwingPilot — Data Flow v1.4

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** v1.4 — v1.0 APROBADO por el propietario (G3, 2026-11-18: "APRUEBO EL CONTRATO TÉCNICO v1.0"); v1.1 aplicó CR-011 (DEC-011); v1.2 aplicó CR-012 (DEC-012); v1.3 aplicó CR-013 (DEC-013) y v1.4 aplica CR-015 (DEC-014), todas aprobadas el 2026-11-19; incorpora CR-001..CR-013 y CR-015. Cambios posteriores solo mediante solicitud de cambio aprobada y versionado

---

## 1. Flujo de Decisión Integral (7 Fases)

Basado en AI_INTEGRATION.md (aprobado DEC-001), con el orden de fases ajustado por CR-004 (DEC-007): el filtro determinista va antes de cualquier llamada a LLM. Todas las fases son secuenciales; no hay salto de fases. Cada llamada a un agente LLM admite 1 reintento; si un agente sigue fallando, el ciclo termina sin propuesta (REQ-G-034).

```
Disparador externo (señal periódica o solicitud manual)
│
▼ FASE 1 — Captura y Preparación de Datos
┌─────────────────────────────────────────────────────────────────────────┐
│ Trading Engine + Market Intelligence                                     │
│                                                                         │
│  - Obtener OHLCV de Binance: D1, H4, H1 para BTC/USDT (WebSocket       │
│    kline_1d/4h/1h; respaldo REST con startTime al reconectar:          │
│    recuperar TODAS las velas cerradas faltantes; mientras no se        │
│    resincroniza → Fail-Closed; REQ-G-097, CR-013)                      │
│  - Solo velas cerradas: descartar la vela en formación; cierre según   │
│    hora del servidor de Binance (REQ-G-070, CR-003)                     │
│  - Validar integridad: completitud, timestamps, duplicados              │
│  - Detectar datos obsoletos, faltantes o inconsistentes                 │
│  - Calcular indicadores técnicos configurados                           │
│  - Registrar fuente, timestamp y versión de los datos                   │
│  - Separar tiempo de mercado vs tiempo de procesamiento                 │
│                                                                         │
│  BLOQUEANTE: si los datos no cumplen condiciones mínimas                │
│  → DATA_UNAVAILABLE (Risk Manager state) → no se genera propuesta      │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ Datos validados + correlation_id
                          ▼ FASE 2 — Filtro Determinista (sin LLM)
┌─────────────────────────────────────────────────────────────────────────┐
│ Regime Engine + ML Engine → Strategy Engine (todos deterministas)       │
│                                                                         │
│  - Regime Engine: clasificación de condiciones de mercado               │
│  - ML Engine: inferencia (ML_INFERENCE_COMPLETED); la consume el        │
│    Strategy Engine (familia ML-Based) y Synthesis solo como contexto.   │
│    No es un decisor paralelo.                                           │
│  - Strategy Engine: evalúa estrategias APROBADAS (versionadas) y        │
│    produce STRATEGY_CANDIDATE (strategy_id, strategy_version,           │
│    conditions, entry_zone, stop_loss, invalidation_conditions)          │
│                                                                         │
│  Familias de INVESTIGACIÓN (Trend Follow., Momentum, Mean Reversion,    │
│  Breakout, Volatility-Based, ML-Based): ninguna habilitada en           │
│  producción sin evidencia experimental.                                 │
│                                                                         │
│  SIN CANDIDATO → NO_SETUP → fin del ciclo, CERO llamadas a LLM          │
│                                                                         │
│  Resolución de candidatos (CR-011, DEC-011; regla binaria, sin          │
│  confianza):                                                            │
│  - 2+ candidatos de entrada en el ciclo (aunque coincidan) → NO_SETUP,  │
│    con candidatos descartados y motivo registrados                      │
│  - Entrada + señal de salida simultáneas → prevalece la salida; el      │
│    candidato de entrada válido se re-evalúa en el SIGUIENTE ciclo       │
│                                                                         │
│  Control de costo previo a Fase 3 (REQ-G-096, CR-006): con posición     │
│  abierta, bloqueo de entradas activo, modo seguro o tope mensual de IA  │
│  alcanzado → fin del ciclo, CERO llamadas a LLM                         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ STRATEGY_CANDIDATEs (si hay)
                          ▼ FASE 3 — Análisis LLM Paralelo
┌─────────────────────────────────────────────────────────────────────────┐
│ AI Orchestrator distribuye a (en paralelo):                             │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Market Analyst  │  │  Macro Analyst   │  │ Strategy Analyst │      │
│  │  (LLM)           │  │  (LLM)           │  │ (LLM)            │      │
│  │  OHLCV+indicad.  │  │  noticias+macro  │  │ STRATEGY_CANDIDATE│     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                         │
│  Todos comparten correlation_id. Cada agente entrega resultado o        │
│  estado explícito (INSUFFICIENT_DATA, ERROR, TIMEOUT).                  │
│  1 reintento por agente; fallo persistente → ciclo sin propuesta.       │
│  Modelos: Haiku 5.5 (analistas), Sonnet 5.5 (Synthesis); Messages API   │
│  sin herramientas, salida estructurada validada (REQ-G-095, CR-006).    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ Resultados de análisis
                          ▼ FASE 4 — Síntesis
┌─────────────────────────────────────────────────────────────────────────┐
│ Decision Synthesis (LLM)                                                 │
│                                                                         │
│  - Integra Fase 2 (Regime, ML como contexto, candidatos) y Fase 3       │
│    (Market, Macro, Strategy Analyst). NO integra al Risk Analyst.       │
│  - Identifica coincidencias y contradicciones (las preserva; no oculta) │
│  - Evalúa consistencia de evidencia entre temporalidades                │
│  - Identifica información faltante o insuficiente                       │
│                                                                         │
│  Decisión: TRADE_PROPOSAL | INSUFFICIENT_INFO | DISCARD | DISAGREEMENT  │
│                                                                         │
│  TRADE_PROPOSAL ≠ orden de ejecución ≠ autorización                    │
│  El descarte explícito también es un resultado válido del ciclo         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ TRADE_PROPOSAL (si aplica)
                          ▼ FASE 5 — Validación Determinista de Riesgo
┌─────────────────────────────────────────────────────────────────────────┐
│ Risk Manager (DETERMINISTA)                                              │
│                                                                         │
│  Verificaciones secuenciales:                                           │
│  1. Capital disponible en Binance (reconciliado)                        │
│  2. Equity actual = Cash + MarketValue                                   │
│  3. RiskBudget = Equity × 0.015                                         │
│  4. Position sizing Q (fórmula)                                         │
│  5. RiskEffective ≤ RiskBudget                                          │
│  6. Stop-loss válido y verificable                                      │
│  7. OpenPositions = 0 (ninguna posición abierta ni orden de entrada pendiente)                                                   │
│  8. MonthlyDrawdown < 5%                                                │
│  9. MonthlyTradeCount < 8                                               │
│ 10. Instrumento = BTC/USDT, dirección = LONG                            │
│ 11. Sin bloqueos activos (LOSS_STREAK_LOCK, etc.)                       │
│ 12. Mecanismo de salida verificable                                     │
│ 13. Duplicidad: ¿ya existe una propuesta idéntica activa?               │
│ 14. Consistencia de cantidad (stepSize, minQty, minNotional)            │
│                                                                         │
│  Resultados:                                                             │
│  - RISK_APPROVED → Risk Analyst (LLM, consultivo, CR-004) evalúa la    │
│    propuesta aprobada y el estado del sistema (RISK_ANALYSIS_COMPLETED);│
│    no puede revertir ni modificar el resultado del Risk Manager.        │
│    Fallo persistente del Risk Analyst → ciclo sin propuesta.            │
│    Luego → autorización humana                                          │
│  - RISK_REJECTED → registra motivos; fin del ciclo                     │
│  - RISK_REQUIRES_REVIEW → escala a Telegram para intervención humana   │
│                                                                         │
│  Fail-Closed (INV-012): cualquier condición no verificable → bloqueo    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ RISK_APPROVED (si aplica)
                          ▼ FASE 6 — Autorización Humana y Ejecución
┌─────────────────────────────────────────────────────────────────────────┐
│ Telegram Bot → Operador Humano → Backend de Autorización                │
│                                                                         │
│  - Telegram muestra: propuesta completa, cálculos de riesgo, estrategia│
│    y la evaluación del Risk Analyst                                    │
│  - Operador aprueba o rechaza (Nivel 1 de autonomía — INV-008)          │
│  - Backend verifica identidad y permisos del operador                   │
│  - Genera human_authorization_id con vigencia de 30 min (REQ-G-039);    │
│    respuesta tardía → AUTH_EXPIRED, sin orden                           │
│  - Estados de la operación: REQ-G-037 (CR-005)                          │
│                                                                         │
│  Execution Engine (solo si autorización válida):                        │
│  - Re-verifica condiciones de riesgo al momento de ejecución            │
│  - Si condiciones cambiaron materialmente → nueva autorización          │
│    (precio > 0.5% del autorizado → nueva autorización, REQ-G-P20)       │
│  - Persiste el estado ANTES de enviar (REQ-G-032); si falla, no envía   │
│  - Envía orden a Binance respetando stepSize/minQty/minNotional          │
│    con identificador de cliente derivado del correlation_id             │
│  - Gestiona respuesta: ORDER_SUBMITTED → ORDER_FILLED / REJECTED        │
│  - Reconcilia ejecuciones parciales como eventos independientes         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ ORDER_FILLED / ORDER_REJECTED
                          ▼ FASE 7 — Registro y Retroalimentación
┌─────────────────────────────────────────────────────────────────────────┐
│ Audit & Governance + Fiscal Ledger                                      │
│                                                                         │
│  Registro completo del ciclo (inmutable):                               │
│  - Datos utilizados (fuente, timestamp, versión)                        │
│  - Análisis por agente (modelo, versión de prompt, resultado)           │
│  - Propuestas generadas y descartadas                                   │
│  - Decisiones del Risk Manager (inputs, fórmulas, resultados)          │
│  - Autorizaciones (humana + Risk Manager)                               │
│  - Órdenes y ejecuciones (confirmadas por Binance)                     │
│  - Comisiones y resultado neto                                          │
│  - Evaluación posterior (para retroalimentación experimental)           │
│                                                                         │
│  Fiscal Ledger (solo si ORDER_FILLED):                                  │
│  - Inserta en trades.db con todos los campos requeridos                 │
│  - Calcula costo acumulado FIFO                                         │
│  - Actualiza posicion_abierta                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ciclo de Vida de Posición

```
Estado: SIN_POSICION
│
├─ Ciclo de decisión completo (7 fases) → RISK_APPROVED
│
▼ Autorización humana → ORDER_SUBMITTED
│
├─ ORDER_FILLED (parcial o completo)
│    ├─ Colocación inmediata de stop en Binance (REQ-G-031, CR-002; OCO con
│    │    pierna STOP_LOSS de mercado y TP limit opcional, CR-012, DEC-012;
│    │    sin TP: orden STOP_LOSS individual)
│    │    - Éxito → STOP_ORDER_PLACED
│    │    - Fallo → STOP_ORDER_FAILED → aviso Telegram + Fail-Closed
│    │      (bloqueo de nuevas entradas; tratamiento según REQ-G-031:
│    │       recolocar el stop o cierre protector)
│    └─ Estado: POSITION_OPEN
│         │
│         ├─ Monitoreo continuo (segunda capa; el stop primario vive en Binance):
│         │    - Precio actual vs stop-loss
│         │    - Equity y drawdown mensual
│         │    - Estado de Binance (reconciliación, incluye stop activo)
│         │
│         ├─ Sin stop activo en Binance (cierre protector, REQ-G-031, CR-005):
│         │    - Precio sobre el stop → recolocar stop (STOP_ORDER_PLACED)
│         │    - Precio en o bajo el stop → venta a mercado
│         │      (PROTECTIVE_CLOSE_SUBMITTED) + aviso + MANUAL_REVIEW
│         │    - Precio no disponible → Fail-Closed + aviso; no se cierra a ciegas
│         │
│         ├─ Modificación de stop permitida (REQ-G-027):
│         │    - Cancelar y reemplazar en Binance → STOP_ORDER_REPLACED
│         │
│         ├─ Evento de salida:
│         │    - Stop ejecutado en Binance → ORDER_FILLED (SELL)
│         │    - Stop alcanzado sin ejecución en Binance → ORDER_SUBMITTED (SELL)
│         │    - Señal de salida del Strategy Engine → ORDER_SUBMITTED (SELL),
│         │      autónoma, sin autorización humana (CR-011, DEC-011; el
│         │      esquema del evento de señal de salida es PENDING de FASE 2)
│         │    - Take-profit alcanzado (si configurado) → ORDER_SUBMITTED
│         │    - Instrucción manual del operador → ORDER_SUBMITTED
│         │    - Bloqueo de riesgo activo → acciones de protección disponibles
│         │
│         └─ ORDER_FILLED (cierre) → Estado: SIN_POSICION
│              └─ Resultado registrado en trades.db
│
└─ ORDER_REJECTED / ORDER_CANCELLED → Estado: SIN_POSICION
     └─ Registrado en Audit con motivo
```

### 2.1 Estados de la operación y recuperación (CR-005)

Correspondencia con los estados formales de la operación (REQ-G-037):

| Ciclo de vida de posición | Estados de la operación |
|---|---|
| Propuesta en evaluación de riesgo | `PROPOSED` → `RISK_APPROVED` / `RISK_REJECTED` |
| Autorización humana (vigencia 30 min, REQ-G-039) | `AWAITING_AUTH` → `AUTHORIZED` / `AUTH_REJECTED` / `AUTH_EXPIRED` |
| ORDER_SUBMITTED (compra) | `ENTRY_PENDING` (persistido antes del envío) |
| ORDER_FILLED, colocación del stop | `ENTRY_FILLED` → `POSITION_OPEN` |
| ORDER_REJECTED / ORDER_CANCELLED sin ejecución | `ENTRY_FAILED` |
| Evento de salida | `EXIT_PENDING` → `CLOSED` |
| Anulada antes del envío (reinicio o condiciones cambiadas) | `INVALIDATED` |

Al arrancar, cada operación no terminal se resuelve según REQ-G-038; el sistema queda en modo seguro hasta confirmación del propietario (REQ-G-P26).

---

## 3. Flujo de Datos de Investigación y ML

Separado completamente del flujo de producción:

```
Modo Research:
│
├─ Hipótesis → Preregistro (congelado)
│
├─ Training Set → Entrenamiento de modelo
│    └─ Validation Set → Selección de configuración
│
├─ OOS Evaluation → Evaluación no usada en desarrollo
│
├─ LOCKBOX OOS → Evaluación final (aislado; no usado hasta aprobación)
│    └─ NUNCA se usa para decisiones de desarrollo
│
├─ Walk-Forward Analysis
│    └─ Bucle: entrenar→evaluar→desplazar→repetir→consolidar
│
└─ Resultado del experimento: APPROVED | REJECTED | INCONCLUSIVE
     └─ APPROVED ≠ autorización de operar con capital real
          └─ Requiere: revisión humana (G3 equivalente experimental)
```

**Restricción crítica:** Los datos de cada partición están segregados. No puede existir contaminación entre Train, Validation, OOS y LOCKBOX. Las transformaciones y selección se ajustan SOLO con datos de la partición permitida.

---

## 4. Flujo de Datos del Fiscal Ledger

```
ORDER_FILLED (confirmado por Binance)
│
▼ Execution Engine extrae de la ejecución:
  - fecha_utc, cantidad, precio_usdt, comisiones_usdt, order_id
│
▼ Fiscal Ledger obtiene:
  - fecha_mxn (conversion de zona horaria a MX)
  - tc_mxn_usd (fuente BCI Banxico, API SIE — REQ-G-P07 resuelto en DEC-006; tratamiento fiscal sujeto a REQ-G-P08)
  - Calcula: monto_usdt, monto_mxn, comisiones_mxn
│
▼ Calcula FIFO:
  - Para BUY: agrega lote al registro de inventario
  - Para SELL: consume lotes en orden FIFO; calcula costo_acum_mxn y ganancia_mxn
│
▼ Inserta en trades.db con todos los campos
│
▼ Actualiza vistas: resumen_anual, posicion_abierta
```

---

## 5. Trazabilidad de Correlation IDs

Toda la cadena de un análisis/operación puede reconstruirse mediante `correlation_id`; cada `causation_id` apunta al evento que causa el siguiente (orden vigente tras CR-004 y CR-005; actualizado por CR-008):

```
E1  ANALYSIS_REQUESTED              (correlation_id: X, causation_id: null)
E2  REGIME_CLASSIFIED               (X, causation_id: E1)
E3  ML_INFERENCE_COMPLETED          (X, causation_id: E1)
E4  STRATEGY_CANDIDATE              (X, causation_id: E2, E3)   — o NO_SETUP (fin del ciclo)
E5  MARKET_ANALYSIS_COMPLETED       (X, causation_id: E4)
E6  MACRO_ANALYSIS_COMPLETED        (X, causation_id: E4)
E7  STRATEGY_ANALYSIS_COMPLETED     (X, causation_id: E4)      — CR-015
E8  DECISION_SYNTHESIS_COMPLETED    (X, causation_id: E5, E6, E7)
E9  TRADE_PROPOSAL                  (X, causation_id: E8)
E10 RISK_APPROVED / RISK_REJECTED   (X, causation_id: E9)
E11 RISK_ANALYSIS_COMPLETED         (X, causation_id: E10)      — solo con RISK_APPROVED
E12 autorización humana             (X, causation_id: E10)
E13 ORDER_SUBMITTED                 (X, causation_id: E12)
E14 ORDER_FILLED                    (X, causation_id: E13)
E15 STOP_ORDER_PLACED               (X, causation_id: E14)
```

Cuando un evento tiene varias causas, `causation_id` registra la principal y el resto se referencia en el cuerpo del mensaje.

**Regla:** Usando correlation_id: uuid-X es posible reconstruir todo el ciclo, desde el disparador hasta el resultado en Binance y el registro fiscal.

---

## 6. Flujo de Bloqueos del Risk Manager

```
Estado inicial: ACTIVE
│
├─ OpenPositions = 1 → agrega: POSITION_OPEN
│    └─ OpenPositions = 0 → remueve: POSITION_OPEN
│
├─ 3 pérdidas consecutivas → agrega: LOSS_STREAK_LOCK
│    └─ Liberación solo con revisión humana explícita (4 pasos)
│
├─ MonthlyDrawdown ≥ 5% → agrega: MONTHLY_DRAWDOWN_LOCK
│    └─ Liberación solo con autorización humana (nuevo mes NO libera automáticamente)
│
├─ MonthlyTradeCount = 8 → agrega: MONTHLY_TRADE_LIMIT_LOCK
│    └─ Liberación automática al inicio del mes calendario siguiente, con aviso por Telegram (DEC-010 Q28)
│
├─ Equity/datos no verificables → agrega: DATA_UNAVAILABLE
│    └─ Liberación cuando se restaura la verificabilidad
│
├─ Discrepancia con Binance → agrega: EXCHANGE_DESYNC
│    └─ Liberación cuando reconciliación es exitosa
│
└─ RISK_REQUIRES_REVIEW → agrega: MANUAL_REVIEW
     └─ Liberación solo con autorización humana explícita

REGLA: Liberar un bloqueo NO elimina otros bloqueos activos.
REGLA: En todos los estados bloqueados, las acciones de protección (stop-loss, cierre) permanecen disponibles.
```

---

## 7. Parámetros que Afectan Flujos (estado tras CR-008)

| ID | Flujo afectado | Estado |
|---|---|---|
| REQ-G-P01 | Fase 1 / Risk Manager | RESUELTO (DEC-004): Binance USDT/MXN en tiempo real; fuente fiscal ligada a P08 |
| REQ-G-P02 | Fase 1 / Risk Manager | RESUELTO (DEC-004): 5 min; excedido = Fail-Closed |
| REQ-G-P06 | Fase 6 | RESUELTO (DEC-004): Telegram con botones |
| REQ-G-P07 | Fiscal Ledger / Fase 7 | RESUELTO (DEC-006): API SIE de Banxico |
| REQ-G-P08 | Fiscal Ledger | **PENDING** (diferido): validación con contador |
| REQ-G-P19 | Fase 6 / Monitoreo | RESUELTO (DEC-004): arranque, antes y después de cada ciclo, cada 5 min con posición abierta |
| REQ-G-P20 | Fase 6 | RESUELTO (DEC-004): 0.5% |

---

*Fin de data_flow.md*
