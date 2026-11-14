# DEC-001 — Resoluciones de Estado Documental para FASE 1

**Fecha:** 2026-11-13  
**Propietario:** Erick Uriel Reyes Gómez  
**Contexto:** Respuestas a CONF-001 y CONF-002 detectados en Gate G0 de FASE 1.

---

## Decisión 1: Estado canónico de TRACEABILITY_MATRIX.md

**Estado canónico:** BORRADOR — pendiente de aprobación humana del propietario.

La fila de la tabla de control de cambios que indica versión 1.0 "Aprobada" es un **error documental**; no constituye aprobación del propietario.

- Para FASE 1: la matriz es fuente normativa del proceso de trazabilidad, con vigencia de borrador.
- No bloquea producir el contrato técnico.
- G3 del contrato técnico no implica aprobación automática de TRACEABILITY_MATRIX como documento.
- Acción pendiente: change request para corregir la tabla de control de cambios.

---

## Decisión 2: Aprobación operativa de parámetros de RISK_POLICY y PROFILE

**Jerarquía de autoridad para Merger y contrato técnico:**
1. `docs/context/OWNEW_CONTEXT.md` — Aprobado — mandato del propietario
2. `docs/policies/RISK_POLICY.md` — BORRADOR formal
3. `docs/policies/PROFILE_AND_OPERATIONAL_POLICIES.md` — Propuesta formal

**Aprobación operativa vinculante para construcción del contrato técnico:**

Los siguientes parámetros están autorizados como decisiones operativas del propietario:

| Parámetro | Valor |
|---|---|
| Capital inicial | $3,000 MXN |
| Riesgo máximo por operación | 1.5% del equity actual |
| Drawdown mensual máximo | 5% |
| Frecuencia máxima | 8 operaciones/mes |
| Exchange | Binance Spot |
| Par inicial | BTC/USDT |
| Dirección | Long-only |
| Posiciones simultáneas | 1 |
| Nivel de autonomía | Nivel 1 — aprobación humana por operación |
| Apalancamiento | No permitido |

**Metodología cuantitativa/investigación (PROFILE):** Aprobada como marco obligatorio de diseño e investigación para el contrato técnico. La aprobación formal del texto completo del documento queda para G3 del paquete de políticas.

**AI_INTEGRATION.md:** Tratar como especificación arquitectónica v1.0 aprobada para diseño del contrato (componentes, flujo, límites de IA). Cambios arquitectónicos posteriores vía change request.

---

## Pendientes explícitos — NO resolver por agentes

- **Fiscal MX** (discrepancia CSF 616 vs ingresos laborales): sin cálculo fiscal definitivo hasta asesoría profesional.
- **Parámetros técnicos "por definir"**: fuente FX USDT/MXN, antigüedad máxima del tipo de cambio, % Train/Val/OOS, umbrales ML, política de reentrenamiento, etc. — permanecen PENDING en requirements.md.

---

## Nota de arquitectura del Harness

- Aprobación documental formal ≠ aprobación operativa de parámetros.
- G3 del contrato técnico = aprobación del paquete `implementation/*`. No sustituye aprobación individual de cada policy salvo indicación explícita del propietario en G3.

---

**Firmado:** Propietario del proyecto — 2026-11-13
