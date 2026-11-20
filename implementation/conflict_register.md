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
