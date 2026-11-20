# DEC-018 — Revisión de IMPL-3: Regime Engine (Q42), CR-018 B.6/B.7, EXP-0001 y autorización parcial de implementación

**Fecha:** 2026-11-20
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensaje del propietario en la sesión del 2026-11-20 («Reviso la propuesta y tomo estas decisiones»), sobre `harness/plans/IMPL-3_Q42_regime_engine_propuesta.md`, `harness/change_requests/CR-018_contratos-motores-cuantitativos.md` y los criterios de FEAT-015..022.
**Alcance:** Decide Q42, CR-018 B.6 y B.7, el tratamiento de EXP-0001 y autoriza la implementación de una parte de IMPL-3. **NO aprueba CR-018 en su conjunto**: el contrato sigue en v1.5 y FEAT-018, FEAT-020, FEAT-021 y FEAT-022 siguen bloqueadas.

---

## Decisiones

| # | Tema | Decisión |
|---|---|---|
| 1 | Q42 — Regime Engine v1 | **Alternativas B + D aprobadas.** Clasificación de volatilidad D1 en **tres categorías** mediante percentiles calculados exclusivamente con datos pasados. Las mediciones de dirección son **contexto, no categorías adicionales**. Los parámetros deben justificarse con Train. |
| 2 | CR-018 B.6 | **Incorporar `STOP_ADJUSTMENT_REQUESTED`.** Es una solicitud: nunca una modificación ejecutada ni una autorización para reducir protecciones. |
| 3 | CR-018 B.7 | **`NO_SETUP` con motivo `PRE_PHASE3_BLOCK`** para el control previo a la Fase 3. Los errores técnicos permanecen como `ERROR`, no como `NO_SETUP`. |
| 4 | EXP-0001 | **No completar ni preregistrar el piloto** hasta recuperar la documentación de EXP-0001 y comprobar la integridad de las particiones. EXP-0001 y Mean Reversion H1 se cuentan en el historial de experimentación. |
| 5 | Autorización de implementación | **Autorizada:** FEAT-015 (snapshot), FEAT-016 (datos en vivo), la infraestructura general de FEAT-017 (sin preregistro definitivo del piloto) y la infraestructura de FEAT-019 (sin modelo entrenado). **Bloqueadas** hasta resolver CR-018 y sus dependencias: FEAT-018, FEAT-020, FEAT-021, FEAT-022. |

## Restricciones vigentes

- No evaluar OOS ni LOCKBOX.
- No utilizar credenciales privadas de Binance.
- No activar estrategias.
- Presupuesto de IA de IMPL-3: USD 0.50, sin consumirlo por defecto (DEC-017 Q47).
- Siguen vigentes las condiciones generales de DEC-017 (sin commit ni push sin autorización).

## Efectos en los documentos del Harness

- **CR-018:** se actualiza a revisión 2 con B.6 (opción 1, con la restricción de la decisión 2) y B.7 (`PRE_PHASE3_BLOCK`; `UPSTREAM_ERROR` sale de `NO_SETUP`). La enumeración de `regime_label` queda acotada por la decisión 1. Sigue pendiente de aprobación global.
- **feature_list.json:** FEAT-015, FEAT-016, FEAT-017 (infraestructura) y FEAT-019 (infraestructura) pasan a IN_PROGRESS; FEAT-018, FEAT-020, FEAT-021 y FEAT-022 a BLOCKED.
- **Pendiente de decisión del propietario:** los nombres exactos de las tres categorías de volatilidad, los percentiles de corte, la ventana mínima, la histéresis y la persistencia. Se proponen con su justificación en Train cuando la snapshot exista; no se fijan por suposición.
