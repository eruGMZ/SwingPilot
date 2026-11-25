# IMPL-3 — Corrección de N-1 (reverificación independiente de CR-020; FEAT-017)

**Fecha:** 2026-11-25
**Autor:** Orquestador de Desarrollo (corrección; no es una verificación independiente).
**Autorización del propietario (2026-11-25):** corrección de N-1 **sin solicitud de cambio**, solo N-1; sin N-2, N-3, D-1..D-5 ni la observación separada de `_marker_error`; sin commit ni push.
**Base:** `67195da` (`develop`). Contrato **v1.10** y `feature_list.json` **v1.21.1** sin cambios.
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_reverificacion_consolidada.md` (N-1) y sonda `IMPL-3_CR-020_reverificacion_sondas/p_builder.py`; ambos se conservan sin modificar.
**Estado:** CORREGIDO Y ACEPTADO POR EL PROPIETARIO (2026-11-25, §8) — PENDIENTE de reverificación independiente focalizada.

## 1. Causa raíz

`ExperimentRegistry.begin_configuration_evaluation` solo comprobaba `kind` y `config_id` de la DEVIATION devuelta por `deviation_builder`; el resto de su validación vive en el constructor sancionado (`preregistration._deviation_builder`) y en `_replay`, que solo lee el archivo. A nivel de la API pública la obligación «DEVIATION construida y validada antes de escribir» no se cumplía:

| Caso reproducido | Mecanismo | Resultado previo |
|---|---|---|
| `experiment_id` ajeno | marcador no vinculable (`_marker_error`: «no corresponde a este par») | registro **corrupto** (P1), `PersistenceUncertainError` |
| `field` ≠ `trials_count` | marcador no vinculable («DEVIATION certificada no corresponde») | registro **corrupto** (P1) |
| `deviation_id` ausente | el marcador certifica `None == None`; `_replay` la rechaza | éxito y acceso denegado después |
| SHA-256 del preregistro erróneo | `_replay` | éxito y acceso denegado después |
| `informed_by` no verificable | `_replay` | éxito y acceso denegado después |

Llamador sancionado (`preregistration.begin_evaluation`): ya validaba en su constructor; no afectado. Comportamiento de la API subyacente: no validaba.

## 2. Corrección

`src/swingpilot/research/experiments.py`: nuevo método `ExperimentRegistry._deviation_output_error` (sin efectos), invocado en `begin_configuration_evaluation` justo después de la comprobación existente de `kind`/`config_id`, dentro del mismo bloqueo y antes de cualquier escritura. Si devuelve un motivo → `EvaluationRequestRejected` («solicitud rechazada, nada escrito»). Comprueba, en este orden: `experiment_id` = el de la solicitud; `field` = `trials_count`; `_deviation_shape_error` (reutilizada por **importación local** desde `preregistration`, sin duplicar: claves obligatorias, `deviation_id` 32 hex, SHA-256 con formato válido, `field` conocido, justificación, `after_oos` booleano, actor, `authorizes_change` = False, `access_log_evidence`, `informed_by` lista); presencia de `informed_by` (R2); SHA-256 = el de PREREGISTERED del experimento (ya calculado en la función); `deviation_id` no repetido en el registro; `informed_by_error` sobre los registros actuales; cronología: `after_oos` = (`_registry_exposure` o evidencia de accesos), la misma regla que `_replay`; y serialización (`_serialize`; un fallo `TypeError`/`ValueError` → rechazo).

La importación local funcionó (el módulo `preregistration` importa `experiments`, por lo que una importación de módulo sería circular); no hubo bloqueo.

**No cambian:** el orden de escritura, `fsync` y marcador; el bloqueo; la ruta de reintento (el constructor solo se invoca si no consta la DEVIATION); `_marker_error`; el cargador; el evaluador; contratos; registro real.

## 3. Trazabilidad contractual

- CR-020 §C.3.2: validaciones previas «antes de escribir»; solicitud rechazada → nada escrito, no cuenta.
- CR-021 §D.4 paso 1 y paso 4: «DEVIATION obligatoria construida y validada antes de escribir. Rechazo → nada escrito».
- CR-021 §D.3: el marcador solo vincula una DEVIATION del mismo par, con su `deviation_id`, `field` = `trials_count` y validada por la reproducción de ORQ-017-01.
- CR-021 §D.5 y §F.2 (P1): un registro corrupto bloquea todo; la corrección impide que esta API lo produzca.
- ORQ-017-01 / R2: forma, SHA-256, `informed_by` y `after_oos` (misma regla que `_replay`).
- No requiere CR: el texto vigente ya exige la validación (aprobado por el propietario).

## 4. Pruebas

Nuevo archivo `tests/unit/test_n1_deviation_prewrite_validation.py` (43 casos; registros temporales y datos sintéticos): los 5 casos reproducidos; 23 defectos estructurales y contextuales adicionales (identidad, `deviation_id`, SHA-256, justificación, actor, `authorizes_change`, `after_oos` sin/ con exposición, `access_log_evidence`, clave ausente, `informed_by` ausente/no lista/mal formada/repetida/procedencia inexistente, `kind`, no serializable); `deviation_id` repetido; salida no dict y constructor que lanza; y controles: salida válida por la API, `informed_by` válido, vía sancionada planificada y no planificada, reintento idempotente (el constructor no se invoca), DEVIATION existente sin marcador (recuperación con copias idénticas, sin invocar el constructor) y rechazo seguido de reintento válido. Cada rechazo comprueba: `EvaluationRequestRejected`, archivo idéntico byte a byte, conteo sin cambios, registro legible, sin marcador y cargador denegado sin leer datos.

**Contra la base sin corregir (`67195da`): 30 failed, 13 passed.**
- 30 fallos de comportamiento (genuinos): escritura/corrupción o éxito con evidencia inválida, `TypeError` sin estructurar para lo no serializable, y registro modificado ante `deviation_id` repetido.
- 13 aprobadas con la base: preventivas/de control (`config_id` distinto o ausente, `kind` distinto, 4 salidas no dict, constructor que lanza —ya rechazados por la comprobación previa—, y los 5 controles de comportamiento válido).

**Con la corrección:** 43 passed.

## 5. Resultados de ejecución

- `.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_n1_deviation_prewrite_validation.py` → 43 passed.
- Regresiones CR-021/CR-020 relevantes (`test_cr021_durability.py`, `test_qa_cr020_01.py`, `test_qa_cr020_02.py`, `test_trials_accounting.py`, `test_cr020_regressions.py`) → 130 passed.
- Suite completa (una vez): `.venv/bin/pytest -q -p no:cacheprovider tests` → **870 passed, 5 skipped** (827 + 43 nuevas).
- `python3 scripts/validate_{manifest,requirements,gates}.py` → código 0.
- Sonda `p_builder.py` reejecutada sobre registros temporales: los cinco casos → `EvaluationRequestRejected`, `written=False`, registro legible, acceso denegado.
- Registro real `research/experiments/registry.jsonl`: SHA-256 `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b` antes y después (sin cambios).

## 6. Archivos

Modificado: `src/swingpilot/research/experiments.py`. Nuevos: `tests/unit/test_n1_deviation_prewrite_validation.py`, este documento. Actualizados: `progress.md`, `session-handoff.md`. Sin cambios: informe y sondas preservados, `feature_list.json`, contratos, conflictos, gates, FEAT.

## 7. Limitaciones residuales

- No es retroactiva: una DEVIATION inválida ya escrita permanece (append-only, sin reparación automática; conciliación manual PENDING). No consta ninguna en el registro real.
- La comprobación de cronología reutiliza `_registry_exposure`, que relee el archivo dentro del bloqueo (las lecturas no toman `flock`; relación con N-2, no tratada).
- `_marker_error` sigue sin exigir la reproducción ORQ-017-01 de la DEVIATION certificada: observación separada, no tratada; tras esta corrección no es alcanzable por esta API.
- Un llamador que escriba líneas directamente en el archivo queda fuera de alcance, como antes.
- Esta corrección no cierra N-1 ni D2: la disposición y la reverificación independiente corresponden al propietario.

## 8. Aceptación del propietario (2026-11-25)

El propietario **acepta la implementación de N-1 y la evidencia de regresión informada** (§4 y §5) y autoriza congelar la corrección en un único commit («fix(research): validate mandatory deviation evidence before persistence»). Las limitaciones residuales de §7 se conservan sin cambios.

**Distinción:** la aceptación de la implementación por el propietario **no es** una reverificación independiente. N-1 queda registrado como **corregido y aceptado por el propietario, pendiente de reverificación independiente focalizada** (a realizar sobre el commit de la corrección; no iniciada). No se cierra D2, ni se resuelven N-2, N-3, D-1..D-5 ni la observación de `_marker_error`.
**Sin cambios:** contrato v1.10, `feature_list.json` v1.21.1, estados de FEAT y de conflictos, gates; D2 pendiente de cierre. La suite funcional no se reejecutó para esta anotación (solo documental).
