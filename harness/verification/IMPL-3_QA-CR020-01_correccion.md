# IMPL-3 — Corrección de QA-CR020-01 (FEAT-017; CR-020)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (corrección; no es una QA independiente).
**Autorización del propietario (2026-11-24):** corrección de QA-CR020-01 **únicamente**, bajo el contrato v1.8 y CR-020; sin resolver QA-CR020-02..06, O3 ni O4 (en particular, sin ampliar la corrección al problema general de durabilidad de `fsync` de QA-CR020-03); sin commit ni push.
**Base:** `e645a2716c8a8fa675c0c4f1b346a334f214ad6d` (`develop` = `origin/develop`, árbol limpio). Base funcional auditada: `f2f05a9` (el commit `e645a27` solo añadió documentación).
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_QA_independiente.md` §3 (QA-CR020-01) y sonda P1 de `IMPL-3_CR-020_QA_sondas.py`. Ambos se conservan sin cambios como evidencia histórica.
**Estado:** CORREGIDO Y ACEPTADO POR EL PROPIETARIO (2026-11-24, §8) — PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## 1. Causa raíz

1. En `ExperimentRegistry.begin_configuration_evaluation`, el registro duradero `CONFIGURATION_EVALUATED` se escribía **antes** de llamar al constructor de la DEVIATION. Las validaciones obligatorias de la desviación (R2 `informed_by`, SHA-256 de PREREGISTERED, reproducción válida de las desviaciones existentes) se ejecutan dentro de ese constructor (`preregistration._deviation_builder.build`), así que una solicitud no válida dejaba el par escrito y contado, sin DEVIATION.
2. La puerta del cargador (`PartitionLoader.load_train_val_for_configuration`) solo comprobaba que el par constara en la evidencia validada; no exigía la DEVIATION obligatoria de un par no planificado, así que ese estado parcial desbloqueaba Train+Val.

## 2. Cambios

| Archivo | Cambio |
|---|---|
| `src/swingpilot/research/experiments.py` (`begin_configuration_evaluation`) | Si el par no está planificado y su DEVIATION aún no consta, el constructor se ejecuta y su resultado se valida **antes** de cualquier escritura, dentro del mismo bloqueo exclusivo. Cualquier fallo → `EvaluationRequestRejected` sin escribir nada. Después se escriben `CONFIGURATION_EVALUATED` (si no constaba) y la DEVIATION, con el mecanismo existente (`_write` con `fsync`; fallo → `PersistenceUncertainError`). La relectura final exige también la DEVIATION de un par no planificado. Reintento: no reescribe la evaluación existente y solo añade la DEVIATION si falta. |
| `src/swingpilot/research/preregistration.py` | Nueva `evaluation_evidence_error(registry, experiment_id, config_id)`, sin efectos: par planificado en la congelación → sin requisito adicional; par no planificado → exige su DEVIATION (`field` = `trials_count`, `config_id` del par) entre las desviaciones **validadas** por `_replay` (SHA-256 de PREREGISTERED, orden, forma). Ausente, mal formada o registro incoherente → motivo de denegación. |
| `src/swingpilot/research/partitions.py` | `load_train_val_for_configuration` consulta `evaluation_evidence_error` tras comprobar el par; si hay motivo, deniega, lo anota y no lee datos. |
| `research/README.md` | Semántica de la corrección. |
| `tests/unit/test_qa_cr020_01.py` (nuevo) | 11 pruebas de regresión (§3). |

No cambian: estados, transiciones, tipos de registro, contabilidad (`accounting`, `trials_count`), evaluador, `confirmatory_status`, el tratamiento de las escrituras inciertas de pares planificados, el registro real ni los documentos contractuales.

## 3. Evidencia de regresión

**Pruebas nuevas (`tests/unit/test_qa_cr020_01.py`, solo datos sintéticos):**

| Prueba | Comportamiento exigido |
|---|---|
| `test_invalid_unplanned_request_appends_nothing_counts_nothing_grants_nothing` (5 casos: par inexistente —sonda P1—, procedencia inexistente, referencia mal formada, incompleta y repetida) | Rechazo (`EvaluationRequestRejected`); registro idéntico byte a byte; conteo sin cambios; el cargador deniega, lo anota y no lee |
| `test_builder_returning_a_wrong_record_is_rejected_before_writing` | Constructor que no devuelve la DEVIATION del par → rechazo sin escritura |
| `test_valid_unplanned_configuration_is_recorded_with_its_deviation_and_unlocks_data` | `CONFIGURATION_EVALUATED` + DEVIATION (`trials_count`, SHA-256 del preregistro); cuenta 1; el cargador entrega los datos |
| `test_retry_after_success_duplicates_neither_count_nor_deviation` | Reintento → registro idéntico; conteo 1 |
| `test_partial_persistence_counts_conservatively_and_denies_data_until_reconciled` | Escritura de la DEVIATION fallida → `EvaluationPersistenceUncertain`; la evaluación consta y cuenta (conservador); el cargador deniega («DEVIATION»); reintento inválido → rechazo sin escritura y sigue denegado; reintento válido → añade solo la DEVIATION, conteo 1, acceso concedido |
| `test_malformed_deviation_does_not_unlock_unplanned_pair` | Una DEVIATION mal formada añadida a mano no desbloquea los datos |
| `test_planned_configuration_behavior_is_unchanged` | Par planificado: sin DEVIATION, cuenta 1, el cargador entrega; sin constructor → rechazo «no está planificada»; constructor que devuelve `None` → rechazo sin escribir la evaluación |

**Contra la base sin corregir (`e645a27`, mismo árbol de código que `f2f05a9`):** 9 failed, 2 passed. Los 9 fallos son de comportamiento, no de interfaz:
- 6 × registro modificado tras una solicitud que debía rechazarse (5 casos de `informed_by` y el constructor erróneo); la aserción del contenido del registro se comprueba antes que el tipo de excepción;
- 2 × «DID NOT RAISE PartitionAccessError» (persistencia parcial y DEVIATION mal formada desbloquean datos);
- 1 × `['CONFIGURATION_EVALUATED'] == []` (constructor `None`: la evaluación quedaba escrita).

Las 2 que pasan con la base (configuración no planificada válida; reintento tras éxito) son controles preventivos.

**Con la corrección:** 11 passed.

**Sonda P1 preservada (sin modificar el archivo de sondas):** ahora `EvaluationRequestRejected`, sin registros del par y sin el par en la contabilidad validada. P2 y P4 siguen mostrando lo mismo que en el informe de QA (QA-CR020-02 y QA-CR020-03 no se tocaron); P9 sigue dando 1 registro con 6 procesos.

## 4. Pruebas y validadores

- `tests/unit/test_qa_cr020_01.py`, `test_trials_accounting.py`, `test_cr020_regressions.py`, `test_snapshot.py` → **195 passed** (incluida, sin cambios, la prueba de TC-ML-023 de configuración no planificada).
- Suite completa: `.venv/bin/pytest -q -p no:cacheprovider tests` → **789 passed, 5 skipped** (778 + 11 nuevas).
- `python3 scripts/validate_manifest.py`, `validate_requirements.py`, `validate_gates.py` → código 0.
- Registro real: SHA-256 `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b`, sin cambios. Ninguna prueba existente modificada.

## 5. Trazabilidad contractual

| Requisito | Cómo se cumple |
|---|---|
| CR-020 §C.3.2 «validaciones previas (antes de escribir)»; B.4.1 «una solicitud rechazada no se registra como evaluada» | La DEVIATION obligatoria se valida antes de cualquier escritura; el rechazo no escribe, no cuenta y no da acceso |
| CR-020 R2 «una referencia inexistente o posterior hace que se rechace la escritura» | Rechazo de toda la solicitud, no solo de la DEVIATION |
| CR-020 §C.3.2 «configuración no planificada: el registro se escribe igualmente y se registra un DEVIATION»; REQ-G-103 v1.8 | Una solicitud válida deja ambos registros; la relectura exige los dos |
| REQ-G-104 v1.8 «append-only»; «si la escritura falla o es incierta, la evaluación no empieza»; «si el registro llegó a escribirse, el par cuenta» | Persistencia parcial: historial intacto, el par cuenta y el cargador deniega los datos hasta conciliar |
| CR-020 §C.3.2 «el reintento es idempotente» | El reintento no duplica la evaluación ni la DEVIATION |
| TC-ML-023 «configuración no planificada → cuenta, se registra DEVIATION y el veredicto es INCONCLUSIVE» | Sin cambios en el evaluador (`UNPLANNED_CONFIGURATION`) |

No exige cambios contractuales ni decisiones de arquitectura: exigir la DEVIATION antes de entregar datos aplica §C.3.2 (que exige ambos registros para una configuración no planificada) con el mismo criterio Fail-Closed de A2.

## 6. Limitaciones residuales

- **QA-CR020-03 sin cambios (fuera de alcance):** tras un fallo de `fsync`, la relectura desde la caché no prueba durabilidad, y el reintento no vuelve a sincronizar. Afecta igual a la DEVIATION: si su `fsync` falla pero la línea es legible, el cargador puede concederse con una DEVIATION no confirmada como duradera.
- **Comprobación de presencia en el reintento:** la decisión de no reconstruir la DEVIATION se basa en un escaneo sin validar (como antes). Si existiera una DEVIATION mal formada para el par, el reintento no la sustituye y el cargador sigue denegando: Fail-Closed, pero requiere conciliación manual.
- **Coste del cargador para pares no planificados:** la puerta reproduce y valida las desviaciones del experimento en cada carga; cualquier incoherencia en ellas deniega los datos (Fail-Closed).
- **Planificadas:** la puerta exige ahora además una congelación legible con `trials_accounting`. Todo par escrito por la API ya la tiene; solo cambia el resultado de pares añadidos a mano a un experimento sin congelación, que ahora se deniegan.
- `confirmatory_status` sigue sin aplicar la lectura estricta de REQ-G-103 (QA-CR020-02, fuera de alcance).

## 7. Estado de los hallazgos de la QA independiente

- QA-CR020-01: **CORREGIDO y aceptado por el propietario; pendiente de reverificación independiente** (§8).
- QA-CR020-02, 03, 04, 05, 06, O3 y O4: **sin resolver**, sin cambios. QA-CR020-03 incluye la durabilidad de los registros legibles tras un fallo de `fsync` (también de la DEVIATION).

## 8. Aceptación del propietario (2026-11-24)

El propietario aprueba la corrección funcional de QA-CR020-01 y acepta la evidencia de regresión. Acepta expresamente:
- la validación de la evidencia obligatoria de la desviación antes de persistir;
- el rechazo sin registros nuevos ni acceso a datos;
- la contabilidad conservadora y la denegación del acceso tras una persistencia parcial;
- el reintento idempotente;
- las 11 pruebas de regresión nuevas, incluidos los 9 fallos de comportamiento genuinos reproducidos con la base;
- 789 passed, 5 skipped y los tres validadores OK;
- el comportamiento Fail-Closed ante desviaciones mal formadas, con conciliación manual sin reescribir ni borrar registros históricos;
- la exigencia de una congelación legible antes de conceder el acceso a datos.

Autoriza el commit de los ocho archivos de la corrección, sin push y sin reejecutar pruebas. Es aceptación del propietario, **no** reverificación independiente. El informe de QA independiente y las sondas se conservan sin cambios. Sin cambios en CONF-009 y CONF-010 (OPEN), FEAT-015 (DONE) ni FEAT-017 (IN_PROGRESS).
