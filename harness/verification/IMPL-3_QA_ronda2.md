# IMPL-3 — QA independiente, ronda 2 (última) — FEAT-015, FEAT-016, FEAT-017 infraestructura, FEAT-019 infraestructura

**Fecha:** 2026-11-20
**Revisor:** QA Agent independiente nuevo: sub-agente de solo lectura, sin red, sin API de Anthropic de SwingPilot (~149K tokens del sub-agente; $0 del presupuesto de IA de IMPL-3). Ejecutado como uid 1000 (no root).
**Reproducciones:** `/tmp/claude-1000/qa-impl3-r2/` (temporales, fuera del repositorio).
**Ronda anterior:** `harness/verification/IMPL-3_QA_ronda1.md` (hallazgos y correcciones).
**Estado:** hallazgos nuevos ABIERTOS. No se corrigen sin autorización: la autorización del propietario cubría QA3-01..19.

pytest (QA): `.venv/bin/pytest -q -p no:cacheprovider tests` → 390 passed, 5 skipped.

## Verificación de la ronda 1

| ID | Veredicto | Nota |
|---|---|---|
| QA3-01 | CERRADO | Reintento con espera exponencial reproducido; sin deadlock (orden de locks feed → store); la generación solo cambia al desconectar. |
| QA3-02 | CERRADO | Descarga truncada abortada; rejilla hasta `range_end`; inicio de cotización declarado. |
| QA3-03 | CERRADO | Antecedentes restringidos y no elegibles. |
| QA3-04 | CERRADO | Con observación QA3R2-04. |
| QA3-05 | CERRADO para NaN/inf | La misma clase de fallo persiste con equity ≤ 0 (QA3R2-01). |
| QA3-06 | CERRADO | Sellado 0o000 verificado, consumo persistido, `_read` restaura el modo en `finally`. |
| QA3-07 | **PARCIAL** | DSR interno (fórmula verificada) y conteo OOS contrastado; equity y retornos no se cruzan con `oos_net_r` (QA3R2-01). |
| QA3-08 | CERRADO | |
| QA3-09, 10, 11, 12 | CERRADOS | 0 diferencias en 700 longitudes de corte; identidad del neto verificada en 370 trades; `iloc[:i+1]` sin coste O(n²) práctico (80k filas en 0,56 s). |
| QA3-13, 14, 16, 17, 18, 19 | CERRADOS | Con observación QA3R2-07 sobre QA3-13. |
| QA3-15 | **PARCIAL** | Un fallo entre el renombrado del directorio y la escritura del manifiesto deja un directorio sin manifiesto que bloquea el reintento (QA3R2-02). |

## Hallazgos nuevos

Ninguno BLOQUEANTE ni MAYOR.

| ID | Sev. | Archivo | Hallazgo | Evidencia | Corrección necesaria |
|---|---|---|---|---|---|
| QA3R2-01 | MENOR | `research/acceptance.py` | `max_drawdown` no valida el dominio: equity a cero da NaN, equity negativa da −0, y una equity de 1 punto con 40 trades da `ELIGIBLE_FOR_HUMAN_REVIEW` sin motivos. Equity y retornos son independientes de `oos_net_r`. `n_resamples=0` y enteros enormes fallan con excepción en vez de INCONCLUSIVE. | Reproducido | Exigir equity > 0 y `len(equity) == len(oos_net_r)+1`; derivar o contrastar equity y retornos con `oos_net_r`; validar `n_resamples ≥ 1`; prueba con equity ≤ 0. |
| QA3R2-02 | MENOR | `research/snapshot.py` | Si el fallo ocurre tras renombrar el directorio y antes del manifiesto, queda un directorio huérfano que bloquea el reintento. | Reproducido | Escribir el manifiesto antes del renombrado final, o limpiar ante fallo del manifiesto. |
| QA3R2-03 | MENOR | `research/partitions.py` | Carrera (TOCTOU) entre la comprobación de consumo y su registro: dos cargadores concurrentes leen el LOCKBOX y registran 2 consumos. Una lectura fallida consume la partición, de forma conservadora pero sin documentar. | Reproducido con barrier | Comprobación y registro atómicos (`flock` sobre el registro); documentar el consumo ante fallo de lectura. |
| QA3R2-04 | OBS | `research/experiments.py` | La cita en la decisión se comprueba por subcadena: «oos» aparece en «choose». `create()` no valida el formato del id. | Reproducido | Línea estructurada (`AUTORIZA: <exp> <partición> <snapshot>`) con regex; validar `EXP-NNNN`. |
| QA3R2-05 | OBS | `market_data/stream.py` | El reintento de resync solo se evalúa al llegar un mensaje; con una conexión silenciosa no hay reintento. Impacto bajo: Binance emite kline cada ~1–2 s. | Reproducido | Evaluar también con timeout de lectura. |
| QA3R2-06 | OBS | `research/backtest.py` | `ExecutionModel` acepta comisión o slippage NaN. El evaluador lo convertiría en INCONCLUSIVE. | Por lectura | Validar finitos. |
| QA3R2-07 | OBS | `research/preregistration.py` | `oos_seen` se deriva del registro de accesos que pasa quien llama, no del registro de experimentos. | Por lectura | Derivarlo de `registry.consumed_partitions()`. |
| QA3R2-08 | OBS | `research/snapshot.py`, `cli.py` | Bajo root o sin permisos POSIX, el sellado 0o000 no aplica y no se detecta. Un SIGKILL dentro de `_read` deja 0o400. `verify-snapshot --id` no valida el id. | Por lectura | Documentar; comprobar con `os.access` y avisar; validar el id en la CLI. |

## Veredicto por FEAT

| FEAT | Veredicto QA ronda 2 |
|---|---|
| FEAT-015 | CONFORME CON OBSERVACIONES (QA3R2-02, QA3R2-03) |
| FEAT-016 | CONFORME CON OBSERVACIONES (QA3R2-05) |
| FEAT-017 (infraestructura) | CONFORME CON OBSERVACIONES; el QA recomienda corregir QA3R2-01 antes de usar el evaluador en una evaluación real |
| FEAT-019 (infraestructura) | CONFORME |

Las rondas de QA permitidas están agotadas (2 de 2). Cualquier corrección posterior requiere la indicación del propietario y su forma de verificación.

---

## Correcciones de QA3R2-01..03 (2026-11-20, Orquestador; sin tercera ronda de QA)

**Autorización del propietario:** «Autorizo el paso 2: corregir QA3R2-01, QA3R2-02 y QA3R2-03, cada uno con una prueba determinista de regresión que reproduzca el fallo original. […] No lances una tercera ronda completa de QA para estos defectos.» Commit base `5c17e92` (más los cambios de ENV-01..04 sin commit). Verificación acordada: pruebas deterministas que **fallan con el código de `5c17e92` y pasan con el corregido**. La revisión del diff queda a cargo del propietario. Las observaciones QA3R2-04..08 no se tocaron.

| ID | Corrección | Pruebas de regresión | Con `5c17e92` | Corregido |
|---|---|---|---|---|
| QA3R2-01 | `acceptance.py`: validación de dominio y coherencia antes de calcular (equity > 0; `len(equity) == trades + 1`; cada paso de la equity con el signo del trade; retornos > −1 y compuestos iguales al crecimiento de la equity, tolerancia relativa 1e-6; bootstrap con enteros `n_resamples ≥ 1`, `block_size ≥ 1`, `seed ≥ 0`; trades enteros en [0, 2^53]; `_finite` sin OverflowError con enteros enormes). Los fallos numéricos del cálculo y las métricas derivadas no finitas dan INCONCLUSIVE. | `test_research.py::test_qa3r2_01_invalid_or_incoherent_inputs_never_eligible` (14 casos) y `…_valid_coherent_evidence_still_eligible` (control) | 6 casos **ELIGIBLE_FOR_HUMAN_REVIEW** (equity a cero, negativa, de 1 punto, de longitud errónea, block_size 0, trades float), 3 REJECTED, 5 **excepción** (IndexError, TypeError, ValueError ×2, OverflowError) | 14/14 INCONCLUSIVE «Fail-Closed»; control ELIGIBLE |
| QA3R2-02 | `snapshot.py`: el manifiesto es el punto de confirmación. Orden: manifiesto temporal (fsync) → renombrado → `os.replace` del manifiesto. Un fallo en el proceso deshace el directorio de datos y el manifiesto temporal. Si el proceso muere, el directorio sin manifiesto no es consumible y el reintento lo aparta como `.incomplete-<id>-<marca>-<pid>` (sin borrarlo) y lo anota en el manifiesto (`incomplete_build_quarantined`; esquema 1.2.0). | `test_snapshot.py::test_qa3r2_02_failure_between_rename_and_manifest_rolls_back`; `…_killed_process_leaves_nothing_consumable_and_retry_quarantines` (subproceso terminado con `os._exit` en el punto de confirmación) | Directorio huérfano tras el fallo; reintento bloqueado («ya existe») | Sin restos tras el fallo; tras la muerte del proceso no se puede verificar ni cargar; el reintento confirma una snapshot nueva y verificable |
| QA3R2-03 | `experiments.py`: `flock` exclusivo sobre `<registro>.lock` en toda escritura; `claim_partition` comprueba y registra dentro del mismo bloqueo. `partitions.py`: `load_final` usa `claim_partition`; si otro proceso consumió primero, se deniega y se anota. La lectura fallida tras el consumo deja la partición consumida (documentado) y se anota en el registro de accesos. | `test_snapshot.py::test_qa3r2_03_two_concurrent_loaders_consume_lockbox_once` (2 procesos `spawn` con barrera en la comprobación: el intercalado de la ronda 2); `…_failed_read_keeps_partition_consumed_and_is_logged` | 3/3 ejecuciones: **los dos procesos leen el LOCKBOX** (`LEIDO, LEIDO`); lectura fallida sin anotar | 5/5 ejecuciones: uno LEIDO y otro DENEGADO; 1 consumo en el registro; 1 acceso permitido; LOCKBOX sellado |

**Ajuste de pruebas existentes (no desactivadas):** en `test_research.py`, el helper `evidence()` deriva equity y retornos de la serie de trades, y los cuatro casos de TC-ML-005 usan evidencia coherente que sigue fallando por el mismo umbral (drawdown, Profit Factor, expectancy, Sharpe). Antes combinaban una equity de 4 puntos o retornos ajenos con 40 trades, que ahora son entradas inválidas.

**Suite:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 450 passed, 5 skipped (431 + 19 nuevas). Validadores → OK.

**Riesgos residuales:** (1) `flock` exige POSIX y un sistema de archivos local: con el registro en un recurso de red (NFS/SMB) la exclusión no está garantizada. (2) Un `n_resamples` válido pero muy grande (p. ej. 10^9) no se acota: tardaría mucho, pero no da un veredicto inválido. Fijar un máximo sería un parámetro del preregistro, que no corresponde al Orquestador. (3) Si dos procesos construyen la misma snapshot a la vez, uno podría apartar el directorio del otro durante su ventana de confirmación. El resultado no es consumible como completo (faltarían archivos), pero fallaría. La construcción de snapshots es manual y única (SNAP-0001 no creada).

---

## Corrección de QA3R2-04 (2026-11-24, Orquestador; sin nueva ronda de QA)

**Autorización del propietario:** «Autorizo exclusivamente corregir QA3R2-04 de FEAT-015: validar el formato EXP-NNNN; sustituir las comprobaciones por subcadena por coincidencias exactas de experimento, snapshot y partición; añadir pruebas deterministas de regresión y verificar el comportamiento Fail-Closed.» Base `e375a18`. Sin cambios de cortes, sin SNAP-0001, sin OOS/LOCKBOX reales, sin cambio de estado de FEAT-015.

| Aspecto | Corrección |
|---|---|
| Formato del id | `create()` y `claim_partition()` exigen `EXP-NNNN` (cuatro dígitos ASCII, `fullmatch`: sin espacios ni salto de línea final). `claim_partition()` exige además partición en `{oos, lockbox}` y snapshot válida (`SNAPSHOT_ID` con `fullmatch`). Si algo es inválido, no escribe nada. Los antecedentes declarados (`ANT-MR-H1`) no cambian. |
| Cita en la decisión | `decision_ok(ref, experiment_id, partition=None, snapshot_id=None)` ya no busca subcadenas. Exige una línea completa (`fullmatch` tras quitar el espacio final), con igualdad exacta de cada campo: `AUTORIZA: EXP-NNNN` para las transiciones del propietario y `AUTORIZA: EXP-NNNN <oos|lockbox> <SNAP-…>` para una partición. Una línea de partición no autoriza la transición, ni al revés. |
| Fail-Closed | Petición mal formada (id, partición, snapshot, `decision_ref` con salto de línea) → motivo de denegación. Documento ilegible o no UTF-8 → denegado (antes se leía con `errors="replace"`). |

**Pruebas de regresión (48 nuevas):** en `test_research.py`, `test_qa3r2_04_create_rejects_malformed_experiment_id` (13), `…_transition_requires_exact_authorization_line` (11), `…_exact_line_still_authorizes` (control) y `…_unreadable_decision_fails_closed`. En `test_snapshot.py`, `test_qa3r2_04_partition_requires_exact_experiment_partition_snapshot` (10; comprueba además que no hay consumo, que el acceso denegado queda anotado y que la partición sigue sellada), `…_exact_partition_line_still_grants` (2 controles), `…_claim_rejects_malformed_ids_without_writing` (9) y `…_decision_ok_rejects_malformed_request`.

**Con `e375a18`:** 45 fallan y 3 (los controles) pasan. 43 fallos se deben a que el control concedía de más. 9 casos **abren OOS/LOCKBOX sintéticos** con una decisión que no los autoriza, entre ellos «oos» dentro de «choose», `EXP-09001`, `SNAP-TEST-2`, «NO AUTORIZA:» y «No se autoriza el lockbox». 10 casos autorizan la transición a OOS_EVALUATION, entre ellos «Se RECHAZA EXP-0101». 1 caso acepta un documento no UTF-8, 13 crean ids mal formados y 9 registran consumos con ids inválidos. Los otros 2 fallos (`AUTORIZA: exp-0101`, `LOCKBOX`) ya se denegaban en la base, y solo cambia el mensaje. **Corregido:** 48/48.

**Ajuste de pruebas existentes (no desactivadas):** los ids de prueba pasan a `EXP-NNNN` (`EXP-A`→`EXP-0101`, `EXP-T`→`EXP-0900`, `EXP-ML`→`EXP-0301`, etc.), y los documentos de decisión simulados usan la línea `AUTORIZA:`. Las aserciones no cambian.

**Suite:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 518 passed, 5 skipped (470 + 48). Validadores → OK.

**Riesgos residuales / para decisión del propietario:** (1) La línea de transición no incluye el estado destino: un mismo `AUTORIZA: EXP-NNNN` vale para OOS_EVALUATION, APPROVED y los terminales que decide el propietario desde HUMAN_REVIEW. Exigir `AUTORIZA: EXP-NNNN <ESTADO>` cerraría esa ambigüedad, pero queda fuera de lo autorizado. (2) Los ids de antecedentes no se validan; no abren particiones ni respaldan modelos. (3) `SNAPSHOT_ID.match` en `snapshot.py`/CLI admite un salto de línea final (parte de QA3R2-08, sin tocar). (4) Las decisiones reales de `docs/decisions` no usan aún la gramática; DEC-018 prohíbe evaluar OOS/LOCKBOX en IMPL-3, así que hoy no hay ninguna autorización real afectada.

---

## Corrección de QA3R2-08 (2026-11-24, Orquestador; sin nueva ronda de QA)

**Autorización del propietario:** «Autorizo corregir QA3R2-08 de FEAT-015». Base `f04a2d1`. Sin cambios de cortes, SNAP-0001, OOS/LOCKBOX reales ni contratos; FEAT-015 sigue en READY_FOR_REVIEW. El esquema del manifiesto no cambia (1.2.0).

| Parte del hallazgo | Corrección |
|---|---|
| Sellado no efectivo (root, FS sin POSIX) sin detectar | `snapshot.enforce_sealing` comprueba con `os.access(R_OK)` cada archivo sellado al construir, al verificar y al abrir un `PartitionLoader`, y emite `SealingWarning`. La construcción lo devuelve en `SnapshotResult.sealing_warnings`. `verify-snapshot` lo imprime como «AVISO de sellado» y termina con código 1. No bloquea la carga: el control principal sigue siendo la autorización en proceso. |
| SIGKILL dentro de `_read` deja 0o400 | La lectura autorizada abre el archivo y lo vuelve a sellar antes de hashear y parsear desde el contenido ya leído: la ventana con 0o400 se reduce a dos `chmod` seguidos. Además, `enforce_sealing` vuelve a sellar a 0o000 cualquier OOS/LOCKBOX con otro modo y lo avisa, sin leer su contenido. |
| `verify-snapshot --id` no valida el id | La CLI exige `SNAP-NNNN` (`fullmatch`) en ambos comandos antes de tocar nada; si no se cumple, termina con código 2. `build_snapshot` usa `valid_snapshot_id` (`fullmatch`; antes `match` admitía un salto de línea final). `load_manifest` rechaza un `snapshot_id` inválido, porque de él sale la ruta de los datos. |

**Pruebas de regresión (28 nuevas, `test_snapshot.py`):** `test_qa3r2_08_cli_rejects_malformed_snapshot_id` (18: 9 ids × 2 comandos), `…_build_rejects_snapshot_id_with_trailing_newline`, `…_manifest_with_invalid_snapshot_id_is_rejected`, `…_ineffective_sealing_is_detected_and_warned` (`os.access` simulado), `…_cli_verify_reports_ineffective_sealing`, `…_leftover_readable_mode_is_resealed` (2), `…_effective_sealing_emits_no_warning` (control), `…_kill_during_authorized_read_leaves_partition_sealed` (subproceso terminado con `os._exit` durante la lectura) y `…_authorized_read_still_verifies_hash_and_reseals` (2 controles).

**Con `f04a2d1`:** fallan 26 y pasan los 2 controles de lectura autorizada. La CLI llama a `build_snapshot`/`verify_snapshot` con los 9 ids inválidos en ambos comandos. `build_snapshot` acepta `SNAP-TEST\n`. Un manifiesto con `snapshot_id` `../../outside` se carga. Tras la muerte durante la lectura, el LOCKBOX queda en 0o400. `verify-snapshot` termina con 0 aunque el sellado no sea efectivo, y no existe aviso alguno. **Corregido:** 28/28.

**Suite:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 546 passed, 5 skipped (518 + 28). Validadores → OK.

**Riesgos residuales:** (1) Con el sellado no efectivo solo se avisa; bloquear (Fail-Closed estricto) impediría construir o usar snapshots como root y queda a decisión del propietario. (2) Entre los dos `chmod` de una lectura autorizada sigue habiendo una ventana mínima. (3) La lectura autorizada carga OOS/LOCKBOX completos en memoria (pocos MB con BTC/USDT 1d/4h/1h). (4) `SNAPSHOT_ID` sigue admitiendo `SNAP-TEST*` en la API de Python (pruebas); la CLI solo acepta `SNAP-NNNN`.

**Aprobación del propietario (2026-11-24):** cambios y 28 pruebas aprobados en su alcance actual. **Estado de QA3R2-08: CONDICIONADO**, no cerrado definitivamente hasta resolver el comportamiento ante sellado no efectivo (riesgo residual 1).

---

## QA3R2-04 — observación adicional: estado destino en la autorización de transiciones (2026-11-24, Orquestador; sin nueva ronda de QA)

**Resolución contractual (aprobada por el propietario, 2026-11-24):** corrección directa, **sin CR**. El contrato v1.7 exige que las transiciones dependan de requisitos verificables y que APPROVED y la evaluación final las decida el propietario (REQ-G-104, REQ-G-107 (4), REQ-G-P23/TC-ML-009, REQ-G-109/TC-ML-001/007/012/016, AC-017-1, AC-015-7). No fija el mecanismo de verificación (`decision_ref`, línea `AUTORIZA:`). La corrección no cambia la máquina de estados, quién decide cada transición, el catálogo de eventos, los esquemas ni `approval_ref`. El propietario mantiene el verbo AUTORIZA para todas las transiciones que decide y aprueba expresamente la gramática `AUTORIZA: EXP-NNNN ESTADO_DESTINO`. La de particiones no cambia.

**Relación con FEAT-017:** la observación surgió de QA3R2-04 (FEAT-015), pero el código afectado es el registro de experimentos de FEAT-017 (AC-017-1). FEAT-015 (AC-015-7: exige OOS_EVALUATION para abrir particiones) y FEAT-019 (promoción con APPROVED, TC-ML-009) dependen de él indirectamente. No cambian estados de FEAT, criterios de aceptación ni `feature_list.json`.

| Aspecto | Corrección (`src/swingpilot/research/experiments.py`) |
|---|---|
| Gramática | Transición: `AUTORIZA: EXP-NNNN <ESTADO>` → tupla (exp, estado, None). Partición, sin cambios: `AUTORIZA: EXP-NNNN <oos\|lockbox> <SNAP-…>`. La línea sin campos ya no autoriza nada. |
| Estados admitidos | `OWNER_DECIDED` = OOS_EVALUATION, APPROVED, REJECTED, INCONCLUSIVE: exactamente los que hoy exigen decisión del propietario (REJECTED/INCONCLUSIVE solo desde HUMAN_REVIEW, como antes). |
| API | `decision_ok(..., *, target_state=None)`: o transición (`target_state`) o partición (`partition` + `snapshot_id`), nunca ambas ni ninguna. `transition()` pasa `target_state=to`. `partitions.py` no cambia. |

**Pruebas (17 nuevas en `test_research.py`, prefijo `test_qa3r2_04b_`):** `bare_line_no_longer_authorizes` (4), `oos_authorization_is_not_reused_for_other_states` (3), `malformed_or_other_state_line_does_not_approve` (6), `owner_decision_with_its_exact_line_succeeds` (3) y `decision_ok_request_modes`. Los fixtures de `test_research.py`, `test_snapshot.py`, `test_ml_registry.py` y `test_engines.py` pasan a la línea con estado destino (dos líneas por experimento en las aprobaciones completas). Las aserciones no cambian.

**Con `c9a054b`:** fallan 8 y pasan 9. **Defecto reproducido:** los 4 casos de `bare_line_no_longer_authorizes`: la línea `AUTORIZA: EXP-0101`, sin estado, autoriza OOS_EVALUATION, APPROVED, REJECTED e INCONCLUSIVE («DID NOT RAISE»). Los otros 4 fallos (`owner_decision_with_its_exact_line_succeeds` ×3, `decision_ok_request_modes`) se deben a que la base no reconoce la gramática nueva. Los 9 que pasan son controles Fail-Closed: la base ya denegaba esas líneas porque no aceptaba un solo campo tras el id. **Corregido:** 17/17.

**Suite:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 563 passed, 5 skipped (546 + 17). Validadores → OK.

**Efecto:** cada línea autoriza un único estado destino. Como la máquina solo avanza, en la práctica sirve una vez. Las decisiones futuras del propietario que autoricen una evaluación final necesitarán dos líneas: `AUTORIZA: EXP-NNNN OOS_EVALUATION` y `AUTORIZA: EXP-NNNN <oos|lockbox> <SNAP-…>`. No hay nada que migrar: el registro real solo contiene antecedentes y ninguna decisión real usa aún la gramática.

**Aprobación del propietario (2026-11-24):** «Apruebo la corrección; autorizo commit en develop, sin push.» Observación adicional de QA3R2-04 cerrada.
