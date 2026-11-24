# IMPL-3 — Verificación independiente de CR-020 (FEAT-017)

**Fecha:** 2026-11-24
**Autor:** revisor de QA independiente (sesión nueva, distinta de la del agente implementador). No aprueba su propio trabajo ni el de la implementación; no cierra conflictos ni cambia estados (AGENTS.md).
**Autorización:** verificación independiente de CR-020 dentro de FEAT-017 autorizada por el propietario (2026-11-24), en solo lectura salvo registros temporales sintéticos; lectura autorizada del registro real y de las referencias documentales históricas. Preservación de esta evidencia autorizada por el propietario (2026-11-24).
**Base verificada:** `f2f05a9c96236a4a4d43530ba5906b3310405829` (`develop` = `origin/develop` según la referencia local; sin `fetch` remoto); árbol limpio al empezar y al terminar la verificación.
**Veredicto del revisor:** **CONFORME CON OBSERVACIONES** (§7).
**Estado tras el informe:** CR-020, D2, CONF-009, CONF-010 y FEAT-017 **sin cerrar**. CONF-009 y CONF-010 OPEN; FEAT-017 IN_PROGRESS.
**Artefacto de reproducción:** `harness/verification/IMPL-3_CR-020_QA_sondas.py` (sondas P1–P11, §4).

> Este informe recoge **solo** los hallazgos del revisor independiente. Las decisiones del propietario se registran aparte en §9 y no forman parte de los hallazgos.

## 1. Alcance

**Revisado:**
- Contrato v1.8: REQ-G-P17, REQ-G-103, REQ-G-104 (`implementation/requirements.md`); TC-ML-006 y TC-ML-020..024 (`implementation/test_plan.md`); AC-017-3, AC-017-8 y AC-017-13 (`feature_list.json`).
- `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` (revisión 3, incluida §H); `docs/decisions/DEC-021_aprobacion-cr020-contabilidad-pruebas.md`; `docs/decisions/DEC-022_procedencia-antecedentes-ant-mr-h1-exp-0001.md`.
- Commits `d372e28` (aplicación contractual), `824fae8` (implementación y corrección A2), `f2f05a9` (procedencia real, DEC-022).
- Código: `src/swingpilot/research/{experiments,preregistration,trials,acceptance,partitions}.py`.
- Pruebas: `tests/unit/test_trials_accounting.py`, `test_cr020_regressions.py`, y las adaptaciones de `test_research.py`, `test_snapshot.py`, `test_ml_registry.py` y `test_engines.py`.
- `harness/verification/IMPL-3_CR-020_implementacion.md` §1–§10.
- Procedencia real: `research/experiments/registry.jsonl` (solo lectura) y el repositorio `trading-bot` (solo lectura, `git cat-file`/`git show`).

**Excluido:** D3–D7, funcionalidades ajenas, particiones reales, SNAP-0001, experimentos reales y proveedores de IA. No se modificó ningún archivo del repositorio durante la verificación.

## 2. Trazabilidad contractual y evidencia

| Obligación | Evidencia | Resultado |
|---|---|---|
| REQ-G-P17, AC-017-8, TC-ML-006: el Deflated Sharpe usa `N_pre`/`N_eval`, nunca el conteo vivo | `acceptance.py:183-194`; `trials.py:48-71`; sonda P7 | CONFORME |
| TC-ML-020: unidad del conteo (par experimento–configuración) y doble conteo | `experiments.py:279-340`; la repetición nativa de una configuración de antecedente es un par distinto (R3) | CONFORME (exclusión de escenarios de costes: ver O3) |
| TC-ML-021, CONF-009: procedencia append-only, gramática estricta `AUTORIZA: PROCEDENCIA`, estado original separado | `experiments.py:342-422`; 14 casos de gramática; sondas P10 y P11 | CONFORME |
| TC-ML-022, AC-017-3: conteo congelado y `candidate_selection_rule` | congelación validada dentro del bloqueo (`experiments.py:587-596`); contenido del preregistro ≠ evidencia congelada → INCONCLUSIVE (P7) | CONFORME |
| TC-ML-023, REQ-G-104: inicio duradero de la evaluación | puerta de estados, idempotencia; carrera de 6 procesos → 1 registro (P9) | CONFORME salvo QA-CR020-01 y QA-CR020-03 |
| TC-ML-024: pruebas posteriores a la congelación | clasificación NO RELEVANTE / RELEVANTE / INDETERMINADA (`trials.py:116-138`) | CONFORME salvo la ambigüedad QA-CR020-04 |
| Fail-Closed ante alteración de la decisión | DEC eliminada tras congelar → INCONCLUSIVE (P8) | CONFORME |
| Corrección A2 y conservación de FEAT-015 | el cuerpo de `_load_train_val_for_inspection` es idéntico al de `load_train_val` en `d372e28` (solo se añadió un docstring); `snapshot.py`, `cli.py` y `backtest.py` sin cambios; las 4 pruebas de FEAT-015 solo cambian el nombre del método | Comportamiento de FEAT-015 conservado |
| AC-017-13, DEC-022: registro real | lectura: H_doc 4, H_bound 4, E 0, G 8; las 2 líneas originales son idénticas byte a byte a `d372e28`; las 2 procedencias citan DEC-022 y coinciden exactamente con sus líneas y su evidencia; SHA-256 del registro `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b` igual antes y después | CONFORME |
| Fuentes históricas | `trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md` l. 11-12 y 38-39 (A, B, E1, E2 evaluadas sobre Train, RECHAZADO; A–D de EXP-0001 «aún sin ejecutar»); `21c5f25:backtest/experiments/EXP-0001/preregistration.md` §6 (A–D); `25f0e3f:backtest/REPORTE_FASE0.md` (las 4 configuraciones rechazadas) | Corroboran DEC-022 |
| Regresiones frente a `d372e28` | `test_cr020_regressions.py` sobre una copia `git archive d372e28 src`: **4 failed** con los mensajes esperados (`assert 2 == 0`; 3 × «DID NOT RAISE») | Reproducido |
| Adaptación de pruebas existentes | ninguna función de prueba eliminada; las 5 aserciones sustituidas pasan a la nueva unidad o a `_evaluate_with_trials`; la ruta completa de `evaluate` queda cubierta por las pruebas de integración de TC-ML-006 | Sin debilitamiento material |

## 3. Hallazgos y observaciones (sin resolver)

Severidad: MENOR = defecto o desajuste que no permite un veredicto ELIGIBLE indebido pero incumple el texto del contrato o debilita una garantía; OBS = observación, ambigüedad o evidencia insuficiente.

| ID | Severidad | Clasificación | Resumen |
|---|---|---|---|
| QA-CR020-01 | MENOR | Defecto de implementación | Una solicitud de configuración no planificada queda registrada como evaluada (y desbloquea datos) aunque su DEVIATION sea rechazada |
| QA-CR020-02 | MENOR | Defecto de implementación | `confirmatory_status()` sigue indicando «confirmatorio» tras una configuración no planificada o una selección fuera de la regla |
| QA-CR020-03 | MENOR | Desajuste contractual y de durabilidad | Tras una escritura incierta el cargador entrega datos y el reintento tiene éxito sin ningún `fsync` correcto |
| QA-CR020-04 | OBS | Ambigüedad contractual | La relevancia de una prueba posterior solo se detecta si se cita el par exacto |
| QA-CR020-05 | OBS | Robustez | Una línea JSON que no es un objeto hace que `evaluate()` lance una excepción en lugar de devolver INCONCLUSIVE |
| QA-CR020-06 | MENOR | Trazabilidad documental | `feature_list.json` no refleja el estado implementado |
| QA-CR020-O3 | OBS | Evidencia insuficiente | Afirmaciones verificadas solo por construcción o no reproducibles desde el historial |
| QA-CR020-O4 | OBS | Nota | El cargador no considera el estado del experimento |

### QA-CR020-01 — DEVIATION validada después del registro duradero (MENOR)

- **Código:** `experiments.py:681-688` escribe `CONFIGURATION_EVALUATED` antes de llamar al constructor de la DEVIATION (`experiments.py:689-700`); las validaciones de `informed_by` y del SHA-256 se ejecutan dentro de `build()` (`preregistration.py:299-308`). `begin_evaluation` solo comprueba antes que `informed_by` sea una lista y que haya justificación (`preregistration.py:337-343`).
- **Contrato:** CR-020 §C.3.2 (validaciones previas antes de escribir; configuración no planificada → registro **y** DEVIATION); B.4.1 (una solicitud rechazada no se registra como evaluada); R2 (una referencia inexistente o posterior rechaza la escritura); TC-ML-023.
- **Reproducción (P1):** `begin_evaluation("Z", justification="j", informed_by=[{"experiment_id": "EXP-0199", "config_id": "Q"}])` lanza `PreregistrationError`; sin embargo el par `(EXP-0101, Z)` consta en `accounting()["pairs"]` (cuenta y el cargador entregaría Train+Val) y no hay DEVIATION.
- **Mitigación existente:** el evaluador devuelve INCONCLUSIVE (`UNPLANNED_CONFIGURATION`, P2); un reintento con `informed_by` válido completa la DEVIATION.

### QA-CR020-02 — `confirmatory_status()` no aplica la interpretación estricta de REQ-G-103 (MENOR)

- **Código:** `preregistration.py:518-525` solo considera las desviaciones de campos de diseño posteriores a la exposición OOS. La interpretación estricta (configuración no planificada o selección fuera de la regla → no confirmatorio) solo se aplica en `trials.py:81-86` y `trials.py:112-114`.
- **Contrato:** REQ-G-103 v1.8 («Evaluar una configuración no planificada, o seleccionar una candidata distinta de la que da la regla, es una desviación y el experimento deja de ser confirmatorio»); interpretación estricta mantenida por el propietario (`IMPL-3_CR-020_implementacion.md` §8).
- **Reproducción (P2, P3):** con la DEVIATION de la configuración no planificada `Z`, o con una selección que incumple `ARGMAX`, `confirmatory_status(...)["confirmatory"]` devuelve `True`; el evaluador devuelve INCONCLUSIVE.
- **Riesgo:** es la consulta prevista para HUMAN_REVIEW (ORQ-017-01, O2); mostraría «confirmatorio» para un experimento que no lo es.

### QA-CR020-03 — Escritura incierta: cargador y reintento sin durabilidad confirmada (MENOR)

- **Código:** el cargador solo exige que el par conste (`partitions.py:140-151`); en un reintento idempotente, `begin_configuration_evaluation` no escribe ni ejecuta `fsync` (`experiments.py:677-710`).
- **Contrato:** TC-ML-023 («escritura fallida o incierta → la evaluación no empieza y el cargador no entrega datos»); REQ-G-104 v1.8 («debe quedar registrado de forma duradera antes de empezar»). En tensión con CR-020 §C.3.2 («si el registro llegó a escribirse, el par cuenta; el reintento es idempotente»).
- **Reproducción (P4):** con `fsync` fallando (EIO), la primera llamada lanza `PersistenceUncertainError`; la puerta del cargador ya entregaría datos; el reintento devuelve éxito con `fsync` todavía fallando (1 intento de `fsync` en total).
- **Riesgo:** tras un fallo de `fsync`, la relectura desde la caché de páginas no prueba durabilidad; una caída podría perder el registro después de ejecutarse la evaluación (subconteo).
- **Cobertura:** `test_trials_accounting.py:427-435` fija que el reintento tiene éxito y no prueba el cargador en este caso.
- **Clasificación:** en parte ambigüedad contractual (si el cargador debe negarse hasta un inicio confirmado) y en parte hueco de durabilidad de la implementación.

### QA-CR020-04 — Relevancia por experimento o por par (OBS, ambigüedad contractual)

- **Contrato:** CR-020 §C.4.2, caso 2: «cita en `informed_by` el experimento o el par de `T`».
- **Código:** `trials.py:126-133` solo reconoce la cita del par exacto.
- **Reproducción (P5):** la selección cita `(EXP-0102, YB)`; `(EXP-0102, YA)` se clasifica NO RELEVANTE y `N_eval` = 2. Con la lectura literal del contrato también YA sería relevante (`N_eval` = 3).
- **Efecto:** la interpretación implementada es la menos conservadora. Requiere aclaración del propietario.

### QA-CR020-05 — Registro con una línea que no es un objeto (OBS, robustez)

- **Código:** `trials.py:49-50` (y `trials.py:89-90`, `trials.py:118-119`) usa `r.get` sin comprobar el tipo.
- **Contrato:** CR-020 §C.4.3 (registro corrupto → INCONCLUSIVE).
- **Reproducción (P6):** añadir `[1, 2]` al registro hace que `evaluate()` lance `AttributeError` en lugar de devolver INCONCLUSIVE. Sigue siendo Fail-Closed (no hay veredicto). `begin_configuration_evaluation` rechaza el mismo caso correctamente (`EvaluationRequestRejected`).

### QA-CR020-06 — `feature_list.json` desactualizado (MENOR, trazabilidad)

- `feature_list.json:1720` («TC-ML-020..024 sin implementar») y `feature_list.json:1768` (`cr020.scope`: mecanismo y procedencia «sin implementar ni escribir») no reflejan `824fae8` ni `f2f05a9`.
- No consta en `feature_list.json` la evidencia de ejecución de CR-020, que AGENTS.md exige para la aceptación.
- El texto de severidad de CONF-009 (`implementation/conflict_register.md:154`) describe todavía el conteo por identificador.
- No se corrige en esta verificación; requiere la indicación del propietario antes de cualquier cierre.

### QA-CR020-O3 — Evidencia insuficiente o por construcción (OBS)

- TC-ML-020, «escenario puro de costes o corrida idéntica no suma»: se cumple solo porque quien llama no registra esas corridas; ningún mecanismo lo impone (`test_trials_accounting.py:160-165`).
- La evidencia «antes de la corrección» de A2 (7 failed) no puede reproducirse desde el historial: A2 se aplicó antes del commit `824fae8`.
- P10: una reducción de procedencia se acepta con la misma lista de evidencia que la anterior; cumple formalmente «evidencia documental citada».
- P11: se tolera el espacio final o CRLF en la línea `AUTORIZA: PROCEDENCIA`, igual que en la gramática de QA3R2-04; no se considera defecto.

### QA-CR020-O4 — El cargador no considera el estado del experimento (OBS)

Un par registrado puede seguir cargando Train+Val cuando el experimento ya está en un estado terminal (`partitions.py:129-151`). El contrato no lo prohíbe.

## 4. Sondas sintéticas (P1–P11) y reproducción

**Artefacto:** `harness/verification/IMPL-3_CR-020_QA_sondas.py`. Solo usa registros y decisiones sintéticos en un directorio temporal; no toca el registro real, particiones ni `docs/decisions`; no afirma nada, solo imprime lo observado; no forma parte de la suite.

**Reproducción (desde la raíz del repositorio):**

```
git checkout --detach f2f05a9            # o un árbol idéntico a esa base
.venv/bin/python -I -B harness/verification/IMPL-3_CR-020_QA_sondas.py [DIRECTORIO_DE_TRABAJO]
git status --porcelain                   # debe seguir vacío
```

`DIRECTORIO_DE_TRABAJO` es opcional (por defecto, un directorio nuevo de `tempfile.mkdtemp()`). El entorno es el de `scripts/setup_env.sh` (Python 3.14.4). Nota: el archivo de sondas se añadió después de `f2f05a9`; para ejecutarlo sobre esa base basta con conservarlo sin seguimiento o copiarlo a la misma ruta.

**Resultados observados con `f2f05a9`:**

| Sonda | Qué comprueba | Resultado observado | Relación |
|---|---|---|---|
| P1 | DEVIATION con `informed_by` no verificable | `PreregistrationError`; `CONFIGURATION_EVALUATED` de Z escrito; par Z en la contabilidad; sin DEVIATION; `confirmatory` = True | QA-CR020-01 |
| P2 | No planificada válida | `confirmatory` = True (desviación en `trials_count`); evaluador INCONCLUSIVE `UNPLANNED_CONFIGURATION` | QA-CR020-02 |
| P3 | Selección fuera de la regla | `confirmatory` = True; evaluador INCONCLUSIVE `SELECTION_RULE_VIOLATION` | QA-CR020-02 |
| P4 | `fsync` fallido | `PersistenceUncertainError`; la puerta del cargador entregaría datos; el reintento devuelve éxito con 1 intento de `fsync` | QA-CR020-03 |
| P5 | Cita por par frente a cita por experimento | `ok` True, `N_pre` 1, `N_eval` 2, relevante solo `(EXP-0102, YB)` | QA-CR020-04 |
| P6 | Línea `[1, 2]` en el registro | `evaluate()` lanza `AttributeError`; `begin_configuration_evaluation` → `EvaluationRequestRejected` | QA-CR020-05 |
| P7 | `trials_accounting` ≠ contenido del preregistro | INCONCLUSIVE `TRIALS_COUNT_INCONSISTENT` | Conforme |
| P8 | Decisión eliminada tras congelar | INCONCLUSIVE `TRIALS_COUNT_INCONSISTENT` | Conforme |
| P9 | 6 procesos concurrentes | códigos de salida `[0, 0, 0, 0, 0, 0]`; 1 línea `CONFIGURATION_EVALUATED` | Conforme |
| P10 | Reducción con la misma evidencia | aceptada; G = 7 | QA-CR020-O3 |
| P11 | Espacio final / CRLF | aceptada | QA-CR020-O3 |

Las sondas se ejecutaron durante la verificación desde el directorio temporal de la sesión y, de nuevo, desde su ruta preservada para comprobar la portabilidad de las instrucciones: los 11 resultados coinciden; el árbol siguió limpio y el SHA-256 del registro real no cambió.

## 5. Pruebas y validadores (ejecutados durante la verificación, sobre `f2f05a9`)

- `tests/unit/test_trials_accounting.py` + `tests/unit/test_cr020_regressions.py` → **81 passed**.
- `tests/unit/test_snapshot.py -k "a2 or tc_ml_023 or inspection"` → 8 passed.
- `tests/unit/test_research.py -k "repository_registry or tc_ml_010"` → 2 passed.
- Suite completa: `.venv/bin/pytest -q -p no:cacheprovider tests` → **778 passed, 5 skipped** (120 s; usuario no root, uid 1000; Python 3.14.4).
- `python3 scripts/validate_manifest.py`, `validate_requirements.py`, `validate_gates.py` → código 0. No verifican la semántica del contrato (limitación ya registrada).
- Regresiones sobre la base `d372e28` → 4 failed, como se esperaba.

La preservación de esta evidencia no volvió a ejecutar la suite.

## 6. Limitaciones residuales

**Aceptadas previamente por el propietario y confirmadas como vigentes:**
- piloto previo al preregistro bloqueado hasta D5;
- `informed_by` es una declaración, no una prueba de lo consultado;
- las decisiones tomadas fuera del registro no son detectables;
- conservación versionada del archivo de resultados de la selección no implementada (O4);
- control de las vías de acceso de la aplicación, no del sistema de archivos (`train_val.parquet` sin sellar; guarda estática por nombre, limitada a `src/` y `scripts/`);
- `flock` POSIX sobre un sistema de archivos local.

**Nueva, para consideración del propietario:** QA-CR020-03 añade un riesgo de subconteo ante una caída tras un fallo de `fsync`; de baja probabilidad y de la misma familia que el riesgo residual de ORQ-017-01.

## 7. Veredicto del revisor independiente

**CONFORME CON OBSERVACIONES.** El núcleo de CR-020 funciona según el contrato: contabilidad por configuraciones, conteo congelado y su reconstrucción, selección de candidata, conciliación de pruebas posteriores, procedencia y contabilidad del registro real. No se encontró ningún defecto que permita a un experimento llegar a `ELIGIBLE_FOR_HUMAN_REVIEW` indebidamente. Quedan sin resolver 4 hallazgos MENORES (QA-CR020-01, 02, 03, 06) y 4 observaciones (QA-CR020-04, 05, O3, O4).

## 8. Recomendaciones del revisor (no son decisiones)

- **CONF-010 (MEDIUM): mantener OPEN.** Antes de proponer su cierre, que el propietario decida sobre QA-CR020-01, 03 y 04 (corregir o aceptar como riesgo residual) y que se resuelva QA-CR020-06. QA-CR020-01 y 03 afectan a las garantías de durabilidad y contabilidad que motivan CONF-010.
- **CONF-009 (LOW): mantener OPEN.** No se encontró ningún defecto en el mecanismo de procedencia ni en los registros reales; desde la QA puede proponerse su cierre una vez actualizada la trazabilidad (QA-CR020-06). Sigue vigente la reevaluación obligatoria antes del cierre formal de FEAT-017.
- **D2:** verificada como sustancialmente implementada; se recomienda considerarla «verificada con observaciones» cuando el propietario resuelva QA-CR020-01..04. Correcciones posibles, pequeñas y locales: validar la DEVIATION antes de la escritura duradera; aplicar la lectura estricta de REQ-G-103 en `confirmatory_status`; `fsync` en el acierto idempotente; comprobar el tipo de las líneas en `reconcile`.
- **FEAT-017:** sigue IN_PROGRESS.

## 9. Decisiones del propietario (registro separado de los hallazgos)

- **2026-11-24:** el propietario acepta el informe de QA independiente tal como se entregó, incluido su veredicto CONFORME CON OBSERVACIONES. Esta aceptación **no** cierra CR-020, D2, CONF-009, CONF-010 ni FEAT-017. Autoriza solo la preservación de esta evidencia (este informe, el archivo de sondas y las entradas de `progress.md` y `session-handoff.md`), sin cambios en código funcional, pruebas funcionales, registro real, `feature_list.json`, documentos contractuales, estados de conflictos ni de gates; sin correcciones, sin reejecutar la suite, sin commit ni push.
- **2026-11-24 (aprobación de la preservación):** el propietario aprueba la preservación de la evidencia de QA independiente de CR-020: este informe en español, las 11 sondas sintéticas reproducibles (`IMPL-3_CR-020_QA_sondas.py`) y las actualizaciones de continuidad (`progress.md`, `session-handoff.md`). Acepta la normalización de los identificadores «O3» y «O4» a QA-CR020-O3 y QA-CR020-O4, sin cambios en su contenido ni en su clasificación. Autoriza el commit de los cuatro archivos, sin push y sin reejecutar pruebas ni sondas. `f2f05a9` se conserva como la base funcional auditada. Los ocho elementos de QA siguen sin resolver; CONF-009 y CONF-010 OPEN; D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
- **Pendientes del propietario (PENDING):** decisión sobre cada uno de QA-CR020-01..06, O3 y O4 (corregir, aclarar el contrato o aceptar como riesgo residual); cierre o no de CONF-009 y CONF-010; estado de D2; actualización de `feature_list.json`.
