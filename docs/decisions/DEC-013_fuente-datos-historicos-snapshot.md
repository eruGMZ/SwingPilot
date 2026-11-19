# DEC-013 — Fuente de datos históricos, snapshot y datos en vivo (resuelve CONF-006)

**Fecha:** 2026-11-19
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensajes del propietario en la sesión del 2026-11-19: propuesta de fuente de datos (klines 1d) y respuesta posterior eligiendo la opción B («Se mantiene H4 como señal. El 1d es solo contexto»), aceptando los 4 vacíos señalados y fijando la snapshot corregida. Ver `harness/change_requests/CR-013_fuente-datos-historicos.md`.
**Alcance:** Registra las decisiones del propietario. Se aplican al contrato mediante CR-013 (contrato v1.3, cuando se apruebe). Resuelve CONF-006. NO autoriza FASE 2.

---

## Decisiones

| Tema | Decisión |
|---|---|
| Temporalidad (CONF-006) | **Opción B.** Se mantiene el contrato: D1 = contexto, H4 = estructura y señal, H1 = evaluación de entrada (REQ-G-001/002). La propuesta inicial de usar solo 1d fue un error por no haber revisado REQ-G-001/002 y se retira. |
| Fuente | Binance REST API, `GET /api/v3/klines`, BTC/USDT. |
| Intervalos | `1d`, `4h`, `1h`, los tres en la misma snapshot. |
| Rango | Desde 2017-08-17 (primer dato de BTC/USDT en Binance) hasta la fecha de snapshot. |
| Snapshot | Se descarga una vez al iniciar FASE 2 y se guarda localmente con timestamp de descarga. El backtest piloto y el walk-forward usan esa snapshot fija; no se re-descarga. Actualizar = nueva snapshot versionada. |
| Formato y particiones | Parquet, un archivo por partición (`train_val.parquet`, `oos.parquet`, `lockbox.parquet`), cada uno con su propio SHA-256, registrado en el preregistro junto con la tasa de trades observada. |
| LOCKBOX | No se carga durante el desarrollo; solo en la evaluación final única. |
| Huecos | Vela faltante = NaN, sin interpolar; el backtest salta ese periodo; el conteo de huecos se registra en el preregistro. |
| Paginación | `limit=1000`, iterando con `startTime`. |
| Modelo de ejecución del backtest | Se preregistra: si el stop se toca dentro de la vela, se llena al precio del stop con slippage de 0.10% (REQ-G-P04); si hay hueco (apertura por debajo del stop), se llena a la apertura. Mismo criterio para el take-profit. Precisiones aceptadas en las aclaraciones 2. |
| Datos en vivo | WebSocket `kline_4h` (señal), `kline_1d` (contexto) y `kline_1h` (evaluación de entrada, aclaración 4). Solo vela cerrada (flag `x`). |
| Respaldo REST | Al reconectar, el bot consulta klines por REST para verificar si se perdió una vela cerrada; si el timestamp del último candle en memoria no coincide, se resincroniza (con `startTime`, aclaración 3). |
| Declaración de régimen | Texto original del propietario: periodos de baja liquidez (2018) y alta volatilidad (2020, 2021) no representativos, y walk-forward que prioriza ventanas recientes. **Reformulado por la aclaración 5 (aceptada):** «régimen distinto» y criterio con todas las ventanas, recientes reportadas por separado. |
| Cálculo de histórico mínimo | Ver CR-011/DEC-011: con ~111 meses de histórico alcanza para 2 ventanas WF + OOS + LOCKBOX hasta una tasa de ~1.8 trades/mes (cuello de botella: ≥30 trades en OOS y en LOCKBOX, 15% cada uno). |

## Aclaraciones resueltas (el propietario aceptó B.1–B.7 de CR-013, 2026-11-19)
1. **Particiones con tres intervalos:** columna `interval` en cada archivo; fechas de corte únicas por fecha, iguales para los tres intervalos; las características de OOS pueden leer la cola de `train_val`, nunca `lockbox`.
2. **Modelo de ejecución:** slippage adverso de 0.10% también en el caso de hueco; si una vela toca stop y TP se asume el stop primero; entrada a la apertura de la vela siguiente a la señal (sin look-ahead), con comisión y slippage; autorización humana instantánea en el backtest; tolerancia de 0.5% (P20) igual que en vivo.
3. **Respaldo REST:** con `startTime` = último `open_time` persistido + 1, recuperando todas las velas cerradas faltantes; Fail-Closed hasta resincronizar.
4. **Datos en vivo:** se añade `kline_1h` (evaluación de entrada, REQ-G-002) con las mismas reglas.
5. **Walk-forward y recencia:** el criterio de aceptación usa todas las ventanas; las recientes se reportan por separado, salvo ponderación congelada de antemano en el preregistro. La declaración de régimen se limita a «régimen distinto» (sin caracterizaciones no medidas, p. ej. «baja liquidez en 2018»), salvo respaldo en datos de la snapshot.
6. **LOCKBOX consumido:** queda registrado como consumido; en una snapshot nueva no se reutiliza como LOCKBOX; solo datos posteriores al final de la snapshot anterior pueden formar uno nuevo.
7. **Hash:** archivos inmutables una vez hasheados; se registra la versión de la librería que los escribió.
