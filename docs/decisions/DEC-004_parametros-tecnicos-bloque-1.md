# DEC-004 — Parámetros técnicos, bloque 1 (ejecución y Risk Manager)

**Fecha:** 2026-11-17
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Sesión de validación técnica en FASE 1 (respuestas del propietario Q1–Q6). Las opciones y recomendaciones se presentaron en la sesión; el propietario las aceptó.
**Alcance:** Resuelve P01–P06, P19 y P20 de `implementation/requirements.md`. NO constituye aprobación de G3 ni autoriza FASE 2.

---

## Decisiones

| Pregunta | Parámetro | Decisión |
|---|---|---|
| Q1 | P01 Fuente USDT/MXN | Par USDT/MXN de Binance en tiempo real para el sizing. La fuente para fines fiscales (p. ej. FIX de Banxico) queda diferida a la validación con contador (P08). |
| Q2 | P02 Antigüedad máxima del tipo de cambio | 5 minutos. Si se excede: Fail-Closed (INV-012). |
| Q3 | P03 Comisión efectiva | Leer la comisión real de la cuenta por API; usar el mayor entre ese valor y 0.10% por lado. |
| Q3 | P04 Reserva de slippage | 0.10%. Revisable con fills reales en FASE 2. |
| Q4 | P05 stepSize / minQty / minNotional | Lectura dinámica del endpoint de información del exchange al arrancar, con refresco diario. Orden que incumpla filtros: rechazada antes de enviarse. |
| Q5 | P06 Aprobación humana | Bot de Telegram con botones Aprobar/Rechazar. Solo el usuario del propietario; aprobación con vencimiento (`valid_until_utc`); nunca ejecuta por mensaje ambiguo. |
| Q6 | P19 Reconciliación con Binance | Al arrancar y antes/después de cada ciclo de decisión; además cada 5 min mientras haya posición abierta. |
| Q6 | P20 Tolerancia de desviación de precio | 0.5% entre precio analizado y precio de ejecución; si se excede, la orden se rechaza. |

## Notas

- Los valores reales de comisión y filtros de Binance se obtienen en tiempo de ejecución; esta decisión fija el mecanismo y el piso conservador, no un valor copiado de la documentación.
- Los valores asociados 0.10% (slippage) y 0.5% (tolerancia) fueron propuestos por el asistente y aceptados por el propietario junto con la opción elegida.
- No resuelve: P07, P08, P10–P18, P21–P25 (bloques posteriores o diferidos).
