# DEC-012 — Tipo de orden del stop en Binance (REQ-G-031)

**Fecha:** 2026-11-19
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensajes del propietario en la sesión del 2026-11-19 (decisión del tipo de orden y aprobación de CR-012: "Aprobado"; observaciones 1 y 2 confirmadas). Ver `harness/change_requests/CR-012_tipo-orden-stop-oco.md`.
**Alcance:** Resuelve el pendiente técnico «stop-limit vs OCO» de CR-002 / REQ-G-031. Se aplica al contrato mediante CR-012 (contrato v1.2). NO autoriza FASE 2.

---

## Decisiones

| Tema | Decisión |
|---|---|
| Tipo de orden del stop | **OCO** de Binance Spot. Pierna de stop: **STOP_LOSS de mercado** (no stop-limit); se ejecuta a mercado cuando el precio toca el stop. |
| Pierna de take-profit | Opcional; para una posición long, **TAKE_PROFIT_LIMIT** (confirmado por el propietario; el tipo definitivo se fija en la implementación). Sin TP: orden `STOP_LOSS` individual, porque el OCO exige dos piernas. |
| Cancelación | Al ejecutarse una pierna, la otra se cancela automáticamente. |
| Modificación del stop | Cancelar y reemplazar la lista OCO completa (REQ-G-027). |
| Contingencia | Si Binance no permitiera OCO con STOP_LOSS de mercado: documentar la limitación y usar STOP_LIMIT con precio límite a 0.5% de distancia del precio de stop. Verificado el 2026-11-19 contra la documentación oficial: la limitación no se produce (`belowType=STOP_LOSS`); se reverifica contra el exchange real en FASE 2. |
| Slippage | Riesgo residual aceptado y documentado, **no cota dura**: la orden de mercado siempre llena pero no acota el deslizamiento, que puede superar la reserva de sizing de 0.10% (REQ-G-P04) y exceder el 1.5% de INV-001 en un hueco extremo. La pérdida queda acotada por «stop + slippage real». |

## Justificación registrada

- Un STOP_LIMIT no ejecuta en un hueco de precio y rompe la cota del 1.5% (INV-001); el STOP_LOSS de mercado siempre llena.
- BTC/USDT en Binance Spot es un par muy líquido: el propietario considera despreciable el impacto de slippage para el tamaño de posición del perfil actual (riesgo de ~$45 MXN por operación, 1.5% de un equity de $3,000 MXN).
- La aclaración de CR-011 sobre MONTHLY_DRAWDOWN_LOCK sigue válida con la precisión de que la cota es stop + slippage real.

## Mantiene sin cambios
Monitoreo en software como segunda capa; STOP_ORDER_FAILED y Fail-Closed; cierre protector autónomo (DEC-008 Q25); reconciliación de que toda posición abierta tiene su stop activo.
