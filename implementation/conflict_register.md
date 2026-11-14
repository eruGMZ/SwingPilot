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
    - Fiscal MX (CSF 616 vs ingresos laborales): sin cálculo fiscal definitivo hasta asesoría profesional.
    - Parámetros "por definir" (FX USDT/MXN, % Train/Val/OOS, umbrales ML, etc.): permanecen PENDING en requirements.md.
  - **Nota arquitectónica:** aprobación documental formal ≠ aprobación operativa de parámetros; G3 del contrato técnico = aprobación del paquete implementation/*, no sustituye aprobación individual de cada policy salvo indicación explícita del propietario en G3.
  - **Autorización:** continuar Merger y Verificador cuando terminen extractores; incorporar estas resoluciones en el contrato técnico.

---

### CONF-003

- **Fecha de detección:** 2026-11-13
- **Documentos en conflicto:** docs/context/OWNEW_CONTEXT.md (DOC-001) vs. docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md (DOC-002)
- **Sección doc1:** "¿Cuál es la situación fiscal y laboral documentada?" — tabla: "Régimen que aparece en la CSF: 616 — Sin obligaciones fiscales"
- **Sección doc2:** "1. Contexto Fiscal" — tabla: "Régimen: Sueldos y Salarios (clave 601)"
- **Naturaleza del conflicto:** DOC-001 indica Régimen 616 (Sin obligaciones fiscales) según la CSF física. DOC-002 indica Régimen 601 (Sueldos y Salarios). Estos son regímenes fiscales distintos con implicaciones diferentes: la exención Art. 93 XIX b) aplicada en DOC-002 está diseñada para Régimen 601. Con Régimen 616, el tratamiento fiscal podría ser distinto. No es posible determinar el régimen correcto sin consulta al SAT o asesoría fiscal.
- **Severidad:** HIGH
- **Estado:** OPEN — escalado al propietario. Requiere verificación directa con el SAT o asesor fiscal antes de establecer obligaciones fiscales definitivas.
- **Resolución:** PENDIENTE — no resolver por los agentes. El Merger debe tratar el cálculo de exención (Art. 93 XIX b) como PENDIENTE/CONDICIONAL hasta resolución. Los parámetros operativos (capital, riesgo, instrumento) no dependen de esta resolución y permanecen vinculantes per CONF-002.

---

### CONF-005

- **Fecha de detección:** 2026-11-13
- **Documentos en conflicto:** docs/context/OWNEW_CONTEXT.md (DOC-001) vs. docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md (DOC-002) y docs/policies/AI_INTEGRATION.md (DOC-003)
- **Sección doc1:** "¿Qué instrumentos y operaciones están permitidos?" — "Instrumento autorizado: BTC/USDT. Otras criptomonedas, conversiones entre criptoactivos... quedan fuera de la validación inicial."
- **Sección doc2:** "Contexto Fiscal — Instrumentos: BTC/USDT o ETH/USDT"
- **Sección doc3:** "¿Qué instrumentos y temporalidades usa? — Activo secundario: ETH/USDT"
- **Naturaleza del conflicto:** DOC-001 (autoridad máxima — operativamente aprobado por DEC-001) restringe el sistema exclusivamente a BTC/USDT y requiere autorización expresa del propietario para incorporar otros activos. DOC-002 y DOC-003 incluyen ETH/USDT como instrumento válido o secundario. El contrato técnico (requirements.md REQ-G-001, REQ-G-005) aplica correctamente la restricción de DOC-001 per la jerarquía de CONF-002. No obstante, la presencia de ETH/USDT en DOC-002 (documento fiscal) tiene implicaciones potenciales para el alcance de las obligaciones SAT — Binance puede reportar también transacciones sobre ETH/USDT bajo CARF.
- **Severidad:** MEDIUM
- **Estado:** OPEN — escalado al propietario. La decisión operativa (BTC/USDT únicamente) es correcta per jerarquía de autoridad. Se requiere confirmación del propietario para: (a) ratificar que ETH/USDT está fuera del alcance de FASE 1 y FASE 2, (b) confirmar que las referencias a ETH/USDT en DOC-002 y DOC-003 son contextuales y no implican habilitación futura sin autorización expresa.
- **Resolución:** PENDIENTE — La restricción BTC/USDT en el contrato técnico es la decisión correcta per DEC-001/CONF-002. El propietario debe ratificar explícitamente que ETH/USDT queda fuera del alcance. Hasta ratificación, el sistema implementa únicamente BTC/USDT.

---

### CONF-004

- **Fecha de detección:** 2026-11-13 (detectado por Merger durante integración)
- **Documentos en conflicto:** docs/policies/AI_INTEGRATION.md (DOC-003) vs. docs/context/OWNEW_CONTEXT.md (DOC-001) + docs/policies/RISK_POLICY.md (DOC-005)
- **Sección doc1 (DOC-003):** Sección "Límites y restricciones operativas" — indica riesgo objetivo "1–2% del capital" como rango orientativo
- **Sección doc2 (DOC-001 + DOC-005):** DOC-001: "riesgo_maximo_por_operacion: 1.5%" (aprobado); DOC-005: invariante INV-001 "RiskEffective ≤ Equity × 0.015" (1.5% explícito, aprobado)
- **Naturaleza del conflicto:** El rango "1–2%" de DOC-003 permite hasta 2% de riesgo por operación. El límite "1.5%" en DOC-001 y DOC-005 es el techo aprobado explícitamente. Los documentos son consistentes si "1–2%" es un rango orientativo y "1.5%" es el límite máximo (1.5% cae dentro de 1–2%). No son consistentes si "1–2%" implica que el límite superior puede ser 2%.
- **Severidad:** HIGH — afecta directamente al invariante INV-001 y a todas las pruebas de position sizing
- **Estado:** OPEN — pendiente de confirmación del propietario. Decisión provisional aplicada en el contrato técnico.
- **Resolución provisional (aplicada por Merger per DEC-001):** Límite vinculante = **1.5%** (máximo). La jerarquía DEC-001 establece que OWNER_CONTEXT y RISK_POLICY tienen precedencia sobre AI_INTEGRATION en parámetros operativos. El "1–2%" de DOC-003 se interpreta como rango referencial; el límite máximo es 1.5%. Requiere confirmación del propietario en G3.
