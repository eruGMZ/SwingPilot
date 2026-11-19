# DEC-014 — Evento del Strategy Analyst y zona horaria del mes calendario del presupuesto de IA

**Fecha:** 2026-11-19
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensaje del propietario en la sesión del 2026-11-19 (FASE 2): «Apruebo CR-015, usa America/Mexico_City … CR-015: Aprobado. Aplica B.1–B.5, marca CONF-007 como RESUELTA, registra en progress.md».
**Alcance:** Registra decisiones del propietario. Q30 se aplica al contrato mediante CR-015 (contrato v1.4) y resuelve CONF-007. Q31 es un parámetro de implementación de REQ-G-096; no modifica el texto del contrato.

---

## Decisiones

| ID | Tema | Decisión |
|---|---|---|
| Q30 | Tipo de evento del análisis del Strategy Analyst (CONF-007) | **Aprobada CR-015:** se añade `STRATEGY_ANALYSIS_COMPLETED` (productor Strategy Analyst, consumidor AI Orchestrator) al catálogo de `api_contracts.md` §2 y se nombra E7 en `data_flow.md` §5. |
| Q31 | Zona horaria del «mes calendario» del presupuesto de IA (REQ-G-096 (1)(2); DEC-010 Q29) | **America/Mexico_City.** El gasto mensual y el aviso único AI_BUDGET_WARNING se cuentan por mes calendario en esa zona horaria. |

## Notas

- Q31 aplica al presupuesto de IA. No se extiende por esta decisión a otros cortes mensuales del contrato (MonthlyBaseline, MONTHLY_TRADE_LIMIT_LOCK), cuya zona horaria no está definida y queda PENDING para cuando se implementen.
