# session-handoff.md — SwingPilot Harness

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
