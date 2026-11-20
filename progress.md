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

---

## 2026-11-18 | FASE 1 | Paquete de revisión de G3 | COMPLETADO

**Actividad:** Resumen del contrato técnico para la decisión de G3, con revisión de consistencia. Hallazgos: H1 (alta) los cambios de CR-001..006 no han pasado por verificación adversarial independiente (G2 es del 2026-11-13); H2 AC-03 contradice REQ-G-034/DEC-007; H3 REQ-G-063 cita 16 eventos (hay 31); H4 encabezados v0.1/DRAFT y "245 requisitos" (son 224); H5 notas PENDING ya resueltas dentro de requisitos; H6 AC-06..16 sin casos de prueba. Opciones presentadas: A (CR-007 + re-verificación + G3, recomendada), B (CR-007 + G3), C (G3 ahora).

**Archivos:** `harness/gates/G3_resumen_contrato.md` (nuevo).

**Estado:** G3 PENDING (decisión del propietario). Contrato sin modificar. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-007 propuesto (opción A de G3) | PROPUESTA

**Actividad:** El propietario eligió la opción A para G3 (CR-007 → verificación adversarial del contrato actual → G3) y pidió definir las pruebas de H6 en CR-007. Al preparar la CR se detectó H7: la numeración AC-01..05 de `test_plan.md` §9 no corresponde a la fuente (AI_INTEGRATION.md; REQ-3054..3069) y la nota de pendientes citaba REQ-3065..3075. CR-007 rehace §9 con TC-AC-01..16 numerados como la fuente (los 5 casos actuales se reubican; AC-11 corrige H2) y corrige H3–H5.

**Archivos:** `harness/change_requests/CR-007_alineacion-contrato-criterios-aceptacion.md` (nuevo), `session-handoff.md`.

**Estado:** CR-007 pendiente de aprobación; contrato sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-007 aprobada y aplicada | COMPLETADO

**Actividad:** El propietario aprobó CR-007 ("APRUEBO CR-007"). Aplicado: `test_plan.md` §9 con TC-AC-01..16 numerados como la fuente (REQ-3054..3069), criticidad C1/C2 por criterio, AC-11 alineado con REQ-G-034 (H2); REQ-G-063 apunta al catálogo de 31 eventos (H3); encabezados a v0.2 y cifra de 224 requisitos (H4); 8 notas PENDING resueltas marcadas, P08 se mantiene (H5).

**Archivos:** `implementation/test_plan.md`, `implementation/requirements.md`, `implementation/architecture.md`, `implementation/api_contracts.md`, `implementation/data_flow.md`, `harness/change_requests/CR-007_alineacion-contrato-criterios-aceptacion.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Siguiente acción:** verificación adversarial independiente del contrato v0.2 (H1), luego G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | Pausa de sesión | PAUSADA

**Actividad:** Se lanzó el verificador adversarial V1 (riesgo y ejecución) y se detuvo sin resultados al pausar la sesión el propietario. V2 no se lanzó.

**Estado:** contrato v0.2 con CR-007 aplicada; CR-007 y `harness/gates/G3_resumen_contrato.md` sin commit. G3 PENDING. Código funcional creado: NINGUNO.

**Siguiente acción:** relanzar V1 y V2 sobre el contrato v0.2; luego G3.

---

## 2026-11-18 | FASE 1 | Re-verificación adversarial (VER-003); CR-008 propuesto | PROPUESTA

**Actividad:** Verificación adversarial independiente del contrato v0.2 con 2 sub-agentes Sonnet de solo lectura (V1 riesgo y ejecución; V2 IA, investigación, fiscal y trazabilidad). Ambos PASS_WITH_FINDINGS, sin hallazgos críticos: 3 ALTA, 12 MEDIA, 10 BAJA; hallazgos comprobados por el Orquestador. Hallazgo adicional O-01: liberación de MONTHLY_TRADE_LIMIT_LOCK pendiente de ratificación desde G2. CR-008 propone las correcciones y dos decisiones (Q28, Q29).

**Consumo de sub-agentes:** V1 ~131K tokens, V2 ~151K tokens (superior a la guía de 80K por sub-agente Sonnet).

**Archivos:** `harness/verification/VER-003_reverificacion_contrato_v0.2.md` (nuevo), `harness/change_requests/CR-008_correcciones-reverificacion.md` (nuevo), `harness/gates/G3_resumen_contrato.md` (30 eventos), `session-handoff.md`.

**Estado:** CR-008 pendiente de aprobación; contrato v0.2 sin modificar. G3 PENDING. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-008 aprobada y aplicada; DEC-010 | COMPLETADO

**Actividad:** El propietario aprobó CR-008 ("APRUEBO CR-008, Q28 A, Q29 A"). DEC-010: MONTHLY_TRADE_LIMIT_LOCK se libera automáticamente al inicio del mes con aviso (cierra FIND-003 de G2); AI_BUDGET_WARNING una vez por mes. Aplicado: contratos completos de los 5 agentes con campos comunes de D2 y `schema_version`; MANUAL eliminado como salida; vigencia fuera de la salida del Risk Manager; evento de auditoría con campos de RISK_POLICY; REQ-G-030 con los 16 criterios textuales; REQ-G-053/059/063/096/115 y fila P19 corregidos; architecture §3.1, §6, §7, §8; data_flow §1, §2, §4, §5 (cadena de causalidad), §6, §7; test_plan TC-INV-007-B, TC-STOP-006, TC-ML-004..010, §8.8 TC-PARAM-001..005, §9, §12. Contrato v0.3.

**Archivos:** `docs/decisions/DEC-010_liberacion-limite-mensual-aviso-presupuesto.md` (nuevo), `implementation/*.md` (5 documentos), `harness/change_requests/CR-008_correcciones-reverificacion.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Siguiente acción:** verificación de cierre acotada a CR-008; luego G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | Verificación de cierre de CR-008 | PASS_WITH_FINDINGS

**Actividad:** 1 verificador independiente (Sonnet, solo lectura, ~80K tokens) confirmó los 22 puntos de CR-008. Hallazgos BAJA: C-01 (rango «3.1–3.8» en api_contracts §3.0) corregido como errata de aplicación; C-02 sin cambio; C-03 (mencionar Q28 en REQ-G-024) pendiente de decisión del propietario, no bloquea G3. Paquete de G3 actualizado (§7).

**Archivos:** `implementation/api_contracts.md`, `harness/verification/VER-003_reverificacion_contrato_v0.2.md`, `harness/gates/G3_resumen_contrato.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Siguiente acción:** decisión del propietario sobre G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-009 aprobada y aplicada; commit | COMPLETADO

**Actividad:** El propietario pidió agregar C-03 ("agrega C-03"). CR-009: REQ-G-024 recoge la liberación automática de MONTHLY_TRADE_LIMIT_LOCK (DEC-010 Q28). Commit de todo lo hecho desde CR-006 (CR-007, CR-008, CR-009, DEC-010, VER-003, paquete de G3, contrato v0.3).

**Archivos:** `implementation/requirements.md`, `harness/change_requests/CR-009_req-g-024-liberacion-limite-mensual.md` (nuevo), `harness/gates/G3_resumen_contrato.md`, `harness/verification/VER-003_reverificacion_contrato_v0.2.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Siguiente acción autorizada:** decisión del propietario sobre G3. Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 — G3 | Aprobación humana del contrato técnico | PASS

**Actividad:** El propietario aprobó el contrato técnico: "APRUEBO EL CONTRATO TÉCNICO v1.0". G3 = PASS (approved_by: propietario; 2026-11-18). Los 5 documentos del contrato pasan a v1.0 APROBADO (CR-001..CR-009 incorporadas). Desde ahora, todo cambio al contrato requiere solicitud de cambio aprobada y versionado.

**Archivos:** `harness/gates/gate_status.json` (G3 PASS, v0.3.0), `harness/manifest.json` (v0.5.0, estado G3_PASS), encabezados de `implementation/*.md` (v1.0), `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Pendientes:** REQ-G-P08 (validación fiscal con contador, diferido). G3 no aprueba TRACEABILITY_MATRIX como documento (DEC-001) ni autoriza Live Trading.

**Estado de fases:** FASE 1 completa. FASE 2 BLOQUEADA hasta "AUTORIZO INICIO DE FASE 2". Código funcional creado: NINGUNO.

---

## 2026-11-18 | FASE 1 | CR-010: estado de FASE 1 en AGENTS.md | COMPLETADO

**Actividad:** Con aprobación del propietario, la tabla de fases de `AGENTS.md` marca FASE 1 como COMPLETADA (G0..G3 PASS). Sin otros cambios; FASE 2 sigue BLOQUEADA. Commit del cierre de FASE 1.

**Archivos:** `AGENTS.md`, `harness/change_requests/CR-010_agents-estado-fase-1.md` (nuevo).

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Siguiente acción autorizada:** esperar "AUTORIZO INICIO DE FASE 2". Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-011 redactada (PROPUESTA) | PENDIENTE DE APROBACIÓN

**Actividad:** El propietario pidió definir, antes de autorizar FASE 2, (A) resolución de candidatos en conflicto, (B) Walk-Forward (embargo, ventanas OOS, histórico mínimo) y (C) confirmación de sizing/minNotional. Se redactó CR-011 con los valores dados por el propietario. NO aplicada: el contrato v1.0 no se modificó. Se dejaron 5 decisiones pendientes explícitas (colocación del embargo, consenso⇒NO_SETUP, autorización de salidas por estrategia, combinación 50/20/15/15 con WF, mínimo de 30 trades por ventana).

**Archivos:** `harness/change_requests/CR-011_conflictos-walk-forward-sizing.md` (nuevo), `progress.md`.

**Pruebas ejecutadas:** ninguna (solo documentación).

**Siguiente acción autorizada:** esperar la respuesta del propietario a las decisiones pendientes y la aprobación de CR-011; luego registrar DEC-011 y aplicar. FASE 2 sigue BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-011 aprobada con valores; aplicación en espera | PARCIAL

**Actividad:** El propietario aprobó CR-011 con valores (embargo interpretación A; consenso⇒NO_SETUP; salida por estrategia autónoma; WF dentro de Train+Val, OOS y LOCKBOX de evaluación única; 30 trades OOS agregado; histórico mínimo con tasa real del backtest piloto). CR-011 actualizada. NO aplicada al contrato: quedan 2 aclaraciones (1: la frase "los cierres protectores requieren autorización" contradice DEC-008 Q25/RISK_POLICY; 2: reformulación "2 ventanas OOS" → "2 ventanas de prueba WF"). Consulta del propietario sobre el tipo de stop: REQ-G-031 deja el tipo (stop-limit vs OCO) PENDING de FASE 2.

**Archivos:** `harness/change_requests/CR-011_conflictos-walk-forward-sizing.md`, `progress.md`.

**Pruebas ejecutadas:** ninguna (solo documentación).

**Siguiente acción autorizada:** resolver aclaraciones 1 y 2; luego DEC-011 y aplicación (contrato v1.1). FASE 2 sigue BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-011 aplicada, DEC-011 registrada, contrato v1.1 | COMPLETADO

**Actividad:** El propietario resolvió las aclaraciones (1: solo las entradas requieren autorización; cierres protectores y salidas por señal son autónomos, contrato sin cambios en ese punto; 2: «2 ventanas de prueba WF» confirmado) y ordenó aplicar CR-011. Se registró DEC-011 y se aplicó al contrato: candidatos en conflicto (2+ entradas → NO_SETUP, entrada+salida → prevalece la salida, regla binaria sin confianza), estructura Walk-Forward (WF dentro de Train+Val; OOS y LOCKBOX de evaluación única; embargo 2 m entre entrenamiento y prueba; mín. 2 ventanas de prueba; 30 trades OOS agregado; preregistro congela diseño de ventanas; histórico mínimo con tasa real del piloto), y sizing (registro del riesgo efectivo en rechazos por mínimos; sin extensión de sizing). Los 5 documentos de `implementation/` pasan a v1.1. Manifest 0.6.0.

**Archivos:** `docs/decisions/DEC-011_conflictos-walk-forward-sizing.md` (nuevo), `harness/change_requests/CR-011_conflictos-walk-forward-sizing.md` (APLICADA), `implementation/requirements.md`, `data_flow.md`, `api_contracts.md`, `test_plan.md` (TC-FLOW-004..008, TC-PS-005..006, TC-ML-011..014), `architecture.md` (versión), `harness/manifest.json`, `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK). Sin pruebas de código (no existe código).

**Pendientes (siguen PENDING de FASE 2):** tipo de orden del stop (stop-limit vs OCO, REQ-G-031); esquema del evento de señal de salida; nombres de los motivos de NO_SETUP; REQ-G-P08 (validación fiscal, diferido). `gate_status.json` no se modificó (G3 PASS se refiere a v1.0; v1.1 aprobado por el propietario mediante CR-011).

**Siguiente acción autorizada:** esperar "AUTORIZO INICIO DE FASE 2". FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-012 redactada (PROPUESTA): tipo de orden del stop | PENDIENTE DE APROBACIÓN

**Actividad:** El propietario decidió el tipo de orden del stop (REQ-G-031): OCO con STOP_LOSS de mercado, TP limit opcional; contingencia STOP_LIMIT al 0.5%. Se verificó en la documentación oficial de Binance Spot que el OCO admite `belowType=STOP_LOSS` (la contingencia no se activa). Se redactó CR-012 con tres observaciones (slippage no acotado vs reserva de 0.10%; tipo de la pierna TP = LIMIT_MAKER; límite de la contingencia). NO aplicada; contrato sigue en v1.1.

**Archivos:** `harness/change_requests/CR-012_tipo-orden-stop-oco.md` (nuevo), `progress.md`.

**Pruebas ejecutadas:** ninguna (solo documentación).

**Siguiente acción autorizada:** aprobación de CR-012; luego DEC-012 y aplicación (v1.2). FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-012 aplicada, DEC-012 registrada, contrato v1.2 | COMPLETADO

**Actividad:** El propietario aprobó CR-012 ("Aprobado"), confirmó el riesgo residual de slippage (no cota dura) y TAKE_PROFIT_LIMIT para la pierna TP, y ordenó aplicar. Se registró DEC-012 y se resolvió el PENDING de REQ-G-031: stop como OCO con pierna STOP_LOSS de mercado y TP limit opcional (sin TP: STOP_LOSS individual); contingencia STOP_LIMIT al 0.5% documentada pero no activa (verificado en la documentación oficial de Binance Spot). Los 5 documentos de `implementation/` pasan a v1.2. Manifest 0.7.0.

**Archivos:** `docs/decisions/DEC-012_tipo-orden-stop-oco.md` (nuevo), `harness/change_requests/CR-012_tipo-orden-stop-oco.md` (APLICADA), `implementation/requirements.md` (REQ-G-031), `data_flow.md`, `test_plan.md` (TC-STOP-009..012), `api_contracts.md` y `architecture.md` (versión), `harness/manifest.json`, `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK). Sin pruebas de código (no existe código).

**Pendientes (siguen PENDING de FASE 2):** reverificar el OCO con STOP_LOSS de mercado contra el exchange real; tipo definitivo de la pierna TP (TAKE_PROFIT_LIMIT, se fija en implementación); esquema del evento de señal de salida; nombres de motivos de NO_SETUP; REQ-G-P08 (validación fiscal, diferido).

**Siguiente acción autorizada:** esperar "AUTORIZO INICIO DE FASE 2". FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CONF-006 registrado: temporalidad 1d vs contrato D1/H4/H1 | ESCALADO

**Actividad:** El propietario propuso la fuente de datos históricos (klines BTC/USDT 1d, snapshot versionada con SHA-256, huecos como NaN, live por websocket `kline_1d`). Al contrastarla con el contrato se detectó un conflicto de temporalidad (el contrato usa H4 para señal y la IA se invoca al cierre H4). Registrado como CONF-006 en `conflict_register.md`, escalado al propietario. No se modificó el contrato.

**Archivos:** `implementation/conflict_register.md`, `progress.md`.

**Pruebas ejecutadas:** ninguna.

**Siguiente acción autorizada:** decisión del propietario sobre la temporalidad; luego CR/DEC para la fuente de datos. FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | DEC-013 registrada y CR-013 redactada (PROPUESTA); CONF-006 resuelta | PENDIENTE DE APROBACIÓN

**Actividad:** El propietario eligió la opción B (se mantiene H4 como señal; 1d solo contexto) y fijó la fuente de datos: klines BTC/USDT en 1d/4h/1h, snapshot única versionada en Parquet por partición (train_val/oos/lockbox, SHA-256 propio), huecos NaN, modelo de ejecución del backtest, datos en vivo por WebSocket con respaldo REST. Se registró DEC-013 y se resolvió CONF-006. CR-013 redactada como PROPUESTA con 7 aclaraciones propuestas (B.1–B.7: granularidad de particiones, huecos del modelo de ejecución, resincronización con startTime, H1 en vivo, «prioriza ventanas recientes» vs preregistro, LOCKBOX consumido, reproducibilidad del hash). NO aplicada; contrato sigue en v1.2.

**Archivos:** `docs/decisions/DEC-013_fuente-datos-historicos-snapshot.md` (nuevo), `harness/change_requests/CR-013_fuente-datos-historicos.md` (nuevo), `implementation/conflict_register.md` (CONF-006 RESUELTA), `progress.md`.

**Pruebas ejecutadas:** ninguna (solo documentación).

**Siguiente acción autorizada:** decisión del propietario sobre B.1–B.7 y aprobación de CR-013; luego aplicar (v1.3). FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 1 (post-G3) | CR-013 aplicada, DEC-013 registrada, CONF-006 resuelta, contrato v1.3 | COMPLETADO

**Actividad:** El propietario aceptó B.1–B.7 y ordenó aplicar CR-013. Aplicado: nuevos REQ-G-097 (datos en vivo: solo vela cerrada, respaldo REST con startTime, Fail-Closed hasta resincronizar, `kline_1h` incluido) y REQ-G-109 (snapshot Parquet por partición con SHA-256, columna `interval`, fechas de corte únicas, LOCKBOX sellado y «consumido», huecos NaN, modelo de ejecución del backtest, declaración de régimen); ampliación de REQ-G-103; Fase 1 de `data_flow.md`; pruebas TC-DATA-003..004 y TC-ML-015..019. CONF-006 RESUELTA (DEC-013, opción B: se mantiene H4 como señal). Los 5 documentos de `implementation/` pasan a v1.3. Manifest 0.8.0.

**Archivos:** `docs/decisions/DEC-013_fuente-datos-historicos-snapshot.md`, `harness/change_requests/CR-013_fuente-datos-historicos.md` (APLICADA), `implementation/requirements.md`, `data_flow.md`, `test_plan.md`, `api_contracts.md` y `architecture.md` (versión), `implementation/conflict_register.md`, `harness/manifest.json`, `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** validate_manifest.py, validate_requirements.py, validate_gates.py (OK). Sin pruebas de código (no existe código).

**Pendientes (siguen PENDING de FASE 2):** esquema del evento de señal de salida; nombres de motivos de NO_SETUP; reverificar el OCO contra el exchange real; tipo definitivo de la pierna TP; identificador de cliente de órdenes; almacenamiento durable del estado; servicios externos (vigilancia, IP); calibración de `effort` y costo real de IA; REQ-G-P08 (validación fiscal, diferido).

**Siguiente acción autorizada:** esperar "AUTORIZO INICIO DE FASE 2". FASE 2 BLOQUEADA. Código funcional creado: NINGUNO.

---

## 2026-11-19 | FASE 2 | INICIO AUTORIZADO; feature_list poblada para IMPL-1 | EN CURSO

**Actividad:** El propietario emitió la frase exacta "AUTORIZO INICIO DE FASE 2". Se ejecutó el procedimiento de inicio (AGENTS.md, progress, handoff, gates, feature_list). Se pobló `feature_list.json` (v0.2.0) con FEAT-001..FEAT-007 de IMPL-1 (Fundamentos de integración, architecture.md §7), derivadas de REQ-G-050/051/058..064/090/091/095/096 y de TC-MSG, TC-SEC, TC-AC del test_plan. Todas NOT_STARTED, sin evidencia. G4..G7 siguen PENDING. No se creó código.

**Archivos:** `feature_list.json`, `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** ninguna.

**Observación:** la tabla de fases de `AGENTS.md` aún dice FASE 2 «BLOQUEADA»; actualizarla requiere solicitud de cambio (precedente CR-010). No modificada.

**Siguiente acción:** implementar FEAT-001/002 (contratos y validación) con pruebas en `tests/unit/`, registrando evidencia.

---

## 2026-11-19 | FASE 2 | FEAT-001/002 implementadas (parcial) y CR-014 aplicada | COMPLETADO

**Actividad:** (1) CR-014 aplicada a petición explícita del propietario: `AGENTS.md` fila FASE 2 → «EN CURSO — autorizada (2026-11-19); IMPL-1 en desarrollo». (2) FEAT-001/002: contrato universal de mensajes con JSON Schema (`src/swingpilot/contracts/`), validación fail-closed, compatibilidad por versión mayor, construcción de cadenas correlation/causation, catálogo de 30 eventos verificado contra api_contracts.md. Entorno `.venv` con pytest y jsonschema (`requirements-dev.txt`).

**Decisión de implementación (no del contrato):** versión inicial del esquema de mensaje `1.0.0`; receptor acepta solo la misma versión mayor (rechazo por defecto; escalación queda al llamador).

**Archivos:** `AGENTS.md`, `harness/change_requests/CR-014_agents-estado-fase-2.md`, `src/swingpilot/**`, `tests/unit/test_message_contract.py`, `requirements-dev.txt`, `.gitignore`, `feature_list.json` (v0.3.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 39 passed.

**Estado:** FEAT-001 y FEAT-002 en PARTIAL (no DONE): faltan los contratos de agentes (§3) y el versionado de prompts/modelos, que dependen de FEAT-004/005. G4 sigue PENDING.

**Siguiente acción:** FEAT-003 (trazabilidad/almacén de eventos inmutable) o FEAT-004 (AI Provider Adapter).

---

## 2026-11-19 | FASE 2 | FEAT-003 implementada (parcial) | COMPLETADO

**Actividad:** almacén de eventos de auditoría `EventStore` (`src/swingpilot/audit/`): SQLite append-only con triggers que prohíben UPDATE/DELETE, validación previa con el contrato universal, idempotencia por `message_id`, rechazo de contenido distinto con el mismo id, reconstrucción ordenada por `correlation_id` con detección de huérfanos y origen único.

**Decisión de implementación (no del contrato):** SQLite para `audit_events` (misma tecnología de trades.db, architecture.md §5). No resuelve el pendiente «almacenamiento durable del estado», que sigue PENDING.

**Archivos:** `src/swingpilot/audit/*`, `tests/unit/test_event_store.py`, `feature_list.json` (v0.4.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 48 passed.

**Estado:** FEAT-003 PARTIAL: TC-AC-04 completo depende de FEAT-004/005; un DROP TRIGGER directo sobre el archivo no está cubierto. G4 PENDING.

**Siguiente acción:** FEAT-004 (AI Provider Adapter).

---

## 2026-11-19 | FASE 2 | FEAT-004 implementada con dobles de prueba (parcial) | COMPLETADO

**Actividad:** AI Provider Adapter (`src/swingpilot/ai/provider.py`) sobre el SDK `anthropic` 2.10: modelos exactos por agente (REQ-G-095), salida estructurada por esquema con validación local, sin herramientas/fallbacks/caching, rechazo = fallo del agente, un único reintento (SDK con max_retries=0, timeout 60 s, límite de ciclo 5 min; REQ-G-034), registro de `usage` por intento. Pruebas con un cliente falso y excepciones reales del SDK; ninguna llamada a la API.

**Decisiones de implementación (no del contrato):** pausa de reintento 2 s; `max_tokens` 16000; `effort` = `medium` por agente (valor inicial de REQ-G-095); versión de `anthropic` sin fijar en requirements-dev.txt.

**Archivos:** `src/swingpilot/ai/*`, `tests/unit/test_ai_provider.py`, `requirements-dev.txt`, `feature_list.json` (v0.5.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 74 passed.

**Estado:** FEAT-004 PARTIAL. No verificado contra la API real (requiere API key del propietario en `.env`); no se usó ninguna clave.

**Siguiente acción:** FEAT-005 (AI Orchestrator) o, con la API key, una prueba de humo real del adaptador.

---

## 2026-11-19 | FASE 2 | FEAT-005 implementada con dobles (parcial); CONF-007 escalado | COMPLETADO

**Actividad:** AI Orchestrator (`src/swingpilot/ai/orchestrator.py`): Fase 3 en paralelo (Market, Macro, Strategy Analyst), Fase 4 (Decision Synthesis), Fase 5 consultiva (Risk Analyst tras RISK_APPROVED); cero llamadas sin exactamente un STRATEGY_CANDIDATE; Fail-Closed ante fallo de cualquier agente; eventos en EventStore. Contratos de los 5 agentes (`src/swingpilot/contracts/agents.py`, api_contracts.md §3). Prompts de sistema versionados 0.1.0 (`src/swingpilot/ai/prompts.py`), borrador derivado de REQ-G-052..056/059.

**Decisiones de implementación (no del contrato):** el LLM produce solo el cuerpo del contrato; los campos deterministas de §3.0 los fija el Orchestrator (model_id = modelo efectivo). Payload de ANALYSIS_REQUESTED = {market_context, macro_context}. 2+ STRATEGY_CANDIDATE recibidos = sin llamadas (defensa; la regla es del Strategy Engine, CR-011). Synthesis que cita analysis_id no recibidos = fuera de contrato.

**Conflicto:** CONF-007 registrado y ESCALADO: el catálogo de eventos no tiene tipo para el análisis del Strategy Analyst (data_flow.md §5, E7). Propuesta: CR para añadir `STRATEGY_ANALYSIS_COMPLETED`. Mitigación provisional: la salida se valida y se usa, pero no se emite como evento.

**Archivos:** `src/swingpilot/ai/{orchestrator,prompts,__init__}.py`, `src/swingpilot/contracts/agents.py`, `tests/unit/test_orchestrator.py`, `implementation/conflict_register.md` (CONF-007), `feature_list.json` (v0.6.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 96 passed.

**Siguiente acción:** decisión del propietario sobre CONF-007; FEAT-006 (control de costo) y FEAT-007 (aislamiento de credenciales).

---

## 2026-11-19 | FASE 2 | CR-015 redactada (PROPUESTA); FEAT-006 implementada (parcial) | COMPLETADO

**Actividad:** (1) CR-015 redactada para CONF-007: añadir `STRATEGY_ANALYSIS_COMPLETED` al catálogo (api_contracts.md §2), nombrar E7 en data_flow.md §5, actualizar REQ-G-063; contrato v1.4. PROPUESTA, no aplicada. (2) FEAT-006 control de costo de IA (`src/swingpilot/ai/budget.py`): `AIBudget` (registro append-only de usage y costo con precios de DEC-009, tope $5, aviso $4 una vez por mes con evento AI_BUDGET_WARNING) y `EntryGate` (bloqueo previo a Fase 3 por posición abierta, bloqueos de entrada, modo seguro, estado desconocido o no disponible, o tope). El adaptador consulta el tope antes de cada intento y registra cada respuesta.

**Decisiones de implementación (no del contrato):** tarifa alta de Haiku 5.5 (>100K tokens de entrada) aplicada a toda la llamada; un estado del Risk Manager desconocido bloquea; un modelo sin precio o usage incompleto = fallo del agente.

**Pendientes para el propietario:** zona horaria del «mes calendario» (hoy parámetro, por defecto UTC; ¿America/Mexico_City?); límite de gasto en la consola de Anthropic (REQ-G-096 (4)); aprobación de CR-015.

**Archivos:** `harness/change_requests/CR-015_evento-analisis-strategy-analyst.md` (nuevo), `implementation/conflict_register.md` (CONF-007 → CR-015), `src/swingpilot/ai/{budget,provider,__init__}.py`, `tests/unit/test_ai_budget.py`, `feature_list.json` (v0.7.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 127 passed.

**Siguiente acción:** FEAT-007 (aislamiento de credenciales); decisiones del propietario arriba.

---

## 2026-11-19 | FASE 2 | CR-015 aplicada, DEC-014 registrada, CONF-007 resuelta, contrato v1.4 | COMPLETADO

**Actividad:** El propietario aprobó CR-015 («CR-015: Aprobado. Aplica B.1–B.5») y fijó la zona horaria del presupuesto de IA en America/Mexico_City. Registrada DEC-014 (Q30: CR-015; Q31: zona horaria). Aplicado B.1–B.5: `STRATEGY_ANALYSIS_COMPLETED` en api_contracts.md §2 (31 tipos), E7 nombrado en data_flow.md §5, REQ-G-063 actualizado, los 5 documentos de `implementation/` pasan a v1.4. CONF-007 RESUELTA. Manifest 0.9.0 (FASE 2). Código: catálogo de eventos +1, el AI Orchestrator emite E7 (se retiró la mitigación provisional), `AIBudget` usa America/Mexico_City por defecto.

**Archivos:** `docs/decisions/DEC-014_evento-strategy-analyst-zona-horaria.md` (nuevo), `harness/change_requests/CR-015_evento-analisis-strategy-analyst.md` (APLICADA), `implementation/*.md` (v1.4), `implementation/conflict_register.md`, `harness/manifest.json`, `src/swingpilot/contracts/message.py`, `src/swingpilot/ai/{orchestrator,budget}.py`, tests correspondientes, `feature_list.json` (v0.8.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 128 passed; validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Nota:** la zona horaria de otros cortes mensuales (MonthlyBaseline, MONTHLY_TRADE_LIMIT_LOCK) sigue sin definir (PENDING para su implementación).

**Siguiente acción:** FEAT-007 (aislamiento de credenciales y prohibiciones de agentes).

---

## 2026-11-19 | FASE 2 | FEAT-007 implementada (parcial); IMPL-1 completa en código | COMPLETADO

**Actividad:** aislamiento de credenciales (`src/swingpilot/security/credentials.py`): `CredentialVault` lee `.env` sin copiarlo a `os.environ` y entrega credenciales por ámbito (execution_engine: Binance; ai_provider: Anthropic; telegram_bot: Telegram); el AI Orchestrator y los agentes no tienen ámbito. `Secret` no se imprime ni se serializa. `process_env_violations` detecta credenciales de Binance/Telegram en el entorno del proceso. El adaptador obtiene la clave con `from_vault` y bloquea el envío si un secreto aparece en el contenido (`leak_check`). El AI Orchestrator solo puede emitir los 5 eventos de análisis. `.env.example` con nombres y sin valores.

**Decisiones de implementación (no del contrato):** nombres `BINANCE_API_SECRET` y `TELEGRAM_BOT_TOKEN`; TC-SEC-001 interpretado como «los nombres solo aparecen en el módulo que lee `.env`; ningún valor literal en `src/`».

**Archivos:** `src/swingpilot/security/*`, `src/swingpilot/ai/{provider,orchestrator}.py`, `.env.example`, `tests/unit/test_credentials.py`, `tests/unit/test_ai_provider.py`, `feature_list.json` (v0.9.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 162 passed.

**Estado de IMPL-1:** FEAT-001..007 implementadas, todas PARTIAL (ninguna DONE). Bloqueo común: verificación contra la API real de Anthropic (requiere `ANTHROPIC_API_KEY` en `.env`). G4 sigue PENDING.

**Siguiente acción:** prueba de humo real (con la clave del propietario) para cerrar FEAT-004/005; decidir con el propietario el criterio de salida de IMPL-1 y el inicio de IMPL-2.

---

## 2026-11-19 | FASE 2 | Prevención de fugas de credenciales a registros (FEAT-003/FEAT-007) | COMPLETADO

**Actividad:** a pregunta del propietario sobre fugas por logs, se revisaron las rutas y se cerraron tres huecos: (1) `EventStore(secret_check=...)` rechaza antes de escribir cualquier mensaje que contenga una credencial (el registro es inmutable); (2) `AIOrchestrator(redact=...)` redacta los mensajes de error de agentes antes de registrarlos (verificado que sin redacción un valor citado por jsonschema se filtraba); (3) `security/startup.py` con `startup_violations`: `.env` ausente o con permisos para grupo/otros, credenciales de Binance/Telegram en el entorno del proceso, `ANTHROPIC_LOG=debug` en modo LIVE o modo desconocido impiden arrancar. Verificado localmente que los logs debug del SDK de Anthropic no incluyen la clave.

**Archivos:** `src/swingpilot/audit/{event_store,__init__}.py`, `src/swingpilot/ai/orchestrator.py`, `src/swingpilot/security/{startup,__init__}.py`, `tests/unit/test_leak_prevention.py`, `feature_list.json` (v0.10.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests/unit` → 181 passed.

**Límites conocidos:** solo se detecta la credencial literal; tracebacks con variables locales pueden mostrar la clave; falta el punto de arranque de la aplicación que conecte vault, EventStore, orquestador y comprobaciones de arranque.

**Siguiente acción:** prueba de humo real contra la API de Anthropic (requiere `ANTHROPIC_API_KEY` en `.env` con permisos 600).

---

## 2026-11-19 | FASE 2 | Prueba de humo contra la API real de Anthropic | COMPLETADO

**Actividad:** con autorización del propietario («dale, escríbelo y córrelo») y `.env` en 600, se escribió y ejecutó `tests/integration/test_anthropic_live.py` (solo corre con `RUN_ANTHROPIC_LIVE=1`). Modo RESEARCH, datos sintéticos, sin Binance ni órdenes. Resultados: (paso 2) Haiku 5.5 y Sonnet 5.5 aceptan la petición tal como la arma el adaptador y devuelven el ID exacto del modelo; (pasos 3-4) los esquemas de los 5 agentes funcionan como salida estructurada; ciclo completo con E5-E8 y E11, cadena completa de 10 eventos sin huérfanos; la instrucción inyectada en una noticia se trató como contenido no fiable. Los agentes respondieron INSUFFICIENT_DATA y la síntesis INSUFFICIENT_INFO, coherente con solo dos velas H4 sintéticas.

**Costo:** $0.026997 USD, registrado en `var/ai_budget.db` (nuevo directorio local, ignorado por git).

**Estado:** FEAT-004 y FEAT-005 pasan a READY_FOR_REVIEW (no DONE: requieren revisión independiente, AGENTS.md). Observación para calibración de prompts: el Macro Analyst listó como «evento» una nota de método y marcó como FACT un ítem SPECULATION.

**Archivos:** `tests/integration/test_anthropic_live.py`, `tests/integration/results/anthropic_live_2026-11-19.json`, `.gitignore` (`var/`), `feature_list.json` (v0.11.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** prueba real → 3 passed (35 s); `.venv/bin/pytest -q tests` → 181 passed, 3 skipped.

**Siguiente acción:** revisión independiente de FEAT-004/005 (QA o propietario); calibración de prompts y `effort`; decidir el cierre de IMPL-1 e inicio de IMPL-2.

---

## 2026-11-19 | FASE 2 | Revisión QA independiente de FEAT-004/005 | COMPLETADO

**Actividad:** a petición del propietario se lanzó un QA Agent independiente (sub-agente `sonnet`, contexto: solo contrato v1.4, código, pruebas y salida bruta de la prueba live; sin historial ni conclusiones del implementador). Veredicto: FEAT-004 y FEAT-005 **APROBADAS CON OBSERVACIONES**, sin hallazgos bloqueantes. 6 hallazgos MENORES registrados en `feature_list.json` (`qa_review`): falta de test de model_id efectivo distinto del pedido; excepción en `_run_agent` sin CycleResult FAILED; carrera can_call/record en paralelo; contexto de mercado/macro sin filtrar; cobertura parcial de TC-AC-06; casos sin prueba (NO_SETUP + candidato, límite de 5 min compartido, input_analysis_ids vacío).

**Pruebas ejecutadas por QA:** `.venv/bin/pytest -q tests/unit` → 181 passed.

**Estado:** FEAT-004/005 siguen READY_FOR_REVIEW hasta que el propietario decida corregir los menores antes o pasarlas a DONE con observaciones.

**Sub-agentes en la sesión:** 1 (QA, sonnet, ~83K tokens, ~1 min).

---

## 2026-11-19 | FASE 2 | Corrección de hallazgos QA, re-auditoría y FEAT-004/005 → DONE | COMPLETADO

**Actividad:** por instrucción del propietario se corrigieron los 6 hallazgos de la QA ronda 1, con pruebas que fallan si se revierten: (1) `model_id` = modelo de la respuesta sin sustitución; (2) excepciones dentro de un agente → salida ERROR con evento FAILED y ciclo FAILED; (3) tope de $5 duro y atómico mediante reservas del costo máximo por llamada bajo candado (`AIBudget.try_reserve/settle/release`); (4) contexto de Market/Macro filtrado a los campos de api_contracts.md §3.1/§3.4; (5) prueba de que Synthesis recibe íntegras limitaciones y desacuerdos; (6) pruebas de NO_SETUP + candidato, límite de 5 min compartido entre Fase 3 y 4 y `input_analysis_ids` que debe citar exactamente los 3 análisis (prompt decision_synthesis 0.1.1). Prueba real re-ejecutada: 3 passed, $0.026509 (acumulado del mes $0.053506), Synthesis cita los 3 analysis_id.

**Decisión de implementación:** el tope de $5 es duro: una llamada se rechaza si su costo máximo posible no cabe bajo el tope (con gasto cercano a $5 se rechaza Sonnet aunque el tope no se haya alcanzado).

**Re-auditoría:** QA independiente nuevo (sonnet): 6/6 hallazgos CORREGIDOS; FEAT-004 y FEAT-005 **CONFORMES**. 3 menores nuevos registrados como pendientes (costo no registrado ante COST_UNMEASURABLE; cota de tokens con texto no ASCII; TC-AC-06 lado salida depende del prompt).

**Aprobación:** FEAT-004 y FEAT-005 → **DONE** (instrucción del propietario condicionada a conformidad de QA; condición cumplida).

**Archivos:** `src/swingpilot/ai/{provider,orchestrator,prompts,budget}.py`, `tests/unit/{test_ai_provider,test_orchestrator,test_ai_budget,test_credentials}.py`, `tests/integration/test_anthropic_live.py`, `tests/integration/results/anthropic_live_2026-11-19T2120Z.json` (renombrado) y `…T2131Z.json`, `feature_list.json` (v0.13.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 205 passed, 3 skipped; prueba real → 3 passed.

**Sub-agentes en la sesión:** 2 (QA ronda 1 y ronda 2, sonnet; ~176K tokens en total, ~2 min).

**Siguiente acción:** atender los 3 menores; cerrar FEAT-001/002/003/006/007 (hoy PARTIAL por dependencias de fases posteriores) o acordar con el propietario el criterio de salida de IMPL-1.

---

## 2026-11-19 | FASE 2 | Corrección de los 3 menores de la QA ronda 2 | COMPLETADO

**Actividad:** a petición del propietario: (1) ante `COST_UNMEASURABLE` se registra en `ai_usage` el costo máximo reservado de la llamada, marcado `estimated=1` (nueva columna con migración automática de bases previas; `var/ai_budget.db` se migra al abrirse), para que una llamada cobrada nunca quede fuera del tope; (2) la cota de tokens de entrada de la reserva se calcula por byte UTF-8 (+2000), válida para texto no ASCII; (3) el AI Orchestrator añade de forma determinista al `missing_data` de la síntesis los datos faltantes declarados por la Fase 3 (y un INSUFFICIENT_DATA sin detalle), con el agente de origen y sin duplicados.

**Decisión de implementación:** la propagación de (3) modifica lo que registra la síntesis respecto de la respuesta literal del LLM: solo añade elementos que la Fase 3 declaró; no inventa ni elimina.

**Archivos:** `src/swingpilot/ai/{budget,provider,orchestrator}.py`, `tests/unit/{test_ai_budget,test_orchestrator}.py`, `feature_list.json` (v0.14.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 218 passed, 3 skipped. Prueba live no re-ejecutada (los cambios no alteran la petición a la API ni los prompts).

**Estado:** FEAT-004/005 siguen DONE; los cambios posteriores a la aprobación están registrados en `post_approval_changes` con re-auditoría PENDING.

**Siguiente acción:** re-auditoría QA de los cambios (opcional, recomendada); acordar criterio de salida de IMPL-1.

---

## 2026-11-19 | FASE 2 | Re-auditoría QA de los cambios posteriores a la aprobación | COMPLETADO

**Actividad:** a petición del propietario, tercer QA independiente (sonnet) sobre los cambios del commit `6b5b32d` que corrigieron los 3 menores de la ronda 2. Resultado: 3/3 CORREGIDOS; migración de `ai_usage`, liberación de reservas y propagación de `missing_data` revisadas sin riesgos bloqueantes; la propagación no se considera desviación del contrato. Veredicto: FEAT-004 y FEAT-005 **SE MANTIENEN DONE**. 3 menores nuevos registrados en `feature_list.json` (texto INSUFFICIENT_DATA generado por el orquestador, a documentar en api_contracts.md §3.3 mediante CR; sin re-validación tras ampliar missing_data; caso límite en `settle`). Nota de QA: la conclusión de que las pruebas fallarían al revertir es por lectura de código.

**Pruebas ejecutadas (QA):** `.venv/bin/pytest -q tests` → 218 passed, 3 skipped.

**Sub-agentes en la sesión:** 3 (QA rondas 1–3, sonnet; ~233K tokens en total, ~2.5 min). Por encima del tope orientativo de 200K de entrada en sub-agentes.

**Siguiente acción:** decidir si atender los 3 menores nuevos (uno requiere CR); acordar criterio de salida de IMPL-1.

---

## 2026-11-19 | FASE 2 | Corrección de los menores 2 y 3 de la QA ronda 3 | COMPLETADO

**Actividad:** a petición del propietario: (2) la salida de Decision Synthesis con `missing_data` ampliado se vuelve a validar contra el contrato; si no valida → ERROR `OUT_OF_CONTRACT` con evento FAILED; (3) `AIBudget.settle` separa medición (`_measure`) y escritura: solo un error de medición lleva al registro conservador; un fallo de escritura se propaga sin segundo intento de registro.

**Archivos:** `src/swingpilot/ai/{budget,orchestrator}.py`, `tests/unit/{test_ai_budget,test_orchestrator}.py`, `feature_list.json` (v0.16.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 223 passed, 3 skipped.

**Estado:** FEAT-004/005 siguen DONE; cambios registrados en `post_approval_changes_2` (re-auditoría PENDING). Abierto: menor 1 (documentar en api_contracts.md §3.3 el texto `<agente>: INSUFFICIENT_DATA`; requiere CR).

**Siguiente acción:** CR para el menor 1 (si el propietario lo decide); acordar criterio de salida de IMPL-1.

---

## 2026-11-19 | FASE 2 | CR-016 redactada (PROPUESTA) para el menor 1 de la QA ronda 3 | PENDIENTE DE APROBACIÓN

**Actividad:** redactada `harness/change_requests/CR-016_propagacion-datos-faltantes-sintesis.md`: documenta en api_contracts.md §3.0/§3.3, REQ-G-073 y TC-AC-06 la propagación determinista de los datos faltantes de la Fase 3 a la salida de Decision Synthesis (formato `"<agente>: …"` y `"<agente>: INSUFFICIENT_DATA"`); contrato v1.5. Sin cambios de código. Alternativa D.1 (campo separado). Sección E: otras tres prácticas implementadas no documentadas (sobre determinista fijado por el Orchestrator; `input_analysis_ids` exactamente los 3 análisis; filtrado de contexto) para que el propietario decida si se incluyen. NO aplicada; contrato sigue en v1.4.

**Archivos:** `harness/change_requests/CR-016_propagacion-datos-faltantes-sintesis.md` (nuevo), `feature_list.json`, `progress.md`.

**Pruebas ejecutadas:** ninguna (solo documentación).

**Siguiente acción:** decisión del propietario sobre CR-016 (B tal cual o D.1; incluir E.1–E.3 o no).

---

## 2026-11-19 | FASE 2 | CR-016 aplicada, DEC-015 registrada, contrato v1.5 | COMPLETADO

**Actividad:** el propietario aprobó CR-016 («CR-016: Aprobado. Propagación en missing_data (sin campo aparte). Incluir E.1, E.2 y E.3»). Registrada DEC-015 (Q32–Q35). Aplicado: api_contracts.md §3.0 (definición de `missing_data`; campos comunes fijados por el Orchestrator, E.1), §3.1 y §3.4 (contexto mínimo, E.3), §3.3 (propagación de datos faltantes, B.1; `input_analysis_ids` = exactamente los 3 análisis, E.2); REQ-G-051 (E.1, E.3) y REQ-G-073 (B.3, E.2); TC-AC-06 (B.4). Los 5 documentos de `implementation/` pasan a v1.5. Manifest 0.10.0. Sin cambios funcionales de código (solo referencias en comentarios). Cerrado el menor 1 de la QA ronda 3; FEAT-004/005 sin menores abiertos.

**Archivos:** `docs/decisions/DEC-015_propagacion-datos-faltantes-sintesis.md` (nuevo), `harness/change_requests/CR-016_propagacion-datos-faltantes-sintesis.md` (APLICADA), `implementation/*.md` (v1.5), `harness/manifest.json`, `src/swingpilot/ai/orchestrator.py` (comentarios), `feature_list.json` (v0.17.0), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 223 passed, 3 skipped; validate_manifest.py, validate_requirements.py, validate_gates.py (OK).

**Pendiente:** re-auditoría de `post_approval_changes_2` de FEAT-004/005 (PENDING); criterio de salida de IMPL-1.

---

## 2026-11-19 | FASE 2 | QA ronda 4, arranque de FEAT-007 y CIERRE DE IMPL-1 | COMPLETADO

**Criterio de salida de IMPL-1 (propietario, 2026-11-19):** G4 pasa con la prueba real documentada en `feature_list.json`; FEAT-001..007 en DONE, o DONE-PARTIAL con dependencia explícita de una fase posterior; los 3 validadores en OK; commit final con `feature_list.json`, `progress.md` y `session-handoff.md` con la transición a IMPL-2; re-auditoría de los menores 2 y 3 registrada.

**QA ronda 4** (cuarto sub-agente independiente, sonnet): A1/A2 (menores 2 y 3 de la ronda 3) CORREGIDOS sin regresiones; clasificación de salida de las 7 FEAT CONFORME; G4 PASS con alcance IMPL-1 (live_api_evidence cuadra con los resultados). Menores: `not_covered` obsoleto en FEAT-001/002 (corregido); el punto de arranque de FEAT-007 se había diferido sin razón técnica (implementado: `src/swingpilot/bootstrap.py`, `tests/unit/test_bootstrap.py`, 10 pruebas; posterior a la auditoría, sin re-auditoría); `verified_by` y G4 por registrar (registrados).

**Resultado:**
- FEAT-001, FEAT-004, FEAT-005: **DONE**. FEAT-002, FEAT-003, FEAT-006, FEAT-007: **DONE-PARTIAL** con dependencias explícitas (IMPL-3, IMPL-4, IMPL-5, IMPL-6, G6 o acción del propietario), justificadas en `impl1_exit.deferred`.
- **G4 = PASS** (alcance IMPL-1) en `harness/gates/gate_status.json`.
- `live_api_evidence` en `feature_list.json`: dos corridas reales, modelos devueltos, tokens y costo por llamada, pasos superados; total $0.053506.
- Re-auditoría de los menores 2 y 3: completada en la ronda 4 (no quedó PENDING).
- Nota: varias dependencias son de fases posteriores a IMPL-2 (p. ej. Execution Engine = IMPL-5); se registró la fase real según architecture.md §7.

**Archivos:** `src/swingpilot/bootstrap.py` (nuevo), `tests/unit/test_bootstrap.py` (nuevo), `feature_list.json` (v1.0.0), `harness/gates/gate_status.json` (G4), `progress.md`, `session-handoff.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 233 passed, 3 skipped; validate_manifest.py, validate_requirements.py, validate_gates.py → OK.

**Sub-agentes en la sesión:** 4 (QA rondas 1–4, sonnet; ~298K tokens en total), por encima del tope orientativo de 200K.

**Siguiente acción autorizada:** iniciar IMPL-2 «Agentes especializados» cuando el propietario lo indique, en una sesión nueva.

---

## 2026-11-19 | FASE 2 | IMPL-2 «Agentes especializados»: registro de FEAT y plan propuesto | PENDIENTE DE APROBACIÓN

**Actividad:** inicio de sesión según AGENTS.md (AGENTS.md, progress.md, session-handoff.md, gate_status.json, feature_list.json). Nota: el commit 31f55e2 citado por el propietario no está en ninguna rama; su árbol es idéntico al de HEAD 29c03f7 (mismo commit de cierre de IMPL-1 tras reordenar la historia). Registradas FEAT-008..014 (status PENDING) desde el contrato v1.5: architecture.md §7 fila 2; REQ-G-050..059, REQ-G-062, REQ-G-071, REQ-G-073, REQ-G-074, REQ-G-091, REQ-G-095 (PENDING FASE 2), REQ-G-096; api_contracts.md §3.0–§3.7; test_plan.md §8.3, §8.4, §8.7, §9; DEC-009 Condiciones. Cada FEAT separa lo heredado de IMPL-1 y las dependencias de fases posteriores. Plan en `impl2_plan` con 4 preguntas abiertas para el propietario (criterio de calidad, datos de prueba y fuente de noticias, tope de gasto, forma de aprobar effort/prompts). Sin cambios de código.

**Archivos:** `feature_list.json` (v1.1.0), `progress.md`.

**Pruebas ejecutadas:** ninguna de código; validate_manifest.py, validate_requirements.py, validate_gates.py → OK; referencias REQ/TC de FEAT-008..014 comprobadas contra el contrato.

**Siguiente acción:** aprobación del plan de IMPL-2 y respuesta a Q1–Q4 por el propietario.

---

## 2026-11-19 | FASE 2 | IMPL-2 aprobada (DEC-016) y paso 1: infraestructura de calibración | COMPLETADO

**Aprobación:** el propietario aprobó el plan de IMPL-2 con las decisiones Q1–Q4 y condiciones adicionales, registradas en `docs/decisions/DEC-016_plan-impl2-calibracion-agentes.md` (Q36–Q40). Plan detallado: `harness/plans/IMPL-2_plan.md`.

**Actividad (paso 1, sin coste de API):** `tests/calibration/` (herramienta de desarrollo, no código operativo): `experiment_budget.py` (tope incremental USD 1.00, aviso al 80%, bloqueo, reserva atómica, candado de proceso, libro append-only; se suma al tope mensual de $5), `scenarios.py` (14 escenarios con resultados esperados), `checks.py` (contrato, V1–V8, expectativas), `run_battery.py` (ejecutor real opt-in con informe JSON y Markdown), `fetch_binance_klines.py` (endpoint público, sin credenciales). Velas públicas de Binance descargadas una vez (data-api.binance.vision; cerradas antes de 2026-11-19T16:00Z) y congeladas. `feature_list.json` v1.2.0 (impl2_plan APROBADO; criterios Q36–Q40 en FEAT-008..014).

**Congelación de resultados esperados (antes de cualquier corrida real, DEC-016 Q36):**
- `tests/calibration/scenarios.py` SHA-256 `07d8c753594fbe07fa61e5aa70bb07b1f19623badb5c73ea84470e5f38e4e5ef`
- `tests/calibration/fixtures/binance_btcusdt_klines.json` SHA-256 `8fe98ecbc2c0a6197947ac6d3f62eefc21b4e4fecc8d164e0d1bdd3385367aa2`

**Archivos:** `docs/decisions/DEC-016_plan-impl2-calibracion-agentes.md`, `harness/plans/IMPL-2_plan.md`, `tests/calibration/*` (nuevos), `tests/unit/test_impl2_calibration.py` (nuevo, 23 pruebas), `feature_list.json`, `progress.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 256 passed, 3 skipped; validate_manifest/requirements/gates → OK.

**Siguiente acción:** paso 2, corrida base real (prompts 0.1.x, effort medium), ≈ $0.15 del tope de IMPL-2.

---

## 2026-11-19 | FASE 2 | IMPL-2 paso 2: corrida base real y congelación v2 de la batería | COMPLETADO

**Corrida base** (prompts 0.1.0 / síntesis 0.1.1, effort medium en los 5): `tests/calibration/results/IMPL2_2026-11-19T2343Z_base.{json,md}`. 14/14 escenarios: contrato 100%, cero críticas (V1–V8), todas las expectativas cumplidas. Costo $0.118517 (acumulado IMPL-2 $0.118517 de $1.00). Ciclo completo de 5 agentes: $0.0304 (CYC-01) y $0.0311 (CYC-02), frente a ~$0.030 estimado en DEC-009. Las observaciones de IMPL-1 (nota de método como evento; FACT en especulación) no se repitieron (MAC-01, MAC-02).

**Revisión del contenido (no la detectan las comprobaciones automáticas):**
- Defecto de datos del escenario (no de los agentes): las velas sintéticas omitían la H4 de 12:00 y la H1 de 15:00, cerradas a DATA_TS según REQ-G-070. Market Analyst y Decision Synthesis lo declararon como dato faltante.
- Nombre `TREND_PULLBACK_SINTETICA_BNB` (CYC-02) interpretado como el token BNB → renombrado a `_HIST`.
- Para el propietario: el Macro Analyst devuelve INSUFFICIENT_DATA en todos los escenarios porque `macro_data` llega vacío (el contrato no define su fuente); la síntesis de CYC-01 decidió INSUFFICIENT_INFO en parte por ello.

**Congelación v2 de la batería** (solo datos de entrada corregidos; ninguna expectativa cambió): `tests/calibration/scenarios.py` SHA-256 `8f68e9a83cfb0658531d12ea616acadbf753d91c81f9274d39ff340dd5eb3a29`. Velas de Binance sin cambios (`8fe98ecb…`). El ejecutor registra ahora la latencia de cada llamada.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 256 passed, 3 skipped.

**Siguiente acción:** paso 4, comparación de effort (Haiku low/high en sus 9 escenarios; síntesis high en SYN-01..03).

---

## 2026-11-19 | FASE 2 | IMPL-2 pasos 3–5: comparación de effort, prompts 0.2.0 y propuesta en DEC-016 | PENDIENTE DE APROBACIÓN

**Comparación de effort (batería v2):** Haiku low FALLA (MAC-01 FACT en especulación; MAC-03 RECOMMENDATION en la noticia inyectada); Haiku medium FALLA STR-01 (dato no recibido como motivo de descarte; en la base había pasado); Haiku high PASA (+37% de costo, más latencia); síntesis high PASA con las mismas decisiones (+52% de costo).

**Prompts 0.2.0** (`src/swingpilot/ai/prompts.py`): macro_analyst y strategy_analyst (reglas en DEC-016). Con medium: 2/2 corridas sin fallos; con low: pasa las expectativas, pero el Macro marca un RUMOR como FACT. `tests/unit/test_orchestrator.py` actualizado a las nuevas versiones.

**Propuesta registrada en DEC-016:** effort medium en los 5 agentes; macro y strategy 0.2.0; resto sin cambios. Modelos sin cambio. Observación abierta: el Macro Analyst responde INSUFFICIENT_DATA porque `macro_data` llega vacío (fuente no definida en el contrato).

**Gasto de API:** acumulado IMPL-2 $0.235959 de $1.00 (sin avisos del 80%).

**Archivos:** `src/swingpilot/ai/prompts.py`, `tests/unit/test_orchestrator.py`, `tests/calibration/run_battery.py` (latencia), `tests/calibration/scenarios.py` (v2), `tests/calibration/results/IMPL2_*` (8 corridas), `docs/decisions/DEC-016_plan-impl2-calibracion-agentes.md`, `progress.md`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` → 256 passed, 3 skipped.

**Siguiente acción:** aprobación del propietario de la configuración de DEC-016 → dos corridas finales consecutivas de la batería completa.

---

## 2026-11-19/20 | FASE 2 | IMPL-2 paso 6: configuración aprobada y dos corridas finales | PENDIENTE DE EVALUACIÓN CUALITATIVA

**Aprobación:** el propietario aprobó la configuración de DEC-016 («Apruebo la configuración de DEC-016; lanza las corridas finales»): effort medium ×5; prompts market 0.1.0, macro 0.2.0, strategy 0.2.0, risk 0.1.0, synthesis 0.1.1.

**Corridas finales consecutivas** (batería v2, sha256 `8f68e9a8…`): `tests/calibration/results/IMPL2_2026-11-19T2358Z_final-1.{json,md}` y `IMPL2_2026-11-20T0001Z_final-2.{json,md}`. Ambas: 14/14 escenarios, contrato 100%, cero críticas, todas las expectativas. Decisiones de la síntesis idénticas en ambas (SYN-01 DISAGREEMENT, SYN-02 INSUFFICIENT_INFO, SYN-03 TRADE_PROPOSAL, CYC-01 INSUFFICIENT_INFO, CYC-02 DISCARD). Ciclo de 5 agentes: $0.029–0.032; latencia sumada de llamadas 50–60 s (Fase 3 en paralelo). Costo $0.121384 + $0.123146; acumulado IMPL-2 $0.480488 de $1.00, sin aviso del 80%.

**Archivos:** `docs/decisions/DEC-016_plan-impl2-calibracion-agentes.md`, `feature_list.json` (evidencia FEAT-008..014; status sigue PENDING), `progress.md`, `session-handoff.md`, resultados en `tests/calibration/results/`.

**Pendiente:** evaluación cualitativa del propietario sobre los dos informes `.md`; QA independiente (≤ 2 rondas); G4 con alcance IMPL-2; aprobación de cierre. Observación abierta: Macro con `macro_data` vacío.

---

## 2026-11-20 | FASE 2 | IMPL-2: QA independiente ronda 1 | COMPLETADO

**QA ronda 1** (sub-agente independiente, sonnet, ~66K tokens; solo contrato, código y evidencia; sin corridas con costo): pytest 256 passed, 3 skipped. FEAT-008..014, tope de experimentación (Q38), corridas finales y prompts 0.2.0: CONFORME. checks.py: OBSERVACIÓN. Sin bloqueantes ni mayores.

**Menores:** (1) gasto desactualizado en DEC-016 → corregido; (2) comentario «pendiente de aprobación» en prompts.py → corregido (sin cambio de texto ni versión de los prompts); (3) MAC-02 pasa con cero eventos → no se cambia (es el resultado esperado de esa entrada); (4) la expectativa de SYN-01 acepta INSUFFICIENT_INFO, más laxa que TC-AC-06 → escalado al propietario (las dos corridas finales dieron DISAGREEMENT; endurecerla exige congelación v3 y repetir las corridas). Registrado en `feature_list.json` → `impl2_plan.qa_reviews`.

**Pruebas ejecutadas:** `.venv/bin/pytest -q tests` (tras las correcciones).

**Pendiente:** evaluación cualitativa del propietario; decisión sobre el menor 4 y sobre `macro_data` vacío; G4 con alcance IMPL-2; aprobación de cierre. Rondas de QA usadas: 1 de 2. Sub-agentes: 1 (~66K tokens).
