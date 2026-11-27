# CR-023 — Particiones de evaluación prospectivas y frontera de independencia verificable (D3)

**Fecha:** 2026-11-25
**Estado:** **APROBADA** por el propietario el 2026-11-25 (**DEC-025**) y **APLICADA contractualmente** al contrato **v1.11** (REQ-G-101, REQ-G-103, REQ-G-104, REQ-G-106, REQ-G-109, REQ-G-P10, REQ-G-P15, REQ-G-P23; `api_contracts.md` §B.0.4 y §B.7; `data_flow.md` §3; TC-ML-009, 014, 015, 016, 019 y TC-ML-025..028; cabeceras de versión) y a `feature_list.json` v1.23.0. **Implementación y verificación independiente PENDIENTES** (§H, §I). Antes: PROPUESTA, revisiones 1 y 2 y revisión final focalizada (2026-11-25).
**Origen:** diagnóstico D3 de solo lectura sobre `aca408e` (2026-11-25); decisiones del propietario D3.1–D3.8, P1–P8, R1–R5, U1–U2, F1–F4 y correcciones C1–C2 (2026-11-25).
**Vinculada a:** DEC-005 Q7, DEC-011/CR-011, DEC-013/CR-013, DEC-018 decisión 4, CR-018/DEC-019 (`api_contracts.md` §B.7), CR-020 (DEC-021), CR-021 (DEC-023), CR-022 (DEC-024). Las decisiones históricas no se reescriben; sus notas de vigencia constan en DEC-025.
**Alcance:** metodología de partición e independencia de las particiones de evaluación, y elegibilidad confirmatoria en la promoción y el uso operativo. No fija fechas reales (D4), no decide la secuencia de exploración (D5), no fija parámetros ni umbrales estadísticos (D6) ni la configuración del piloto (D7). No cambia la contabilidad (CR-020), la durabilidad y la conciliación (CR-021) ni la relevancia por par exacto (CR-022).
**Estado de la revisión FEAT-017 al aplicar:** D1, D2 y D8 cerradas; **D3 ABIERTA** (condiciones de cierre en §L); D4 bloqueada; D5–D7 sin iniciar. CONF-009 RESOLVED (reevaluación obligatoria antes del cierre de FEAT-017); CONF-010 OPEN. FEAT-015 reabierta de forma focalizada (§G); FEAT-017, FEAT-019 y FEAT-020 IN_PROGRESS.
**Notación:** «P1–P8 (D3)» son disposiciones de esta CR; «P5 de CR-021» es el procedimiento de conciliación manual pendiente de CR-021 §F.2. Son cosas distintas. «ET-n» son etapas del ciclo (§C.9), no eventos E1–E8 de `data_flow.md`.

---

## A. Problema y evidencia

1. **Regla anterior.** REQ-G-P10, DEC-005 Q7 y REQ-G-109 (v1.10) fijaban cortes 50/20/15/15 por porcentaje desde 2017-08-17 hasta la fecha de la snapshot (`snapshot.py`: `SPLIT_PCT`, `compute_cuts`).
2. **Exposición previa** (`harness/verification/IMPL-3_EXP-0001_procedencia.md` §2–§4): **documentada**, 2023-05-01 → 2025-11-08T19:00Z (Fase 0 de Mean Reversion H1; diseño y congelación de EXP-0001); **incierta**, 2025-11-08T20:00Z → 2026-10-31 (LOCKBOX_OOS_001 de `trading-bot`, «no plenamente ciego» según su D-009; estado posterior a 2026-11-09 no verificable); **desconocida**, antes de 2023-05-01 y el periodo de la fixture de calibración de IMPL-2 (congelada con SHA-256 el 2026-11-19; no inspeccionada).
3. **Consecuencia.** Con cualquier snapshot verosímil a finales de 2026, la OOS caía al 100 % en exposición documentada y el LOCKBOX en ≈95 % en exposición documentada o incierta: incumplimiento sustantivo de REQ-G-101 e imposibilidad de satisfacer REQ-G-108. Sin cambio contractual, una OOS posterior a toda exposición conocida exigía un fin de snapshot ≥ 2030-10-13.
4. **Vacíos.** REQ-G-103 solo preveía limitaciones por histórico insuficiente, no por contaminación; `check_new_lockbox` solo ve consumos nativos (riesgo residual aceptado en QA3R2-07).
5. **Circularidad preexistente en v1.10.** Congelar exige una tasa observada «solo con Train» y el histórico mínimo (`preregistration.py:672-674`); evaluar una configuración sobre `train_val` solo se admite en DEVELOPMENT o VALIDATION, después de congelar (`experiments.py:142`, CR-020). Ningún experimento podía obtener la tasa que necesita para congelarse.

## B. Decisiones del propietario (2026-11-25)

### B.1 Decisiones metodológicas D3.1–D3.8

| ID | Decisión |
|---|---|
| D3.1 | Opción C2: OOS y LOCKBOX prospectivas tras una frontera de independencia verificable. Se sustituye la asignación 50/20/15/15. Ninguna fecha (2026-11-01, la fecha actual u otra) se trata automáticamente como frontera |
| D3.2 | La independencia exige evidencia positiva o aislamiento prospectivo verificable. La ausencia de exposición documentada no es evidencia. La recolección prospectiva no basta si los datos informan el desarrollo, la selección de parámetros o decisiones experimentales |
| D3.3 | Las restricciones de exposición se aplican a todas las hipótesis BTC/USDT de SwingPilot, coherentes con la población de CR-020 |
| D3.4 | La familiaridad general con la historia de BTC es una limitación declarada, distinta de la exposición material que influye en el diseño, la selección o la calibración |
| D3.5 | LOCKBOX_OOS_001 es exposición incierta, excluida de la evaluación confirmatoria; no se afirma consumo ni pristinidad |
| D3.6 | La inspección de la fixture de IMPL-2 queda diferida; relevancia desconocida; no se clasifica como inocua |
| D3.7 | No se reabre la investigación anterior a 2023; la incertidumbre se conserva y el histórico sirve para desarrollo |
| D3.8 | Exposición externa registrada en el preregistro y con evidencia versionada; sin tipo de evento nuevo; las alternativas mínimas se someten a aprobación separada |

### B.2 Disposiciones P1–P8 (D3)

| # | Disposición |
|---|---|
| P1 | Train:Validation = 5:2 dentro de la región de desarrollo |
| P2 | Solo ventanas de calendario fijas; sin ampliación, recorte ni parada anticipada por rendimiento o número de operaciones; operaciones insuficientes ⇒ INCONCLUSIVE |
| P3 | Un único experimento confirmatorio por frontera; sus configuraciones planificadas se rigen por CR-020 |
| P4 | ≥ 24 h entre la publicación y `B`, con `B` a las 00:00 UTC; sin servicio externo de sellado de tiempo; la publicación en Git es evidencia operativa, no sellado de tiempo certificado |
| P5 (D3) | Cierre forzoso al cierre de la última vela cerrada de la ventana, con comisión y slippage |
| P6 | Una snapshot de evaluación por ventana, sellada y autorizada de forma independiente |
| P7 | Reapertura focalizada de FEAT-015 al entrar en vigor (§G) |
| P8 | Registro mediante el `DEVIATION` existente con semántica de independencia y alcance sobre las hipótesis BTC/USDT afectadas |

### B.3 Correcciones y disposiciones de revisión

| ID | Resolución |
|---|---|
| R1 | Cinco niveles de integridad (§C.2); experimento exploratorio de estimación de tasa (§C.3); AC-017-10 se desbloquea con I1 + I2; la verificación de ventanas es posterior y específica del experimento |
| R2 | Sin puente dentro de `train_val`; snapshots de evaluación con `context` sellado; los cargadores de desarrollo rechazan snapshots de evaluación (§C.1, §C.6) |
| R3 | Congelación completa antes de `B` (§C.5) |
| R4 | `DEVIATION` de independencia y función común `independence_status` (§D) |
| R5 | D3 no se cierra solo documentalmente (§L) |
| U1 | Enmienda de REQ-G-P23: elegibilidad recalculada antes de la promoción y del uso operativo; registros APPROVED históricos conservados; la pérdida de elegibilidad bloquea el uso sin impedir la gestión protectora ni el cierre (§D.8) |
| U2 | Almacén recuperable de preregistros dentro de CR-023; O4 sigue siendo una obligación independiente (§C.4.1) |
| F1 | Lista única V1–V8 (§C.9) |
| F2 | Alcance de la contaminación por periodo; el dueño queda afectado en cualquier estado; momento de la exposición distinto del momento del registro (§D.3) |
| F3 | Matriz de requisitos por etapa ET-1..ET-10 (§C.9) |
| F4 | Digest canónico de contenido y continuidad del contexto del LOCKBOX (§C.6.5) |
| C1 | V4 depende de la etapa: V4-pre antes del consumo, V4-post después (§C.9) |
| C2 | Ineligibilidad metodológica (`NO_SETUP`, `NO_APPROVED_STRATEGY`) distinta del fallo técnico (`ERROR`, `ELIGIBILITY_UNDETERMINED`); ambos bloquean entradas nuevas; protección y cierre siempre disponibles (§D.8) |

## C. Modelo metodológico

### C.1 Regiones, snapshots y archivos

| Elemento | Contenido | Archivo y snapshot | Acceso |
|---|---|---|---|
| Región de desarrollo | 2017-08-17 → `D_dev` (exclusivo; D4) | `train_val.parquet` de la **snapshot de desarrollo** (`kind: development`) | Cargadores de desarrollo; Train = primeros 5/7 y Validation = últimos 2/7 por fecha (P1), idénticos para 1d, 4h y 1h |
| Tramo puente | `[D_dev, B)` | Solo dentro del `context.parquet` de la snapshot de evaluación de la OOS | Nunca en desarrollo |
| Ventana OOS | `[B, B + L_oos)` | `oos.parquet` + `context.parquet` (`[D_dev, B)`) de la snapshot de evaluación de la OOS (`kind: evaluation`, `window_id = <experiment_id>/OOS`) | Evaluación final única |
| Ventana LOCKBOX | `[B + L_oos, B + L_oos + L_lb)` | `lockbox.parquet` + `context.parquet` (`[D_dev, B + L_oos)`) de la snapshot de evaluación del LOCKBOX (`window_id = <experiment_id>/LOCKBOX`) | Evaluación final de un solo uso, posterior al consumo de la OOS |

La snapshot de desarrollo no tiene `oos` ni `lockbox`; las snapshots de evaluación no tienen `train_val`. Las características de una ventana pueden leer el `train_val` de la snapshot de desarrollo referenciada (hash en el manifiesto) y el `context` de su propia snapshot de evaluación; nunca datos posteriores a su ventana. El primer `open_time` del `context` es igual a `D_dev` (comprobación mecánica).

### C.2 Niveles de integridad

| Nivel | Qué acredita | Cuándo | Condiciona |
|---|---|---|---|
| I1 — Integridad metodológica del diseño de particiones | Contrato, implementación y verificación de CR-023 | Cierre de D3 (§L) | D4, AC-017-10 |
| I2 — Integridad física de la snapshot de desarrollo | SHA-256, sellado, manifiesto, ausencia de ventanas reservadas | D4 | AC-017-10; todo acceso a `train_val` |
| I3 — Evaluaciones exploratorias autorizadas y contabilizadas | Piloto de tasa solo en Train, registrado según CR-020 y CR-021 | Tras I1, I2, AC-017-10, O3 y O4 | El preregistro confirmatorio |
| I4 — Preregistro confirmatorio y congelación del diseño | Diseño completo (C.5), declaración de frontera, `B` | Antes de `B` | Las ventanas |
| I5 — Verificación real de las particiones futuras | Comprobaciones V aplicables a cada etapa (C.9) | ET-4..ET-10, por experimento | Construcción, autorización, consumo, evaluación, revisión, promoción y uso |

Secuencia habilitada (el orden concreto de exploración corresponde a D5): cierre de D3 (I1) → D4: snapshot de desarrollo (I2) → piloto de tasa (I3) → preregistro confirmatorio congelado y declaración de frontera publicada (I4) → `B` → ventanas → snapshots de evaluación, autorizaciones y consumos (I5). El preregistro confirmatorio nunca exige información que solo se obtiene después de congelarlo. El cierre de D3 no exige particiones prospectivas.

### C.3 Experimento exploratorio de estimación de tasa

1. Experimento ordinario (mismos 12 estados; sin estados ni tipos de registro nuevos) cuyo preregistro declara `independence_boundary = {"confirmatory_eligible": false, "purpose": "TRADE_RATE_PILOT", "access_scope": "TRAIN_ONLY"}`.
2. Exento del cálculo de histórico mínimo con `r` (es lo que estima); el resto de su congelación sigue REQ-G-103, incluida la contabilidad de CR-020.
3. Solo accede a la porción Train de la snapshot de desarrollo; el cargador no le entrega Validation, ninguna snapshot de evaluación ni `FinalEvaluationGrant`.
4. `confirmatory_status` siempre no confirmatorio; no transita a OOS_EVALUATION; termina en REJECTED o INCONCLUSIVE por decisión del propietario.
5. Sus pares evaluados cuentan según CR-020 en la población BTC/USDT y entran en el `N_pre` del experimento confirmatorio posterior.
6. Su tasa `r` (por configuración y agregada), con referencia al experimento, es la `trade_rate_source` del preregistro confirmatorio.
7. Su uso, configuraciones y orden corresponden a D5; CR-023 solo lo hace posible.

### C.4 Frontera prospectiva de independencia `B`

**C.4.1 Almacén recuperable de preregistros (U2).**
1. **Ruta y contenido:** `research/preregistrations/<experiment_id>/<sha256>.json`, con los **bytes exactos** sobre los que se calculó el SHA-256 registrado en PREREGISTERED; versionado en Git.
2. **Orden de escritura:** creación exclusiva (sin sobrescritura) → `fsync` → comprobación SHA-256(bytes) = nombre → registro PREREGISTERED. Un archivo sin PREREGISTERED que lo cite es huérfano: se conserva como evidencia y no tiene autoridad.
3. **Sin sustitución silenciosa:** el nombre es el hash; cada lectura recalcula el SHA-256 y lo compara con el nombre y con PREREGISTERED. Un archivo con contenido distinto de su nombre, la falta del archivo citado o dos contenidos distintos para el mismo PREREGISTERED son un fallo técnico de evidencia (`independence_status` INDETERMINATE; Fail-Closed). Sin reparación automática.
4. **Preservación:** ningún archivo se modifica ni se borra; la historia de Git conserva la evidencia, con la misma limitación de autenticidad que N-3 (sin tamper-evidence).
5. **O4:** el almacén es el mecanismo exigido por C.4 y C.5. **Implementarlo no satisface O4**, que sigue siendo una obligación independiente con evidencia propia, verificación independiente y aceptación expresa del propietario.

**C.4.2 Condiciones de validez** (todas obligatorias; si falta alguna, Fail-Closed):
1. El experimento confirmatorio está en PREREGISTERED y su contenido es recuperable (C.4.1).
2. Una declaración de frontera en `docs/decisions` cita ese SHA-256 y está confirmada en un commit publicado en `origin`. `B` es un instante a las 00:00 UTC al menos 24 h posterior a la publicación (P4). La publicación es evidencia operativa (§K-R1).
3. `D_dev < B`; `B` es posterior al fin de toda exposición documentada o incierta inventariada (LOCKBOX_OOS_001: 2026-10-31; fixture de IMPL-2: congelada el 2026-11-19) y al fin de toda ventana anterior reservada, consumida o contaminada. Que `B` sea posterior no convierte esos periodos en independientes.
4. Un experimento por frontera (P3): ningún otro preregistro congelado reserva ventanas que se solapen (comprobación mecánica sobre el almacén).
5. Inventario de exposición en el preregistro: periodos documentados, inciertos y desconocidos con referencias `repo@commit:ruta`; limitación D3.4; fixture de IMPL-2 desconocida; identificadores de todos los `DEVIATION` de independencia existentes; ámbito BTC/USDT.

### C.5 Congelación completa del diseño antes de `B`

Los valores se fijan en el preregistro con aprobación del propietario; esta CR **no** los define (D6, D7).

| Elemento obligatorio | Campo del preregistro |
|---|---|
| Hipótesis principal y nula, pregunta, justificación, universo, temporalidades | `research_question`, `hypothesis`, `null_hypothesis`, `justification`, `universe`, `timeframes` |
| Configuraciones planificadas | `trials_count` / `trials_accounting.planned_config_ids` (CR-020) |
| Versiones de estrategia y configuración | `model_config` con identificador y SHA-256 del código de estrategia y de cada configuración |
| Regla de selección de la candidata | `candidate_selection_rule` |
| Modelo de ejecución y costes | `execution_model`, `costs` |
| Umbrales de aceptación y rechazo | `acceptance_criteria`, `rejection_criteria` |
| Métricas y métodos estadísticos | `metrics`, `statistical_tests`, `sharpe_definition` |
| Reglas de selección y promoción | `candidate_selection_rule`; referencia a REQ-G-P23 |
| Parámetros de régimen y versiones de modelos que condicionan la estrategia | `conditioning_components` (versión y SHA-256, o declaración de que no se usa ninguno) |
| Ventanas, regla de parada, posiciones abiertas | `independence_boundary`: `B`, `L_oos`, `L_lb`, `k`, regla de calendario, regla P5 (D3) |
| Walk-Forward, horizonte de etiquetas, snapshot de desarrollo, tasa y fuente | `wf_design`, `label_horizon_months`, `snapshot`, `observed_trade_rate_per_month`, `trade_rate_source` |

**Regla endurecida:** en un experimento con `independence_boundary.confirmatory_eligible = true`, un `DEVIATION` de **cualquier** campo posterior a PREREGISTERED lo hace no confirmatorio, haya o no consumo. Fuera de esos experimentos se conserva la regla vigente (DESIGN_FIELDS tras la exposición). La nueva información sobre exposición anterior a `B` se documenta en `docs/decisions` y se evalúa en V7.

### C.6 Etapas de las particiones prospectivas

1. **Recolección.** SwingPilot no acumula datos de las ventanas: existen en el histórico público de Binance. Cada snapshot de evaluación se descarga **una vez, después del cierre** de su ventana (solo velas cerradas). El constructor exige el preregistro congelado y recuperable con la ventana solicitada, la confirmación del propietario (`--confirm`) y, para el LOCKBOX, la OOS del mismo experimento consumida y la continuidad de C.6.5. No calcula señales ni resultados.
2. **Sellado.** SHA-256 por archivo; inmutabilidad; `context` y `oos`/`lockbox` con permisos 0o000; comprobación del sellado efectivo (QA3R2-08); manifiesto versionado con `kind`, `window_id`, límites, `D_dev`, referencia a la snapshot de desarrollo (id y hashes), digests canónicos (C.6.5) y versiones de librerías.
3. **Autorización.** `FinalEvaluationGrant` por ventana y experimento, con `decision_ref` a un documento del propietario con la atestación de V1, V6 y V7; el resto de las comprobaciones de ET-5 se verifican de forma mecánica (C.9). La autorización no implica consumo.
4. **Consumo.** `PARTITION_CONSUMED` antes de leer (mecanismo vigente). El `context` se lee solo junto con su partición, bajo la misma autorización y el mismo consumo. Sin reevaluación (TC-ML-007, TC-ML-012). Un LOCKBOX consumido no se reutiliza (REQ-G-109).
5. **Continuidad del contexto del LOCKBOX (F4).**
   - En ET-4 se calcula en memoria, antes de sellar y sin generar resultados, un **digest canónico de contenido** por archivo e intervalo: SHA-256 de las filas ordenadas por (`interval`, `open_time`), serializando `interval`, `open_time`, `close_time`, `open`, `high`, `low`, `close` y `volume` con los números en IEEE-754 binary64 big-endian y un único NaN canónico. Se guarda en el manifiesto con el número de filas y de huecos, para el `context` y para la partición.
   - Al construir la snapshot del LOCKBOX, sus filas de contexto en `[D_dev, B)` y en `[B, B + L_oos)` deben producir exactamente los digests, filas y huecos registrados en el manifiesto de la snapshot de la OOS (su `context` y su `oos`, respectivamente). La comparación usa solo el manifiesto versionado de la OOS: **no se abre `oos.parquet`, no se emite autorización para la OOS y no se calcula ningún resultado.**
   - Discrepancia: la construcción se aborta con el rollback vigente (ningún archivo sellado), se documenta en `docs/decisions` y la evaluación del LOCKBOX queda bloqueada. Solo se admite repetir la descarga con el mismo procedimiento (comprobación de integridad, independiente de resultados). El `oos` sellado no puede sustituir al contexto. Si persiste, decide el propietario (por ejemplo, INCONCLUSIVE).
   - ET-5 y ET-6 vuelven a comprobar los digests registrados (V5).
   - Se conservan el uso único, el sellado, el consumo y la prohibición de generar resultados a partir del contexto.

**Separación verificable entre desarrollo y contexto:** los cargadores de desarrollo (`load_train_val_for_configuration`, piloto de tasa) solo aceptan `kind: development`; una snapshot de desarrollo no puede contener datos de una ventana reservada no consumida ni liberada (su último `open_time` es anterior al inicio de toda ventana activa del almacén); el evaluador final solo genera señales, entradas y resultados con velas de la ventana, el `context` solo alimenta indicadores y las posiciones empiezan sin operaciones abiertas; el contexto del LOCKBOX contiene el periodo de la OOS descargado de nuevo, solo tras el consumo de la OOS y sin cálculo de resultados sobre él.

### C.7 Aislamiento frente al desarrollo y a la observación en vivo

1. Mientras una ventana esté reservada y no consumida, sus datos no pueden usarse en ningún desarrollo, selección, calibración ni decisión experimental de ninguna hipótesis BTC/USDT (D3.3), incluidos los datos de captura en vivo (FEAT-016) y las salidas de agentes u operación en vivo. Los cargadores de investigación solo aceptan snapshots versionadas.
2. La observación en vivo no se puede impedir; se neutraliza porque, tras C.5, no queda nada modificable sin perder el carácter confirmatorio.
3. Una ventana reservada no consumida solo pasa a ser dato de desarrollo por decisión del propietario, y nunca vuelve a ser ventana de evaluación.
4. Una frontera nueva corresponde a un experimento nuevo, y su `B` es posterior al fin de toda ventana anterior reservada, consumida o contaminada.

### C.8 Suficiencia, ventanas, parada y posiciones abiertas

- **Mínimos sin cambios (REQ-G-P15):** ≥ 100 operaciones en Train+Val, ≥ 30 en la OOS (agregado) y ≥ 30 en el LOCKBOX.
- **Región de desarrollo:** `H_dev,min = max(38 ; 100/r)` meses (38 = 24 + 2 + 6 + 6). Si no se alcanza: limitación documentada, ajuste propuesto por el propietario y el experimento no pasa de DESIGN.
- **Ventanas:** `L_oos ≥ k·30/r` y `L_lb ≥ k·30/r` meses, `k ≥ 1`, `r` del piloto de tasa. Valores en el preregistro (D6).
- **Parada (P2):** solo de calendario, congelada antes de `B`. Al cierre, < 30 operaciones ⇒ evaluación INCONCLUSIVE y ventana consumida, sin ampliación ni reevaluación. Si la OOS no es favorable, el LOCKBOX no se evalúa. Un nuevo intento exige experimento y frontera nuevos y la contabilidad de CR-020.
- **Posiciones abiertas (P5, D3), compatible con REQ-G-109:** se aplica el modelo de ejecución vigente vela a vela; una señal cuya entrada caería en la apertura de una vela posterior al fin de la ventana no se ejecuta; una posición abierta al cierre de la última vela cerrada de la ventana (temporalidad de ejecución del preregistro) se cierra a ese precio de cierre con slippage adverso de 0,10 % (REQ-G-P04) y comisión `max(real; 0,10 %)` (REQ-G-P03); si en esa vela se tocan stop o TP, prevalecen las reglas vigentes (stop primero); no se lee ningún dato posterior. La operación cuenta en las métricas y en P15, marcada `forced_window_close`, y se informa por separado. Solo en las ventanas OOS y LOCKBOX; el Walk-Forward no cambia.

### C.9 Comprobaciones de independencia y requisitos por etapa (F1, F3, C1)

| Id | Comprobación | Tipo |
|---|---|---|
| V1 | La declaración de frontera cita el SHA-256 del preregistro congelado y fue publicada en `origin` al menos 24 h antes de `B` (evidencia operativa de Git; no es un sellado de tiempo certificado) | Documental |
| V2 | El contenido del preregistro es recuperable desde el almacén (C.4.1) y su SHA-256 coincide con el de PREREGISTERED | Mecánica |
| V3 | No hay ningún `DEVIATION` del experimento posterior a PREREGISTERED | Mecánica |
| V4 | **Consumo, según la etapa (C1).** **V4-pre** (antes del consumo): la ventana no tiene ningún `PARTITION_CONSUMED`; para el LOCKBOX, la OOS del mismo experimento está consumida. **V4-post** (después del consumo): consta exactamente un `PARTITION_CONSUMED` de la ventana, del experimento dueño, con el `decision_ref` de la `FinalEvaluationGrant` que la autorizó; ninguna otra consumición de la ventana por ningún experimento; ningún uso del LOCKBOX consumido como LOCKBOX en otra snapshot (REQ-G-109). Para el LOCKBOX, V4-post también se cumple para su OOS. Las denegaciones registradas en el registro de accesos no son consumos (observación TC-ML-012 conservada) | Mecánica |
| V5 | Manifiesto de la snapshot de evaluación: hash, sellado, `kind`, `window_id`, límites iguales a los del preregistro, contigüidad del `context` con `D_dev`, referencia a la snapshot de desarrollo y, para el LOCKBOX, continuidad del contexto (C.6.5) | Mecánica |
| V6 | Atestación del propietario: ningún uso de la ventana ni inspección prematura de resultados para ninguna hipótesis BTC/USDT | Documental |
| V7 | El inventario de exposición cita todos los `DEVIATION` de independencia existentes (parte mecánica) y la nueva información anterior a `B` está evaluada (parte documental) | Mixta |
| V8 | `independence_status` = `INDEPENDENT_AS_DECLARED` (D.4) | Mecánica |

**Requisitos por etapa.** «R» = requerida; «—» = no aplicable (su evidencia no existe todavía o ya se acreditó en una etapa anterior). Una comprobación requerida cuya evidencia falta, es incoherente o no puede verificarse impide la etapa (Fail-Closed). Una comprobación no aplicable nunca bloquea.

| Etapa | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | Requisitos adicionales |
|---|---|---|---|---|---|---|---|---|---|
| ET-1 Congelación (DESIGN → PREREGISTERED) | — | R (contenido escrito en el almacén antes de PREREGISTERED) | — | — | — | — | R (parte mecánica) | — | C.4.2.3–C.4.2.5; campos de C.5; snapshot de desarrollo verificada (I2) |
| ET-2 Declaración de frontera | R (cita del SHA-256) | R | R | — | — | — | — | R | Publicación posterior a ET-1 |
| ET-3 Inicio de la ventana (`B`) | R (publicación ≥ 24 h antes) | — | — | — | — | — | — | — | Si falla V1, frontera inválida: experimento nuevo |
| ET-4 Construcción de la snapshot de evaluación | R | R | R | R (V4-pre) | — (el manifiesto se crea aquí) | — | — | R | Ventana cerrada (última vela cerrada según la hora del servidor); `--confirm`; LOCKBOX: continuidad C.6.5 |
| ET-5 Autorización (`FinalEvaluationGrant`) | R | R | R | R (V4-pre) | R | R | R | R | `decision_ref` con la atestación de V1, V6 y V7 |
| ET-6 Consumo (`load_final`, dentro del bloqueo) | — (acreditada en ET-5) | R | R | R (V4-pre, reclamación atómica vigente) | R | — | — | R | Autorización válida; `PARTITION_CONSUMED` antes de leer |
| ET-7 Evaluación y veredicto | — | R | R | R (V4-post) | R | — | — | R | Resultados solo con velas de la ventana; sin ELIGIBLE_FOR_HUMAN_REVIEW si falla alguna (D.8) |
| ET-8 HUMAN_REVIEW | R | R | R | R (V4-post) | R | R | R | R | `confirmatory_status` coherente (obligación vigente) |
| ET-9 Promoción (REQ-G-P23) | — | R | R | R (V4-post) | R | — | — | R | `confirmatory_status` recalculado; clasificación D.8 |
| ET-10 Uso operativo (cada ciclo con posible entrada) | — | R | R | R (V4-post) | R | — | — | R | REQ-G-P23; clasificación D.8; solo bloquea entradas nuevas |

V1, V6 y V7 (parte documental) son comprobaciones documentales: el software solo verifica la existencia y la sintaxis de la referencia; su validez la acredita el propietario en ET-5 y ET-8.

## D. Contaminación, invalidación y elegibilidad

### D.1 Eventos y consecuencias

| Evento | Consecuencia |
|---|---|
| Exposición no autorizada de una ventana reservada | `DEVIATION` de independencia (D.2); periodo contaminado (D.3); no confirmatorio |
| Cambio material de estrategia o parámetros tras congelar | `DEVIATION` del campo (regla endurecida C.5) ⇒ no confirmatorio |
| Decisión de desarrollo informada por datos de evaluación | `DEVIATION` de independencia, clase `DEVELOPMENT_INFORMED`; CR-022 se aplica sin cambios a las citas de pares en `informed_by` |
| Inspección prematura de resultados | `DEVIATION` de independencia, clase `PREMATURE_INSPECTION`; sin reevaluación |
| Imposibilidad de establecer o mantener la independencia | `independence_status` INDETERMINATE ⇒ Fail-Closed (D.4, D.8); si se constata, `DEVIATION` con clase `INDEPENDENCE_UNVERIFIABLE` |

La evidencia no confirmatoria puede informarse, pero nunca es elegible para APPROVED (REQ-G-108). Los requisitos vigentes de `confirmatory_status` no se debilitan.

### D.2 Registro con el `DEVIATION` existente (P8)

- `field = "independence_boundary"`, campo obligatorio del preregistro (C.5): cumple la validación vigente («campo conocido») sin tipos de registro nuevos.
- Se conservan todas las claves vigentes: `deviation_id`, `experiment_id` (**siempre el dueño de la ventana**, P3, sea cual sea la actividad o la hipótesis que causó la exposición), `preregistration_sha256` (el de su PREREGISTERED), `old` (valor congelado), `justification`, `after_oos` (derivable, como hoy), `access_log_evidence`, `actor`, `authorizes_change: false` e `informed_by` (CR-020 R2; vacío no establece independencia).
- `new` es exactamente `{"contaminated_window_ids": [...], "class": UNAUTHORIZED_EXPOSURE | DEVELOPMENT_INFORMED | PREMATURE_INSPECTION | INDEPENDENCE_UNVERIFIABLE, "evidence": ["repo@commit:ruta", ...], "exposure_started_at": "<instante UTC ISO-8601>" | "UNKNOWN"}`. Ventanas del propio experimento; `evidence` no vacío con la sintaxis de `_EVIDENCE_REF`; `exposure_started_at` no puede ser anterior al inicio de ninguna ventana citada (los datos no existían); `"UNKNOWN"` se trata como «anterior a todo consumo de la ventana». Mal formado ⇒ registro incoherente (Fail-Closed vigente para `DEVIATION` mal formados).
- Se admite en cualquier estado posterior a PREREGISTERED, **también en un estado terminal**. No se registra como contaminación la observación de datos de una ventana ya consumida.
- Se escribe con `append_deviation` (bloqueo exclusivo y `fsync`); una escritura incierta sigue la condición operativa de ORQ-017-01 (no continuar hasta conciliar).
- Append-only: no se retira ni se corrige; un registro erróneo solo se supera con un experimento y una frontera nuevos.
- **Sin reinterpretación histórica:** en v1.10 `independence_boundary` no es un campo válido y la validación lo rechazaría («campo desconocido»), así que ningún `DEVIATION` anterior puede tener este significado; el registro real no contiene ningún `DEVIATION`. Los `DEVIATION` de otros campos conservan su semántica, incluida «válidas y ajenas: se ignoran».

### D.3 Alcance de la contaminación (F2)

Un `DEVIATION` de independencia válido define un **periodo contaminado**: la unión de las ventanas que cita.

1. **Afectados:** todo experimento, en cualquier estado (incluidos APPROVED, REJECTED e INCONCLUSIVE), cuya evaluación final, consumida o pendiente, se haya hecho o deba hacerse sobre datos de ese periodo. Por P3 y C.7.4 es el dueño de la ventana; la regla se formula por intersección de periodos para no depender de esa unicidad.
2. **Restricción global (D3.3):** ninguna hipótesis BTC/USDT puede usar el periodo contaminado como ventana de evaluación; toda frontera posterior es posterior a su fin (C.4.2.3); todo preregistro posterior cita el `DEVIATION` en su inventario (V7, ET-1).
3. **No afectados, con fundamento:** un experimento cuyas ventanas no intersectan el periodo contaminado no está afectado. No se apoya en la ausencia de evidencia, sino en la construcción del modelo: sus ventanas son disjuntas y posteriores a toda ventana anterior (C.4.2.3), así que el periodo contaminado es, para él, histórico anterior a su `B`, que está permitido para desarrollo. El uso de una ventana reservada durante su reserva incumple C.7.1 y contamina la ventana de su dueño, no la evidencia confirmatoria de otro experimento.
4. **Momento de la exposición y del registro:** el efecto lo determinan el periodo contaminado y la exposición, conocida o presunta (`"UNKNOWN"`). La posición del registro en el archivo solo determina qué etapas ya se habían superado al descubrirse (D.5). Una contaminación registrada tarde tiene el mismo efecto que una registrada a tiempo, a partir de la siguiente etapa que la evalúe.
5. **CR-022:** sin cambios. El `DEVIATION` es un punto de decisión del dueño en C.4.2 de CR-020; no altera la relevancia de pares de otros experimentos, que sigue determinándose por la cita del par exacto.

### D.4 Función común de independencia

`independence_status(registry, prereg_store, experiment_id)` devuelve `INDEPENDENT_AS_DECLARED`, `CONTAMINATED` (determinación metodológica válida: un `DEVIATION` de independencia válido cuyo periodo intersecta las ventanas del experimento) o `INDETERMINATE` (fallo técnico de evidencia: contenido del preregistro no recuperable o con hash distinto; `independence_boundary` ausente o mal formado; registro ilegible o corrupto según CR-021; manifiesto que no coincide con el preregistro). La usan `confirmatory_status`, `PartitionLoader.load_final` (dentro del bloqueo vigente), el evaluador de aceptación, HUMAN_REVIEW, la promoción y el uso operativo, con las etapas de C.9 y la clasificación de D.8.

### D.5 Descubrimiento tardío

Según la posición del registro en el archivo: antes de ET-5, no se emite la autorización; entre ET-5 y ET-6, `load_final` deniega, registra la denegación y no consume; tras ET-6, el resultado es no confirmatorio y el evaluador (ET-7) y HUMAN_REVIEW (ET-8) no lo certifican; tras APPROVED, el registro APPROVED se conserva sin cambios y ET-9 y ET-10 recalculan la elegibilidad y bloquean la promoción y las entradas nuevas (REQ-G-P23). Las reclasificaciones posteriores las decide el propietario con los mecanismos vigentes; no hay estados ni tipos de registro nuevos.

### D.6 Detectable y no detectable

Se detectan de forma mecánica los `DEVIATION` registrados, los consumos, las denegaciones y los accesos registrados, las discrepancias de hash, manifiesto o digest, los preregistros no recuperables y el solapamiento de ventanas. **No** se detecta la exposición externa no declarada (descarga manual de Binance, observación de gráficos, uso informal de salidas en vivo): depende de V6, V7 y de su declaración. **El software no puede detectar por sí mismo toda la contaminación externa.**

### D.7 Preservación de CR-020, CR-021 y CR-022

- **CR-020:** un `DEVIATION` de independencia no añade pares ni cambia `N_pre`; el piloto de tasa cuenta como cualquier evaluación nativa.
- **CR-021:** sin cambios en `EVALUATION_PERSISTED`, I2a/I2b, P1–P5 de CR-021 ni el tratamiento de registros corruptos; el `DEVIATION` de independencia no es evidencia certificada por un marcador.
- **CR-022:** el `DEVIATION` de independencia es un punto de decisión más en C.4.2, sin excepciones; puede producir INCONCLUSIVE en pruebas posteriores, coherente con un experimento ya no confirmatorio.

### D.8 Ineligibilidad metodológica frente a fallo técnico (U1, C2)

**Clasificación de la determinación de elegibilidad** (ET-7, ET-9, ET-10; también en ET-5 y ET-6 para el motivo de denegación):

| Resultado | Condición | Naturaleza |
|---|---|---|
| `ELIGIBLE` | Todas las comprobaciones requeridas en la etapa se cumplen y `confirmatory_status` es confirmatorio | — |
| `NOT_ELIGIBLE` | Toda la evidencia requerida es legible y coherente, y: `confirmatory_status` no confirmatorio; o un `DEVIATION` posterior a PREREGISTERED (V3); o `independence_status` = `CONTAMINATED`; o V4-post muestra una reutilización prohibida | Determinación metodológica válida |
| `UNDETERMINABLE` | Registro ilegible o corrupto (CR-021); preregistro no recuperable o incoherente (V2); manifiesto ausente o incoherente (V5); falta el `PARTITION_CONSUMED` de una ventana evaluada (V4-post incoherente); `independence_status` = `INDETERMINATE`; evidencia requerida ilegible; fallo interno | Fallo técnico |

**Precedencia:** si concurre cualquier condición de `UNDETERMINABLE`, el resultado es `UNDETERMINABLE` y no se afirma ninguna determinación metodológica. Un fallo técnico nunca se reclasifica como ausencia ordinaria de estrategia elegible.

**Efectos:**
- **ET-10 (Strategy Engine, uso operativo):**
  - `NOT_ELIGIBLE` → la estrategia se excluye (`evaluated_strategies.result = NOT_ELIGIBLE`); si no queda ninguna estrategia elegible, `NO_SETUP` con `reason_code = NO_APPROVED_STRATEGY` y `reason_detail = CONFIRMATORY_ELIGIBILITY_LOST` (`api_contracts.md` §B.7). Si quedan otras elegibles, el ciclo sigue con ellas y la exclusión consta en la auditoría.
  - `UNDETERMINABLE` → error técnico según CR-018 y DEC-018 decisión 3: `STRATEGY_CANDIDATE` con `result_status = ERROR`, `error.code = ELIGIBILITY_UNDETERMINED`, `stage = STRATEGY_EVALUATION`, `strategy_id`/`strategy_version` de la estrategia afectada y sobre `FAILED` (B.7.1); el ciclo termina sin llamadas a LLM. No es `NO_SETUP`.
  - **En ambos casos** no hay entradas nuevas. La determinación de elegibilidad solo afecta a la evaluación de entradas: `STRATEGY_EXIT_SIGNAL` y `STOP_ADJUSTMENT_REQUESTED` de las posiciones abiertas se evalúan y emiten con independencia de ella y no se suprimen. El stop en el exchange (REQ-G-031), los cierres protectores (`PROTECTIVE_CLOSE_SUBMITTED`), la reconciliación y el modo seguro (REQ-G-032, REQ-G-P26) no dependen del Strategy Engine y siguen disponibles.
- **ET-9 (promoción):** `NOT_ELIGIBLE` → rechazada y registrada con motivo metodológico; `UNDETERMINABLE` → rechazada y registrada como fallo técnico, con su causa. Ningún registro de estado se reescribe.
- **ET-7 (evaluador):** no emite ELIGIBLE_FOR_HUMAN_REVIEW salvo con `ELIGIBLE`; `UNDETERMINABLE` se informa como error con su causa, no como veredicto (como el Fail-Closed vigente de CR-021).
- **ET-5/ET-6 (autorización y consumo):** ambos resultados deniegan; la denegación registra si la causa es metodológica o técnica.
- Un modelo de ML no genera entradas por sí mismo (REQ-G-105): su uso operativo pasa por la elegibilidad de la estrategia que lo usa (sus versiones constan en `conditioning_components`, C.5); la promoción del modelo aplica ET-9.

## E. Enmiendas contractuales aplicadas (contrato v1.10 → v1.11)

| Referencia | Cambio aplicado |
|---|---|
| REQ-G-100, 102, 105, 107, 108 | Sin cambio |
| REQ-G-101 | Texto sin cambios; añadido CR-023: OOS y LOCKBOX solo tras una frontera válida; ausencia de exposición documentada no establece independencia; ámbito BTC/USDT |
| REQ-G-103 | Histórico mínimo sustituido por `H_dev,min` y `L ≥ k·30/r` (CR-011 modificado); añadido CR-023: piloto de tasa, congelación completa, almacén (no satisface O4), regla endurecida, contaminación |
| REQ-G-104 | Añadido: experimentos no elegibles sin OOS_EVALUATION ni autorizaciones finales; `DEVIATION` de independencia admitido en estados terminales; estados y transiciones sin cambios |
| REQ-G-106 | Estructura de validación y referencia de histórico mínimo sin porcentajes; se conservan 24/2/6/6, ≥ 2 ventanas y el agregado de la OOS |
| REQ-G-109 | Snapshot de desarrollo, frontera, snapshots de evaluación por ventana con `context`, digests y continuidad, lectura del pasado, posiciones abiertas, ventanas consumidas o contaminadas; huecos, hash, intervalos, modelo de ejecución, régimen y LOCKBOX consumido conservados; criterios de aceptación ampliados |
| REQ-G-P10 | 50/20/15/15 sustituido por desarrollo 5:2 + ventanas prospectivas |
| REQ-G-P15 | Valores sin cambio; por ventana, sin ampliación ni reevaluación; `forced_window_close` |
| REQ-G-P16, REQ-G-P17 | Sin cambio |
| REQ-G-P23 | Añadida la elegibilidad recalculada en promoción y uso, la clasificación D.8 y la protección de posiciones |
| `api_contracts.md` §B.0.4 | Código `ELIGIBILITY_UNDETERMINED` (solo Strategy Engine; cambio aditivo, §8) |
| `api_contracts.md` §B.7 | `NO_APPROVED_STRATEGY` con elegibilidad vigente; `reason_detail` ∈ `NONE_APPROVED`, `CONFIRMATORY_ELIGIBILITY_LOST`; fallo técnico remitido a B.7.1; salidas y protección no se suprimen |
| `data_flow.md` §3 | Nota de la frontera, ventanas prospectivas y contexto |
| `architecture.md` | Solo cabecera de versión |
| DEC-005 Q7, DEC-011/CR-011, DEC-013/CR-013, DEC-018 | Sin reescritura; notas de vigencia en DEC-025 |
| `harness/gates/G3_resumen_contrato.md:72` | Sin cambio (resumen histórico de G3) |

## F. Criterios de aceptación y pruebas

Identificadores comprobados como libres antes de asignarlos: AC-015-9, AC-017-14, TC-ML-025..028.

- **FEAT-015:** AC-015-1, AC-015-3 y AC-015-7 enmendados; AC-015-9 nuevo (snapshots de evaluación por ventana, `context`, sellado, contigüidad, digests canónicos, continuidad del LOCKBOX, exclusión de ventanas reservadas en las snapshots de desarrollo).
- **FEAT-017:** AC-017-3 (campos de C.5, almacén, regla endurecida), AC-017-4 (fórmulas de C.8 y piloto de tasa), AC-017-9 (invalidación D.1 y C.7.4), AC-017-10 (I1 + I2), AC-017-11 (piloto de tasa no confirmatorio y contabilizado) enmendados; AC-017-14 nuevo (frontera, comprobaciones V por etapa, `independence_status`, `DEVIATION` de independencia con alcance por periodo, Fail-Closed).
- **FEAT-019:** AC-019-2 (promoción con elegibilidad recalculada; clasificación D.8).
- **FEAT-020:** AC-020-2 (elegibilidad confirmatoria vigente por ciclo; `NO_APPROVED_STRATEGY`/`CONFIRMATORY_ELIGIBILITY_LOST` frente a `ERROR`/`ELIGIBILITY_UNDETERMINED`; salidas y protección continúan).
- **Plan de pruebas:** TC-ML-009, 014, 015, 016 y 019 enmendadas; TC-ML-025 (frontera, congelación, etapas), TC-ML-026 (contaminación y alcance), TC-ML-027 (snapshots de evaluación, contexto, digests, posiciones abiertas), TC-ML-028 (elegibilidad en promoción y uso, metodológica frente a técnica) nuevas. TC-ML-007 y TC-ML-012 sin cambio de fondo; observación TC-ML-012 conservada.

## G. Reapertura focalizada de FEAT-015 (P7)

Al entrar en vigor el contrato v1.11, FEAT-015 pasa de DONE a IN_PROGRESS conforme a su propia condición de reapertura («una CR futura aprobada que modifique los cortes de las particiones, REQ-G-109 o cualquier criterio AC-015-*»). Se conserva su disposición histórica DONE bajo v1.10 (aprobación del propietario del 2026-11-24). Se reabren solo AC-015-1, AC-015-3, AC-015-7 y el nuevo AC-015-9; AC-015-2, AC-015-4, AC-015-5, AC-015-6 y AC-015-8 conservan su evidencia y quedan con obligación de regresión. DONE solo se restituye tras verificación independiente y aprobación expresa del propietario.

## H. Componentes afectados (implementación pendiente; autorización separada)

`snapshot.py` (tipos de snapshot, constructor de evaluación, digests, continuidad, exclusión de ventanas, contigüidad); `partitions.py` (tipo de snapshot, alcance Train-only, `load_final` con `independence_status`, V4-pre/V4-post, orden OOS → LOCKBOX); `preregistration.py` (campos C.5, almacén C.4.1, regla endurecida, `independence_status`, validación de `DEVIATION` de `independence_boundary`, fórmulas); `experiments.py` (transición bloqueada para no elegibles; `DEVIATION` en estados terminales); `acceptance.py` (P15 por ventana, `forced_window_close`, clasificación D.8); evaluador de backtest (señales solo dentro de la ventana; cierre forzoso); Strategy Engine (filtro de elegibilidad por ciclo, `NO_SETUP`/`ERROR` según D.8, salidas independientes); registro de modelos de FEAT-019 (puerta de promoción); `cli.py`; `research/README.md`; pruebas. **Sin cambios:** tipos de registro de `registry.jsonl`, `trials.py`, `EVALUATION_PERSISTED`.

## I. Verificación y regresión requeridas

1. Pruebas de §F con datos sintéticos, con reproducción sobre la base cuando proceda.
2. Regresión completa de CR-020 (TC-ML-020..024), CR-021 (I2a/I2b, P1–P5 de CR-021) y CR-022, y de la suite.
3. Verificación independiente de CR-023 y de la reapertura de FEAT-015.
4. Sin SNAP-0001, datos reales, OOS ni LOCKBOX.

## J. Dependencias y decisiones diferidas

D4 (`D_dev` y SNAP-0001 como snapshot de desarrollo; requisito previo: cierre de D3 y autorización del propietario); D5 (uso del piloto de tasa y orden de exploración y preregistro: única dependencia de secuencia pendiente, no resuelta aquí); D6 (`k` y parámetros estadísticos); D7 (configuración del piloto); O3 y O4 como requisitos previos del piloto de tasa (evaluación del pipeline); declaración de frontera, `B` y longitudes de ventana como decisión del propietario específica del experimento (I4), no de D4.

## K. Riesgos y limitaciones residuales

- **R1:** la publicación antes de `B` se acredita con Git como evidencia operativa; sin sellado de tiempo certificado (P4); misma limitación de autenticidad que N-3.
- **R2:** la exposición externa no declarada no es detectable (D.6).
- **R3:** la exposición incierta y la desconocida permanecen en la región de desarrollo, sin afirmación de independencia.
- **R4:** espera larga (≈ 2k·30/r meses) y reserva global BTC/USDT de las ventanas.
- **R5:** las revisiones de datos de Binance dentro de las ventanas se detectan solo para el periodo de la OOS (C.6.5), no se previenen; en la propia ventana del LOCKBOX no hay segunda copia que comparar.
- **R6:** un `DEVIATION` de independencia erróneo es permanente.
- **R7:** los resultados de la OOS se conocen antes de cerrarse la ventana del LOCKBOX; neutralizado por la congelación (C.5).
- **R8:** la coexistencia en un mismo ciclo de un `STRATEGY_CANDIDATE` en ERROR por elegibilidad y de un `STRATEGY_EXIT_SIGNAL` debe verificarse con TC-ML-028 y TC-FLOW-011 al implementar.

## L. Condiciones de cierre de D3

D3 sigue ABIERTA hasta que se cumplan todas: (1) CR-023 aprobada (DEC-025) y aplicada contractualmente — **cumplida con el contrato v1.11**; (2) implementación de §H completada y aceptada; (3) verificación independiente aceptada; (4) reapertura focalizada de FEAT-015 y sus obligaciones de nueva verificación resueltas (§G); (5) el mecanismo de §D (antes «sección J» de la revisión 1) implementado y verificado. No se admite un cierre solo documental. El cierre acredita I1 (método e implementación con datos sintéticos), no I5; no exige particiones prospectivas; no desbloquea D4 sin autorización del propietario y no cierra FEAT-017.

## M. Obligaciones preservadas

Reevaluación de CONF-009 antes del cierre de FEAT-017; CONF-010 OPEN con O3 y O4 antes del pipeline; P5 de CR-021 PENDIENTE con las condiciones de `IMPL-3_N-2_disposicion.md` §3 y `IMPL-3_N-3_disposicion.md` §4; S1–S4; riesgos residuales de N-2 y N-3; sin tamper-evidence; `confirmatory_status` coherente en HUMAN_REVIEW (ELIGIBLE_FOR_HUMAN_REVIEW no es aprobación); N-1 no retroactiva; observación separada de `_marker_error` abierta; cierres de D1, D2 y D8 sin cambios; mínimos estadísticos sin cambios; semántica de CR-020, CR-021 y CR-022.

## N. Historial de revisiones

- **Revisión 1 (2026-11-25):** propuesta inicial; preguntas P1–P8.
- **Revisión 2 (2026-11-25):** P1–P8 y R1–R5; snapshots de evaluación con `context`; piloto de tasa; `B` en la declaración del experimento; congelación completa; `DEVIATION` de independencia; preguntas U1–U2.
- **Revisión final focalizada (2026-11-25):** U1 (REQ-G-P23, §B.7, AC-019-2, AC-020-2) y U2 (almacén; O4 independiente); F1 (V1–V8), F2 (alcance por periodo; sustituye el alcance de la revisión 2, que invalidaba todo experimento congelado no terminal), F3 (matriz ET-1..ET-10), F4 (digest canónico y continuidad).
- **Aprobación (2026-11-25, DEC-025)** con las correcciones obligatorias **C1** (V4-pre/V4-post) y **C2** (`NOT_ELIGIBLE` → `NO_SETUP`/`NO_APPROVED_STRATEGY`/`CONFIRMATORY_ELIGIBILITY_LOST`; `UNDETERMINABLE` → `ERROR`/`ELIGIBILITY_UNDETERMINED`; se retira `CONFIRMATORY_ELIGIBILITY_INDETERMINATE` de la revisión final), incorporadas antes de la aplicación contractual.

---

## Notas de vigencia (CR-024, contrato v1.12; el texto original de CR-023 se conserva)

- **§C.6.4 y §H («sin cambios de tipos de registro»):** vigente salvo `WINDOW_RESULT_PERSISTED`, tipo añadido por CR-024 §B.4. `PARTITION_CONSUMED`, `EVALUATION_PERSISTED` y `trials.py` no cambian.
- **§C.9, V4-pre del LOCKBOX y ET-4 («OOS consumida»):** enmendados; el LOCKBOX exige el OOS consumido **y** favorable autoritativo en ET-4, ET-5, ET-6 y `resolve_lockbox`. La continuidad de §C.6.5 no cambia.
- **§C.9, ET-8 y la frase «V1, V6 y V7 solo verifican existencia y sintaxis»:** ampliados; ET-8 verifica además los `evaluation_hash` de OOS y LOCKBOX (CR-024 §B.8). V4-post, la gramática y la unicidad de la decisión 5 no cambian.
- **B7 («no escribe en el registro»):** se conserva para `evaluate_window`; la persistencia vive en un módulo de orquestación.
- **CR-021 (Train+Val):** semántica sin cambios.

## Notas de vigencia (CR-025, contrato v1.13; el texto original de CR-023 se conserva)

- **§C.9 (matriz ET-1..ET-10):** ET-9 y ET-10 añaden la comprobación V9 (integridad autoritativa ligada a la aprobación, CR-025); ET-8 comparte con V9 la verificación de evidencia de resultados.
- **§D.8 (clasificación):** la lista de causas `UNDETERMINABLE` añade «V9: integridad del resultado ligado a la aprobación» (siempre técnica; incluye el bloqueo del registro no obtenido en 2 s en ET-10).
- **§H («sin cambios de tipos de registro»):** vigente; la ligadura es una clave de la evidencia de la transición APPROVED (`approval_binding`), no un tipo de registro.
- **ET-10 en el Strategy Engine:** diferido a B9.
