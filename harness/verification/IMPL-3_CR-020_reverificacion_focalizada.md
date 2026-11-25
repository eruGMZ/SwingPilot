# IMPL-3 — Reverificación independiente focalizada de CR-020 (N-1; disposiciones N-2, N-3; conciliación D-1..D-5)

**Fecha:** 2026-11-25
**Autor:** auditor de QA independiente (sesión distinta de la del implementador; no implementó, corrigió ni aprobó lo revisado). No aprueba su propio trabajo ni cierra hallazgos, conflictos, decisiones, FEAT ni gates (AGENTS.md).
**Punto de control auditado:** `eac0fa77eccffc04dc53c207b57b5814cc7d5c2f` (`develop`; árbol limpio antes y después; `origin/develop` = `eac0fa7` según la referencia local). Contrato **v1.10**; `feature_list.json` **v1.21.2**; D2 pendiente de cierre.
**Veredicto independiente:** **CONFORME CON OBSERVACIONES.** Ninguna disconformidad contractual. N-1 corregido y verificado de forma independiente; las disposiciones de N-2 y N-3 y la conciliación D-1..D-5 son fieles al informe preservado y al contrato v1.10.
**Estado:** el propietario acepta este informe (2026-11-25) como evidencia para decisiones de cierre posteriores. **La aceptación no constituye el cierre formal** de ningún hallazgo, conflicto, decisión, FEAT ni gate.

## 0. Clasificación del contenido

| Clase | Dónde |
|---|---|
| **Hallazgos independientes** (evidencia de esta revisión) | §1–§4 |
| **Recomendaciones del auditor** (no son decisiones) | §6 |
| **Decisiones del propietario** | §7 (solo la aceptación de este informe; las decisiones de cierre siguen PENDIENTES) |
| **Limitaciones de la evidencia** | §8 |

Referencias de partida (no modificadas): `IMPL-3_CR-020_reverificacion_consolidada.md` y `IMPL-3_CR-020_reverificacion_sondas/` (`67195da`), `IMPL-3_N-1_correccion.md` (`f8e8861`), `IMPL-3_N-2_disposicion.md` (`06d55aa`), `IMPL-3_N-3_disposicion.md` (`95ae440`), conciliación documental (`eac0fa7`).

Alcance: reverificación focalizada; **no** repite la auditoría consolidada completa de CR-020. Solo recursos locales y registros sintéticos temporales; sin servicios externos, datos reales de mercado, credenciales, OOS ni LOCKBOX. Sin modificar archivos del repositorio durante la auditoría; sin sub-agentes; sin commit.

## 1. Veredictos individuales

| Elemento | Veredicto | Evidencia independiente |
|---|---|---|
| **N-1** | **Conforme (corregido y verificado)** | `_deviation_output_error` (`src/swingpilot/research/experiments.py:890`) se invoca en `begin_configuration_evaluation` dentro del bloqueo exclusivo existente, solo en la ruta del constructor y antes de `_write_lines`. Equivale a lo que `_replay` exige a una DEVIATION nueva (forma vía `_deviation_shape_error`; `informed_by` presente, R2; SHA-256 de PREREGISTERED; `informed_by_error` sobre los registros actuales, equivalente a `records[:i]` para una línea añadida al final; cronología `after_oos` con `_registry_exposure`) y añade las precondiciones de vinculación del marcador (`experiment_id`, `field` = `trials_count`), `deviation_id` no repetido y serialización. Orden de escritura, `fsync`, marcador y ruta de reintento sin cambios |
| **N-2** | **Disposición conforme** | No existe requisito vinculante de bloqueo de lectura; CR-021 P1 define la cola sin salto de línea como corrupción en toda lectura, por lo que la denegación transitoria Fail-Closed es conforme. Distingue denegación transitoria (disponibilidad) de corrupción persistente; no añade cifras nuevas (remite al informe preservado); registra la condición P5 (confirmar bajo bloqueo exclusivo o con escritores en reposo, conservar evidencia, autorización del propietario por operación, ningún error transitorio único desencadena recuperación). Comprobado en el código: `transition`, `begin_configuration_evaluation` y `claim_partition` leen bajo `_locked()` |
| **N-3** | **Disposición conforme** | Acotada a la reescritura destructiva externa fuera del protocolo append-only (I4, P1–P3); distingue la evidencia obsoleta en un instante (operación legítima) de la vista mixta ELIGIBLE reproducida; conserva la excepción acotada a la afirmación «ninguna ruta del evaluador usa registros no validados», la ausencia de tamper-evidence criptográfico, las obligaciones de P5 y de HUMAN_REVIEW («ELIGIBLE_FOR_HUMAN_REVIEW no es una aprobación»). No afirma garantías más fuertes. Comprobado: las únicas sustituciones/renombrados de `src/` están en `snapshot.py` |
| **D-1** | Conforme | «QA-CR020-O3, sin resolver» conservado como histórico y anotado con la aceptación del propietario (2026-11-24) |
| **D-2** | Conforme | Nota nueva de CONF-010 añadida; la nota anterior se conserva; CONF-010 sigue OPEN |
| **D-3** | Conforme | `evidence.pending` de FEAT-017 cubre QA-CR020-01..06, O3, O4 y N-1..N-3, con un elemento separado de obligaciones; la aceptación de QA-CR020-06 está respaldada en `feature_list.json` (entrada `qa_reviews`, línea 1800) |
| **D-4** | Conforme | `metadata.last_updated` = 2026-11-25 |
| **D-5** | Conforme | «`develop` = `origin/develop` en `95ae440` antes del commit» coincide con el reflog de la referencia remota local; las menciones «sin push» eran exactas al redactarse (publicación posterior por el propietario). Las entradas antiguas «1 commit por delante» se conservan como históricas y condicionales |

**Disconformidades contractuales:** ninguna.

## 2. Pruebas y evidencia independiente

| Comprobación | Resultado |
|---|---|
| Pruebas dirigidas de N-1 (`tests/unit/test_n1_deviation_prewrite_validation.py`) | **43 passed** |
| Las mismas 43 pruebas contra el código sin corregir (`67195da`, exportado con `git archive` a un directorio temporal fuera del repositorio, con el archivo de pruebas de `eac0fa7` copiado) | **30 failed, 13 passed** — reproduce la afirmación del implementador |
| Cinco sondas originales `IMPL-3_CR-020_reverificacion_sondas/p_builder.py` (sin modificar) | Los cinco casos (`experiment_id` ajeno, `field` ≠ `trials_count`, `deviation_id` ausente, SHA-256 del preregistro erróneo, `informed_by` no verificable) → `EvaluationRequestRejected`, `written=False`, registro legible, acceso denegado |
| Verificación independiente del motivo de rechazo por caso (`motivos_rechazo_n1.py`, §3) | Los 31 casos de mutación se rechazan por su **motivo previsto**, no por una comprobación genérica anterior; solo `config_id_other`, `config_id_missing` y `kind_other` caen en la comprobación preexistente, como documenta la corrección |
| Regresiones CR-020/CR-021 (`test_cr021_durability.py`, `test_qa_cr020_01.py`, `test_qa_cr020_02.py`, `test_trials_accounting.py`, `test_cr020_regressions.py`) | **130 passed** |
| Suite funcional completa (una vez; `.venv/bin/pytest -q -p no:cacheprovider -rs tests`) | **870 passed, 5 skipped** (133 s). Los 5 skips son pruebas en vivo opcionales (Anthropic ×3, Binance ×2) sin variable de activación: **no se ejecutaron y no cuentan como superadas** |
| `scripts/validate_{manifest,requirements,gates}.py` | código 0 los tres (no verifican semántica contractual) |
| `feature_list.json` | JSON válido; versión 1.21.2 |

**Valoración de las pruebas de N-1:** establecen rechazo antes de cualquier mutación (archivo idéntico byte a byte; por tanto ciclo de vida sin cambios), conteo sin cambios (`trials_count`), registro legible, ausencia de `EVALUATION_PERSISTED`, cargador denegado con `reads == []` (sin acceso a particiones), rechazo estructurado de salidas no dict y de un constructor que lanza, conservación de la vía válida (API y vía sancionada, planificada y no planificada), reintento idempotente sin invocar el constructor y recuperación con copias idénticas (protocolo de durabilidad y reintento conservado). Las pruebas solo afirman el tipo de excepción, no el motivo; esa laguna se cubrió con la verificación por caso.

## 3. Scripts del auditor preservados

Directorio `harness/verification/IMPL-3_CR-020_reverificacion_focalizada_sondas/`. Copias **byte a byte idénticas** de los scripts realmente ejecutados en esta revisión (recuperados del directorio temporal de la sesión; solo cambia el nombre del archivo):

| Archivo | Nombre original | SHA-256 | Uso |
|---|---|---|---|
| `motivos_rechazo_n1.py` | `reasons.py` | `a6481f81adfb1f793678267920cc06ec246952037cc9194b10b6311d54d291c5` | Motivo de rechazo por caso de N-1 (reutiliza en solo lectura `CASES`, `valid_record` y `call` del archivo de pruebas de N-1 y `frozen` de `test_qa_cr020_01.py`) |
| `diff_feature_list.py` | `fldiff.py` | `397b0f74d2ac8670bfcb7d8194fd7aae515cc2a1cc4713a3ff1ca8b06e465247` | Comparación estructurada de `feature_list.json` entre dos versiones |

Reproducción (desde la raíz del repositorio; `W` es un directorio temporal nuevo):

```
W=$(mktemp -d); D=harness/verification/IMPL-3_CR-020_reverificacion_focalizada_sondas
.venv/bin/python -B $D/motivos_rechazo_n1.py $W
for c in 2625ee9 67195da eac0fa7; do git show "${c}:feature_list.json" > $W/fl_${c}.json; done
python3 -I $D/diff_feature_list.py $W/fl_2625ee9.json $W/fl_eac0fa7.json
python3 -I $D/diff_feature_list.py $W/fl_67195da.json $W/fl_eac0fa7.json
# Comparación contra la base sin corregir:
mkdir $W/base && git archive 67195da | tar -x -C $W/base
cp tests/unit/test_n1_deviation_prewrite_validation.py $W/base/tests/unit/
(cd $W/base && <repo>/.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_n1_deviation_prewrite_validation.py)
```

**Salida observada de `motivos_rechazo_n1.py`** (transcrita; mensajes truncados a 110 caracteres por el propio script):

| Caso | Motivo observado |
|---|---|
| `foreign_experiment_id`, `experiment_id_missing` | experiment_id distinto del de la solicitud |
| `field_not_trials_count`, `field_unknown` | field debe ser trials_count |
| `deviation_id_missing`, `sha256_missing`, `required_key_missing` | faltan campos |
| `wrong_preregistration_sha256` | el SHA-256 del preregistro no coincide con el de PREREGISTERED |
| `informed_by_unverifiable` | informed_by no verificable: referencia inexistente o posterior |
| `deviation_id_not_hex32`, `deviation_id_none` | deviation_id no válido |
| `sha256_malformed` | SHA-256 no válido |
| `config_id_other`, `config_id_missing`, `kind_other` | el constructor no devolvió la DEVIATION de esta configuración (comprobación preexistente) |
| `justification_blank`, `justification_not_str` | sin justificación |
| `actor_blank` | sin actor |
| `authorizes_change_true` | un registro DEVIATION no autoriza cambios |
| `after_oos_not_bool` | after_oos no booleano |
| `after_oos_true_without_exposure`, `after_oos_false_with_exposure` | after_oos no coincide con la cronología del registro |
| `access_log_evidence_not_list`, `access_log_evidence_foreign` | evidencia del registro de accesos no válida |
| `informed_by_absent` | falta «informed_by» (obligatorio en las desviaciones nuevas, R2) |
| `informed_by_not_list` | informed_by no es una lista |
| `informed_by_malformed_ref` | informed_by no verificable: referencia mal formada |
| `informed_by_repeated` | informed_by no verificable: referencia repetida |
| `informed_by_unknown_provenance` | informed_by no verificable: procedencia inexistente o posterior |
| `not_serializable`, `not_serializable_nan_key` | no serializable: TypeError |

Todos con `EvaluationRequestRejected`; ningún caso aceptado.

**Salida observada de `diff_feature_list.py`** (transcrita), tanto `2625ee9 → eac0fa7` como `67195da → eac0fa7`: mismos identificadores de FEAT; sin diferencias en `status`, `acceptance_criteria`, `acceptance_criteria_status` ni `evidence.covered` de ninguna FEAT; ninguna otra FEAT modificada; en FEAT-017 solo cambian `evidence.pending`, `cr020` y `qa_reviews`; metadatos: `version` 1.21.1 → 1.21.2 y `last_updated` 2026-11-24 → 2026-11-25; ninguna otra clave de primer nivel modificada.

## 4. Integridad documental

- `git diff --numstat 67195da eac0fa7`: solo añadidos, salvo 5 líneas reemplazadas en `feature_list.json` (D-1, D-3, D-4 y versión). `implementation/conflict_register.md`: 1 línea añadida. Informes, sondas y correcciones históricos sin cambios.
- `cr020`: el único cambio es la anotación de D-1 en `regression_vs_base`; `qa_reviews`: solo se añade una entrada nueva; las anteriores quedan intactas.
- CONF-009 y CONF-010: **OPEN**. Estados de FEAT, criterios de aceptación, `acceptance_criteria_status`, `evidence.covered` y gates sin cambios.
- Registro real `research/experiments/registry.jsonl`: SHA-256 `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b` antes y después de todas las comprobaciones, igual a `HEAD` y al valor registrado.

## 5. Observaciones no bloqueantes, riesgos residuales y obligaciones

**Observaciones menores (no bloqueantes):**
- `test_duplicate_deviation_id_of_an_existing_record_is_rejected` no afirma la denegación del cargador ni la ausencia de marcador (la identidad byte a byte del archivo lo implica).
- `not_serializable_nan_key` tiene un nombre impreciso: prueba una clave de tupla, no NaN.
- Las pruebas de N-1 afirman el tipo de excepción, no el motivo (cubierto por §3).
- La salida del constructor puede incluir claves adicionales o sustituir `at_utc`; `_replay` acepta lo mismo, por lo que no es una disconformidad.
- Las entradas antiguas de `session-handoff.md` con «1 commit por delante» no se anotaron en el lugar; la corrección de D-5 se hace mediante el nuevo punto de reanudación y `progress.md`.

**Riesgos residuales aceptados (no son disconformidades):** N-2 (denegaciones Fail-Closed espurias y ruido de auditoría `allowed=False`); N-3 (integridad acotada a escritor de confianza y operación append-only; sin tamper-evidence); N-1 no retroactiva; la observación separada de `_marker_error` sigue abierta (ya no alcanzable mediante esta API).

**Limitaciones y obligaciones que deben sobrevivir a cualquier cierre:**
- O3: verificación de la contabilidad de escenarios de coste antes de habilitar el pipeline de evaluación de investigación.
- O4: verificación de modificaciones sustantivas bajo un `config_id` existente antes de habilitar el pipeline.
- Supuestos de despliegue S1–S4 (G6, Laptop B); S4 (éxito falso de `fsync`) no verificable aquí.
- P5 (conciliación manual) PENDING, con las condiciones de `IMPL-3_N-2_disposicion.md` §3 y `IMPL-3_N-3_disposicion.md` §4; ninguna reescritura, sustitución ni truncamiento externos del registro.
- `confirmatory_status(..., selection_inputs=…)` consistente obligatorio antes de aprobar en HUMAN_REVIEW.
- N-3 como excepción acotada a toda afirmación general de que todas las rutas del evaluador fallan cerrando; sin tamper-evidence.
- N-2: denegaciones espurias posibles; evidencia solo en ext4.
- N-1 no retroactiva; observación de `_marker_error` abierta.
- FEAT-017 sigue IN_PROGRESS (AC-017-10 y AC-017-11 pendientes).

## 6. Recomendaciones del auditor (no son decisiones)

- **Ocho hallazgos originales (QA-CR020-01..06, O3, O4):** elegibles para cierre formal por el propietario, trasladando las limitaciones y obligaciones de §5.
- **CONF-009:** técnicamente elegible para cierre (sin defecto en la procedencia ni en el registro real); la reevaluación obligatoria antes del cierre de FEAT-017 sigue vigente.
- **CONF-010:** el mecanismo de contabilidad es conforme con v1.10; el cierre depende de que el propietario decida si las obligaciones previas al pipeline de O3 y O4 son condición de cierre. Recomendación: mantener OPEN, o cerrar solo si esas obligaciones se trasladan a un control trazable de la habilitación del pipeline de evaluación.
- **D2:** elegible para cierre formal por el propietario como «verificada con observaciones»; se cumplen las precondiciones de §6 del informe consolidado (N-1 corregido, N-2 decidido, D-1..D-5 tratados).

## 7. Decisiones del propietario

- **Tomada (2026-11-25):** aceptación de este informe como evidencia para decisiones de cierre posteriores; autorización de preservación solo documental.
- **PENDIENTES:** cierre formal de los ocho hallazgos de CR-020, de N-1..N-3 y D-1..D-5, de CONF-009, CONF-010, D2 y FEAT-017. Este informe no aprueba ningún cierre en nombre del propietario.

## 8. Limitaciones de la evidencia

- Las salidas de pruebas, sondas y scripts se observaron en terminal y se **transcriben** aquí; **no se conservaron como archivos de salida en bruto**. Se reproducen con §3.
- La comparación contra la base sin corregir se hizo con comandos de shell (no un script); los comandos se documentan en §3.
- Los dos scripts preservados son los originales ejecutados (copias byte a byte, renombradas); no se reconstruyó evidencia. La primera ejecución de la comparación estructurada falló por la expansión de `$c:f` en zsh y se repitió con `${c}`; solo cuenta la segunda.
- Las disposiciones de N-2 y N-3 se revisaron sobre la evidencia preservada y la inspección de código; no se repitieron los experimentos probabilísticos de concurrencia ni de reescritura.
- Verificado solo en ext4 local, Linux (kernel 7.0.0-44), con el `.venv` del repositorio.

## 9. Estado

Sin cambios en código funcional, pruebas, contrato v1.10, `feature_list.json` v1.21.2, estados de FEAT y de conflictos, gates, informes y sondas históricos ni en el registro real (SHA-256 `07efad20…`). D2 pendiente de cierre. Sub-agentes: 0.
