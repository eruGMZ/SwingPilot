# DEC-024 — Aprobación de CR-022 (la relevancia de las pruebas posteriores se acredita solo con la cita del par exacto)

**Fecha:** 2026-11-24
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-24: aprobación expresa de CR-022 y de su redacción, y decisiones sobre CR-022 §I. Antes: evaluación de solo lectura de QA-CR020-04 (sonda P5 reproducida sobre `d84535a`); elección de la opción A (par exacto), rechazo de la atribución implícita a nivel de experimento y autorización de la preparación de CR-022.
**Alcance:** aprueba `harness/change_requests/CR-022_relevancia-por-par-exacto.md` y autoriza **solo su aplicación contractual y documental**: contrato v1.9 → **v1.10** con las enmiendas mínimas de CR-022 §D. **No autoriza** cambiar código funcional ni pruebas ejecutables, implementar o ejecutar las pruebas de caracterización, modificar `feature_list.json`, el registro real, la evidencia de QA original, las sondas, los estados de FEAT ni los gates, ni hacer commit o push. Cada uno requiere una autorización posterior y expresa.
**Relación con CR-020 / DEC-021:** CR-022 **aclara** CR-020 §C.4.2 (casos 1, 2 y 3) sin sustituir ninguna otra obligación. CR-020 y DEC-021 se conservan como evidencia aprobada; la aclaración consta en la nota de vigencia §J de CR-020. CR-021 y DEC-023 no cambian.
**Conflicto:** CONF-011.

## Decisión

| N.º | Elemento | Decisión |
|---|---|---|
| 1 | Regla de cita por par exacto (CR-022 §C.1) | Un punto de decisión cita una prueba posterior solo si su `informed_by` contiene exactamente la referencia de su par. Ni otro par del mismo experimento ni una referencia `provenance_id` la citan. Aprobado |
| 2 | Clasificación por separado (§C.1, §C.2) | Cada prueba posterior se clasifica con sus propias citas; citar una configuración no hace relevante a ninguna otra, tampoco del mismo experimento. Aprobado |
| 3 | Precedencia del caso 3 (§C.2) | Cualquier condición del caso 3 prevalece sobre el caso 2; una sola INDETERMINADA da INCONCLUSIVE. Aprobado |
| 4 | Atribución implícita a nivel de experimento (§B, §G) | Rechazada: aumentar `N_eval` no sustituye a la evidencia de influencia, y eliminar un INCONCLUSIVE por inferencia no es aceptable con la política Fail-Closed |
| 5 | Referencias explícitas a experimentos (§G) | Diferidas hasta que un requisito operativo justifique ampliar la gramática de `informed_by` |
| 6 | Aplicación (§D) | Contrato v1.10: REQ-G-P17, TC-ML-024, cabeceras de versión; nota de vigencia §J en CR-020. Autorizada |
| 7 | Pruebas de caracterización (§F, 1–4) | Aprobadas en alcance; implementación y ejecución diferidas a una autorización separada, posterior a la congelación del punto de control contractual |
| 8 | Severidad de CONF-011 | LOW, confirmada |

**Se conservan:** la gramática de `informed_by` (pares y `provenance_id`), la semántica de `provenance_id`, `N_pre`, `N_eval` = `N_pre` + │pares relevantes│ con deduplicación por par, el carácter confirmatorio (REQ-G-103; QA-CR020-02), el cálculo estadístico de aceptación (Deflated Sharpe con `N_eval`) y los resultados de P5 y de su variante con DEVIATION.

## Efectos

- **Contrato v1.10:** REQ-G-P17 ampliado con una frase; TC-ML-024 con entradas y resultado esperado nuevos; versión v1.10 en los cinco documentos de `implementation/`.
- **Implementación:** la actual ya cumple todas las obligaciones de CR-022 (§E); no se requiere cambio de código.
- **CONF-011:** OPEN hasta que se produzca y revise la evidencia de caracterización.
- **QA-CR020-04:** pendiente de verificación.
- **CONF-009 y CONF-010:** OPEN. **FEAT-015:** DONE. **FEAT-017:** IN_PROGRESS.
- **Riesgo y ejecución:** ninguno. Solo investigación, sin órdenes (REQ-G-081).
- **Siguen vigentes** las restricciones de DEC-017 y DEC-018. El commit y el push requieren la indicación del propietario.

## Aceptación de la aplicación (propietario, 2026-11-24)

El propietario acepta la aplicación de CR-022 bajo esta decisión y el contrato de requisitos v1.10, y aprueba las enmiendas documentales, la trazabilidad contractual, la conservación del texto histórico aprobado (CR-020 §I y §J) y los tres validadores en OK. Autoriza congelar el punto de control contractual con el commit de los 11 archivos documentales, sin push y sin volver a ejecutar pruebas ni validadores para el commit. CONF-011 sigue OPEN y QA-CR020-04 pendiente de la evidencia de caracterización; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS. La implementación y ejecución de las pruebas de caracterización de CR-022 §F siguen requiriendo una autorización separada.
