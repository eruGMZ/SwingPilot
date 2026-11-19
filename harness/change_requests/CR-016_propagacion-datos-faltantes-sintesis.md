# CR-016 — Propagación determinista de datos faltantes a la salida de Decision Synthesis

**Fecha:** 2026-11-19
**Estado:** APROBADA por el propietario el 2026-11-19 («CR-016: Aprobado. Propagación en missing_data (sin campo aparte). Incluir E.1, E.2 y E.3») y APLICADA (contrato v1.5; DEC-015). B.1–B.5 y E.1–E.3 aplicados; alternativa D.1 descartada.
**Origen:** QA ronda 3 (re-auditoría de FEAT-004/005), hallazgo menor 1: el texto `"<agente>: INSUFFICIENT_DATA"` lo genera el AI Orchestrator y no la Fase 3; conviene documentarlo en `api_contracts.md` §3.3. Registrado en `feature_list.json` (FEAT-004/005, `approval.open_minor_items`).

## A. Problema

Para cubrir TC-AC-06 del lado de la salida sin depender del prompt (QA ronda 2, menor 3), el AI Orchestrator añade de forma determinista al `missing_data` de la salida de Decision Synthesis lo que declararon los agentes de la Fase 3 (`src/swingpilot/ai/orchestrator.py`, `_propagate_limitations`):

- cada elemento de `missing_data` de Market, Macro y Strategy Analyst, con el prefijo `"<agente>: "`;
- `"<agente>: INSUFFICIENT_DATA"` cuando un agente respondió `status: INSUFFICIENT_DATA` sin detallar qué falta;
- sin duplicados, después de los elementos que la propia síntesis declaró;
- la salida ampliada se vuelve a validar contra el contrato.

El contrato no describe este comportamiento. `api_contracts.md` §3.0 define `missing_data` como «datos faltantes declarados; nunca inventados», sin decir quién los declara. Hoy la salida registrada de la síntesis incluye elementos que no produjo el LLM, y el formato `"<agente>: …"` no está documentado. La QA ronda 3 concluyó que no es una desviación (refuerza REQ-G-056: «identifica datos faltantes», «no oculta incertidumbre»), pero quien lea el registro de auditoría no puede saber por el contrato qué parte escribió el modelo.

## B. Cambio propuesto

1. **api_contracts.md §3.3**, añadir tras la línea «Entrada: …»:

   > **Datos faltantes propagados (CR-016):** el AI Orchestrator añade de forma determinista al `missing_data` de esta salida los datos faltantes declarados por la Fase 3, con el formato `"<agente>: <elemento>"` (`<agente>` ∈ `market_analyst`, `macro_analyst`, `strategy_analyst`). Si un agente respondió `INSUFFICIENT_DATA` sin detallar, se añade `"<agente>: INSUFFICIENT_DATA"`. Los elementos propagados van después de los que declaró la síntesis y sin duplicados. No se inventa ni se elimina nada: solo se copia lo declarado por la Fase 3. La salida ampliada se valida de nuevo contra este contrato; si no valida, la síntesis queda en `ERROR` (`OUT_OF_CONTRACT`).

2. **api_contracts.md §3.0**, en la línea de `missing_data` de la salida: «datos faltantes declarados; nunca inventados» → «datos faltantes declarados por el agente o, en Decision Synthesis, propagados desde la Fase 3 (§3.3); nunca inventados».
3. **requirements.md REQ-G-073:** añadir «Los datos faltantes declarados en la Fase 3 se propagan de forma determinista a la salida de la síntesis (api_contracts.md §3.3, CR-016).»
4. **test_plan.md TC-AC-06:** añadir al Expected: «los datos faltantes de la Fase 3 aparecen en `missing_data` de la síntesis con el prefijo del agente, aunque el LLM los omita».
5. Versión del contrato: v1.4 → v1.5 en los 5 documentos de `implementation/`.

## C. Impacto

- **Riesgo y ejecución:** ninguno. Solo afecta a lo que la síntesis registra como datos faltantes; no cambia decisiones, propuestas ni autoridad.
- **Código:** ninguno. El comportamiento ya está implementado y probado (`test_phase3_limitations_are_propagated_to_synthesis_output`, `test_no_limitations_leaves_synthesis_missing_data_unchanged`, `test_propagation_does_not_duplicate_items`, `test_propagated_synthesis_is_revalidated`, `test_propagated_synthesis_failing_validation_is_out_of_contract`). La CR documenta lo implementado.
- **Compatibilidad:** sin cambio de esquema; `missing_data` sigue siendo una lista de cadenas.

## D. Alternativas consideradas

1. **Campo separado** (p. ej. `propagated_missing_data`) para distinguir lo del LLM de lo propagado. Más claro en la auditoría, pero cambia el esquema de §3.3 (cambio incompatible para quien consuma la salida) y obliga a cambiar el código. Se puede elegir en lugar de B.1–B.2.
2. **Retirar la propagación** y volver a depender del prompt. Deja TC-AC-06 (lado salida) sin validación determinista, que es lo que la QA ronda 2 pidió corregir.

## E. Otras prácticas de implementación no documentadas (para que el propietario decida si se incluyen aquí)

Detectadas al redactar esta CR; no forman parte del hallazgo, pero tienen la misma naturaleza (comportamiento implementado que el contrato no describe):

- **E.1** Los campos comunes de §3.0 (`analysis_id`, `correlation_id`, `causation_id`, `schema_version`, `agent`, `model_id`, `prompt_version`, timestamps) los fija el AI Orchestrator, no el LLM; el LLM produce solo el cuerpo del contrato.
- **E.2** Decision Synthesis debe citar en `input_analysis_ids` exactamente los tres análisis de la Fase 3; otra cosa se trata como fuera de contrato (REQ-G-056/073).
- **E.3** El contexto de Market y Macro Analyst se filtra a los campos de §3.1 y §3.4; cualquier otro campo se descarta.

## F. Aprobación

Requiere aprobación explícita del propietario, indicando si se aplica B.1–B.5 tal cual, se cambia a la alternativa D.1, y si se incluyen E.1–E.3. Al aprobarse: registrar la decisión (DEC), aplicar, pasar el contrato a v1.5, cerrar el menor 1 en `feature_list.json` y registrar en `progress.md`.
