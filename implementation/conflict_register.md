# conflict_register.md — Registro de Conflictos

> **ESTADO:** PENDIENTE — Documento a poblar en FASE 1.
>
> Este registro se actualiza durante la extracción y el merge en FASE 1.

## Formato de entrada

```
### CONF-NNN

- **Fecha de detección:** YYYY-MM-DD
- **Documentos en conflicto:** [doc1] vs [doc2]
- **Sección doc1:** ...
- **Sección doc2:** ...
- **Naturaleza del conflicto:** descripción del conflicto
- **Severidad:** CRITICAL | HIGH | MEDIUM | LOW
- **Estado:** OPEN | ESCALATED | RESOLVED
- **Resolución:** (si RESOLVED) descripción de la resolución y autoridad que la aprobó
```

---

## Conflictos registrados en FASE 1

---

### CONF-001

- **Fecha de detección:** 2026-11-13
- **Documentos en conflicto:** docs/policies/TRACEABILITY_MATRIX.md (encabezado) vs. docs/policies/TRACEABILITY_MATRIX.md (tabla de versiones)
- **Sección doc1:** Encabezado — campo "Estado: BORRADOR — pendiente de aprobación humana"
- **Sección doc2:** Sección "¿Cómo se versiona este documento?" — tabla con entrada: Versión 1.0 | 2026-11-11 | Estado: Aprobada
- **Naturaleza del conflicto:** El mismo documento declara simultáneamente dos estados incompatibles: BORRADOR (pendiente de aprobación) y Aprobada. No es posible determinar el estado real sin consulta al propietario.
- **Severidad:** HIGH
- **Estado:** OPEN — escalado al propietario
- **Resolución:** RESUELTA — 2026-11-13. Estado canónico: **BORRADOR — pendiente de aprobación humana** (igual que el encabezado). La fila de la tabla de control de cambios que indica "Aprobada" es un error documental; no constituye aprobación del propietario. Para FASE 1: la matriz es fuente normativa del proceso de trazabilidad con vigencia de borrador; no bloquea producir el contrato técnico. G3 del contrato no implica aprobación automática de TRACEABILITY_MATRIX. Acción pendiente: change request para actualizar tabla de control de cambios en el documento.

---

### CONF-002 (Pregunta abierta — incertidumbre de estado de BORRADOR vs parámetros operativos)

- **Fecha de detección:** 2026-11-13
- **Documentos afectados:** docs/policies/RISK_POLICY.md, docs/policies/PROFILE_AND_OPERATIONAL_POLICIES.md
- **Naturaleza:** Ambos documentos se declaran en estado BORRADOR o "Propuesta para aprobación". Sin embargo, DOC-001 (OWNEW_CONTEXT.md, aprobado) y DOC-003 (AI_INTEGRATION.md, con principios D1-D4 marcados como aprobados individualmente) referencian implícitamente parámetros que coinciden con los valores de RISK_POLICY.md y PROFILE_AND_OPERATIONAL_POLICIES.md.
- **Severidad:** MEDIUM
- **Estado:** RESUELTA — 2026-11-13
- **Resolución (decisión del propietario):**
  - Jerarquía para el Merger: OWNER_CONTEXT.md (mandato del propietario) > RISK_POLICY.md y PROFILE (borradores formales).
  - **Aprobación operativa vinculante para extracción, Merger y contrato FASE 1:** Los parámetros alineados entre OWNER_CONTEXT y RISK_POLICY están autorizados como decisiones operativas del propietario: capital inicial $3,000 MXN, riesgo 1.5% por operación, drawdown mensual 5%, máx. 8 operaciones/mes, Binance Spot BTC/USDT long-only, una posición simultánea, Nivel 1 de aprobación humana por operación, sin apalancamiento.
  - Metodología cuantitativa/investigación (PROFILE): aprobada como marco obligatorio de diseño e investigación. Aprobación formal del texto queda para G3 del paquete de políticas.
  - AI_INTEGRATION.md: tratar como especificación arquitectónica v1.0 aprobada para diseño del contrato (componentes, flujo, límites IA). Cambios arquitectónicos posteriores vía change request.
  - **Pendientes explícitos (NO resolver por agentes):**
    - Fiscal MX: sin cálculo fiscal definitivo hasta asesoría profesional.
    - Parámetros "por definir" (FX USDT/MXN, % Train/Val/OOS, umbrales ML, etc.): permanecen PENDING en requirements.md.
  - **Nota arquitectónica:** aprobación documental formal ≠ aprobación operativa de parámetros; G3 del contrato técnico = aprobación del paquete implementation/*, no sustituye aprobación individual de cada policy salvo indicación explícita del propietario en G3.
  - **Autorización:** continuar Merger y Verificador cuando terminen extractores; incorporar estas resoluciones en el contrato técnico.

---

### CONF-003

- **Fecha de detección:** 2026-11-13
- **Documentos:** docs/context/OWNEW_CONTEXT.md (DOC-001) vs. docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md (DOC-002)
- **Naturaleza:** discrepancia sobre el régimen fiscal del propietario.
- **Severidad:** HIGH
- **Estado:** RESUELTA — 2026-11-16 (DEC-003)
- **Resolución (propietario):** régimen **605 — Sueldos y Salarios e Ingresos Asimilados a Salarios** (616 del 29/06/2021 al 12/10/2025; 605 con efecto desde el 13/10/2025; aviso al SAT presentado el 17/11/2026). Originales corregidos por instrucción expresa del propietario. El tratamiento fiscal de las ganancias sigue sujeto a validación profesional (REQ-G-P08).

---

### CONF-005

- **Fecha de detección:** 2026-11-13
- **Documentos en conflicto:** docs/context/OWNEW_CONTEXT.md (DOC-001) vs. docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md (DOC-002) y docs/policies/AI_INTEGRATION.md (DOC-003)
- **Sección doc1:** "¿Qué instrumentos y operaciones están permitidos?" — "Instrumento autorizado: BTC/USDT. Otras criptomonedas, conversiones entre criptoactivos... quedan fuera de la validación inicial."
- **Sección doc2:** "Contexto Fiscal — Instrumentos: BTC/USDT o ETH/USDT"
- **Sección doc3:** "¿Qué instrumentos y temporalidades usa? — Activo secundario: ETH/USDT"
- **Naturaleza del conflicto:** DOC-001 (autoridad máxima — operativamente aprobado por DEC-001) restringe el sistema exclusivamente a BTC/USDT y requiere autorización expresa del propietario para incorporar otros activos. DOC-002 y DOC-003 incluyen ETH/USDT como instrumento válido o secundario. El contrato técnico (requirements.md REQ-G-001, REQ-G-005) aplica correctamente la restricción de DOC-001 per la jerarquía de CONF-002. No obstante, la presencia de ETH/USDT en DOC-002 (documento fiscal) tiene implicaciones potenciales para el alcance de las obligaciones SAT — Binance puede reportar también transacciones sobre ETH/USDT bajo CARF.
- **Severidad:** MEDIUM
- **Estado:** RESUELTA — 2026-11-15 (DEC-002)
- **Resolución (propietario):** BTC/USDT es el único par autorizado (Binance, Spot, Long-only; comprar BTC con USDT y vender BTC por USDT). ETH/USDT nunca fue autorizado y se elimina de los alcances operativos. Corrección de DOC-002/DOC-003 vía CR-001 (pendiente de aprobación).

---

### CONF-004

- **Fecha de detección:** 2026-11-13 (detectado por Merger durante integración)
- **Documentos en conflicto:** docs/policies/AI_INTEGRATION.md (DOC-003) vs. docs/context/OWNEW_CONTEXT.md (DOC-001) + docs/policies/RISK_POLICY.md (DOC-005)
- **Sección doc1 (DOC-003):** Sección "Límites y restricciones operativas" — indica riesgo objetivo "1–2% del capital" como rango orientativo
- **Sección doc2 (DOC-001 + DOC-005):** DOC-001: "riesgo_maximo_por_operacion: 1.5%" (aprobado); DOC-005: invariante INV-001 "RiskEffective ≤ Equity × 0.015" (1.5% explícito, aprobado)
- **Naturaleza del conflicto:** El rango "1–2%" de DOC-003 permite hasta 2% de riesgo por operación. El límite "1.5%" en DOC-001 y DOC-005 es el techo aprobado explícitamente. Los documentos son consistentes si "1–2%" es un rango orientativo y "1.5%" es el límite máximo (1.5% cae dentro de 1–2%). No son consistentes si "1–2%" implica que el límite superior puede ser 2%.
- **Severidad:** HIGH — afecta directamente al invariante INV-001 y a todas las pruebas de position sizing
- **Estado:** RESUELTA — 2026-11-15 (DEC-002)
- **Resolución provisional (aplicada por Merger per DEC-001):** Límite vinculante = **1.5%** (máximo). La jerarquía DEC-001 establece que OWNER_CONTEXT y RISK_POLICY tienen precedencia sobre AI_INTEGRATION en parámetros operativos. El "1–2%" de DOC-003 se interpreta como rango referencial; el límite máximo es 1.5%. **Confirmado por el propietario (DEC-002):** 1.5% máximo vinculante, no es rango; la referencia "1–2%" de AI_INTEGRATION es incorrecta y debe eliminarse (CR-001).

---

### CONF-006

- **Fecha de detección:** 2026-11-19 (detectado por el Orquestador de Desarrollo al revisar la propuesta de fuente de datos históricos del propietario)
- **Documentos en conflicto:** propuesta del propietario (sesión 2026-11-19: klines BTC/USDT `interval 1d` y `btcusdt@kline_1d` para backtesting y live) vs. contrato v1.2 (REQ-G-001/002 temporalidades D1/H4/H1; DEC-006 P18; DEC-008 Q24; DEC-009; TC-DATA-001/002) y AI_INTEGRATION.md («Estructura y señal: H4»)
- **Sección doc1:** propuesta del propietario — datos y operación live solo en velas diarias (1d).
- **Sección doc2:** REQ-G-001/002: D1 = contexto, H4 = estructura y señal, H1 = evaluación de entrada; «no se extrapolan resultados de una temporalidad a otra sin validación». DEC-006 P18: la IA se invoca solo al cierre de vela H4 con setup. DEC-009: estimación de costo con 180 ciclos H4/mes. TC-DATA-001/002: vela H4 cerrada.
- **Naturaleza del conflicto:** el contrato define H4 como temporalidad de señal; la propuesta usa solo 1d. Un backtest en 1d no valida estrategias H4, y el diseño de costos/ciclos de IA y las pruebas de datos asumen H4.
- **Severidad:** HIGH — afecta temporalidad de estrategias, ciclo de decisión, costo de IA y pruebas de datos.
- **Estado:** RESUELTA — 2026-11-19 (DEC-013)
- **Resolución (propietario):** opción B. Se mantiene el contrato: D1 contexto, H4 señal, H1 entrada. La propuesta de usar solo 1d se retira por haberse redactado sin revisar REQ-G-001/002. Fuente de datos y snapshot en DEC-013 / CR-013.

---

## Conflictos registrados en FASE 2

### CONF-007

- **Fecha de detección:** 2026-11-19 (detectado por el Orquestador de Desarrollo al implementar FEAT-005, AI Orchestrator)
- **Documentos en conflicto:** `implementation/api_contracts.md` §2 (catálogo de 30 eventos) vs. `implementation/data_flow.md` §5 (cadena E1..E15) y REQ-G-061/062 (todo mensaje con tipo del catálogo; ciclo reconstruible por eventos)
- **Sección doc1:** api_contracts.md §2: existen MARKET_ANALYSIS_COMPLETED y MACRO_ANALYSIS_COMPLETED, pero ningún tipo para la salida del Strategy Analyst.
- **Sección doc2:** data_flow.md §5: «E7 análisis del Strategy Analyst (X, causation_id: E4)», sin nombre de evento; E8 (DECISION_SYNTHESIS_COMPLETED) lo cita como causa.
- **Naturaleza del conflicto:** el flujo exige registrar el análisis del Strategy Analyst como evento de la cadena, pero el catálogo no define su tipo. Sin él, la salida del Strategy Analyst no queda en el registro de auditoría y la reconstrucción del ciclo (TC-AC-04) es incompleta. Añadir un tipo de evento modifica el contrato aprobado.
- **Severidad:** MEDIUM — no afecta riesgo ni ejecución; afecta trazabilidad y auditoría.
- **Estado:** RESUELTA — 2026-11-19 (DEC-014 Q30, CR-015 aplicada, contrato v1.4)
- **Resolución (propietario):** se añade `STRATEGY_ANALYSIS_COMPLETED` al catálogo y se nombra E7. La mitigación provisional (salida validada pero no emitida como evento) se retiró del AI Orchestrator.
- **Historial:** escalado el 2026-11-19; CR-015 (`harness/change_requests/CR-015_evento-analisis-strategy-analyst.md`) propuesta y aprobada el mismo día; añade `STRATEGY_ANALYSIS_COMPLETED` a api_contracts.md §2 y a data_flow.md §5 (E7).

---

### CONF-008

- **Fecha de detección:** 2026-11-20 (QA independiente focalizada de FEAT-018..022, hallazgo QA3E-01; confirmado por el Orquestador de Desarrollo al corregirlo)
- **Documentos en conflicto:** `implementation/api_contracts.md` §3.8 B.8 punto 2 y `test_plan.md` TC-NORM-002 vs. `api_contracts.md` §2 (catálogo cerrado de 33 tipos, REQ-G-063/064) y REQ-G-061 (todo mensaje registrado tiene un tipo del catálogo)
- **Sección doc1:** B.8 punto 2: si la síntesis no es consistente con el candidato, «no se emite TRADE_PROPOSAL. `DECISION_SYNTHESIS_COMPLETED` se conserva y se registra la inconsistencia con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados». TC-NORM-002: «se registra PROPOSAL_INCONSISTENT_WITH_CANDIDATE».
- **Sección doc2:** §2: ningún tipo del catálogo transporta el resultado de la normalización; TRADE_PROPOSAL está prohibido en este caso por el propio B.8; E8 ya está registrado y el EventStore es append-only.
- **Naturaleza del conflicto:** el contrato exige registrar la inconsistencia, pero no define el tipo con que se registra. Hoy queda solo en memoria (`CycleReport.normalization`), sin rastro en el EventStore. Registrarla exige elegir un tipo nuevo o ampliar uno existente, y cualquiera de las dos cosas modifica el contrato aprobado.
- **Severidad:** MEDIUM. No afecta al riesgo ni a la ejecución: no se emite ninguna propuesta y Fail-Closed se mantiene. Afecta a la trazabilidad y a la auditoría (TC-AC-04).
- **Estado:** RESUELTA — 2026-11-20 (DEC-020, CR-019 aplicada, contrato v1.7)
- **Resolución (propietario):** opción A. Se añade `PROPOSAL_NORMALIZATION_REJECTED` al catálogo (34 tipos) en la posición E9, con `causation_id` = E8 (`api_contracts.md` §3.8 B.10). El ciclo lo registra en el EventStore. QA3E-01 queda corregido.
- **Opciones (para decisión del propietario; ninguna aplicada):**
  - A. **Tipo nuevo** `PROPOSAL_NORMALIZATION_REJECTED`. Productor: la capa de validación del AI Orchestrator; `causation_id` = E8; payload con `reason_code` (`PROPOSAL_INCONSISTENT_WITH_CANDIDATE` | `OUT_OF_CONTRACT`) y `affected_fields`; ocupa la posición E9. Es el mismo patrón que CONF-007 y CR-015, y el catálogo pasa a 34 tipos.
  - B. **Ampliar `NO_SETUP`** con un motivo nuevo. No se recomienda: `NO_SETUP` es del Strategy Engine, con `causation_id` = E2 (B.7), y mezclaría productores.
  - C. **Registrarlo fuera del EventStore** (registro de auditoría aparte). No se recomienda: la cadena del ciclo quedaría incompleta (REQ-G-062).
- **Recomendación del Orquestador:** A, mediante una CR (CR-019) con impacto en api_contracts §2 y §3.8 B.8, data_flow §5 (E9) y test_plan TC-NORM-002.
- **Historial:** 2026-11-20: el propietario elige la opción A («redacta CR-019 opción A»). CR-019 queda redactada en PROPUESTA (`harness/change_requests/CR-019_evento-rechazo-normalizacion.md`), sin aplicar.

---

### CONF-009

- **Fecha de detección:** 2026-11-24 (detectado por el Orquestador de Desarrollo al preparar el registro de la resolución D1 de FEAT-017, antes de escribir nada)
- **Documentos en conflicto:** resolución D1 del propietario (2026-11-24; `progress.md`, `harness/verification/IMPL-3_EXP-0001_procedencia.md` §6) vs. semántica del registro de experimentos (`src/swingpilot/research/experiments.py`; `research/experiments/registry.jsonl`; `research/README.md`)
- **Sección doc1:** D1: la documentación recuperada de `trading-bot@21c5f25` (preregistro v4 congelado, D-024, configuraciones A–D, hash del manifiesto de datos) basta para reconocer EXP-0001 como antecedente histórico documentado; su ejecución, sus resultados de Train y su rendimiento estadístico siguen siendo desconocidos. No se clasifica como aprobado, validado, exitoso, rechazado ni inconcluso.
- **Sección doc2:** `ANTECEDENT_STATES = ("PENDING_DOCUMENTATION", "REJECTED", "INCONCLUSIVE")` (`experiments.py:100`); `register_antecedent` rechaza un identificador ya registrado (`experiments.py:241-242`); `transition` rechaza los antecedentes declarados (`experiments.py:292-293`); los tipos `TRANSITION`, `PARTITION_CONSUMED` y `DEVIATION` tienen otro significado; el registro no se edita a mano (`research/README.md`).
- **Naturaleza del conflicto:** la semántica vigente del registro no puede representar con exactitud la resolución D1. `PENDING_DOCUMENTATION` contradice la suficiencia documental aprobada; `REJECTED` e `INCONCLUSIVE` clasificarían EXP-0001 por resultados que no existen; un segundo registro `ANTECEDENT` escrito a mano eludiría la validación y, al reproducirse el registro, sustituiría el historial anterior en lugar de añadirse. Ningún otro tipo de registro corresponde.
- **Severidad:** LOW. No afecta al riesgo, a la ejecución ni al conteo actual de `trials_count` (el antecedente sigue contado una vez); los antecedentes declarados no son elegibles para abrir particiones ni promover modelos. Afecta a la trazabilidad: el estado registrado de EXP-0001 no refleja la decisión vigente del propietario.
- **Estado:** OPEN
- **Mitigación vigente (propietario, 2026-11-24, opción A):** el registro de experimentos no se modifica. EXP-0001 conserva `PENDING_DOCUMENTATION` **solo** porque la semántica actual no puede representar la resolución aprobada; ese estado **no** debe interpretarse como la valoración actual del propietario sobre la suficiencia documental. La resolución D1 consta a nivel documental en `progress.md`, `session-handoff.md` y en el informe de procedencia (§6). El registro de Mean Reversion H1 (`ANT-MR-H1`, `REJECTED`) no cambia.
- **Solución candidata diferida (no aprobada; no es una CR):** B. un tipo de registro de procedencia separado (p. ej., `ANTECEDENT_PROVENANCE`), leído junto al registro `ANTECEDENT` original sin cambiar su estado ni el conteo de `trials_count`. Exigiría cambios de código y pruebas, autorización del propietario y probablemente una CR. Otra alternativa analizada y no elegida: C. un estado de antecedente nuevo (p. ej., `DOCUMENTED_RESULT_UNKNOWN`), que también exige código, pruebas y probablemente una CR.
- **Condición de reevaluación (propietario, 2026-11-24):** la resolución de CONF-009 debe reevaluarse obligatoriamente antes del cierre formal de FEAT-017. FEAT-017 no puede cerrarse formalmente mientras esa reevaluación no conste.
- **Historial:** 2026-11-24: el Orquestador detiene el registro de D1 y escala el conflicto con las opciones A, B y C; el propietario aprueba la opción A con seguimiento formal y mantiene el conflicto abierto. 2026-11-24: el propietario confirma la severidad LOW y el estado OPEN, aprueba el registro (commit `2e13c27`) y fija la condición de reevaluación.
- **Seguimiento (2026-11-24):** la opción B se evalúa dentro de CR-020 (PROPUESTA, no aprobada; `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md`), junto con CONF-010. A diferencia de la descripción anterior, en CR-020 el registro de procedencia **sí** alimenta el conteo de pruebas (por configuraciones), porque D2 cambia la unidad de `trials_count`. CONF-009 sigue OPEN.
- **Solución propuesta aprobada (propietario, 2026-11-24):** `ANTECEDENT_PROVENANCE` (CR-020 C.3.1), siempre que las consultas consolidadas distingan el estado original inmutable del registro `ANTECEDENT` de la procedencia documental vigente. Aprobación de la solución, no de su aplicación: CONF-009 sigue OPEN hasta su implementación y verificación, y se mantiene la reevaluación obligatoria antes del cierre formal de FEAT-017.
- **CR-020 aprobada (2026-11-24, DEC-021) y aplicada solo contractualmente (contrato v1.8).** `ANTECEDENT_PROVENANCE` queda en el contrato (REQ-G-104). CONF-009 sigue OPEN hasta que se acepten la evidencia de implementación y la de verificación; la reevaluación obligatoria antes del cierre formal de FEAT-017 sigue vigente.
- **Procedencia real registrada (2026-11-24, DEC-022):** dos registros `ANTECEDENT_PROVENANCE` (ANT-MR-H1 y EXP-0001) escritos con la API validada; la consulta consolidada separa el estado original (PENDING_DOCUMENTATION de EXP-0001) de la procedencia vigente (DOCUMENTED, ejecución UNKNOWN). CONF-009 sigue OPEN hasta la verificación independiente.
- **Verificación independiente de CR-020 (2026-11-24; nota añadida por la conciliación documental de QA-CR020-06):** el revisor independiente (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, base `f2f05a9`) declaró CONFORME el mecanismo de procedencia (TC-ML-021; gramática `AUTORIZA: PROCEDENCIA`; estado original separado) y el registro real (AC-017-13, DEC-022), y no encontró ningún defecto en ellos; veredicto global CONFORME CON OBSERVACIONES, aceptado por el propietario. El informe recomienda (§8) que pueda proponerse el cierre de CONF-009 una vez actualizada la trazabilidad (QA-CR020-06); es una recomendación del revisor, no una decisión. CONF-009 sigue OPEN; su cierre y la reevaluación obligatoria antes del cierre formal de FEAT-017 siguen PENDIENTES del propietario.
- **Nota de vigencia de la severidad (2026-11-24; QA-CR020-06):** la frase de la severidad «No afecta […] ni al conteo actual de `trials_count` (el antecedente sigue contado una vez)» se conserva sin cambios y describe el conteo por identificador de experimento vigente al detectarse el conflicto. Desde CR-020 (DEC-021, contrato v1.8; implementado en `824fae8`) y DEC-022 (`f2f05a9`), `trials_count` cuenta pares experimento–configuración y la procedencia documental alimenta el conteo: registro real H_doc 4, H_bound 4 (cota), E 0, G 8 (seguimiento anterior y `harness/verification/IMPL-3_CR-020_implementacion.md` §10). Esta nota no reevalúa la severidad (LOW) ni cambia el estado.

---

### CONF-010

- **Fecha de detección:** 2026-11-24 (revisión de solo lectura de D2, unidad de `trials_count`, por el Orquestador de Desarrollo)
- **Documentos en conflicto:** `docs/decisions/DEC-005_parametros-investigacion-ml-bloque-2.md` Q11 y `implementation/requirements.md` REQ-G-P17 vs. `docs/policies/PROFILE_AND_OPERATIONAL_POLICIES.md` §«Entrenamiento y selección» (línea 250), y ambos vs. la implementación de FEAT-017 (`src/swingpilot/research/experiments.py`, `acceptance.py`, `preregistration.py`)
- **Sección doc1:** DEC-005 Q11: «corrección por número de experimentos probados (p. ej. Deflated Sharpe), usando el conteo del preregistro». REQ-G-P17: «corrección por nº de experimentos».
- **Sección doc2:** política: «Cuando se comparen numerosos modelos, deberá registrarse el número de configuraciones probadas y contemplarse el riesgo de selección estadística». La extracción la recogió (`harness/extraction/outputs/DOC-004.json`), pero no pasó al contrato.
- **Naturaleza del conflicto:** (1) **Unidad:** experimentos (DEC-005, REQ-G-P17) frente a configuraciones (política); el contrato no define «prueba». (2) **Fuente del conteo:** DEC-005 exige el conteo del preregistro; la implementación usa el conteo vivo del registro al evaluar (`acceptance.py:182`, por QA3-07) y el campo `trials_count` del preregistro solo se comprueba por presencia (`preregistration.py:28`). (3) **Qué cuenta la implementación:** identificadores de experimento con registro `CREATED` o `ANTECEDENT` (`experiments.py:187-189`), sin distinguir configuraciones, ideas no evaluadas ni ejecución desconocida; con el registro real da 2, frente a 8 configuraciones documentadas en los antecedentes (4 evaluadas de Mean Reversion H1 y 4 de EXP-0001 con ejecución desconocida). Resolverlo cambia el significado de REQ-G-P17 y exige una CR.
- **Severidad:** MEDIUM (confirmada por el propietario el 2026-11-24). No afecta al riesgo ni a la ejecución (solo investigación) ni a ningún resultado actual: no hay evaluaciones confirmatorias. Si no se corrige, la corrección por selección del piloto quedaría subestimada y el umbral efectivo del Deflated Sharpe sería demasiado permisivo.
- **Estado:** OPEN
- **Dirección aprobada (propietario, 2026-11-24, D2):** contar configuraciones evaluadas (incluidas rechazadas y abandonadas); excluir ideas y configuraciones confirmadas como nunca evaluadas; cota conservadora documentada para antecedentes con ejecución desconocida; conteo histórico inicial conservador de 8 (4 evaluaciones documentadas de Mean Reversion H1 y 4 configuraciones preregistradas de EXP-0001 como cota, no como ejecuciones verificadas); excluir escenarios puros de costes y corridas idénticas de reproducibilidad solo si no introducen selección adicional. No aprobada: la regla del máximo de ambos conteos.
- **Solución propuesta:** CR-020 (PROPUESTA, no aprobada ni aplicada; `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md`).
- **Historial:** 2026-11-24: detectado en la revisión de D2; el propietario aprueba la dirección metodológica y pide registrar el conflicto y redactar una CR. 2026-11-24: el propietario confirma la severidad MEDIUM y fija decisiones para la revisión 2 de CR-020 (población de todas las familias BTC/USDT; conteo congelado con conciliación de pruebas posteriores basada en evidencia y sin LLM; configuraciones planificadas incluidas; reducción prospectiva de cotas solo con evidencia y aprobación). CR-020 sigue PROPUESTA; CONF-010 sigue OPEN. 2026-11-24: el propietario aprueba CR-020 revisión 3 (DEC-021) y autoriza solo su aplicación contractual: contrato v1.8 (REQ-G-P17, REQ-G-103, REQ-G-104, TC-ML-006, TC-ML-020..024) y AC-017-3/8/13. CONF-010 sigue OPEN hasta que se acepten la evidencia de implementación y la de verificación.
- **CR-021 aprobada (2026-11-24, DEC-023) y aplicada solo documentalmente (contrato v1.9):** concreta REQ-G-P17: un inicio de evaluación no confirmado cuenta de forma conservadora mientras conste, y toda evaluación con acceso autorizado tiene evidencia contable duradera (`EVALUATION_PERSISTED`; origen: QA-CR020-03). Implementación y verificación PENDIENTES. CONF-010 sigue OPEN.
- **Seguimiento (2026-11-24; nota añadida por la conciliación documental de QA-CR020-06; las entradas anteriores se conservan):** CR-020 implementada (`824fae8`, con la corrección A2) y aceptada por el propietario; procedencia real registrada (DEC-022, `f2f05a9`). Verificación independiente de CR-020 sobre `f2f05a9`: CONFORME CON OBSERVACIONES, informe aceptado por el propietario (`harness/verification/IMPL-3_CR-020_QA_independiente.md`). CR-021 implementada (`0051014`) y aceptada por el propietario. Correcciones QA-CR020-01 (`fde522c`), QA-CR020-02 (`d84535a`) y QA-CR020-03 (CR-021) aceptadas por el propietario; QA-CR020-04 aclarada por CR-022 (DEC-024, contrato v1.10; CONF-011 RESOLVED) y QA-CR020-05 resuelto por solapamiento con CR-021, ambos verificados por el implementador y aceptados. Reverificación independiente de QA-CR020-01..05 PENDIENTE; QA-CR020-O3 y O4 sin resolver. Aceptación del propietario ≠ verificación independiente. Esta nota no reevalúa la severidad (MEDIUM) ni cambia el estado: CONF-010 sigue OPEN.

### CONF-011

- **Fecha de detección:** 2026-11-24 (QA independiente de CR-020, hallazgo QA-CR020-04, sonda P5; confirmado en la evaluación de solo lectura sobre `d84535a` por el Orquestador de Desarrollo)
- **Documentos en conflicto:** `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` §C.4.2, tabla de clasificación, caso 2, vs. la definición de `informed_by` (R2) de la misma sección; y el texto de CR-020 vs. la implementación de FEAT-017 (`src/swingpilot/research/trials.py:128-145`, `experiments.py` `informed_by_error`). REQ-G-P17, TC-ML-024 y DEC-021 no lo resuelven.
- **Sección doc1:** caso 2: «Algún punto de decisión de X posterior a `T` cita en `informed_by` el experimento o el par de `T`» → RELEVANTE. Casos 1 y 3: «cita `T`», sin nivel.
- **Sección doc2:** R2: `informed_by` «es la lista de pares (`experiment_id`, `config_id`) o de `provenance_id` cuyos resultados se consultaron»; `T` es un único registro `CONFIGURATION_EVALUATED` (un par).
- **Naturaleza del conflicto:** el caso 2 nombra una cita a nivel de experimento que la gramática aprobada no puede expresar. Caben dos lecturas con efectos distintos: (P) solo cuenta el par exacto, que es lo implementado; (E) citar un par de `Y` cita todo `Y`, lo que eleva `N_eval` pero en el caso 3 cambiaría un INCONCLUSIVE por RELEVANTE. Ninguna está establecida de forma explícita.
- **Severidad:** LOW (confirmada por el propietario el 2026-11-24, DEC-024). Solo investigación; sin evaluaciones confirmatorias ni resultados afectados. Afecta a `N_eval` y a la clasificación de pruebas posteriores, no al riesgo ni a la ejecución.
- **Estado:** RESOLVED (2026-11-24; OPEN desde su registro hasta la aceptación de la evidencia de caracterización)
- **Resolución (propietario, 2026-11-24):** se adopta la lectura por par exacto. CR-022 (`harness/change_requests/CR-022_relevancia-por-par-exacto.md`), aprobada por DEC-024 (`docs/decisions/DEC-024_aprobacion-cr022-relevancia-par-exacto.md`) y aplicada al contrato v1.10 (REQ-G-P17, TC-ML-024; nota de vigencia §J en CR-020): un punto de decisión cita una prueba posterior solo con la referencia exacta de su par; cada prueba posterior se clasifica por separado, también las del mismo experimento; el caso 3 prevalece sobre el caso 2; la gramática de `informed_by` y la semántica de `provenance_id` no cambian; no hay referencias a experimentos completos. Evidencia aceptada: `harness/verification/IMPL-3_CR-022_caracterizacion.md` (4 pruebas de caracterización con su discriminación por mutantes; 826 passed, 5 skipped; validadores OK). Sin cambios de código funcional. Pendiente: reverificación independiente de QA-CR020-04.
- **Dirección aprobada (propietario, 2026-11-24):** opción A, referencias al par exacto; se rechaza la atribución implícita a nivel de experimento; cada configuración se clasifica por separado; se conserva INCONCLUSIVE cuando la influencia no puede determinarse; las referencias explícitas a experimentos quedan diferidas.
- **Solución propuesta:** CR-022 (`harness/change_requests/CR-022_relevancia-por-par-exacto.md`; PROPUESTA al registrarse, APROBADA después por DEC-024). La implementación actual ya cumple la aclaración propuesta (CR-022 §E).
- **Historial:** 2026-11-24: registrado al preparar CR-022 por indicación del propietario. QA-CR020-04 sigue sin resolver hasta que la aclaración se apruebe y se verifique.
- **CR-022 aprobada (2026-11-24, DEC-024) y aplicada al contrato v1.10:** REQ-G-P17 y TC-ML-024; nota de vigencia §J en CR-020. Pruebas de caracterización (CR-022 §F) aprobadas en alcance; implementación y ejecución diferidas a una autorización separada. CONF-011 sigue OPEN hasta que se produzca y revise esa evidencia.
- **Resolución (2026-11-24):** el propietario aprueba la evidencia de caracterización de CR-022 §F bajo DEC-024 y el contrato v1.10 y resuelve CONF-011. Se conservan las entradas anteriores.
