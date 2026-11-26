# SwingPilot — Architecture Contract v1.12

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** v1.12 (CR-024, aprobada por el propietario el 2026-11-26: persistencia autoritativa de resultados OOS y LOCKBOX y `evaluation_hash`; sin cambios de arquitectura; el módulo de persistencia de resultados es componente de implementación (CR-024 §C)) — v1.11 (CR-023, DEC-025, 2026-11-25: particiones de evaluación prospectivas y frontera de independencia verificable; sin cambios de arquitectura) — v1.10 (CR-022, DEC-024, 2026-11-24: la influencia de una prueba posterior se acredita solo con la cita del par exacto; sin cambios de arquitectura) — v1.9 (CR-021, DEC-023, 2026-11-24: durabilidad confirmada como condición de acceso a datos; sin cambios de arquitectura) — v1.8 (CR-020, DEC-021, 2026-11-24: contabilidad de pruebas de REQ-G-P17; sin cambios de arquitectura) — v1.7 (CR-019, DEC-020, 2026-11-20: evento PROPOSAL_NORMALIZATION_REJECTED; sin cambios de arquitectura) — v1.6 (CR-018, DEC-019: contratos de los motores de la Fase 2; sin cambios de arquitectura) — v1.5 — v1.0 APROBADO por el propietario (G3, 2026-11-18: "APRUEBO EL CONTRATO TÉCNICO v1.0"); v1.1 aplicó CR-011 (DEC-011); v1.2 aplicó CR-012 (DEC-012); v1.3 aplicó CR-013 (DEC-013); v1.4 aplicó CR-015 (DEC-014) y v1.5 aplica CR-016 (DEC-015), todas aprobadas el 2026-11-19; incorpora CR-001..CR-013, CR-015 y CR-016. Cambios posteriores solo mediante solicitud de cambio aprobada y versionado  
**Autoridad documental:** DEC-001 — AI_INTEGRATION.md v1.0 (principios D1–D4 aprobados)

---

## 1. Decisiones Arquitectónicas Fundacionales

Las siguientes decisiones están aprobadas (DEC-001) y no son negociables para FASE 2:

| ID | Principio | Decisión | Fuente |
|---|---|---|---|
| D1 | Orquestación centralizada | AI Orchestrator central — no hay red de agentes autónoma | AI_INTEGRATION.md |
| D2 | Contratos estructurados | JSON validado con esquemas versionados entre todos los componentes | AI_INTEGRATION.md |
| D3 | Comunicación orientada a eventos | correlation_id/causation_id en cada mensaje; operaciones idempotentes | AI_INTEGRATION.md |
| D4 | Proveedor LLM: Anthropic Claude | API de Anthropic (no Claude Pro); AI Provider Adapter como capa de abstracción | AI_INTEGRATION.md |

**Restricción arquitectónica transversal:** El Risk Manager es determinista y no-LLM. Los agentes LLM tienen autoridad consultiva; la autoridad de ejecución recae en componentes deterministas y en el operador humano (Nivel 1 de autonomía).

---

## 2. Diagrama de Componentes (texto)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAPA DE INTERACCIÓN HUMANA                           │
│                                                                             │
│  [Operador / Propietario]                                                   │
│        │  Autorización individual de operación (INV-008)                   │
│        │  Control de capital, modo operativo, políticas                    │
│        ▼                                                                   │
│  [Telegram Bot Interface]                                                   │
│        │  Propuestas, alertas, solicitudes de aprobación                   │
│        │  El backend valida cada acción                                    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────────┐
│                        CAPA DE ORQUESTACIÓN IA                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────┐                   │
│  │               AI Orchestrator (Central)              │                   │
│  │  - Coordina agentes bajo demanda                    │                   │
│  │  - Gestiona correlation_id                          │                   │
│  │  - Valida respuestas contra contratos               │                   │
│  │  - Maneja errores/timeouts                          │                   │
│  │  - Registra todas las interacciones                 │                   │
│  └──────┬──────┬──────┬──────┬──────────────────────┬──┘                   │
│         │      │      │      │                      │                       │
│    ┌────▼──┐ ┌─▼───┐ ┌▼────┐ ┌▼──────────────┐ ┌──▼──────────────┐        │
│    │Market │ │Macro│ │Strat│ │  Risk Analyst  │ │Decision Synthesis│       │
│    │Analyst│ │Anal.│ │Anal.│ │  (consultivo)  │ │   (TRADE_PROPOSAL│       │
│    │(LLM)  │ │(LLM)│ │(LLM)│ │  (LLM)         │ │   no es orden)   │       │
│    └───────┘ └─────┘ └─────┘ └────────────────┘ └─────────────────┘        │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    AI Provider Adapter                             │    │
│  │          (abstracción entre Orchestrator y Anthropic API)         │    │
│  └────────────────────────┬───────────────────────────────────────────┘   │
│                            │                                               │
│                   [Anthropic Claude API]                                   │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │  Eventos/mensajes JSON con contrato
┌────────────────────────────▼────────────────────────────────────────────────┐
│                     CAPA DE MOTORES DETERMINISTAS                           │
│                                                                             │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐                │
│  │  Trading Engine│  │Market Intel. │  │  Regime Engine  │                │
│  │  (coordinación)│  │(datos OHLCV, │  │(clasificación de│                │
│  │                │  │ indicadores) │  │  condiciones)   │                │
│  └────────┬───────┘  └──────┬───────┘  └────────┬────────┘                │
│           │                 │                   │                          │
│  ┌────────▼───────┐  ┌──────▼───────┐  ┌────────▼────────┐                │
│  │Strategy Engine │  │  ML Engine   │  │Portfolio Manager│                │
│  │(estrategias    │  │(inferencia   │  │(posición única, │                │
│  │ versionadas)   │  │ Python/SK)   │  │ 1 simultánea)   │                │
│  └────────┬───────┘  └──────┬───────┘  └────────┬────────┘                │
│           │                 │                   │                          │
│  ┌────────▼─────────────────▼───────────────────▼────────────────────┐    │
│  │               Risk Manager (DETERMINISTA)                          │    │
│  │   - 12 invariantes INV-001..INV-012                                │    │
│  │   - 8 estados: ACTIVE, POSITION_OPEN, LOSS_STREAK_LOCK,           │    │
│  │     MONTHLY_DRAWDOWN_LOCK, MONTHLY_TRADE_LIMIT_LOCK,              │    │
│  │     DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW              │    │
│  │   - Fail-Closed (INV-012)                                          │    │
│  │   - Solo genera: RISK_APPROVED / RISK_REJECTED / RISK_REQ_REVIEW  │    │
│  └───────────────────────────┬────────────────────────────────────────┘   │
│                               │  RISK_APPROVED + autorización humana       │
│  ┌────────────────────────────▼──────────────────────────────────────┐    │
│  │               Execution Engine                                    │    │
│  │  - Solo acepta autorizaciones válidas                             │    │
│  │  - Reconcilia con Binance                                         │    │
│  │  - Gestiona órdenes parciales                                     │    │
│  └───────────────────────────┬────────────────────────────────────────┘   │
│                               │                                            │
│  ┌────────────────────────────▼──────────────────────────────────────┐    │
│  │               Fiscal Ledger                                       │    │
│  │  - SQLite: trades.db                                              │    │
│  │  - FIFO method                                                    │    │
│  │  - BCI Banxico exchange rate                                      │    │
│  │  - Vistas: resumen_anual, posicion_abierta                        │    │
│  └───────────────────────────┬────────────────────────────────────────┘   │
│                               │                                            │
│  ┌────────────────────────────▼──────────────────────────────────────┐    │
│  │               Audit & Governance                                  │    │
│  │  - Registros inmutables                                           │    │
│  │  - 14 tipos de eventos de auditoría                               │    │
│  │  - correlation_id trazable                                        │    │
│  │  - Traceability Matrix (TRC-NNN)                                  │    │
│  └───────────────────────────┬────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Research & Backtesting  (modo Research — no en flujo Live Trading) │  │
│  │  - Investigación experimental, backtesting, evaluación ML          │  │
│  │  - Separación estricta Train/Val/OOS/LOCKBOX                       │  │
│  │  - Ver REQ-G-057, REQ-G-100..REQ-G-108                            │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┼────────────────────────────────────────────┘
                                │
                       [Binance Spot API]
                       (BTC/USDT — solo)
```

---

## 3. Responsabilidades por Componente

### 3.1 AI Orchestrator

**Responsabilidades:**
- Recibir solicitudes de análisis con contexto estructurado
- Determinar qué agentes participan y en qué orden
- Preparar y distribuir contexto (cada agente recibe contexto mínimo necesario)
- Administrar correlation_id para toda la cadena de un análisis
- Coordinar el análisis paralelo de Fase 3 (Market, Macro y Strategy Analyst) y los pasos secuenciales (CR-004)
- Validar respuestas de agentes contra contratos JSON definidos
- Enviar resultados consolidados a Decision Synthesis
- Registrar todas las interacciones: modelo, versión, prompt versión, timestamp
- Gestionar errores, timeouts y respuestas incompletas (no asumir aprobación ante falta de respuesta)
- Invocar a cada agente como llamada independiente a la Messages API, sin herramientas, con salida estructurada validada por esquema; sin prompt caching (REQ-G-095, CR-006)
- Aplicar los controles de costo: tope mensual, aviso al 80% y omisión de llamadas cuando no puede haber entrada (REQ-G-096)
- NO puede autorizar operaciones ni cambiar capital configurado

**Restricciones:**
- No tiene autoridad de ejecución
- No puede invocar directamente a Binance
- No puede modificar parámetros de riesgo
- Solo coordina; no interpreta el mercado ni genera señales

### 3.2 Agentes LLM Especializados

| Agente | Entrada | Salida | Restricciones |
|---|---|---|---|
| Market Analyst | OHLCV, indicadores, temporalidades | Análisis estructurado (observaciones, evidencia, confianza, limitaciones, timestamp_datos) | No puede autorizar operaciones |
| Macro Analyst | Noticias, eventos macro, regulaciones | Análisis contextual (confirmados vs rumores) | No puede convertir noticia en señal de entrada |
| Strategy Analyst | STRATEGY_CANDIDATE del Strategy Engine (Fase 3, en paralelo con Market y Macro; CR-004) | Evaluación de lógica, condiciones, invalidaciones | No puede modificar estrategias aprobadas ni ejecutar |
| Risk Analyst | Propuesta con RISK_APPROVED, estado del sistema (Fase 5, después del Risk Manager; CR-004) | Evaluación consultiva (no vinculante), mostrada al propietario en Telegram | No tiene autoridad de aprobación; no puede revertir el resultado del Risk Manager |
| Decision Synthesis | Resultados de Fase 2 (deterministas) y Fase 3 (Market, Macro, Strategy Analyst); no del Risk Analyst (CR-004) | TRADE_PROPOSAL o descarte explícito | No puede ocultar incertidumbre; TRADE_PROPOSAL ≠ orden |

**Modelos (REQ-G-095, DEC-009, CR-006):** Market Analyst, Macro Analyst, Strategy Analyst y Risk Analyst → `claude-haiku-5-5`; Decision Synthesis → `claude-sonnet-5-5`. Ningún agente recibe herramientas.

### 3.3 Risk Manager (Determinista)

**Este componente es el más crítico del sistema. Debe ser completamente determinista, reproducible y auditable.**

**Responsabilidades:**
- Recibir TRADE_PROPOSAL y ejecutar validaciones deterministas
- Calcular equity actual (`Equity_t = Cash_t + MarketValue_t`)
- Calcular RiskBudget (`Equity_t × 0.015`)
- Calcular position sizing (`Q = (RiskBudget - FixedCosts) / ((P_e - P_s) + C_e + C_s + S)`)
- Verificar los 12 invariantes INV-001..INV-012
- Gestionar los 8 estados y su coexistencia
- Generar RISK_APPROVED / RISK_REJECTED / RISK_REQUIRES_REVIEW
- Registrar los 14 tipos de eventos de auditoría
- Aplicar Fail-Closed (INV-012) ante incapacidad de verificar cualquier condición

**Implementación obligatoria:**
- Python puro con lógica determinista
- Sin llamadas LLM dentro del Risk Manager
- Sin estado implícito: estado completo serializable y reconstruible
- Cada cálculo registra inputs, fórmula, resultado y timestamp

### 3.4 Execution Engine

**Responsabilidades:**
- Solo acepta autorizaciones válidas (RISK_APPROVED + autorización humana)
- Verificar vigencia, identidad y condiciones de la autorización al ejecutar
- Enviar órdenes a Binance respetando stepSize, minQty, minNotional
- Reconciliar órdenes enviadas con ejecuciones reportadas por Binance
- Gestionar ejecuciones parciales como eventos independientes
- Mantener la máquina de estados de la operación, persistiendo cada transición antes de la acción externa (REQ-G-037, CR-005)
- Ejecutar la recuperación por estado al arrancar (REQ-G-038) y el cierre protector (REQ-G-031)
- No tiene credenciales compartidas con componentes LLM

### 3.5 Fiscal Ledger

**Responsabilidades:**
- Registrar cada operación en trades.db (ver DDL en requirements.md, REQ-G-111)
- Aplicar FIFO de forma consistente durante el ejercicio fiscal
- Usar tipo de cambio BCI Banxico del día de la operación
- Mantener vistas `resumen_anual` y `posicion_abierta`
- No se puede cambiar el motor SQLite ni el método FIFO sin autorización del propietario

### 3.6 Telegram Bot Interface

**Responsabilidades:**
- Mostrar estado del sistema, análisis, propuestas y alertas
- Recibir y registrar autorización humana de operaciones individuales
- El backend valida cada acción; Telegram no es fuente de autoridad independiente
- Las acciones críticas requieren verificación de identidad y permisos en el backend

---

## 4. Modos Operativos

| Modo | Descripción | Órdenes Reales | Requisitos de Activación |
|---|---|---|---|
| Research | Investigación, backtesting, experimentación ML | No | Ninguno (modo predeterminado) |
| Paper Trading | Simulación del flujo completo sin capital real | No | Autorización del operador |
| Live Trading | Operaciones reales en Binance | Sí | Autorización explícita + controles de riesgo activos + credenciales apropiadas |

**Restricción:** Ningún agente LLM puede cambiar el modo a Live Trading de forma autónoma. El cambio está protegido, registrado y requiere autorización humana.

---

## 5. Estrategia de Tecnología

| Componente | Tecnología | Justificación |
|---|---|---|
| Modelos cuantitativos y ML | Python (pandas, NumPy, scikit-learn, XGBoost) | Ecosistema cuantitativo estándar |
| PyTorch/LSTM | Solo con justificación experimental en preregistro | Requiere evidencia adicional |
| Base de datos fiscal | SQLite (trades.db) | Volumen < 1000 filas/año; sin infraestructura de servidor |
| LLM runtime | Anthropic API (Claude) | Decisión aprobada D4; API key en .env |
| Interfaz de usuario | Telegram Bot API | Canal ya definido en las políticas |
| Exchange | Binance Spot API | Único exchange autorizado |
| Formato de contratos | JSON con JSON Schema validado | Versioned, auditable, automáticamente validable |

---

## 6. Separación de Responsabilidades (Tabla de Autoridad)

Fuente: AI_INTEGRATION.md, «¿Quién tiene autoridad sobre qué?» (texto fiel; CR-008). En SwingPilot, el operador humano y el operador autorizado son el propietario.

| Decisión o actividad | Autoridad | Notas del contrato |
|---|---|---|
| Interpretar mercado | Agentes de IA | Resultado consultivo, no vinculante |
| Analizar contexto macro | Agentes de IA | No convierte una noticia en señal |
| Generar hipótesis | IA y Research | Preregistro obligatorio (REQ-G-103) |
| Evaluar estrategias | Strategy Engine | Determinista, versionado |
| Ejecutar modelos predictivos | ML Engine | Determinista, versionado |
| Consolidar evidencia | Decision Synthesis | No fabrica consenso |
| Determinar límites de riesgo | Configuración aprobada y Risk Manager | Invariantes INV-001..012 |
| Aprobar o rechazar técnicamente una operación | Risk Manager determinista | Verifica todos los invariantes |
| Enviar órdenes autorizadas | Execution Engine | Solo con autorización humana válida (INV-008) |
| Decidir aportaciones y retiros de capital | Operador humano (propietario) | — |
| Decidir asignación del presupuesto | Operador humano (propietario) | — |
| Cambiar el modo operativo | Operador autorizado (propietario) | Registrado; ningún LLM puede cambiarlo |
| Modificar políticas críticas | Operador autorizado (propietario) | Requiere aprobación explícita |

Adicionales del contrato (no en la tabla fuente): autorización individual de cada operación por el propietario (INV-008); registro fiscal por el Fiscal Ledger (inmutable); verificación por un componente distinto al implementador (C1/C2).

---

## 7. Fases de Implementación (referencia)

Las 6 fases de AI_INTEGRATION.md («¿En qué fases se implementa la integración?»). No se avanza de fase por haber completado tareas: cada fase requiere evidencia verificable.

| Fase | Contenido | Criterio de salida |
|---|---|---|
| 1. Fundamentos de integración | AI Provider Adapter; Anthropic API; AI Orchestrator; contratos universales; catálogo inicial de eventos; validación y trazabilidad | El Orchestrator coordina una solicitud y recibe respuestas estructuradas, validadas y auditables |
| 2. Agentes especializados | Market, Macro, Strategy y Risk Analyst; Decision Synthesis | Los agentes trabajan coordinadamente, conservan sus resultados y expresan desacuerdos sin producir autorizaciones financieras |
| 3. Integración cuantitativa | ML Engine; Regime Engine; Strategy Engine; normalización de propuestas; consistencia entre análisis y resultados cuantitativos | Las propuestas se relacionan con estrategias, inferencias y evidencia reproducible |
| 4. Integración con riesgo | Decision Synthesis con Risk Manager; validaciones deterministas; autorizaciones con vigencia; bloqueos y fail-safe | Ninguna propuesta llega a ejecución sin autorización válida del Risk Manager |
| 5. Paper Trading | Execution Engine simulado; eventos de órdenes; ejecuciones parciales; reconciliación; trazabilidad | El ciclo completo se prueba sin comprometer capital real |
| 6. Live Trading | Revisión de seguridad; permisos de Binance; reconciliación; aprobación humana del cambio de modo; pruebas controladas | Autorización explícita del operador y cumplimiento de los criterios de aceptación de producción |

Los criterios de cierre de la integración de IA son AC-01..AC-16 (REQ-3054..REQ-3069), con casos en `test_plan.md` §9.

---

## 8. Parámetros de Arquitectura (estado tras CR-008)

| ID | Parámetro | Estado |
|---|---|---|
| REQ-G-P06 | Mecanismo técnico de aprobación humana | RESUELTO (DEC-004): Telegram con botones |
| REQ-G-P18 | Tiempos, consumo y reintentos de la API de IA | RESUELTO (DEC-006, DEC-007, DEC-009): REQ-G-034, REQ-G-095, REQ-G-096 |
| REQ-G-P19 | Frecuencia de reconciliación con Binance | RESUELTO (DEC-004): arranque, antes y después de cada ciclo, cada 5 min con posición abierta |
| REQ-G-P21..P24 | Reentrenamiento, degradación, promoción y límites adicionales | RESUELTO (DEC-005) |

Pendientes técnicos de FASE 2 (no parámetros del propietario): tipo de orden de stop, formato del identificador de cliente, almacenamiento durable, servicio de vigilancia, servicio de IP pública, calibración de `effort`, límite de gasto en consola.

---

*Fin de architecture.md*
