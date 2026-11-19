# CR-013 — Fuente de datos históricos, snapshot versionada y datos en vivo

**Fecha:** 2026-11-19
**Estado:** APROBADA por el propietario el 2026-11-19 (aceptó B.1–B.7) y APLICADA (contrato v1.3; DEC-013).
**Origen:** DEC-013 (decisiones del propietario, sesión 2026-11-19); resuelve CONF-006 (temporalidad 1d vs contrato) con la opción B. Cierra el vacío «fuente y calidad de datos históricos» detectado antes de FASE 2.

## A. Cambio propuesto (valores del propietario, DEC-013)
1. **Temporalidad: sin cambio** (D1 contexto, H4 señal, H1 entrada). CONF-006 queda RESUELTA.
2. **Snapshot de datos:** Binance REST `GET /api/v3/klines`, BTC/USDT, intervalos `1d`, `4h`, `1h`, desde 2017-08-17 hasta la fecha de snapshot; descarga única al iniciar FASE 2, guardada con timestamp de descarga; fija para el backtest piloto y el walk-forward; actualizar = nueva snapshot versionada. Paginación `limit=1000` con `startTime`.
3. **Formato y sellado:** Parquet por partición (`train_val`, `oos`, `lockbox`), cada una con su SHA-256, registrado en el preregistro junto con la tasa de trades observada. El LOCKBOX no se carga durante el desarrollo; solo en la evaluación final única.
4. **Huecos:** NaN sin interpolar; el backtest salta ese periodo; el conteo de huecos va en el preregistro.
5. **Modelo de ejecución del backtest (preregistrado):** stop tocado dentro de la vela → se llena al precio del stop con slippage 0.10% (REQ-G-P04); hueco (apertura < stop) → se llena a la apertura; mismo criterio para el TP.
6. **Datos en vivo:** WebSocket `kline_4h` (señal) y `kline_1d` (contexto); solo vela cerrada (flag `x`); al reconectar, verificación y resincronización por REST.
7. **Declaración de régimen** en el preregistro (2018 baja liquidez; 2020/2021 alta volatilidad; el walk-forward prioriza ventanas recientes).

## B. Correcciones y aclaraciones propuestas (NO decididas; el propietario debe confirmarlas o modificarlas)
1. **Particiones con tres intervalos.** «Un archivo por partición» deja abierto cómo se guardan 1d/4h/1h. Propuesta: cada archivo incluye una columna `interval`, y las fechas de corte de las particiones (50/20/15/15, cronológicas, DEC-005 P10) se fijan **una sola vez por fecha** y se aplican igual a los tres intervalos, para que ningún intervalo filtre información de otra partición. Las características de OOS pueden leer la cola de `train_val` (datos pasados, no es leakage); nunca al revés, ni nada de `lockbox` durante el desarrollo.
2. **Modelo de ejecución: tres huecos.**
   a) *Slippage en caso de hueco:* la decisión dice «a la apertura»; ¿se aplica además el 0.10%? Propuesta conservadora: sí, adverso.
   b) *Vela que toca stop y TP:* con barras OHLC no se sabe cuál fue primero. Propuesta: regla pesimista, se asume que se tocó primero el stop.
   c) *Modelo de entrada:* no está definido. Propuesta: señal sobre vela cerrada → entrada a la apertura de la vela siguiente (sin look-ahead), con comisión y slippage; la autorización humana se asume instantánea en el backtest y la tolerancia de 0.5% de P20 se aplica igual que en vivo.
   Estas reglas deben quedar en el preregistro de cada experimento y no pueden cambiarse tras ver resultados OOS.
3. **Respaldo REST.** `limit=2` solo detecta la última vela perdida; si la desconexión supera un intervalo (4h o 1d) faltarían más. Propuesta: al reconectar, consultar con `startTime` = `open_time` del último candle persistido + 1 y recuperar todos los candles cerrados faltantes antes de operar; hasta resincronizar, aplicar Fail-Closed (no se generan señales).
4. **Datos en vivo de 1h.** DEC-013 lista `kline_4h` y `kline_1d` pero REQ-G-002 asigna H1 a la evaluación de entrada. Propuesta: incluir `kline_1h` en vivo con las mismas reglas (solo cerrada, respaldo REST). Si el propietario no quiere H1 en vivo, hay que decir cómo se evalúa la entrada.
5. **«El walk-forward prioriza ventanas recientes».** Con el preregistro congelado (REQ-G-103, CR-011) no puede decidirse después de ver resultados qué ventanas pesan más. Propuesta: el criterio de aceptación sigue usando **todas** las ventanas WF; las ventanas recientes se reportan por separado (sin ponderar) salvo que el preregistro congele de antemano una ponderación por recencia. Además, la declaración de régimen debe ser verificable: mantener «régimen distinto» y retirar caracterizaciones no medidas (p. ej. «baja liquidez en 2018») salvo que se respalden con datos de la propia snapshot.
6. **Snapshot nueva y LOCKBOX consumido.** Al crear una snapshot posterior, el LOCKBOX ya evaluado deja de ser dato no visto. Propuesta: un LOCKBOX evaluado queda «consumido» y se registra; en la nueva snapshot ese periodo no puede volver a usarse como LOCKBOX, y solo los datos posteriores al final de la snapshot anterior pueden constituir un LOCKBOX nuevo. Un modelo evaluado en un LOCKBOX no puede reevaluarse en uno que lo contenga.
7. **Reproducibilidad del hash.** Reescribir un Parquet puede cambiar sus bytes aunque los datos sean iguales. Propuesta: los archivos son inmutables una vez hasheados y el preregistro registra la versión de la librería que los escribió.

## Documentos del contrato afectados (al aprobar)
- `requirements.md`: nuevo REQ-G-109 (snapshot y particiones de datos de investigación; Módulo 10) y nuevo REQ-G-097 (datos en vivo: velas cerradas, respaldo REST, Fail-Closed; Módulo 9); ampliación de REQ-G-103 (campos de preregistro: hash, huecos, modelo de ejecución, declaración de régimen).
- `data_flow.md`: Fase 1 (captura de datos en vivo y resincronización).
- `test_plan.md`: pruebas nuevas (hash/particiones; LOCKBOX no cargado; huecos NaN; modelo de ejecución; resincronización tras reconexión; vela en formación ignorada).
- `architecture.md`: componente responsable de la captura de datos (Market Intelligence / Trading Engine): solo si el propietario lo pide; no se añaden componentes.
- `implementation/conflict_register.md`: CONF-006 → RESUELTA (DEC-013).
- Versión: contrato v1.2 → v1.3.

## Impacto
- **Arquitectónico:** bajo. Concreta una fuente y una política de datos; no añade componentes ni cambia límites de RISK_POLICY.
- **Riesgo:** reduce el riesgo de leakage (particiones selladas) y de señales sobre datos incompletos (resincronización).
- **Costos de IA:** sin cambio respecto a DEC-009 (la IA sigue invocándose al cierre H4 con setup).

## Pendientes que NO cubre este CR (siguen PENDING de FASE 2)
Esquema del evento de señal de salida; nombres de motivos de `NO_SETUP`; reverificación del OCO contra el exchange; REQ-G-P08 (validación fiscal).

## Aprobación
Aprobada por el propietario el 2026-11-19 ("B.1–B.7: Acepto todas. Aplica el CR-013, registra DEC-013, actualiza a contrato v1.3, resuelve CONF-006"). Aplicada en: `docs/decisions/DEC-013_fuente-datos-historicos-snapshot.md`; `requirements.md` (nuevos REQ-G-097 y REQ-G-109; ampliación de REQ-G-103); `data_flow.md` (Fase 1); `test_plan.md` (TC-DATA-003..004, TC-ML-015..019); `conflict_register.md` (CONF-006 RESUELTA); `api_contracts.md`, `architecture.md` (solo versión). Los cinco documentos pasan a v1.3.
