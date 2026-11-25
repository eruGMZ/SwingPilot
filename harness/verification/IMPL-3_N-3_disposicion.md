# IMPL-3 — Disposición del propietario de N-3 (vista mixta por reescritura externa; reverificación independiente de CR-020; FEAT-017)

**Fecha:** 2026-11-25
**Autor:** Orquestador de Desarrollo (registro de la disposición; no es una revisión independiente).
**Base:** `06d55aa` (`develop`). Contrato **v1.10** y `feature_list.json` **v1.21.1** sin cambios (se concilian en la reconciliación documental consolidada posterior).
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_reverificacion_consolidada.md` (N-3, OBS) y sonda `IMPL-3_CR-020_reverificacion_sondas/p_eval.py`, sección 05-c; ambos se conservan sin modificar y son la **fuente autoritativa** de la evidencia.
**Estado:** N-3 **ACEPTADO POR EL PROPIETARIO (opción A, 2026-11-25) — PENDIENTE de revisión independiente focalizada de la disposición.**

## 1. Disposición

El propietario aprueba la **opción A**: aceptar el escenario de vista mixta reproducido como **riesgo residual de integridad fuera del protocolo append-only aprobado**, sin cambios funcionales, de pruebas ni contractuales. No se introducen aislamiento de lecturas, evidencia de manipulación (tamper-evidence) ni garantías de sistema de archivos; no se implementa P5 ni se modifica el evaluador.

## 2. Registro de la evaluación (solo lectura; sin sondas ni pruebas nuevas)

Basada en la evidencia independiente preservada y en la inspección del código (`trials.py`, `acceptance.py`, `experiments.py`, `snapshot.py`); **no se ejecutó ninguna sonda, prueba ni la suite**.

- **Garantías y supuestos aplicables:** CR-021 I4 (la recuperación solo añade líneas), P1–P3 (corrupción Fail-Closed, ninguna línea ignorada, archivo original conservado sin reescribir), P5 (recuperación futura solo con procedimiento aprobado y autorización humana), supuestos de despliegue S1–S4 y operación con escritor de confianza.
- **Evidencia preservada:** el informe consolidado demuestra un resultado ELIGIBLE_FOR_HUMAN_REVIEW sobre una **vista mixta** cuando el archivo del registro se **reescribe destructivamente desde fuera del protocolo** (sustitución completa por una versión sin una DEVIATION mal formada) entre dos lecturas de `evaluate()`: `reconcile()` usa la primera lectura para los pasos 1, 3 y 4 y el paso 2 relee el archivo. Las inyecciones por añadido (05-b) dan siempre INCONCLUSIVE. El escenario exige dos acciones fuera del protocolo (inyección de la línea inválida y su retirada en la ventana).
- **Operaciones autorizadas:** en las rutas evaluadas no se identificó un veredicto favorable incorrecto equivalente mediante operaciones append-only autorizadas. Las escrituras de `ExperimentRegistry` solo añaden bajo el bloqueo exclusivo; las únicas sustituciones/renombrados de `src/` (`snapshot.py`) afectan al manifiesto y al directorio de datos, no al registro.
- **Escrituras por añadido concurrentes:** pueden producir evidencia **obsoleta en un instante** (vista anterior a una línea añadida después). Esa evidencia **no debe caracterizarse como garantía de elegibilidad vigente**: un veredicto describe el estado leído, no el estado actual del registro.
- **N-1 y N-2:** no cambian de forma material el escenario reproducido de N-3. N-1 valida solo antes de añadir y bajo el bloqueo del escritor, y no añade lecturas del evaluador ni reescrituras; N-2 es una denegación transitoria Fail-Closed (disponibilidad) distinta de la vista mixta ELIGIBLE de N-3 (integridad, solo con reescritura externa). Ambas permanecen separadas en el registro.
- **Sin evidencia de manipulación criptográfica:** el registro no ofrece tamper-evidence criptográfico (sus comprobaciones son «un control en proceso, no criptográfico»); la protección frente a modificación externa descansa en los supuestos de despliegue y en controles del sistema de archivos que no se autorizan ni implementan aquí. Un bloqueo de lectura consultivo (`flock`) no obliga a un actor externo.
- **Solicitud de cambio:** **no se requiere CR** dentro del alcance contractual vigente; las garantías ya se limitan a operación append-only.

## 3. Excepción acotada

**N-3 se conserva como excepción acotada a cualquier afirmación general** de que todas las rutas del evaluador fallan cerrando o usan únicamente registros validados (matiza la afirmación «ninguna ruta del evaluador usa registros no validados» de QA-CR020-05). La excepción solo opera con una reescritura, sustitución o truncamiento destructivo externo del archivo entre lecturas del evaluador.

## 4. Condiciones operativas

1. **No se permite** la reescritura, sustitución ni truncamiento externos del registro.
2. Una **modificación externa sospechada** impide confiar en resultados favorables del evaluador hasta reconciliar la integridad.
3. **Conservar el registro afectado como evidencia** y aplicar los requisitos de autorización de P5 (autorización explícita del propietario por operación; confirmación consistente de la corrupción según la condición operativa registrada en `IMPL-3_N-2_disposicion.md` §3). **P5 sigue PENDING**; esta disposición no autoriza su implementación.
4. Se **conserva la obligación de HUMAN_REVIEW** de obtener evidencia consistente de `confirmatory_status(..., selection_inputs=…)` antes de la aprobación. **ELIGIBLE_FOR_HUMAN_REVIEW no es una aprobación.**

## 5. Limitaciones residuales

Riesgo de integridad acotado a manipulación externa destructiva; ausencia de tamper-evidence criptográfico; dependencia de S1–S4 y de escritor de confianza; evidencia obsoleta en un instante posible bajo escrituras concurrentes legítimas; evaluación basada en evidencia preservada e inspección de código, sin ejecuciones nuevas. Alternativas (lectura única con instantánea, evidencia de manipulación, controles del sistema de archivos) no evaluadas ni autorizadas.

## 6. Sin cambios

Informe independiente y sondas, código funcional, pruebas, contrato v1.10, `feature_list.json` v1.21.1, estados de FEAT y de conflictos, gates, D2 (pendiente de cierre), registro real (SHA-256 `07efad20…`). No se tratan D-1..D-5, la observación separada de `_marker_error`, el cierre de conflictos ni D3–D7.

## 7. Verificación pendiente

Revisión independiente focalizada de esta disposición: fidelidad al informe preservado, registro de las condiciones operativas y de la excepción acotada, separación respecto de N-2, y ausencia de cambios funcionales o contractuales. No iniciada.
