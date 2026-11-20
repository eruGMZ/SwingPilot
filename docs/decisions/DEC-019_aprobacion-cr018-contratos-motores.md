# DEC-019 — Aprobación de CR-018 rev. 3 (contratos de los motores de la Fase 2)

**Fecha:** 2026-11-20
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-20: «Apruebo CR-018 rev. 3».
**Alcance:** aprueba `harness/change_requests/CR-018_contratos-motores-cuantitativos.md` rev. 3 completa (B.0–B.8, incluido B.7.1) y su aplicación según B.9. Contrato v1.5 → **v1.6**.

## Decisión

| Elemento | Decisión |
|---|---|
| B.0 | Reglas comunes de los eventos de motores (sobre, tiempos, `data_refs`, `result_status`, códigos de error, sin confianza) — aprobadas |
| B.1 | Catálogo: + `STRATEGY_EXIT_SIGNAL` y `STOP_ADJUSTMENT_REQUESTED` (33 tipos) — aprobado |
| B.2–B.5 | REGIME_CLASSIFIED, ML_INFERENCE_COMPLETED (`NO_ACTIVE_MODEL`), STRATEGY_CANDIDATE, STRATEGY_EXIT_SIGNAL — aprobados |
| B.6 | `STOP_ADJUSTMENT_REQUESTED` como solicitud (DEC-018 decisión 2) — aprobado |
| B.7 | Motivos estructurados de NO_SETUP; `PRE_PHASE3_BLOCK`; errores técnicos fuera de NO_SETUP (DEC-018 decisión 3) — aprobado |
| B.7.1 | Error técnico del Strategy Engine en `STRATEGY_CANDIDATE` con `result_status = ERROR`, sobre `FAILED`, campos de candidato prohibidos; `INVALID_CANDIDATE` como error técnico — aprobado |
| B.8 | Normalización determinista de TRADE_PROPOSAL desde el candidato; §4.1 v1.1.0 aditivo — aprobado |

## Efectos

- `implementation/*.md` → v1.6; `api_contracts.md` §3.8 transcribe B.0–B.8; casos nuevos TC-MSG-004/005, TC-FLOW-009/010/011, TC-NORM-001/002/003.
- `src/swingpilot/contracts/message.py`: catálogo de 33 tipos.
- Desbloquea, según sus demás dependencias: FEAT-019 AC-019-4; FEAT-020; FEAT-021; FEAT-022; FEAT-018 (con `UNCLASSIFIED` hasta aprobar los parámetros de la clasificación, DEC-018 decisión 1).
- **No autoriza** su implementación por sí misma: el inicio del código de FEAT-018..022 queda a indicación del propietario. Siguen vigentes las restricciones de DEC-017/DEC-018 (sin OOS/LOCKBOX, sin credenciales privadas, sin activar estrategias, IA $0.50 sin consumo, sin commit ni push).
