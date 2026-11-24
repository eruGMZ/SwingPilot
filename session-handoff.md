# session-handoff.md — SwingPilot Harness

## IMPL-3 (2026-11-24) — QA3R2-06 RESUELTO POR COMPLETO (FEAT-017); commit en develop, sin push

**Aprobación del propietario (2026-11-24):** corrección y evidencia aprobadas; riesgos residuales aceptados dentro del alcance. **Requisito conservado:** verificar la coherencia entre el `execution_model` preregistrado y `ExecutionModel` antes del piloto confirmatorio. Sin validación adicional ni topes realistas de costes en esta etapa. Sin pruebas adicionales tras la aprobación.
**Estado:** FEAT-017 IN_PROGRESS (sin cambios en `feature_list.json`); QA3R2-07 abierto; SNAP-0001 no creada.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

### Registro previo a la aprobación — QA3R2-06 corregido (FEAT-017), pendiente de aprobación; sin commit

**Push:** los seis commits aprobados están en `origin/develop` (`c3f526c`, sincronizado).
**Hecho:** corrección directa autorizada de QA3R2-06, sin CR. `ExecutionModel.__post_init__` (`src/swingpilot/research/backtest.py`) acepta `commission_rate` y `slippage` solo como reales finitos no booleanos con `0.001 ≤ valor < 1.0`; si no, `ValueError`. Límite superior comprobado sin conflicto con el contrato. 65 pruebas nuevas en `tests/unit/test_research.py`: 24 regresiones (fallan con `c3f526c`), 8 normalizaciones de `TypeError` a `ValueError`, 12 rechazos existentes y 21 controles. Detalle en `harness/verification/IMPL-3_QA_ronda2.md` §Corrección de QA3R2-06.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 636 passed, 5 skipped. Validadores → OK.
**Sin commit ni push.** Archivos modificados: `src/swingpilot/research/backtest.py`, `tests/unit/test_research.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** contrato, AC, `feature_list.json`, estados de FEAT (FEAT-017 IN_PROGRESS), evaluador, preregistro, lógica de ejecución. QA3R2-07 abierto. SNAP-0001 no creada; OOS/LOCKBOX reales intactos; $0 de IA.
**Pendiente del propietario (FEAT-017):** aprobación de QA3R2-06; QA3R2-07; decisiones D1–D8 del análisis de AC-017-10/11 (suficiencia de la documentación de EXP-0001, unidad de `trials_count`, cortes y creación de SNAP-0001, orden del piloto en Train, campos del preregistro sin valor contractual, configuración del piloto).
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — FEAT-015 CERRADA como DONE

**Aprobación del propietario (2026-11-24):** AC-015-1..8 definitivos; FEAT-015 READY_FOR_REVIEW → DONE. Riesgos residuales y controles de despliegue diferidos (G6, Laptop B) aceptados. `feature_list.json` v1.16.0.
**Condiciones de reapertura:** CR aprobada que modifique los cortes, REQ-G-109 o algún AC-015-*; o un defecto de implementación confirmado al construir o verificar SNAP-0001 (→ IN_PROGRESS por gobernanza). Un entorno incompatible, por sí solo, no es necesariamente un defecto.
**Fuera del cierre (autorización separada):** creación de SNAP-0001; validación metodológica de la independencia histórica de las particiones.
**Evidencia:** código verificado congelado en `4391df5` (571 passed, 5 skipped); validadores OK al cerrar; la suite no se volvió a ejecutar.
**Estado de IMPL-3:** FEAT-015 y FEAT-016 DONE; FEAT-017..022 IN_PROGRESS (pendientes AC-017-10/11, AC-018-2/6, AC-020-8, AC-022-6 y SNAP-0001).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — FEAT-015: trazabilidad consolidada, revisión de cierre preparada

**Hecho:** `feature_list.json` v1.15.0. FEAT-015 → `evidence.traceability_review`: matriz AC-015-1..8 (todos CUMPLEN), hallazgos QA3R2-02/03/04/08 resueltos, riesgos aceptados, controles diferidos (G6, Laptop B), SNAP-0001 fuera del alcance técnico, condiciones de reapertura y recomendación (DONE). Estado sin cambio: READY_FOR_REVIEW.
**Evidencia:** última verificación del código, sobre el árbol congelado en `4391df5`: 571 passed, 5 skipped; validadores OK. No se ejecutaron pruebas en este paso.
**Sin commit.** Archivos: `feature_list.json`, `progress.md`, `session-handoff.md`.
**Pendiente del propietario:** aceptación formal de AC-015-1..8 y decisión de cierre de FEAT-015.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — QA3R2-08 RESUELTO POR COMPLETO (bloqueo ante sellado no efectivo)

**Hecho:** corrección directa sin CR según las decisiones del propietario. Sonda de sellado antes de descargar o apartar huérfanos; comprobación final antes de confirmar, con rollback; `PartitionLoader` bloqueado (también `train_val`) y nueva comprobación antes de consumir; `verify-snapshot` → ERROR y código 1; sin omisión. 10 regresiones (todas fallan con `f8e7643`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 571 passed, 5 skipped (como usuario no root). Validadores → OK.
**Aprobación final del propietario (2026-11-24)**, congelada en un commit en develop, sin push. Riesgos aceptados: CI con usuario sin privilegios; cuarentena de huérfanos existente; privilegios especiales de Linux y aislamiento del despliegue sujetos a G6; Laptop B como requisito previo de despliegue. Archivos: `src/swingpilot/research/{snapshot,partitions,cli}.py`, `tests/unit/test_snapshot.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Requisito de despliegue pendiente:** verificar en Laptop B usuario no root, sistema de archivos POSIX y sellado efectivo (no confirmado).
**Sin cambios:** contratos, `feature_list.json`, estados de FEAT (FEAT-015 READY_FOR_REVIEW), cortes, SNAP-0001, OOS/LOCKBOX reales.
**Estado de hallazgos de FEAT-015:** QA3R2-02, 03, 04 y 08 resueltos y aprobados. FEAT-015 sigue en READY_FOR_REVIEW (su cierre requiere decisión del propietario).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 RESUELTO POR COMPLETO

**Estado:** QA3R2-04 resuelto por completo y aprobado por el propietario: corrección principal (`f04a2d1`) y observación adicional sobre el estado destino (`c314d92`, 17 pruebas). Registro en `harness/verification/IMPL-3_QA_ronda2.md`.
**Última verificación (sobre `c314d92`):** 563 passed, 5 skipped; validadores OK. En este paso no se ejecutaron pruebas.
**Sin cambios:** FEAT-015 en READY_FOR_REVIEW y demás estados de FEAT; contratos; SNAP-0001 no creada; OOS/LOCKBOX reales intactos; sin push.
**Pendiente:** QA3R2-08 CONDICIONADO (sellado no efectivo: avisar o bloquear).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 (observación adicional): estado destino en transiciones, APROBADA (commit en develop, sin push)

**Hecho:** corrección directa sin CR, aprobada contractualmente por el propietario. Las transiciones que decide el propietario exigen `AUTORIZA: EXP-NNNN ESTADO_DESTINO` (OOS_EVALUATION, APPROVED, REJECTED, INCONCLUSIVE); la línea sin estado ya no autoriza nada; la gramática de particiones no cambia. Código afectado: registro de experimentos de FEAT-017 (AC-017-1). 17 regresiones (4 reproducen el defecto con `c9a054b`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 563 passed, 5 skipped. Validadores → OK.
**Aprobada por el propietario (2026-11-24)** y congelada en un commit en develop, sin push. Archivos: `src/swingpilot/research/experiments.py`, `tests/unit/test_{research,snapshot,ml_registry,engines}.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** máquina de estados, contratos, AC, `feature_list.json`, estados de FEAT; QA3R2-08 sigue CONDICIONADO; SNAP-0001 y OOS/LOCKBOX reales intactos.
**Pendientes:** QA3R2-08 CONDICIONADO (sellado no efectivo: avisar o bloquear).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-08 aprobado en su alcance actual (CONDICIONADO); commit en develop, sin push

**Hecho:** corrección autorizada de QA3R2-08 (FEAT-015). Detección del sellado no efectivo (`SealingWarning`; `verify-snapshot` → código 1), re-sellado de OOS/LOCKBOX con modo alterado, lectura autorizada con re-sellado inmediato (SIGKILL ya no deja 0o400), id `SNAP-NNNN` obligatorio en la CLI y `fullmatch` en `build_snapshot`/`load_manifest`. 28 regresiones (26 fallan con `f04a2d1`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 546 passed, 5 skipped. Validadores → OK.
**Aprobado por el propietario (2026-11-24) en su alcance actual** y congelado en un commit en develop, sin push. **QA3R2-08 CONDICIONADO, no cerrado:** falta decidir y resolver el comportamiento ante sellado no efectivo (hoy solo avisa). Archivos: `src/swingpilot/research/{snapshot,partitions,cli}.py`, `tests/unit/test_snapshot.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** FEAT-015 en READY_FOR_REVIEW; cortes, SNAP-0001, OOS/LOCKBOX reales, contratos y esquema del manifiesto intactos. QA3R2-02/03 ya estaban corregidas (`04dc2ea`).
**Pendientes registrados:** QA3R2-08 condicionado (sellado no efectivo: avisar o bloquear); observación de QA3R2-04 sobre el estado destino en la línea de transición (sin analizar ni implementar).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 corregido y aprobado (commit en develop, sin push)

**Hecho:** corrección autorizada de QA3R2-04 (FEAT-015). `create()`/`claim_partition()` validan `EXP-NNNN`; las decisiones se comprueban con una línea exacta `AUTORIZA: EXP-NNNN [<oos|lockbox> <SNAP-…>]` en lugar de por subcadena; decisión ilegible → denegada. 48 regresiones (45 fallan con `e375a18`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 518 passed, 5 skipped. Validadores → OK.
**Aprobado por el propietario (2026-11-24)** y congelado en un commit en develop, sin push. Archivos: `src/swingpilot/research/{experiments,partitions}.py`, `tests/unit/test_{research,snapshot,ml_registry,engines}.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** FEAT-015 sigue en READY_FOR_REVIEW; cortes, SNAP-0001, OOS/LOCKBOX y registro real intactos.
**Observaciones sin implementar (por indicación del propietario):** estado destino en la línea de transición; ids de antecedentes; `SNAPSHOT_ID.match` con salto final (QA3R2-08); formato `AUTORIZA:` en decisiones reales.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-23) — FEAT-016 cerrada como DONE

**Aprobación del propietario (2026-11-23):** FEAT-016 pasa de READY_FOR_REVIEW a DONE. No es DONE-PARTIAL porque AC-016-9 excluye la operación continua de IMPL-3. `feature_list.json` v1.14.0 incluye la aprobación, `closure_verification` sobre `c384386` (470 passed, 5 skipped) y la evidencia pública del 2026-11-20 conservada.
**Riesgo residual aceptado:** QA3R2-05 (resync sin reintento con una conexión WebSocket silenciosa; Fail-Closed intacto). Está asignado a **IMPL-5**: recuperación autónoma ante conexiones silenciosas.
**Sin commit:** solo registros (`feature_list.json`, `progress.md`, `session-handoff.md`). No se tocó código ni contratos.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario (commit de este cierre; FEAT-015; FEAT-017..022; AC pendientes; SNAP-0001).

## IMPL-3 (2026-11-20) — QA de motores cerrada; CR-019 aplicada (contrato v1.7)

**Commits (sin push):** `04dc2ea` (ENV-01..04 y QA3R2-01..03), `bca19fc` (QA3E-02..06 y 10; CONF-008). **Sin commit:** CR-019 aprobada (DEC-020) y aplicada, que corrige QA3E-01, pendiente de revisión del propietario.
**Contrato v1.7:** `PROPOSAL_NORMALIZATION_REJECTED` (34 tipos; §3.8 B.10) en E9. CONF-008 RESUELTA.
**QA de FEAT-018..022:** todos los hallazgos autorizados están corregidos (`harness/verification/IMPL-3_QA_engines.md`). QA3E-07..09 son observaciones sin tocar. DATA_STALE queda PENDING (sin umbral en el contrato).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 470 passed, 5 skipped. Validadores → OK.
**Siguiente acción autorizada:** ninguna. Esperar la revisión y el commit de CR-019 por indicación del propietario.
**Sin cambios:** FEAT-015..022 sin cerrar (FEAT-015/016 en READY_FOR_REVIEW, sin aprobar; FEAT-017..022 en IN_PROGRESS); SNAP-0001 sin crear; OOS/LOCKBOX intactos; pendientes del propietario: AC-018-2/6, AC-020-8, AC-022-6.

## IMPL-3 (2026-11-20) — ENV-01..04 y QA3R2-01..03 corregidos; base congelada para la QA de FEAT-018..022

**Hecho y aprobado por el propietario:** (1) ENV-01..04: Python 3.14.4 (`.python-version`, instalado con uv), `requirements-dev.lock` con hashes SHA-256, `scripts/setup_env.sh`, scikit-learn excluido (DEC-017 Q44), `tests/regression/test_environment_lock.py`. (2) QA3R2-01..03 corregidos con regresiones que fallan con `5c17e92` (`IMPL-3_QA_ronda2.md` §Correcciones). Riesgos residuales aceptados en `progress.md`.

**Entorno en otra máquina:** ejecutar `scripts/setup_env.sh` (requiere `uv`). Sin eso, `test_environment_lock.py` falla, que es lo esperado.

**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 450 passed, 5 skipped. Validadores → OK.

**Siguiente acción autorizada:** paso 3, la QA independiente focalizada de FEAT-018..022 (una sola revisión, solo lectura) sobre el commit congelado.

**Sin cambios / pendiente:** FEAT-015/016 no aprobadas; SNAP-0001 no creada y sus cortes sin decidir; OOS/LOCKBOX intactos; CR-017, REQ-G-P08 y G5–G7 fuera de esta etapa; QA3R2-04..08 (observaciones) sin tocar; sin push.

## IMPL-3 «Integración cuantitativa» (2026-11-20) — EN CURSO: QA de 2 rondas completada

**Estado:** DEC-017, DEC-018 y DEC-019 (CR-018 aprobada y aplicada). Contrato **v1.6**. `feature_list.json` v1.12.0. Código de FEAT-018..022 implementado (sin QA).

| FEAT | Estado | QA ronda 2 |
|---|---|---|
| FEAT-015 Snapshot | READY_FOR_REVIEW | Conforme con observaciones (QA3R2-02, 03) |
| FEAT-016 Datos en vivo | READY_FOR_REVIEW | Conforme con observaciones (QA3R2-05) |
| FEAT-017 Research | IN_PROGRESS (AC-017-10/11 bloqueados) | Infraestructura conforme con observaciones (QA3R2-01: corregir antes de usar el evaluador) |
| FEAT-019 ML | IN_PROGRESS (AC-019-4, CR-018) | Infraestructura conforme |
| FEAT-018..022 | IN_PROGRESS | Implementadas en `src/swingpilot/engines/` (36 pruebas); sin QA independiente; pendientes AC-018-2/6, AC-020-8, AC-022-6 |

**Informes:** `harness/verification/IMPL-3_QA_ronda1.md` (hallazgos y correcciones), `IMPL-3_QA_ronda2.md`, `IMPL-3_entorno_reproducibilidad.md`, `IMPL-3_EXP-0001_procedencia.md`.

**Pendiente del propietario:**
1. Hallazgos de la ronda 2 (3 MENOR, 5 OBS). Las rondas de QA están agotadas (2/2): corregirlos requiere indicar cómo se verifican.
2. Cierre de FEAT-015/016 (no autorizado aún).
3. ENV-01..04.
4. Cortes de SNAP-0001 frente a los datos ya usados por Fase 0/EXP-0001. SNAP-0001 NO se crea sin autorización expresa.
5. QA independiente de FEAT-018..022 (nueva tanda de rondas) y, si se quiere, corridas reales con LLM de FEAT-022 (USD 0.50).

**Restricciones vigentes:** sin OOS/LOCKBOX; sin credenciales privadas; sin activar estrategias; IA $0.50 sin consumo; sin commit ni push.

**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 426 passed, 5 skipped. Validadores → OK.

**Siguiente acción autorizada:** ninguna de código hasta la indicación del propietario.

### Planificación (histórico de esta sesión)

**Pendiente en su momento (resuelto en DEC-018 salvo lo indicado arriba):** Q42, CR-018 B.6/B.7, EXP-0001, criterios de FEAT-015..022.

### Registro inicial de FEAT (histórico de esta sesión)

**Estado previo:** FEAT-015..022 registradas en `feature_list.json` v1.4.0 con status PENDING; plan en `impl3_plan`. Sin código.

| FEAT | Contenido | Vacío del contrato |
|---|---|---|
| FEAT-015 | Snapshot histórica sellada (REQ-G-109) | Ubicación (Q46) |
| FEAT-016 | Datos en vivo, velas cerradas, resync (REQ-G-097) | Fase no asignada en §7 (Q41) |
| FEAT-017 | Research & Backtesting (preregistro, WF, modelo de ejecución) | — |
| FEAT-018 | Regime Engine (REGIME_CLASSIFIED) | Clases y esquema (Q42, Q45) |
| FEAT-019 | ML Engine (versionado, promoción, drift) | Esquema; alcance (Q44, Q45) |
| FEAT-020 | Strategy Engine (STRATEGY_CANDIDATE, NO_SETUP) | Estrategia concreta; esquemas (Q43, Q45) |
| FEAT-021 | Normalización TRADE_PROPOSAL §4.1 | — |
| FEAT-022 | Ciclo Fase 1→4 con datos reales (salida de IMPL-3) | Tope de gasto (Q47) |

- Bloqueo: Q41–Q47 del propietario. Q45 propone CR-018 (esquemas) antes del código de FEAT-018..021.
- Sigue abierto: CR-017 (PROPUESTA, B.1–B.5).
- Nota de entorno: esta máquina no tiene `.venv`; crearla con `requirements-dev.txt` antes de ejecutar pruebas.
- (Superado: planificación aprobada en DEC-017.)

## Cierre de IMPL-2 (2026-11-20) — transición a IMPL-3

**Estado:** IMPL-2 «Agentes especializados» CERRADA con aprobación del propietario (2026-11-20). Contrato v1.5. G0..G4 PASS (G4 con alcance IMPL-1 + IMPL-2); G5..G7 PENDING.

| FEAT | Estado | Dependencia explícita |
|---|---|---|
| FEAT-008 Market Analyst | DONE | — |
| FEAT-009 Macro Analyst | DONE-PARTIAL | G6 (TC-SEC-003 amplio); CR-017 (fuente de noticias y macro_data) |
| FEAT-010 Strategy Analyst | DONE-PARTIAL | IMPL-3: STRATEGY_CANDIDATE real |
| FEAT-011 Risk Analyst | DONE-PARTIAL | IMPL-4: RISK_APPROVED real y Telegram (TC-FLOW-003) |
| FEAT-012 Decision Synthesis | DONE-PARTIAL | IMPL-3 normalización §4.1; IMPL-4 Risk Manager y Telegram |
| FEAT-013 effort y costo | DONE | — |
| FEAT-014 Ciclo de 5 agentes | DONE-PARTIAL | IMPL-5: cadena hasta ORDER_FILLED |

- Configuración vigente (DEC-016): effort medium ×5; prompts market 0.1.0, macro 0.2.0, strategy 0.2.0, risk 0.1.0, synthesis 0.1.1.
- Calibración: `tests/calibration/` (batería v2 congelada; `RUN_ANTHROPIC_LIVE=1 .venv/bin/python -m tests.calibration.run_battery --label <x>`). Gasto IMPL-2 $0.480488 de $1.00 (libro `var/impl2_experiment_budget.db`).
- Verificar: `.venv/bin/pytest -q tests` → 256 passed, 3 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Abierto: CR-017 (PROPUESTA, B.1–B.5 PENDING del propietario).
- Siguiente acción autorizada: iniciar IMPL-3 «Integración cuantitativa» (ML, Regime y Strategy Engine; architecture.md §7 fila 3) solo con indicación del propietario, poblando sus FEAT desde el contrato v1.5.

## IMPL-2 «Agentes especializados» (2026-11-20) — criterios cumplidos, esperando aprobación de cierre

**Actualización 2:** evaluación cualitativa APROBADA por el propietario; QA ronda 1 sin bloqueantes ni mayores (1 de 2 rondas usadas); G4 PASS con alcance IMPL-1 + IMPL-2; FEAT-008..014 en READY_FOR_REVIEW (salida propuesta en `impl2_exit`: 008/013 DONE, resto DONE-PARTIAL). CR-017 (fuente de noticias y `macro_data`) en PROPUESTA. Siguiente: aprobación de cierre de IMPL-2 por el propietario; luego IMPL-3 (Integración cuantitativa) solo con su indicación.

(Estado anterior:)

**Actualización:** configuración de DEC-016 APROBADA; corridas finales `IMPL2_2026-11-19T2358Z_final-1` y `IMPL2_2026-11-20T0001Z_final-2` PASAN (14/14, cero críticas). Gasto IMPL-2 $0.480488 de $1.00. Siguiente: evaluación cualitativa del propietario sobre los `.md` → QA independiente → G4 → aprobación de cierre.

(Estado anterior:)

**Estado:** plan aprobado (DEC-016, Q36–Q40; `harness/plans/IMPL-2_plan.md`). FEAT-008..014 registradas (PENDING) en `feature_list.json` v1.2.0. Pasos 1–4 hechos; paso 5 (aprobación de la configuración en DEC-016) PENDIENTE del propietario. Sin commit.

- Infraestructura: `tests/calibration/` (tope de USD 1.00 con aviso al 80% y reserva atómica; 14 escenarios congelados, v2 SHA-256 `8f68e9a8…`; comprobaciones V1–V8; ejecutor con informe JSON y MD). Pruebas: `tests/unit/test_impl2_calibration.py`.
- Propuesta: effort medium en los 5; macro_analyst y strategy_analyst con prompt 0.2.0 (ya en `prompts.py`); resto sin cambio.
- Gasto IMPL-2: $0.235959 de $1.00. Suite: 256 passed, 3 skipped.
- Abierto para el propietario: Macro Analyst en INSUFFICIENT_DATA por `macro_data` vacío (sin fuente en el contrato).
- Siguiente acción autorizada tras la aprobación: dos corridas finales consecutivas (`RUN_ANTHROPIC_LIVE=1 .venv/bin/python -m tests.calibration.run_battery --label final-1`, luego `final-2`), evaluación cualitativa del propietario sobre los `.md`, QA independiente (≤ 2 rondas, sonnet), G4 con alcance IMPL-2. No declarar DONE sin aprobación.
- Sub-agentes usados en IMPL-2: 0.

## Cierre de IMPL-1 (2026-11-19) — transición a IMPL-2

**Estado:** FASE 2 EN CURSO (autorizada 2026-11-19). **IMPL-1 «Fundamentos de integración» CERRADA** con el criterio de salida fijado por el propietario. Contrato **v1.5** (CR-015, CR-016; DEC-014, DEC-015). G0..G4 PASS (G4 con alcance IMPL-1); G5..G7 PENDING.

### Estado de las funcionalidades (feature_list.json v1.0.0)

| FEAT | Estado | Dependencia explícita |
|---|---|---|
| FEAT-001 Contrato universal de mensajes | DONE | — |
| FEAT-002 Versionado de contratos | DONE-PARTIAL | IMPL-3: versionado de estrategias (Strategy Engine) |
| FEAT-003 Registro de eventos y trazabilidad | DONE-PARTIAL | IMPL-5: TC-AC-04 completo (Risk Manager, órdenes); G6: protección del archivo SQLite |
| FEAT-004 AI Provider Adapter | DONE | IMPL-2: calibración de effort |
| FEAT-005 AI Orchestrator | DONE | IMPL-2: calibración de prompts; IMPL-3: normalización TRADE_PROPOSAL → §4.1 |
| FEAT-006 Control de costo de IA | DONE-PARTIAL | IMPL-4: aviso por Telegram; propietario: límite en consola Anthropic; G6: conciliación con factura |
| FEAT-007 Aislamiento de credenciales | DONE-PARTIAL | IMPL-4: Telegram (TC-SEC-006/007) y REQ-G-059 con Risk Manager; IMPL-6: permisos de Binance; G6: limitaciones de un solo proceso |

Cada dependencia tiene justificación en `feature_list.json` → `impl1_exit.deferred`. Verificado por QA ronda 4 (CONFORME).

### Qué existe (src/swingpilot/)
- `contracts/`: mensaje universal (31 eventos), versionado, contratos de los 5 agentes.
- `audit/`: EventStore append-only con rechazo de secretos.
- `ai/`: adaptador Anthropic (modelos exactos, 1 reintento, tope duro con reservas), orquestador (Fases 3–5), prompts 0.1.x, presupuesto y EntryGate.
- `security/`: CredentialVault por ámbito, comprobaciones de arranque.
- `bootstrap.py`: `build_ai_stack` conecta todo con Fail-Closed.

### Cómo verificar
- `.venv/bin/pytest -q tests` → 233 passed, 3 skipped.
- `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Prueba real (cuesta ~$0.03): `RUN_ANTHROPIC_LIVE=1 .venv/bin/pytest -v tests/integration/test_anthropic_live.py` (requiere `.env` en 600 con ANTHROPIC_API_KEY). Gasto acumulado del mes: $0.053506 (`var/ai_budget.db`, local).

### Para IMPL-2 «Agentes especializados» (architecture.md §7, fila 2)
- Criterio de salida del contrato: los agentes trabajan coordinadamente, conservan sus resultados y expresan desacuerdos sin producir autorizaciones financieras.
- Pendientes que entran en IMPL-2: calibración de prompts (0.1.x) y de `effort` por agente; costo real por ciclo; observaciones de la prueba real (el Macro Analyst listó una nota de método como evento y marcó FACT un ítem SPECULATION).
- Antes de empezar: poblar `feature_list.json` con las FEAT de IMPL-2 desde el contrato v1.5 (no inventar).
- Pendientes del propietario: límite de gasto en la consola de Anthropic; zona horaria de otros cortes mensuales (al implementarlos); REQ-G-P08 (fiscal, diferido).
- Sub-agentes: esta sesión usó 4 (QA, sonnet, ~298K tokens), por encima del tope orientativo de 200K. Abrir sesión nueva para IMPL-2.

### Siguiente acción autorizada
Iniciar IMPL-2 cuando el propietario lo indique. (Las secciones siguientes son del cierre de FASE 1; su frase «FASE 2 BLOQUEADA» queda superada.)

## Cierre de sesión 2026-11-19 — siguiente acción

- **G3 = PASS** (2026-11-18): el propietario aprobó el contrato técnico ("APRUEBO EL CONTRATO TÉCNICO v1.0"). Contrato v1.3 (CR-011..CR-013; 2026-11-19) en `implementation/`; pendientes de FASE 2: reverificar el OCO contra el exchange real, tipo de la pierna TP, esquema del evento de señal de salida, nombres de motivos de NO_SETUP.
- Decisiones: DEC-001..DEC-013. Change requests CR-001..CR-013 aprobadas y aplicadas (CR-011: candidatos en conflicto, Walk-Forward, sizing; CR-012: stop OCO con STOP_LOSS de mercado; CR-013: fuente de datos y snapshot; todas 2026-11-19; contrato v1.3). CONF-006 resuelta. Verificación: G2 (2026-11-13) y VER-003 (re-verificación y cierre).
- Producción en Laptop B; desarrollo e investigación en Laptop A; vigilancia con servicio externo (DEC-007). IA: Haiku 5.5 en 4 agentes, Sonnet 5.5 en Decision Synthesis (DEC-009).
- Pendiente diferido: REQ-G-P08 (validación fiscal con contador); bloquea cálculos fiscales, no FASE 2.
- Cambios al contrato desde ahora: solo con solicitud de cambio aprobada y versionado (v1.x).
- **FASE 2 BLOQUEADA** hasta la frase exacta "AUTORIZO INICIO DE FASE 2". Código funcional creado: NINGUNO.
- Siguiente acción autorizada: esperar autorización de FASE 2. Al iniciarla: poblar `feature_list.json` desde el contrato aprobado, empezando por la Fase 1 de implementación (Fundamentos de integración, architecture.md §7).

> Actualizado: 2026-11-18 — FASE 1 completa: G0..G3 PASS; contrato v1.0 aprobado; FASE 2 pendiente de autorización

---

## Estado Actual de Gates

| Gate | Nombre | Estado | Requiere aprobación humana |
|------|--------|--------|---------------------------|
| G0 | Integridad y registro documental | **PASS** | No |
| G1 | Cobertura de extracción | **PASS** | No |
| G2 | Consistencia y trazabilidad | **PASS** | No |
| G3 | Aprobación humana del contrato | **PASS** (propietario, 2026-11-18) | SÍ |
| G4 | Pruebas de implementación | PENDING | No |
| G5 | Integración y regresión | PENDING | No |
| G6 | Seguridad | PENDING | No |
| G7 | Aprobación de release | PENDING | SÍ |

---

## Próxima Acción Requerida: autorización de FASE 2

G3 aprobado el 2026-11-18. FASE 2 requiere la frase exacta del propietario: **"AUTORIZO INICIO DE FASE 2"**. Paquete de revisión de G3: `harness/gates/G3_resumen_contrato.md`.

---

## Resumen de Extracción

| Documento | ID | Requisitos | Formato IDs |
|-----------|-----|-----------|-------------|
| OWNEW_CONTEXT.md | DOC-001 | 22 | REQ-1001..1022 |
| CONTEXTO_FISCAL_OPERATIVO.md | DOC-002 | 15 | REQ-2001..2015 |
| AI_INTEGRATION.md | DOC-003 | 75 | REQ-3001..3075 |
| PROFILE_AND_OPERATIONAL_POLICIES.md | DOC-004 | 38 | REQ-4001..4038 |
| RISK_POLICY.md | DOC-005 | 42 | REQ-5001..5042 |
| TRACEABILITY_MATRIX.md | DOC-006 | 32 | REQ-6001..6032 |
| **TOTAL** | | **224** | |

Nota: Extracción completa. Las 6 extracciones cubren íntegramente los 6 documentos fuente.

---

## Conflictos Registrados

| ID | Estado |
|----|--------|
| CONF-001 | RESUELTA (DEC-001) — TRACEABILITY_MATRIX = BORRADOR |
| CONF-002 | RESUELTA (DEC-001) |
| CONF-003 | RESUELTA (DEC-003) — régimen 605; tratamiento fiscal sujeto a validación profesional (P08) |
| CONF-004 | RESUELTA (DEC-002) — 1.5% máximo vinculante |
| CONF-005 | RESUELTA (DEC-002) — solo BTC/USDT |

**CR-001** APROBADA y aplicada el 2026-11-17 (1–2% y ETH/USDT eliminados; TRACEABILITY_MATRIX corregida).

**Historial fiscal (confirmado por el propietario el 2026-11-17, cerrado):** régimen 616 hasta el 12/10/2025; el 605 debió iniciar el 13/10/2025; el aviso ante el SAT se presentó el 17/11/2026. No hay fecha pendiente.

**Diferido por el propietario (2026-11-17):** la validación con contador (REQ-G-P08) queda para después; no se calcula nada fiscal mientras tanto. G3 se mantiene PENDING.

---

## Parámetros PENDING

**Resueltos en DEC-004 (2026-11-17):** P01–P06, P19, P20 (fuente FX, antigüedad, comisión, slippage, filtros, Telegram, reconciliación, tolerancia de precio).

**Resueltos en DEC-005 (2026-11-17):** P10–P17, P21–P24 (investigación y ML).

**Resueltos en DEC-006 (2026-11-17):** P07, P18, P25 y P26 (nuevo: recuperación ante fallos).

**Todos los parámetros del Módulo 15 están resueltos excepto P08 (diferido).**

**CR-002** (stop-loss en Binance) APROBADA y aplicada el 2026-11-17 (REQ-G-031, eventos STOP_ORDER_*, TC-STOP-001..006).

**Diferido por el propietario:** P08 (validación fiscal con contador; incluye tratamiento de ganancias y periodo 13/10/2025–17/11/2026).


---

## Archivos del Harness (todos validados)

```
harness/manifest.json              — G2_PASS, todos los docs VERIFIED
harness/gates/gate_status.json     — G0=PASS, G1=PASS, G2=PASS, G3..G7=PENDING
harness/extraction/outputs/        — 6 archivos JSON, 224 requisitos
harness/verification/VER-001.json  — reporte adversarial PASS
implementation/requirements.md     — contrato de requisitos DRAFT
implementation/architecture.md     — contrato de arquitectura DRAFT
implementation/api_contracts.md    — contratos de API DRAFT
implementation/data_flow.md        — flujo de datos DRAFT
implementation/test_plan.md        — plan de pruebas DRAFT
implementation/conflict_register.md — CONF-001, CONF-002 resueltos
```

---

## Reglas para el Próximo Agente

1. G3 aprobado por el propietario (2026-11-18); G7 solo con autorización humana explícita
2. Si el propietario aprueba G3, marcar gate_status.json con `approved_by: "propietario"`, `approved_at: "fecha"` y `evidence: "texto de la aprobación"`
3. FASE 2 está BLOQUEADA hasta "AUTORIZO INICIO DE FASE 2"
4. Los archivos en `docs/` son SOLO LECTURA — fuentes documentales del propietario
5. Los archivos en `src/` están vacíos — correctamente, hasta FASE 2
6. Los parámetros PENDING no se rellenan por suposición — solo con información real del propietario o del sistema Binance
7. No crear código funcional de SwingPilot hasta la autorización de FASE 2
