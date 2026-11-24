# CR-022 — Aclaración: la relevancia de las pruebas posteriores se establece por el par exacto (CR-020 §C.4.2)

**Fecha:** 2026-11-24
**Estado:** **APROBADA** por el propietario el 2026-11-24 (**DEC-024**) y APLICADA al contrato **v1.10** (REQ-G-P17, TC-ML-024, cabeceras de versión; nota de vigencia §J en CR-020). Las pruebas de caracterización de §F están aprobadas en alcance; su implementación y ejecución quedan diferidas a una autorización separada (§J). Antes: PROPUESTA (2026-11-24).
**Origen:** QA-CR020-04 (`harness/verification/IMPL-3_CR-020_QA_independiente.md` §3, sonda P5 de `harness/verification/IMPL-3_CR-020_QA_sondas.py`) y la evaluación de solo lectura del 2026-11-24 sobre `d84535a`.
**Conflicto:** CONF-011 (`implementation/conflict_register.md`), OPEN.
**Vinculada a:** CR-020 (DEC-021; contrato v1.8) y contrato v1.9 (CR-021, DEC-023). Aclara CR-020 §C.4.2 (casos 1, 2 y 3), REQ-G-P17 y TC-ML-024. CR-020 se conserva sin cambios como evidencia aprobada.
**Alcance:** solo el significado de «citar» una prueba posterior `T` en la clasificación de C.4.2. No toca la gramática de `informed_by`, `N_pre`, la deduplicación, el carácter confirmatorio, el cálculo estadístico, CR-021 ni QA-CR020-01, 02, 03, 05, 06, O3 y O4.
**Estado de los conflictos y funcionalidades:** QA-CR020-04 pendiente de verificación; CONF-009, CONF-010 y CONF-011 OPEN (CONF-011 hasta que se produzca y revise la evidencia de caracterización); FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## A. Problema

1. **Texto aprobado (CR-020 §C.4.2, caso 2):** una prueba posterior `T` es RELEVANTE si «algún punto de decisión de X posterior a `T` cita en `informed_by` **el experimento o el par** de `T`». Los casos 1 y 3 dicen solo «cita `T`».
2. **Definiciones aprobadas en la misma sección:** `T` es un único registro `CONFIGURATION_EVALUATED` de otro experimento `Y ≠ X` (un par). `informed_by` (R2) es «la lista de pares (`experiment_id`, `config_id`) o de `provenance_id` cuyos resultados se consultaron». La gramática no tiene ninguna referencia a un experimento, y `experiments.py` (`informed_by_error`) la aplica así.
3. **Ambigüedad:** el caso 2 nombra una cita a nivel de experimento que la gramática no puede expresar. Caben dos lecturas: (P) solo cuenta la cita del par exacto, y «el experimento» queda sin efecto; (E) citar cualquier par de `Y` equivale a citar `Y`, así que todas las pruebas posteriores de `Y` serían relevantes. REQ-G-P17, TC-ML-024 y DEC-021 no lo resuelven.
4. **Comportamiento implementado** (`src/swingpilot/research/trials.py:128-145`): lectura P. Sonda P5: la selección cita `(EXP-0102, YB)`; `(EXP-0102, YA)` es NO RELEVANTE; `N_eval` = `N_pre` + 1. Variante (una DEVIATION posterior a ambos pares cita solo `YB`): `YA` es INDETERMINADA → INCONCLUSIVE (`SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`).

## B. Decisión del propietario (2026-11-24)

1. **Opción A (lectura P):** se conservan las referencias al par exacto.
2. **Se rechaza la atribución implícita a nivel de experimento:** citar una configuración no establece la relevancia de otras configuraciones, tampoco de las del mismo experimento.
3. **Motivo:** aumentar `N_eval` no sustituye a la evidencia de influencia. La lectura E podría eliminar un INCONCLUSIVE infiriendo relevancia (variante de A.4), lo que no es aceptable con la política Fail-Closed vigente.
4. **Referencias explícitas a un experimento:** diferidas hasta que un requisito operativo justifique ampliar la gramática.

## C. Aclaración propuesta

### C.1 Regla (sustituye la lectura de «citar `T`» en CR-020 §C.4.2, casos 1, 2 y 3)

> **Cita de una prueba posterior (CR-022).** Un punto de decisión de X cita una prueba posterior `T` = (`Y`, `c`) solo si su `informed_by` contiene exactamente la referencia de par `{"experiment_id": Y, "config_id": c}`. Ninguna otra referencia cita `T`: ni la de otro par, aunque sea del mismo experimento `Y`, ni una referencia `provenance_id`. La gramática de `informed_by` (R2) no cambia y no admite referencias a un experimento. Cada prueba posterior se clasifica por separado con sus propias citas: citar una configuración no hace relevante ni no relevante a ninguna otra, tampoco del mismo experimento.

### C.2 Casos de CR-020 §C.4.2 con la aclaración aplicada

| Caso | Texto aprobado (CR-020) | Lectura aclarada (CR-022) |
|---|---|---|
| 1 — NO RELEVANTE | Constan las cinco evidencias y ningún punto de decisión de X posterior a `T` es una desviación ni cita `T` | Sin cambio de significado; «cita `T`» = contiene la referencia exacta del par de `T` (C.1) |
| 2 — RELEVANTE | Algún punto de decisión de X posterior a `T` cita en `informed_by` **el experimento o el par** de `T` | Algún punto de decisión de X posterior a `T` cita **el par exacto** de `T` (C.1), y no se da ninguna condición del caso 3 |
| 3 — INDETERMINADA | Falta alguna de las cinco evidencias; o algún punto de decisión posterior a `T` no es reproducible y no cita `T`; o falta o está mal formado `informed_by` | Sin cambio de significado; «no cita `T`» = no contiene la referencia exacta del par de `T`. Citar otro par del mismo experimento no evita este caso |

**Precedencia (explicita lo que ya implican Fail-Closed y C.4.2):** si para una misma `T` se da cualquier condición del caso 3, `T` es INDETERMINADA aunque otro punto de decisión la cite (caso 2). Una sola INDETERMINADA da INCONCLUSIVE (`SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`).

### C.3 Lo que no cambia

- La gramática de `informed_by` (pares y `provenance_id`) y la semántica de `provenance_id`: una referencia `provenance_id` nunca cita una prueba posterior, porque `T` siempre es una evaluación nativa.
- `N_pre`, que se conserva y se informa; `N_eval` = `N_pre` + │pares relevantes│, con cada par contado una vez aunque lo citen varios puntos de decisión.
- El carácter confirmatorio (REQ-G-103; QA-CR020-02): `N_eval` no lo restaura.
- El cálculo estadístico: el Deflated Sharpe usa `N_eval`, o `N_pre` si no hay pares relevantes.
- Las cinco evidencias positivas de B.4.4, el tratamiento de `informed_by` vacío (no prueba independencia) y el de los registros DEVIATION históricos sin el campo.
- Resultados esperados: P5 → `N_eval` = `N_pre` + 1, con `YA` NO RELEVANTE; variante → `YA` INDETERMINADA y veredicto INCONCLUSIVE.

## D. Enmiendas mínimas (tras la aprobación; contrato v1.9 → v1.10)

### D.1 Contrato

| Cláusula | Texto vigente | Cambio propuesto (añadido; el resto se conserva) |
|---|---|---|
| REQ-G-P17 (`implementation/requirements.md`, Módulo 15) | «Las pruebas posteriores a la congelación se informan; si influyeron en la selección se suman al conteo de evaluación sin alterar el congelado; …» | Añadir tras esa frase: «**CR-022:** la influencia se acredita solo con la referencia exacta del par evaluado en `informed_by`; citar una configuración no hace relevantes otras configuraciones, tampoco del mismo experimento, que se clasifican por separado y, si su influencia no puede determinarse, dan INCONCLUSIVE. No hay referencias a experimentos completos.» |
| TC-ML-024 (`implementation/test_plan.md`) | Input: «pruebas de otros experimentos posteriores a la congelación, con y sin puntos de decisión posteriores del experimento evaluado» | Input, añadir: «varias configuraciones posteriores del mismo experimento de las que se cita solo una; referencias `provenance_id`». Expected, añadir: «solo cita una prueba posterior la referencia exacta de su par; una configuración no citada del mismo experimento se clasifica por separado (NO RELEVANTE tras una selección reproducible; INDETERMINADA → INCONCLUSIVE si una desviación posterior no la cita); una referencia `provenance_id` no cita ninguna prueba posterior; cada par relevante suma una vez» |
| Cabeceras de versión de los documentos de `implementation/` | v1.9 | v1.10 (CR-022, DEC-024) |

### D.2 CR-020 (nota de vigencia, sin reescribir el texto aprobado)

Añadir una sección «J. Nota de vigencia (CR-022)»: §C.4.2, casos 1, 2 y 3. «Citar `T`» significa incluir la referencia exacta de su par en `informed_by`; las palabras «el experimento o» del caso 2 no crean ninguna referencia a experimentos (CR-022 §C). Se conserva la §I (CR-021).

### D.3 Sin cambios

`feature_list.json` (AC-017-8 no repite la redacción afectada; su desactualización general es QA-CR020-06), `api_contracts.md`, `data_flow.md`, `architecture.md`, gramática y validación de `informed_by`, código funcional.

## E. Conformidad de la implementación actual (`d84535a`)

| Obligación (C.1–C.3) | Implementación | ¿Cumple? |
|---|---|---|
| Cita = referencia exacta del par | `trials.py:135-140`: `ref in p[2]` / `ref not in p[2]` comparan el diccionario `{"experiment_id", "config_id"}` completo | Sí |
| Otro par del mismo experimento no cita `T` | Misma comparación exacta | Sí (P5) |
| `provenance_id` no cita `T` | Un diccionario `{"provenance_id"}` nunca es igual a la referencia de un par | Sí (por construcción; sin prueba específica) |
| Clasificación por separado de cada `T` | Bucle por par posterior (`trials.py:129`) | Sí |
| Precedencia del caso 3 sobre el caso 2 | El orden de las ramas comprueba primero `informed_by` ausente y la DEVIATION que no cita `T` | Sí (variante) |
| Cinco evidencias antes de NO RELEVANTE | Las evidencias 1–4 se comprueban en los pasos anteriores, que devuelven INCONCLUSIVE si fallan; la evidencia 5, con `informed_by` ausente (`None`) y validado al escribir y al reproducir | Sí |
| `N_eval` = `N_pre` + │pares relevantes│, sin duplicados; `N_pre` conservado | Conjunto `relevant`; `trials.py:144` | Sí |
| Sin cambios en el carácter confirmatorio ni en el DSR | No se tocan `confirmatory_findings` ni `acceptance.py` | Sí |

**Conclusión:** la implementación actual ya cumple todas las obligaciones propuestas. No se requiere cambio de código.

## F. Pruebas (tras la aprobación; requieren autorización)

Pruebas de caracterización de TC-ML-024 en `tests/unit/test_trials_accounting.py`, que deben **pasar** con el código actual (no son regresiones):
1. P5: dos configuraciones posteriores de `Y`; la selección cita solo una → la otra es NO RELEVANTE; `N_eval` = `N_pre` + 1.
2. Variante: una DEVIATION posterior a ambas cita solo una → la otra es INDETERMINADA; veredicto INCONCLUSIVE.
3. Una referencia `provenance_id` en la selección no hace relevante ninguna prueba posterior.
4. Un par citado por dos puntos de decisión suma una sola vez.

No se adapta ninguna prueba existente. Las sondas de la QA independiente se conservan sin cambios.

## G. Alternativas consideradas

- **Lectura E (atribución implícita a nivel de experimento):** rechazada por el propietario (B.2–B.3). Aumenta `N_eval`, pero en el caso 3 convierte un INCONCLUSIVE en RELEVANTE por inferencia.
- **Referencia explícita `{"experiment_id"}`:** diferida (B.4). Cambiaría la gramática R2, `informed_by_error` y TC-ML-024, y exigiría su propia CR.
- **Conservar el texto sin aclaración:** no recomendada. El texto seguiría siendo más amplio que la implementación y el hallazgo podría reabrirse.

## H. Limitaciones residuales

1. Si quien decide consultó varias configuraciones de `Y` pero solo cita una, las demás quedan NO RELEVANTES después de una selección reproducible. Es el riesgo residual ya aceptado de las decisiones no registradas (ORQ-017-01; CR-020 §C.4.2) y no se amplía.
2. Las referencias a experimentos completos no existen mientras no se apruebe una ampliación de la gramática.

## I. Decisiones del propietario requeridas

1. Aprobar CR-022 y su redacción (C.1, C.2, D.1, D.2).
2. Autorizar su aplicación al contrato v1.10 y el documento de decisión correspondiente.
3. Autorizar, por separado, las pruebas de caracterización de §F.
4. Confirmar la severidad de CONF-011 (propuesta: LOW).

QA-CR020-04 sigue sin resolver hasta que la aclaración se apruebe y se verifique.

## J. Aprobación del propietario (2026-11-24; DEC-024)

1. **CR-022 aprobada**, incluidas la regla de cita por par exacto (§C.1), la clasificación por separado de cada prueba posterior y la precedencia explícita del caso 3 (§C.2).
2. **Aplicación autorizada como contrato v1.10**, limitada a las enmiendas mínimas de §D: REQ-G-P17 (una frase), TC-ML-024 (entradas y resultado esperado), cabeceras de versión de los cinco documentos de `implementation/` y nota de vigencia §J en CR-020. Aplicada el 2026-11-24.
3. **Pruebas de caracterización (§F, 1–4):** aprobadas en alcance. Su implementación y ejecución quedan **diferidas** a una autorización separada, posterior a la congelación del punto de control contractual.
4. **Severidad de CONF-011:** LOW, confirmada.

**Sin cambios:** gramática de `informed_by`, semántica de `provenance_id`, `N_pre`, cálculo de `N_eval`, deduplicación por par, carácter confirmatorio, cálculo estadístico de aceptación, código funcional, pruebas ejecutables, `feature_list.json`, registro real, evidencia de QA original, sondas, estados de FEAT y gates.
**Estado:** CONF-011 OPEN hasta que se produzca y revise la evidencia de caracterización. QA-CR020-04 pendiente de verificación. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
