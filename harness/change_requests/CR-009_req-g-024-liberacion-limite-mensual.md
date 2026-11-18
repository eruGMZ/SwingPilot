# CR-009 — Liberación del límite mensual en REQ-G-024

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("agrega C-03") y aplicada.
**Origen:** hallazgo C-03 (BAJA) de la verificación de cierre de CR-008 (`harness/verification/VER-003_reverificacion_contrato_v0.2.md`).

## Cambio

`implementation/requirements.md`, REQ-G-024 (estados del Risk Manager): añadir «MONTHLY_TRADE_LIMIT_LOCK se libera automáticamente al inicio del mes calendario siguiente, con aviso por Telegram (DEC-010 Q28); los demás bloqueos siguen sus propias reglas de liberación».

La regla ya estaba en `data_flow.md` §6 y en TC-PARAM-005; este cambio la lleva al requisito.

## Impacto

Ninguno nuevo: reproduce una decisión aprobada (DEC-010). Sin pruebas nuevas (cubierto por TC-PARAM-005).
