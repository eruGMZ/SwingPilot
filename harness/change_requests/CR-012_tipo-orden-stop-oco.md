# CR-012 — Tipo de orden del stop en Binance (REQ-G-031): OCO con STOP_LOSS de mercado

**Fecha:** 2026-11-19
**Estado:** APROBADA por el propietario el 2026-11-19 ("Aprobado") y APLICADA (contrato v1.2; DEC-012).
**Origen:** decisión del propietario (sesión 2026-11-19) sobre el pendiente técnico de CR-002 / REQ-G-031 («stop-limit vs OCO»). Valores del propietario; no se han inventado valores.

## Decisión del propietario (a registrar como DEC-012 al aprobar)
1. Stop en **OCO** de Binance Spot. Pierna de stop: **STOP_LOSS de mercado** (no stop-limit); se ejecuta a mercado cuando el precio toca el stop.
2. Pierna de take-profit (limit): **opcional**. Si no se define TP, solo la pierna de stop (ver observación 2).
3. Al ejecutarse una pierna, la otra se cancela automáticamente.
4. Razón: un STOP_LIMIT no ejecuta en un hueco de precio y rompe la cota del 1.5% (INV-001); la orden de mercado siempre llena.
5. **Contingencia:** si Binance no permitiera OCO con STOP_LOSS de mercado, documentar la limitación y usar STOP_LIMIT con precio límite a 0.5% de distancia del precio de stop.

## Verificación contra la documentación de Binance (2026-11-19)
Documentación oficial de Spot (`POST /api/v3/orderList/oco`, «New Order list - OCO»): `belowType` admite `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT`; `aboveType` admite además `LIMIT_MAKER`. Se exige una orden limit y otra `STOP_LOSS`/`STOP_LOSS_LIMIT`; la pierna `STOP_LOSS` solo usa precio de stop (sin precio límite). **La limitación prevista en el punto 5 no se produce**: el OCO con STOP_LOSS de mercado está soportado. La contingencia se conserva solo como respaldo documental. Debe reverificarse contra el exchange real en FASE 2 (el contrato exige datos reales).

## Cambio propuesto
`requirements.md` REQ-G-031: sustituir el PENDING de tipo de orden por: OCO con pierna inferior `STOP_LOSS` (mercado) y, si hay TP, pierna superior limit; sin TP, orden `STOP_LOSS` individual (el OCO exige dos piernas). Modificar el stop (REQ-G-027) = cancelar y reemplazar la lista OCO completa. Se mantienen: monitoreo en software como segunda capa, STOP_ORDER_FAILED, cierre protector (DEC-008 Q25), reconciliación.
Afecta además: `data_flow.md` (colocación del stop), `test_plan.md` (TC-STOP: pierna ejecutada cancela la otra; sin TP; reemplazo; hueco de precio con ejecución a mercado). Contrato v1.1 → v1.2.

## Observaciones (no resueltas por este CR)
1. **«Siempre llena» no equivale a «acotado».** La orden de mercado elimina el riesgo de no ejecución, pero no acota el deslizamiento: en un hueco fuerte el precio de salida puede quedar por debajo del stop más allá de la reserva de slippage del sizing (REQ-G-P04, 0.10%) y exceder el 1.5% de INV-001. El riesgo residual es el deslizamiento por encima de esa reserva. La aclaración de CR-011 sobre MONTHLY_DRAWDOWN_LOCK sigue válida («stop de mercado + slippage»), pero la cota es «stop + slippage real», no una cantidad fija. **Confirmado por el propietario** como riesgo residual aceptado y documentado, no como cota dura.
2. **Tipo de la pierna TP.** Para una posición long, la pierna limit superior es `LIMIT_MAKER` (o `TAKE_PROFIT_LIMIT`); el tipo `TAKE_PROFIT` de Binance dispara una orden a mercado. **Resuelto por el propietario:** `TAKE_PROFIT_LIMIT` para la pierna TP de una long; se fija en la implementación. (Nota: es una orden con disparo, por lo que, si el precio supera el nivel y revierte antes de llenar el límite, puede quedar sin ejecutar; es una consecuencia aceptada.)
3. **Contingencia STOP_LIMIT al 0.5%.** Si se usara, un hueco mayor a 0.5% por debajo del stop seguiría sin ejecutar la orden; ese caso lo cubre el cierre protector a mercado (DEC-008 Q25). Como el OCO con mercado está soportado, no se activa.

## Impacto
Bajo/arquitectónico: define el tipo de orden ya previsto en CR-002; no cambia límites de RISK_POLICY. Riesgo: sustituye el riesgo de no ejecución del stop-limit por riesgo de deslizamiento.

## Aprobación y aplicación
Aprobada por el propietario el 2026-11-19 ("Aprobado"; observaciones 1 y 2 confirmadas; "Aplica el CR-012, registra DEC-012, actualiza a contrato v1.2"). Aplicada en: `docs/decisions/DEC-012_tipo-orden-stop-oco.md` (nuevo); `requirements.md` (REQ-G-031); `data_flow.md` (colocación del stop); `test_plan.md` (TC-STOP-009..012); `api_contracts.md`, `architecture.md` (solo versión). Los cinco documentos pasan a v1.2.
