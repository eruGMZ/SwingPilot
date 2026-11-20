# IMPL-3 — QA independiente, ronda 2 (última) — FEAT-015, FEAT-016, FEAT-017 infraestructura, FEAT-019 infraestructura

**Fecha:** 2026-11-20
**Revisor:** QA Agent independiente nuevo: sub-agente de solo lectura, sin red, sin API de Anthropic de SwingPilot (~149K tokens del sub-agente; $0 del presupuesto de IA de IMPL-3). Ejecutado como uid 1000 (no root).
**Reproducciones:** `/tmp/claude-1000/qa-impl3-r2/` (temporales, fuera del repositorio).
**Ronda anterior:** `harness/verification/IMPL-3_QA_ronda1.md` (hallazgos y correcciones).
**Estado:** hallazgos nuevos ABIERTOS. No se corrigen sin autorización: la autorización del propietario cubría QA3-01..19.

pytest (QA): `.venv/bin/pytest -q -p no:cacheprovider tests` → 390 passed, 5 skipped.

## Verificación de la ronda 1

| ID | Veredicto | Nota |
|---|---|---|
| QA3-01 | CERRADO | Reintento con espera exponencial reproducido; sin deadlock (orden de locks feed → store); la generación solo cambia al desconectar. |
| QA3-02 | CERRADO | Descarga truncada abortada; rejilla hasta `range_end`; inicio de cotización declarado. |
| QA3-03 | CERRADO | Antecedentes restringidos y no elegibles. |
| QA3-04 | CERRADO | Con observación QA3R2-04. |
| QA3-05 | CERRADO para NaN/inf | La misma clase de fallo persiste con equity ≤ 0 (QA3R2-01). |
| QA3-06 | CERRADO | Sellado 0o000 verificado, consumo persistido, `_read` restaura el modo en `finally`. |
| QA3-07 | **PARCIAL** | DSR interno (fórmula verificada) y conteo OOS contrastado; equity y retornos no se cruzan con `oos_net_r` (QA3R2-01). |
| QA3-08 | CERRADO | |
| QA3-09, 10, 11, 12 | CERRADOS | 0 diferencias en 700 longitudes de corte; identidad del neto verificada en 370 trades; `iloc[:i+1]` sin coste O(n²) práctico (80k filas en 0,56 s). |
| QA3-13, 14, 16, 17, 18, 19 | CERRADOS | Con observación QA3R2-07 sobre QA3-13. |
| QA3-15 | **PARCIAL** | Un fallo entre el renombrado del directorio y la escritura del manifiesto deja un directorio sin manifiesto que bloquea el reintento (QA3R2-02). |

## Hallazgos nuevos

Ninguno BLOQUEANTE ni MAYOR.

| ID | Sev. | Archivo | Hallazgo | Evidencia | Corrección necesaria |
|---|---|---|---|---|---|
| QA3R2-01 | MENOR | `research/acceptance.py` | `max_drawdown` no valida el dominio: equity a cero da NaN, equity negativa da −0, y una equity de 1 punto con 40 trades da `ELIGIBLE_FOR_HUMAN_REVIEW` sin motivos. Equity y retornos son independientes de `oos_net_r`. `n_resamples=0` y enteros enormes fallan con excepción en vez de INCONCLUSIVE. | Reproducido | Exigir equity > 0 y `len(equity) == len(oos_net_r)+1`; derivar o contrastar equity y retornos con `oos_net_r`; validar `n_resamples ≥ 1`; prueba con equity ≤ 0. |
| QA3R2-02 | MENOR | `research/snapshot.py` | Si el fallo ocurre tras renombrar el directorio y antes del manifiesto, queda un directorio huérfano que bloquea el reintento. | Reproducido | Escribir el manifiesto antes del renombrado final, o limpiar ante fallo del manifiesto. |
| QA3R2-03 | MENOR | `research/partitions.py` | Carrera (TOCTOU) entre la comprobación de consumo y su registro: dos cargadores concurrentes leen el LOCKBOX y registran 2 consumos. Una lectura fallida consume la partición, de forma conservadora pero sin documentar. | Reproducido con barrier | Comprobación y registro atómicos (`flock` sobre el registro); documentar el consumo ante fallo de lectura. |
| QA3R2-04 | OBS | `research/experiments.py` | La cita en la decisión se comprueba por subcadena: «oos» aparece en «choose». `create()` no valida el formato del id. | Reproducido | Línea estructurada (`AUTORIZA: <exp> <partición> <snapshot>`) con regex; validar `EXP-NNNN`. |
| QA3R2-05 | OBS | `market_data/stream.py` | El reintento de resync solo se evalúa al llegar un mensaje; con una conexión silenciosa no hay reintento. Impacto bajo: Binance emite kline cada ~1–2 s. | Reproducido | Evaluar también con timeout de lectura. |
| QA3R2-06 | OBS | `research/backtest.py` | `ExecutionModel` acepta comisión o slippage NaN. El evaluador lo convertiría en INCONCLUSIVE. | Por lectura | Validar finitos. |
| QA3R2-07 | OBS | `research/preregistration.py` | `oos_seen` se deriva del registro de accesos que pasa quien llama, no del registro de experimentos. | Por lectura | Derivarlo de `registry.consumed_partitions()`. |
| QA3R2-08 | OBS | `research/snapshot.py`, `cli.py` | Bajo root o sin permisos POSIX, el sellado 0o000 no aplica y no se detecta. Un SIGKILL dentro de `_read` deja 0o400. `verify-snapshot --id` no valida el id. | Por lectura | Documentar; comprobar con `os.access` y avisar; validar el id en la CLI. |

## Veredicto por FEAT

| FEAT | Veredicto QA ronda 2 |
|---|---|
| FEAT-015 | CONFORME CON OBSERVACIONES (QA3R2-02, QA3R2-03) |
| FEAT-016 | CONFORME CON OBSERVACIONES (QA3R2-05) |
| FEAT-017 (infraestructura) | CONFORME CON OBSERVACIONES; el QA recomienda corregir QA3R2-01 antes de usar el evaluador en una evaluación real |
| FEAT-019 (infraestructura) | CONFORME |

Las rondas de QA permitidas están agotadas (2 de 2). Cualquier corrección posterior requiere la indicación del propietario y su forma de verificación.
