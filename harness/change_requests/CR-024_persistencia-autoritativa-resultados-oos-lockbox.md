# CR-024 — Persistencia autoritativa de resultados de evaluación OOS y LOCKBOX (`evaluation_hash`)

**Fecha:** 2026-11-26 (revisión 3)
**Estado:** **APROBADA por el propietario (2026-11-26) y APLICADA contractualmente** (contrato v1.12; `feature_list.json` v1.24.0). Implementada (I1–I3, commit `0f2185c`) y B8.1–B8.4 sin commit (ver CR-025 y `research/README.md`); la verificación independiente y el cierre de FEAT siguen **PENDIENTES**; sin push.
**Origen:** bloqueo de B8.0 (`progress.md`, 2026-11-26, decisión 5). Opción **B** aprobada; decisiones 1–6 de la revisión 1 resueltas por el propietario (§E).
**Vinculada a:** CR-021 (se reutilizan S1–S4, P1–P4 y `PersistenceUncertainError` sin modificarlos), CR-023 (ET-4..ET-8, V4, B6, B7), decisión 5.
**Alcance mínimo:** persistir de forma durable, inmutable y única el resultado de OOS y LOCKBOX; ligarlo al preregistro congelado y al consumo autorizado; exigir un OOS favorable autoritativo antes de progresar al LOCKBOX; definir el `evaluation_hash` de ET-8.
**Fuera de alcance (conservado):** Train+Val (`CONFIGURATION_EVALUATED`, `EVALUATION_PERSISTED`), CR-020, CR-022, forma de `PARTITION_CONSUMED`, O3/O4, CONF-010, P5 de CR-021 (PENDIENTE), D3 ABIERTA, D4 bloqueada, **D6 diferida** (sin umbrales ni métodos estadísticos), hash de fuentes del evaluador (diferido). El acceso final ya no está bloqueado por `_FINAL_ACCESS_BLOCKED_UNTIL_B6`: esa constante no existe en `src/` ni en `tests/` (verificado) y esta CR no la invoca; las menciones históricas en `progress.md` y `session-handoff.md` no se editan.

---

## A. Problema

`WindowOutcome`/`FinalWindowsResult` (B7) solo existen en memoria; `evaluate_window` no escribe en el registro; `PARTITION_CONSUMED` no lleva hash. Tras el consumo (irreversible; `consumption_reversed` y `retry_allowed` son siempre `False`) el resultado puede perderse sin rastro y ET-8 carece de referente para `OOS=`/`LOCKBOX=<evaluation_hash>`.

## B. Cambio propuesto

### B.1 Documento de resultado (`schema` = 1) y tipos canónicos

Campos exactos: `schema`; `experiment_id`; `partition` (`oos`|`lockbox`); `prereg_sha256`; `snapshot_id`; `window_id`; `manifest_sha256` (bytes del manifiesto sellado verificado en B7.4b); `consumption` = `{decision_ref, consumed_line_sha256}` (bytes exactos de la línea `PARTITION_CONSUMED` sin salto final, criterio de CR-021 §D.3); `evaluator_version`; `outcome` = todos los campos de `WindowOutcome`.

- **`evaluator_version` (obligatorio, derivado por el sistema):** cadena no vacía calculada por el evaluador a partir de la versión del contrato vigente, el `schema` y las versiones de las librerías que ya registran los manifiestos (python, pandas, pyarrow). Nunca la aporta el llamador; ausente o vacía → no persistible. **No** es un hash de fuentes (diferido): no identifica ni garantiza el código del evaluador, dos ejecuciones con el mismo valor pueden provenir de fuentes distintas y no acredita reproducibilidad de código.
- **Tipos admitidos (cerrados) y codificación:**

| Tipo de origen | Codificación canónica |
|---|---|
| `str` | cadena JSON UTF-8, sin normalización ni sustitución |
| `bool` | `true`/`false` (nunca como entero) |
| `int` (incl. `numpy.integer`, convertido por tipo exacto) | entero decimal sin ceros a la izquierda ni `+`; `-0` no existe |
| `float` (incl. `numpy.floating`) | objeto **etiquetado** `{"$f64":"<16 hex minúsculas>"}` = binary64 big-endian; un único NaN canónico `7ff8000000000000`; `-0.0` (`8000…`) distinto de `0.0`; `±Infinity` **rechazado** |
| `None` | `null` |
| `list`/`tuple` | arreglo, orden conservado |
| `dict` | objeto con claves `str` únicas, ordenadas por punto de código |

Cualquier otro tipo (Timestamp, array, Decimal, enum, bytes, `set`, clave no `str`, una clave `$f64` en cualquier `dict` ordinario, a cualquier nivel: la clave está **reservada** al etiquetado de `float`) → rechazo. Serialización: UTF-8, separadores `,`/`:`, sin espacios, `ensure_ascii=False`. **Lectura estricta:** se rechazan números JSON con fracción o exponente, `NaN`/`Infinity`, claves duplicadas y toda desviación: el documento releído debe reserializarse a los **mismos bytes**. Un `$f64` es una cadena etiquetada, jamás ambigua con un `str`.
- **`evaluation_hash`** = SHA-256 (64 hex minúsculas) de esos bytes; excluye `at_utc` y `actor`.
- El evaluador canonicaliza su resultado **al emitirlo**: si no es canonicalizable, `evaluate_window` lo convierte en un resultado `TECHNICAL`/`UNDETERMINABLE` con `metrics = None`, que sí lo es; así un fallo de tipo no deja un consumo sin resultado.
- Se persisten **todos** los veredictos y fallos.

### B.2 Procedencia confiable del resultado

Solo `evaluate_window` emite un objeto opaco `IssuedWindowResult` (clase con credencial interna privada y constructor no invocable desde fuera; precedente: `FreezeCheck`, `ConsumptionCheck`, B6.3), que lleva el documento canónico ya validado y sus ligaduras. La persistencia exige `type(...) is IssuedWindowResult` y revalida la ligadura al consumo y al preregistro dentro del bloqueo; un diccionario, un `WindowOutcome` suelto, una copia o un hash aportado por el llamador → rechazo, nada escrito. Opera dentro del modelo de proceso confiable (no es tamper-evident frente a un proceso Python comprometido).

### B.3 Evidencia inmutable (almacén separado)

`<store_resultados>/<EXP-NNNN>/<partition>.result.json`, distinto del almacén de preregistros, con el protocolo de `prereg_store` (`O_EXCL`, `fsync` del archivo y de la cadena de directorios, relectura con descriptor nuevo y comprobación del hash). Sin sobrescritura ni reparación automática; bytes idénticos sobre un archivo presente son idempotentes; distintos → incoherente.

### B.4 Evento dedicado `WINDOW_RESULT_PERSISTED` (append-only, `registry.jsonl`)

Campos: `experiment_id`, `partition`, `snapshot_id`, `evaluation_hash`, `prereg_sha256`, `verdict`, `eligibility`, `evaluator_version`, `consumed_line_sha256`, `actor`, `at_utc`. **Válido** solo si, antes de él en el archivo, hay exactamente un `PARTITION_CONSUMED` de la ventana por el experimento dueño cuya línea produce `consumed_line_sha256`; el `prereg_sha256` coincide con el PREREGISTERED vigente; y la evidencia existe, su SHA-256 es `evaluation_hash`, cumple la lectura estricta de B.1 y repite los campos duplicados. Todo fallo → incoherente (Fail-Closed).

**Favorable autoritativo** (definición única): `RESULT_VALID` con `verdict == ELIGIBLE_FOR_HUMAN_REVIEW` **y** `eligibility == ELIGIBLE` **y** `nature is None`, comprobadas en la evidencia y en el marcador y coincidentes. Cualquier otra combinación no es favorable.

### B.5 Unicidad y orden de escritura (reutiliza CR-021)

Una identidad lógica por (`experiment_id`, `partition`); copia byte a byte idéntica = el mismo resultado; distinta → incoherente; sin reemplazo ni versión posterior. Bajo el bloqueo exclusivo y con S1–S4: (1) canonicalizar y hashear; (2) escribir y confirmar la evidencia; (3) escribir el marcador y `fsync` en descriptor nuevo; (4) releer y verificar B.4. Error en 2–4 → `PersistenceUncertainError`, sin éxito informado. **Tras la emisión del resultado técnico:** el consumo ya es irreversible y el resultado ya se emitió; un fallo de persistencia no lo revierte ni autoriza reevaluar ni reintentar con datos nuevos, el resultado en memoria no es autoritativo y la ventana queda en `CONSUMED_NO_RESULT` o `EVIDENCE_ONLY` (B.6), que bloquean la progresión. La persistencia vive en un módulo de orquestación invocado por `evaluate_final_windows`; `evaluate_window` sigue sin escribir.

### B.6 Conciliación Fail-Closed

| Estado | Condición | Efecto |
|---|---|---|
| `NOT_CONSUMED` | sin consumo | nada que conciliar |
| `RESULT_VALID` | consumo + evidencia + marcador válidos | autoritativo |
| `CONSUMED_NO_RESULT` | consumo sin evidencia ni marcador | **bloquea** LOCKBOX, ET-8 y toda progresión; **disposición manual del propietario**; sin reevaluación, sin reversión del consumo, sin reconstrucción desde datos |
| `EVIDENCE_ONLY` | evidencia válida ligada al consumo, sin marcador | recuperable **solo con comando explícito del CLI**: relee únicamente la evidencia (sin datos de mercado), **revalida su durabilidad** (nuevo `fsync` de archivo y cadena de directorios y relectura con descriptor nuevo) y luego escribe el marcador; error → `PersistenceUncertainError`; ningún acceso lo dispara |
| `CORRUPT` | marcador sin evidencia, hash distinto, sin consumo previo, duplicado conflictivo | `RegistryCorruptError`; conciliación manual (P5 de CR-021, PENDIENTE; no se define aquí) |

### B.7 Progresión al LOCKBOX

El LOCKBOX exige un OOS **favorable autoritativo** (B.4), releído del registro y la evidencia y no de la memoria del proceso, en **ET-4** (construcción de su snapshot), **ET-5** (grant), **ET-6** (`claim_partition`, dentro del bloqueo, vía `ConsumptionCheck`) y en `resolve_lockbox`. Enmienda V4-pre del LOCKBOX en CR-023 §C.9 y ET-4 (antes «OOS consumida»); la continuidad de C.6.5 no cambia. `evaluate_final_windows` persiste y relee el OOS antes de `resolve_lockbox`; si falla, el LOCKBOX no se inicia.

### B.8 `evaluation_hash` en ET-8

`OOS=` y `LOCKBOX=` de la línea `AUTORIZA: APROBACION …` son los `evaluation_hash` de B.1. Bajo el bloqueo y con `_load`, ET-8 comprueba para cada partición: `RESULT_VALID`, favorable autoritativo (B.4), hash de la línea = del marcador = SHA-256 de la evidencia, mismo `experiment_id` y `prereg_sha256`, y V4-post. Gramática y unicidad de la decisión 5 sin cambios.

## C. Identificadores afectados (verificados contra `requirements.md`, `test_plan.md` y `feature_list.json`; contrato v1.11 → v1.12)

- **Requisitos (existen):** REQ-G-104 (estados, `HUMAN_REVIEW → APPROVED`), REQ-G-106 (evaluación única OOS/LOCKBOX), REQ-G-109 (consumo, LOCKBOX, V4), REQ-G-P23 (promoción; fila de tabla). **Sin cambios:** REQ-G-P17, REQ-G-103.
- **CR-023:** §C.6.4, §C.9 (V4-pre del LOCKBOX; ET-4; fila ET-8), §H («sin cambios de tipos de registro»).
- **Criterios existentes:** AC-015-7, AC-015-9 (FEAT-015); AC-017-1, AC-017-8, AC-017-9, AC-017-14 (FEAT-017); AC-019-2 (FEAT-019, promoción). **Nuevo propuesto:** AC-017-15 (persistencia, unicidad, procedencia y Fail-Closed de resultados). Corrección: la revisión 1 citaba AC-017-3/4/10/11; no se ven afectados.
- **Pruebas:** TC-ML-007, TC-ML-012, TC-ML-019, TC-ML-025, TC-ML-027 (existen; enmiendas); **TC-ML-029** libre (nueva). `tests/unit/test_cr024_result_persistence.py` (tipos canónicos incl. `-0.0`, NaN, Inf, bool vs int, `$f64` vs `str`, lectura estricta; procedencia: rechazo de tipos no emitidos; unicidad; cada fallo de B.5 y estado de B.6; LOCKBOX bloqueado en ET-4/5/6/`resolve_lockbox` sin OOS favorable, incluido `verdict` favorable con `eligibility` no `ELIGIBLE`; ET-8); adaptar `test_cr023_b7_e2e_window.py` y `test_cr023_b7_acceptance_window.py`; regresión sin cambios de `test_cr021_durability.py`, CR-020, CR-022 y la suite.
- **Código (autorización separada):** módulo de persistencia de resultados; `window_evaluation.py` (emisión de `IssuedWindowResult`, orquestación); `experiments.py`; `partitions.py`; `independence.py`; `evaluation_snapshot.py` (ET-4); `cli.py` (recuperación); `research/README.md`.

## D. Conflictos

1. CR-023 §C.6.4/§H (tipos de registro sin cambios) → enmendado por B.4 con nota de vigencia.
2. CR-023 §C.9 (V1/V6/V7 solo existencia y sintaxis; ET-4 solo «consumida») → B.7 y B.8 añaden verificaciones mecánicas.
3. B7 «no escribe en el registro» → conservado para `evaluate_window`.
4. TC-ML-007/012 (sin reevaluación) → compatibles: la recuperación solo reescribe un marcador desde evidencia ya calculada.
5. Dependencia: P5 de CR-021 PENDIENTE para `CORRUPT` y la disposición de `CONSUMED_NO_RESULT`.

## E. Decisiones del propietario (2026-11-26; resueltas)

1. Contenido canónico aprobado con `evaluator_version` obligatorio derivado por el sistema; hash de fuentes diferido. 2. Almacén de evidencia separado e inmutable. 3. `CONSUMED_NO_RESULT` bloquea; disposición manual; sin reevaluación ni reversión. 4. OOS favorable autoritativo en ET-4, ET-5, ET-6 y `resolve_lockbox`. 5. `EVIDENCE_ONLY` solo por CLI explícito con revalidación de durabilidad. 6. B8 bloqueada hasta implementar y verificar CR-024.

## F. Limitaciones residuales

Modelo de proceso confiable (sin protección frente a un proceso Python comprometido); durabilidad bajo S1–S4; un resultado perdido antes de B.5-2 solo se detecta y bloquea.

## G. Aplicación contractual (2026-11-26)

Contrato v1.11 → **v1.12** y `feature_list.json` v1.23.0 → **v1.24.0**: REQ-G-104, REQ-G-106, REQ-G-109 y REQ-G-P23; AC-015-7, AC-015-9, AC-017-1, AC-017-8, AC-017-9, AC-017-14, AC-017-15 (nuevo) y AC-019-2; TC-ML-007, TC-ML-012, TC-ML-019, TC-ML-025, TC-ML-027 y TC-ML-029 (nueva); notas de vigencia en CR-023. Sin cambios: CR-020, CR-021, CR-022, forma de `PARTITION_CONSUMED`, REQ-G-P17, REQ-G-103. **Pendientes:** implementación y pruebas (autorización separada), verificación independiente, P5, O3/O4 y D6; B8 permanece bloqueada hasta implementar y verificar CR-024.

## Notas de vigencia (CR-025, contrato v1.13; el texto original de CR-024 se conserva)

- **§B.8 y REQ-G-P23 («el recálculo de ET-9/ET-10 no cambia»):** ~~no cambia~~ — enmendado por CR-025: ET-9 y ET-10 incorporan V9. La verificación de `evaluation_hash` de ET-8 se mantiene y su núcleo (`verify_result_evidence`) se comparte con V9.
- **§F (limitaciones):** se añade la limitación continua de CR-025 §F (editar la línea `APROBACION` o su documento bloquea como `TECH`).
- **§E decisión 6 (B8 bloqueada hasta implementar y verificar CR-024):** sin cambios.
