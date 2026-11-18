# progress.md — SwingPilot Engineering Harness

> **REGLA:** Este archivo es append-only. No se borran entradas anteriores.
> Formato de entrada: fecha | fase | actividad | resultado | archivos afectados

---

## 2026-11-13 | FASE 0 | Bootstrap del Harness | COMPLETADO

**Actividad:** Construcción de la infraestructura del Harness Engineering.

**Resultado:** Estructura completa creada. Todos los archivos requeridos por FASE 0 existen y los scripts de validación han sido ejecutados satisfactoriamente.

**Archivos creados:**
- `AGENTS.md`
- `README.md`
- `feature_list.json`
- `progress.md` (este archivo)
- `session-handoff.md`
- `init.sh`
- `harness/README.md`
- `harness/manifest.json`
- `harness/extraction/README.md`
- `harness/extraction/schemas/extraction.schema.json`
- `harness/extraction/outputs/.gitkeep`
- `harness/merge/README.md`
- `harness/verification/README.md`
- `harness/verification/verification.schema.json`
- `harness/gates/README.md`
- `harness/gates/gate_status.json`
- `harness/change_requests/.gitkeep`
- `docs/README.md`
- `docs/context/README.md`
- `docs/decisions/README.md`
- `docs/policies/README.md`
- `implementation/README.md`
- `implementation/requirements.md`
- `implementation/architecture.md`
- `implementation/api_contracts.md`
- `implementation/data_flow.md`
- `implementation/test_plan.md`
- `implementation/conflict_register.md`
- `scripts/validate_manifest.py`
- `scripts/validate_requirements.py`
- `scripts/validate_gates.py`
- `tests/README.md`
- `tests/unit/.gitkeep`
- `tests/integration/.gitkeep`
- `tests/acceptance/.gitkeep`
- `tests/regression/.gitkeep`
- `tests/security/.gitkeep`
- `release/README.md`
- `src/` (directorio vacío)

**Scripts ejecutados:** `validate_manifest.py`, `validate_requirements.py`, `validate_gates.py`, `init.sh`

**Estado de gates:** Todos inicializados en PENDING.

**Código funcional de SwingPilot creado:** NINGUNO (correcto para FASE 0).

**Decisión humana registrada:** Documento SWINGPILOT_ENGINEER.md autoriza FASE 0 exclusivamente.

**Próxima acción autorizada:** Esperar incorporación de documentación original en `docs/context/` y autorización explícita "AUTORIZO INICIO DE FASE 1".

---

## 2026-11-13 | FASE 1 — G0 | Integridad y registro documental | PASS

**Actividad:** Inventario y verificación SHA-256 de los 6 documentos fuente depositados por el propietario.

**Resultado:** G0=PASS. 6 documentos registrados con SHA-256 verificados. Conflictos CONF-001 y CONF-002 detectados, registrados y resueltos en `implementation/conflict_register.md`. Estado de CONF-003 (régimen fiscal) escalado al propietario.

**Archivos actualizados:**
- `harness/manifest.json` (v0.2.0 → v0.3.0: status G1_PASS_EXTRACTION_COMPLETE)
- `harness/gates/gate_status.json` (G0=PASS, G1=PASS)
- `implementation/conflict_register.md` (CONF-001 y CONF-002 resueltos, CONF-003 abierto)

---

## 2026-11-13 | FASE 1 — G1 | Extracción independiente | PASS

**Actividad:** Extracción de requisitos de los 6 documentos fuente por extractores aislados.

**Resultado:** G1=PASS. 6 extractores completados. 224 requisitos únicos extraídos en 6 archivos JSON. validate_requirements.py=OK. validate_manifest.py=OK. validate_gates.py=OK.

**Resumen de extracción:**
- DOC-001 (OWNEW_CONTEXT.md): 22 requisitos
- DOC-002 (CONTEXTO_FISCAL_OPERATIVO.md): 15 requisitos
- DOC-003 (AI_INTEGRATION.md): 75 requisitos
- DOC-004 (PROFILE_AND_OPERATIONAL_POLICIES.md): 38 requisitos
- DOC-005 (RISK_POLICY.md): 42 requisitos
- DOC-006 (TRACEABILITY_MATRIX.md): 32 requisitos
- **Total: 224 requisitos**

**Conflictos inter-documentales detectados durante extracción:**
- CONF-003: Régimen fiscal — DOC-001 indica 616, DOC-002 indica 601. OPEN — escalado al propietario.

**Archivos creados:**
- `harness/extraction/outputs/DOC-001.json`
- `harness/extraction/outputs/DOC-002.json`
- `harness/extraction/outputs/DOC-003.json`
- `harness/extraction/outputs/DOC-004.json`
- `harness/extraction/outputs/DOC-005.json`
- `harness/extraction/outputs/DOC-006.json`

**Código funcional de SwingPilot creado:** NINGUNO (correcto para FASE 1 extracción).

**Próxima acción:** Merger — integración de los 224 requisitos extraídos en el contrato técnico (implementation/*.md). Precede a G2 y G3.

---

## 2026-11-13 | FASE 1 — Merger | Integración del contrato técnico | COMPLETADO

**Actividad:** El Merger consolidó los 224 requisitos de 6 extractores en documentos de contrato técnico.

**Resultado:** 5 documentos de contrato producidos en `implementation/`. 15 módulos funcionales. 25 parámetros PENDING registrados. CONF-003 (fiscal) OPEN — escalado al propietario.

**Resumen de requisitos integrados:** 153 requisitos globales REQ-G-NNN de 15 módulos:
- Módulo 1-2: Perfil operativo, capital y position sizing (REQ-G-001..016)
- Módulo 3-4: Risk Manager, estados y autorización humana (REQ-G-020..045)
- Módulo 5-7: Arquitectura de IA, mensajes y flujo de decisión (REQ-G-050..076)
- Módulo 8-9: Modos operativos e integración tecnológica (REQ-G-080..094)
- Módulo 10: Framework de investigación cuantitativa y ML (REQ-G-100..108)
- Módulo 11: Fiscal Ledger / trades.db (REQ-G-110..115)
- Módulo 12-13: Trazabilidad y seguridad (REQ-G-120..132)
- Módulo 14-15: Requisitos no funcionales y parámetros PENDING (REQ-G-140..142, REQ-G-P01..P25)

**Archivos producidos:**
- `implementation/requirements.md` (contrato de requisitos — 153 REQ-G-NNN)
- `implementation/architecture.md` (contrato de arquitectura)
- `implementation/api_contracts.md` (contratos de mensajes y eventos)
- `implementation/data_flow.md` (flujo de decisión 7 fases)
- `implementation/test_plan.md` (plan de verificación — 16 criterios de aceptación globales)

**Código funcional de SwingPilot creado:** NINGUNO (correcto para FASE 1 Merger).

**Próxima acción:** Verifier adversarial — auditoría del contrato técnico contra documentos originales. Produce reporte de verificación para G2.

---

## 2026-11-13 | FASE 1 — G2 | Verificación adversarial del contrato técnico | PASS

**Actividad:** Dos verificaciones adversariales independientes del contrato técnico contra los 6 documentos fuente originales.

**Resultado:** G2=PASS. VER-001.json (primera verificación, sesión anterior): PASS 10/10. VERIFICATION_G2_REPORT.md (segunda verificación adversarial, esta sesión): PASS_WITH_FINDINGS — 0 hallazgos críticos, 6 hallazgos aplicados.

**Hallazgos aplicados:**
- FIND-001 (HIGH): `fecha_hora` inventada eliminada de api_contracts.md Sección 7.1 — no existe en DDL de DOC-002.
- FIND-002 (MEDIUM): CONF-005 (ETH/USDT vs BTC/USDT) registrado en conflict_register.md — contradicción entre DOC-001, DOC-002 y DOC-003.
- FIND-003 (LOW): MONTHLY_TRADE_LIMIT_LOCK en data_flow.md marcado como PENDING ratificación (auto-liberación mensual no explícita en DOC-005).
- FIND-004 (LOW): REQ-G-115 ya tenía advertencia de CONF-003 prominente — sin cambios necesarios.
- FIND-005 (LOW): `OpenPositions < 1` corregido a `OpenPositions = 0` en data_flow.md.
- FIND-006 (LOW): Research & Backtesting agregado al diagrama de architecture.md.

**18 ítems críticos verificados independientemente:** 12 invariantes INV-001..012, 4 fórmulas (position sizing, equity, risk budget, drawdown), DDL trades.db (16 columnas), 5 agentes IA, 11 componentes no-LLM, 8 estados Risk Manager, 16 eventos, prohibiciones absolutas.

**Archivos actualizados:** api_contracts.md, data_flow.md, architecture.md, conflict_register.md (CONF-005), harness/verification/VERIFICATION_G2_REPORT.md, harness/gates/gate_status.json (G2=PASS), harness/manifest.json (v0.4.0).

**Código funcional de SwingPilot creado:** NINGUNO (correcto para FASE 1 Verificación).

**Estado actual de gates:** G0=PASS, G1=PASS, G2=PASS, G3=PENDING (requiere aprobación humana), G4-G7=PENDING.

**Próxima acción requerida:** G3 — Aprobación humana del contrato técnico por el propietario. BLOQUEANTE: solo el propietario puede autorizar G3. Ver paquete G3 a continuación.

---

## 2026-11-13 | FASE 1 — G2 | Verificación adversarial del contrato | PASS

**Actividad:** Verificador adversarial independiente auditó el contrato técnico (5 documentos + 6 extraction outputs) contra los 10 checks del esquema de verificación.

**Resultado:** G2=PASS. VER-001.json producido. 10/10 checks pasados. 2 findings LOW no bloqueantes documentados.

**Hallazgos:**
- FIND-001 (LOW, RESUELTO): Extracciones parciales — DOC-001 (22 reqs), DOC-002 (15), DOC-004 (38), DOC-005 (42). No bloquea G3. Requisitos críticos (riesgo, IA, trazabilidad) están completos.
- FIND-002 (LOW, ABIERTO): 12 parámetros técnicos PENDING — se resuelven en FASE 2 (comisión Binance, stepSize, FX, slippage, Telegram, umbrales ML, etc.).

**Verificación automática:**
- 160 referencias REQ-XXXX en requirements.md → 100% válidas
- 12/12 invariantes INV-001..INV-012 presentes
- 8/8 estados del Risk Manager presentes
- 16/16 criterios AC del sistema (DOC-003)
- 16/16 criterios RM del Risk Manager (DOC-005)
- Comportamiento Fail-Closed (INV-012) en data_flow.md
- CONF-001, CONF-002 resueltos
- 20 items PENDING explícitamente marcados

**Archivos producidos:**
- `harness/verification/VER-001.json` (reporte de verificación adversarial)
- `harness/gates/gate_status.json` (G2=PASS)
- `harness/manifest.json` (todos los documentos: VERIFIED)

**Código funcional de SwingPilot creado:** NINGUNO (correcto para FASE 1 verificación).

**Próxima acción requerida: G3 — Aprobación humana del contrato técnico.**
- G3 requiere aprobación humana EXPLÍCITA del propietario.
- El propietario debe revisar implementation/*.md y confirmar con "APRUEBO EL CONTRATO TÉCNICO v1.0" o similar.
- G3 NO puede ser aprobado por ningún agente.

---

## 2026-11-13 | FASE 1 — Re-verificación adversarial | PASS

**Actividad:** Sesión de continuación — re-ejecución del Merger (5 documentos de contrato producidos desde cero) y verificación adversarial adicional post-reconstitución del contexto.

**Hallazgos del Verificador adversarial (VER-001-v2):**
- FIND-001 (HIGH → RESUELTO): REQ-G-115 no marcaba régimen fiscal como PENDING/CONDICIONAL a pesar de CONF-003 OPEN y mandato DEC-001. Corregido: REQ-G-115 ahora incluye cláusula CONDICIONAL, referencia a CONF-003, y restricción de implementación del Fiscal Ledger configurable.
- FIND-002 (MEDIUM → RESUELTO): test_plan.md no cubría AC-06..AC-16. Corregido: AC-06..AC-16 marcados PENDING con proceso definido en Sección 9.
- FIND-003 (MEDIUM → RESUELTO): REQ-G-030 solo decía "ver REQ-5047" sin listar los 16 criterios del RM. Corregido: lista reconstructiva de 16 criterios incluida en REQ-G-030.
- FIND-004 (LOW → RESUELTO): Fases de implementación sin REQ-G-NNN. Corregido: architecture.md nota explícita de asignación requerida antes de FASE 2.
- FIND-005 (LOW → RESUELTO): api_contracts.md sin cross-reference a REQ-G-112/113. Corregido: referencia añadida en Sección 7.1.

**Conflictos OPEN que requieren confirmación del propietario en G3:**
- CONF-003: CSF régimen 616 vs CONTEXTO_FISCAL_OPERATIVO régimen 601 — pendiente validación fiscal profesional
- CONF-004: DOC-003 riesgo "1-2%" vs DOC-001/DOC-005 límite "1.5%" — pendiente confirmación de que 1.5% es el límite vinculante definitivo

**Archivos producidos/modificados:**
- `implementation/requirements.md` (re-producido completo + corrección FIND-001/003)
- `implementation/architecture.md` (re-producido + corrección FIND-004)
- `implementation/api_contracts.md` (re-producido + corrección FIND-005)
- `implementation/data_flow.md` (re-producido)
- `implementation/test_plan.md` (re-producido + corrección FIND-002)
- `implementation/conflict_register.md` (CONF-004 añadido)
- `harness/verification/verification_report_v1.json` (VER-001-v2: PASS, 5 findings resueltos)

**Estado del sistema:** G0=PASS, G1=PASS, G2=PASS. Esperando G3 — aprobación humana del propietario.

---

## 2026-11-15 | FASE 1 | Resolución de CONF-003, CONF-004, CONF-005 | COMPLETADO

**Actividad:** El propietario resolvió los tres conflictos abiertos (registrado en DEC-002). Régimen fiscal 616; riesgo 1.5% máximo vinculante; BTC/USDT único par (ETH/USDT eliminado).

**Resultado:** Los 5 conflictos (CONF-001..005) están RESUELTOS. El tratamiento fiscal de las ganancias sigue PENDING (REQ-G-P08). G3 sigue PENDING: DEC-002 no es aprobación del contrato.

**Archivos:** `docs/decisions/DEC-002_resolucion-conf-003-004-005.md` (nuevo), `harness/change_requests/CR-001_correcciones-documentos-originales.md` (nuevo, propuesta pendiente de aprobación; los documentos originales NO se modificaron), `implementation/conflict_register.md`, `implementation/requirements.md`.

**Notas de sesión:** el extractor DOC-003 fue detenido (TaskStop) al terminar el Merger oficial para evitar sobrescritura de salidas ya validadas; DOC-003.json (75 req) validado por validate_requirements.py.

**Código funcional creado:** NINGUNO.

**Próxima acción:** G3 — aprobación humana explícita del contrato técnico; aprobar o rechazar CR-001.

---

## 2026-11-16 | FASE 1 | DEC-003: régimen fiscal 605 | COMPLETADO

**Actividad:** Por instrucción expresa del propietario se fijó el régimen 605 y se retiró cualquier otro régimen de documentos originales, extracciones, contrato y decisiones. Fecha de regularización dada por el propietario: 17/11/2026.

**Archivos:** `docs/decisions/DEC-003_regimen-fiscal-605.md` (nuevo), `docs/context/OWNEW_CONTEXT.md` y `docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md` (solo referencias al régimen), `harness/manifest.json` (SHA-256 de esos dos), `harness/extraction/outputs/DOC-001.json`, `DOC-002.json`, `implementation/requirements.md`, `implementation/conflict_register.md`, DEC-001, DEC-002, CR-001, `session-handoff.md`.

**Estado:** G3 sigue PENDING. Código funcional creado: NINGUNO.

**Corrección (2026-11-16):** la entrada anterior dice "regularización"; el propietario aclaró que el cambio a 605 se hará el 17/11/2026 (programado, aún no realizado). Textos actualizados a "programado"; SHA-256 de OWNEW_CONTEXT.md recalculado.

---

## 2026-11-17 | FASE 1 | CR-001 aprobada; historial fiscal | COMPLETADO

**Actividad:** El propietario aprobó CR-001. Se aplicó: eliminación de "1–2%" y ETH/USDT en AI_INTEGRATION.md y CONTEXTO_FISCAL_OPERATIVO.md; fila de versión 1.0 de TRACEABILITY_MATRIX.md corregida a BORRADOR. Historial fiscal registrado: 616 del 29/06/2021 al 12/10/2025; 605 desde el 13/10/2025.

**Pendiente:** la fecha del cambio a 605 (13/10/2025 según la instrucción más reciente; 17/11/2026 según una anterior).

**Archivos:** docs/policies/AI_INTEGRATION.md, docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md, docs/policies/TRACEABILITY_MATRIX.md, docs/context/OWNEW_CONTEXT.md, harness/manifest.json (SHA-256), harness/change_requests/CR-001, docs/decisions/DEC-003, implementation/requirements.md, implementation/conflict_register.md, harness/extraction/outputs/DOC-001.json, session-handoff.md.

**Estado:** G3 sigue PENDING (el propietario no lo aprobó).

**Corrección (2026-11-17):** el 605 debía tener efecto desde el 13/10/2025, pero el aviso de cambio de régimen ante el SAT se presentó el 17/11/2026. Se registran ambas fechas. Entre ambas, el registro ante el SAT figura en 616; la implicación fiscal queda pendiente de validación con contador (REQ-G-P08). Ver DEC-003.

---

## 2026-11-17 | FASE 1 | Cierre de fecha fiscal; diferimiento de validación con contador | COMPLETADO

**Actividad:** El propietario confirmó el historial fiscal: régimen 616 cerrado el 12/10/2025; el 605 debió iniciar el 13/10/2025; el aviso ante el SAT se presentó el 17/11/2026 por falta de regularización a tiempo. Queda cerrado el pendiente "fecha del cambio a 605" de la entrada anterior.

**Decisiones del propietario:** (1) la validación con contador (REQ-G-P08) se difiere para después; (2) G3 se mantiene PENDING.

**Archivos:** `session-handoff.md`.

**Estado:** G3 PENDING. Código funcional creado: NINGUNO.

**Próxima acción:** G3 cuando el propietario decida; validación fiscal con contador diferida (bloquea cualquier cálculo fiscal, no G3).

---

## 2026-11-17 | FASE 1 | Validación técnica bloque 1 (DEC-004) | COMPLETADO

**Actividad:** Sesión de validación técnica con el propietario. Resueltos P01–P06, P19 y P20 (FX Binance, antigüedad 5 min, comisión real con piso 0.10%, slippage 0.10%, filtros dinámicos, Telegram, reconciliación, tolerancia 0.5%).

**Archivos:** `docs/decisions/DEC-004_parametros-tecnicos-bloque-1.md` (nuevo), `implementation/requirements.md` (tabla Módulo 15), `session-handoff.md`.

**Pendiente:** bloque 2 (P07, P10–P18, P21–P25); P08 diferido (contador). G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-17 | FASE 1 | Validación técnica bloque 2 (DEC-005) | COMPLETADO

**Actividad:** Resueltos P10–P17 y P21–P24 (división 50/20/15/15, muestra mínima, umbrales PF 1.3 / expectancy 0.10R / DD 20% / Sharpe 0.8, Walk-Forward 24/6/6, requisitos estadísticos, ciclo de vida de modelos, límites RM). Criterios congelados antes de cualquier experimento.

**Archivos:** `docs/decisions/DEC-005_parametros-investigacion-ml-bloque-2.md` (nuevo), `implementation/requirements.md` (Módulo 15), `session-handoff.md`.

**Pendiente:** bloque 3 (P07, P18, P25, recuperación ante fallos); P08 diferido. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-17 | FASE 1 | Validación técnica bloque 3 (DEC-006) y CR-002 | COMPLETADO

**Actividad:** Resueltos P07 (API SIE de Banxico), P18 (tope de $5 USD/mes en API de IA, timeouts, sin SLA 24/7), P25 (matriz de trazabilidad en JSON) y nuevo P26 (recuperación ante fallos en modo seguro con confirmación humana). Detectado hueco: el stop-loss solo vive en software; propuesto CR-002 para colocarlo también en Binance.

**Archivos:** `docs/decisions/DEC-006_parametros-operativos-bloque-3.md` (nuevo), `harness/change_requests/CR-002_stop-loss-en-exchange.md` (nuevo, PROPUESTA), `implementation/requirements.md` (Módulo 15, P26 añadido), `session-handoff.md`.

**Estado:** todos los parámetros PENDING resueltos salvo P08 (diferido). CR-002 pendiente de aprobación. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-17 | FASE 1 | CR-002 aprobada y aplicada; cierre de sesión | COMPLETADO

**Actividad:** El propietario aprobó CR-002 ("APRUEBO CR-002"). Aplicada en el contrato: REQ-G-031 (stop-loss en Binance, Fail-Closed si falla), `data_flow.md` §2, eventos STOP_ORDER_PLACED / STOP_ORDER_REPLACED / STOP_ORDER_FAILED en `api_contracts.md`, pruebas TC-STOP-001..006 en `test_plan.md`.

**Aclaración registrada:** en DEC-005 la justificación de P24 omitió que INV-011 (LOSS_STREAK_LOCK) y la no liberación automática del bloqueo mensual (REQ-G-030 criterio 9) ya existen; la adición de P24 es probablemente redundante. Pendiente confirmación del propietario.

**Archivos:** `implementation/requirements.md`, `implementation/data_flow.md`, `implementation/api_contracts.md`, `implementation/test_plan.md`, `harness/change_requests/CR-002_stop-loss-en-exchange.md`, `docs/decisions/DEC-005_parametros-investigacion-ml-bloque-2.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `validate_requirements.py`, `validate_manifest.py`, `validate_gates.py`.

**Bloqueos:** G3 PENDING (decisión del propietario). P08 diferido. Cambios sin commit.

**Siguiente acción autorizada:** esperar decisión del propietario sobre G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-003 propuesto (feedback externo, puntos A–C) | PROPUESTA

**Actividad:** Revisión de un feedback externo contra el contrato. El propietario aceptó incluir A (persistencia y reinicio), B (seguridad explícita de credenciales) y C (solo velas cerradas). Redactado CR-003. D (heartbeat), E (ubicación de Strategy/Risk Analyst) y F (reintentos) quedan para después.

**Archivos:** `harness/change_requests/CR-003_persistencia-seguridad-velas-cerradas.md` (nuevo).

**Estado:** CR-003 pendiente de aprobación formal; contrato sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-003 aprobada y aplicada | COMPLETADO

**Actividad:** El propietario aprobó CR-003 ("APRUEBO CR-003"). Aplicado: REQ-G-032 (persistir antes de actuar, invalidar autorizaciones no enviadas al reiniciar, identificador de cliente idempotente), REQ-G-033 (seguridad del bot de Telegram), REQ-G-070 (solo velas cerradas), REQ-G-093 (clave Binance sin retiro, restricción por IP, verificación al arrancar). 3 eventos nuevos y 8 pruebas nuevas.

**Archivos:** `implementation/requirements.md`, `implementation/data_flow.md`, `implementation/api_contracts.md`, `implementation/test_plan.md`, `harness/change_requests/CR-003_persistencia-seguridad-velas-cerradas.md`.

**Pruebas ejecutadas:** validate_requirements.py, validate_manifest.py, validate_gates.py.

**Pendiente:** puntos D (heartbeat externo), E (ubicación de Strategy/Risk Analyst), F (reintentos) del feedback; aclaración de P24 (DEC-005). G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | DEC-007 registrada; CR-004 propuesto | PROPUESTA

**Actividad:** Sesión técnica sobre los puntos D, E y F del feedback. Decisiones (DEC-007): Q18 C (vigilante en la segunda máquina del propietario), Q19 B (filtro determinista antes de LLM), Q20 B (1 reintento), Q21 A (fallo de agente = ciclo sin propuesta), Q22 A (laptop en casa con no-break, configuración y uso dedicado). Redactado CR-004 con los cambios al contrato; incluye un ajuste respecto a lo presentado en sesión (Risk Manager antes que Risk Analyst).

**Archivos:** `docs/decisions/DEC-007_monitoreo-reintentos-hosting.md` (nuevo), `harness/change_requests/CR-004_reordenamiento-flujo-monitoreo-hosting.md` (nuevo).

**Estado:** CR-004 pendiente de aprobación formal; contrato sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | Corrección de DEC-007 y CR-004 (asignación de máquinas) | COMPLETADO

**Actividad:** El propietario distinguió Laptop A (actual, potente, se apaga) y Laptop B (antigua, encendida siempre). Asignación: SwingPilot en producción en Laptop B; desarrollo, investigación y backtesting en Laptop A. Como ninguna máquina distinta de Laptop B queda encendida 24/7, Q18 pasa de C a B (servicio externo de vigilancia).

**Archivos:** `docs/decisions/DEC-007_monitoreo-reintentos-hosting.md`, `harness/change_requests/CR-004_reordenamiento-flujo-monitoreo-hosting.md`.

**Estado:** CR-004 pendiente de aprobación. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-004 aprobada y aplicada | COMPLETADO

**Actividad:** El propietario aprobó CR-004 ("APRUEBO CR-004"). Aplicado: flujo reordenado (Fase 2 filtro determinista con NO_SETUP sin LLM; Fase 3 Market/Macro/Strategy Analyst en paralelo; Fase 4 Synthesis sin Risk Analyst; Risk Analyst tras RISK_APPROVED y visible en Telegram); rol del ML Engine explícito; REQ-G-034 (reintentos y fallo de agentes), REQ-G-035 (latido a servicio externo y reinicio automático en Laptop B), REQ-G-036 (verificación de IP pública). 4 eventos y 9 pruebas nuevas.

**Archivos:** `implementation/data_flow.md`, `implementation/requirements.md`, `implementation/architecture.md`, `implementation/api_contracts.md`, `implementation/test_plan.md`, `harness/change_requests/CR-004_reordenamiento-flujo-monitoreo-hosting.md`.

**Pruebas ejecutadas:** validate_requirements.py, validate_manifest.py, validate_gates.py.

**Pendiente:** aclaración de P24 (DEC-005); P08 diferido. Los puntos A–F del feedback externo quedan atendidos. G3 PENDING. Cambios sin commit. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | P24 ajustado; cierre de sesión | COMPLETADO

**Actividad:** El propietario retiró la adición de P24 por redundante (INV-011 y REQ-G-030 criterio 9 ya la cubren). P24 queda como "ninguno adicional". P08 sigue diferido. G3 se mantiene PENDING por decisión del propietario.

**Archivos:** `docs/decisions/DEC-005_parametros-investigacion-ml-bloque-2.md`, `implementation/requirements.md` (fila P24), `session-handoff.md`.

**Pruebas ejecutadas:** validate_requirements.py, validate_manifest.py, validate_gates.py.

**Bloqueos:** G3 PENDING; P08 diferido; cambios sin commit.

**Siguiente acción autorizada:** esperar decisión del propietario sobre G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | DEC-008 registrada; CR-005 propuesto | PROPUESTA

**Actividad:** Revisión de un documento externo de feedback (`error-handling.md`, manejo de fallos y recuperación) contra el contrato. Aporta la máquina de estados de la operación y la recuperación por estado; contradice en 10 puntos lo aprobado (el más grave: reintentaba ejecución desde RISK_APPROVED sin autorización humana, INV-008). Decisiones del propietario (DEC-008): Q23 A (máquina de estados en el contrato), Q24 vigencia de autorización 30 min, Q25 A (cierre protector a mercado si el precio cruzó el stop sin orden protectora). Redactado CR-005 con los cambios al contrato y la lista de puntos no adoptados.

**Archivos:** `docs/decisions/DEC-008_estados-operacion-vigencia-cierre-protector.md` (nuevo), `harness/change_requests/CR-005_estados-operacion-recuperacion.md` (nuevo), `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Estado:** CR-005 pendiente de aprobación formal; contrato sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-005 aprobada y aplicada | COMPLETADO

**Actividad:** El propietario aprobó CR-005 ("APRUEBO CR-005"). Aplicado: REQ-G-037 (máquina de estados de la operación, 14 estados, sin estado ERROR genérico), REQ-G-038 (recuperación por estado al arrancar en modo seguro), REQ-G-039 (vigencia de autorización de 30 min con hora del backend), REQ-G-031 ampliado con el cierre protector. 3 eventos y 13 pruebas nuevas.

**Archivos:** `implementation/requirements.md`, `implementation/data_flow.md`, `implementation/api_contracts.md`, `implementation/architecture.md`, `implementation/test_plan.md`, `harness/change_requests/CR-005_estados-operacion-recuperacion.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Bloqueos:** G3 PENDING (decisión del propietario); P08 diferido; cambios sin commit.

**Siguiente acción autorizada:** esperar decisión del propietario sobre G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | DEC-009 registrada; CR-006 propuesto | PROPUESTA

**Actividad:** Validación de la integración con la API de Claude (precios, caché, salida estructurada, opciones multi-agente) contra la referencia oficial. Decisiones (DEC-009): Q26 B (Haiku 5.5 en Market/Macro/Strategy/Risk Analyst, Sonnet 5.5 en Decision Synthesis; ~$0.03 por ciclo con setup), Q27 (Messages API orquestada por código, sin herramientas, salida estructurada, sin prompt caching, reintentos del SDK alineados con REQ-G-034, límite en consola como respaldo). Redactado CR-006, que además propone no llamar a la IA con posición abierta o bloqueo de entradas activo, y aviso al 80% del tope.

**Archivos:** `docs/decisions/DEC-009_modelos-orquestacion-ia.md` (nuevo), `harness/change_requests/CR-006_modelos-orquestacion-costo-ia.md` (nuevo), `session-handoff.md`. Fuera del repo: memoria de reglas de sub-agentes de construcción corregida (TTL 1 h solo con huecos de 5–60 min; lectura de caché 0.05× en Sonnet/Opus 5.5; prefijo mínimo 512 tokens).

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py.

**Estado:** CR-006 pendiente de aprobación formal; contrato sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-006 aprobada y aplicada | COMPLETADO

**Actividad:** El propietario aprobó CR-006 ("APRUEBO CR-006"). Aplicado: REQ-G-095 (Haiku 5.5 en Market/Macro/Strategy/Risk Analyst, Sonnet 5.5 en Decision Synthesis; Messages API sin herramientas; salida estructurada validada; rechazo = fallo; sin caching), REQ-G-096 (tope, aviso al 80%, sin llamadas a LLM con posición abierta o bloqueo de entradas, límite en consola, registro de uso), REQ-G-034 (reintentos del SDK alineados). 1 evento y 7 pruebas nuevas.

**Archivos:** `implementation/requirements.md`, `implementation/data_flow.md`, `implementation/architecture.md`, `implementation/api_contracts.md`, `implementation/test_plan.md`, `harness/change_requests/CR-006_modelos-orquestacion-costo-ia.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Bloqueos:** G3 PENDING (decisión del propietario); P08 diferido; DEC-009 y CR-006 sin commit.

**Siguiente acción autorizada:** esperar decisión del propietario sobre G3. Código funcional creado: NINGUNO.
