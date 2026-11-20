# DEC-020 — Aprobación de CR-019 (evento de rechazo de la normalización de TRADE_PROPOSAL)

**Fecha:** 2026-11-20
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-20: «Apruebo CR-019». Antes eligió la opción A de CONF-008 («redacta CR-019 opción A»).
**Alcance:** aprueba `harness/change_requests/CR-019_evento-rechazo-normalizacion.md` completa (B.1–B.7) y su aplicación. Contrato v1.6 → **v1.7**. Como indica la sección E de la CR, presentada al propietario antes de aprobarla, la aprobación cubre también la implementación de la sección C con pruebas de regresión y el cierre de CONF-008.

## Decisión

| Elemento | Decisión |
|---|---|
| B.1 | Catálogo: se añade `PROPOSAL_NORMALIZATION_REJECTED` (34 tipos). Aprobado |
| B.2 | `api_contracts.md` §3.8 B.10: cuándo se emite, posición E9, sobre, payload y campos prohibidos. Aprobado |
| B.3 | Referencias en B.8 puntos 2 y 5. Aprobado |
| B.4 | `data_flow.md` §5: E9 = TRADE_PROPOSAL \| PROPOSAL_NORMALIZATION_REJECTED. Aprobado |
| B.5 | REQ-G-063: 34 tipos. Aprobado |
| B.6 | TC-NORM-002 actualizada; TC-NORM-004 y TC-NORM-005 nuevas. Aprobado |
| B.7 | Contrato v1.7. Aprobado |

## Efectos

- Resuelve CONF-008 y permite cerrar QA3E-01 (FEAT-021 y FEAT-022).
- No afecta al riesgo ni a la ejecución: el evento es de auditoría, no lo consume el Risk Manager y no autoriza nada (REQ-G-073).
- Siguen vigentes las restricciones de DEC-017 y DEC-018: sin OOS ni LOCKBOX, sin credenciales privadas, sin activar estrategias y sin consumo del presupuesto de IA. El push sigue requiriendo la indicación del propietario.
