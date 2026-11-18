# VER-003 — Re-verificación adversarial del contrato v0.2

**Fecha:** 2026-11-18
**Alcance:** contrato técnico v0.2 (CR-001..CR-007 aplicadas), hallazgo H1 del paquete de G3.
**Verificadores:** 2 sub-agentes independientes (Claude Sonnet 5.5, solo lectura), sin acceso a extracciones, verificaciones previas, paquete de G3, `progress.md` ni `session-handoff.md`.
- **V1 — riesgo y ejecución:** RISK_POLICY, OWNEW_CONTEXT, DEC-002/004/006/007/008, CR-002..005 contra requirements Módulos 1–4, data_flow §1 (fases 5–7), §2, §6; api_contracts §2, §4, §5; test_plan §3, §4, §8.1–8.6.
- **V2 — IA, investigación, fiscal y trazabilidad:** AI_INTEGRATION, PROFILE_AND_OPERATIONAL_POLICIES, TRACEABILITY_MATRIX, CONTEXTO_FISCAL_OPERATIVO, DEC-001/003/005/009, CR-001/006/007 contra requirements Módulos 5–14, architecture, api_contracts §1, §3, §6–8, data_flow restante, test_plan §5–7, §8.7, §9.

**Veredicto:** V1 PASS_WITH_FINDINGS; V2 PASS_WITH_FINDINGS. **Sin hallazgos críticos.**

**Comprobación del Orquestador:** cada hallazgo se contrastó con el contrato y la fuente. "Confirmado" = comprobado por el Orquestador; "Plausible" = coherente con lo revisado, se confirma al aplicar la corrección.

**Consumo:** V1 ~131K tokens, V2 ~151K tokens (por encima de la guía de 80K por sub-agente Sonnet; el alcance asignado era mayor que el presupuesto).

---

## Hallazgos

| ID | Sev. | Hallazgo | Estado |
|---|---|---|---|
| V1-01 | ALTA | `exit_mechanism.type` admite `MANUAL`; RISK_POLICY rechaza salidas que dependen exclusivamente de una decisión discrecional futura. | Confirmado |
| V1-02 / V2-01 | ALTA | La salida de Decision Synthesis incluye `agent_summaries.risk_analyst`; desde CR-004 el Risk Analyst corre después del Risk Manager. | Confirmado |
| V2-02 | ALTA | Faltan contratos de Macro Analyst, Strategy Analyst y Risk Analyst, y los de entrada de todos salvo Market Analyst (D2: entrada y salida por agente). | Confirmado |
| V1-03 | MEDIA | data_flow §2 mantiene "cierre o intervención del propietario" ante STOP_ORDER_FAILED; CR-005 lo eliminó. | Confirmado |
| V1-04 | MEDIA | El evento de auditoría no tiene `operation_id`, `decision`, `reason` ni `actor` explícitos (RISK_POLICY "Información mínima por evento"). | Confirmado |
| V1-05 | MEDIA | `valid_until_utc` aparece en la salida del Risk Manager; REQ-G-039 lo fija el backend al enviar la solicitud. | Confirmado |
| V1-06 / V2-06 | MEDIA | Tablas de parámetros PENDING en api_contracts §9, data_flow §7 y línea de tc_mxn_usd, architecture §8 y test_plan §12 listan como pendientes parámetros ya resueltos. | Confirmado |
| V1-07 | MEDIA | Sin pruebas ni ubicación en el flujo para la tolerancia de 0.5% (P20), el tipo de cambio > 5 min (P02) y la frecuencia de reconciliación (P19). | Confirmado |
| V1-08 | MEDIA | REQ-G-030 lista 16 criterios "reconstructivos" distintos de RISK_POLICY ("¿Cuándo se considera bien implementada…?"). | Confirmado |
| V2-04 | MEDIA | architecture §3.1: paralelo "Market, Macro, ML, Regime"; desde CR-004 es Market, Macro y Strategy Analyst. | Confirmado |
| V2-05 | MEDIA | architecture §7: fases de implementación distintas a AI_INTEGRATION; referencias obsoletas (REQ-3048..3059, FIND-004). | Confirmado |
| V2-07 | MEDIA | Contratos de agente sin `schema_version` (D2 y TC-AC-02 lo exigen). | Confirmado |
| V2-08 | MEDIA | data_flow §5: cadena de correlación con orden previo a CR-004 y `causation_id` genérico. | Confirmado |
| V2-09 | MEDIA | Sin pruebas para los criterios de DEC-005 (P11–P17, P22, P23, LOCKBOX de un solo uso). | Plausible |
| V1-09 | BAJA | TC-STOP-006 espera solo alerta y bloqueo; REQ-G-031 (CR-005) exige recolocar o cierre protector. | Confirmado |
| V1-10 / V2-03 | BAJA | REQ-G-063 dice 31 tipos de evento; el catálogo tiene 30 (error introducido por CR-007). | Confirmado |
| V1-11 | BAJA | Fila P19 omite "antes y después de cada ciclo" (DEC-004 Q6). | Plausible |
| V2-10 | BAJA | test_plan §9: "antes de G6" y "condición de G4" para la misma ejecución. | Confirmado |
| V2-11 | BAJA | REQ-G-053 omite la salida del Macro Analyst (eventos, impacto, horizonte, fuentes, fecha, incertidumbre). | Confirmado |
| V2-12 | BAJA | REQ-G-059 y tabla de autoridad de architecture difieren del texto fuente. | Plausible |
| V2-13 | BAJA | Falta la nota de CONTEXTO_FISCAL de reevaluar PFAE si los tickets superan $50,000 MXN (la de swaps ya está cubierta por la prohibición de REQ-G-005). | Confirmado |
| V2-14 | BAJA | TC-AI-006 exige el aviso "una sola vez en el mes"; ni REQ-G-096 ni CR-006 lo dicen (añadido del Orquestador al aplicar CR-006). | Confirmado |

## Hallazgo adicional del Orquestador

| ID | Sev. | Hallazgo |
|---|---|---|
| O-01 | MEDIA | data_flow §6: la liberación de MONTHLY_TRADE_LIMIT_LOCK "al inicio del mes calendario siguiente" sigue marcada "PENDING: requiere ratificación del propietario" desde G2 (FIND-003). RISK_POLICY no define la liberación; su criterio 11 exige "las autorizaciones correspondientes". Requiere decisión del propietario. |

## Correcciones

Tramitadas en CR-008.

---

## Verificación de cierre de CR-008 (2026-11-18)

**Verificador:** 1 sub-agente independiente (Claude Sonnet 5.5, solo lectura, ~80K tokens), sin acceso a este informe ni al paquete de G3.
**Resultado:** los 22 puntos de CR-008 aplicados y conformes. **Veredicto: PASS_WITH_FINDINGS** (solo BAJA).

| ID | Sev. | Hallazgo | Tratamiento |
|---|---|---|---|
| C-01 | BAJA | api_contracts.md §3.0 decía «secciones 3.1–3.8»; el contrato llega a 3.7. | Corregido como errata de la aplicación de CR-008. |
| C-02 | BAJA | REQ-G-063 conserva «Catálogo inicial de 16 tipos» con la cifra vigente (30) entre paréntesis; redacción confusa pero correcta. | Sin cambio (texto de origen preservado). |
| C-03 | BAJA | REQ-G-024 (estados del Risk Manager) no menciona la liberación automática de MONTHLY_TRADE_LIMIT_LOCK (DEC-010 Q28); está en data_flow §6 y TC-PARAM-005. CR-008 no lo exigía. | Aplicado en CR-009. |

Comprobado sin hallazgos: ausencia de `valid_until_utc` en la salida del Risk Manager, de MANUAL como salida y de `risk_analyst` en la síntesis; solo P08 PENDING; IDs de TC y eventos existentes; encabezados v0.3; Q28/Q29 reflejados.
