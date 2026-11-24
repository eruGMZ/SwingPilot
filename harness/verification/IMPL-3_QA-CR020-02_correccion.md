# IMPL-3 — Corrección de QA-CR020-02 (FEAT-017; CR-020; contrato v1.9)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (corrección; no es una QA independiente).
**Autorización del propietario (2026-11-24):** acepta la evaluación de solo lectura de QA-CR020-02 y autoriza su corrección bajo el contrato v1.9. **Opción A:** si el carácter confirmatorio no puede verificarse → `PreregistrationError`. Incluir la condición de `candidate_selection_rule` solo si CR-020 §C.3.4 la establece sin condición y no exige enmienda. Sin resolver otros hallazgos; sin modificar contrato, registro real, estados de FEAT ni gates; sin sub-agentes, commit ni push.
**Base:** `00510143c200749257dc80206a617a1f83f61bff` (`develop` = `origin/develop`, árbol limpio).
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_QA_independiente.md` §3 (QA-CR020-02) y sondas P2 y P3 de `IMPL-3_CR-020_QA_sondas.py`. Ambos se conservan sin cambios.
**Estado:** CORREGIDO Y ACEPTADO POR EL PROPIETARIO (2026-11-24, §9) — PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE. No se declara cerrado. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## 1. Causa raíz

`confirmatory_status()` (`preregistration.py`) solo consideraba las desviaciones de campos de diseño posteriores a la exposición a OOS/LOCKBOX (regla de CR-011). No aplicaba las dos causas incondicionales de REQ-G-103 v1.8/v1.9 (interpretación estricta mantenida por el propietario, `IMPL-3_CR-020_implementacion.md` §8, decisión 3):

1. **Configuración no planificada:** su DEVIATION se registra en `trials_count` con `after_oos = False`; no es un campo de diseño ni posterior a la exposición, así que no contaba.
2. **Selección distinta de la regla:** no genera DEVIATION; la selección está en la evidencia de la transición a OOS_EVALUATION y el registro solo guarda el SHA-256 del archivo de resultados. La regla congelada está en el contenido del preregistro, no en el registro. Con `(registry, experiment_id)` no podía comprobarse.

El evaluador sí aplicaba ambas (`trials.py`, `UNPLANNED_CONFIGURATION` y `SELECTION_RULE_VIOLATION`). Reproducción en la base: P2 y P3 → `confirmatory = True` con el evaluador en INCONCLUSIVE.

## 2. Trazabilidad contractual

| Causa de pérdida (demostrada) | Fuente | Antes | Ahora |
|---|---|---|---|
| Desviación de un campo de diseño tras la exposición | REQ-G-103 (CR-011) | Sí | Sí (sin cambios) |
| Par de X evaluado fuera de `planned_config_ids` congelado en PREREGISTERED, conste o no su DEVIATION | REQ-G-103 v1.8/v1.9; CR-020 §C.3.2, §C.4.1.4 | No | Sí |
| Candidata seleccionada ≠ la que da la regla congelada | REQ-G-103 v1.8/v1.9; CR-020 §C.3.4, §C.4.1.5 | No | Sí |
| Desviación de `candidate_selection_rule`, en cualquier momento | CR-020 §C.3.4 («Cambiar la regla o seleccionar una configuración distinta de la que da la regla es una desviación de un campo de diseño: el experimento deja de ser confirmatorio») | Solo tras la exposición | Sí, sin condición temporal |

**Condición de `candidate_selection_rule`: sin bloqueo contractual.** CR-020 §C.3.4 la establece sin condición; DEC-021 aprueba §C.3.4 sin reservas (tabla, fila «Evidencia de congelación (§C.3.3) y `candidate_selection_rule` (§C.3.4, R1)… Aprobado»); CR-021/DEC-023 solo sustituye obligaciones de §C.3.2. REQ-G-103 no la menciona, pero no la contradice: es detalle aprobado de la CR que el requisito cita. No requiere enmienda.

**No son pérdida del carácter confirmatorio** (INCONCLUSIVE probatorios o estadísticos; C.4.1–C.4.3): `TRIALS_COUNT_INCONSISTENT`, `SELECTION_MISSING`, `SELECTION_INPUTS_UNVERIFIABLE`, `SELECTION_NOT_REPRODUCIBLE`, `INFORMED_BY_UNVERIFIABLE`, `SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`, registro ilegible y los criterios estadísticos. `N_eval` no restaura el carácter perdido (C.4.2; sin cambios).

## 3. Cambios

| Archivo | Cambio |
|---|---|
| `src/swingpilot/research/preregistration.py` | Nueva excepción `ConfirmatoryStatusUnverifiable(PreregistrationError)`. Nueva `confirmatory_findings(registry, experiment_id, *, preregistration=None, selection_inputs=None)`, sin efectos: reúne las cuatro causas de §2 y lo no verificable (`unverified`); solo lanza ante un registro ilegible, corrupto o incoherente (como `_replay`). Los pares se reconstruyen con `accounting(require_complete=False)` (la completitud de la procedencia no afecta a los pares). La selección se comprueba como en el evaluador: preregistro verificado y vinculado al SHA-256 de PREREGISTERED, `selection_inputs` con el hash registrado, resultados = pares evaluados de X, regla congelada aplicada. `confirmatory_status(...)` acepta los mismos argumentos opcionales: pérdida demostrada → `confirmatory = False` (con `unverified` informado); sin pérdida demostrada y con `unverified` → `ConfirmatoryStatusUnverifiable`. `FrozenPreregistration.confirmatory_status(registry, *, selection_inputs=None)` pasa el propio preregistro. La propiedad `confirmatory` no cambia de firma: tras la selección, sin pérdida demostrada, lanza `ConfirmatoryStatusUnverifiable`. Nuevos campos del resultado: `selection_rule_changes`, `unplanned_config_ids`, `selection`, `selection_rule_violation`, `unverified` (los anteriores se conservan). |
| `src/swingpilot/research/trials.py` | El paso 2 usa `confirmatory_findings` (misma fuente) y devuelve `NOT_CONFIRMATORY` ante desviaciones de diseño tras la exposición **o** desviaciones de `candidate_selection_rule`. Las comprobaciones de configuración no planificada y de selección, sus códigos y su orden no cambian. |
| `research/README.md` | Semántica de la corrección. |
| `tests/unit/test_qa_cr020_02.py` (nuevo) | 11 pruebas (§4). |
| `tests/unit/test_research.py`, `tests/unit/test_cr021_durability.py` | Adaptaciones de solo entrada (§5). |

**Lectura del resultado:** `confirmatory = False` = pérdida demostrada; `ConfirmatoryStatusUnverifiable` = no verificable (no es «no confirmatorio»); `confirmatory = True` = ninguna pérdida y todo verificado. Antes de la selección de candidata, el estado es verificable solo con el registro.

**No cambian:** estados, transiciones, tipos de registro, contabilidad, cargadores, protocolo y garantías de CR-021 (P1–P5, marcadores, copias idénticas), códigos y precedencia del evaluador (salvo la condición añadida de §C.3.4 en `NOT_CONFIRMATORY`), contrato v1.9, registro real, `feature_list.json`, gates.

**Consumidores revisados:** `confirmatory_status` (función), `FrozenPreregistration.confirmatory_status`, `FrozenPreregistration.confirmatory`, `trials.reconcile` (evaluador, vía `acceptance.evaluate`). No hay otros consumidores en `src/`, `scripts/` ni `research/`.

## 4. Evidencia de regresión

**Pruebas nuevas (`tests/unit/test_qa_cr020_02.py`, solo datos sintéticos):**

| Prueba | Comportamiento exigido |
|---|---|
| `test_control_compliant_selection_is_confirmatory_and_eligible` | Control: selección conforme → `True`, `unverified` vacío; evaluador ELIGIBLE |
| `test_before_selection_status_is_verifiable_from_the_registry_alone` | Sin selección: verificable solo con el registro; la propiedad certifica |
| `test_p2_unplanned_configuration_with_deviation_is_not_confirmatory` | **P2:** `False`, `unplanned_config_ids = ["Z"]` antes y después de la selección; evaluador `UNPLANNED_CONFIGURATION` (no `NOT_CONFIRMATORY`) |
| `test_p2_unplanned_pair_without_its_deviation_is_still_not_confirmatory` | Par no planificado sin DEVIATION (persistencia parcial) → `False` |
| `test_p3_selection_against_frozen_rule_is_not_confirmatory` | **P3:** `False`, `selection_rule_violation = True`; evaluador `SELECTION_RULE_VIOLATION` (no `NOT_CONFIRMATORY`) |
| `test_unverifiable_selection_evidence_raises_and_is_not_reported_as_false` | Sin entradas, hash distinto, sin preregistro o preregistro no vinculado → `ConfirmatoryStatusUnverifiable`; la propiedad también; con las entradas correctas → `True` |
| `test_evidentiary_inconclusive_is_not_loss_of_confirmatory_status` | Evaluador `SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`, pero `confirmatory = True` |
| `test_established_violation_is_not_concealed_by_missing_evidence` | Configuración no planificada + selección sin entradas → `False` con `unverified` informado |
| `test_design_deviation_after_oos_with_missing_selection_evidence_is_false` | Desviación de diseño tras OOS + selección sin entradas → `False` |
| `test_selection_rule_change_before_exposure_is_not_confirmatory` | §C.3.4: desviación de `candidate_selection_rule` antes de la exposición → `False` (con y sin entradas); evaluador `NOT_CONFIRMATORY` aunque la selección siga la regla congelada |
| `test_non_selection_design_deviation_before_exposure_keeps_existing_rule` | Regla vigente conservada: otra desviación de diseño antes de la exposición no basta |

**Frente a la base `0051014`** (copia `git archive 0051014 src` en el directorio temporal de la sesión, con un adaptador de API solo en esa copia: `ConfirmatoryStatusUnverifiable` → `PreregistrationError`, argumentos nuevos ignorados): **10 failed, 1 passed**.

- **Fallos de comportamiento genuinos (6):** P2 (`True is False`), par no planificado sin DEVIATION (`True is False`), P3 (`True is False`), evidencia no verificable (`DID NOT RAISE`), pérdida demostrada con evidencia ausente (`True is False`), cambio de la regla de selección (`True is False`).
- **Solo por campos nuevos del resultado (4; `KeyError`):** los dos controles, la desviación de diseño tras OOS y la regla vigente conservada. Su comportamiento ya era correcto en la base; protegen que no cambie.
- **Pasa en la base (1):** INCONCLUSIVE probatorio con `confirmatory = True` (control).

Sin el adaptador, el archivo no se puede importar en la base (`ImportError`), lo que no es evidencia de comportamiento.

**Sondas originales:** sin modificar. Una reproducción equivalente de P2 y P3 en el árbol corregido da: P2 → `confirmatory = False` (evaluador sin cambios: `UNPLANNED_CONFIGURATION`); P3 llamada sin preregistro ni entradas, como en la sonda → `ConfirmatoryStatusUnverifiable` (ya no `True`); con ellas → `False` (prueba P3).

## 5. Pruebas existentes adaptadas (solo entradas de verificación)

En las cuatro, el experimento ya ha pasado por la selección de candidata y la aserción espera «confirmatorio». Con la opción A, certificarlo exige el archivo de resultados; solo se aporta esa entrada. Ninguna aserción de comportamiento cambia.

| Prueba | Adaptación |
|---|---|
| `test_research.py::test_qa3r2_07_authorization_without_consumption_is_not_exposure` | `fz.confirmatory` → `fz.confirmatory_status(reg, selection_inputs=SELECTION_INPUTS)["confirmatory"]` |
| `test_research.py::test_qa3r2_07_pre_exposure_and_non_design_deviations_preserved` | Igual en las dos aserciones positivas; la negativa (`not fz.confirmatory`) no cambia: la pérdida está demostrada |
| `test_research.py::test_orq_017_01_exposure_chronology_is_file_order` | `selection_inputs=SELECTION_INPUTS` en la consulta que espera `True` |
| `test_cr021_durability.py::test_p1_control_clean_registry_allows_every_path` | `preregistration=fz, selection_inputs=inputs` en la consulta; aserción idéntica. Las garantías P1 de CR-021 no cambian (la ruta `read.confirmatory_status` sigue fallando ante cada corrupción) |

## 6. Resultados

- Pruebas focalizadas: `tests/unit/test_qa_cr020_02.py` → 11 passed; `test_research.py`, `test_trials_accounting.py`, `test_cr021_durability.py`, `test_qa_cr020_01.py` → 332 passed.
- Suite: `.venv/bin/pytest -q -p no:cacheprovider tests` → **822 passed, 5 skipped** (811 + 11 nuevas).
- Validadores: `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Registro real sin cambios (SHA-256 `07efad20…`).

## 7. Limitaciones residuales

1. **La propiedad `confirmatory` no puede recibir `selection_inputs`:** tras la selección, sin pérdida demostrada, lanza `ConfirmatoryStatusUnverifiable`. La consulta de HUMAN_REVIEW debe usar `confirmatory_status(..., selection_inputs=…)`.
2. **Las decisiones tomadas fuera del registro** siguen sin ser detectables (riesgo residual de ORQ-017-01 y CR-020 §C.4.2; sin cambios).
3. **Pares de X anteriores a la congelación:** se tratan igual que en el evaluador (todo par de X fuera de `planned_config_ids` es no planificado). Hoy no pueden existir porque la evaluación solo se permite en DEVELOPMENT y VALIDATION (decisión provisional; la evaluación exploratoria previa queda para D5). Si D5 la permite, habrá que revisar esta regla en ambos sitios.
4. **Consistencia entre la consulta y el evaluador:** la comprobación de configuraciones no planificadas y de la selección está en ambos sitios con la misma lógica (el evaluador conserva sus códigos propios). Las pruebas P2 y P3 comprueban ambos lados.
5. **`feature_list.json`** no se actualiza (QA-CR020-06 sigue sin resolver).

## 8. Archivos

Modificados: `src/swingpilot/research/preregistration.py`, `src/swingpilot/research/trials.py`, `research/README.md`, `tests/unit/test_research.py`, `tests/unit/test_cr021_durability.py`, `progress.md`, `session-handoff.md`. Nuevos: `tests/unit/test_qa_cr020_02.py`, este documento. Sin commit ni push. Sub-agentes: 0.

## 9. Aceptación del propietario (2026-11-24)

El propietario aprueba la corrección de QA-CR020-02 bajo el contrato v1.9 y acepta:

- la opción A y la excepción `ConfirmatoryStatusUnverifiable`;
- las cuatro causas contractuales de pérdida del carácter confirmatorio, incluida la condición incondicional de `candidate_selection_rule` (CR-020 §C.3.4);
- la precedencia de las pérdidas demostradas sobre la evidencia de verificación ausente;
- la conservación de los códigos del evaluador y de las garantías de CR-021;
- las cuatro adaptaciones de pruebas existentes, con sus aserciones de comportamiento conservadas;
- las 11 pruebas nuevas, incluida la distinción entre los 6 fallos de comportamiento genuinos y los 4 fallos de interfaz frente a la base;
- las limitaciones residuales de §7;
- el resultado de la suite (822 passed, 5 skipped) y los tres validadores OK.

**Estado:** QA-CR020-02 CORREGIDO Y ACEPTADO POR EL PROPIETARIO; PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE.

**Obligaciones de la reverificación independiente:**
1. Coherencia entre la consulta (`confirmatory_status` / `confirmatory_findings`) y el evaluador (`trials.reconcile`) en las cuatro causas de pérdida.
2. Vinculación del preregistro congelado al SHA-256 de PREREGISTERED (incluido el preregistro alterado o ajeno).
3. Validación del hash del archivo de resultados de la selección (`selection_inputs_sha256`).
4. Ausencia de certificación confirmatoria falsa: ninguna ruta devuelve `confirmatory = True` sin verificación completa.

**Commit autorizado:** los nueve archivos de §8, con el mensaje «fix(impl-3): resolve QA-CR020-02 confirmatory status consistency», sin push; pruebas no reejecutadas para el commit. Sin cambios en contrato, evidencia de QA original, sondas, registro real ni `feature_list.json`. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
