# IMPL-3 — Implementación de CR-021 (durabilidad confirmada; QA-CR020-03)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (implementación; no es una QA independiente).
**Autorización del propietario (2026-11-24):** implementación funcional de CR-021 revisión 2 bajo DEC-023 y el contrato v1.9, exclusivamente para resolver QA-CR020-03; adaptación de las pruebas ejecutables de CR-021 §G.5; sin commit ni push.
**Base:** `f48114c9ad0076671a1f687939f4c93bcd7f7a64` (`develop` = `origin/develop`, árbol limpio). Código igual al de `fde522c`.
**Estado:** IMPLEMENTADO Y ACEPTADO POR EL PROPIETARIO (2026-11-24, §10). QA-CR020-03: **CORREGIDO y aceptado por el propietario; pendiente de reverificación independiente**. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
**Evidencia previa conservada sin cambios:** `IMPL-3_CR-020_QA_independiente.md`, `IMPL-3_CR-020_QA_sondas.py`, `IMPL-3_QA-CR020-03_reproduccion.py`.

## 1. Implementación

| Archivo | Cambio | Contrato |
|---|---|---|
| `src/swingpilot/research/experiments.py` | `RegistryCorruptError`; `_parse_registry`/`_load`: lectura en bytes, P1–P2 (cola sin salto de línea, línea vacía, no válida o que no es un objeto → corrupto), duplicados (evaluación por par y DEVIATION por `deviation_id`: idéntica byte a byte = una entidad lógica; distinta → corrupto) y validación y vinculación de `EVALUATION_PERSISTED` (forma, `marker_id` único, SHA-256 de líneas **anteriores** del tipo, par y `deviation_id` correctos). `records()` usa `_load` (nunca devuelve una lectura parcial). `_write` valida el registro antes de añadir (P1/P3 en la frontera de escritura) y delega en `_write_lines` (descriptor nuevo + `fsync`, supuesto S1). `append_deviation` valida antes de su bloque de incertidumbre. `begin_configuration_evaluation`: protocolo de §D.4 (abajo). `certified()` y `_certifies_all()` | REQ-G-104 v1.9; CR-021 §D.2–§D.4, §F.2–§F.4 |
| `src/swingpilot/research/preregistration.py` | `_replay`: una copia idéntica de un `deviation_id` ya visto se omite como misma desviación lógica (cronología de la primera aparición). `evaluation_evidence_error`: exige un marcador válido del par y, si no está planificada, que certifique su DEVIATION validada | CR-021 §D.2, §D.5; ORQ-017-01 sustituida en ese punto |
| `src/swingpilot/research/trials.py` | Los puntos de decisión DEVIATION se deduplican por `deviation_id` (primera aparición) | CR-021 §D.2 |
| `src/swingpilot/research/partitions.py` | `_deny_reason` (OOS/LOCKBOX): un registro corrupto se deniega **y se anota** en lugar de propagar la excepción sin registro de acceso | CR-021 §F.2 P1 |
| `research/README.md` | Tipo `EVALUATION_PERSISTED`, regla de identidad de DEVIATION y semántica de durabilidad y corrupción | — |

**Protocolo de `begin_configuration_evaluation` (CR-021 §D.4), bajo el bloqueo exclusivo existente:**
1. Lectura validada (`_load`); corrupción o incoherencia → `EvaluationRequestRejected`, nada escrito.
2. Validaciones previas de CR-020 y, para una configuración no planificada sin DEVIATION, construcción y validación de la DEVIATION **antes** de escribir (QA-CR020-01).
3. Si un marcador válido del par certifica toda la evidencia exigida → éxito sin escribir.
4. Si no: evidencia (evaluación nueva o copia byte a byte de su primera aparición; DEVIATION nueva o copia idéntica con el mismo `deviation_id`) en una sola escritura con descriptor nuevo + `fsync`. Fallo → `PersistenceUncertainError`, sin marcador.
5. Marcador con los SHA-256 exactos de esas líneas + `fsync`. Fallo → `PersistenceUncertainError` (R2: la evidencia ya es duradera; el marcador legible autoriza a otros).
6. Relectura validada: solo hay éxito si consta un marcador válido.

**Contabilidad (sin cambios de código en `accounting`):** el conteo sigue siendo por par lógico desde la primera aparición; las copias no suman (I2b, TC-ML-020). Los marcadores no cuentan.

## 2. Trazabilidad contractual

| Obligación (contrato v1.9 / CR-021) | Implementación | Pruebas |
|---|---|---|
| Acceso solo con `EVALUATION_PERSISTED` válido (REQ-G-104; §D.5) | `evaluation_evidence_error`, cargador | `test_cr021_durability.py`: P4, línea legible, conciliación, objeto nuevo y proceso separado |
| Fallos de `fsync` de la evidencia: ni éxito ni acceso; reintentos fallidos repetidos (TC-ML-023) | §D.4 pasos 4 y 6 | `test_p4_repeated_fsync_failures…`, `test_readable_record_after_fsync_failure…` |
| Copias idénticas, sin doble conteo (TC-ML-020, §D.2) | pasos 3–4; `_integrity_error` | `test_durable_reconciliation…`, `test_identical_evaluation_copy…` |
| DEVIATION obligatoria certificada; `deviation_id` conservado | pasos 2 y 4; `_replay` | `test_uncertain_mandatory_deviation…`; `test_qa_cr020_01.py` |
| R2: `fsync` del marcador fallido; marcador perdido (§F.4) | paso 5; acceso basado en el marcador legible | `test_r2_marker_fsync_failure…`, `test_r2_lost_marker…` |
| I2a / I2b (§F.1, §F.8) | contabilidad legible; copia certificada | `test_i2a_…`, `test_i2b_…` (2) |
| Duplicados conflictivos, marcador no vinculable, `marker_id` repetido → Fail-Closed | `_integrity_error`, `_marker_error` | matriz P1; `test_research.py::test_orq_017_01_…` |
| P1–P5 en todas las rutas de TC-ML-023 | `_load` en toda lectura; `_write` y `append_deviation` antes de escribir; `_deny_reason` | matriz P1 (§4) |
| QA-CR020-01 conservado | paso 2 sin cambios de semántica | `test_qa_cr020_01.py` (11) |

## 3. Pruebas adaptadas (CR-021 §G.5)

Ninguna aserción no afectada se eliminó. Cada cambio se justifica por la obligación que sustituye la anterior:

| Prueba | Expectativa anterior | Expectativa nueva | Obligación |
|---|---|---|---|
| `test_trials_accounting.py::test_tc_ml_023_uncertain_write_blocks_start_record_present_counts` | El reintento tiene éxito sin escribir; 1 línea de evaluación | El reintento escribe una copia idéntica y un marcador: 2 líneas idénticas, conteo 1, 1 marcador | CR-021 §D.4 (sustituye CR-020 §C.3.2 paso 1); TC-ML-023 v1.9 |
| `test_trials_accounting.py::test_tc_ml_023_failed_write_before_bytes_is_uncertain_and_does_not_count` | Simulaba el fallo sustituyendo `_write` | Sustituye `_write_lines` (nueva primitiva de escritura con `fsync` del inicio de evaluación); mismas aserciones + marcador tras el reintento | §D.4; §G.5 |
| `test_qa_cr020_01.py::test_valid_unplanned_…` | Tipos `[CE, DEVIATION]` | `[CE, DEVIATION, EVALUATION_PERSISTED]` | §D.3 |
| `test_qa_cr020_01.py::test_partial_persistence_…` | Reintento: `[CE, DEVIATION]` | `[CE, CE (copia), DEVIATION, EVALUATION_PERSISTED]`, conteo 1 | §D.4; TC-ML-020 v1.9 |
| `test_qa_cr020_01.py::test_planned_configuration_behavior_is_unchanged` | `[CE]` | `[CE, EVALUATION_PERSISTED]` | §D.3 |
| `test_qa_cr020_01.py::_fail_deviation_writes` (auxiliar compartido) | Sustituía `_write` para el registro DEVIATION | Sustituye `_write_lines` y deja llegar solo la evaluación (persistencia parcial). Afecta también a `test_malformed_deviation_does_not_unlock_unplanned_pair`, cuyo cuerpo y aserciones **no cambian** | §D.4 |
| `test_research.py::test_tc_ml_010_…` | 11 líneas | 12 (+1 `EVALUATION_PERSISTED`) | §D.3 |
| `test_research.py::test_orq_017_01_chronology_and_duplicate_inconsistencies_fail_closed` (bloque de duplicado) | Dos DEVIATION añadidas con el mismo id → «duplicado» | Con `now` fijo: dos líneas idénticas → una desviación lógica; mismo id con otra justificación → «duplicado» (Fail-Closed). Los otros bloques no cambian | §D.2; §G.3 |

Nota: `test_malformed_deviation_does_not_unlock_unplanned_pair` no figuraba por nombre en §G.5; solo cambia el auxiliar compartido con la prueba listada, no la prueba.

## 4. Evidencia de regresión frente a la base

Código de la base extraído con `git archive f48114c src` en un directorio temporal; mismas pruebas.

**`tests/unit/test_cr021_durability.py` (22 pruebas nuevas) con la base: 18 failed, 4 passed.**

| Clase | Pruebas | Resultado con la base |
|---|---|---|
| **Defecto de comportamiento genuino** (QA-CR020-03) | `test_p4_repeated_fsync_failures…` | 1 incierto y **2 éxitos falsos** |
| | `test_readable_record_after_fsync_failure…` | el cargador **entrega** datos |
| | `test_durable_reconciliation…` | el reintento no falla con `fsync` fallando (P4) |
| | `test_i2a_authorized_evaluation_survives…` | tras perder la línea original no duradera, el conteo de una evaluación **con acceso concedido** cae a 0 (subconteo de I2a) |
| | Matriz P1: `blank_middle_line`, `conflicting_evaluation`, `conflicting_deviation`, `no_final_newline`, `non_object_line` | rutas abiertas (abajo) y, en los cuatro primeros, **archivo modificado** |
| **Diagnóstico solamente** (la base ya fallaba cerrando en las 13 rutas, sin identificar la corrupción) | Matriz P1: `invalid_middle_line`, `truncated_tail` | 13 rutas cerradas, archivo intacto; falla solo la aserción del diagnóstico |
| **Protocolo nuevo** (comportamiento que la base no tiene) | `test_uncertain_mandatory_deviation…` (la base escribe la evaluación y falla antes de la DEVIATION), `test_r2_marker_fsync_failure…`, `test_r2_lost_marker…`, 2 de concurrencia | sin marcador ni copias |
| **No aplicable a la base** | Matriz P1: `unbindable_marker`, `duplicate_marker_id` | la base no tiene marcadores que corromper (`StopIteration` en la preparación) |
| Controles (pasan con la base) | `test_p1_control_clean_registry…`, 2 × I2b, `test_identical_evaluation_copy…` | pasan |

**Rutas abiertas con la base en la matriz P1** (las que no fallaron ante la corrupción):

| Corrupción | Rutas abiertas con la base | Archivo modificado |
|---|---|---|
| línea vacía en medio | 9 de 13 (lecturas, `create`, `register_antecedent`, `transition`, `register_provenance`, `record_deviation`, `claim_partition`) | sí |
| evaluación duplicada conflictiva | 9 de 13 | sí |
| DEVIATION duplicada conflictiva | 7 de 13 | sí |
| cola sin salto de línea | 4 de 13 (lecturas y `create`, que **unió la línea nueva a la cola**) | sí |
| línea que no es un objeto | 1 de 13 (`records()`) | no |
| línea final truncada / línea no válida en medio | 0 de 13 | no |

**Pruebas adaptadas con la base:** 8 fallan por diseño, porque afirman el comportamiento de CR-021. Además, `test_repository_registry_contains_declared_antecedents` falla solo en la copia temporal porque no contiene el registro real (artefacto del entorno de la copia).

**Con la implementación:** 22 passed.

## 5. Concurrencia

- `test_concurrent_starts_produce_one_logical_evaluation_and_one_marker`: 6 procesos inician el mismo par sobre un registro sin evidencia → códigos `[0]×6`; exactamente `[CE, EVALUATION_PERSISTED]`; conteo 1; acceso concedido.
- `test_concurrent_recovery_writes_one_copy_and_one_marker`: tras un intento incierto, 6 procesos reintentan a la vez → exactamente una copia y un marcador (`[CE, CE, EVALUATION_PERSISTED]`); conteo 1.
- La sonda P9 preservada sigue dando 1 línea de evaluación con 6 procesos.

## 6. Cobertura de P1 (TC-ML-023)

`test_p1_corruption_blocks_every_path_skips_no_line_and_preserves_the_file`: 9 tipos de corrupción × 13 rutas. Cada ruta debe fallar con un diagnóstico de «registro corrupto»; el archivo debe quedar byte a byte intacto.

- **Corrupciones:** línea final truncada; cola completa sin salto de línea; línea no válida en medio; línea vacía en medio; línea que no es un objeto; evaluación duplicada conflictiva; DEVIATION duplicada conflictiva; marcador no vinculable; `marker_id` repetido.
- **Rutas:**
  - lectura: `records()`, contabilidad (`trials_count`), `confirmatory_status`;
  - escritura: `create`, `register_antecedent`, `transition`, `register_provenance`, `begin_configuration_evaluation`, `record_deviation`, `claim_partition`;
  - acceso a particiones: cargador de Train+Val y cargador de OOS/LOCKBOX (`load_final`, con el sellado aislado para llegar a la puerta del registro; sin leer datos);
  - evaluación: `acceptance.evaluate` (nunca ELIGIBLE).
- **Control:** `test_p1_control_clean_registry_allows_every_path`: con el mismo registro sin corromper, el cargador entrega, el evaluador da ELIGIBLE_FOR_HUMAN_REVIEW y el conteo es 2. La denegación se debe, pues, a la corrupción.
- **P2:** ninguna lectura omite líneas; `records()` nunca devuelve una lectura parcial. **P3/P4:** ninguna ruta reescribe ni repara. **P5:** no hay ruta de recuperación (procedimiento PENDING).

## 7. Resultados

- Focalizadas: `test_cr021_durability.py` 22 passed; `test_trials_accounting.py` + `test_qa_cr020_01.py` 88 passed. Los demás archivos afectados (`test_cr020_regressions`, `test_research`, `test_snapshot`, `test_ml_registry`, `test_engines`) pasan dentro de la suite completa.
- Suite completa: `.venv/bin/pytest -q -p no:cacheprovider tests` → **811 passed, 5 skipped** (789 + 22).
- `python3 scripts/validate_manifest.py`, `validate_requirements.py`, `validate_gates.py` → código 0.
- Registro real: SHA-256 `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b`, sin cambios; sigue siendo legible con las reglas P1–P2 (termina en salto de línea, sin líneas vacías; `test_repository_registry_contains_declared_antecedents` pasa).
- **Artefactos preservados ejecutados sin modificarlos:**
  - `IMPL-3_QA-CR020-03_reproduccion.py`: secciones 1–3 → tres intentos inciertos, conteo 1 y el cargador deniega. La línea «proceso separado» comprueba el predicado de **conteo** (I2b, aprobado), no el acceso. Sección 4 → «ENTREGA datos». El artefacto hace fallar el 2.º `fsync` y lo rotula como el de la DEVIATION. Con el protocolo nuevo, la evaluación y la DEVIATION comparten una escritura y un `fsync`, así que el 2.º es el del marcador: es el caso R2 aprobado (evidencia duradera, marcador legible → acceso; DEC-023 punto 5).
  - Sonda P4: su línea de «puerta» también comprueba el predicado de conteo, y el reintento ya no informa éxito.
  - Sonda P6: INCONCLUSIVE (`REGISTRY_UNREADABLE`) en lugar de una excepción (solapamiento con QA-CR020-05, §8).

## 8. Solapamientos con otros hallazgos (no se cierran)

- **QA-CR020-05** (línea que no es un objeto → excepción en lugar de INCONCLUSIVE): la política P1 hace que `records()` rechace esas líneas, y el evaluador devuelve ahora INCONCLUSIVE (`REGISTRY_UNREADABLE`). Es una consecuencia de CR-021, no una corrección independiente: QA-CR020-05 sigue abierto hasta la decisión del propietario.
- **QA-CR020-O4** (el cargador no considera el estado): sin cambios.
- **QA-CR020-02** (`confirmatory_status` y la lectura estricta de REQ-G-103): sin cambios.
- **QA-CR020-06** (`feature_list.json` desactualizado): sin cambios. El bloque `cr021` de `feature_list.json` dice «implemented: NO» y deberá actualizarse con la indicación del propietario.

## 9. Limitaciones residuales

1. Supuestos S1–S4 de CR-021: un éxito falso de `fsync` del almacenamiento invalida I1 e I2a (verificación en el despliegue, G6, Laptop B).
2. Durabilidad del marcador no garantizada (R2): su pérdida deniega el acceso; la operación original informa incertidumbre mientras otros procesos pueden acceder.
3. Pérdida no detectada de intentos no confirmados antes de cualquier congelación (I2b), aprobada.
4. Una sola línea corrupta bloquea todo el registro de investigación hasta una conciliación manual con procedimiento aprobado (PENDING).
5. Coste: cada lectura y cada escritura validan el archivo completo (lectura en bytes, JSON y SHA-256 por línea); lineal en el tamaño del registro.
6. Solo el inicio de evaluación usa marcador. El resto de escrituras (`CREATED`, `TRANSITION`, `PARTITION_CONSUMED`, procedencia, desviaciones de `record_deviation`) conservan su tratamiento (fuera de alcance, CR-021 §I.5); ahora todas se niegan a escribir sobre un registro corrupto.
7. Acceso directo a `train_val.parquet` fuera de la garantía (A2).
8. La entrada de directorio y la creación del archivo del registro no se sincronizan (S3).

## 10. Aceptación del propietario (2026-11-24)

El propietario aprueba la implementación funcional de CR-021 bajo DEC-023 y el contrato v1.9, y acepta la evidencia:
- 811 passed, 5 skipped y los tres validadores OK;
- las 22 pruebas nuevas y la distinción entre regresiones de comportamiento genuinas y expectativas del protocolo nuevo;
- las 117 combinaciones de corrupción y ruta de la matriz P1;
- la evidencia de concurrencia y de recuperación;
- las adaptaciones autorizadas de pruebas ejecutables y la del auxiliar compartido `_fail_deviation_writes`, con sus aserciones existentes conservadas;
- las limitaciones residuales aprobadas y los solapamientos documentados con QA-CR020-05 y QA-CR020-06, que **no** se cierran.

**QA-CR020-03:** CORREGIDO y aceptado por el propietario; **pendiente de reverificación independiente**. Es aceptación del propietario, no QA independiente.

**Obligaciones de la reverificación independiente (conservadas por indicación del propietario):**
1. Verificar la relación entre la escritura de la evidencia y su `fsync`: que ambos ocurren sobre el **mismo descriptor recién abierto** (supuesto S1), sin depender de un `fsync` posterior ni de otro descriptor.
2. Verificar el **orden de emisión del marcador**: solo después de un `fsync` correcto de la evidencia exacta que certifica, nunca antes ni tras un fallo, y con el SHA-256 de esos bytes.
3. Verificar el **acceso real a los datos entre procesos** (el cargador de Train+Val en otro proceso y con objetos nuevos), no solo los predicados de conteo (`accounting()["pairs"]`), que por diseño (I2b) incluyen intentos no confirmados.

Commit autorizado de los 12 archivos de la implementación, sin push y sin reejecutar pruebas. `feature_list.json` no se modifica (su bloque `cr021` sigue diciendo «implemented: NO»; QA-CR020-06). CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
