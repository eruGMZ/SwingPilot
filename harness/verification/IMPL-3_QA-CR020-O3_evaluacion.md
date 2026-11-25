# IMPL-3 — Evaluación y disposición de QA-CR020-O3 (FEAT-017; CR-020)

**Fecha:** 2026-11-24
**Origen:** observación QA-CR020-O3 (OBS, evidencia insuficiente o por construcción) de `harness/verification/IMPL-3_CR-020_QA_independiente.md` §3 (informe y sondas conservados sin cambios).
**Base evaluada:** `c70f593` (`develop`). Evaluación de solo lectura por el Orquestador de Desarrollo; no aprueba su propio trabajo. Sin cambios en código funcional, pruebas, contrato v1.10, registro real, estados de FEAT ni de conflictos, gates. Sub-agentes: 0.
**Estado:** QA-CR020-O3 **ACEPTADO por el propietario** (cuatro disposiciones); **pendiente de reverificación independiente**.

## 1. Evaluación por componente

| # | Componente | Obligación vinculante | Comportamiento y evidencia | Clasificación |
|---|---|---|---|---|
| 1 | TC-ML-020: exclusión de escenarios de costes «solo por construcción» | REQ-G-P17 y TC-ML-020 (corrida idéntica o escenario puro de costes no suma; el escenario usado para seleccionar es una configuración propia); CR-020 §B.1, §C.1 | La corrida idéntica la impone el mecanismo (unidad = par; las copias de CR-021 no suman). El escenario puro de costes queda fuera solo porque quien llama no lo registra. Lo que decide la selección queda cubierto: la regla elige solo entre configuraciones planificadas (cuentan por `N_pre`); una configuración evaluada no planificada o una selección distinta de la regla da INCONCLUSIVE (`UNPLANNED_CONFIGURATION`, `SELECTION_RULE_VIOLATION`). Resto no detectable: influencia sobre una decisión tomada fuera del registro | Riesgo residual aceptable (dentro de la limitación aceptada «decisiones fuera del registro no detectables», `IMPL-3_CR-020_implementacion.md` §7) |
| 2 | A2: evidencia previa a la corrección no reproducible | AGENTS.md (evidencia verificable y reproducible; no inventar); obligación del propietario de regresiones que fallen con el código anterior (progress.md) | `d372e28` no tiene cargador con puerta ni `trials.py`; `824fae8` ya contiene A2. El estado «mecanismo de CR-020 sin A2» nunca se confirmó en un commit, por lo que «7 failed, 5 passed» no puede reejecutarse. Sí es reproducible el estado posterior (7 pruebas A2 pasan) y la cobertura posterior frente a bases confirmadas (QA-CR020-01 frente a `e645a27`; matriz P1 de CR-021 frente a `f48114c`) | Limitación permanente de evidencia; no es incumplimiento contractual |
| 3 | P10: reducción de procedencia aceptada con la misma lista de evidencia | REQ-G-P17 (cotas solo se reducen con evidencia documental y aprobación del propietario, solo prospectivo); CR-020 §C.3.1; TC-ML-021 | Se impone la sintaxis: línea `AUTORIZA: PROCEDENCIA` exacta con conteos coincidentes, `supersedes` coherente, ninguna configuración desaparece, `evidence` no vacía y bien formada, sin decisión se rechaza. No se impone la sustancia: que la evidencia citada respalde `DOCUMENTED_NOT_EVALUATED`, que exista el commit citado ni que difiera de la anterior; el contrato no lo exige | Riesgo residual aceptable (la autorización del propietario es el control sustantivo) |
| 4 | P11: espacio final o CRLF en la línea de autorización | CR-020 §C.3.1 («mismos criterios que QA3R2-04»; `fullmatch` campo por campo); TC-ML-021; criterio aprobado de QA3R2-04 («`fullmatch` tras quitar el espacio final», `rstrip`) | CRLF/CR y espacios o tabuladores finales se normalizan (criterio aprobado); ningún campo se altera (prefijo, mayúsculas, signo, ceros, no ASCII y tokens de más se rechazan: 13 casos). Ninguna prueba fija el comportamiento para `PROCEDENCIA`; las líneas reales de DEC-022 no tienen espacio final ni CR | Criterio aprobado con borde sin fijar por prueba |

## 2. Evidencia ejecutada (solo existente, registros temporales sintéticos)

- `.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_trials_accounting.py -k "tc_ml_020 or tc_ml_021"` → 26 passed.
- `.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_snapshot.py -k "a2"` → 7 passed.
- `.venv/bin/python -I -B harness/verification/IMPL-3_CR-020_QA_sondas.py <directorio temporal>`: el artefacto no permite seleccionar sondas y ejecutó P1–P11; solo se usaron P10 (reducción aceptada con la misma evidencia; G = 7) y P11 (espacio final y CRLF aceptados). Árbol limpio tras la ejecución.
- Historial de Git: `d372e28` (cargador con puerta 0, `trials.py` no); `824fae8` (cargador con puerta 1, `_load_train_val_for_inspection` presente, `trials.py` sí).
- Lectura de código y de la documentación de Python, **no ejecutada**: `str.rstrip()` elimina todo espacio Unicode y `str.splitlines()` reconoce también `\x0b`, `\x0c`, `\x1c`–`\x1e`, `\x85`, `\u2028` y `\u2029` como separadores.

## 3. Aceptación del propietario (2026-11-24)

1. **TC-ML-020:** acepta la limitación residual. **Condición:** verificar la contabilidad correcta de los escenarios de costes antes de habilitar el pipeline de evaluación de investigación.
2. **A2:** acepta la limitación histórica permanente de evidencia. No se reconstruye el estado previo a la corrección ni se presenta evidencia posterior como evidencia original.
3. **P10:** acepta la imposición sintáctica y la responsabilidad del propietario sobre la justificación documental sustantiva. Toda reducción futura exige evidencia que respalde realmente `DOCUMENTED_NOT_EVALUATED`. **No se autoriza ninguna reducción del registro real.**
4. **P11:** acepta el criterio aprobado de normalización de espacio final y fin de línea. El comportamiento con espacios y separadores Unicode **sigue sin verificarse y no se certifica**.

No se autorizan cambios funcionales, de pruebas ni contractuales. **QA-CR020-O3: ACEPTADO por el propietario; pendiente de reverificación independiente.**

## 4. Limitaciones residuales

- Escenarios de costes: sin mecanismo que distinga un escenario puro de uno que influyó en una decisión no registrada; la verificación previa a habilitar el pipeline es una obligación abierta.
- A2: la discriminación previa a la corrección es irrecuperable.
- P10: el validador no comprueba que la evidencia respalde la reducción.
- P11: comportamiento con espacios y separadores Unicode no verificado; ninguna prueba fija el criterio para `PROCEDENCIA`.

## 5. Obligación de reverificación independiente (QA-CR020-O3)

Comprobar que el registro de la disposición es fiel a esta evaluación y a la evidencia citada; que ningún documento presenta evidencia posterior como original (A2); que el registro real no tiene reducciones; que la condición de TC-ML-020 consta como obligación abierta antes de habilitar el pipeline; y que el comportamiento Unicode no se presenta como certificado.
