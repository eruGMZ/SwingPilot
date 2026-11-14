# session-handoff.md — SwingPilot Harness
> Actualizado: 2026-11-13 — Fin de sesión FASE 1 (G2 PASS — verificación adversarial completa, 6 hallazgos aplicados)

---

## Estado Actual de Gates

| Gate | Nombre | Estado | Requiere aprobación humana |
|------|--------|--------|---------------------------|
| G0 | Integridad y registro documental | **PASS** | No |
| G1 | Cobertura de extracción | **PASS** | No |
| G2 | Consistencia y trazabilidad | **PASS** | No |
| G3 | Aprobación humana del contrato | **PENDING** | **SÍ — BLOQUEANTE** |
| G4 | Pruebas de implementación | PENDING | No |
| G5 | Integración y regresión | PENDING | No |
| G6 | Seguridad | PENDING | No |
| G7 | Aprobación de release | PENDING | SÍ |

---

## Próxima Acción Requerida: G3

**G3 solo puede aprobarse con autorización humana explícita del propietario.**

El contrato técnico está listo para revisión. Documentos a revisar:
- [implementation/requirements.md](implementation/requirements.md) — 224 requisitos consolidados, 12 invariantes, 8 estados Risk Manager
- [implementation/architecture.md](implementation/architecture.md) — 15 componentes, flujo de decisión 7 fases
- [implementation/api_contracts.md](implementation/api_contracts.md) — contratos de mensajes, Binance, Anthropic, Telegram, trades.db
- [implementation/data_flow.md](implementation/data_flow.md) — flujos principal, bloqueo, investigación, fiscal, Fail-Closed
- [implementation/test_plan.md](implementation/test_plan.md) — 16 AC + 16 RM criterios, plan por fase

**Para aprobar G3, el propietario debe responder explícitamente** (ejemplos aceptables):
- "APRUEBO EL CONTRATO TÉCNICO v1.0"
- "G3 aprobado — proceder a FASE 2"
- "El contrato está bien, autorizo FASE 2"

**Tras G3:** Se habilita FASE 2 — implementación incremental con evidencia por criterio de aceptación.

---

## Resumen de Extracción

| Documento | ID | Requisitos | Formato IDs |
|-----------|-----|-----------|-------------|
| OWNEW_CONTEXT.md | DOC-001 | 22 | REQ-1001..1022 |
| CONTEXTO_FISCAL_OPERATIVO.md | DOC-002 | 15 | REQ-2001..2015 |
| AI_INTEGRATION.md | DOC-003 | 75 | REQ-3001..3075 |
| PROFILE_AND_OPERATIONAL_POLICIES.md | DOC-004 | 38 | REQ-4001..4038 |
| RISK_POLICY.md | DOC-005 | 42 | REQ-5001..5042 |
| TRACEABILITY_MATRIX.md | DOC-006 | 32 | REQ-6001..6032 |
| **TOTAL** | | **224** | |

Nota: Extracción completa. Las 6 extracciones cubren íntegramente los 6 documentos fuente.

---

## Conflictos Registrados

| ID | Documentos | Estado |
|----|-----------|--------|
| CONF-001 | TRACEABILITY_MATRIX.md (encabezado vs tabla versiones) | RESUELTA — estado canónico: BORRADOR |
| CONF-002 | RISK_POLICY.md, PROFILE (BORRADOR vs parámetros operativos) | RESUELTA — parámetros operativos aprobados vía OWNEW_CONTEXT |
| CONF-003 | OWNEW_CONTEXT (régimen 616) vs CONTEXTO_FISCAL (régimen 601) | OPEN — escalado al propietario, requiere asesoría fiscal |
| CONF-004 | AI_INTEGRATION "1-2% riesgo" vs OWNER_CONTEXT/RISK_POLICY "1.5% máximo" | OPEN — límite vinculante 1.5% aplicado en contrato |
| CONF-005 | DOC-001 (BTC/USDT únicamente) vs DOC-002/DOC-003 (también ETH/USDT) | OPEN — restricción BTC/USDT aplicada per jerarquía DEC-001 |

---

## Parámetros PENDING (12 ítems — resolver en FASE 2)

1. Fuente de conversión USDT/MXN
2. Antigüedad máxima aceptable del tipo de cambio
3. Comisión efectiva de Binance (obtener de cuenta real)
4. Reserva de slippage (configuración técnica conservadora)
5. Tolerancia de desviación de precio
6. stepSize / minQty / minNotional BTC/USDT (obtener de Binance)
7. Frecuencia de reconciliación con Binance
8. Mecanismo técnico de aprobación humana (Telegram)
9. Procedimiento de recuperación ante fallos
10. Umbrales ML (Sharpe, Drawdown, Win Rate, etc.)
11. Splits Train/Validation/OOS
12. Asesoría fiscal definitiva (Régimen 616 vs ganancias trading)

---

## Archivos del Harness (todos validados)

```
harness/manifest.json              — G2_PASS, todos los docs VERIFIED
harness/gates/gate_status.json     — G0=PASS, G1=PASS, G2=PASS, G3..G7=PENDING
harness/extraction/outputs/        — 6 archivos JSON, 224 requisitos
harness/verification/VER-001.json  — reporte adversarial PASS
implementation/requirements.md     — contrato de requisitos DRAFT
implementation/architecture.md     — contrato de arquitectura DRAFT
implementation/api_contracts.md    — contratos de API DRAFT
implementation/data_flow.md        — flujo de datos DRAFT
implementation/test_plan.md        — plan de pruebas DRAFT
implementation/conflict_register.md — CONF-001, CONF-002 resueltos
```

---

## Reglas para el Próximo Agente

1. **G3 solo puede aprobarse con autorización humana explícita** — no auto-aprueben
2. Si el propietario aprueba G3, marcar gate_status.json con `approved_by: "propietario"`, `approved_at: "fecha"` y `evidence: "texto de la aprobación"`
3. FASE 2 está BLOQUEADA hasta G3
4. Los archivos en `docs/` son SOLO LECTURA — fuentes documentales del propietario
5. Los archivos en `src/` están vacíos — correctamente, hasta FASE 2
6. Los parámetros PENDING no se rellenan por suposición — solo con información real del propietario o del sistema Binance
7. No crear código funcional de SwingPilot hasta G3 aprobado
