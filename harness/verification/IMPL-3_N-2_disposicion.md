# IMPL-3 — Disposición del propietario de N-2 (lecturas sin bloqueo; reverificación independiente de CR-020; FEAT-017)

**Fecha:** 2026-11-25
**Autor:** Orquestador de Desarrollo (registro de la disposición; no es una revisión independiente).
**Base:** `f8e8861` (`develop`). Contrato **v1.10** y `feature_list.json` **v1.21.1** sin cambios (se concilian en la reconciliación documental consolidada posterior).
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_reverificacion_consolidada.md` (N-2, OBS) y sonda `IMPL-3_CR-020_reverificacion_sondas/p_concurrency.py`; ambos se conservan sin modificar y son la **fuente autoritativa** de los resultados medidos.
**Estado:** N-2 **ACEPTADO POR EL PROPIETARIO (opción A, 2026-11-25) — PENDIENTE de revisión independiente focalizada de esta disposición.**

## 1. Disposición

El propietario aprueba la **opción A**: aceptar el comportamiento actual de lectura sin `flock` como **riesgo residual de disponibilidad**, sin cambios funcionales, de pruebas ni contractuales. No se implementan bloqueos de lectura compartidos, reintentos ni procedimientos de recuperación.

## 2. Registro de la evaluación (solo lectura; sin sondas ni pruebas nuevas)

La evaluación se basa en la evidencia independiente preservada y en la inspección del código (`experiments.py`, `partitions.py`); **no se ejecutó ninguna sonda, prueba ni la suite**.

- **Sin requisito vinculante de bloqueo de lectura:** CR-020, CR-021 y el contrato v1.10 solo obligan al bloqueo exclusivo de las escrituras (QA3R2-03). CR-021 §F.2 P1 y §D.4 paso 2 definen la cola sin salto de línea como corrupción en toda lectura; no distinguen una causa transitoria de una persistente. El hallazgo no es una disconformidad, sino una limitación derivada del silencio del contrato sobre lecturas.
- **Efecto observable:** una lectura concurrente incompleta puede provocar denegaciones transitorias Fail-Closed («cola sin salto de línea»; falsa corrupción transitoria). Los resultados medidos (líneas de 5 KB y de ~150 B, número de denegaciones por llamada, con ejecuciones sin ninguna) constan **únicamente** en el informe consolidado (N-2 y la tabla de hallazgos); este documento no los reproduce ni añade cifras. La evidencia es probabilística y no determinista.
- **Sin consecuencias persistentes en las rutas evaluadas:** no se identificó mutación persistente del registro, acceso no autorizado, cambio de conteo ni transición de ciclo de vida irreversible automática. Un estado visto es siempre un prefijo válido del archivo (solo se añade) o una cola sin salto de línea que falla cerrando; una vista anticipada solo puede denegar. Las transiciones y `begin_configuration_evaluation` leen bajo el bloqueo; `load_final` revalida bajo el bloqueo en `claim_partition`; el evaluador devuelve INCONCLUSIVE sin escribir, y pasar un experimento a `INCONCLUSIVE` es una transición decidida por el propietario (`OWNER_DECIDED`), no automática.
- **Efecto persistente fuera del registro:** una denegación falsa puede dejar entradas persistentes `allowed=False` en el registro de accesos del cargador. No constituyen exposición (`_is_exposure_entry` exige `allowed=True`); son ruido de auditoría.
- **Corrección de N-1:** no cambia de forma material el comportamiento de concurrencia evaluado. Su validación se ejecuta dentro del bloqueo exclusivo del escritor y antes de cualquier escritura (solo añade lecturas bajo el bloqueo, sin ampliar la ventana de los lectores sin bloqueo); el protocolo de escritura, `fsync` y marcador no cambia.

## 3. Condición operativa obligatoria para el procedimiento futuro P5

Antes de autorizar una recuperación, **confirmar la corrupción persistente mediante una lectura consistente bajo el bloqueo exclusivo del registro o con todos los escritores en reposo**. Conservar el registro afectado como evidencia y exigir autorización explícita del propietario para cada operación de recuperación. **Un único error transitorio de lectura incompleta no debe desencadenar una recuperación manual.**

**P5 sigue PENDING** (CR-021 §F.2). Esta disposición **no autoriza su implementación** ni modifica el contrato.

## 4. Limitaciones residuales conservadas

- Disponibilidad: denegaciones Fail-Closed espurias y ocasionales; pueden aparecer entradas `allowed=False` sin exposición real.
- Riesgo operativo: tratar un único error de «cola sin salto de línea» como corrupción persistente (mitigado por la condición de §3).
- Entorno: la evidencia procede de ext4, kernel 7.0.0-44, Python 3.14.4; la visibilidad de una escritura en curso para lectores sin bloqueo depende del sistema de archivos local y de la semántica POSIX (supuestos S1–S4 del despliegue).
- La evaluación se funda en la evidencia preservada y la inspección de código, no en ejecuciones nuevas.
- Alternativas funcionales (bloqueo de lectura compartido, reintentos de lectura) no evaluadas ni autorizadas.

## 5. Sin cambios

Informe independiente y sondas, código funcional, pruebas, contrato v1.10, `feature_list.json` v1.21.1, estados de FEAT y de conflictos, gates, D2 (pendiente de cierre), registro real (SHA-256 `07efad20…`). No se tratan N-3, D-1..D-5, la observación separada de `_marker_error`, el cierre de conflictos ni D3–D7.

## 6. Verificación pendiente

Revisión independiente focalizada de esta disposición: fidelidad al informe preservado (sin cifras nuevas), registro de la condición P5, y ausencia de cambios funcionales o contractuales. No iniciada.
