# IMPL-3 — QA independiente, ronda 1 (FEAT-015, FEAT-016, FEAT-017 infraestructura, FEAT-019 infraestructura)

**Fecha:** 2026-11-20
**Revisor:** QA Agent independiente: sub-agente de solo lectura, sin acceso a la conversación de implementación, sin red, sin API de Anthropic de SwingPilot (~193K tokens del sub-agente; presupuesto de IA de IMPL-3: $0 consumido).
**Reproducciones:** `/tmp/claude-1000/qa-impl3/` (fuera del repositorio; temporales).
**Verificación del Orquestador:** QA3-01, 02, 03, 05 y 06 reejecutados el 2026-11-20 con el mismo resultado. Los demás se aceptan por la evidencia del QA.
**Estado:** hallazgos ABIERTOS. No se aplicó ninguna corrección (instrucción del propietario: entregar hallazgos y correcciones necesarias, sin ampliar el alcance).

pytest (QA): `.venv/bin/pytest -q -p no:cacheprovider tests` → 325 passed, 5 skipped. **Las pruebas no detectan ninguno de los hallazgos.**

## Hallazgos

| ID | Sev. | FEAT / AC | Archivo | Hallazgo | Evidencia | Corrección necesaria |
|---|---|---|---|---|---|---|
| QA3-01 | MAYOR | 016 / AC-016-4, -5 | `market_data/stream.py`, `live.py` | Tras `GAP_DETECTED`, `CONFLICT` o una resync inicial fallida, `run_stream` no vuelve a resincronizar hasta que se cae la conexión. El feed queda en `RESYNC_REQUIRED` indefinidamente (Fail-Closed sin recuperación) y `_held` crece sin límite. | Confirmado: hueco a mitad del stream → 1 resync, estado RESYNC_REQUIRED, 57 velas en espera. REST caído al conectar → 100 en espera. | Reintentar `resync` en el bucle con backoff mientras `state != SYNCED`. Usar `report.ok`. Acotar `_held`. Pruebas de ambos casos. |
| QA3-02 | MAYOR | 015 / AC-015-3, -4; TC-ML-017 | `binance_public.py`, `research/snapshot.py` | Una página corta se interpreta como fin de datos, y la rejilla de cada intervalo va de su primera a su última vela presente, no del rango común. Una descarga truncada se sella como snapshot válida, sin huecos contados. | Confirmado: 300 velas 1h en la 1.ª página → 1h solo en train_val, OOS/LOCKBOX 1h vacíos, `gaps_total.1h = 0`, sin error. | Rejilla 1h/4h sobre `[range_start, range_end)`, con el primer día parcial real declarado aparte. Fallar si un intervalo no llega a `range_end`. En `klines_range`, verificar que se alcanzó `end`. |
| QA3-03 | MAYOR | 017 / AC-017-1; 015 / AC-015-7; 019 / AC-019-2 | `research/experiments.py`, `partitions.py`, `ml/registry.py` | `register_antecedent` acepta cualquier estado. Un antecedente creado en `OOS_EVALUATION` o `APPROVED` elude el ciclo de vida y la decisión del propietario: abre OOS/LOCKBOX y permite promover modelos. | Confirmado: lectura de lockbox y oos (1860 filas) y promoción a ACTIVE. | Limitar los estados de antecedente a `PENDING_DOCUMENTATION`, `REJECTED` e `INCONCLUSIVE`. Los consumidores exigen `origin == REGISTRY`. |
| QA3-04 | MAYOR | 015 / AC-015-7; 017 / AC-017-1 | `partitions.py`, `experiments.py` | La «decisión existente» se valida solo por nombre de archivo, en un `decisions_dir` que pasa quien llama; «propietario» es una cadena libre. | Confirmado: un `DEC-005_x.md` cualquiera en un directorio ad hoc autoriza cargar OOS. | Fijar `decisions_dir` a `docs/decisions`. Exigir que la decisión cite experimento, partición y snapshot. Documentar que es un control en proceso, no criptográfico. |
| QA3-05 | MAYOR | 017 / AC-017-8; TC-ML-004..006 | `research/acceptance.py` | El evaluador falla en abierto con NaN (`nan < umbral` es False). | Confirmado: drawdown, Sharpe o DSR NaN, o NaN en `oos_net_r` → `ELIGIBLE_FOR_HUMAN_REVIEW` sin motivos. | Rechazar entradas no finitas: INCONCLUSIVE o error, con prueba. |
| QA3-06 | MENOR | 015 / AC-015-7 | `snapshot.py`, `partitions.py` | Hay vías a OOS/LOCKBOX fuera del control: `verify_snapshot(partitions=("oos","lockbox"))` no registra el acceso, `pq.read_table` directo funciona, y si se borra el log de accesos se pierde el «consumido». | Confirmado (reejecutado). | Registrar o prohibir esas particiones en `verify_snapshot`. Persistir el consumo en un registro versionado, no solo en el log. |
| QA3-07 | MENOR | 017 / AC-017-8 | `acceptance.py` | El evaluador confía en conteos y en el DSR declarados, sin contrastarlos con `oos_net_r` ni con el registro. | Confirmado: `oos=500` declarado con 7 valores → ELIGIBLE. | Calcular el DSR internamente con `registry.trials_count()`. Comprobar la coherencia de conteos. |
| QA3-08 | MENOR | 016 / AC-016-4 | `store.py`, `stream.py`, `live.py` | `check_same_thread=False` sin lock. En `run_stream` el acceso es secuencial (0 solapes), pero el uso concurrente corrompe: errores y 2728 de 3000 filas. Si se cancela durante `to_thread(resync)`, el hilo huérfano deja `SYNCED`. | Confirmado por el QA. | `threading.Lock` en `CandleStore` y `LiveFeed`. Ante `CancelledError`, llamar a `on_disconnect`. |
| QA3-09 | MENOR | 015 / AC-015-4 | `snapshot.py` | `gaps_total` se calcula antes del recorte a `range_end`. | Confirmado: total 1, por partición 0. | Calcularlo tras el recorte. |
| QA3-10 | MENOR | 015 / AC-015-3 | `snapshot.py` | El corte en coma flotante desplaza `val_end` un día en 114 de 4940 longitudes probadas. | Confirmado por el QA. | Aritmética entera. |
| QA3-11 | MENOR | 017 / AC-017-7; TC-ML-002 | `backtest.py` | La lógica de estrategia recibe el DataFrame completo, con barras futuras visibles. | Confirmado: una estrategia tramposa opera con `iloc[i+1]`. | Pasar `bars.iloc[:i+1]`. Prueba de perturbación del futuro. |
| QA3-12 | MENOR | 017 / AC-017-6; REQ-G-142 | `backtest.py` | El slippage está dentro de `gross_r`, así que el «bruto» no es bruto. Las señales no se validan: un TP bajo la entrada sale de inmediato y un stop NaN deja la posición sin stop. | Confirmado por el QA. | Separar el slippage como costo. Validar stop finito y menor que la entrada, y TP mayor que la entrada. |
| QA3-13 | MENOR | 017 / AC-017-7, -3 | `scaling.py`, `preregistration.py` | `fit` comprueba solo la etiqueta «train», no los datos. `mark_oos_seen` es manual. | Confirmado por el QA. | Validar por fecha de corte. Derivar `oos_seen` del registro de accesos. |
| QA3-14 | MENOR | 019 / AC-019-3; P22 | `ml/registry.py` | La degradación falla en abierto con NaN. | Confirmado: IC NaN con media −5 R → no suspende. | Suspender ante valores no finitos. |
| QA3-15 | MENOR | 015 / AC-015-5; TC-ML-019 | `snapshot.py`, `cli.py` | Un fallo a medias deja el directorio huérfano y bloquea el reintento. `check_new_lockbox` no está conectado en la CLI. `--id` no se sanea. | Confirmado por el QA. | Escribir en directorio temporal y renombrar. Cargar los LOCKBOX consumidos desde un registro. Validar el id. |
| QA3-16 | MENOR | 016 / AC-016-1 | `candles.py`, `live.py` | `bool("false")` es True. Un JSON que no es objeto lanza `AttributeError`. `events` crece sin límite. | Confirmado por el QA. | Exigir `x is True` y un dict. Acotar `events`. |
| QA3-17 | OBS. | 017 | `indicators.py` | `expanding_percentile_rank` es O(n²) (~1 min para ~80k velas). | Medido por el QA. | Estructura incremental. |
| QA3-18 | OBS. | 016 / 019 | `live.py`, `ml/registry.py` | Si Binance no tiene una vela, el Fail-Closed es permanente; no hay política contractual (PENDING). `data_hash`/`code_hash` son cadenas libres. | Por lectura. | Registrar la política como pendiente. Validar el formato SHA-256. |
| QA3-19 | OBS. | Pruebas | `tests/unit/test_snapshot.py`, `test_research.py` | Pruebas débiles: las proporciones se comprueban como 70/15/15 y no 50/20; no hay pruebas de stream con hueco ni de resync fallida; una aserción del embargo repite el código; el escalado solo mira la etiqueta; el evaluador comprueba el resultado y no la razón. | Por lectura. | Pruebas que cubran QA3-01, 02, 05, 10 y 13. |

Conforme según la QA: indicadores sin look-ahead (0 discrepancias de truncado, con huecos), orden del backtest (trailing desde la vela siguiente, stop primero, hueco y TP, pisos de comisión y slippage), el evaluador nunca devuelve APPROVED, la paginación sin bucles, el hash canónico del preregistro, y los SHA-256 por archivo con chmod y versiones.

## Veredictos

| Prioridad del propietario | Veredicto |
|---|---|
| 1. Integridad de datos | NO CONFORME (QA3-02; QA3-09, 10) |
| 2. Recuperación WebSocket | NO CONFORME (QA3-01) |
| 3. Concurrencia SQLite | CONFORME CON OBSERVACIONES (QA3-08) |
| 4. Ausencia de look-ahead | CONFORME CON OBSERVACIONES (QA3-11, 13) |
| 5. Protección OOS/LOCKBOX | NO CONFORME (QA3-03, 04; QA3-06) |
| 6. Trazabilidad de hashes | CONFORME CON OBSERVACIONES (QA3-06, 15, 18) |

| FEAT | Veredicto QA |
|---|---|
| FEAT-015 | NO CONFORME (QA3-02, 03, 04) |
| FEAT-016 | NO CONFORME (QA3-01) |
| FEAT-017 (infraestructura) | NO CONFORME (QA3-03, 05; relacionados 04, 07) |
| FEAT-019 (infraestructura) | CONFORME CON OBSERVACIONES (depende de QA3-03; QA3-14) |

## Siguiente paso propuesto

Corregir QA3-01..05 (MAYOR) y los MENOR, con una prueba por hallazgo, y después la ronda 2 de QA, que es la última (≤ 2 rondas, mismo criterio que IMPL-2). Requiere indicación del propietario.

## Correcciones aplicadas (2026-11-20, autorizadas por el propietario: «Autorizo corregir QA3-01..19 y lanzar la QA ronda 2»)

| ID | Corrección | Prueba nueva o reforzada |
|---|---|---|
| QA3-01 | `run_stream` reintenta la resync dentro de la conexión mientras el feed no esté SYNCED, con espera exponencial (`resync_backoff_s`, máx. `resync_backoff_max_s`), usando `report.ok`. Cola de velas en espera acotada (`max_held`, descarta las más antiguas, que la resync REST recupera). | `test_qa3_01_gap_mid_stream_triggers_resync_without_reconnect`, `test_qa3_01_failed_initial_resync_is_retried_with_backoff`, `test_qa3_01_held_queue_is_bounded` |
| QA3-02 | `klines_range(require_end=True)` falla si la última vela no es la de `end`. La snapshot exige descarga completa por intervalo, primera vela dentro del primer día (inicio de cotización declarado en `listing_start`, no como hueco) y datos hasta `range_end`; la rejilla cubre hasta `range_end`. | `test_qa3_02_*` (3 en snapshot, 1 en market_data), `test_first_partial_day_is_declared_not_counted_as_gap` |
| QA3-03 | Antecedentes solo en PENDING_DOCUMENTATION, REJECTED o INCONCLUSIVE. `eligible_state()` (None para antecedentes) lo usan `PartitionLoader`, `ModelRegistry.register` y `ModelRegistry.promote`. | `test_qa3_03_*` (snapshot, research, ml) |
| QA3-04 | `decision_ref`: nombre `DEC-NNN…md` sin ruta, dentro de `docs/decisions` (directorio por defecto del registro; sustituible solo en pruebas), sin enlaces simbólicos, y el texto debe citar experimento (y partición y snapshot para OOS/LOCKBOX). Documentado como control en proceso, no criptográfico. | `test_qa3_04_*` (3) |
| QA3-05 | El evaluador devuelve INCONCLUSIVE ante cualquier entrada no finita, vacía o fuera de dominio. | `test_qa3_05_non_finite_inputs_fail_closed` (6 casos) |
| QA3-06 | `oos`/`lockbox` escritos con permisos 0o000 (solo el cargador los abre temporalmente con autorización). `verify_snapshot` solo verifica `train_val`. El consumo se registra en el registro de experimentos versionado (`PARTITION_CONSUMED`) antes de leer. | `test_qa3_06_*` (2), `test_tc_ml_007_019_lockbox_single_use_persisted_in_registry` |
| QA3-07 | El evaluador calcula Sharpe, drawdown y DSR desde las series; el número de pruebas sale de `registry.trials_count()`; el conteo OOS declarado debe coincidir con la serie. | `test_qa3_07_*`, `test_tc_ml_006_*` (DSR con 10 000 pruebas) |
| QA3-08 | `RLock` en `CandleStore` y `LiveFeed`; la resync hace la red sin el lock; generación por desconexión (una resync huérfana no deja SYNCED); `CancelledError` → `on_disconnect`. | `test_qa3_08_*` (3) |
| QA3-09 | `gaps_total` = suma por partición tras el recorte. | `test_tc_ml_017_gaps_are_nan_and_counted_consistently` |
| QA3-10 | Cortes en aritmética entera. | `test_qa3_10_integer_cuts` (6 longitudes); reproducción del QA: 0 diferencias |
| QA3-11 | La lógica recibe `bars.iloc[:i+1]`. | `test_qa3_11_strategy_only_sees_past_and_future_perturbation_is_irrelevant` |
| QA3-12 | Bruto con precios de referencia; `slippage_r` y `commission_r` separados; señales inválidas descartadas y contadas. | `test_tc_ml_018_a_*`, `test_qa3_12_invalid_signals_are_rejected` (5 casos) |
| QA3-13 | `TrainOnlyScaler.fit` exige columna temporal y que todas las filas sean anteriores al corte de Train. La desviación «tras OOS» se deriva del registro de accesos. | `test_tc_ml_003_*`, `test_tc_ml_013_deviation_after_oos_derived_from_access_log` |
| QA3-14 | La degradación suspende ante valores no finitos. | `test_qa3_14_non_finite_inputs_suspend` (4 casos) |
| QA3-15 | Escritura en directorio temporal y renombrado; limpieza ante fallo; `snapshot_id` validado; la CLI pasa los LOCKBOX consumidos del registro. | `test_qa3_15_*` (2), `test_cli_reads_consumed_lockboxes_from_registry` |
| QA3-16 | Mensaje debe ser objeto; `x` booleano; `x=true` antes del cierre según `E` se rechaza; `events` acotado. | `test_qa3_16_*` (4) |
| QA3-17 | Percentil incremental con bisect. | `test_expanding_percentile_rank_values_and_speed` (80k < 5 s; medido < 0.1 s) |
| QA3-18 | Hashes de modelo validados como SHA-256. Política ante vela ausente en Binance: documentada como PENDING (decisión del propietario) en `live.py`. | `test_qa3_18_hashes_must_be_sha256` (4 casos) |
| QA3-19 | Pruebas reforzadas: proporciones 50/20/15/15 por días, primer día parcial, stream con hueco y resync fallida, fechas WF escritas a mano y velas de entrenamiento fuera del embargo, escalado por datos, motivos del evaluador. | ver las filas anteriores |

Resultado: `.venv/bin/pytest -q -p no:cacheprovider tests` → **390 passed, 5 skipped** (antes 325 passed). Reproducciones del QA reejecutadas: QA3-08 (0 errores, 3000 filas), QA3-10 (0 diferencias), QA3-16 (todos REJECTED), QA3-17 (40k filas en 0.09 s), QA3-11 (la lógica tramposa recibe IndexError). r1_stream sigue en RESYNC_REQUIRED con un servidor simulado que nunca da por cerradas las velas que el stream entrega, y con un backoff de 5 s de reloj real en un guion de milisegundos; el reintento ocurre (2 resyncs) y queda espaciado por diseño. Lo cubren las pruebas con reloj inyectado.
