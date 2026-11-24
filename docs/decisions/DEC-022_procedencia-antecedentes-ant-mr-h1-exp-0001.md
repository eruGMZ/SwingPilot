# DEC-022 — Registro de la procedencia documental de ANT-MR-H1 y EXP-0001

**Fecha:** 2026-11-24
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-24: acepta el commit `824fae8` como implementación funcional congelada de CR-020 y autoriza expresamente el registro de la procedencia real de los antecedentes ANT-MR-H1 y EXP-0001, y solo de ellos.
**Referencias:** DEC-021 (aprobación de CR-020; conteo histórico conservador inicial = 8); `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` §C.3.1 y §D; resolución D1 (`harness/verification/IMPL-3_EXP-0001_procedencia.md` §6); CONF-009.
**Alcance:** autoriza exactamente los dos registros `ANTECEDENT_PROVENANCE` de abajo en `research/experiments/registry.jsonl`, mediante la API de registro de procedencia. No cambia los estados originales de los antecedentes, no crea experimentos nativos, no congela preregistros ni autoriza evaluaciones, backtests, particiones ni SNAP-0001.

## Decisión

| Antecedente | Estado original (inmutable) | Estado documental | Ejecución | Configuraciones | Clase de evidencia |
|---|---|---|---|---|---|
| ANT-MR-H1 (Mean Reversion H1, Fase 0 de `trading-bot`) | REJECTED | DOCUMENTED | DOCUMENTED_EXECUTED | A, B, E1, E2 | DOCUMENTED_EVALUATED (evaluación documentada sobre Train; resultados originales no recuperados) |
| EXP-0001 (Trend Following H4) | PENDING_DOCUMENTATION | DOCUMENTED | UNKNOWN | A, B, C, D | CONSERVATIVE_BOUND (cota conservadora; **no** son ejecuciones verificadas) |

**Evidencia documental** (repositorio `trading-bot`, solo lectura):
- ANT-MR-H1: `trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md` (4 configuraciones A, B, E1, E2 evaluadas sobre Train; dictamen RECHAZADO) y `trading-bot@25f0e3f:backtest/REPORTE_FASE0.md` (informe de Fase 0).
- EXP-0001: `trading-bot@21c5f25:backtest/experiments/EXP-0001/preregistration.md` (preregistro v4 congelado, D-024; configuraciones A–D, §6) y `trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md` (A–D preregistradas, «aún sin ejecutar» en el último registro versionado).

**Autorización** (líneas exactas; CR-020 §C.3.1, R4):

AUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=4 COTA=0
AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4

## Efectos

- Conteo histórico resultante: H_doc = 4, H_bound = 4, E = 0, G = 8. Las 4 de EXP-0001 son una cota, no ejecuciones verificadas; su ejecución y sus resultados siguen desconocidos (D1).
- El rechazo de Mean Reversion H1 se conserva sin afirmar que se hayan recuperado sus resultados originales (el CSV previo de Fase 0 no se conservó).
- Una reducción posterior de cualquiera de estas cotas exige evidencia documental y una nueva decisión del propietario, y solo se aplica a preregistros futuros (DEC-021).
- CONF-009 y CONF-010 siguen OPEN hasta que se acepte la verificación independiente. FEAT-017 sigue IN_PROGRESS.
- Siguen vigentes las restricciones de DEC-017 y DEC-018. El commit y el push requieren la indicación del propietario.
