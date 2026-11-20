# IMPL-3 — QA independiente focalizada de FEAT-018..022 (motores de Fase 2)

**Fecha:** 2026-11-20
**Autorización del propietario:** «Autorizo lanzar la QA focalizada de FEAT-018..022 sobre 7bd631a».
**Base revisada:** `04dc2ea`. Es equivalente a `7bd631a`: los dos commits tienen el mismo árbol, `ff2ef00db2376ad4c6e12fd191ecdbd275607717`. `04dc2ea` es un `commit --amend` hecho fuera de la sesión que solo cambió el mensaje (reflog).
**Revisor:** sub-agente independiente (sonnet). Trabajó en solo lectura, sin red y sin el historial ni las conclusiones del Orquestador. Usó ~115K tokens, 12 herramientas y ~4 min. Gasto de IA de SwingPilot: $0.
**Forma:** una sola revisión focalizada, sin rondas adicionales. Reproducciones y mutaciones en `/tmp/claude-1000/qa-impl3-engines/` (copia del repo). El repo quedó intacto (`git status` vacío tras la revisión).
**Referencia:** contrato v1.6 (`api_contracts.md` §3.8 B.0–B.8 y §4.1 v1.1.0; `data_flow.md`; `test_plan.md`), `feature_list.json`, DEC-017..019.

## Ejecución

`.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_engines.py tests/security/test_impl3_isolation.py` → **39 passed**.

## Hallazgos

Ninguno BLOQUEANTE. Las líneas son las verificadas por el Orquestador en `04dc2ea`; algunas referencias del informe del QA no correspondían a los archivos.

| ID | Sev. | Archivo | Hallazgo | Evidencia | Corrección sugerida |
|---|---|---|---|---|---|
| QA3E-01 | MAYOR | `engines/cycle.py:100-102` | B.8 (`api_contracts.md:547`): ante una síntesis inconsistente con el candidato, la inconsistencia debe **registrarse** con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados. El ciclo solo la deja en `CycleReport.normalization` (en memoria). La cadena del EventStore termina en `DECISION_SYNTHESIS_COMPLETED` sin rastro auditable. | Reproducido por el QA; confirmado por lectura | Registrar la inconsistencia en el EventStore; la prueba de síntesis inconsistente debe comprobar el store. |
| QA3E-02 | MAYOR | `engines/strategy.py:176` | B.6 (`api_contracts.md:455`): `requested_stop ≤ current_stop` es inválida, no se emite y debe quedar registrada como error de la estrategia (`ERROR`, `INVALID_STOP_REQUEST`). El motor la descarta en silencio, y la prueba TC-FLOW-006 fija ese comportamiento. | Reproducido por el QA (trailing 94 con stop 95 → solo `NO_SETUP`); confirmado por lectura | Emitir `STRATEGY_CANDIDATE` ERROR con `INVALID_STOP_REQUEST` (B.7.1); actualizar la prueba. |
| QA3E-03 | MENOR | `engines/regime.py`, `engines/strategy.py` (`MarketInput`) | `DATA_STALE` y `DATA_INCONSISTENT` (duplicados, huecos, desorden; `api_contracts.md:310`) están en el catálogo (`schemas.py:27`), pero ningún motor los emite. Solo se comprueba la última vela cerrada. | Reproducido por el QA (vela D1 duplicada o hueco de 10 días → `COMPLETED`); confirmado por búsqueda | Validar orden, duplicados y huecos en la entrada de mercado. Es validación de datos, no lógica de mercado. |
| QA3E-04 | MENOR | `ai/orchestrator.py` (filtro de la Fase 3), `test_engines.py` | El filtro es correcto, pero la prueba combina sobre FAILED y payload ERROR. Quitar cualquiera de las dos condiciones deja 39 passed. | Mutación (QA) | Dos casos: sobre FAILED con payload COMPLETED, y sobre COMPLETED con payload ERROR. |
| QA3E-05 | MENOR | `engines/strategy.py` | `StrategyDefinition.signal_timeframe` no se usa: una estrategia D1 produce un candidato H4. | Reproducido (QA) | Validar la coincidencia o eliminar el atributo. |
| QA3E-06 | MENOR | `engines/strategy.py` | Si E2 y E3 tienen distinto `correlation_id`, el motor lanza `ValueError` en vez de emitir un ERROR registrado. Quitar la comprobación deja 39 passed. | Lectura y mutación (QA) | Prueba de esa rama; decidir si debe ser un ERROR registrado (B.7.1). |
| QA3E-10 | MENOR | `engines/schemas.py` (B.4) | Las pruebas no detectan dos mutaciones: `satisfied` de `const true` a `boolean`, y la eliminación de `take_profit > entry_zone.max`. | Mutación (QA) | Casos negativos en TC-MSG-004. |
| QA3E-07 | OBS | `strategy.py`, `schemas.py` | Con señal de salida no se evalúa la entrada. `supersedes_entry_candidates` y `discarded_candidates` siempre salen vacíos, y `SUPERSEDED_BY_EXIT` no se usa. Es coherente con re-evaluar en el ciclo siguiente (B.7). | Reproducido (QA) | Documentar la decisión. |
| QA3E-08 | OBS | `engines/normalizer.py` | El normalizador no comprueba que la síntesis parta de ese candidato; solo compara el `correlation_id`. `timestamp_utc` copia el de la síntesis. | Lectura (QA) | Comprobar el vínculo causal o documentarlo. |
| QA3E-09 | OBS | `tests/security/test_impl3_isolation.py` | La prueba de «sin estrategia piloto» solo busca el literal `TF_H4` y la ausencia de `strategies/`. | Lectura (QA) | Comprobar que `StrategyEngine()` y `DecisionCycle` por defecto parten de cero estrategias. |

## Conforme según el QA

- **Sin lógica inventada:** el Regime Engine sin especificación da UNCLASSIFIED, sin estrategia el resultado es NO_SETUP (NO_APPROVED_STRATEGY) y sin modelo es NO_ACTIVE_MODEL. No hay estrategia piloto.
- **Fail-Closed:** los errores técnicos viajan como STRATEGY_CANDIDATE ERROR con sobre FAILED (B.7.1), y la Fase 3 los rechaza sin llamar al LLM. Nada llega a Risk Manager ni a órdenes.
- **Esquemas:** campos, enums y condicionales de B.0–B.7.1 coinciden con el contrato.
- **Normalización:** TRADE_PROPOSAL v1.1.0 se valida, v1.0.0 sigue legible y `causation_id` = E8.
- **Ciclo:** una sola cadena E1→E9 en el mismo EventStore, sin llamadas de IA sin candidato.
- **Mutaciones que las pruebas detectan:** take_profit, zona y stop del normalizador; multi-candidato; piso de stop; Research en Paper; prioridad de salida; ERROR ignorado por el ciclo; ML sin modelo.

## Veredictos

| FEAT | Veredicto |
|---|---|
| FEAT-018 | CONFORME CON OBSERVACIONES (QA3E-03) |
| FEAT-019 (AC-019-4) | CONFORME |
| FEAT-020 | **NO CONFORME** (QA3E-02), con QA3E-05, 06, 07 y 10 |
| FEAT-021 | **NO CONFORME** (QA3E-01), con QA3E-08 |
| FEAT-022 | CONFORME CON OBSERVACIONES (QA3E-01, QA3E-04) |

NO CONFORME se refiere a la conformidad plena con B.6 (FEAT-020) y B.8 (FEAT-021). No hay lógica inventada ni fallos de Fail-Closed.

## Estado

Sin correcciones aplicadas. Los estados de `feature_list.json` no cambian: FEAT-018..022 siguen en IN_PROGRESS. Corregir requiere la indicación del propietario y la forma de verificarlo.

---

## Correcciones (2026-11-20, Orquestador; sin tercera ronda de QA)

**Autorización del propietario:** «Autorizo corregir QA3E-01..06 y QA3E-10 según tu recomendación». Base `04dc2ea`. Verificación:
- Cambios de código: pruebas deterministas que fallan con `04dc2ea` y pasan con la corrección.
- Hallazgos que solo afectaban a las pruebas (QA3E-04 y 10): las mutaciones que antes sobrevivían ahora las detecta la suite.

| ID | Corrección | Pruebas | Con `04dc2ea` | Corregido |
|---|---|---|---|---|
| QA3E-01 | **NO CORREGIDO: bloqueado por CONF-008.** El contrato exige registrar la inconsistencia, pero el catálogo cerrado no define con qué tipo. Elegir uno modifica el contrato, así que se escala con opciones (`conflict_register.md`). | — | — | Pendiente de decisión del propietario |
| QA3E-02 | `strategy.py`: `requested_stop ≤ current_stop` deja de descartarse en silencio. No se emite STOP_ADJUSTMENT_REQUESTED y se registra STRATEGY_CANDIDATE ERROR `INVALID_STOP_REQUEST` (etapa `STRATEGY_EVALUATION`, con `strategy_id`). Se retira de TC-FLOW-006 la aserción que fijaba el comportamiento anterior; el resto de esa prueba no cambia. | `test_qa3e_02_invalid_stop_request_is_recorded_as_error` (94 y 95 con stop actual 95) | 2/2 fallan (solo NO_SETUP) | 2/2 pasan |
| QA3E-03 | `common.py`: `MarketInput.inconsistency(tf)` detecta duplicados, huecos y desorden. Regime, ML (con modelo activo) y Strategy (temporalidad de señal) emiten ERROR `DATA_INCONSISTENT` antes de comprobar la última vela. **DATA_STALE queda PENDING:** el contrato no fija su umbral para velas (P02 es del tipo de cambio). | `test_qa3e_03_regime_…` (3 casos D1), `test_qa3e_03_strategy_and_ml_…` (3 casos H4, en Strategy y ML) y control con serie contigua | 6/6 fallan (`COMPLETED`/sin error) | 6/6 pasan; el control sigue en COMPLETED |
| QA3E-04 | Solo pruebas: el filtro de la Fase 3 se prueba con sobre FAILED + payload COMPLETED y con sobre COMPLETED + payload ERROR, además del caso original. | `test_orchestrator_rejects_error_candidate_in_phase3` (3 casos) | Mutaciones M1 (quitar `status == FAILED`) y M2 (quitar `result_status ≠ COMPLETED`): 39 passed | M1 → 1 failed; M2 → 1 failed |
| QA3E-05 | `strategy.py`: el motor rechaza al construirse una estrategia cuya `signal_timeframe` difiera de la suya. | `test_qa3e_05_strategy_timeframe_must_match_engine` | Falla (se acepta) | Pasa |
| QA3E-06 | `strategy.py`: E2 y E3 de ciclos distintos dejan de lanzar `ValueError` y se registran como STRATEGY_CANDIDATE ERROR `INTERNAL_ERROR`, etapa `INPUT_VALIDATION`, con `upstream_message_id` = E3 (B.7.1). Es un fallo de cableado, no de datos, por eso no se usa DATA_INCONSISTENT. | `test_qa3e_06_e2_e3_from_different_cycles_is_recorded_error` | Falla (excepción) | Pasa |
| QA3E-10 | Solo pruebas: casos negativos de B.4 (condición con `satisfied=false`; take_profit igual, dentro o por debajo de la zona) y un control válido. | `test_qa3e_10_b4_candidate_rules_are_enforced` (4 casos) | Mutaciones M3 (`satisfied` boolean) y M4 (sin regla de take_profit): 39 passed | M3 → 1 failed; M4 → 3 failed |

Con `04dc2ea`, la prueba de control de QA3E-03 falla porque el método no existía; no reproduce ningún defecto.

**Suite:** `tests/unit/test_engines.py` + `tests/security/test_impl3_isolation.py` → 56 passed (39 + 17). Completa: `.venv/bin/pytest -q -p no:cacheprovider tests` → 467 passed, 5 skipped. Validadores → OK.

**Sin tocar:** QA3E-07..09 (observaciones fuera del alcance autorizado), `ai/orchestrator.py` y `engines/schemas.py` (el código ya era correcto; se probaron por mutación y se restauraron byte a byte), SNAP-0001, OOS/LOCKBOX. $0 de IA.

**Estado de las FEAT:** sin cambios en `feature_list.json`; siguen IN_PROGRESS. FEAT-021 tiene QA3E-01 bloqueado por CONF-008.
