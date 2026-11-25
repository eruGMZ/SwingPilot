# IMPL-3 — Evaluación y disposición de QA-CR020-O4 (FEAT-017; CR-020)

**Fecha:** 2026-11-25
**Origen:** observación QA-CR020-O4 (OBS, nota) de `harness/verification/IMPL-3_CR-020_QA_independiente.md` §3 («El cargador no considera el estado del experimento»; informe y sondas conservados sin cambios).
**Base evaluada:** `3e52745` (`develop`). Evaluación de solo lectura por el Orquestador de Desarrollo; no aprueba su propio trabajo. Sin cambios en código funcional, pruebas, contrato v1.10, registro real, estados de FEAT ni de conflictos, gates. Sub-agentes: 0.
**Estado:** QA-CR020-O4 **ACEPTADO por el propietario (opción A)**; **pendiente de reverificación independiente**.
**Distinción:** no es la observación «O4» antigua (conservación versionada del archivo de resultados de la selección; `IMPL-3_CR-020_QA_independiente.md` §6 y CR-020 §C.3.3), que es otra y no se ve afectada.

## 1. Evaluación

| Aspecto | Resultado |
|---|---|
| Obligación vinculante | REQ-G-104 y CR-020 §C.3.2: el **inicio** de una evaluación solo se registra si el estado, las transiciones y las autorizaciones vigentes lo permiten («un estado no terminal no basta», DEC-021). CR-021 §D.5 (REQ-G-104/P17, v1.9): el acceso a Train+Val para un par exige la evidencia validada del par, la DEVIATION validada si no está planificada y un `EVALUATION_PERSISTED` válido. Ninguna cláusula añade una condición de estado al acceso; CR-021 §F.4 y TC-ML-023 admiten el reintento idempotente |
| Comportamiento actual | `load_train_val_for_configuration` (`partitions.py:133-157`; el informe citaba `:129-151`) no consulta el estado del experimento. El registro del inicio solo es posible en DEVELOPMENT o VALIDATION (`EVALUATION_STATES`, `experiments.py`; TC-ML-023, `test_trials_accounting.py:399`); un par registrado en esos estados conserva el acceso tras avanzar el experimento. La vía OOS/LOCKBOX sí exige `OOS_EVALUATION` |
| Recuperación de evidencia frente a evaluación nueva | En la API de registro sí (`accounting()`, `records()`, `certified()`, `evaluation_recorded()`, `trials_count()` no leen datos); en el cargador no: toda llamada entrega Train+Val y se anota como «evaluación de la configuración» |
| Clasificación | No es una violación contractual; riesgo residual metodológico aceptable; limitación de evidencia estrecha (ninguna prueba caracteriza el cargador con el experimento posterior a VALIDATION) |

## 2. Evidencia

Solo inspección de código y de la documentación contractual (`partitions.py`, `experiments.py`, `requirements.md` REQ-G-104, `test_plan.md` TC-ML-023, CR-020 §C.3.2, CR-021 §D.5/§F.4) y búsqueda en las pruebas existentes. **No se ejecutó ninguna prueba nueva** ni se reejecutó la suite.

## 3. Aceptación del propietario (2026-11-25, opción A)

Acepta el comportamiento actual como riesgo residual metodológico, sin cambios funcionales, de pruebas ni contractuales. Registra:
- El registro de la evaluación sigue sujeto a las puertas contractuales de ciclo de vida y autorización.
- La recuperación de Train+Val de un par ya certificado no está sujeta a una puerta de estado adicional.
- La recuperación repetida no incrementa el conteo de configuraciones (conteo por par, deduplicado).
- El cargador no distingue la recuperación de evidencia de una reevaluación repetida.
- No se garantiza detectar cambios sustantivos de configuración bajo un `config_id` existente.
- La evaluación se basa en inspección de código, no en pruebas ejecutadas de nuevo.

**Obligación operativa abierta (no autoriza implementación):** antes de habilitar el pipeline de evaluación de investigación, verificar que las configuraciones sustantivamente modificadas no puedan tratarse como repeticiones idénticas para eludir la contabilidad.

**QA-CR020-O4: ACEPTADO por el propietario; pendiente de reverificación independiente.**

## 4. Limitaciones residuales

- Reevaluación posterior al avance del experimento sobre un par ya contado: no impedida ni distinguida por el cargador.
- Cambio sustantivo bajo el mismo `config_id`: no detectable por diseño (se suma a «decisiones fuera del registro no detectables», `IMPL-3_CR-020_implementacion.md` §7).
- Sin prueba de caracterización del cargador fuera de DEVELOPMENT/VALIDATION.

## 5. Obligación de reverificación independiente (QA-CR020-O4)

Comprobar que el registro es fiel a esta evaluación y a las fuentes citadas; que la obligación operativa consta como abierta antes de habilitar el pipeline y no como implementada; que no se presenta evidencia ejecutada donde solo hubo inspección de código; y que no se confunde con la O4 antigua.
