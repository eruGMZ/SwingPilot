# VERIFICATION REPORT — G2 — SwingPilot Technical Contract

**Verifier:** VERIFIER-AGENT (independent, fresh context — no Merger reasoning inherited)  
**Date:** 2026-11-13  
**Contract version:** requirements.md v0.1, architecture.md v0.1, api_contracts.md v0.1, data_flow.md v0.1, test_plan.md v0.1, conflict_register.md v0.1  
**Sources audited:** DOC-001 (OWNEW_CONTEXT.md), DOC-002 (CONTEXTO_FISCAL_OPERATIVO.md), DOC-003 (AI_INTEGRATION.md), DOC-004 (PROFILE_AND_OPERATIONAL_POLICIES.md), DOC-005 (RISK_POLICY.md), DOC-006 (TRACEABILITY_MATRIX.md)

---

## VERDICT: PASS_WITH_FINDINGS

---

## Summary

The merged technical contract faithfully represents the original source documents across all critical dimensions: all 12 risk invariants (INV-001 through INV-012) are present with correct values, all four formulas (position sizing, equity, risk budget, drawdown) match the sources exactly, the 5 AI agents and 11 non-LLM components are correctly identified, all absolute prohibitions are present, and the DDL schema for trades.db matches DOC-002 field-by-field. No critical (FAIL-level) findings were identified. Two major findings require correction before or at G3: an invented field in api_contracts.md that is absent from the source DDL, and an unregistered contradiction between source documents regarding ETH/USDT instrument scope. Four minor findings are documented for completeness.

---

## Critical Findings (FAIL-level — must resolve before G3)

**None.**

---

## Major Findings (must address before G3 or document as PENDING)

### FIND-001 — Invented field `fecha_hora` in api_contracts.md

- **Severity:** HIGH
- **Source section:** DOC-002 (CONTEXTO_FISCAL_OPERATIVO.md), Section 3 "Esquema de Base de Datos" — DDL defines columns: `id, fecha_utc, fecha_mxn, activo, accion, cantidad, precio_usdt, monto_usdt, tc_mxn_usd, monto_mxn, comisiones_mxn, costo_acum_mxn, ganancia_mxn, metodo_costo, exchange, order_id`. No column named `fecha_hora` exists.
- **Contract section:** api_contracts.md Section 7.1 "Contrato del Fiscal Ledger — Inserción en trades.db" lists both: `fecha_hora | TEXT | Sí | ISO 8601 UTC — campo canónico (alias: fecha_utc)` AND `fecha_utc | TIMESTAMP | Sí | ...` as separate rows.
- **Description:** The field `fecha_hora` does not appear anywhere in the source DDL (DOC-002). It is not a renamed version of an existing column — the DDL has `fecha_utc` already listed separately in the same table. This field is therefore invented by the Merger without source support. Requirements.md REQ-G-111 correctly describes the DDL without `fecha_hora`, creating an internal contradiction between the two contract files.
- **Required correction:** Remove `fecha_hora` from api_contracts.md Section 7.1. The canonical column is `fecha_utc` (TIMESTAMP NOT NULL) as defined in DOC-002. The api_contracts.md insertion contract must match the DDL in REQ-G-111.

---

### FIND-002 — Unregistered contradiction regarding ETH/USDT instrument scope

- **Severity:** MEDIUM
- **Source sections:**
  - DOC-001 (OWNEW_CONTEXT.md) Section "¿Qué instrumentos y operaciones están permitidos?": "Instrumento autorizado: BTC/USDT"; "Otras criptomonedas, conversiones entre criptoactivos, staking, Earn, airdrops y movimientos adicionales quedan fuera de la validación inicial. No deben incorporarse al alcance por iniciativa de los agentes."
  - DOC-002 (CONTEXTO_FISCAL_OPERATIVO.md) Section 1 "Contexto Fiscal": "Instrumentos: BTC/USDT o ETH/USDT"
  - DOC-003 (AI_INTEGRATION.md) Section "¿Qué instrumentos y temporalidades usa?": "Activo secundario: ETH/USDT"
- **Contract section:** conflict_register.md — no entry for this conflict. Requirements.md REQ-G-001 and REQ-G-005 correctly restrict to BTC/USDT per DOC-001 hierarchy.
- **Description:** DOC-002 and DOC-003 explicitly reference ETH/USDT as a valid or secondary asset. DOC-001 — which per DEC-001/CONF-002 has precedence as the owner's operative mandate — restricts operations to BTC/USDT and requires owner authorization to add other instruments. The merger's decision to restrict to BTC/USDT is hierarchically correct. However, this contradiction between three source documents is not registered in conflict_register.md. For complete transparency and owner awareness (especially because DOC-002's fiscal instrument list could have SAT-reporting implications), this conflict must be formally documented.
- **Required correction:** Add CONF-005 to conflict_register.md documenting: DOC-001 (sole authorized instrument: BTC/USDT) vs. DOC-002 and DOC-003 (also reference ETH/USDT). Confirm in the register that the BTC/USDT restriction in the contract is the authoritative operative decision per CONF-002 resolution hierarchy, and that ETH/USDT remains out of scope for FASE 1 unless owner explicitly authorizes.

---

## Minor Findings (can be addressed post-G3)

### FIND-003 — `MONTHLY_TRADE_LIMIT_LOCK` auto-release at month boundary not supported by source

- **Severity:** LOW
- **Source section:** DOC-005 (RISK_POLICY.md) Section "¿Cuál es el límite de operaciones al mes?": "Al alcanzar ocho operaciones completadas, el sistema bloqueará nuevas entradas durante el periodo." Section "Restablecimiento mensual": "El cambio de mes no deberá interpretarse como una autorización automática para reanudar operaciones. El sistema podrá inicializar una nueva referencia mensual, pero cualquier bloqueo preventivo o de seguridad pendiente deberá resolverse conforme a su mecanismo de revisión. El bloqueo por drawdown requerirá autorización humana para su liberación."
- **Contract section:** data_flow.md Section 6 "Flujo de Bloqueos del Risk Manager": `MonthlyTradeCount = 8 → agrega: MONTHLY_TRADE_LIMIT_LOCK. Liberación automática al inicio del siguiente mes`
- **Description:** DOC-005's "Restablecimiento mensual" section states the month change does not constitute automatic authorization to resume operations, and explicitly names only the drawdown lock as requiring human authorization. The monthly trade count lock releasing at the start of a new period is a reasonable inference (the limit is "during the period") and not prohibited by the source, but it is not explicitly stated. The other contract files (requirements.md REQ-G-022, REQ-G-024) do not make this auto-release claim, creating internal inconsistency between data_flow.md and requirements.md.
- **Required correction:** Align data_flow.md with requirements.md. Either (a) add explicit wording to requirements.md that MONTHLY_TRADE_LIMIT_LOCK resets automatically at month boundary, or (b) change data_flow.md to say "Liberación al inicio del siguiente mes calendario (ver nota: CONF-005 / resolución técnica pendiente)." Requires owner ratification or explicit technical decision.

---

### FIND-004 — REQ-G-115 describes regime 601 as operative framework without leading caveat

- **Severity:** LOW
- **Source section:** DOC-001 (OWNEW_CONTEXT.md) Section "¿Cuál es la situación fiscal y laboral documentada?": "Régimen que aparece en la CSF: 616 — Sin obligaciones fiscales." DOC-002 (CONTEXTO_FISCAL_OPERATIVO.md) Section 1: "Régimen: Sueldos y Salarios (clave 601)." These are distinct tax regimes with different obligations; CONF-003 correctly identifies this as HIGH severity and OPEN.
- **Contract section:** requirements.md REQ-G-115 description begins "Marco fiscal: régimen Sueldos y Salarios (clave 601). La ganancia neta anual de trading se declara bajo la exención del Art. 93 XIX b) LISR..."
- **Description:** The description presents regime 601 and its associated exemption as the operative fiscal framework before flagging the unresolved conflict at the end. A reader encountering this requirement in isolation would see regime 601 as the established framework. While the PENDING note (REQ-G-P08, REQ-G-P09) is present, the unresolved regime contradiction is severity HIGH per CONF-003.
- **Required correction (cosmetic, non-blocking):** Prepend the REQ-G-115 description with an explicit advisory flag such as: "NOTA: Existe un conflicto fiscal no resuelto (CONF-003). El régimen que aparece en la CSF física del propietario es 616 (DOC-001), mientras que DOC-002 opera bajo régimen 601. Los siguientes parámetros provienen de DOC-002 y están marcados PENDING hasta resolución fiscal profesional." This makes the unresolved nature prominent rather than trailing.

---

### FIND-005 — Notation inconsistency: `OpenPositions < 1` in data_flow vs `OpenPositions ≤ 1` (INV-003)

- **Severity:** LOW
- **Source section:** DOC-005 (RISK_POLICY.md) Section "¿Cuáles son los invariantes de riesgo?": "INV-003 — Posición única: `OpenPositions ≤ 1`"
- **Contract section:** data_flow.md Section 1, Phase 5 validation step 7: "7. OpenPositions < 1"
- **Description:** INV-003 defines the invariant as `OpenPositions ≤ 1` (invariant of the system state). The data_flow pre-check for a new entry uses `< 1` (which translates to: must have 0 open positions before opening a new one). These are operationally equivalent in integer context (you cannot have 0.5 positions), but the inconsistent notation could cause confusion during implementation or testing. Requirements.md REQ-G-007 and REQ-G-028 correctly state the invariant as `<= 1`.
- **Required correction:** Change data_flow.md Phase 5 step 7 to: "7. OpenPositions = 0 (ninguna posición abierta ni orden de entrada pendiente)" to unambiguously express the pre-condition for a new entry without introducing a different notation than INV-003.

---

### FIND-006 — `Research & Backtesting` component absent from architecture diagram

- **Severity:** LOW
- **Source section:** DOC-003 (AI_INTEGRATION.md) Section "Componentes no basados en LLM": lists 11 components including "Research & Backtesting: Investigación y evaluación experimental."
- **Contract section:** architecture.md Section 2 diagram (CAPA DE MOTORES DETERMINISTAS) shows: Trading Engine, Market Intelligence, Regime Engine, Strategy Engine, ML Engine, Portfolio Manager, Risk Manager, Execution Engine, Fiscal Ledger, Audit & Governance — 10 components. "Research & Backtesting" is omitted from the visual layer.
- **Description:** The source document lists 11 non-LLM components. The contract's REQ-G-057 correctly lists all 11, but the architecture diagram only shows 10. The omission is non-critical because (a) the diagram represents the Live Trading / production flow per architecture.md's own caveat ("Esta vista representa el flujo lógico"), and (b) Research & Backtesting operates in Research mode, not in the production data path shown. However, the diagram could mislead implementers into omitting this component from the system design.
- **Required correction (cosmetic):** Add "Research & Backtesting" to the architecture diagram as a separate layer or annotate the diagram: "Research & Backtesting opeartes in Research mode (see REQ-G-057)." Ensures the diagram is consistent with REQ-G-057.

---

## Verified Items (independently confirmed accurate against source citations)

The following items were independently verified by reading source documents without relying on Merger reasoning:

1. **All 12 risk invariants (INV-001 through INV-012)** — REQ-G-028 matches DOC-005 (RISK_POLICY.md, Section "¿Cuáles son los invariantes de riesgo?") exactly, with correct formulas, thresholds and descriptions for all 12 invariants.

2. **Position sizing formula** — REQ-G-015 `Q = (RiskBudget - FixedCosts) / ((P_e - P_s) + C_e + C_s + S)` matches DOC-005 Section "¿Cómo se calcula el tamaño de posición? — Fórmula general" exactly, variable by variable.

3. **Equity formula** — REQ-G-012 `Equity_t = Cash_t + MarketValue_t`; `Equity_USDT = USDT_disponible + BTC_total × Precio_BTC`; `Equity_MXN = Equity_USDT × FX_USDT/MXN` matches DOC-005 Section "¿Cómo se define el capital y el equity?" exactly.

4. **Risk budget formula** — REQ-G-013 `RiskBudget_t = Equity_t × 0.015` matches DOC-005 Section "¿Cuál es el presupuesto de riesgo por operación?" with the correct initial example ($3,000 × 0.015 = $45 MXN).

5. **Drawdown formula** — REQ-G-020 `MonthlyDrawdown = (MonthlyBaseline - CurrentEquity) / MonthlyBaseline × 100` with 5% limit matches DOC-005 Section "¿Cómo funciona el drawdown mensual?" including the explicit note that 5% substitutes any prior reference to 6%.

6. **trades.db DDL schema (REQ-G-111)** — All 16 columns (id, fecha_utc, fecha_mxn, activo, accion, cantidad, precio_usdt, monto_usdt, tc_mxn_usd, monto_mxn, comisiones_mxn, costo_acum_mxn, ganancia_mxn, metodo_costo, exchange, order_id) with correct types, constraints and defaults match DOC-002 Section 3 "Esquema de Base de Datos" field for field. The 3 indexes (idx_fecha on fecha_mxn, idx_activo on activo, idx_accion on accion) are correctly identified.

7. **5 AI agents** — Market Analyst, Macro Analyst, Strategy Analyst, Risk Analyst, Decision Synthesis — with correct responsibilities, restrictions and output contracts in REQ-G-052 through REQ-G-056 match DOC-003 Section "¿Cómo se organizan agentes y motores?" exactly.

8. **11 non-LLM components** (REQ-G-057) — Trading Engine, Market Intelligence, Regime Engine, Strategy Engine, ML Engine, Portfolio Manager, Risk Manager, Execution Engine, Fiscal Ledger, Research & Backtesting, Audit & Governance — match DOC-003 Section "Componentes no basados en LLM" exactly.

9. **Absolute prohibitions** — REQ-G-006 (no futures, no margin, no leverage, no short, no copy trading, no borrowed capital), REQ-G-008 (no averaging down), REQ-G-040/REQ-G-043 (no auto-authorization, no self-approval), REQ-G-011 (no WeirdCow capital, no borrowed capital) — all present and correctly cited to DOC-001 and DOC-005.

10. **8 Risk Manager states** — ACTIVE, POSITION_OPEN, LOSS_STREAK_LOCK, MONTHLY_DRAWDOWN_LOCK, MONTHLY_TRADE_LIMIT_LOCK, DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW — REQ-G-024 matches DOC-005 Section "¿En qué estados puede estar el Risk Manager?" exactly, including the coexistence rule.

11. **3-loss streak rule** — REQ-G-023 matches DOC-005 Section "¿Qué pasa tras tres pérdidas seguidas?" including: net realized result after commissions defines a loss, counter resets on net positive, zero result neither increments nor resets the counter, and 4-step human review required for liberation.

12. **Stop modification constraint** — REQ-G-027 `P_stop_nuevo >= P_stop_inicial` for Long positions matches DOC-005 Section "¿Se puede modificar el stop después de entrar?" exactly, including the prohibition on moving stop down and the slippage exception.

13. **Drawdown action sequence** — REQ-G-022 5-step sequence (suspend new operations, cancel pending entry orders, maintain exit mechanisms, register blocking event, request human authorization) matches DOC-001 Section "¿Qué ocurre con el drawdown mensual?" and DOC-005 Section "Condición de bloqueo" exactly.

14. **Fiscal obligations** — REQ-G-114 identifies all 10 SAT-critical fields from DOC-002 Section 4 "Campos Críticos (auditoría SAT)" correctly. The penalty range ($2,050–$25,360 MXN for non-declaration) matches DOC-002 Section 6 Note 1.

15. **Registered conflicts** — CONF-001 (TRACEABILITY_MATRIX dual-state), CONF-002 (BORRADOR parameters operative status), CONF-003 (regime 616 vs 601), CONF-004 (1–2% vs 1.5% risk limit) are all correctly identified, documented and handled in the contract and conflict_register.md.

16. **16 events catalog** — REQ-G-063 lists ANALYSIS_REQUESTED, MARKET_ANALYSIS_COMPLETED, MACRO_ANALYSIS_COMPLETED, ML_INFERENCE_COMPLETED, REGIME_CLASSIFIED, STRATEGY_CANDIDATE, DECISION_SYNTHESIS_COMPLETED, TRADE_PROPOSAL, RISK_APPROVED, RISK_REJECTED, RISK_REQUIRES_REVIEW, ORDER_SUBMITTED, ORDER_PARTIALLY_FILLED, ORDER_FILLED, ORDER_CANCELLED, ORDER_REJECTED — matching DOC-003 Section "Catálogo de eventos principales" exactly.

17. **PENDING discipline** — Reviewed 10 PENDING parameters (REQ-G-P01 through REQ-G-P10). All are genuinely unresolvable from source documents: each is explicitly marked "Por definir" in DOC-005, "No consultada" in DOC-001, or is a live-data parameter (Binance fees, BCI FX rate) that cannot be pre-determined. No convenience PENDING detected.

18. **Architectural authority table** — Architecture.md Section 6 "Separación de Responsabilidades" matches DOC-003 Section "¿Quién tiene autoridad sobre qué?" and DOC-004 Section "¿Quién decide qué en la arquitectura de riesgo?" including correct assignment of deterministic authority to Risk Manager and human authority for capital.

---

## Recommendation

**PROCEED TO G3 WITH CONDITIONS**

The contract is substantively correct and ready for human review. Before G3 sign-off, the following must be addressed:

**Required before G3 sign-off:**
1. **FIND-001 (HIGH):** Remove the invented `fecha_hora` field from api_contracts.md Section 7.1. The insertion contract must match the DDL in REQ-G-111.
2. **FIND-002 (MEDIUM):** Add CONF-005 to conflict_register.md documenting the ETH/USDT instrument scope contradiction between DOC-001, DOC-002 and DOC-003, and confirm the BTC/USDT restriction as the authoritative operative decision.

**Can be addressed at G3 or immediately post-G3:**
3. **FIND-003 (LOW):** Explicitly document the MONTHLY_TRADE_LIMIT_LOCK reset behavior and obtain owner ratification or technical decision.
4. **FIND-004 (LOW):** Add unresolved-conflict caveat to REQ-G-115 description.
5. **FIND-005 (LOW):** Normalize `OpenPositions < 1` notation in data_flow.md.
6. **FIND-006 (LOW):** Add Research & Backtesting to the architecture diagram.

The contract may proceed to human review (G3) with FIND-001 and FIND-002 addressed. No critical blocking issue was identified that would prevent G3.
