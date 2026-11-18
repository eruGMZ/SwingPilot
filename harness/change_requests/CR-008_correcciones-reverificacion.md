# CR-008 — Correcciones de la re-verificación adversarial (VER-003)

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-008, Q28 A, Q29 A") y aplicada. Decisiones Q28 y Q29 registradas en DEC-010.
**Origen:** `harness/verification/VER-003_reverificacion_contrato_v0.2.md` (hallazgos V1-01..11, V2-01..14, O-01). Opción A de G3.
**Naturaleza:** correcciones de fidelidad a las fuentes y a decisiones aprobadas, más dos decisiones del propietario (§E).

---

## A. Riesgo y ejecución

1. **Salida discrecional (V1-01).** `api_contracts.md` §4.1: `exit_mechanism.type` pasa a `STOP_LOSS|TRAILING_STOP|TARGET_PRICE`; se elimina `MANUAL`. TC-INV-007-B: Input `exit_mechanism.type = "MANUAL"` o salida que dependa solo de una decisión discrecional futura → Expected RISK_REJECTED (INV-007). Fuente: RISK_POLICY, «Condición de rechazo».
2. **Fallo del stop (V1-03).** `data_flow.md` §2: «(bloqueo de nuevas entradas; cierre o intervención del propietario)» → «(bloqueo de nuevas entradas; tratamiento según REQ-G-031: recolocar el stop o cierre protector)».
3. **Evento de auditoría (V1-04).** `api_contracts.md` §6: añadir campos de primer nivel `operation_id`, `equity`, `risk_budget`, `effective_risk`, `position_size`, `decision` (`APPROVED|REJECTED|BLOCKED`), `reason`, `actor`. Fuente: RISK_POLICY, «Información mínima por evento».
4. **Vigencia (V1-05).** `api_contracts.md` §4.2: eliminar `valid_until_utc` de la salida del Risk Manager y añadir la nota: «La vigencia de la autorización la fija el backend de autorización al enviar la solicitud por Telegram (REQ-G-039); el Risk Manager re-verifica las condiciones al ejecutar (REQ-G-042)».
5. **Parámetros resueltos sin prueba (V1-07).** `data_flow.md` §1 Fase 6: añadir «desviación de precio > 0.5% respecto a la propuesta autorizada → nueva autorización (REQ-G-P20)». `test_plan.md` nueva §8.8 «Parámetros operativos (C1)»:
   - TC-PARAM-001 — Precio al ejecutar se desvía > 0.5% del autorizado → no se envía la orden; se requiere nueva autorización.
   - TC-PARAM-002 — Tipo de cambio USDT/MXN con antigüedad > 5 min → Fail-Closed (DATA_UNAVAILABLE), sin propuesta.
   - TC-PARAM-003 — Reconciliación al arrancar, antes y después de cada ciclo de decisión y cada 5 min con posición abierta.
   - TC-PARAM-004 — Comisión usada en el sizing = max(comisión real, 0.10%) por lado.
6. **REQ-G-030 (V1-08).** Sustituir la «lista reconstructiva» por los 16 criterios textuales de RISK_POLICY («¿Cuándo se considera bien implementada esta política?»): (1) equity calculado a partir de saldos y posiciones reales; (2) presupuesto del 1.5% actualizado con el equity actual; (3) sizing con precio, costes y reserva de slippage; (4) redondeo que no permite exceder el presupuesto; (5) no pueden existir dos posiciones abiertas; (6) rechazo de operaciones sin mecanismo de salida; (7) rechazo de cualquier intento de promediar a la baja; (8) drawdown con pérdidas realizadas y no realizadas; (9) bloqueo mensual al 5%; (10) tres pérdidas consecutivas activan la suspensión; (11) los bloqueos requieren las autorizaciones correspondientes para su liberación; (12) los stops no pueden modificarse para ampliar el riesgo inicial; (13) se respeta el límite mensual de ocho operaciones; (14) los agentes no pueden ejecutar sin aprobación humana; (15) errores de datos o sincronización producen comportamiento restrictivo; (16) todos los eventos de riesgo quedan registrados y son auditables. Se elimina la nota «verificar texto definitivo».
7. **TC-STOP-006 (V1-09).** Expected: la reconciliación lo detecta, emite alerta, bloquea nuevas entradas y aplica REQ-G-031 (recolocar o cierre protector; ver TC-STOP-007/008).
8. **P19 (V1-11).** Fila P19: «arranque + antes y después de cada ciclo de decisión + cada 5 min con posición abierta» (DEC-004 Q6).

## B. IA y contratos de agentes

9. **Risk Analyst fuera de la síntesis (V1-02, V2-01).** `api_contracts.md` §3.3: eliminar `agent_summaries.risk_analyst`.
10. **Contratos de agentes completos (V2-02, V2-07).** `api_contracts.md` §3:
    - Añadir `schema_version` a los contratos existentes (§3.1, §3.2, §3.3).
    - **Campos comunes de toda salida de agente** (D2): `analysis_id`, `correlation_id`, `causation_id`, `schema_version`, `agent`, `model_id`, `prompt_version`, `data_timestamp_utc`, `analysis_timestamp_utc`, `sources` (fuentes y referencias), `missing_data` (datos faltantes declarados), `status` (`COMPLETED|INSUFFICIENT_DATA|ERROR`); cada afirmación lleva `statement_type` (`FACT|INFERENCE|RECOMMENDATION`).
    - **Campos comunes de toda entrada de agente:** `correlation_id`, `causation_id`, `schema_version`, `agent`, `data_timestamp_utc`, `context` (datos específicos del agente).
    - **Macro Analyst** (salida): `events[]` con `description`, `potential_impact`, `time_horizon`, `source`, `publication_date`, `confirmation` (`CONFIRMED|RUMOR|SPECULATION`), `uncertainty` (`HIGH|MEDIUM|LOW`). Entrada: fuentes de noticias, información macroeconómica y datos temporales. Fuente: AI_INTEGRATION «Macro Analyst».
    - **Strategy Analyst** (salida): por cada STRATEGY_CANDIDATE, `strategy_id`, `strategy_version`, `logic_assessment`, `activation_conditions_assessment`, `signal_invalidation_coherence`, `weakening_conditions[]`, `comparison` (solo con evidencia suficiente), `discard_reasons[]`. Entrada: STRATEGY_CANDIDATE del Strategy Engine. Fuente: AI_INTEGRATION «Strategy Analyst».
    - **Risk Analyst** (salida): `hidden_risks[]`, `entry_stop_target_inconsistencies[]`, `external_event_exposure[]`, `operational_data_risks[]`, `challenged_assumptions[]`, `advisory_only: true`. Entrada: propuesta con RISK_APPROVED y estado del sistema. Fuente: AI_INTEGRATION «Risk Analyst».
    - **Decision Synthesis** (entrada): salidas de Fase 2 y Fase 3 con sus `analysis_id`.
11. **Orchestrator (V2-04).** `architecture.md` §3.1: «Coordinar análisis paralelos (Market, Macro, ML, Regime)» → «Coordinar el análisis paralelo de Fase 3 (Market, Macro y Strategy Analyst) y los pasos secuenciales (CR-004)».
12. **Fases de implementación (V2-05).** `architecture.md` §7: sustituir por las 6 fases y criterios de salida de AI_INTEGRATION («¿En qué fases se implementa la integración?»): Fundamentos de integración; Agentes especializados; Integración cuantitativa; Integración con riesgo; Paper Trading; Live Trading. Eliminar las referencias a REQ-3048..3059, «v0.1» y FIND-004; los criterios de cierre son AC-01..AC-16 (REQ-3054..3069, test_plan §9).
13. **Cadena de correlación (V2-08).** `data_flow.md` §5: reescribir en el orden vigente (ANALYSIS_REQUESTED → REGIME_CLASSIFIED / ML_INFERENCE_COMPLETED → STRATEGY_CANDIDATE o NO_SETUP → MARKET/MACRO_ANALYSIS_COMPLETED y análisis del Strategy Analyst → DECISION_SYNTHESIS_COMPLETED → TRADE_PROPOSAL → RISK_APPROVED/REJECTED → RISK_ANALYSIS_COMPLETED → autorización → ORDER_SUBMITTED → ORDER_FILLED → STOP_ORDER_PLACED), con cada `causation_id` apuntando al evento que lo causa.
14. **Macro Analyst (V2-11).** REQ-G-053: añadir la salida de la fuente: eventos relevantes, impacto potencial, horizonte temporal, fuentes, fecha de publicación y nivel de incertidumbre.
15. **Fidelidad de autoridad (V2-12).** REQ-G-059: usar el texto fuente («no transformar una recomendación en una orden»). `architecture.md` tabla de autoridad: «Operador autorizado (propietario)» y filas separadas para Strategy Engine y ML Engine según AI_INTEGRATION «¿Quién tiene autoridad sobre qué?».

## C. Investigación y fiscal

16. **Pruebas de DEC-005 (V2-09).** `test_plan.md` §5, añadir:
    - TC-ML-004 — Muestra insuficiente (< 100 trades Train+Val, o < 30 en OOS o LOCKBOX) → experimento INCONCLUSIVE.
    - TC-ML-005 — Umbrales netos: PF ≥ 1.3, expectancy ≥ 0.10 R, drawdown ≤ 20%, Sharpe OOS ≥ 0.8; incumplir cualquiera → REJECTED.
    - TC-ML-006 — IC bootstrap 95% del expectancy > 0, comparación con línea base ingenua y corrección por número de experimentos.
    - TC-ML-007 — LOCKBOX evaluado una sola vez; segundo acceso bloqueado y registrado.
    - TC-ML-008 — Drift: expectancy de los últimos 20 trades < límite inferior del IC OOS, o PSI > 0.25 → modelo suspendido.
    - TC-ML-009 — Promoción a producción solo por HUMAN_REVIEW → APPROVED; el hash datos+código+parámetros queda registrado.
    - TC-ML-010 — Experimentos rechazados quedan registrados (no se descartan resultados desfavorables).
17. **PFAE (V2-13).** REQ-G-115: añadir «Si los tickets superan $50,000 MXN, reevaluar el riesgo de PFAE (CONTEXTO_FISCAL_OPERATIVO); hoy el máximo extraordinario es $10,000 MXN (REQ-G-010)».

## D. Consistencia del contrato

18. **Parámetros resueltos (V1-06, V2-06).** `api_contracts.md` §9, `data_flow.md` §7 y línea de `tc_mxn_usd` en §4, `architecture.md` §8 y `test_plan.md` §12: marcar los parámetros resueltos con su DEC; solo P08 queda PENDING.
19. **Número de eventos (V1-10, V2-03).** REQ-G-063: «31 tipos» → «30 tipos». (Fe de erratas de CR-007 §B.1.) Con los eventos de esta CR no se agregan tipos nuevos.
20. **G4 y G6 (V2-10).** `test_plan.md` §9: «Su ejecución con evidencia es condición de G4; TC-AC-16 es además condición de G6».

## E. Decisiones del propietario

21. **Q28 — Liberación de MONTHLY_TRADE_LIMIT_LOCK (O-01).** RISK_POLICY no la define (criterio 11: «requieren las autorizaciones correspondientes»). `data_flow.md` §6 la tiene como «al inicio del mes siguiente (PENDING: ratificación)».
    - **A (recomendada):** liberación automática al inicio del mes calendario siguiente, con aviso por Telegram. El límite es mensual por definición y alcanzarlo no indica deterioro (a diferencia del drawdown); la «autorización correspondiente» es la propia regla mensual que aprobaste.
    - B: liberación solo con tu autorización expresa.
22. **Q29 — Aviso de presupuesto de IA (V2-14).** TC-AI-006 dice «una sola vez en el mes», que no está en CR-006.
    - **A (recomendada):** ratificarlo y añadirlo a REQ-G-096 (evita avisos repetidos en cada ciclo).
    - B: quitarlo de la prueba (el aviso podría repetirse en cada ciclo sobre $4).

---

## Documentos del contrato afectados

`requirements.md` (REQ-G-030, 053, 059, 063, 096 si Q29 = A, 115; fila P19), `architecture.md` (§3.1, §7, §8, tabla de autoridad), `api_contracts.md` (§3, §4.1, §4.2, §6, §9), `data_flow.md` (§1 Fase 6, §2, §4, §5, §6, §7), `test_plan.md` (TC-INV-007-B, TC-STOP-006, §5, §8.8 nueva, §9, §12). Encabezados a v0.3.

## Impacto

- **Arquitectónico:** ninguno nuevo; completa contratos que D2 ya exigía.
- **Riesgo:** reduce (salida discrecional prohibida, pruebas de parámetros y de investigación, auditoría completa).
- **Tras aplicar:** verificación de cierre acotada a los cambios de esta CR (no una re-verificación completa) y G3.

## Aprobación

Aprobada el 2026-11-18 con "APRUEBO CR-008, Q28 A, Q29 A". Aplicada en los cinco documentos del contrato (v0.3). Adicional derivado de Q28: TC-PARAM-005 (liberación del límite mensual) en `test_plan.md` §8.8.
