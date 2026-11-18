# CR-006 — Modelos por agente, orquestación y controles de costo de la IA

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-006") y aplicada.
**Origen:** DEC-009 (Q26, Q27). Amplía REQ-G-091 (integración Anthropic), REQ-G-034 (reintentos) y REQ-G-P18 (tope de $5 USD/mes, DEC-006).

---

## A. Modelo por agente (Q26)

| Agente | Modelo | Identificador |
|---|---|---|
| Market Analyst | Claude Haiku 5.5 | `claude-haiku-5-5` |
| Macro Analyst | Claude Haiku 5.5 | `claude-haiku-5-5` |
| Strategy Analyst | Claude Haiku 5.5 | `claude-haiku-5-5` |
| Decision Synthesis | Claude Sonnet 5.5 | `claude-sonnet-5-5` |
| Risk Analyst | Claude Haiku 5.5 | `claude-haiku-5-5` |

1. Se usan identificadores exactos, sin alias; `model_id` de cada salida (api_contracts.md §3) registra el modelo efectivamente usado (REQ-G-091).
2. El nivel de esfuerzo (`effort`) se fija explícitamente por agente; valor inicial `medium`, calibrado en el modo de prueba de FASE 2 (el razonamiento se cobra como tokens de salida).
3. Cambiar el modelo de un agente requiere una DEC nueva.

## B. Forma de orquestación (Q27)

1. Cada agente es una llamada independiente a la **Messages API**, orquestada por el AI Orchestrator determinista según las fases de `data_flow.md` §1. No se usan Claude Agent SDK ni Managed Agents: dan al modelo control del bucle o acceso a archivos y terminal, incompatible con el aislamiento de los componentes LLM (sin credenciales ni acciones).
2. Los agentes **no reciben herramientas** (tools). Su salida se obtiene como **salida estructurada validada por esquema** (`output_config.format`) con el contrato JSON de `api_contracts.md` §3; una salida que no valida cuenta como respuesta fuera de contrato (REQ-G-034).
3. No se usa la Batches API: su latencia es incompatible con el ciclo de 5 min.
4. Una respuesta con `stop_reason: "refusal"` se trata como fallo del agente (REQ-G-034): ciclo sin propuesta. No se activa el cambio automático de modelo (`fallbacks`), para que el modelo de cada análisis sea siempre el registrado en §A.

## C. Reintentos del SDK (alinea REQ-G-034)

1. El SDK de Anthropic reintenta por defecto 2 veces (errores 408/409/429/5xx y de conexión). Se configura para que el total sea **1 reintento**, sea con el reintento del SDK o con el propio; nunca ambos.
2. Timeout por llamada: 60 s (REQ-G-P18), configurado explícitamente en el cliente.

## D. Sin prompt caching

1. No se usa `cache_control`. El ciclo es cada 4 h (la caché de 1 h vence antes del siguiente ciclo) y los 5 agentes tienen prompts distintos con datos de mercado que cambian cada ciclo: la escritura en caché (1.25× o 2×) no tendría lecturas que la compensen.
2. Si el modo de prueba muestra reutilización real (p. ej. reintentos con el mismo prefijo), se revisa mediante DEC.

## E. Controles de costo

1. **Contador interno** (ya en REQ-G-034): con el tope mensual de $5 alcanzado, no hay llamadas.
2. **Aviso al 80%:** al alcanzar $4 de gasto en el mes, aviso por Telegram (AI_BUDGET_WARNING).
3. **Sin análisis cuando no puede haber entrada:** antes de la Fase 3, si hay una posición abierta (INV-003) o un bloqueo del Risk Manager que impide nuevas entradas (LOSS_STREAK_LOCK, MONTHLY_DRAWDOWN_LOCK, MONTHLY_TRADE_LIMIT_LOCK, DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW, modo seguro), el ciclo termina sin llamadas a LLM. Cualquier propuesta sería rechazada en la Fase 5; este control solo evita pagar por ella. No afecta las acciones de protección ni la gestión de la posición abierta.
4. **Límite en la consola de Anthropic** como respaldo, igual o ligeramente superior a $5, si la cuenta lo permite (PENDING FASE 2: disponibilidad en la cuenta).
5. Se registra el uso (`usage`) de cada llamada para medir el costo real por ciclo (REQ-G-091).

---

## Documentos del contrato afectados

- `implementation/requirements.md`:
  - **REQ-G-095 (nuevo):** modelos por agente, orquestación por Messages API sin herramientas, salida estructurada, sin caching, rechazo como fallo (§A, §B, §D).
  - **REQ-G-096 (nuevo):** controles de costo (§E).
  - REQ-G-034: reintentos del SDK alineados (§C).
  - REQ-G-091 y REQ-G-P18: referencias a REQ-G-095 y REQ-G-096.
- `implementation/data_flow.md` — §1: control previo a la Fase 3 (§E punto 3).
- `implementation/architecture.md` — AI Orchestrator / agentes: forma de invocación y modelos.
- `implementation/api_contracts.md` — `model_id` con los valores de §A; evento nuevo AI_BUDGET_WARNING.
- `implementation/test_plan.md` — pruebas nuevas:
  - TC-AI-001 — Cada agente usa el modelo de §A y lo registra en `model_id`.
  - TC-AI-002 — Las llamadas a agentes no incluyen herramientas.
  - TC-AI-003 — Salida que no valida contra el esquema → tratada como fuera de contrato (1 reintento; luego ciclo sin propuesta).
  - TC-AI-004 — `stop_reason: "refusal"` → fallo del agente; sin cambio de modelo.
  - TC-AI-005 — Error transitorio → total de 1 reintento (SDK + propio).
  - TC-AI-006 — Gasto mensual en $4 → AI_BUDGET_WARNING.
  - TC-AI-007 — Posición abierta o bloqueo de entradas activo → ciclo sin llamadas a LLM.

## Impacto

- **Arquitectónico:** bajo. Concreta cómo se invoca a los agentes existentes; no agrega componentes.
- **Costo:** estimado ~$0.03 por ciclo con setup; el control §E.3 reduce llamadas inútiles.
- **Riesgo:** reduce. Sin herramientas ni control del bucle por el modelo; salida validada; modelo registrado.
- **Pendiente técnico (FASE 2):** calibración de `effort`; costo real por ciclo; disponibilidad del límite de gasto en consola.

## Aprobación

Aprobada el 2026-11-18 con la frase "APRUEBO CR-006". Aplicada en: `requirements.md` (REQ-G-095 y REQ-G-096 nuevos; REQ-G-034 con reintentos del SDK; REQ-G-091 y REQ-G-P18 con referencias), `data_flow.md` (§1 control de costo previo a Fase 3; modelos en Fase 3), `architecture.md` (§3.1 AI Orchestrator; §3.2 modelos), `api_contracts.md` (§3 valores de `model_id`; evento AI_BUDGET_WARNING), `test_plan.md` (§8.7 TC-AI-001..007).
