# SwingPilot — Data Flow v0.1

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** DRAFT — pendiente de verificación adversarial (G2) y aprobación humana (G3)

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
│  - Obtener OHLCV de Binance: D1, H4, H1 para BTC/USDT                  │
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
│  - Genera human_authorization_id con vigencia limitada                  │
│                                                                         │
│  Execution Engine (solo si autorización válida):                        │
│  - Re-verifica condiciones de riesgo al momento de ejecución            │
│  - Si condiciones cambiaron materialmente → nueva autorización          │
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
│    ├─ Colocación inmediata de stop en Binance (REQ-G-031, CR-002)
│    │    - Éxito → STOP_ORDER_PLACED
│    │    - Fallo → STOP_ORDER_FAILED → aviso Telegram + Fail-Closed
│    │      (bloqueo de nuevas entradas; cierre o intervención del propietario)
│    └─ Estado: POSITION_OPEN
│         │
│         ├─ Monitoreo continuo (segunda capa; el stop primario vive en Binance):
│         │    - Precio actual vs stop-loss
│         │    - Equity y drawdown mensual
│         │    - Estado de Binance (reconciliación, incluye stop activo)
│         │
│         ├─ Modificación de stop permitida (REQ-G-027):
│         │    - Cancelar y reemplazar en Binance → STOP_ORDER_REPLACED
│         │
│         ├─ Evento de salida:
│         │    - Stop ejecutado en Binance → ORDER_FILLED (SELL)
│         │    - Stop alcanzado sin ejecución en Binance → ORDER_SUBMITTED (SELL)
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
  - tc_mxn_usd (PENDING: fuente BCI Banxico — REQ-G-P07)
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

Toda la cadena de un análisis/operación puede reconstruirse mediante correlation_id:

```
ANALYSIS_REQUESTED (correlation_id: uuid-X, causation_id: null)
├─ MARKET_ANALYSIS_COMPLETED (correlation_id: uuid-X, causation_id: uuid-X)
├─ MACRO_ANALYSIS_COMPLETED (correlation_id: uuid-X, causation_id: uuid-X)
├─ ML_INFERENCE_COMPLETED (correlation_id: uuid-X, causation_id: uuid-X)
├─ REGIME_CLASSIFIED (correlation_id: uuid-X, causation_id: uuid-X)
├─ STRATEGY_CANDIDATE (correlation_id: uuid-X, causation_id: uuid-X)
├─ DECISION_SYNTHESIS_COMPLETED (correlation_id: uuid-X, causation_id: uuid-X)
├─ TRADE_PROPOSAL (correlation_id: uuid-X, causation_id: uuid-X)
├─ RISK_APPROVED (correlation_id: uuid-X, causation_id: uuid-X)
├─ [Autorización humana] (correlation_id: uuid-X, causation_id: uuid-X)
├─ ORDER_SUBMITTED (correlation_id: uuid-X, causation_id: uuid-X)
└─ ORDER_FILLED (correlation_id: uuid-X, causation_id: uuid-X)
```

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
│    └─ Liberación al inicio del mes calendario siguiente (PENDING: requiere ratificación del propietario — ver FIND-003)
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

## 7. Parámetros PENDING que Afectan Flujos

| ID | Flujo afectado | Descripción |
|---|---|---|
| REQ-G-P01 | Fiscal Ledger / Fase 7 | Fuente USDT/MXN para `tc_mxn_usd` |
| REQ-G-P02 | Fase 1 / Risk Manager | Antigüedad máxima del tipo de cambio |
| REQ-G-P06 | Fase 6 | Mecanismo técnico de aprobación humana |
| REQ-G-P19 | Fase 6 / Monitoreo | Frecuencia de reconciliación con Binance |
| REQ-G-P20 | Fase 6 | Tolerancia de desviación de precio antes de nueva autorización |

---

*Fin de data_flow.md*
