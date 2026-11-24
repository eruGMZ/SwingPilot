# IMPL-3 — Pruebas de caracterización de CR-022 §F (QA-CR020-04; contrato v1.10)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (caracterización; no es una QA independiente).
**Autorización del propietario (2026-11-24):** implementar y ejecutar las cuatro pruebas de caracterización aprobadas en CR-022 §F bajo DEC-024 y el contrato v1.10, para verificar QA-CR020-04 frente a la semántica aclarada. Solo registros temporales sintéticos; sin modificar código funcional ni pruebas existentes; si alguna falla, detenerse e informar. Sin commit ni push.
**Base:** `4fbeecb8e21bbe502cfd5f0166a2055e6478f6a3` (`develop` = `origin/develop`, árbol limpio; sincronización confirmada por el propietario).
**Hallazgo de origen:** QA-CR020-04 (`harness/verification/IMPL-3_CR-020_QA_independiente.md` §3; sonda P5 de `IMPL-3_CR-020_QA_sondas.py`). Ambos se conservan sin cambios.
**Estado:** EVIDENCIA ACEPTADA POR EL PROPIETARIO (2026-11-24, §6). QA-CR020-04 VERIFICADO POR EL IMPLEMENTADOR Y ACEPTADO POR EL PROPIETARIO — PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE. CONF-011 RESOLVED. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## 1. Trazabilidad contractual

| Prueba | CR-022 | Cláusula del contrato v1.10 |
|---|---|---|
| F.1 | §C.1 (cita por par exacto; clasificación por separado), §C.2 casos 1 y 2, §F.1 | REQ-G-P17 (frase CR-022); TC-ML-024 (entrada «varias configuraciones posteriores del mismo experimento de las que se cita solo una»; resultado «NO RELEVANTE tras una selección reproducible») |
| F.2 | §C.2 caso 3 y precedencia, §F.2 | REQ-G-P17 («si su influencia no puede determinarse, dan INCONCLUSIVE»); TC-ML-024 («INDETERMINADA → INCONCLUSIVE si una desviación posterior no la cita») |
| F.3 | §C.1 y §C.3 (semántica de `provenance_id` sin cambios), §F.3 | TC-ML-024 («una referencia `provenance_id` no cita ninguna prueba posterior») |
| F.4 | §C.3 (deduplicación por par), §F.4 | TC-ML-024 («cada par relevante suma una vez»); CR-020 §C.4.2 caso 2 (`N_eval = N_pre + │pares relevantes│`) |

## 2. Pruebas (`tests/unit/test_trials_accounting.py`, añadidas tras el bloque TC-ML-024)

Preparación común (`_x_and_two_later_y_configs`): X = EXP-0101 se congela con `A` planificada y la evalúa; después Y = EXP-0102 se congela y evalúa `YA` y `YB`, que son dos pruebas posteriores a la congelación de X. Cada prueba recorre el evaluador completo (`acceptance.evaluate`) sobre un registro temporal con decisiones sintéticas.

| Prueba | Aserciones |
|---|---|
| `test_cr022_f1_exact_reference_to_sibling_does_not_make_pair_relevant` | La selección cita solo `YB` → ELIGIBLE_FOR_HUMAN_REVIEW; `trials_after_freeze` = [`YA`, `YB`]; `relevant` = [`YB`]; `YA` no relevante y `undetermined` vacío; `N_eval` = `N_pre` + 1; `trials_count` del DSR = `N_eval` |
| `test_cr022_f2_later_deviation_not_citing_sibling_leaves_it_undetermined` | Una DEVIATION posterior a `YA` y `YB` cita solo `YB` (la selección también) → INCONCLUSIVE con `SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`; `undetermined` = [`YA`]; `YB` no indeterminada; `N_eval` y `trials_count` = `None` |
| `test_cr022_f3_provenance_reference_does_not_cite_any_later_native_pair` | Con procedencia histórica registrada, la selección cita un `provenance_id` válido (aceptado y registrado tal cual) → ELIGIBLE; `trials_after_freeze` = [`YA`, `YB`]; `relevant` y `undetermined` vacíos; `N_eval` = `N_pre` = `trials_count` |
| `test_cr022_f4_pair_cited_by_two_decision_points_counts_once` | Una DEVIATION cita `YA` y `YB` y la selección vuelve a citar `YB` → ELIGIBLE; `relevant` = [`YA`, `YB`]; `N_eval` = `N_pre` + 2 (`YB` cuenta una vez, no dos); `trials_count` = `N_eval` |

## 3. Resultados

- **Caracterización:** `.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_trials_accounting.py -k cr022` → **4 passed**. Ninguna discrepancia: el comportamiento vigente cumple CR-022, como anticipaba su §E.
- **Suite:** `.venv/bin/pytest -q -p no:cacheprovider tests` → **826 passed, 5 skipped** (822 + 4).
- **Validadores:** `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- **Registro real:** sin cambios (SHA-256 `07efad20…`).

**Capacidad de discriminación (mutantes, solo en copias temporales de `src`; el código del repositorio no se modificó):** si se cambia `trials.py` para violar cada propiedad, las pruebas lo detectan.

| Mutante | Cambio | Resultado |
|---|---|---|
| Atribución a nivel de experimento (lectura rechazada) | Una cita de cualquier par de `Y` cita `T`, en los casos 2 y 3 | F.1 y F.2 fallan (`relevant` incluye `YA`; ELIGIBLE en lugar de INCONCLUSIVE); F.3 y F.4 pasan |
| Sin deduplicación | Un par suma una vez por cada punto de decisión que lo cita | F.4 falla; las demás pasan |
| `provenance_id` como cita | Una referencia `provenance_id` cita toda prueba posterior | F.3 falla; las demás pasan |

## 4. Limitaciones residuales

1. **Caracterización, no regresión:** las pruebas pasan con la base, porque el comportamiento ya era conforme. Su valor es fijar la semántica aclarada; la tabla de mutantes muestra que la protegen.
2. **Una sola configuración de la familia citada:** las pruebas usan un experimento posterior con dos configuraciones y uno o dos puntos de decisión. La regla es por par, sin dependencia del tamaño del experimento, pero no se ha probado un experimento posterior grande.
3. **Decisiones no registradas:** si quien decide consultó configuraciones que no cita, quedan NO RELEVANTES tras una selección reproducible. Es el riesgo residual ya aceptado (ORQ-017-01; CR-020 §C.4.2; CR-022 §H.1) y no se amplía.
4. **Sin verificación independiente:** esta evidencia la produce el Orquestador de Desarrollo; su revisión corresponde al propietario.

## 5. Archivos

Modificado: `tests/unit/test_trials_accounting.py` (solo se añaden 4 pruebas, un auxiliar y dos constantes; ninguna prueba existente cambia). Nuevo: este documento. Actualizados: `progress.md`, `session-handoff.md`. Sin cambios en código funcional, contrato v1.10, CR-020, CR-022, DEC-024, `implementation/conflict_register.md` (CONF-011 sigue OPEN), registro real, informe y sondas de la QA original, `feature_list.json`, estados de FEAT ni gates. Sin commit ni push. Sub-agentes: 0.

## 6. Aceptación del propietario (2026-11-24)

El propietario aprueba la evidencia de caracterización de CR-022 bajo DEC-024 y el contrato v1.10, y acepta:

- las cuatro pruebas de caracterización y su trazabilidad contractual (§1, §2);
- la evidencia de mutantes, que demuestra que cada prueba detecta la violación de su regla (§3);
- el resultado de la suite (826 passed, 5 skipped) y los tres validadores OK;
- las limitaciones residuales de §4;
- la conclusión de que no se requiere ningún cambio de código funcional.

**Estado:** QA-CR020-04 VERIFICADO POR EL IMPLEMENTADOR Y ACEPTADO POR EL PROPIETARIO; PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE. **CONF-011: RESOLVED** (`implementation/conflict_register.md`), con cita de CR-022, DEC-024 y esta evidencia; se conservan sus entradas históricas.

**Obligaciones de la reverificación independiente:**
1. Coincidencia por par exacto: solo la referencia exacta del par cita una prueba posterior; otro par del mismo experimento no la cita.
2. Precedencia del caso 3: cualquier condición del caso 3 prevalece sobre una cita (caso 2) y da INCONCLUSIVE.
3. Separación de `provenance_id`: una referencia `provenance_id` nunca cita una prueba posterior nativa.
4. Deduplicación por par: un par relevante suma una sola vez en `N_eval`, con independencia del número de puntos de decisión que lo citen.

**Commit autorizado:** los cuatro archivos de §5 más la actualización de `implementation/conflict_register.md`, con el mensaje «test(impl-3): characterize CR-022 exact-pair relevance and resolve CONF-011», sin push; pruebas no reejecutadas para el commit. Sin cambios en contrato, código funcional, aserciones de pruebas existentes, registro real, evidencia de QA original, sondas ni `feature_list.json`. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
