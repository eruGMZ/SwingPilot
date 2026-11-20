# IMPL-3 — Procedencia de EXP-0001 y de Mean Reversion H1, e integridad de las particiones

**Fecha:** 2026-11-20
**Autor:** Orquestador de Desarrollo
**Origen:** DEC-018 decisión 4; instrucción del propietario del 2026-11-20 («buscar la documentación y evidencia original… No reconstruir resultados como si fueran evidencia histórica»).
**Estado:** INFORME. No modifica DEC-018, no preregistra el piloto y no crea SNAP-0001.

---

## 1. Dónde se buscó

| Lugar | Resultado |
|---|---|
| Repositorio SwingPilot: árbol actual, todas las ramas, reflog, stash y objetos inalcanzables | Sin documentación de EXP-0001. Las únicas menciones son las de DEC-017/DEC-018 y del trabajo de IMPL-3. «Mean Reversion» solo aparece como familia de investigación en los documentos de política. |
| Memoria del asistente | Sin menciones. |
| Disco del propietario bajo `/home/erick` (nombres de archivo) | Sin archivos con EXP-0001, Mean Reversion o Trend Following en el nombre fuera de SwingPilot. |
| **Proyecto hermano `/home/erick/Documentos/Projects/trading-bot` (historia de git)** | **Encontrada la documentación original** (§2). El directorio `backtest/` ya no está en disco ni versionado (commit `3efea65`, «chore: stop tracking backtest directory», 2026-11-09), pero su contenido sigue en la historia. |

**Método:** solo lectura con `git show` y `git log` sobre la historia de `trading-bot`. No se hizo checkout, no se modificó nada y **no se abrió ningún CSV de precios**. Ese proyecto protegía sus datos con controles que impedían a los agentes leerlos, incluido el historial de git. Solo se leyeron documentos, manifiestos y metadatos.

## 2. Evidencia original encontrada

Repositorio `trading-bot`, rama `master`. Última versión del directorio `backtest/` en el commit **`21c5f25`** (2026-11-09; árbol `backtest` `78a2973`, idéntico en `ab26e2a` y `e8858a3`).

| Elemento | Ruta en `21c5f25` | Contenido verificado |
|---|---|---|
| Registro de experimentos | `backtest/docs/REGISTRO_EXPERIMENTOS.md` | FASE-0 (H-000, Mean Reversion H1): 4 configuraciones (A, B, E1, E2) en Train, **RECHAZADO**. EXP-0001 (H-001, Trend Following H4): 4 configuraciones (A primaria, B, C, D) **preregistradas**; «Train (pendiente)»; «PREREGISTRO CONGELADO — Train autorizado (D-024)». LOCKBOX_OOS_001 **no consumido**. |
| Preregistro EXP-0001 | `backtest/experiments/EXP-0001/preregistration.md` | v4, **CONGELADO** por decisión humana D-024 (2026-11-09). |
| Auditorías del preregistro | `audit_preregistration_v3.md`, `audit_preregistration_DH3.md`, `audit_preregistration_final.md` | Presentes. |
| Verificaciones | `verificacion_comisiones_D-H1.md`, `verificacion_capital_D-H2.md` | Presentes (D-021, D-022). |
| Motor del experimento | `engine/*.py`, `run_exp0001.py`, `tests/*.py`, `MANIFEST_ENGINE.json` (SHA-256 por archivo) | Presentes (commit `dbfb388`, «Motor de backtest EXP-0001 implementado (pre-Train)»). |
| Datos | `research/data/MANIFEST.json` | Dataset derivado `btcusdt_h1_research_v1.csv`, SHA-256 `6b4b4200…46639c1c`, 22 128 velas H1, 2023-05-01 → 2025-11-07T23:00Z, sin velas del lockbox. |
| Fase 0 (Mean Reversion H1) | `backtest/REPORTE_FASE0.md` (commit `25f0e3f`) | Las 4 configuraciones con expectancy neta negativa y PF < 1.0 en Train. Dictamen humano 2026-11-08: no avanzar; **OOS no ejecutado**. |
| Política de datos y lockbox | `backtest/docs/POLITICA_DATOS_OOS.md`, `EVIDENCIA_AISLAMIENTO_LOCKBOX.md`, `REGISTRO_DECISIONES.md` | LOCKBOX_OOS_001 = `2025-11-08T20:00Z ≤ open_time < 2026-11-01T00:00Z`. D-009: «**no se certifica como plenamente ciego**; se conserva como evaluación histórica restringida». |

### Parámetros de EXP-0001 según el preregistro congelado (v4)

- H4 agregada desde H1 (vela H4 válida solo con sus 4 H1). Calentamiento de 200 velas H4.
- Entrada long: `close > EMA200` (H4) y `ADX14 > umbral` (H4); entrada a la apertura de la vela siguiente.
- Salida: **solo** trailing stop ATR (`stop = max(stop_vigente, close − ATR_mult × ATR14)`); sin salida por reversión de señal.
- Configuraciones: **A** ADX 25 / 2.0×ATR14 (primaria); **B** ADX 20 / 2.0×; **C** ADX 25 / 1.5×; **D** ADX 25 / 3.0×.
- Train: `open_time < 2025-11-08T00:00Z`; efectivo ≈ 2023-06-03 → 2025-11-07 (~29 meses).
- Comisión 0.10% por lado (D-021); capital simulado 150.00 USDT (D-022); IC bootstrap obligatorio (D-023).
- Walk-Forward propio: 4 ventanas IS 18 m / OOS 3 m. **Es distinto del de SwingPilot** (24/2/6, DEC-011).

## 3. Lo que NO puede recuperarse

| Dato | Situación |
|---|---|
| **Resultados de Train de EXP-0001** | **No existen en ninguna rama ni commit.** El último registro (`acaa868`, 2026-11-09) sigue diciendo «preregistradas (aún sin ejecutar)». Si el backtest se ejecutó después de dejar de versionar `backtest/` (`3efea65`), sus salidas estaban solo en disco y ese directorio ya no existe. **No se puede saber si EXP-0001 llegó a ejecutarse ni con qué resultado.** |
| CSV previo de Fase 0 (SHA-256 `4c7417d3…`) | «No conservado» según el propio proyecto (INC-001); solo queda su hash. |
| Estado actual de LOCKBOX_OOS_001 | En git consta «no consumido» a 2026-11-09. Lo ocurrido después en disco no es verificable. |
| Archivos de datos originales | Siguen en la historia de git de `trading-bot`, pero no se abrieron (§1) y **no deben usarse** como sustituto de la snapshot de SwingPilot (REQ-G-109). |

**No se reconstruyó ningún resultado.** EXP-0001 queda registrado como experimento con preregistro congelado y **resultado desconocido**, no como «no ejecutado» ni como «rechazado».

## 4. Integridad de las particiones de SwingPilot

Cortes que produciría SNAP-0001 (50/20/15/15 por fecha desde 2017-08-17), calculados solo con aritmética de fechas, **sin crear la snapshot**:

| Si la snapshot termina | Train | Validation | OOS | LOCKBOX |
|---|---|---|---|---|
| 2026-11-19 | 2017-08-17 → 2022-04-03 | 2022-04-04 → 2024-02-08 | 2024-02-09 → 2025-06-29 | 2025-06-30 → 2026-11-19 |
| 2026-12-30 | → 2022-04-23 | → 2024-03-08 | → 2025-08-03 | 2025-08-04 → 2026-12-30 |

Datos ya usados en decisiones de investigación de `trading-bot` sobre BTC/USDT:
- **Fase 0 (Mean Reversion H1):** Train procesado hasta 2025-11-08T19:00Z (primera ejecución) y 2023-10-31 → 2025-10-31 (reejecución).
- **EXP-0001 (Trend Following H4):** el preregistro se diseñó y congeló sobre el segmento 2023-05-01 → 2025-11-07, y Fase 0 ya había procesado ese mismo periodo. Si EXP-0001 se ejecutó, ese periodo es su Train (desconocido, §3).
- **LOCKBOX_OOS_001:** 2025-11-08T20:00Z → 2026-10-31, declarado «no plenamente ciego» (D-009 de `trading-bot`).

**Solapamiento con SNAP-0001 (fin 2026-11-19):**
- La **OOS completa** de SwingPilot (2024-02 → 2025-06) está dentro de datos ya usados por Fase 0 y por EXP-0001.
- El **LOCKBOX** de SwingPilot (2025-06-30 → 2026-11-19) contiene ~4 meses ya usados (2025-06-30 → 2025-11-08) y, después, el periodo del LOCKBOX_OOS_001 de `trading-bot`, que no es plenamente ciego.
- Para **Trend Following H4** y **Mean Reversion H1**, las particiones OOS y LOCKBOX de SNAP-0001 **no estarían limpias** con el corte 50/20/15/15 estándar. El preregistro debe declararlo (REQ-G-101, REQ-G-102), y probablemente exige una decisión del propietario sobre los cortes o sobre el uso de OOS/LOCKBOX para estas familias.

## 5. Efectos y opciones (para el propietario; nada se aplica)

1. **Registro de experimentos de SwingPilot.** Actualizar EXP-0001 de `PENDING_DOCUMENTATION` a un estado que diga «preregistro v4 congelado (trading-bot D-024); resultado desconocido», con la ruta de la evidencia (`trading-bot@21c5f25`). Contar además **5 configuraciones** de EXP-0001 y Fase 0 donde el registro ahora cuenta 2 experimentos. El presupuesto de pruebas de `trading-bot` contaba por configuración (D-016): 4 de Fase 0 + 4 de EXP-0001 = 8. Hace falta decidir si `trials_count` (REQ-G-P17) cuenta experimentos o configuraciones. El registro es append-only: la actualización sería un registro nuevo, no una edición.
2. **Cortes de SNAP-0001.** Opciones:
   - (a) mantener 50/20/15/15 y declarar que OOS y LOCKBOX no son limpios para TF H4 y MR H1;
   - (b) excluir esas familias de la evaluación confirmatoria en esta snapshot;
   - (c) usar como LOCKBOX solo datos posteriores a 2026-11-01 (fin del LOCKBOX_OOS_001), lo que exige histórico nuevo (validación prospectiva);
   - (d) otra regla que decida el propietario.

   Cambiar los cortes de DEC-005 P10 requiere una CR.
3. **Relación con el preregistro de `trading-bot`.** El piloto de SwingPilot no es EXP-0001: el contrato impone otro Walk-Forward (24/2/6), otro capital y otra partición. Reutilizar EXP-0001 como «antecedente» no significa heredar su preregistro.

Hasta la decisión del propietario: el piloto no se preregistra (DEC-018) y SNAP-0001 no se crea.
