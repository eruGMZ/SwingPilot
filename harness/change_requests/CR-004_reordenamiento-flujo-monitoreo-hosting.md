# CR-004 — Reordenamiento del flujo de decisión, reintentos, vigilancia e IP

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-004") y aplicada.
**Origen:** DEC-007 (Q18–Q22); feedback externo puntos D, E y F.

---

## A. Reordenamiento del flujo de decisión (Q19)

**Problemas actuales:**
1. **Dependencia circular:** el Risk Analyst recibe como entrada la propuesta de operación (architecture.md §3.2, REQ-G-055), pero Decision Synthesis, que produce esa propuesta, integra la salida del Risk Analyst (data_flow.md Fase 4).
2. **Choque con DEC-006 (P18):** la IA solo debe invocarse cuando los filtros deterministas detectan un posible setup, pero hoy los LLM (Fase 2) corren antes del Strategy Engine (Fase 3).
3. **Strategy Analyst sin ubicación:** aparece en architecture.md pero en ninguna fase de data_flow.md.

**Flujo propuesto (sigue siendo de 7 fases):**

| Fase | Contenido | LLM |
|---|---|---|
| 1 | Captura y preparación de datos (sin cambios; solo velas cerradas, CR-003) | No |
| 2 | **Filtro determinista:** Regime Engine y ML Engine; el Strategy Engine evalúa estrategias aprobadas con esos resultados y produce STRATEGY_CANDIDATE. **Si no hay candidato: fin del ciclo con resultado NO_SETUP, sin llamadas a LLM.** | No |
| 3 | **Análisis LLM en paralelo:** Market Analyst, Macro Analyst y Strategy Analyst (este último evalúa los STRATEGY_CANDIDATE) | Sí |
| 4 | **Síntesis:** Decision Synthesis integra Fase 2 y Fase 3; produce TRADE_PROPOSAL o descarte. Ya no integra al Risk Analyst. | Sí |
| 5 | **Validación determinista de riesgo** (Risk Manager, sin cambios). Si RISK_APPROVED: **Risk Analyst** emite su evaluación consultiva sobre la propuesta aprobada y el estado del sistema. | Sí (solo si RISK_APPROVED) |
| 6 | Autorización humana y ejecución. Telegram muestra la propuesta, los cálculos de riesgo **y la evaluación del Risk Analyst**. | No |
| 7 | Registro y retroalimentación (sin cambios) | No |

**Ajuste respecto a lo presentado en la sesión:** en la sesión se planteó Risk Analyst → Risk Manager. Se propone el orden inverso (Risk Manager → Risk Analyst) porque el Risk Manager es determinista y gratuito: si rechaza, no se gasta la llamada al Risk Analyst, y el Risk Analyst evalúa una propuesta que ya pasó los invariantes. Su evaluación sigue siendo consultiva y no vinculante (REQ-G-055); no puede revertir un RISK_REJECTED ni convertir un rechazo en aprobación.

**Rol del ML Engine:** queda explícito que el ML Engine corre en la Fase 2 (determinista); su salida (ML_INFERENCE_COMPLETED) la consume el Strategy Engine (familia ML-Based) y Decision Synthesis solo como contexto. No es un decisor paralelo. Ningún modelo opera en producción sin experimento aprobado (DEC-005).

**Latencia máxima:** 3 tramos LLM secuenciales (Fase 3 en paralelo, Fase 4, Risk Analyst en Fase 5), 60 s cada uno + 1 reintento (B) dentro del límite de 5 min del ciclo.

## B. Reintentos y fallo de agentes (Q20, Q21)

1. Cada llamada a un agente LLM admite **1 reintento** tras pausa breve, solo ante errores transitorios (red, saturación, límite de tasa) o respuesta que no cumple el contrato JSON. Nunca fuera del límite de 5 min del ciclo.
2. Si un agente sigue fallando tras el reintento, **el ciclo termina sin propuesta** (Fail-Closed), con el estado explícito del agente (ERROR/TIMEOUT) registrado.
3. Si se alcanza el tope mensual de gasto de IA (DEC-006), no se hacen llamadas y el ciclo termina sin propuesta.
4. Lo anterior no aplica a órdenes a Binance (rige REQ-G-032). Las lecturas de datos de Binance admiten el mismo reintento único.

## C. Vigilancia del proceso (Q18) y reinicio automático (Q22)

1. SwingPilot emite un latido (heartbeat) tras cada ciclo de reconciliación y como mínimo cada 15 min. El latido no contiene saldo, posiciones ni credenciales.
2. Un **servicio externo de vigilancia** (dead-man's switch), fuera de la red del propietario, emite alerta si pasan 30 min sin latido.
3. La URL o clave de ping es secreta (`.env`). El servicio externo no tiene ninguna capacidad de aprobar operaciones ni acceso a credenciales.
4. En la máquina de SwingPilot (Laptop B, DEC-007), el proceso se reinicia automáticamente si se cae; al arrancar entra en modo seguro (REQ-G-P26) y aplica REQ-G-032.

## D. Verificación de IP pública (Q22)

1. SwingPilot consulta su IP pública al arrancar y en cada ciclo.
2. Si difiere de la IP registrada en la restricción de la clave de Binance (REQ-G-093), entra en Fail-Closed (sin operaciones nuevas) y avisa por Telegram antes de intentar operar.
3. Reanudar requiere que el propietario actualice la IP en Binance y confirme.
4. Posiciones abiertas: protegidas por el stop en Binance (REQ-G-031) aunque el sistema no pueda operar.

---

## Documentos del contrato afectados

- `implementation/data_flow.md` — §1 (fases 2 a 6 reordenadas), §2 si aplica.
- `implementation/requirements.md` — REQ-G-071, REQ-G-072, REQ-G-073, REQ-G-074, REQ-G-075 (fases); REQ-G-055 (Risk Analyst: momento de ejecución); REQ-G-P18 (reintentos); requisitos nuevos REQ-G-034 (reintentos y fallo de agentes), REQ-G-035 (vigilancia y reinicio), REQ-G-036 (verificación de IP).
- `implementation/architecture.md` — §3.2 (entrada/momento del Risk Analyst y Strategy Analyst), diagrama de orquestación si aplica.
- `implementation/api_contracts.md` — eventos nuevos: NO_SETUP, RISK_ANALYSIS_COMPLETED, HEARTBEAT, PUBLIC_IP_CHANGED.
- `implementation/test_plan.md` — pruebas nuevas:
  - TC-FLOW-001 — Sin STRATEGY_CANDIDATE → NO_SETUP y cero llamadas a LLM.
  - TC-FLOW-002 — RISK_REJECTED → no se invoca al Risk Analyst.
  - TC-FLOW-003 — Telegram muestra la evaluación del Risk Analyst junto con la propuesta.
  - TC-LLM-001 — Error transitorio → 1 reintento; segundo fallo → ciclo sin propuesta.
  - TC-LLM-002 — Respuesta fuera de contrato JSON → 1 reintento; segundo fallo → ciclo sin propuesta.
  - TC-LLM-003 — Tope mensual alcanzado → sin llamadas; ciclo sin propuesta.
  - TC-OPS-001 — Sin latido 30 min → alerta del servicio externo.
  - TC-OPS-002 — Proceso terminado → reinicio automático en modo seguro.
  - TC-OPS-003 — IP pública distinta → Fail-Closed y aviso antes de operar.

## Impacto

- **Arquitectónico:** medio. Reordena fases del flujo aprobado en AI_INTEGRATION.md (DOC-003) sin agregar ni quitar agentes ni componentes. AI_INTEGRATION.md no se modifica: el contrato registra la desviación con referencia a este CR y DEC-007.
- **Costo:** reduce llamadas a la IA (cero sin setup; sin Risk Analyst si el Risk Manager rechaza).
- **Riesgo:** elimina la dependencia circular; reduce operaciones con información incompleta; detecta caídas y cambios de IP.
- **Pendiente técnico (FASE 2):** elección del servicio externo de vigilancia; servicio de consulta de IP pública.

## Aprobación

Aprobada el 2026-11-18 con la frase "APRUEBO CR-004". Aplicada en: `data_flow.md` (§1 fases 2–6), `requirements.md` (REQ-G-055, 071, 072, 073, 074 y P18 ampliados; REQ-G-034, 035, 036 nuevos), `architecture.md` (§3.2), `api_contracts.md` (eventos NO_SETUP, RISK_ANALYSIS_COMPLETED, HEARTBEAT, PUBLIC_IP_CHANGED), `test_plan.md` (TC-FLOW-001..003, TC-LLM-001..003, TC-OPS-001..003).
