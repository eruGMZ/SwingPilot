# CR-002 — Stop-loss colocado en Binance (protección ante caída del sistema)

**Fecha:** 2026-11-17
**Estado:** APROBADA por el propietario el 2026-11-17 ("APRUEBO CR-002") y aplicada.
**Origen:** DEC-006 §Q17; REQ-5021 (las acciones de protección permanecen disponibles); REQ-5011 (toda operación con mecanismo de salida definido).

## Problema

En el contrato actual el stop-loss vive solo en el software: `implementation/data_flow.md` (monitoreo de posición, ~líneas 162–167) compara precio actual contra stop-loss y, al alcanzarlo, emite `ORDER_SUBMITTED (SELL)`. Si SwingPilot se cae con una posición abierta, nadie vigila el stop y la posición queda sin protección.

## Cambio propuesto

1. Al confirmarse la ejecución de una compra, colocar de inmediato una orden de stop-loss en Binance (stop-limit u OCO, a definir en implementación) con el precio de stop autorizado.
2. El monitoreo en software se mantiene como segunda capa y para reconciliación.
3. Modificaciones del stop (solo para reducir riesgo, REQ-G existente: `P_stop_nuevo >= P_stop_inicial`) se reflejan cancelando y reemplazando la orden en Binance.
4. Si la orden de stop no puede colocarse en Binance tras la compra: estado de alerta, aviso por Telegram y cierre de la posición o intervención del propietario (Fail-Closed; detalle a definir en implementación).
5. La reconciliación (P19, P26) verifica que toda posición abierta tenga su stop activo en Binance.

## Documentos del contrato afectados

- `implementation/data_flow.md` — flujo de ejecución y monitoreo de posición.
- `implementation/api_contracts.md` — orden de stop en la integración con Binance; eventos de colocación/cancelación.
- `implementation/requirements.md` — requisito nuevo o ampliación de los requisitos de stop-loss.
- `implementation/test_plan.md` — pruebas: stop presente tras cada compra; caída simulada con posición abierta; fallo al colocar stop.

## Impacto

- **Arquitectónico:** bajo; añade una orden y un evento al flujo de ejecución existente.
- **Riesgo:** reduce el riesgo de pérdida no controlada ante caídas.
- **Pendiente técnico:** tipo de orden (stop-limit vs OCO) y manejo de huecos de precio con stop-limit; se definen en FASE 2 con datos reales de Binance.

## Aprobación

Aprobada el 2026-11-17 con la frase "APRUEBO CR-002". Aplicada en: `requirements.md` (REQ-G-031), `data_flow.md` (§2 ciclo de vida de posición), `api_contracts.md` (eventos STOP_ORDER_PLACED / STOP_ORDER_REPLACED / STOP_ORDER_FAILED), `test_plan.md` (TC-STOP-001..006).
