# SwingPilot — Architecture Contract v0.1

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** DRAFT — pendiente de verificación adversarial (G2) y aprobación humana (G3)  
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
- Coordinar análisis paralelos (Market, Macro, ML, Regime) y secuenciales
- Validar respuestas de agentes contra contratos JSON definidos
- Enviar resultados consolidados a Decision Synthesis
- Registrar todas las interacciones: modelo, versión, prompt versión, timestamp
- Gestionar errores, timeouts y respuestas incompletas (no asumir aprobación ante falta de respuesta)
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

| Acción | Autoridad | Notas |
|---|---|---|
| Interpretación de mercado | Agentes LLM | Resultado consultivo, no vinculante |
| Generación de señales estratégicas | Strategy Engine + ML Engine | Determinista, versionado |
| Aprobación técnica de operación | Risk Manager determinista | Verifica todos los invariantes |
| Autorización de ejecución | Operador humano | Individual, por operación (INV-008) |
| Envío de órdenes | Execution Engine | Solo con autorización válida vigente |
| Asignación de capital | Operador humano | Cambio requiere autorización del propietario |
| Cambio de modo operativo | Operador autorizado | Registrado; LLM no puede automodificarlo |
| Modificación de políticas críticas | Propietario del proyecto | Cambio requiere aprobación explícita |
| Registro fiscal | Fiscal Ledger | Registros inmutables |
| Verificación | Componente distinto al implementador | Separación de responsabilidades C1/C2 |

---

## 7. Fases de Implementación (referencia)

Las 6 fases de implementación definidas en AI_INTEGRATION.md se mantienen como referencia de orden:

1. Fundaciones: infraestructura base, contratos de mensajes, gestión de secretos
2. Componentes deterministas: Risk Manager, Trading Engine, Market Intelligence
3. Integración LLM: Orchestrator, agentes especializados, AI Provider Adapter
4. Pipeline completo: Research → Paper Trading → Live Trading
5. Interfaz humana: Telegram, mecanismo de aprobación, alertas
6. Producción: seguridad, monitoreo, reconciliación, Fiscal Ledger

**Criterio de salida de cada fase:** criterios de aceptación definidos en AI_INTEGRATION.md (REQ-3048..REQ-3059) verificados por componente distinto al implementador. Estos criterios de salida no tienen REQ-G-NNN asignados en requirements.md v0.1 (ver FIND-004 en verification_report_v1.json); deben ser asignados e incorporados al plan de verificación antes de iniciar FASE 2.

---

## 8. Parámetros PENDING de Arquitectura

| ID | Parámetro | Impacto |
|---|---|---|
| REQ-G-P06 | Mecanismo técnico de aprobación humana | Diseño del Telegram Bot + backend de autorización |
| REQ-G-P18 | Tiempos máximos de respuesta, límites de consumo API | SLA del sistema y configuración de timeouts |
| REQ-G-P19 | Frecuencia de reconciliación con Binance | Frecuencia de polling del Execution Engine |
| REQ-G-P21..P24 | Política de reentrenamiento ML, umbrales de degradación, promoción a producción | Ciclo de vida de modelos ML |

---

*Fin de architecture.md*
