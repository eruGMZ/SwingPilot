# CR-015 — Tipo de evento para el análisis del Strategy Analyst

**Fecha:** 2026-11-19
**Estado:** APROBADA por el propietario el 2026-11-19 («CR-015: Aprobado. Aplica B.1–B.5») y APLICADA (contrato v1.4; DEC-014 Q30).
**Origen:** CONF-007 (ESCALATED), detectado al implementar FEAT-005 (AI Orchestrator) en FASE 2.

## A. Problema

`implementation/data_flow.md` §5 incluye en la cadena del ciclo el paso «E7 análisis del Strategy Analyst (X, causation_id: E4)», y E8 (DECISION_SYNTHESIS_COMPLETED) lo cita como causa. El catálogo de `api_contracts.md` §2 (30 tipos) define MARKET_ANALYSIS_COMPLETED y MACRO_ANALYSIS_COMPLETED, pero ningún tipo para el Strategy Analyst. REQ-G-061/062 exigen que todo mensaje tenga un tipo del catálogo y que el ciclo pueda reconstruirse por sus eventos (TC-AC-04). Hoy la salida del Strategy Analyst no puede registrarse en la auditoría.

## B. Cambio propuesto

1. **api_contracts.md §2:** añadir una fila al catálogo (pasa de 30 a 31 tipos):

   | Tipo | Productor | Consumidor Principal | Descripción |
   |---|---|---|---|
   | STRATEGY_ANALYSIS_COMPLETED | Strategy Analyst | AI Orchestrator | Evaluación de las estrategias candidatas (§3.6); consultiva, no modifica estrategias (REQ-G-054) |

2. **data_flow.md §5:** «E7 análisis del Strategy Analyst» → «E7 STRATEGY_ANALYSIS_COMPLETED (X, causation_id: E4)».
3. **requirements.md REQ-G-063:** actualizar la referencia «catálogo vigente … 30 tipos» → «31 tipos» y citar CR-015.
4. **test_plan.md:** ninguna prueba nueva; TC-MSG-003 y TC-AC-04 pasan a cubrir E7 con su tipo.
5. Versión del contrato: v1.3 → v1.4 en los 5 documentos de `implementation/`.

## C. Impacto

- **Riesgo y ejecución:** ninguno. El evento es informativo; el Strategy Analyst sigue sin autoridad (REQ-G-054, REQ-G-058).
- **Código:** `EVENT_TYPES` en `src/swingpilot/contracts/message.py` (+1 tipo; el test que compara con api_contracts.md §2 lo verificará) y `EVENT_FOR_AGENT["strategy_analyst"]` en `src/swingpilot/ai/orchestrator.py` (de `None` al nuevo tipo). Se elimina la mitigación provisional de CONF-007.
- **Compatibilidad:** cambio aditivo al catálogo; el esquema de mensaje no cambia de versión mayor.

## D. Alternativa considerada

Registrar la salida del Strategy Analyst dentro del payload de DECISION_SYNTHESIS_COMPLETED. Se descarta: la salida no quedaría registrada si Decision Synthesis falla o no se invoca (fallo de otro agente), y E7 no tendría identidad propia en la cadena.

## E. Aprobación

Requiere aprobación explícita del propietario. Al aprobarse: aplicar B.1–B.5, marcar CONF-007 como RESUELTA, registrar en `progress.md`.
