# IMPL-3 — Implementación de CR-020 (contabilidad de pruebas y procedencia de antecedentes)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (implementación; no es una QA independiente)
**Base contractual congelada:** `d372e28` (contrato v1.8, DEC-021), aceptada por el propietario.
**Autorización:** implementación funcional de CR-020 dentro de FEAT-017 (propietario, 2026-11-24). Sin registros reales de procedencia, sin decisiones con líneas `AUTORIZA: PROCEDENCIA`, sin cambios en contrato, AC, estados de FEAT ni gates, sin commit.
**Estado:** IMPLEMENTADO — PENDIENTE DE REVISIÓN DEL PROPIETARIO. CONF-009 y CONF-010 siguen OPEN; FEAT-017 sigue IN_PROGRESS.

## 1. Cambios y trazabilidad

| Archivo | Cambio | Contrato |
|---|---|---|
| `src/swingpilot/research/experiments.py` | Tipos `ANTECEDENT_PROVENANCE` y `CONFIGURATION_EVALUATED`; `accounting()` (reproducción hasta un punto), `trials_accounting()`, `trials_count()` = H_doc + H_bound + E (Fail-Closed si falta procedencia); consulta `antecedents()` con `original_state` separado; `register_provenance()` con gramática `AUTORIZA: PROCEDENCIA` estricta; `begin_configuration_evaluation()` (validaciones previas, escritura con fsync, relectura, idempotente, DEVIATION en el mismo bloqueo si no está planificada); `transition()` valida dentro del bloqueo `trials_accounting` (PREREGISTERED) y la selección (OOS_EVALUATION); `informed_by_error()`. Estados y transiciones sin cambios. | REQ-G-P17, REQ-G-103, REQ-G-104; CR-020 §C.1–C.3; R2–R4 |
| `src/swingpilot/research/preregistration.py` | `candidate_selection_rule` obligatoria y en `DESIGN_FIELDS`; `freeze()` valida el desglose de `trials_count` y la regla (`PRIMARY`, `ARGMAX … TIEBREAK …`); `preregister()`; `begin_evaluation()`; `informed_by` obligatorio en desviaciones nuevas y verificado al reproducir; históricas sin el campo se conservan. | REQ-G-103; CR-020 §C.3.2–C.3.4; R1, R2 |
| `src/swingpilot/research/trials.py` (nuevo) | Conciliación determinista para el evaluador: reconstrucción de `N_pre`, carácter confirmatorio, configuraciones no planificadas, selección reproducible, clasificación de pruebas posteriores (NO RELEVANTE / RELEVANTE / INDETERMINADA), `N_eval`. | CR-020 §C.4; B.4.2, B.4.4 |
| `src/swingpilot/research/acceptance.py` | `evaluate(ev, registry, *, preregistration, selection_inputs)`: usa `N_pre`/`N_eval`, nunca el conteo vivo; cualquier fallo de conciliación → INCONCLUSIVE con motivo; métricas del desglose (la cota se etiqueta como cota). | REQ-G-P17; CR-020 §C.4–C.5; TC-ML-006 |
| `src/swingpilot/research/partitions.py` | `load_train_val_for_configuration()`: solo entrega Train+Val si el par consta en el registro. | CR-020 §C.3.2 |
| `research/README.md` | Semántica de los tipos nuevos y de la contabilidad. | CR-020 §D |

## 2. Pruebas

| Caso | Pruebas (`tests/unit/`) |
|---|---|
| TC-ML-006 (actualizada) | `test_trials_accounting.py::test_tc_ml_006_*` (3): conteo conciliado (9 = 8 históricas + 1 planificada) → ELIGIBLE; cota grande (61) → REJECTED por Deflated Sharpe; INCONCLUSIVE no cambia el estado. Umbrales en `test_research.py` vía `_evaluate_with_trials`. |
| TC-ML-020 | 7 pruebas: ideas no cuentan; conteo histórico 8 (4 + 4 de cota); rechazadas y abandonadas cuentan, reruns no; escenario de costes que selecciona es configuración propia; planificada y evaluada cuenta una vez; par previo a la congelación no se duplica; repetición nativa de configuración de antecedente = par nuevo. |
| TC-ML-021 | 19 pruebas: vista consolidada; reducción con decisión y evidencia, prospectiva, con historial; `supersedes` incoherente → indeterminado; primera procedencia y cota; 14 rechazos de gramática y evidencia; identificador, antecedente inexistente, decisión ilegible y enlace simbólico. |
| TC-ML-022 | 20 pruebas: 6 `trials_count` mal formados; 10 reglas mal formadas; congelación rechazada si el registro cambió; evaluador usa `N_pre` (10) y no el vivo (9); `trials_accounting` alterado → INCONCLUSIVE; selección fuera de la regla → INCONCLUSIVE; empate ARGMAX por TIEBREAK. |
| TC-ML-023 | 16 pruebas + 1 en `test_snapshot.py`: rechazo en IDEA, DESIGN, PREREGISTERED, DATA_VALIDATION, OOS_EVALUATION y terminal; 6 solicitudes inválidas sin escritura; registro ilegible; fsync incierto (cuenta, no empieza, reintento idempotente); fallo antes de escribir (no cuenta); no planificada (DEVIATION, cuenta, INCONCLUSIVE); cargador con snapshot sintética real. |
| TC-ML-024 | 12 pruebas: NO RELEVANTE, RELEVANTE (`N_eval` = 2, `N_pre` = 1), `informed_by` vacío → INDETERMINADA, DEVIATION histórica sin el campo, referencias no verificables rechazadas al escribir, 3 casos de evidencia de selección insuficiente, selección ausente, `N_eval` mayor no restaura el carácter confirmatorio, registro ilegible. |
| Regresiones sobre la base | `test_cr020_regressions.py` (4), solo con interfaces existentes en `d372e28`. |

**Adaptación de pruebas existentes (solo preparación o interfaz):** helpers de `test_research.py`, `test_snapshot.py`, `test_ml_registry.py` y `test_engines.py` añaden `trials_accounting`, el inicio de evaluación y la evidencia de selección; `informed_by=[]` en 35 llamadas a `record_deviation`; las pruebas de umbrales usan `_evaluate_with_trials`. Dos aserciones cambian porque el contrato cambió la unidad: `test_tc_ml_010_…` y `test_repository_registry_…` esperaban 4 y ≥ 2 «experimentos»; ahora esperan conteo indeterminado (`TrialsAccountingError`) con antecedentes sin procedencia. Las demás aserciones de esas pruebas se conservan.

## 3. Evidencia de regresión frente a `d372e28`

Fuente de la base extraída con `git archive d372e28 src` en el directorio temporal de la sesión; mismas pruebas.

| Conjunto | Resultado con la base | Clasificación |
|---|---|---|
| `test_cr020_regressions.py` | 4 failed: `assert 2 == 0` (ideas contadas), 3 × «DID NOT RAISE» (antecedente sin procedencia contado; congelación sin desglose aceptada; preregistro con conteo escalar y sin regla aceptado) | **Regresiones de comportamiento genuinas** |
| `test_trials_accounting.py` | error de colección: `ImportError` (`EvaluationRequestRejected`) | Interfaz nueva |
| `test_research.py` (adaptado) | error de colección: `ImportError` (`TrialsAccountingError`) | Interfaz nueva |
| `test_snapshot.py`, `test_ml_registry.py`, `test_engines.py` (adaptados) | 34 failed, 133 passed: 33 × `AttributeError` (`trials_accounting`); 1 `AssertionError` por la ausencia de `docs/decisions` en la copia temporal | Interfaz nueva / artefacto del entorno de la copia |

Con la implementación: las 4 regresiones pasan.

## 4. Suite y validadores

- `.venv/bin/pytest -q -p no:cacheprovider tests` → **771 passed, 5 skipped** (antes 689 + 82 nuevas).
- `python3 scripts/validate_manifest.py`, `validate_requirements.py`, `validate_gates.py` → OK (código 0). No verifican la corrección semántica del contrato.
- `research/experiments/registry.jsonl` sin cambios (`git diff` vacío). Sin decisiones nuevas en `docs/decisions`.

## 5. Ambigüedades contractuales (no reinterpretadas; implementación Fail-Closed)

1. **Estados que permiten evaluar.** REQ-G-104 v1.8 exige que el estado, las transiciones y las autorizaciones vigentes permitan la evaluación, pero el contrato no enumera esos estados. La implementación solo admite DEVELOPMENT y VALIDATION (tras PREREGISTERED y con la snapshot verificada). El backtest piloto previo a la congelación para estimar la tasa de trades (AC-017-4, AC-017-11, REQ-G-103) **no puede registrarse** como evaluación: queda bloqueado hasta que D5 (secuencia de exploración y preregistro) o una decisión del propietario lo resuelva.
2. **Acceso genérico a Train+Val.** CR-020 §C.3.2 exige el par registrado «antes de entregar datos para esa configuración». Se añadió `load_train_val_for_configuration`; `load_train_val` (acceso de desarrollo sin configuración, usado por FEAT-015) se conserva sin cambios. Es un camino que el cargador no puede distinguir de una evaluación. Decisión pendiente del propietario: conservarlo, restringirlo o eliminarlo.
3. **Configuración no planificada.** CR-020 §C.3.2 dice «deja de ser confirmatorio según las reglas vigentes de desviación»; REQ-G-103 v1.8 y §C.4.1 lo establecen sin condición. Se aplicó el texto del contrato: INCONCLUSIVE siempre.

## 6. Decisiones de implementación (dentro de lo aprobado)

- `config_id`: ASCII `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`.
- Archivo de resultados de la selección: JSON `{"experiment_id", "results": {config_id: {métrica: valor}}}` con exactamente los pares evaluados de X; ARGMAX elige el mayor valor y desempata por el orden de TIEBREAK.
- La violación de la regla de selección no escribe un DEVIATION automático: el evaluador la detecta y devuelve INCONCLUSIVE.
- La procedencia se revalida al reproducir el registro (incluido el documento de decisión): si después se borra o altera la decisión, el conteo pasa a indeterminado.
- Con antecedentes sin procedencia, `trials_count()`, la congelación, el inicio de evaluaciones y la selección fallan (Fail-Closed). Es el estado actual del registro real.

## 7. Riesgos residuales

- `informed_by` es una declaración: no prueba qué se consultó. Una decisión reproducible posterior con lista vacía se acepta como NO RELEVANTE (por diseño del contrato); una desviación con lista vacía queda INDETERMINADA.
- Las decisiones tomadas fuera del registro no son detectables (mismo riesgo aceptado en ORQ-017-01).
- El archivo de resultados lo aporta quien evalúa; su conservación versionada no está implementada (relacionado con O4).
- Control en proceso con `flock` POSIX y sistema de archivos local; no sustituye permisos del sistema operativo.
- Edición manual del archivo del registro: se detecta solo cuando rompe la coherencia (hash, procedencia, conteo).
- `load_train_val` genérico (§5.2).

## 8. Corrección A2 — vía única de acceso a Train+Val (2026-11-24)

**Aceptación provisional del propietario (2026-11-24):** resultados de la implementación de CR-020 (771 passed, 5 skipped), sin autorizar commit ni aprobación final. Decisiones: (1) DEVELOPMENT y VALIDATION como restricción provisional; la evaluación exploratoria previa al preregistro queda para D5; (2) el `load_train_val` genérico exige una revisión focalizada (A2); (3) se mantiene la interpretación estricta de REQ-G-103 (configuración no planificada → desviación e INCONCLUSIVE). `trials.py` aceptado como decisión organizativa interna de CR-020.

**Revisión de solo lectura (A2):** ningún llamador de `load_train_val` ni de `load_train_val_for_configuration` en `src/` ni `scripts/`; solo cuatro pruebas de FEAT-015. Ningún flujo de evaluación existente carga Train+Val (`run_backtest` recibe el DataFrame; la CLI solo construye y verifica snapshots; los motores usan `MarketInput` en vivo): no había un bypass alcanzable, sino un uso indebido teórico de una API interna. Defecto hallado: el cargador con puerta validaba con un escaneo del archivo sin validar.

**Decisión del propietario: opción B**, dentro de CR-020 (soportada por REQ-G-104 v1.8; sin CR).

**Corrección (`src/swingpilot/research/partitions.py`):**
- `load_train_val` → `_load_train_val_for_inspection` (privado), con el mismo comportamiento, verificación de SHA-256 y registro de accesos. Solo para la integridad de la snapshot (FEAT-015).
- `load_train_val_for_configuration` es la única vía pública: exige el par exacto en `accounting()["pairs"]` (evidencia validada). Registro ausente, ilegible, corrupto, mal formado o incoherente (incluido un antecedente sin procedencia) → denegado, anotado y sin leer datos.
- `ExperimentRegistry.evaluation_recorded` queda como diagnóstico sin valor de autorización.

**Pruebas (`tests/unit/test_snapshot.py`):** guarda estática por AST sobre `src/` y `scripts/` (con autocomprobación del detector); solo el cargador con puerta es público; registro mal formado no desbloquea; el par debe coincidir exactamente ((X, B) y (Y, A) denegados); registro corrupto, incoherente o ausente → denegado y anotado, sin lectura. Las cuatro pruebas de FEAT-015 solo cambian el nombre del método; sus aserciones no cambian.

**Evidencia contra la implementación anterior a la corrección (mismas pruebas):** 7 failed, 5 passed.

| Prueba | Resultado previo | Clasificación |
|---|---|---|
| `test_a2_malformed_evaluation_record_does_not_unlock_data` | `AssertionError: leyó datos` | **Defecto de comportamiento genuino** |
| `test_a2_unreadable_or_inconsistent_registry_denies_and_logs[inconsistent_antecedent]` | `AssertionError: leyó datos` | **Defecto de comportamiento genuino** |
| `test_a2_only_the_guarded_loader_is_public` | el nombre público antiguo existía | Cambio de interfaz |
| 4 pruebas de FEAT-015 renombradas | `AttributeError` (`_load_train_val_for_inspection`) | Cambio de interfaz |
| Guarda estática, par exacto, JSON corrupto, registro ausente, TC-ML-023 previa | pasaban | Sin regresión (preventivas) |

**Tras la corrección:** suite completa **778 passed, 5 skipped** (771 + 7). Validadores → OK. Registro real sin cambios.

**Límite de arquitectura (documentado, no resuelto):** la corrección hace cumplir las vías de acceso soportadas por la aplicación, no la seguridad del sistema de archivos. `train_val.parquet` no está sellado (FEAT-015) y puede leerse directamente con cualquier herramienta; sellarlo cambiaría FEAT-015 y exigiría una CR. La guarda estática detecta usos por nombre de atributo en `src/` y `scripts/`; no detecta accesos dinámicos (`getattr` con cadenas) ni código fuera de esas carpetas.

## 9. Aprobación del propietario de la implementación (2026-11-24)

- **Aprobada:** la implementación funcional de CR-020 bajo el contrato v1.8 y DEC-021, incluida la corrección A2 (opción B).
- **Evidencia aceptada por el propietario:** 778 passed, 5 skipped; los tres validadores OK; dos defectos de comportamiento de A2 corregidos; las 12 pruebas focalizadas pasan; comportamiento y aserciones de FEAT-015 conservados. La suite no se volvió a ejecutar para esta aprobación documental.
- **Limitaciones residuales aceptadas** con sus condiciones operativas y obligaciones diferidas: piloto previo al preregistro bloqueado hasta D5; `informed_by` como declaración; decisiones fuera del registro no detectables; conservación del archivo de resultados de selección (O4); conteo del registro real indeterminado hasta los registros de procedencia autorizados; control de vías de la aplicación, no del sistema de archivos.
- **Distinción:** es la aceptación de la evidencia de implementación por el propietario, **no** una aprobación de QA independiente, que sigue pendiente.
- **D2:** resuelta metodológicamente, aplicada contractualmente e implementada funcionalmente. Pendientes: registro real de la procedencia de los antecedentes (requiere autorización expresa y una decisión con líneas `AUTORIZA: PROCEDENCIA`) y verificación independiente.
- **Sin cambios:** CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; contrato, AC, gates y registro real.
