# DEC-010 — Liberación del límite mensual de operaciones y aviso de presupuesto de IA

**Fecha:** 2026-11-18
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Re-verificación adversarial VER-003 (hallazgos O-01 y V2-14). Preguntas Q28–Q29 de CR-008; opciones y recomendaciones presentadas en la sesión.
**Alcance:** Registra las decisiones. Se aplican al contrato mediante CR-008. NO constituye aprobación de G3 ni autoriza FASE 2.

---

| Pregunta | Tema | Decisión |
|---|---|---|
| Q28 | Liberación de MONTHLY_TRADE_LIMIT_LOCK | **Opción A:** liberación automática al inicio del mes calendario siguiente, con aviso por Telegram. Cierra el pendiente FIND-003 de G2. |
| Q29 | Frecuencia del aviso AI_BUDGET_WARNING | **Opción A:** una sola vez por mes calendario, al alcanzar $4. |

## Justificación registrada

- **Q28:** el límite de 8 operaciones es mensual por definición (REQ-G-004) y alcanzarlo no indica deterioro, a diferencia de MONTHLY_DRAWDOWN_LOCK (que no se libera por cambio de mes) y LOSS_STREAK_LOCK. Para este bloqueo, la «autorización correspondiente» que exige RISK_POLICY (criterio 11) es esta decisión del propietario sobre la regla mensual. La liberación no elimina otros bloqueos activos (REQ-G-024).
- **Q29:** evita repetir el aviso en cada ciclo una vez superados los $4.
