# DEC-015 — Propagación de datos faltantes a Decision Synthesis y prácticas del Orchestrator

**Fecha:** 2026-11-19
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensaje del propietario en la sesión del 2026-11-19 (FASE 2): «Apruebo CR-016 tal cual con E.1–E.3, aplícala y haz commit. CR-016: Aprobado. Propagación en missing_data (sin campo aparte). Incluir E.1, E.2 y E.3. Aplica, contrato a v1.5, haz commit.»
**Alcance:** Registra la decisión del propietario. Se aplica al contrato mediante CR-016 (contrato v1.5). Cierra el hallazgo menor 1 de la QA ronda 3 (FEAT-004/005).

---

## Decisiones

| ID | Tema | Decisión |
|---|---|---|
| Q32 | Datos faltantes de la Fase 3 en la salida de Decision Synthesis | **Aprobada CR-016 B.1–B.5:** propagación determinista en `missing_data` con formato `"<agente>: …"` y `"<agente>: INSUFFICIENT_DATA"`. Se descarta la alternativa D.1 (campo separado). |
| Q33 | Campos comunes de las salidas de agentes (E.1) | Los fija el AI Orchestrator, no el LLM (api_contracts.md §3.0). |
| Q34 | `input_analysis_ids` de Decision Synthesis (E.2) | Debe contener exactamente los tres análisis de la Fase 3; lo demás es fuera de contrato (§3.3). |
| Q35 | Contexto de Market y Macro Analyst (E.3) | Solo los campos de §3.1 y §3.4; el resto se descarta. |
