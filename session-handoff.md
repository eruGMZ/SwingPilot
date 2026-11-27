# session-handoff.md — SwingPilot Harness

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-025 aplicada contractualmente (contrato v1.13); B8.1–B8.3 sin commit conservados; ET-10 diferido a B9

**Base:** `0f2185c` (CR-024 implementada y commiteada). **Cambios sin commit:** documentos de CR-025 (CR-025, CR-023/024 notas, `implementation/*`, `feature_list.json` v1.25.0, `progress.md`, este archivo) y el trabajo de B8.1–B8.3 (`independence.py`, `experiments.py`, `ml/registry.py` y pruebas: `test_cr024_b8_1_approval_attestation.py`, `test_cr024_b8_2_approval_transition.py`, `test_cr024_b8_3_promotion_eligibility.py`, `historical_approval.py` y ajustes en `test_engines.py`, `test_ml_registry.py`, `test_research.py`, `test_cr023_b3_preregistration.py`). Comprobar con `git status -sb`.
**B8.4a/b (2026-11-26):** CLI `approve` implementada y probada; `pytest tests/unit tests/security` → 1500 passed, 0 skipped, 0 failed; validadores 0/0/0; registro real intacto. B8.1–B8.4 siguen sin commit; QA independiente pendiente; ET-10 y CLI de promoción ML diferidos a B9. Ver `progress.md` y `research/README.md`.
**Corrección:** las notas «B8 bloqueada» y «B8 sin iniciar» de los puntos inferiores están **obsoletas**: B8.1–B8.3 existen sin commit y sin verificar en esta sesión (no se ejecutaron pruebas); B8 no está cerrada. Texto original conservado.
**CR-025 (contrato v1.13):** V9 técnica en ET-9 y ET-10; `approval_binding` (con `attestation_sha256`) persistida en la evidencia de APPROVED; `HISTORICAL_APPROVALS` cerrado y vacío; plazo de 2 s para el bloqueo de ET-10. **B8 debe integrar CR-025 antes de cerrarse** (D5): contrato de retorno de `ApprovalCheck`, V9 en ET-9, fixtures históricas solo con parche por prueba. **ET-10 en el Strategy Engine: B9.**
**Pendientes:** implementación y verificación independiente de CR-025 (autorización separada); P5 de CR-021; O3/O4; D6 diferida; CONF-010 OPEN; D3 ABIERTA; D4 bloqueada; SNAP-0001 no creada. Ningún FEAT cerrado.
**Siguiente acción autorizada:** ninguna hasta la revisión del propietario. Sin commit ni push.

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-024 aplicada contractualmente (contrato v1.12); B8 sigue bloqueada

**Base:** `a762f72`; cambios documentales **sin commit**. CR-024 (aprobada por el propietario) aplicada: contrato v1.12, `feature_list.json` v1.24.0 (REQ-G-104/106/109/P23; AC-015-7, AC-015-9, AC-017-1, AC-017-8, AC-017-9, AC-017-14, AC-017-15 nuevo, AC-019-2; TC-ML-007/012/019/025/027 y TC-ML-029 nueva). Detalle en `progress.md` (entrada CR-024).
**Estado vigente:** B1–B7 de CR-023 implementados; el acceso final no está bloqueado por `_FINAL_ACCESS_BLOCKED_UNTIL_B6` (no existe). **B8 bloqueada** hasta implementar y verificar CR-024 (módulo de persistencia de resultados, `IssuedWindowResult`, `WINDOW_RESULT_PERSISTED`, ET-4/5/6/`resolve_lockbox`, CLI de recuperación): requiere autorización separada. No se ejecutó código, pruebas ni subagentes.
**Pendientes:** implementación y verificación independiente de CR-024; P5 de CR-021 (PENDIENTE); O3/O4; D6 diferida; CONF-010 OPEN; D3 ABIERTA; D4 bloqueada; SNAP-0001 no creada. Ningún FEAT cerrado.
**Siguiente acción autorizada:** ninguna hasta la revisión del propietario. Sin commit ni push.

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-023 decisión 5 / atestación ET-8 (B8.0) registrada; B8 bloqueada por ambigüedad

**Base:** `a762f72`; cambios documentales **sin commit**. Regla aprobada: `HUMAN_REVIEW → APPROVED` exige ET-8 ELIGIBLE y `AUTORIZA: APROBACION EXP-NNNN SHA256=… OOS=… LOCKBOX=… V1/V6/V7=CONFIRMADA` (ASCII estricto, única por experimento, ligada al `decision_ref`), revalidada bajo el bloqueo del registro; sin overrides; aprobaciones históricas intactas. Detalle en `progress.md` (entrada 2026-11-26, decisión 5).
**BLOQUEO:** no existe `evaluation_hash` autoritativo persistido (CR-021 cubre solo `train_val`; `PARTITION_CONSUMED` sin hash; B7 no persiste resultados). Requiere decisión del propietario (¿digest de snapshot/manifiesto o hash del resultado con registro nuevo?) y posible enmienda de contrato. No implementar B8 hasta resolverlo.
**Se conservan:** `_FINAL_ACCESS_BLOCKED_UNTIL_B6`; O3/O4; CONF-010 OPEN; P5 PENDIENTE; D3 ABIERTA; D4 bloqueada; SNAP-0001 no creada. **[Nota de corrección 2026-11-26 (CR-024): la mención de B6 y de `_FINAL_ACCESS_BLOCKED_UNTIL_B6` está obsoleta; B6 y B7 se implementaron (`8a50604`, `a762f72`) y esa constante no existe en `src/` ni en `tests/`. Texto original conservado.]**

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-023 decisiones 2 y 3 registradas; entrada para B6

**Base:** `804880a`. Decisión 2 (gramática `AUTORIZA: ATESTACION`, ligada a la grant, única, reutiliza V1; sustituye el dict `attestations`; ET-8 diferida a B8) y decisión 3 (resolvedor snapshot→ventana por manifiestos verificados; credencial interna obligatoria para escribir consumos con precedente `FreezeCheck`; ET-4 rechaza manifiestos duplicados; publicación y claim de ET-6 serializados por el bloqueo del registro) APROBADAS; detalle y compatibilidad en `progress.md` (entrada 2026-11-26, decisiones 2 y 3). Sin conflicto contractual; forma de `PARTITION_CONSUMED`, C2 y CR-020/021/022 preservados.
**Para B6:** implementar solo con autorización expresa; incluye ajuste de B5 (duplicados y publicación bajo bloqueo) y adaptación de pruebas por el cambio de firma de `claim_partition`. Los cambios documentales de esta entrada están **sin commit**.
**Se conservan:** `_FINAL_ACCESS_BLOCKED_UNTIL_B6`; O3/O4; CONF-010 OPEN; P5 PENDIENTE; D3 ABIERTA; D4 bloqueada; B6–B9 sin iniciar; SNAP-0001 no creada. **[Nota de corrección 2026-11-26 (CR-024): la mención de B6 y de `_FINAL_ACCESS_BLOCKED_UNTIL_B6` está obsoleta; B6 y B7 se implementaron (`8a50604`, `a762f72`) y esa constante no existe en `src/` ni en `tests/`. Texto original conservado.]**

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-023 B5 implementado sin commit; siguiente: revisión del propietario

**Base:** `e908472` más B5 **sin commit** (comprobar con `git status -sb`). Detalle y disposiciones B5-02, B5-03A y B5-03B en `progress.md` (entrada 2026-11-26, bloque B5). Contrato v1.11; `feature_list.json` v1.23.0 sin cambios.
**Se conservan:** bloqueo de acceso final hasta B6; O3/O4; CONF-010 OPEN; P5 PENDIENTE; B6–B9 sin iniciar; SNAP-0001 no creada. **[Nota de corrección 2026-11-26 (CR-024): la mención de B6 y de `_FINAL_ACCESS_BLOCKED_UNTIL_B6` está obsoleta; B6 y B7 se implementaron (`8a50604`, `a762f72`) y esa constante no existe en `src/` ni en `tests/`. Texto original conservado.]**
**Siguiente acción autorizada:** ninguna hasta la revisión del propietario. Sin push.

## PUNTO DE REANUDACIÓN (2026-11-26) — CR-023 decisión 1 registrada; entrada para B4

**Hecho:** decisión 1 aprobada por el propietario y registrada en `progress.md` (entrada 2026-11-26, «decisión 1»): línea `AUTORIZA: FRONTERA EXP-NNNN SHA256=<64 hex> B=YYYY-MM-DDT00:00:00Z` con gramática estricta, unicidad y ligadura al preregistro; V1 se acredita con una atestación del propietario que debe existir en ET-3 (ET-4 la reutiliza; ET-5 la cita o reafirma), no con fechas de commit; clasificación C2 (metodológica frente a técnica).
**Atestación V1 aprobada (2026-11-26):** `AUTORIZA: PUBLICACION EXP-NNNN SHA256=<64 hex> B=YYYY-MM-DDT00:00:00Z P=<YYYY-MM-DDTHH:MM:SSZ|NONE> RESULTADO=<VALIDA|INVALIDA>`, detalle en `progress.md`.
**Para B4:** implementar solo con autorización expresa. Sin cambios de contrato, código ni pruebas en este registro.
**Se conservan:** las cuatro decisiones abiertas restantes; B3 y el resto del estado del punto de reanudación inferior.

## PUNTO DE REANUDACIÓN (2026-11-26) — siguiente: revisión del propietario de CR-023 B3 (commit `2b825b0`)

**Base:** `2b825b0` en `develop` (= `origin/develop`, comprobado con Git el 2026-11-26): B3 **ya está commiteado y publicado** (corrige la referencia anterior «`8629d0f` más B3 sin commit»). Contrato **v1.11**; `feature_list.json` **v1.23.0** sin cambios.
**Hecho:** B3 implementado (detalle y Decisión 4 —inventario mínimo obligatorio de exposiciones— en `progress.md`, entrada 2026-11-26). Suite 1197 passed, 5 skipped; validadores → código 0; registro real `07efad20…` sin cambios.
**Se conservan:** bloqueo de acceso final hasta B6; O3/O4; cuatro decisiones abiertas restantes; CONF-010 OPEN; P5 de CR-021 PENDIENTE; S1–S4; D3 ABIERTA; D4 bloqueada; B4–B9 sin iniciar. **[Nota de corrección 2026-11-26 (CR-024): la mención de B6 y de `_FINAL_ACCESS_BLOCKED_UNTIL_B6` está obsoleta; B6 y B7 se implementaron (`8a50604`, `a762f72`) y esa constante no existe en `src/` ni en `tests/`. Texto original conservado.]**
**Siguiente acción autorizada:** ninguna. Los cambios documentales de la decisión 1 están sin commit.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: revisión del propietario de la aplicación contractual de CR-023 (DEC-025); sin commit

**Base:** `aca408e` en `develop` (= `origin/develop` al iniciar; árbol limpio antes de esta aplicación) más la aplicación documental de CR-023, **sin commit** (comprobar con `git status -sb`). Contrato **v1.11**; `feature_list.json` **v1.23.0**.
**Aprobación del propietario (2026-11-25, DEC-025):** CR-023 aprobada con D3.1–D3.8, P1–P8, R1–R5, U1–U2 y F1–F4, y las correcciones obligatorias C1 (V4-pre/V4-post por etapa) y C2 (no elegibilidad metodológica ⇒ `NO_SETUP`/`NO_APPROVED_STRATEGY`/`CONFIRMATORY_ELIGIBILITY_LOST`; fallo técnico ⇒ `ERROR`/`ELIGIBILITY_UNDETERMINED`), incorporadas antes de aplicar. Documentos: `harness/change_requests/CR-023_particiones-prospectivas-frontera-independencia.md`, `docs/decisions/DEC-025_aprobacion-cr023-particiones-prospectivas.md`.
**Aplicado:** REQ-G-101, 103, 104, 106, 109, P10, P15, P23; `api_contracts.md` §B.0.4 y §B.7; `data_flow.md` §3; cabeceras v1.11; TC-ML-009, 014, 015, 016, 019 y TC-ML-025..028. **FEAT-015 DONE → IN_PROGRESS** (reapertura focalizada: AC-015-1, 3, 7 y nuevo AC-015-9; DONE histórico bajo v1.10 conservado; regresión de AC-015-2, 4, 5, 6, 8). FEAT-017 (AC-017-3, 4, 9, 10, 11; nuevo AC-017-14), FEAT-019 (AC-019-2) y FEAT-020 (AC-020-2) siguen IN_PROGRESS; sin implementación ni verificación.
**Verificación:** validadores → código 0; IDs AC y TC únicos; registro real `07efad20…` sin cambios; sin cambios de código, pruebas, registro ni gates; pruebas y sondas no ejecutadas (solo documental).
**Estado:** **D3 ABIERTA** (solo cumplida la condición 1 de CR-023 §L); **D4 bloqueada**; D5–D7 sin iniciar; SNAP-0001 no creada. Se conservan CONF-009 (reevaluación antes del cierre de FEAT-017), CONF-010 OPEN, O3/O4 (el almacén de preregistros no satisface O4), P5 de CR-021 PENDIENTE, S1–S4, N-2, N-3, `_marker_error`, HUMAN_REVIEW, CR-020/021/022 y los cierres de D1, D2 y D8.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario de la aplicación contractual antes de cualquier commit o implementación. Sin push.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: D3, integridad histórica de las particiones (pendiente de una sesión nueva y de autorización explícita del propietario; no iniciada)

**Base:** commit «docs(impl-3): formalize CR-020 findings closure and D2 resolution» en `develop` sobre `82785a4` («docs(impl-3): preserve focused independent CR-020 reverification evidence»; `develop` = `origin/develop` en `82785a4` al iniciar); sin push (comprobar con `git status -sb`). **Aprobación del propietario (2026-11-25):** acepta la documentación de cierre, la conclusión de compatibilidad contractual y las desviaciones informadas, y autoriza un único commit documental; D4 bloqueada (se conserva la entrada histórica PENDIENTE); los documentos de disposición de N-1, N-2 y N-3 se conservan sin anotaciones de cierre. La entrada siguiente («sin commit») se conserva como histórica: la preservación quedó confirmada en `82785a4`. Contrato **v1.10**; `feature_list.json` **v1.22.0**.
**Decisiones del propietario (2026-11-25):** 16 elementos de CR-020 CERRADOS (QA-CR020-01..06; O3 y O4 con obligaciones abiertas; N-1 corregido y verificado; N-2 y N-3 con riesgos residuales aceptados; D-1..D-5) con el veredicto independiente CONFORME CON OBSERVACIONES; **CONF-009 RESOLVED**; **CONF-010 OPEN** (MEDIUM; mecanismo conforme con v1.10; O3 y O4 pendientes antes del pipeline); **D2 CERRADA: VERIFICADO CON OBSERVACIONES**. Compatibilidad contractual comprobada antes de aplicar (ver `progress.md`). El cierre de D2 no resuelve CONF-010, no cierra FEAT-017 (IN_PROGRESS) ni habilita el pipeline.
**Referencias:** `67195da` (consolidada), `f8e8861` (N-1), `06d55aa` (N-2), `95ae440` (N-3), `eac0fa7` (conciliación), `82785a4` (focalizada).
**Obligaciones conservadas:** O3 y O4 antes de habilitar el pipeline; S1–S4 (G6, Laptop B); P5 PENDIENTE con las condiciones de `IMPL-3_N-2_disposicion.md` §3 y `IMPL-3_N-3_disposicion.md` §4; N-2 denegaciones transitorias; N-3 excepción acotada; sin tamper-evidence; `confirmatory_status` consistente en HUMAN_REVIEW (ELIGIBLE_FOR_HUMAN_REVIEW no es aprobación); N-1 no retroactiva; `_marker_error` abierta; reevaluación de CONF-009 antes del cierre de FEAT-017. D3–D7 sin resolver; D4 bloqueada. FEAT, criterios, `evidence.covered`, gates y registro real (`07efad20…`) sin cambios.
**Verificación:** JSON válido; validadores → código 0; pruebas y sondas no reejecutadas (solo documental).
**Siguiente acción autorizada:** ninguna. Próximo punto de control: D3 (integridad histórica de las particiones), en una sesión nueva y solo con autorización explícita del propietario. Sin push. SNAP-0001 no creada; P5 no implementado; pipeline no habilitado.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: decisiones de cierre del propietario sobre CR-020, CONF-009, CONF-010 y D2 (no iniciadas)

**Base:** `eac0fa7` en `develop` (= `origin/develop` según la referencia local al auditar) más la preservación documental de la reverificación focalizada, **sin commit** (comprobar con `git status -sb`). Contrato **v1.10**; `feature_list.json` **v1.21.2** sin cambios.
**Reverificación independiente focalizada:** `harness/verification/IMPL-3_CR-020_reverificacion_focalizada.md` (scripts en `IMPL-3_CR-020_reverificacion_focalizada_sondas/`) — **CONFORME CON OBSERVACIONES**, sin disconformidades contractuales: N-1 conforme (corregido y verificado), disposiciones de N-2 y N-3 conformes, D-1..D-5 conformes. Informe aceptado por el propietario como evidencia; **no es cierre formal**.
**Recomendaciones del auditor (no decisiones):** ocho hallazgos originales, CONF-009 y D2 elegibles para cierre formal con obligaciones conservadas; CONF-010: mantener OPEN o cerrar solo trasladando O3/O4 a un control trazable previo al pipeline.
**Obligaciones conservadas:** O3 y O4 antes de habilitar el pipeline de evaluación; S1–S4; P5 PENDING con las condiciones de `IMPL-3_N-2_disposicion.md` §3 y `IMPL-3_N-3_disposicion.md` §4; `confirmatory_status` consistente en HUMAN_REVIEW; N-3 como excepción acotada; N-1 no retroactiva; observación de `_marker_error` abierta. FEAT-017 IN_PROGRESS; CONF-009 y CONF-010 OPEN; D2 pendiente de cierre; FEAT, criterios, conflictos y gates sin cambios.
**Verificación:** validadores → código 0; registro real `07efad20…` sin cambios; pruebas funcionales no reejecutadas (solo documental).
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario y su autorización de commit. D3–D7 no iniciadas.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: reverificación independiente focalizada de N-1 y revisión de N-2, N-3 y D-1..D-5 (no iniciada)

**Base:** commit «docs(impl-3): reconcile CR-020 reverification findings and dispositions» en `develop` (sin push; comprobar con `git status -sb`; antes del commit `develop` = `origin/develop` en `95ae440`). Contrato **v1.10**; `feature_list.json` **v1.21.2** (parche solo documental).
**Aceptación del propietario (2026-11-25):** conciliación documental D-1..D-5 aceptada y congelada en un commit. Es una aceptación **documental**: no es verificación independiente ni cierre formal.
**Distinción vigente:** corrección de implementación ≠ aceptación del propietario ≠ reverificación independiente ≠ cierre formal. N-1 corregido (`f8e8861`) y aceptado, pendiente de reverificación focalizada; N-2 (`06d55aa`) y N-3 (`95ae440`) aceptados como riesgos residuales, pendientes de revisión de sus disposiciones; D-1..D-5 conciliados, pendientes de revisión. Ningún hallazgo, D2, CONF-009, CONF-010 ni FEAT-017 está formalmente cerrado.
**Obligaciones conservadas:** O3 y O4 antes de habilitar el pipeline de evaluación; S1–S4; P5 PENDING con las condiciones de `IMPL-3_N-2_disposicion.md` §3 y `IMPL-3_N-3_disposicion.md` §4; `confirmatory_status` consistente en HUMAN_REVIEW; N-3 como excepción acotada; D2 pendiente de cierre. FEAT, criterios de aceptación, `evidence.covered`, conflictos y gates sin cambios.
**Verificación:** JSON válido; validadores → código 0; registro real `07efad20…` sin cambios; suite no reejecutada (solo documental).
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (la revisión independiente no está iniciada).

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: conciliación documental consolidada de D-1..D-5 (no iniciada)

**Base:** commit «docs(impl-3): record owner disposition of N-3 external rewrite risk» en `develop` (sin push; comprobar con `git status -sb`). Contrato **v1.10**; `feature_list.json` **v1.21.1**, sin cambios (se concilia en la reconciliación documental consolidada).
**Disposiciones del propietario de la reverificación consolidada:**
- **N-1:** CORREGIDO (`f8e8861`) y ACEPTADO; pendiente de reverificación independiente focalizada (`IMPL-3_N-1_correccion.md`).
- **N-2:** ACEPTADO (opción A; riesgo residual de disponibilidad); pendiente de revisión independiente focalizada de la disposición (`IMPL-3_N-2_disposicion.md`). Condición operativa para P5: confirmar corrupción persistente bajo bloqueo exclusivo o con escritores en reposo; un error transitorio no desencadena la recuperación.
- **N-3:** ACEPTADO (opción A; riesgo residual de integridad fuera del protocolo append-only; sin CR); pendiente de revisión independiente focalizada de la disposición (`harness/verification/IMPL-3_N-3_disposicion.md`). Excepción acotada a toda afirmación general de que todas las rutas del evaluador fallan cerrando o usan solo registros validados. Condiciones: sin reescritura/sustitución/truncamiento externos; una modificación externa sospechada impide confiar en resultados favorables hasta reconciliar; conservar el registro y aplicar la autorización de P5 (PENDING, sin implementar); se conserva la obligación de `confirmatory_status` consistente en HUMAN_REVIEW; ELIGIBLE_FOR_HUMAN_REVIEW no es aprobación. Sin tamper-evidence criptográfico.
**Evidencia:** validadores OK (código 0); sin pruebas ni sondas nuevas en las disposiciones de N-2 y N-3; registro real `07efad20…` sin cambios.
**Sin resolver:** D-1..D-5 (siguiente: conciliación documental consolidada, incluida `feature_list.json`), estado de cada hallazgo QA-CR020-01..06, O3 y O4 tras la reverificación, D2, CONF-009, CONF-010; observación separada de `_marker_error`. Obligaciones de O3/O4, S1–S4 y conciliación manual (P5) PENDING se conservan.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: evaluación de solo lectura de N-3 (no iniciada)

**Base:** commit «docs(impl-3): record owner disposition of N-2 concurrent read risk» en `develop` (sin push; comprobar con `git status -sb`). Contrato **v1.10**; `feature_list.json` **v1.21.1**, sin cambios (conciliación documental consolidada posterior).
**N-1:** CORREGIDO (`f8e8861`) y ACEPTADO por el propietario; pendiente de reverificación independiente focalizada.
**N-2:** ACEPTADO por el propietario (opción A: riesgo residual de disponibilidad; sin cambios funcionales, de pruebas ni contractuales); pendiente de revisión independiente focalizada de la disposición (`harness/verification/IMPL-3_N-2_disposicion.md`). **Condición operativa obligatoria para P5 (PENDING, sin autorizar su implementación):** confirmar la corrupción persistente con una lectura consistente bajo el bloqueo exclusivo o con los escritores en reposo; conservar el registro afectado como evidencia; autorización explícita del propietario por operación; un único error transitorio de lectura incompleta no desencadena la recuperación manual. Las cifras medidas constan solo en el informe consolidado preservado.
**Evidencia:** validadores OK (código 0); sin pruebas ni sondas nuevas; registro real `07efad20…` sin cambios.
**Sin resolver:** N-3 (siguiente; evaluación de solo lectura y decisión del propietario antes de cualquier cambio), D-1..D-5, D2, CONF-009, CONF-010; observación separada de `_marker_error`. Obligaciones de O3/O4, S1–S4 y conciliación manual PENDING se conservan.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente: evaluación y disposición del propietario de N-2 (no iniciada)

**Base:** commit «fix(research): validate mandatory deviation evidence before persistence» en `develop` (sin push; comprobar con `git status -sb`). Contrato **v1.10**; `feature_list.json` **v1.21.1**, sin cambios.
**N-1:** CORREGIDO y ACEPTADO por el propietario; **pendiente de reverificación independiente focalizada** (la aceptación no la sustituye). Detalle: `harness/verification/IMPL-3_N-1_correccion.md` (§7 limitaciones residuales conservadas; §8 aceptación).
**Evidencia:** 43 pruebas nuevas; suite 870 passed, 5 skipped; validadores OK; registro real `07efad20…` sin cambios.
**Sin resolver:** N-2 (siguiente; evaluación de solo lectura y decisión del propietario antes de cualquier cambio), N-3, D-1..D-5, D2, CONF-009, CONF-010; observación separada de `_marker_error`. Obligaciones de O3/O4, S1–S4 y conciliación manual PENDING se conservan.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario.

## PUNTO DE REANUDACIÓN (2026-11-25) — reverificación independiente consolidada PRESERVADA; esperar decisiones del propietario

**Base:** reverificación sobre `2625ee9`; evidencia preservada en el commit «docs(impl-3): preserve independent CR-020 consolidated reverification evidence» (sin push; comprobar con `git status -sb`). Contrato **v1.10**; `feature_list.json` **v1.21.1**, sin cambios.
**Resultado del revisor:** CONFORME CON OBSERVACIONES para QA-CR020-01..06, O3 y O4 (informe: `harness/verification/IMPL-3_CR-020_reverificacion_consolidada.md`; sondas y strace: `harness/verification/IMPL-3_CR-020_reverificacion_sondas/`). El propietario acepta la **recepción**; no es cierre de hallazgos, D2 ni conflictos.
**Sin resolver (decisión del propietario):** N-1 (el constructor de la DEVIATION solo se comprueba por `kind` y `config_id` en `begin_configuration_evaluation`), N-2 (lecturas sin `flock`: falsa corrupción transitoria), N-3 (vista mixta del evaluador solo ante reescritura fuera del protocolo append-only), D-1..D-5 (inconsistencias documentales), estado de cada hallazgo, D2, CONF-009, CONF-010.
**Se conservan abiertas:** obligaciones de O3 y O4 previas al pipeline; S1–S4 en el despliegue; conciliación manual PENDING.
**Evidencia:** suite 827 passed, 5 skipped (reverificación; no reejecutada para la preservación); validadores OK; registro real SHA-256 `07efad20…` sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario.

## PUNTO DE REANUDACIÓN (2026-11-25) — siguiente sesión: reverificación independiente consolidada de QA-CR020-01..06, O3 y O4 (no iniciada; requiere autorización expresa)

**Base:** commit «docs(impl-3): record owner disposition of QA-CR020-O4» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`). Contrato **v1.10** sin cambios; `feature_list.json` **v1.21.1** (v1.21.0 + conciliación aislada de `evidence.pending` de FEAT-017 para O3 y O4).
**Última evidencia:** suite funcional → 827 passed, 5 skipped (registrada en `9026797`; no reejecutada, solo cambios documentales). JSON válido; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`).

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar): QA-CR020-01..06 y O3 resueltos o aceptados por el propietario; **QA-CR020-O4: ACEPTADO por el propietario (opción A, 2026-11-25); todos pendientes de reverificación independiente.** Ninguna observación queda sin disposición.

**QA-CR020-O4** (`harness/verification/IMPL-3_QA-CR020-O4_evaluacion.md`): riesgo residual metodológico aceptado, sin cambios funcionales, de pruebas ni contractuales. El registro del inicio de evaluación sigue sujeto a las puertas de ciclo de vida y autorización; la recuperación de Train+Val de un par certificado no tiene puerta de estado adicional; la recuperación repetida no incrementa el conteo; el cargador no distingue recuperación de evidencia de reevaluación; los cambios sustantivos bajo un `config_id` existente no se garantiza detectarlos; evaluación basada en inspección de código, sin pruebas nuevas. **Obligación operativa abierta (no autoriza implementación):** antes de habilitar el pipeline de evaluación de investigación, verificar que las configuraciones sustantivamente modificadas no puedan tratarse como repeticiones idénticas para eludir la contabilidad. Distinta de la O4 antigua (conservación versionada de la evidencia).

**Obligación de reverificación independiente de QA-CR020-O4:** registro fiel a la evaluación y a las fuentes; la obligación operativa consta como abierta, no implementada; no se presenta evidencia ejecutada donde solo hubo inspección de código; no se confunde con la O4 antigua. Las obligaciones de QA-CR020-01..06 y O3 se conservan en los puntos de reanudación anteriores.

**Estado general:** D2 pendiente de cierre; CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (la reverificación consolidada no está iniciada).

## PUNTO DE REANUDACIÓN (2026-11-24) — siguiente sesión: QA-CR020-O4 (sustituido por el punto de reanudación superior)

**Base:** commit «docs(impl-3): record owner disposition of QA-CR020-O3» en `develop` (HEAD). Al empezar esta sesión se comprobó localmente, sin `fetch`, que `develop` = `origin/develop` en `c70f593` (0 por delante, 0 por detrás); la indicación «1 commit por delante» de puntos anteriores quedó desactualizada. Comprobar el estado actual con `git status -sb`. Contrato **v1.10** sin cambios; `feature_list.json` **v1.20.0**.
**Última evidencia:** suite funcional → 827 passed, 5 skipped (registrada en `9026797`; no reejecutada, solo cambios documentales). Pruebas dirigidas de O3 (`-k "tc_ml_020 or tc_ml_021"` → 26 passed; `-k a2` → 7 passed). JSON válido; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`, sin reducciones).

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):
- QA-CR020-01..05: CORREGIDOS o verificados y aceptados por el propietario; pendientes de reverificación independiente (obligaciones en el punto siguiente).
- QA-CR020-06: conciliado, verificado por el implementador y aceptado; pendiente de reverificación independiente.
- **QA-CR020-O3: ACEPTADO por el propietario (cuatro disposiciones); pendiente de reverificación independiente** (`harness/verification/IMPL-3_QA-CR020-O3_evaluacion.md`). Condiciones vigentes: verificar la contabilidad correcta de los escenarios de costes antes de habilitar el pipeline de evaluación de investigación; limitación permanente de la evidencia previa de A2 (no reconstruir ni presentar evidencia posterior como original); toda reducción futura de procedencia exige evidencia que respalde `DOCUMENTED_NOT_EVALUATED` y **no se autoriza ninguna reducción del registro real**; el comportamiento Unicode de la línea de autorización no está verificado ni certificado.
- **QA-CR020-O4: SIN RESOLVER — siguiente trabajo.**

**QA-CR020-O4 (OBS, nota; para la sesión siguiente):** según el informe §3, el cargador no considera el estado del experimento: un par registrado puede seguir cargando Train+Val cuando el experimento ya está en un estado terminal (`src/swingpilot/research/partitions.py`; el informe cita `:129-151`, que puede haberse desplazado). El informe señala que el contrato no lo prohíbe. Antes de cualquier cambio: evaluación de solo lectura y decisión del propietario; no inferir requisitos nuevos; no ampliar a otros hallazgos.

**Obligación de reverificación independiente de QA-CR020-O3:** el registro de la disposición es fiel a la evaluación y a la evidencia citada; ningún documento presenta evidencia posterior como original (A2); el registro real no tiene reducciones; la condición de TC-ML-020 consta como obligación abierta; el comportamiento Unicode no se presenta como certificado. Las demás obligaciones (QA-CR020-01..06) se conservan en el punto de reanudación anterior.

**Estado general:** D2 pendiente de cierre; CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (ninguna implementación ni enmienda documental autorizada para QA-CR020-O4).

## PUNTO DE REANUDACIÓN (2026-11-24) — siguiente sesión: QA-CR020-O3 (sustituido por el punto de reanudación superior)

**Base:** commit «docs(impl-3): reconcile CR-020 implementation evidence and resolve QA-CR020-06» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`). Contrato **v1.10** y `feature_list.json` **v1.19.0** sin cambios.
**Última evidencia:** suite funcional → 827 passed, 5 skipped (registrada en `9026797`; no reejecutada desde entonces, solo cambios documentales). Tras la conciliación de QA-CR020-06: JSON válido; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`).

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):

| Hallazgo | Estado |
|---|---|
| QA-CR020-01 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-01_correccion.md`) |
| QA-CR020-02 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-02_correccion.md` §9) |
| QA-CR020-03 | CORREGIDO y aceptado; pendiente de reverificación independiente (CR-021; `IMPL-3_CR-021_implementacion.md` §10) |
| QA-CR020-04 | VERIFICADO y aceptado; pendiente de reverificación independiente (CR-022, DEC-024; `IMPL-3_CR-022_caracterizacion.md` §6) |
| QA-CR020-05 | RESUELTO por solapamiento con CR-021, VERIFICADO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-05_caracterizacion.md` §9) |
| QA-CR020-06 | CONCILIADO documentalmente, VERIFICADO por el implementador y aceptado; pendiente de reverificación independiente (`feature_list.json` v1.19.0, FEAT-017 `qa_reviews`; `progress.md`) |
| **QA-CR020-O3** | **SIN RESOLVER — siguiente trabajo; ninguna implementación ni enmienda documental autorizada** |
| QA-CR020-O4 | Sin resolver (observación) |

**QA-CR020-O3 (para la sesión siguiente; OBS, evidencia insuficiente o por construcción):** según el informe §3: (a) TC-ML-020, «escenario puro de costes o corrida idéntica no suma», se cumple solo porque quien llama no registra esas corridas; ningún mecanismo lo impone (el informe cita `test_trials_accounting.py:160-165`; la línea puede haberse desplazado); (b) la evidencia «antes de la corrección» de A2 (7 failed) no es reproducible desde el historial (A2 se aplicó antes de `824fae8`; referencia cruzada en `feature_list.json`, `cr020.evidence`); (c) P10: una reducción de procedencia se acepta con la misma lista de evidencia que la anterior; (d) P11: se tolera espacio final o CRLF en `AUTORIZA: PROCEDENCIA` (el revisor no lo considera defecto). Antes de cualquier cambio: evaluación de solo lectura y decisión del propietario; no ampliar a QA-CR020-O4.

**Obligaciones de reverificación independiente pendientes (consolidadas; para una QA posterior):**
- QA-CR020-01 y QA-CR020-03: relación escritura/`fsync` de la evidencia sobre el mismo descriptor nuevo; orden de emisión del marcador; acceso real a datos entre procesos, no solo predicados de conteo.
- QA-CR020-02: coherencia entre la consulta (`confirmatory_status` / `confirmatory_findings`) y el evaluador; vinculación del preregistro congelado; validación del hash del archivo de resultados de la selección; ausencia de certificación confirmatoria falsa.
- QA-CR020-04: coincidencia por par exacto; precedencia del caso 3; separación de `provenance_id`; deduplicación por par.
- QA-CR020-05: cualquier línea que no es un objeto (cualquier posición y tipo JSON, también entre lecturas) → veredicto estructurado INCONCLUSIVE sin excepción, sin conteo y sin modificar el registro; ninguna ruta del evaluador usa registros no validados.
- QA-CR020-06: exactitud documental de FEAT-017 en `feature_list.json` v1.19.0 y de las notas añadidas a CONF-009 y CONF-010 frente a la evidencia citada; preservación de la evidencia histórica (`evidence.covered`, entradas anteriores del registro de conflictos, informes y sondas); coherencia de los estados registrados (FEAT, conflictos, D2, hallazgos) entre `feature_list.json`, `conflict_register.md`, `progress.md` y `session-handoff.md`.

**Estado general:** D2 pendiente de cierre; CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (ninguna implementación ni enmienda documental autorizada para QA-CR020-O3).

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-06: conciliación documental aplicada, aceptada por el propietario y en commit (sustituido por el punto de reanudación superior)

**Base:** `9026797` en `develop`. **Sincronización comprobada el 2026-11-24 (`git status -sb`): `develop` = `origin/develop`**; la indicación «1 commit por delante» del punto de reanudación siguiente estaba desactualizada. Cambios sin commit. Contrato **v1.10** sin cambios.
**Autorización:** enmiendas A1–A5 y B1–B11 del inventario de QA-CR020-06, con las decisiones del propietario (detalle en `progress.md`).
**Hecho:** `feature_list.json` **v1.19.0** (solo FEAT-017: `evidence.pending`, `contract_sections`, `implementation_paths` + nota, `test_paths`, `qa_reviews` con entrada de alcance CR-020, `cr020` con `amended_by` y `evidence`, `cr021`); `implementation/conflict_register.md` con notas añadidas en CONF-009 (verificación independiente; vigencia de la frase de severidad) y CONF-010 (seguimiento), sin reescribir entradas ni reevaluar severidades.
**Verificar:** JSON válido; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK; estados de FEAT idénticos a `HEAD`; `evidence.covered` sin cambios. Suite funcional no ejecutada (no autorizada).
**Archivos (sin commit):** `feature_list.json`, `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`.
**Fuera de alcance (sin cambios):** cabeceras de estado de CR-020/021/022 (incluida la última línea de CR-020 §I), CONF-010 l. «Solución propuesta», `notes` de FEAT-017, `metadata.description`; QA-CR020-O3 y O4.
**Estado:** QA-CR020-06 PENDIENTE de aceptación del propietario; QA-CR020-01..05 aceptados y pendientes de reverificación independiente (obligaciones en el punto siguiente); QA-CR020-O3 y O4 sin resolver. D2 pendiente de cierre; CONF-009 y CONF-010 OPEN; CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS; gates sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario (commit y push solo con su indicación).

## PUNTO DE REANUDACIÓN (2026-11-24) — siguiente sesión: QA-CR020-06 (sustituido por el punto de control superior)

**Base:** commit «test(impl-3): characterize QA-CR020-05 structured corruption verdict» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`; **desactualizado:** el 2026-11-24 se comprobó `develop` = `origin/develop`, ver el punto superior). Contrato **v1.10** sin cambios.
**Última evidencia:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 827 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`). Pruebas no reejecutadas para el commit.

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):

| Hallazgo | Estado |
|---|---|
| QA-CR020-01 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-01_correccion.md`) |
| QA-CR020-02 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-02_correccion.md` §9) |
| QA-CR020-03 | CORREGIDO y aceptado; pendiente de reverificación independiente (CR-021; `IMPL-3_CR-021_implementacion.md` §10) |
| QA-CR020-04 | VERIFICADO y aceptado; pendiente de reverificación independiente (CR-022, DEC-024; `IMPL-3_CR-022_caracterizacion.md` §6) |
| QA-CR020-05 | RESUELTO por solapamiento con CR-021, VERIFICADO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-05_caracterizacion.md` §9) |
| **QA-CR020-06** | **SIN RESOLVER — siguiente trabajo; ninguna implementación ni corrección documental autorizada** |
| QA-CR020-O3, O4 | Sin resolver (observaciones) |

**QA-CR020-06 (para la sesión siguiente; MENOR, trazabilidad):** según el informe, `feature_list.json` no refleja la implementación de CR-020 («TC-ML-020..024 sin implementar»; `cr020.scope`: mecanismo y procedencia «sin implementar ni escribir») ni consta su evidencia de ejecución, que AGENTS.md exige para la aceptación; además, el texto de severidad de CONF-009 en `implementation/conflict_register.md` describe todavía el conteo por identificador. Las líneas citadas por el informe (`feature_list.json:1720`, `:1768`; `conflict_register.md:154`) pueden haberse desplazado. Desde la QA se añadieron más elementos sin reflejar: el bloque `cr021` («implemented: NO») y la evidencia de QA-CR020-01..05, CR-021, CR-022 y DEC-024. `feature_list.json` está en v1.18.0 y no se ha tocado. Antes de cualquier cambio: evaluación de solo lectura y decisión del propietario sobre el alcance; no cambiar estados de FEAT ni cerrar D2, CONF-009 o CONF-010 sin su decisión.

**Obligaciones de reverificación independiente pendientes** (para una QA posterior):
- QA-CR020-01 y QA-CR020-03: relación escritura/`fsync` de la evidencia sobre el mismo descriptor nuevo; orden de emisión del marcador; acceso real a datos entre procesos, no solo predicados de conteo.
- QA-CR020-02: coherencia entre la consulta (`confirmatory_status` / `confirmatory_findings`) y el evaluador; vinculación del preregistro congelado; validación del hash del archivo de resultados de la selección; ausencia de certificación confirmatoria falsa.
- QA-CR020-04: coincidencia por par exacto; precedencia del caso 3; separación de `provenance_id`; deduplicación por par.
- QA-CR020-05: cualquier línea que no es un objeto (cualquier posición y tipo JSON, también entre lecturas) → veredicto estructurado INCONCLUSIVE sin excepción, sin conteo y sin modificar el registro; ninguna ruta del evaluador usa registros no validados (las variantes y la corrupción entre lecturas solo constan como observaciones de solo lectura).

**Estado general:** CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); CONF-011 RESOLVED; D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (ninguna implementación ni corrección documental autorizada para QA-CR020-06).

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-05: caracterización ejecutada, aceptada y en commit (sustituido por el punto de reanudación superior)

**Base:** `45bc540` en `develop` (= `origin/develop`). Cambios sin commit. Contrato **v1.10** sin cambios.
**Disposición aceptada:** el defecto original quedó resuelto como consecuencia de CR-021 (P1); la obligación vinculante del veredicto estructurado es CR-020 §C.4.3 (CR-021 P1 admite «INCONCLUSIVE o error»; rige la más estricta, sin enmienda).
**Hecho:** prueba de caracterización `tests/unit/test_trials_accounting.py::test_qa_cr020_05_non_object_line_gives_structured_inconclusive_verdict` → 1 passed; discrimina el fallo original (un mutante que propaga el error la hace fallar, mientras la fila `non_object_line` de la matriz P1 sigue pasando). Evidencia de solo lectura conservada (variantes y corrupción entre lecturas). Detalle: `harness/verification/IMPL-3_QA-CR020-05_caracterizacion.md`.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 827 passed, 5 skipped; validadores OK; registro real sin cambios (`07efad20…`).
**Archivos (sin commit):** `tests/unit/test_trials_accounting.py` (una prueba añadida), `harness/verification/IMPL-3_QA-CR020-05_caracterizacion.md` (nuevo), `progress.md`, `session-handoff.md`.
**Obligación de reverificación independiente (QA-CR020-05):** cualquier línea que no es un objeto (cualquier posición y tipo JSON), también entre lecturas → veredicto estructurado INCONCLUSIVE, sin excepción, sin conteo y sin modificar el registro; ninguna ruta del evaluador usa registros no validados (documento §7). Siguen pendientes las de QA-CR020-01..04 (punto de control siguiente).
**Estado:** QA-CR020-05 pendiente de la aceptación del propietario; QA-CR020-01..04 pendientes de reverificación independiente; QA-CR020-06, O3 y O4 sin resolver. CONF-009 y CONF-010 OPEN; CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS; `feature_list.json` sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario.

## PUNTO DE CONTROL (2026-11-24) — reanudación en QA-CR020-05 (sustituido por el punto de reanudación superior)

**Base:** commit «test(impl-3): characterize CR-022 exact-pair relevance and resolve CONF-011» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`). Contrato **v1.10** sin cambios.
**Última evidencia:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 826 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`). Pruebas no reejecutadas para el commit.

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):

| Hallazgo | Estado |
|---|---|
| QA-CR020-01 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-01_correccion.md`) |
| QA-CR020-02 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-02_correccion.md` §9) |
| QA-CR020-03 | CORREGIDO y aceptado; pendiente de reverificación independiente (CR-021; `IMPL-3_CR-021_implementacion.md` §10) |
| QA-CR020-04 | VERIFICADO por el implementador y aceptado; pendiente de reverificación independiente (CR-022, DEC-024; `IMPL-3_CR-022_caracterizacion.md` §6) |
| **QA-CR020-05** | **SIN RESOLVER — siguiente trabajo; ninguna implementación autorizada** |
| QA-CR020-06 | Sin resolver; `feature_list.json` desactualizado (incluido el bloque `cr021`) |
| QA-CR020-O3, O4 | Sin resolver (observaciones) |

**QA-CR020-05 (para la sesión siguiente; OBS, robustez):** con una línea JSON válida que no es un objeto (p. ej. `[1, 2]`), `evaluate()` lanzaba `AttributeError` en lugar de devolver INCONCLUSIVE (CR-020 §C.4.3). El informe cita `trials.py:49-50`, `:89-90` y `:118-119` (usos de `r.get` sin comprobar el tipo); hoy están en `trials.py:49`, `:92` y `:123`. Reproducción: sonda P6 de `harness/verification/IMPL-3_CR-020_QA_sondas.py`. **Solapamiento conocido:** desde CR-021 (P1), la lectura validada del registro trata esa línea como corrupción, y la sonda P6 da ahora INCONCLUSIVE (`IMPL-3_CR-021_implementacion.md`). Antes de cualquier cambio: evaluación de solo lectura y decisión del propietario sobre si el hallazgo queda cubierto por P1 o exige algo más; no cerrarlo sin decisión ni ampliar a otros hallazgos.

**Obligaciones de reverificación independiente pendientes** (para una QA posterior):
- QA-CR020-01 y QA-CR020-03: relación escritura/`fsync` de la evidencia sobre el mismo descriptor nuevo; orden de emisión del marcador; acceso real a datos entre procesos, no solo predicados de conteo.
- QA-CR020-02: coherencia entre la consulta (`confirmatory_status` / `confirmatory_findings`) y el evaluador; vinculación del preregistro congelado; validación del hash del archivo de resultados de la selección; ausencia de certificación confirmatoria falsa.
- QA-CR020-04: coincidencia por par exacto; precedencia del caso 3; separación de `provenance_id`; deduplicación por par.

**Estado general:** CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); CONF-011 RESOLVED; D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios; `feature_list.json` sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (ninguna implementación autorizada para QA-CR020-05).

## PUNTO DE CONTROL (2026-11-24) — pruebas de caracterización de CR-022 §F ejecutadas, aceptadas y en commit; CONF-011 RESOLVED (sustituido por el punto de reanudación superior)

**Base:** `4fbeecb` en `develop` (= `origin/develop`, sincronización confirmada por el propietario). Cambios sin commit. Contrato **v1.10** sin cambios.
**Hecho:** cuatro pruebas de caracterización de TC-ML-024 / CR-022 §F en `tests/unit/test_trials_accounting.py` (F.1 P5; F.2 variante con DEVIATION; F.3 `provenance_id`; F.4 par citado dos veces) → 4 passed, sin discrepancias. Mutantes temporales: cada prueba falla ante la violación de su propiedad. Detalle: `harness/verification/IMPL-3_CR-022_caracterizacion.md`.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 826 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK; `.venv/bin/pytest -q -p no:cacheprovider tests/unit/test_trials_accounting.py -k cr022` → 4 passed. Registro real sin cambios (`07efad20…`).
**Archivos (sin commit):** `tests/unit/test_trials_accounting.py` (solo adiciones), `harness/verification/IMPL-3_CR-022_caracterizacion.md` (nuevo), `progress.md`, `session-handoff.md`.
**Estado:** CONF-011 OPEN y QA-CR020-04 pendiente hasta la revisión de esta evidencia por el propietario. QA-CR020-01, 02 y 03 pendientes de reverificación independiente; 05, 06, O3 y O4 sin resolver. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; `feature_list.json` sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario.

## PUNTO DE CONTROL (2026-11-24) — pruebas de caracterización de CR-022 §F autorizadas en alcance (sustituido por el punto de reanudación superior)

**Base:** commit «docs(impl-3): approve CR-022 exact-pair relevance under DEC-024» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`). Contrato **v1.10** congelado (CR-022, DEC-024).
**Última evidencia funcional:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 822 passed, 5 skipped (en `d84535a`; CR-022 no cambió código ni pruebas). Validadores OK antes del commit. Registro real sin cambios (SHA-256 `07efad20…`).

**Objetivo siguiente (aprobado en alcance por DEC-024; implementación y ejecución pendientes de autorización separada y expresa):** cuatro pruebas de caracterización de TC-ML-024 (CR-022 §F) en `tests/unit/test_trials_accounting.py`, solo con datos sintéticos:
1. P5: dos configuraciones posteriores de `Y`; la selección cita solo una → la otra es NO RELEVANTE; `N_eval` = `N_pre` + 1.
2. Variante: una DEVIATION posterior a ambas cita solo una → la otra es INDETERMINADA; veredicto INCONCLUSIVE (`SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`).
3. Una referencia `provenance_id` en la selección no hace relevante ninguna prueba posterior.
4. Un par citado por dos puntos de decisión suma una sola vez.
Deben **pasar** con el código actual (son de caracterización, no regresiones); no se adapta ninguna prueba existente ni se modifica código funcional. La evidencia se revisa antes de cerrar CONF-011 y de verificar QA-CR020-04.

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar): QA-CR020-01, 02 y 03 corregidos y aceptados, pendientes de reverificación independiente (obligaciones en los puntos de control anteriores); **QA-CR020-04 pendiente de la evidencia de caracterización** (aclaración contractual CR-022 aplicada; implementación conforme, CR-022 §E); QA-CR020-05, 06, O3 y O4 sin resolver.
**Estado general:** CONF-009, CONF-010 y CONF-011 OPEN (CONF-011, LOW, hasta revisar la evidencia de caracterización); D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios; `feature_list.json` sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar la autorización expresa del propietario para implementar y ejecutar las pruebas de caracterización.

## PUNTO DE CONTROL (2026-11-24) — CR-022 APROBADA (DEC-024); contrato v1.10 aplicado y aceptado; congelado en commit (sustituido por el punto de reanudación superior)

**Base:** `d84535a` en `develop` (= `origin/develop`). Cambios contractuales y documentales sin commit. Contrato **v1.10** (CR-022, DEC-024) aplicado; congelarlo requiere la revisión del propietario y su indicación de commit.
**Aplicado:** REQ-G-P17 (frase CR-022) y TC-ML-024 (entradas y resultado esperado); cabeceras v1.10 en los cinco documentos de `implementation/`; CR-020 §J (nota de vigencia); CR-022 APROBADA (§J); DEC-024 (nuevo); CONF-011 con severidad LOW confirmada. **Validadores:** OK. Suite no ejecutada (sin cambios de código ni de pruebas).
**Archivos (sin commit):** `docs/decisions/DEC-024_aprobacion-cr022-relevancia-par-exacto.md` (nuevo), `harness/change_requests/CR-022_relevancia-por-par-exacto.md` (nuevo), `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` (§J añadida), `implementation/{requirements,test_plan,architecture,api_contracts,data_flow,conflict_register}.md`, `progress.md`, `session-handoff.md`.
**Se conservan:** gramática de `informed_by`, semántica de `provenance_id`, `N_pre`, `N_eval`, deduplicación por par, carácter confirmatorio y cálculo estadístico. La implementación actual ya cumple CR-022 (§E).
**Pruebas de caracterización (CR-022 §F, 1–4: P5; variante con DEVIATION; `provenance_id`; par citado dos veces):** aprobadas en alcance; implementación y ejecución **diferidas** a una autorización separada, después de congelar este punto de control. Deben pasar con el código actual (no son regresiones).
**Estado:** CONF-011 OPEN hasta que se produzca y revise la evidencia de caracterización; QA-CR020-04 pendiente de verificación. QA-CR020-01, 02 y 03 pendientes de reverificación independiente; 05, 06, O3 y O4 sin resolver. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; `feature_list.json` sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario. **Siguiente objetivo previsto** (requiere autorización expresa): congelar el contrato v1.10 (commit) y después implementar y ejecutar las pruebas de caracterización de CR-022 §F.

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-04: CR-022 PROPUESTA y CONF-011 registrado (sustituido por el punto de reanudación superior)

**Base:** `d84535a` en `develop` (= `origin/develop`). Cambios documentales sin commit. Contrato **v1.9** sin cambios.
**Decisión del propietario (2026-11-24):** opción A (referencias al par exacto); se rechaza la atribución implícita a nivel de experimento; referencias explícitas a experimentos diferidas.
**Preparado:** `harness/change_requests/CR-022_relevancia-por-par-exacto.md` (PROPUESTA) y CONF-011 en `implementation/conflict_register.md` (OPEN; severidad LOW propuesta). La implementación actual ya cumple la aclaración (CR-022 §E): sin cambio de código.
**Archivos (sin commit):** CR-022 (nuevo), `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`.
**Decisiones pendientes del propietario:** CR-022 §I (aprobación, aplicación al contrato v1.10 con su documento de decisión, pruebas de caracterización de §F, severidad de CONF-011).
**Estado:** QA-CR020-04 sin resolver hasta que la aclaración se apruebe y se verifique. Los demás estados no cambian respecto del punto siguiente (QA-CR020-01, 02 y 03 pendientes de reverificación independiente; 05, 06, O3 y O4 sin resolver). CONF-009, CONF-010 y CONF-011 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario.

## PUNTO DE CONTROL (2026-11-24) — reanudación en QA-CR020-04 (sustituido por el punto de reanudación superior)

**Base:** commit «fix(impl-3): resolve QA-CR020-02 confirmatory status consistency» en `develop` (HEAD; 1 commit por delante de `origin/develop` hasta que el propietario haga push; comprobar con `git status -sb`). Contrato **v1.9** sin cambios.
**Última evidencia:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 822 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`). Pruebas no reejecutadas para el commit.

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):

| Hallazgo | Estado |
|---|---|
| QA-CR020-01 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-01_correccion.md`) |
| QA-CR020-02 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-02_correccion.md` §9) |
| QA-CR020-03 | CORREGIDO y aceptado; pendiente de reverificación independiente (CR-021; `IMPL-3_CR-021_implementacion.md` §10) |
| **QA-CR020-04** | **SIN RESOLVER — siguiente trabajo; ninguna implementación autorizada** |
| QA-CR020-05 | Sin resolver; solapamiento con P1 de CR-021 (no cerrar sin decisión) |
| QA-CR020-06 | Sin resolver; `feature_list.json` desactualizado (incluido el bloque `cr021`) |
| QA-CR020-O3, O4 | Sin resolver (observaciones) |

**QA-CR020-04 (para la sesión siguiente):** ambigüedad contractual. CR-020 §C.4.2, caso 2: una prueba posterior `T` es RELEVANTE si un punto de decisión de X «cita en `informed_by` el experimento o el par de `T`»; el código solo reconoce la cita del par exacto (`src/swingpilot/research/trials.py:129-139`; el informe cita `:126-133`, desplazadas por la corrección de QA-CR020-02). Reproducción: sonda P5 de `harness/verification/IMPL-3_CR-020_QA_sondas.py` (`N_eval` = 2 frente a 3 con la lectura literal). La interpretación implementada es la menos conservadora. Requiere aclaración del propietario antes de cualquier cambio; no ampliar a otros hallazgos.

**Obligaciones de reverificación independiente pendientes** (para una QA posterior):
- QA-CR020-01 y QA-CR020-03: relación escritura/`fsync` de la evidencia sobre el mismo descriptor nuevo; orden de emisión del marcador; acceso real a datos entre procesos, no solo predicados de conteo.
- QA-CR020-02: coherencia entre la consulta (`confirmatory_status` / `confirmatory_findings`) y el evaluador; vinculación del preregistro congelado; validación del hash del archivo de resultados de la selección; ausencia de certificación confirmatoria falsa.

**Estado general:** CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario (ninguna implementación autorizada para QA-CR020-04).

**Aceptación del propietario — corrección de QA-CR020-02 (2026-11-24):** aprobada bajo el contrato v1.9 (detalle en `IMPL-3_QA-CR020-02_correccion.md` §9 y `progress.md`). Commit de los nueve archivos, sin push.

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-02 CORREGIDO (aceptado por el propietario y en commit; ver el punto de reanudación superior)

**Base:** `0051014` en `develop` (= `origin/develop`; la indicación previa de «1 commit por delante» estaba desactualizada y se corrigió abajo). Cambios sin commit. Contrato **v1.9** sin cambios.
**Autorización:** corrección de QA-CR020-02 bajo el contrato v1.9, opción A (no verificable → `PreregistrationError`).
**Hecho:** `confirmatory_status` aplica las causas contractuales de pérdida (diseño tras la exposición; par no planificado, conste o no su DEVIATION; selección distinta de la regla congelada; desviación de `candidate_selection_rule` en cualquier momento, CR-020 §C.3.4, sin bloqueo contractual). Pérdida demostrada → `False`; no verificable → `ConfirmatoryStatusUnverifiable`. El evaluador conserva sus códigos y su orden. Detalle: `harness/verification/IMPL-3_QA-CR020-02_correccion.md`.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 822 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK; `tests/unit/test_qa_cr020_02.py` → 11 passed (10 failed frente a `0051014`, 6 de ellos fallos de comportamiento genuinos). Registro real sin cambios (`07efad20…`).
**Archivos (sin commit):** `src/swingpilot/research/{preregistration,trials}.py`, `research/README.md`, `tests/unit/test_qa_cr020_02.py` (nuevo), `tests/unit/test_research.py` y `tests/unit/test_cr021_durability.py` (solo entradas de verificación), `harness/verification/IMPL-3_QA-CR020-02_correccion.md` (nuevo), `progress.md`, `session-handoff.md`.
**Cambio de uso:** tras la selección de candidata, la consulta de HUMAN_REVIEW debe pasar `preregistration` y `selection_inputs`; la propiedad `FrozenPreregistration.confirmatory` lanza `ConfirmatoryStatusUnverifiable` en ese caso si no hay pérdida demostrada.
**Pendiente:** QA-CR020-01 y 03 pendientes de reverificación independiente (obligaciones en el punto anterior); QA-CR020-02 pendiente de revisión del propietario y de reverificación independiente; QA-CR020-04, 05, 06, O3 y O4 sin resolver. CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; `feature_list.json` sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario (commit y push solo con su indicación).

## PUNTO DE CONTROL (2026-11-24) — reanudación en QA-CR020-02 (sustituido por el punto de reanudación superior)

**Base:** commit «fix(impl-3): implement CR-021 durable evaluation authorization» en `develop` (publicado: `develop` = `origin/develop`, comprobado el 2026-11-24; corrige la indicación anterior «1 commit por delante», que estaba desactualizada). Árbol limpio. Contrato **v1.9** congelado (DEC-023).
**Última evidencia:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 811 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real sin cambios (SHA-256 `07efad20…`; H_doc 4, H_bound 4, E 0, G 8).

**Cerrado en diseño y aprobado — NO reabrir:** CR-021 revisión 2 (DEC-023): `EVALUATION_PERSISTED`, I2a/I2b, R2, copias idénticas, duplicados conflictivos Fail-Closed, P1–P5. Implementación aceptada por el propietario (`harness/verification/IMPL-3_CR-021_implementacion.md` §10). Cualquier cambio de ese diseño exige una CR nueva.

**Estado de los hallazgos de la QA independiente de CR-020** (`harness/verification/IMPL-3_CR-020_QA_independiente.md`, sin modificar):

| Hallazgo | Estado |
|---|---|
| QA-CR020-01 | CORREGIDO y aceptado; pendiente de reverificación independiente (`IMPL-3_QA-CR020-01_correccion.md`) |
| **QA-CR020-02** | **SIN RESOLVER — siguiente trabajo, requiere autorización expresa** |
| QA-CR020-03 | CORREGIDO y aceptado; pendiente de reverificación independiente (CR-021; `IMPL-3_CR-021_implementacion.md`) |
| QA-CR020-04 | Sin resolver (ambigüedad contractual: relevancia por par o por experimento) |
| QA-CR020-05 | Sin resolver; solapamiento: P1 de CR-021 ya hace que una línea que no es objeto dé INCONCLUSIVE (no cerrar sin decisión) |
| QA-CR020-06 | Sin resolver; `feature_list.json` desactualizado (incluido el bloque `cr021`, «implemented: NO») |
| QA-CR020-O3, O4 | Sin resolver (observaciones) |

**QA-CR020-02 (para la sesión siguiente):** `preregistration.confirmatory_status()` (`src/swingpilot/research/preregistration.py:556`) solo considera las desviaciones de campos de diseño posteriores a la exposición OOS. No aplica la lectura estricta de REQ-G-103 v1.8/v1.9 que mantuvo el propietario (configuración no planificada o selección fuera de la regla → no confirmatorio). El evaluador sí la aplica (`src/swingpilot/research/trials.py:79-86` y `:113`). Reproducción: sondas P2 y P3 de `harness/verification/IMPL-3_CR-020_QA_sondas.py` (`confirmatory = True` con INCONCLUSIVE del evaluador). Riesgo: es la consulta prevista para HUMAN_REVIEW (ORQ-017-01, O2). Antes de corregir: confirmar con el propietario el alcance (solo `confirmatory_status` o también sus consumidores) y si hace falta aclaración contractual; no ampliar a otros hallazgos.

**Obligaciones de reverificación independiente pendientes** (QA-CR020-01 y QA-CR020-03; para una QA posterior, no para la corrección de QA-CR020-02): relación escritura/`fsync` de la evidencia sobre el mismo descriptor nuevo; orden de emisión del marcador; acceso real a datos entre procesos, no solo predicados de conteo.

**Estado general:** CONF-009 y CONF-010 OPEN (CONF-009 con reevaluación obligatoria antes del cierre de FEAT-017); D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Restricciones vigentes:** sin particiones reales, experimentos, SNAP-0001 ni IA; registro real solo lectura; commit y push solo con indicación del propietario.
**Siguiente acción autorizada:** ninguna. Esperar la autorización expresa del propietario para QA-CR020-02.

## PUNTO DE CONTROL (2026-11-24) — CR-021 APROBADA (DEC-023); contrato v1.9 congelado en develop (sin implementar), sin push

**Aceptación del propietario (2026-11-24):** aplicación documental aceptada y contrato v1.9 congelado. Comprobación semántica de REQ-G-104: aclaración mínima («…de la evidencia certificada (no del marcador; …)») para no contradecir R2; validadores OK; registrado en DEC-023. Commit de los 13 archivos, sin push. **Siguiente acción autorizada:** ninguna; esperar instrucciones del propietario.

**Base:** `fde522c` (`develop` = `origin/develop`). **Decisión:** DEC-023.
**Aplicado:** contrato v1.9 (REQ-G-104, REQ-G-P17, TC-ML-020, TC-ML-023 y cabeceras); CR-021 APROBADA (§L); nota de vigencia en CR-020 (§I; sustitución sin reescritura); `feature_list.json` v1.18.0 (bloque `cr021`: requisitos aprobados frente a comportamiento no implementado); historial de CONF-010.
**No implementado:** CR-021 completa. El código de `fde522c` sigue reproduciendo QA-CR020-03 (`harness/verification/IMPL-3_QA-CR020-03_reproduccion.py`).
**Obligaciones de implementación (requieren autorización):** protocolo CR-021 §D.4–§D.5; P1 demostrada en todas las rutas de lectura, escritura, acceso y evaluación (no basta el salto de línea final); adaptación de las pruebas ejecutables de CR-021 §G.5; regresiones que fallen con `fde522c`.
**Validadores:** OK. Suite no ejecutada.
**Archivos (sin commit):** `docs/decisions/DEC-023_…md` (nuevo), `harness/change_requests/CR-021_…md` (nuevo), `harness/change_requests/CR-020_…md` (§I añadida), `harness/verification/IMPL-3_QA-CR020-03_reproduccion.py` (nuevo), `implementation/{requirements,test_plan,architecture,api_contracts,data_flow,conflict_register}.md`, `feature_list.json`, `progress.md`, `session-handoff.md`.
**Estado:** QA-CR020-03 sin resolver; QA-CR020-01 corregido y aceptado (pendiente de reverificación independiente); QA-CR020-02, 04, 05, 06, O3 y O4 sin resolver; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-03 bloqueado contractualmente; CR-021 PROPUESTA (revisión 2); sin commit

**Revisión 2 (documental):** diseño conceptual aceptado provisionalmente (no es aprobación final). R1: garantías I2a (evaluaciones autorizadas, evidencia duradera) e I2b (intentos no confirmados: cuentan mientras consten; su pérdida antes de congelar no se detecta; requiere enmendar REQ-G-P17, CR-020 §C.3.2 y TC-ML-023). R2: autorización basada en la durabilidad de la evidencia, no del marcador (§F.4). R3: política P1–P5 ante corrupción (§F.2). Decisiones pendientes: CR-021 §J (1–7). Sin contradicción técnica abierta; queda la confirmación de la lectura de R2 (decisión 2).

**Base:** `fde522c` (`develop` = `origin/develop`). La corrección de QA-CR020-03 se detuvo antes de tocar código (bloqueo aceptado por el propietario).
**Bloqueo:** una línea legible no prueba durabilidad; una corrección sólida exige un registro escrito tras un `fsync` correcto (tipo nuevo) y reescribir la evidencia en el reintento (contrario a CR-020 §C.3.2 paso 1).
**Propuesta:** `harness/change_requests/CR-021_durabilidad-autorizacion-evaluacion.md` (PROPUESTA; su preparación está autorizada, no su aprobación ni su implementación): `EVALUATION_PERSISTED`, copias idénticas de recuperación, conteo conservador separado del acceso autorizado.
**Reproducción:** `.venv/bin/python -I -B harness/verification/IMPL-3_QA-CR020-03_reproduccion.py` sobre `fde522c`.
**Archivos nuevos o modificados (sin commit):** CR-021 (nuevo), `harness/verification/IMPL-3_QA-CR020-03_reproduccion.py` (nuevo), `progress.md`, `session-handoff.md`.
**Estado:** QA-CR020-03 sin resolver (QA-CR020-02, 04, 05, 06, O3 y O4 también); QA-CR020-01 corregido y aceptado, pendiente de reverificación independiente; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; contrato v1.8 sin cambios.
**Decisiones pendientes del propietario:** CR-021 §J.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## PUNTO DE CONTROL (2026-11-24) — QA-CR020-01 corregido y aceptado por el propietario; pendiente de reverificación independiente; commit en develop, sin push

**Aceptación del propietario (2026-11-24):** corrección funcional y evidencia aprobadas (validación previa de la desviación, rechazo sin escritura ni acceso, contabilidad conservadora y acceso denegado tras persistencia parcial, reintento idempotente, 11 pruebas nuevas, 789 passed / 5 skipped, validadores OK, Fail-Closed ante desviaciones mal formadas con conciliación manual sin reescribir historial, congelación legible exigida). Detalle: `harness/verification/IMPL-3_QA-CR020-01_correccion.md` §8. QA-CR020-03 sigue sin resolver, incluida la durabilidad de registros legibles tras un fallo de `fsync`. Commit de los ocho archivos, sin push; pruebas no reejecutadas para el commit. **Siguiente acción autorizada:** ninguna; esperar instrucciones del propietario.

**Base:** `e645a27` (`develop` = `origin/develop`); base funcional auditada `f2f05a9`.
**Autorización:** corregir solo QA-CR020-01 (contrato v1.8, CR-020).
**Hecho:** la DEVIATION obligatoria de una configuración no planificada se valida antes de escribir nada; una solicitud rechazada no escribe, no cuenta ni da acceso; la persistencia parcial cuenta (conservador) pero el cargador deniega los datos hasta conciliar; el reintento no duplica. Detalle: `harness/verification/IMPL-3_QA-CR020-01_correccion.md`.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 789 passed, 5 skipped; validadores → OK. Regresiones `tests/unit/test_qa_cr020_01.py`: 9 failed con la base sin corregir, 11 passed con la corrección.
**Archivos modificados (sin commit):** `src/swingpilot/research/{experiments,preregistration,partitions}.py`, `research/README.md`, `tests/unit/test_qa_cr020_01.py` (nuevo), `harness/verification/IMPL-3_QA-CR020-01_correccion.md` (nuevo), `progress.md`, `session-handoff.md`.
**Sin resolver:** QA-CR020-02, 03, 04, 05, 06, O3 y O4. CONF-009 y CONF-010 OPEN; D2 pendiente de cierre; FEAT-015 DONE; FEAT-017 IN_PROGRESS. Informe y sondas de la QA independiente conservados sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario.

## PUNTO DE CONTROL (2026-11-24) — QA independiente de CR-020: CONFORME CON OBSERVACIONES; evidencia preservada y aprobada; commit en develop, sin push

**Aprobación del propietario de la preservación (2026-11-24):** aprueba el informe en español, las 11 sondas reproducibles y las actualizaciones de continuidad; acepta la normalización a QA-CR020-O3 y QA-CR020-O4 sin cambios de contenido ni de clasificación. `f2f05a9` se conserva como la base funcional auditada. Commit de los cuatro archivos autorizados en develop, sin push; pruebas y sondas no reejecutadas para el commit. Los ocho elementos siguen sin resolver; D2 pendiente de cierre. **Siguiente acción autorizada:** ninguna; esperar instrucciones del propietario.

**Base verificada:** `f2f05a9` (`develop` = `origin/develop`). **Revisor:** QA independiente en sesión nueva (no es el agente implementador).
**Aceptación del propietario (2026-11-24):** acepta el informe tal como se entregó, con su veredicto; **no** cierra CR-020, D2, CONF-009, CONF-010 ni FEAT-017; autoriza solo la preservación de la evidencia.
**Artefactos (sin commit):** `harness/verification/IMPL-3_CR-020_QA_independiente.md` (informe; §9 separa las decisiones del propietario de los hallazgos) y `harness/verification/IMPL-3_CR-020_QA_sondas.py` (sondas P1–P11; reproducción: `.venv/bin/python -I -B harness/verification/IMPL-3_CR-020_QA_sondas.py` sobre `f2f05a9`).
**Evidencia:** 778 passed, 5 skipped; validadores OK; 4 regresiones reproducidas sobre `d372e28`; registro real G = 8 (4 + 4 de cota), sin cambios. Suite no reejecutada al preservar.
**Sin resolver (8; decisión del propietario PENDIENTE para cada uno):**
- QA-CR020-01 (MENOR): DEVIATION de configuración no planificada validada después del `CONFIGURATION_EVALUATED` duradero.
- QA-CR020-02 (MENOR): `confirmatory_status` no aplica la lectura estricta de REQ-G-103.
- QA-CR020-03 (MENOR): tras escritura incierta, el cargador entrega datos y el reintento no confirma durabilidad (TC-ML-023).
- QA-CR020-04 (OBS): relevancia por par frente a «el experimento o el par de T» (ambigüedad contractual).
- QA-CR020-05 (OBS): línea JSON no objeto → excepción en lugar de INCONCLUSIVE.
- QA-CR020-06 (MENOR): `feature_list.json` (l. 1720, 1768) y texto de CONF-009 desactualizados.
- QA-CR020-O3 (OBS): evidencia por construcción (escenarios de costes) o no reproducible (A2 previo).
- QA-CR020-O4 (OBS): el cargador no considera el estado del experimento.
**Estado:** CONF-009 y CONF-010 OPEN; D2 sin cerrar; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Archivos modificados:** los dos artefactos nuevos, `progress.md`, `session-handoff.md`. Sin cambios en código, pruebas funcionales, registro real, `feature_list.json`, contrato ni estados.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario.

## PUNTO DE CONTROL (2026-11-24) — CR-020 completa; siguiente sesión: verificación independiente de CR-020

**Rama:** `develop`. **Commits de CR-020:** `d372e28` (aplicación contractual, contrato v1.8, DEC-021), `824fae8` (implementación funcional + corrección A2) y el commit «feat(impl-3): register historical trial provenance under DEC-022» (procedencia real). El push lo decide el propietario.
**D2:** resuelta metodológicamente, aplicada contractualmente, implementada funcionalmente y poblada con la procedencia real autorizada. **Pendiente: QA independiente.**
**Estado:** CONF-009 y CONF-010 OPEN (se cierran solo con la verificación independiente aceptada; CONF-009 exige además su reevaluación antes del cierre formal de FEAT-017). FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; gates sin cambios.
**Última evidencia:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 778 passed, 5 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK. Registro real: 4 líneas (2 `ANTECEDENT` + 2 `ANTECEDENT_PROVENANCE` de DEC-022); H_doc 4, H_bound 4 (cota), E 0, G 8.
**Alcance de la verificación independiente (solo con autorización expresa del propietario):**
- Contrato: `implementation/requirements.md` v1.8 (REQ-G-P17, REQ-G-103, REQ-G-104), `test_plan.md` (TC-ML-006, TC-ML-020..024), `docs/decisions/DEC-021…md`, `DEC-022…md`, `harness/change_requests/CR-020_…md` (rev. 3, §H).
- Código: `src/swingpilot/research/{experiments,preregistration,trials,acceptance,partitions}.py`.
- Pruebas: `tests/unit/test_trials_accounting.py`, `test_cr020_regressions.py`, `test_snapshot.py` (A2 y TC-ML-023), `test_research.py`.
- Evidencia y limitaciones aceptadas: `harness/verification/IMPL-3_CR-020_implementacion.md` §1–§10.
- Restricciones: solo lectura salvo autorización; registros temporales y datos sintéticos; sin particiones reales, SNAP-0001, experimentos ni IA; la QA no aprueba su propio trabajo (AGENTS.md).
**Siguiente acción autorizada:** ninguna. Esperar instrucciones del propietario.

## IMPL-3 (2026-11-24) — Procedencia real de ANT-MR-H1 y EXP-0001 registrada y aceptada (DEC-022)

**Base:** `824fae8` (implementación congelada de CR-020; develop = `origin/develop`).
**Hecho:** DEC-022 con las dos líneas `AUTORIZA: PROCEDENCIA`; dos registros `ANTECEDENT_PROVENANCE` escritos con la API (`f0c4e2bf…`, `7b5a8245…`). Registro real: 4 líneas, las 2 originales intactas.
**Resultado:** H_doc 4, H_bound 4 (cota), E 0, G 8, `trials_count()` 8; estados originales REJECTED y PENDING_DOCUMENTATION conservados. Validadores → OK.
**Aceptación del propietario:** DEC-022 y evidencia contable aprobadas; `test_repository_registry_contains_declared_antecedents` actualizada al estado autorizado (G = 8, DEC-022). Suite 778 passed, 5 skipped; validadores OK.
**Aprobación final del propietario (2026-11-24):** registro de DEC-022, actualización de la prueba y evidencia aceptados; commit en develop, sin push.

## IMPL-3 (2026-11-24) — Implementación de CR-020 APROBADA por el propietario (con A2); commit en develop, sin push

**Aprobación del propietario:** implementación funcional de CR-020 (v1.8, DEC-021) con la corrección A2; evidencia aceptada (778 passed, 5 skipped; validadores OK) y limitaciones residuales aceptadas. No es aprobación de QA independiente.
**D2:** resuelta metodológicamente, aplicada contractualmente e implementada funcionalmente. Pendientes: registro real de procedencia y verificación independiente.
**Estado:** CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS; D3–D7 PENDIENTES; SNAP-0001 no creada; registro real sin cambios.
**Siguiente acción autorizada:** ninguna. Esperar autorización expresa antes de registrar la procedencia real de los antecedentes.

### Registro previo a la aprobación — Corrección A2 aplicada (opción B); sin commit

**Propietario:** aceptación provisional de CR-020 (sin commit ni aprobación final); DEVELOPMENT/VALIDATION provisional (exploración previa → D5); REQ-G-103 estricta; opción B de A2 aprobada.
**Hecho:** cargador sin configuración privado (`_load_train_val_for_inspection`); `load_train_val_for_configuration` única vía pública, con el par en `accounting()["pairs"]` y Fail-Closed; guarda estática sobre `src/` y `scripts/`. Detalle: `harness/verification/IMPL-3_CR-020_implementacion.md` §8.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 778 passed, 5 skipped. Validadores → OK. Antes de la corrección: 2 defectos de comportamiento genuinos + 5 fallos de interfaz.
**Límite:** control de vías de la aplicación, no del sistema de archivos (`train_val.parquet` sin sellar).
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario antes del commit.

## IMPL-3 (2026-11-24) — CR-020 implementada (FEAT-017); pendiente de revisión del propietario; sin commit

**Base:** `d372e28` (develop = `origin/develop`, sincronizados).
**Hecho:** registro (`ANTECEDENT_PROVENANCE`, `CONFIGURATION_EVALUATED`, conteo G/N_pre), congelación y selección validadas en el bloqueo, `informed_by`, regla de selección, conciliación del evaluador (`trials.py`), cargador con puerta. Detalle: `harness/verification/IMPL-3_CR-020_implementacion.md`.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 771 passed, 5 skipped. Validadores → OK. Regresiones contra `d372e28`: 4 de comportamiento.
**Ambigüedades abiertas (Fail-Closed):** estados que permiten evaluar (piloto previo a la congelación bloqueado hasta D5); `load_train_val` genérico; configuración no planificada → INCONCLUSIVE sin condición.
**Registro real:** sin cambios; su `trials_count()` es indeterminado hasta los registros de procedencia autorizados.
**Archivos modificados:** `src/swingpilot/research/{experiments,preregistration,acceptance,partitions,trials}.py`, `research/README.md`, `tests/unit/test_{research,snapshot,ml_registry,engines,trials_accounting,cr020_regressions}.py`, `harness/verification/IMPL-3_CR-020_implementacion.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** contrato, AC, `feature_list.json`, estados de FEAT, gates; CONF-009/010 OPEN; D3–D7.
**Siguiente acción autorizada:** ninguna. Esperar la revisión del propietario antes del commit, de los registros reales de procedencia o de la QA independiente.

## IMPL-3 (2026-11-24) — Aplicación contractual de CR-020 APROBADA; D2 resuelta (método y contrato); commit en develop, sin push

**Aprobación del propietario (2026-11-24):** aplicación contractual de CR-020, contrato v1.8, DEC-021 y `feature_list.json` v1.17.0; REQ-4036 como fuente extraída; omisión de las líneas `AUTORIZA: PROCEDENCIA` en DEC-021 (los registros reales de procedencia requieren una autorización separada).
**D2:** RESUELTA metodológica y contractualmente; implementación y verificación PENDIENTES. CONF-009 y CONF-010 OPEN.
**Limitación:** los validadores existentes no verifican la corrección semántica del texto del contrato.
**Siguiente acción autorizada:** ninguna. Esperar la autorización expresa de implementación de CR-020.

### Registro previo a la aprobación — CR-020 aplicada solo contractualmente; sin commit

**Aprobación del propietario:** CR-020 revisión 3 y sus decisiones; tres detalles de implementación (formas de `candidate_selection_rule`, validación de procedencia, validaciones previas con la condición de que la evaluación la permitan el estado, las transiciones y las autorizaciones vigentes; un estado no terminal no basta). Solo aplicación contractual.
**Aplicado:** DEC-021 (nuevo); contrato v1.8 (REQ-G-P17, REQ-G-103, REQ-G-104; TC-ML-006, TC-ML-020..024); `feature_list.json` v1.17.0 (AC-017-3/8/13; FEAT-017 sigue IN_PROGRESS); CR-020 §H; historial de CONF-009/010.
**D2:** resolución metodológica y contractual APROBADA; implementación y verificación PENDIENTES. CONF-009 y CONF-010 OPEN.
**Validadores:** manifest, requirements y gates → OK. Suite funcional no ejecutada.
**Sin cambios:** código, registro de experimentos, estados y transiciones, estados de FEAT, D3–D7; SNAP-0001 no creada.
**Archivos modificados (sin commit, desde `259dbf6`):** CR-020 (nuevo), DEC-021 (nuevo), `implementation/{requirements,architecture,api_contracts,data_flow,test_plan,conflict_register}.md`, `feature_list.json`, `progress.md`, `session-handoff.md`.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario para el commit o la implementación de CR-020.

## IMPL-3 (2026-11-24) — CR-020 revisión 3 (PROPUESTA): R1–R4 incorporadas; lista para aprobación final; sin commit

**Decisiones del propietario (no aprueban la CR):** R1–R4 con condiciones (§B.3 de CR-020) y cuatro ambigüedades resueltas (§B.4): solicitud rechazada ≠ evaluada; `N_eval` no restaura el carácter confirmatorio; registro duradero = límite contable de un inicio autorizado, no prueba de ejecución; NO RELEVANTE solo con evidencia positiva suficiente.
**§F:** sin decisiones metodológicas abiertas; pendiente la aprobación final de CR-020 (incluye las formas de `candidate_selection_rule`, los patrones de R4 y las validaciones previas, redactados por el Orquestador).
**Estado:** CR-020 PROPUESTA; D2 pendiente de aprobación contractual; CONF-009 y CONF-010 OPEN; D3–D7 PENDIENTES; FEAT-017 IN_PROGRESS; contrato v1.7.
**Archivos modificados (sin commit, acumulados desde `259dbf6`):** CR-020 (nuevo), `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`. Sin pruebas ejecutadas.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación final expresa de CR-020.

## IMPL-3 (2026-11-24) — CR-020 revisión 2 (PROPUESTA) con decisiones del propietario; D2 pendiente de aprobación contractual; sin commit

**Decisiones del propietario (no aprueban la CR):** población de todas las familias BTC/USDT; conteo congelado con conciliación de pruebas posteriores basada en evidencia, sin LLM, e INCONCLUSIVE si la influencia es indeterminable; configuraciones planificadas incluidas aunque no se evalúen; reducción de cotas solo con evidencia y aprobación, prospectiva; `ANTECEDENT_PROVENANCE` aprobado como solución propuesta de CONF-009 (estado original separado de la procedencia vigente). CONF-010 MEDIUM confirmada.
**CR-020 rev. 2:** ver §C (conteos y doble conteo, registro duradero, procedencia append-only, conciliación C.4, distinción de resultados C.5, texto contractual C.6). Decisiones abiertas R1–R4 (§F). Conteo inicial 8 = 4 verificadas documentalmente + 4 de cota.
**Estado:** CR-020 PROPUESTA; D2 pendiente de aprobación contractual; CONF-009 y CONF-010 OPEN; D3–D7 PENDIENTES; FEAT-017 IN_PROGRESS; contrato v1.7.
**Archivos modificados (sin commit):** CR-020 (nuevo), `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`. Sin pruebas ejecutadas.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — D2: dirección aprobada; resolución contractual PENDIENTE de CR-020; CONF-010 registrado; sin commit

**Base:** `259dbf6` (`develop` = `origin/develop`).
**D2 (identificador de revisión, no DEC):** dirección metodológica aprobada (opción B): configuraciones evaluadas; rechazadas y abandonadas cuentan; ideas y no evaluadas confirmadas no cuentan; cota conservadora para ejecución desconocida; conteo histórico inicial 8 (MR H1: 4 documentadas; EXP-0001: 4 como cota). Regla del máximo NO aprobada. **Resolución contractual PENDIENTE de CR-020.**
**CR-020 (PROPUESTA):** `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md`. Conteo congelado y verificado contra el registro; tipos `ANTECEDENT_PROVENANCE` (opción B de CONF-009) y `CONFIGURATION_EVALUATED`; contrato v1.8 propuesto. Decisiones abiertas en su §F.
**Conflictos abiertos:** CONF-009 (LOW; reevaluación obligatoria antes del cierre de FEAT-017); CONF-010 (MEDIUM propuesta).
**Archivos modificados:** CR-020 (nuevo), `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`. Sin pruebas ejecutadas.
**Sin cambios:** contrato v1.7, código, registro de experimentos, AC, `feature_list.json`, estados de FEAT, cortes; D3–D7 PENDIENTES; SNAP-0001 no creada.
**Bloqueos:** AC-017-10 (D3–D7); AC-017-11; CR-020 y sus decisiones §F; O4; coherencia `execution_model`/`ExecutionModel`; TC-ML-012.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — D1 APROBADA (nivel documental); CONF-009 LOW/OPEN con reevaluación obligatoria; commit en develop, sin push

**Aprobación del propietario (2026-11-24):** los cuatro cambios documentales de `2e13c27`; D1 resuelta a nivel documental; CONF-009 con severidad LOW y estado OPEN.
**Condición:** CONF-009 debe reevaluarse obligatoriamente antes del cierre formal de FEAT-017 (registrada en `implementation/conflict_register.md`).
**Estado:** AC-017-10 bloqueado (D3 y D2, D4–D7 PENDIENTES); FEAT-017 IN_PROGRESS; registro de experimentos sin cambios; SNAP-0001 no creada. Archivos de este paso: `implementation/conflict_register.md`, `progress.md`, `session-handoff.md`. Sin pruebas ejecutadas.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — D1 RESUELTA a nivel documental (EXP-0001); CONF-009 abierto; sin commit

**Sincronización:** `develop` = `origin/develop` = `ec2e926` (push del propietario; árbol limpio antes de este paso). Las entradas anteriores que dicen «sin push» quedan superadas.
**Identificadores de revisión de FEAT-017 (no son DEC-XXX):** D1 suficiencia documental de EXP-0001 — **RESUELTA**; D2 unidad de `trials_count`; D3 integridad metodológica de las particiones; D4 autorización y cortes de SNAP-0001; D5 secuencia de exploración y preregistro; D6 parámetros y umbrales estadísticos; D7 configuración del piloto — **PENDIENTES**; D8 resolución de QA3R2-06/07 — **RESUELTA**.
**D1:** la evidencia de `trading-bot@21c5f25` (preregistro v4 congelado, D-024, configuraciones A–D, hash del manifiesto) establece la procedencia documental; ejecución, resultados de Train y rendimiento siguen desconocidos; sin clasificación por resultados. Mean Reversion H1 conserva su rechazo documentado. Resuelve solo la dependencia documental de AC-017-10; **AC-017-10 no está satisfecho**.
**CONF-009 (OPEN):** el registro de experimentos no puede representar D1; no se modifica (opción A). `PENDING_DOCUMENTATION` de EXP-0001 se conserva solo por esa limitación y no es la valoración actual del propietario. Opción B (tipo de registro de procedencia) diferida, no aprobada.
**Archivos modificados:** `implementation/conflict_register.md`, `harness/verification/IMPL-3_EXP-0001_procedencia.md` (ruta corregida a `/home/erick/Descargas/Projects/trading-bot`; §6), `progress.md`, `session-handoff.md`. Sin pruebas ejecutadas.
**Sin cambios:** registro de experimentos, código, contratos, AC, `feature_list.json`, estados de FEAT, cortes; SNAP-0001 no creada; $0 de IA.
**Bloqueos:** AC-017-10 (D3 y D2, D4–D7); AC-017-11 (AC-017-10 y SNAP-0001); antes del piloto confirmatorio: coherencia `execution_model`/`ExecutionModel` y recuperabilidad del preregistro (O4); TC-ML-012 (aclaración contractual); CONF-009.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — ORQ-017-01 RESUELTO (FEAT-017); commit en develop, sin push

**Aprobación del propietario (2026-11-24):** implementación y evidencia aprobadas; riesgos residuales aceptados dentro del alcance. Sin pruebas adicionales tras la aprobación.
**Condición operativa:** tras un fallo de persistencia incierto (`DeviationPersistenceUncertain`), el experimento afectado **no continúa ni pasa por HUMAN_REVIEW** hasta conciliar el intento con el registro (reconstruir con objetos nuevos, comprobar el `deviation_id`, volver a registrar si falta, revisión manual si el registro quedó ilegible). Condición operativa, **no** un mecanismo implementado entre procesos. Solo un DEVIATION escrito con éxito cuenta como duradero.
**Pendientes de FEAT-017:** AC-017-10/11; decisiones D1–D7; SNAP-0001; recuperabilidad del contenido del preregistro antes del piloto confirmatorio (O4); observación TC-ML-012 (aclaración contractual). **D8 RESUELTA** (QA3R2-06 y QA3R2-07 cerrados).
**Estado:** FEAT-017 IN_PROGRESS (sin cambios en `feature_list.json`).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

### Registro previo a la aprobación — ORQ-017-01 corregido, pendiente de aprobación; sin commit

**Base:** `4ad42ed` (develop, 2 commits por delante de `origin/develop`).
**Hecho:** corrección directa autorizada (O1–O4), sin CR. Las desviaciones se escriben como registros `DEVIATION` append-only en `research/experiments/registry.jsonl`, bajo el mismo bloqueo exclusivo que `PARTITION_CONSUMED` (cronología = orden del archivo). El carácter confirmatorio se reconstruye desde el registro (`preregistration.confirmatory_status`) para HUMAN_REVIEW; vinculado al SHA-256 de PREREGISTERED; Fail-Closed ante evidencia ausente, corrupta o incoherente; escrituras fallidas tratadas como inciertas. Defecto reproducido aparte con `4ad42ed`. 24 pruebas nuevas; QA3R2-07 y TC-ML-013 con las mismas aserciones (solo cambia la preparación). Detalle en `harness/verification/IMPL-3_QA_ronda2.md` §Corrección de ORQ-017-01.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 689 passed, 5 skipped. Validadores → OK.
**Observación registrada (sin cambios):** TC-ML-012 («registrada como desviación») frente al comportamiento actual (acceso denegado en el registro de accesos); aclaración contractual posterior.
**Requisito diferido (O4):** el contenido del preregistro confirmatorio deberá poder recuperarse para comprobar su SHA-256 antes del piloto.
**Sin commit ni push.** Archivos modificados: `src/swingpilot/research/{experiments,preregistration}.py`, `tests/unit/test_research.py`, `research/README.md`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** evaluador, cargador de particiones, contrato, AC, `feature_list.json`, estados de FEAT (FEAT-017 IN_PROGRESS), D1–D7. SNAP-0001 no creada; OOS/LOCKBOX reales intactos; $0 de IA.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — QA3R2-07 RESUELTO POR COMPLETO (FEAT-017); commit en develop, sin push

**Aprobación del propietario (2026-11-24):** corrección y evidencia aprobadas; riesgos residuales aceptados dentro del alcance de QA3R2-07, excepto la persistencia de las desviaciones. Sin pruebas adicionales tras la aprobación.
**Abierto:** ORQ-017-01 (desviaciones del preregistro solo en memoria; REQ-G-103, AC-017-3). Revisión contractual separada antes del cierre de FEAT-017; sin persistencia, nuevos tipos de registro ni cambios en el evaluador hasta entonces.
**Estado:** FEAT-017 IN_PROGRESS (pendientes AC-017-10/11, ORQ-017-01, decisiones D1–D8 y SNAP-0001). QA3R2-06 y QA3R2-07 resueltos.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

### Registro previo a la aprobación — QA3R2-07 corregido (FEAT-017), pendiente de aprobación; sin commit

**Base:** `daa78d0` (develop, 1 commit por delante de `origin/develop`).
**Hecho:** corrección directa autorizada de QA3R2-07, sin CR. `oos_seen`/`record_deviation` (`src/swingpilot/research/preregistration.py`) exigen un `ExperimentRegistry` y un experimento nativo registrado; la exposición sale de PARTITION_CONSUMED del mismo experimento (todas las snapshots); el registro de accesos solo añade evidencia; Fail-Closed ante registro ausente, ilegible, corrupto o incoherente. Defecto reproducido aparte con `daa78d0`. 29 pruebas nuevas y TC-ML-013 adaptada (mismas aserciones). Detalle en `harness/verification/IMPL-3_QA_ronda2.md` §Corrección de QA3R2-07.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 665 passed, 5 skipped. Validadores → OK.
**Hallazgo nuevo ORQ-017-01 (NO RESUELTO):** las desviaciones del preregistro solo viven en memoria (REQ-G-103, AC-017-3). Revisión contractual separada antes del cierre de FEAT-017; sin persistencia ni nuevos tipos de registro por ahora.
**Sin commit ni push.** Archivos modificados: `src/swingpilot/research/preregistration.py`, `tests/unit/test_research.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** contrato, AC, `feature_list.json`, estados de FEAT (FEAT-017 IN_PROGRESS), carga de particiones, evaluador, D1–D7. SNAP-0001 no creada; OOS/LOCKBOX reales intactos; $0 de IA.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — QA3R2-06 RESUELTO POR COMPLETO (FEAT-017); commit en develop, sin push

**Aprobación del propietario (2026-11-24):** corrección y evidencia aprobadas; riesgos residuales aceptados dentro del alcance. **Requisito conservado:** verificar la coherencia entre el `execution_model` preregistrado y `ExecutionModel` antes del piloto confirmatorio. Sin validación adicional ni topes realistas de costes en esta etapa. Sin pruebas adicionales tras la aprobación.
**Estado:** FEAT-017 IN_PROGRESS (sin cambios en `feature_list.json`); QA3R2-07 abierto; SNAP-0001 no creada.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

### Registro previo a la aprobación — QA3R2-06 corregido (FEAT-017), pendiente de aprobación; sin commit

**Push:** los seis commits aprobados están en `origin/develop` (`c3f526c`, sincronizado).
**Hecho:** corrección directa autorizada de QA3R2-06, sin CR. `ExecutionModel.__post_init__` (`src/swingpilot/research/backtest.py`) acepta `commission_rate` y `slippage` solo como reales finitos no booleanos con `0.001 ≤ valor < 1.0`; si no, `ValueError`. Límite superior comprobado sin conflicto con el contrato. 65 pruebas nuevas en `tests/unit/test_research.py`: 24 regresiones (fallan con `c3f526c`), 8 normalizaciones de `TypeError` a `ValueError`, 12 rechazos existentes y 21 controles. Detalle en `harness/verification/IMPL-3_QA_ronda2.md` §Corrección de QA3R2-06.
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 636 passed, 5 skipped. Validadores → OK.
**Sin commit ni push.** Archivos modificados: `src/swingpilot/research/backtest.py`, `tests/unit/test_research.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** contrato, AC, `feature_list.json`, estados de FEAT (FEAT-017 IN_PROGRESS), evaluador, preregistro, lógica de ejecución. QA3R2-07 abierto. SNAP-0001 no creada; OOS/LOCKBOX reales intactos; $0 de IA.
**Pendiente del propietario (FEAT-017):** aprobación de QA3R2-06; QA3R2-07; decisiones D1–D8 del análisis de AC-017-10/11 (suficiencia de la documentación de EXP-0001, unidad de `trials_count`, cortes y creación de SNAP-0001, orden del piloto en Train, campos del preregistro sin valor contractual, configuración del piloto).
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — FEAT-015 CERRADA como DONE

**Aprobación del propietario (2026-11-24):** AC-015-1..8 definitivos; FEAT-015 READY_FOR_REVIEW → DONE. Riesgos residuales y controles de despliegue diferidos (G6, Laptop B) aceptados. `feature_list.json` v1.16.0.
**Condiciones de reapertura:** CR aprobada que modifique los cortes, REQ-G-109 o algún AC-015-*; o un defecto de implementación confirmado al construir o verificar SNAP-0001 (→ IN_PROGRESS por gobernanza). Un entorno incompatible, por sí solo, no es necesariamente un defecto.
**Fuera del cierre (autorización separada):** creación de SNAP-0001; validación metodológica de la independencia histórica de las particiones.
**Evidencia:** código verificado congelado en `4391df5` (571 passed, 5 skipped); validadores OK al cerrar; la suite no se volvió a ejecutar.
**Estado de IMPL-3:** FEAT-015 y FEAT-016 DONE; FEAT-017..022 IN_PROGRESS (pendientes AC-017-10/11, AC-018-2/6, AC-020-8, AC-022-6 y SNAP-0001).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — FEAT-015: trazabilidad consolidada, revisión de cierre preparada

**Hecho:** `feature_list.json` v1.15.0. FEAT-015 → `evidence.traceability_review`: matriz AC-015-1..8 (todos CUMPLEN), hallazgos QA3R2-02/03/04/08 resueltos, riesgos aceptados, controles diferidos (G6, Laptop B), SNAP-0001 fuera del alcance técnico, condiciones de reapertura y recomendación (DONE). Estado sin cambio: READY_FOR_REVIEW.
**Evidencia:** última verificación del código, sobre el árbol congelado en `4391df5`: 571 passed, 5 skipped; validadores OK. No se ejecutaron pruebas en este paso.
**Sin commit.** Archivos: `feature_list.json`, `progress.md`, `session-handoff.md`.
**Pendiente del propietario:** aceptación formal de AC-015-1..8 y decisión de cierre de FEAT-015.
**Siguiente acción autorizada:** ninguna. Esperar la aprobación expresa del propietario.

## IMPL-3 (2026-11-24) — QA3R2-08 RESUELTO POR COMPLETO (bloqueo ante sellado no efectivo)

**Hecho:** corrección directa sin CR según las decisiones del propietario. Sonda de sellado antes de descargar o apartar huérfanos; comprobación final antes de confirmar, con rollback; `PartitionLoader` bloqueado (también `train_val`) y nueva comprobación antes de consumir; `verify-snapshot` → ERROR y código 1; sin omisión. 10 regresiones (todas fallan con `f8e7643`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 571 passed, 5 skipped (como usuario no root). Validadores → OK.
**Aprobación final del propietario (2026-11-24)**, congelada en un commit en develop, sin push. Riesgos aceptados: CI con usuario sin privilegios; cuarentena de huérfanos existente; privilegios especiales de Linux y aislamiento del despliegue sujetos a G6; Laptop B como requisito previo de despliegue. Archivos: `src/swingpilot/research/{snapshot,partitions,cli}.py`, `tests/unit/test_snapshot.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Requisito de despliegue pendiente:** verificar en Laptop B usuario no root, sistema de archivos POSIX y sellado efectivo (no confirmado).
**Sin cambios:** contratos, `feature_list.json`, estados de FEAT (FEAT-015 READY_FOR_REVIEW), cortes, SNAP-0001, OOS/LOCKBOX reales.
**Estado de hallazgos de FEAT-015:** QA3R2-02, 03, 04 y 08 resueltos y aprobados. FEAT-015 sigue en READY_FOR_REVIEW (su cierre requiere decisión del propietario).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 RESUELTO POR COMPLETO

**Estado:** QA3R2-04 resuelto por completo y aprobado por el propietario: corrección principal (`f04a2d1`) y observación adicional sobre el estado destino (`c314d92`, 17 pruebas). Registro en `harness/verification/IMPL-3_QA_ronda2.md`.
**Última verificación (sobre `c314d92`):** 563 passed, 5 skipped; validadores OK. En este paso no se ejecutaron pruebas.
**Sin cambios:** FEAT-015 en READY_FOR_REVIEW y demás estados de FEAT; contratos; SNAP-0001 no creada; OOS/LOCKBOX reales intactos; sin push.
**Pendiente:** QA3R2-08 CONDICIONADO (sellado no efectivo: avisar o bloquear).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 (observación adicional): estado destino en transiciones, APROBADA (commit en develop, sin push)

**Hecho:** corrección directa sin CR, aprobada contractualmente por el propietario. Las transiciones que decide el propietario exigen `AUTORIZA: EXP-NNNN ESTADO_DESTINO` (OOS_EVALUATION, APPROVED, REJECTED, INCONCLUSIVE); la línea sin estado ya no autoriza nada; la gramática de particiones no cambia. Código afectado: registro de experimentos de FEAT-017 (AC-017-1). 17 regresiones (4 reproducen el defecto con `c9a054b`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 563 passed, 5 skipped. Validadores → OK.
**Aprobada por el propietario (2026-11-24)** y congelada en un commit en develop, sin push. Archivos: `src/swingpilot/research/experiments.py`, `tests/unit/test_{research,snapshot,ml_registry,engines}.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** máquina de estados, contratos, AC, `feature_list.json`, estados de FEAT; QA3R2-08 sigue CONDICIONADO; SNAP-0001 y OOS/LOCKBOX reales intactos.
**Pendientes:** QA3R2-08 CONDICIONADO (sellado no efectivo: avisar o bloquear).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-08 aprobado en su alcance actual (CONDICIONADO); commit en develop, sin push

**Hecho:** corrección autorizada de QA3R2-08 (FEAT-015). Detección del sellado no efectivo (`SealingWarning`; `verify-snapshot` → código 1), re-sellado de OOS/LOCKBOX con modo alterado, lectura autorizada con re-sellado inmediato (SIGKILL ya no deja 0o400), id `SNAP-NNNN` obligatorio en la CLI y `fullmatch` en `build_snapshot`/`load_manifest`. 28 regresiones (26 fallan con `f04a2d1`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 546 passed, 5 skipped. Validadores → OK.
**Aprobado por el propietario (2026-11-24) en su alcance actual** y congelado en un commit en develop, sin push. **QA3R2-08 CONDICIONADO, no cerrado:** falta decidir y resolver el comportamiento ante sellado no efectivo (hoy solo avisa). Archivos: `src/swingpilot/research/{snapshot,partitions,cli}.py`, `tests/unit/test_snapshot.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** FEAT-015 en READY_FOR_REVIEW; cortes, SNAP-0001, OOS/LOCKBOX reales, contratos y esquema del manifiesto intactos. QA3R2-02/03 ya estaban corregidas (`04dc2ea`).
**Pendientes registrados:** QA3R2-08 condicionado (sellado no efectivo: avisar o bloquear); observación de QA3R2-04 sobre el estado destino en la línea de transición (sin analizar ni implementar).
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-24) — QA3R2-04 corregido y aprobado (commit en develop, sin push)

**Hecho:** corrección autorizada de QA3R2-04 (FEAT-015). `create()`/`claim_partition()` validan `EXP-NNNN`; las decisiones se comprueban con una línea exacta `AUTORIZA: EXP-NNNN [<oos|lockbox> <SNAP-…>]` en lugar de por subcadena; decisión ilegible → denegada. 48 regresiones (45 fallan con `e375a18`).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 518 passed, 5 skipped. Validadores → OK.
**Aprobado por el propietario (2026-11-24)** y congelado en un commit en develop, sin push. Archivos: `src/swingpilot/research/{experiments,partitions}.py`, `tests/unit/test_{research,snapshot,ml_registry,engines}.py`, `harness/verification/IMPL-3_QA_ronda2.md`, `progress.md`, `session-handoff.md`.
**Sin cambios:** FEAT-015 sigue en READY_FOR_REVIEW; cortes, SNAP-0001, OOS/LOCKBOX y registro real intactos.
**Observaciones sin implementar (por indicación del propietario):** estado destino en la línea de transición; ids de antecedentes; `SNAPSHOT_ID.match` con salto final (QA3R2-08); formato `AUTORIZA:` en decisiones reales.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario.

## IMPL-3 (2026-11-23) — FEAT-016 cerrada como DONE

**Aprobación del propietario (2026-11-23):** FEAT-016 pasa de READY_FOR_REVIEW a DONE. No es DONE-PARTIAL porque AC-016-9 excluye la operación continua de IMPL-3. `feature_list.json` v1.14.0 incluye la aprobación, `closure_verification` sobre `c384386` (470 passed, 5 skipped) y la evidencia pública del 2026-11-20 conservada.
**Riesgo residual aceptado:** QA3R2-05 (resync sin reintento con una conexión WebSocket silenciosa; Fail-Closed intacto). Está asignado a **IMPL-5**: recuperación autónoma ante conexiones silenciosas.
**Sin commit:** solo registros (`feature_list.json`, `progress.md`, `session-handoff.md`). No se tocó código ni contratos.
**Siguiente acción autorizada:** ninguna. Esperar indicación del propietario (commit de este cierre; FEAT-015; FEAT-017..022; AC pendientes; SNAP-0001).

## IMPL-3 (2026-11-20) — QA de motores cerrada; CR-019 aplicada (contrato v1.7)

**Commits (sin push):** `04dc2ea` (ENV-01..04 y QA3R2-01..03), `bca19fc` (QA3E-02..06 y 10; CONF-008). **Sin commit:** CR-019 aprobada (DEC-020) y aplicada, que corrige QA3E-01, pendiente de revisión del propietario.
**Contrato v1.7:** `PROPOSAL_NORMALIZATION_REJECTED` (34 tipos; §3.8 B.10) en E9. CONF-008 RESUELTA.
**QA de FEAT-018..022:** todos los hallazgos autorizados están corregidos (`harness/verification/IMPL-3_QA_engines.md`). QA3E-07..09 son observaciones sin tocar. DATA_STALE queda PENDING (sin umbral en el contrato).
**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 470 passed, 5 skipped. Validadores → OK.
**Siguiente acción autorizada:** ninguna. Esperar la revisión y el commit de CR-019 por indicación del propietario.
**Sin cambios:** FEAT-015..022 sin cerrar (FEAT-015/016 en READY_FOR_REVIEW, sin aprobar; FEAT-017..022 en IN_PROGRESS); SNAP-0001 sin crear; OOS/LOCKBOX intactos; pendientes del propietario: AC-018-2/6, AC-020-8, AC-022-6.

## IMPL-3 (2026-11-20) — ENV-01..04 y QA3R2-01..03 corregidos; base congelada para la QA de FEAT-018..022

**Hecho y aprobado por el propietario:** (1) ENV-01..04: Python 3.14.4 (`.python-version`, instalado con uv), `requirements-dev.lock` con hashes SHA-256, `scripts/setup_env.sh`, scikit-learn excluido (DEC-017 Q44), `tests/regression/test_environment_lock.py`. (2) QA3R2-01..03 corregidos con regresiones que fallan con `5c17e92` (`IMPL-3_QA_ronda2.md` §Correcciones). Riesgos residuales aceptados en `progress.md`.

**Entorno en otra máquina:** ejecutar `scripts/setup_env.sh` (requiere `uv`). Sin eso, `test_environment_lock.py` falla, que es lo esperado.

**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 450 passed, 5 skipped. Validadores → OK.

**Siguiente acción autorizada:** paso 3, la QA independiente focalizada de FEAT-018..022 (una sola revisión, solo lectura) sobre el commit congelado.

**Sin cambios / pendiente:** FEAT-015/016 no aprobadas; SNAP-0001 no creada y sus cortes sin decidir; OOS/LOCKBOX intactos; CR-017, REQ-G-P08 y G5–G7 fuera de esta etapa; QA3R2-04..08 (observaciones) sin tocar; sin push.

## IMPL-3 «Integración cuantitativa» (2026-11-20) — EN CURSO: QA de 2 rondas completada

**Estado:** DEC-017, DEC-018 y DEC-019 (CR-018 aprobada y aplicada). Contrato **v1.6**. `feature_list.json` v1.12.0. Código de FEAT-018..022 implementado (sin QA).

| FEAT | Estado | QA ronda 2 |
|---|---|---|
| FEAT-015 Snapshot | READY_FOR_REVIEW | Conforme con observaciones (QA3R2-02, 03) |
| FEAT-016 Datos en vivo | READY_FOR_REVIEW | Conforme con observaciones (QA3R2-05) |
| FEAT-017 Research | IN_PROGRESS (AC-017-10/11 bloqueados) | Infraestructura conforme con observaciones (QA3R2-01: corregir antes de usar el evaluador) |
| FEAT-019 ML | IN_PROGRESS (AC-019-4, CR-018) | Infraestructura conforme |
| FEAT-018..022 | IN_PROGRESS | Implementadas en `src/swingpilot/engines/` (36 pruebas); sin QA independiente; pendientes AC-018-2/6, AC-020-8, AC-022-6 |

**Informes:** `harness/verification/IMPL-3_QA_ronda1.md` (hallazgos y correcciones), `IMPL-3_QA_ronda2.md`, `IMPL-3_entorno_reproducibilidad.md`, `IMPL-3_EXP-0001_procedencia.md`.

**Pendiente del propietario:**
1. Hallazgos de la ronda 2 (3 MENOR, 5 OBS). Las rondas de QA están agotadas (2/2): corregirlos requiere indicar cómo se verifican.
2. Cierre de FEAT-015/016 (no autorizado aún).
3. ENV-01..04.
4. Cortes de SNAP-0001 frente a los datos ya usados por Fase 0/EXP-0001. SNAP-0001 NO se crea sin autorización expresa.
5. QA independiente de FEAT-018..022 (nueva tanda de rondas) y, si se quiere, corridas reales con LLM de FEAT-022 (USD 0.50).

**Restricciones vigentes:** sin OOS/LOCKBOX; sin credenciales privadas; sin activar estrategias; IA $0.50 sin consumo; sin commit ni push.

**Verificar:** `.venv/bin/pytest -q -p no:cacheprovider tests` → 426 passed, 5 skipped. Validadores → OK.

**Siguiente acción autorizada:** ninguna de código hasta la indicación del propietario.

### Planificación (histórico de esta sesión)

**Pendiente en su momento (resuelto en DEC-018 salvo lo indicado arriba):** Q42, CR-018 B.6/B.7, EXP-0001, criterios de FEAT-015..022.

### Registro inicial de FEAT (histórico de esta sesión)

**Estado previo:** FEAT-015..022 registradas en `feature_list.json` v1.4.0 con status PENDING; plan en `impl3_plan`. Sin código.

| FEAT | Contenido | Vacío del contrato |
|---|---|---|
| FEAT-015 | Snapshot histórica sellada (REQ-G-109) | Ubicación (Q46) |
| FEAT-016 | Datos en vivo, velas cerradas, resync (REQ-G-097) | Fase no asignada en §7 (Q41) |
| FEAT-017 | Research & Backtesting (preregistro, WF, modelo de ejecución) | — |
| FEAT-018 | Regime Engine (REGIME_CLASSIFIED) | Clases y esquema (Q42, Q45) |
| FEAT-019 | ML Engine (versionado, promoción, drift) | Esquema; alcance (Q44, Q45) |
| FEAT-020 | Strategy Engine (STRATEGY_CANDIDATE, NO_SETUP) | Estrategia concreta; esquemas (Q43, Q45) |
| FEAT-021 | Normalización TRADE_PROPOSAL §4.1 | — |
| FEAT-022 | Ciclo Fase 1→4 con datos reales (salida de IMPL-3) | Tope de gasto (Q47) |

- Bloqueo: Q41–Q47 del propietario. Q45 propone CR-018 (esquemas) antes del código de FEAT-018..021.
- Sigue abierto: CR-017 (PROPUESTA, B.1–B.5).
- Nota de entorno: esta máquina no tiene `.venv`; crearla con `requirements-dev.txt` antes de ejecutar pruebas.
- (Superado: planificación aprobada en DEC-017.)

## Cierre de IMPL-2 (2026-11-20) — transición a IMPL-3

**Estado:** IMPL-2 «Agentes especializados» CERRADA con aprobación del propietario (2026-11-20). Contrato v1.5. G0..G4 PASS (G4 con alcance IMPL-1 + IMPL-2); G5..G7 PENDING.

| FEAT | Estado | Dependencia explícita |
|---|---|---|
| FEAT-008 Market Analyst | DONE | — |
| FEAT-009 Macro Analyst | DONE-PARTIAL | G6 (TC-SEC-003 amplio); CR-017 (fuente de noticias y macro_data) |
| FEAT-010 Strategy Analyst | DONE-PARTIAL | IMPL-3: STRATEGY_CANDIDATE real |
| FEAT-011 Risk Analyst | DONE-PARTIAL | IMPL-4: RISK_APPROVED real y Telegram (TC-FLOW-003) |
| FEAT-012 Decision Synthesis | DONE-PARTIAL | IMPL-3 normalización §4.1; IMPL-4 Risk Manager y Telegram |
| FEAT-013 effort y costo | DONE | — |
| FEAT-014 Ciclo de 5 agentes | DONE-PARTIAL | IMPL-5: cadena hasta ORDER_FILLED |

- Configuración vigente (DEC-016): effort medium ×5; prompts market 0.1.0, macro 0.2.0, strategy 0.2.0, risk 0.1.0, synthesis 0.1.1.
- Calibración: `tests/calibration/` (batería v2 congelada; `RUN_ANTHROPIC_LIVE=1 .venv/bin/python -m tests.calibration.run_battery --label <x>`). Gasto IMPL-2 $0.480488 de $1.00 (libro `var/impl2_experiment_budget.db`).
- Verificar: `.venv/bin/pytest -q tests` → 256 passed, 3 skipped; `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Abierto: CR-017 (PROPUESTA, B.1–B.5 PENDING del propietario).
- Siguiente acción autorizada: iniciar IMPL-3 «Integración cuantitativa» (ML, Regime y Strategy Engine; architecture.md §7 fila 3) solo con indicación del propietario, poblando sus FEAT desde el contrato v1.5.

## IMPL-2 «Agentes especializados» (2026-11-20) — criterios cumplidos, esperando aprobación de cierre

**Actualización 2:** evaluación cualitativa APROBADA por el propietario; QA ronda 1 sin bloqueantes ni mayores (1 de 2 rondas usadas); G4 PASS con alcance IMPL-1 + IMPL-2; FEAT-008..014 en READY_FOR_REVIEW (salida propuesta en `impl2_exit`: 008/013 DONE, resto DONE-PARTIAL). CR-017 (fuente de noticias y `macro_data`) en PROPUESTA. Siguiente: aprobación de cierre de IMPL-2 por el propietario; luego IMPL-3 (Integración cuantitativa) solo con su indicación.

(Estado anterior:)

**Actualización:** configuración de DEC-016 APROBADA; corridas finales `IMPL2_2026-11-19T2358Z_final-1` y `IMPL2_2026-11-20T0001Z_final-2` PASAN (14/14, cero críticas). Gasto IMPL-2 $0.480488 de $1.00. Siguiente: evaluación cualitativa del propietario sobre los `.md` → QA independiente → G4 → aprobación de cierre.

(Estado anterior:)

**Estado:** plan aprobado (DEC-016, Q36–Q40; `harness/plans/IMPL-2_plan.md`). FEAT-008..014 registradas (PENDING) en `feature_list.json` v1.2.0. Pasos 1–4 hechos; paso 5 (aprobación de la configuración en DEC-016) PENDIENTE del propietario. Sin commit.

- Infraestructura: `tests/calibration/` (tope de USD 1.00 con aviso al 80% y reserva atómica; 14 escenarios congelados, v2 SHA-256 `8f68e9a8…`; comprobaciones V1–V8; ejecutor con informe JSON y MD). Pruebas: `tests/unit/test_impl2_calibration.py`.
- Propuesta: effort medium en los 5; macro_analyst y strategy_analyst con prompt 0.2.0 (ya en `prompts.py`); resto sin cambio.
- Gasto IMPL-2: $0.235959 de $1.00. Suite: 256 passed, 3 skipped.
- Abierto para el propietario: Macro Analyst en INSUFFICIENT_DATA por `macro_data` vacío (sin fuente en el contrato).
- Siguiente acción autorizada tras la aprobación: dos corridas finales consecutivas (`RUN_ANTHROPIC_LIVE=1 .venv/bin/python -m tests.calibration.run_battery --label final-1`, luego `final-2`), evaluación cualitativa del propietario sobre los `.md`, QA independiente (≤ 2 rondas, sonnet), G4 con alcance IMPL-2. No declarar DONE sin aprobación.
- Sub-agentes usados en IMPL-2: 0.

## Cierre de IMPL-1 (2026-11-19) — transición a IMPL-2

**Estado:** FASE 2 EN CURSO (autorizada 2026-11-19). **IMPL-1 «Fundamentos de integración» CERRADA** con el criterio de salida fijado por el propietario. Contrato **v1.5** (CR-015, CR-016; DEC-014, DEC-015). G0..G4 PASS (G4 con alcance IMPL-1); G5..G7 PENDING.

### Estado de las funcionalidades (feature_list.json v1.0.0)

| FEAT | Estado | Dependencia explícita |
|---|---|---|
| FEAT-001 Contrato universal de mensajes | DONE | — |
| FEAT-002 Versionado de contratos | DONE-PARTIAL | IMPL-3: versionado de estrategias (Strategy Engine) |
| FEAT-003 Registro de eventos y trazabilidad | DONE-PARTIAL | IMPL-5: TC-AC-04 completo (Risk Manager, órdenes); G6: protección del archivo SQLite |
| FEAT-004 AI Provider Adapter | DONE | IMPL-2: calibración de effort |
| FEAT-005 AI Orchestrator | DONE | IMPL-2: calibración de prompts; IMPL-3: normalización TRADE_PROPOSAL → §4.1 |
| FEAT-006 Control de costo de IA | DONE-PARTIAL | IMPL-4: aviso por Telegram; propietario: límite en consola Anthropic; G6: conciliación con factura |
| FEAT-007 Aislamiento de credenciales | DONE-PARTIAL | IMPL-4: Telegram (TC-SEC-006/007) y REQ-G-059 con Risk Manager; IMPL-6: permisos de Binance; G6: limitaciones de un solo proceso |

Cada dependencia tiene justificación en `feature_list.json` → `impl1_exit.deferred`. Verificado por QA ronda 4 (CONFORME).

### Qué existe (src/swingpilot/)
- `contracts/`: mensaje universal (31 eventos), versionado, contratos de los 5 agentes.
- `audit/`: EventStore append-only con rechazo de secretos.
- `ai/`: adaptador Anthropic (modelos exactos, 1 reintento, tope duro con reservas), orquestador (Fases 3–5), prompts 0.1.x, presupuesto y EntryGate.
- `security/`: CredentialVault por ámbito, comprobaciones de arranque.
- `bootstrap.py`: `build_ai_stack` conecta todo con Fail-Closed.

### Cómo verificar
- `.venv/bin/pytest -q tests` → 233 passed, 3 skipped.
- `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Prueba real (cuesta ~$0.03): `RUN_ANTHROPIC_LIVE=1 .venv/bin/pytest -v tests/integration/test_anthropic_live.py` (requiere `.env` en 600 con ANTHROPIC_API_KEY). Gasto acumulado del mes: $0.053506 (`var/ai_budget.db`, local).

### Para IMPL-2 «Agentes especializados» (architecture.md §7, fila 2)
- Criterio de salida del contrato: los agentes trabajan coordinadamente, conservan sus resultados y expresan desacuerdos sin producir autorizaciones financieras.
- Pendientes que entran en IMPL-2: calibración de prompts (0.1.x) y de `effort` por agente; costo real por ciclo; observaciones de la prueba real (el Macro Analyst listó una nota de método como evento y marcó FACT un ítem SPECULATION).
- Antes de empezar: poblar `feature_list.json` con las FEAT de IMPL-2 desde el contrato v1.5 (no inventar).
- Pendientes del propietario: límite de gasto en la consola de Anthropic; zona horaria de otros cortes mensuales (al implementarlos); REQ-G-P08 (fiscal, diferido).
- Sub-agentes: esta sesión usó 4 (QA, sonnet, ~298K tokens), por encima del tope orientativo de 200K. Abrir sesión nueva para IMPL-2.

### Siguiente acción autorizada
Iniciar IMPL-2 cuando el propietario lo indique. (Las secciones siguientes son del cierre de FASE 1; su frase «FASE 2 BLOQUEADA» queda superada.)

## Cierre de sesión 2026-11-19 — siguiente acción

- **G3 = PASS** (2026-11-18): el propietario aprobó el contrato técnico ("APRUEBO EL CONTRATO TÉCNICO v1.0"). Contrato v1.3 (CR-011..CR-013; 2026-11-19) en `implementation/`; pendientes de FASE 2: reverificar el OCO contra el exchange real, tipo de la pierna TP, esquema del evento de señal de salida, nombres de motivos de NO_SETUP.
- Decisiones: DEC-001..DEC-013. Change requests CR-001..CR-013 aprobadas y aplicadas (CR-011: candidatos en conflicto, Walk-Forward, sizing; CR-012: stop OCO con STOP_LOSS de mercado; CR-013: fuente de datos y snapshot; todas 2026-11-19; contrato v1.3). CONF-006 resuelta. Verificación: G2 (2026-11-13) y VER-003 (re-verificación y cierre).
- Producción en Laptop B; desarrollo e investigación en Laptop A; vigilancia con servicio externo (DEC-007). IA: Haiku 5.5 en 4 agentes, Sonnet 5.5 en Decision Synthesis (DEC-009).
- Pendiente diferido: REQ-G-P08 (validación fiscal con contador); bloquea cálculos fiscales, no FASE 2.
- Cambios al contrato desde ahora: solo con solicitud de cambio aprobada y versionado (v1.x).
- **FASE 2 BLOQUEADA** hasta la frase exacta "AUTORIZO INICIO DE FASE 2". Código funcional creado: NINGUNO.
- Siguiente acción autorizada: esperar autorización de FASE 2. Al iniciarla: poblar `feature_list.json` desde el contrato aprobado, empezando por la Fase 1 de implementación (Fundamentos de integración, architecture.md §7).

> Actualizado: 2026-11-18 — FASE 1 completa: G0..G3 PASS; contrato v1.0 aprobado; FASE 2 pendiente de autorización

---

## Estado Actual de Gates

| Gate | Nombre | Estado | Requiere aprobación humana |
|------|--------|--------|---------------------------|
| G0 | Integridad y registro documental | **PASS** | No |
| G1 | Cobertura de extracción | **PASS** | No |
| G2 | Consistencia y trazabilidad | **PASS** | No |
| G3 | Aprobación humana del contrato | **PASS** (propietario, 2026-11-18) | SÍ |
| G4 | Pruebas de implementación | PENDING | No |
| G5 | Integración y regresión | PENDING | No |
| G6 | Seguridad | PENDING | No |
| G7 | Aprobación de release | PENDING | SÍ |

---

## Próxima Acción Requerida: autorización de FASE 2

G3 aprobado el 2026-11-18. FASE 2 requiere la frase exacta del propietario: **"AUTORIZO INICIO DE FASE 2"**. Paquete de revisión de G3: `harness/gates/G3_resumen_contrato.md`.

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

| ID | Estado |
|----|--------|
| CONF-001 | RESUELTA (DEC-001) — TRACEABILITY_MATRIX = BORRADOR |
| CONF-002 | RESUELTA (DEC-001) |
| CONF-003 | RESUELTA (DEC-003) — régimen 605; tratamiento fiscal sujeto a validación profesional (P08) |
| CONF-004 | RESUELTA (DEC-002) — 1.5% máximo vinculante |
| CONF-005 | RESUELTA (DEC-002) — solo BTC/USDT |

**CR-001** APROBADA y aplicada el 2026-11-17 (1–2% y ETH/USDT eliminados; TRACEABILITY_MATRIX corregida).

**Historial fiscal (confirmado por el propietario el 2026-11-17, cerrado):** régimen 616 hasta el 12/10/2025; el 605 debió iniciar el 13/10/2025; el aviso ante el SAT se presentó el 17/11/2026. No hay fecha pendiente.

**Diferido por el propietario (2026-11-17):** la validación con contador (REQ-G-P08) queda para después; no se calcula nada fiscal mientras tanto. G3 se mantiene PENDING.

---

## Parámetros PENDING

**Resueltos en DEC-004 (2026-11-17):** P01–P06, P19, P20 (fuente FX, antigüedad, comisión, slippage, filtros, Telegram, reconciliación, tolerancia de precio).

**Resueltos en DEC-005 (2026-11-17):** P10–P17, P21–P24 (investigación y ML).

**Resueltos en DEC-006 (2026-11-17):** P07, P18, P25 y P26 (nuevo: recuperación ante fallos).

**Todos los parámetros del Módulo 15 están resueltos excepto P08 (diferido).**

**CR-002** (stop-loss en Binance) APROBADA y aplicada el 2026-11-17 (REQ-G-031, eventos STOP_ORDER_*, TC-STOP-001..006).

**Diferido por el propietario:** P08 (validación fiscal con contador; incluye tratamiento de ganancias y periodo 13/10/2025–17/11/2026).


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

1. G3 aprobado por el propietario (2026-11-18); G7 solo con autorización humana explícita
2. Si el propietario aprueba G3, marcar gate_status.json con `approved_by: "propietario"`, `approved_at: "fecha"` y `evidence: "texto de la aprobación"`
3. FASE 2 está BLOQUEADA hasta "AUTORIZO INICIO DE FASE 2"
4. Los archivos en `docs/` son SOLO LECTURA — fuentes documentales del propietario
5. Los archivos en `src/` están vacíos — correctamente, hasta FASE 2
6. Los parámetros PENDING no se rellenan por suposición — solo con información real del propietario o del sistema Binance
7. No crear código funcional de SwingPilot hasta la autorización de FASE 2

---

## Estado CR-023 B7 (2026-11-26, cierre B7.4c)

- B7 implementado sin commit: `window_evaluation.py` (nuevo), `acceptance.py`, `backtest.py`, `partitions.py` modificados; 5 archivos de pruebas/auxiliar nuevos en `tests/unit/`. HEAD `8a50604`.
- Verificación (exit codes reales): unit 1353 passed (0); security/aislamiento 3 passed (0); validate_gates/manifest/requirements OK (0/0/0). Registro de experimentos intacto (md5 `8af8e3e0…`).
- Decisiones aprobadas: procedencia de ventana vía `FinalEvaluationData`; LOCKBOX perezoso (solo tras OOS ELIGIBLE_FOR_HUMAN_REVIEW). Esquema D6 y métodos estadísticos DIFERIDOS.
- Limitaciones: controles en proceso sin tamper-evidence; ninguna evaluación real autorizada; B8–B9 sin iniciar; D3 abierta, D4 bloqueada.
- QA independiente pendiente (sesión distinta, solo lectura) antes de cerrar FEAT. No hay commit ni push autorizados.

### B7.4d — Resoluciones del propietario (2026-11-26)
- R1 (opción B): `FinalWindowProvenance` inmutable emitido por el cargador y adjunto a `FinalEvaluationData` (grant, experimento, snapshot, ventana, registro de consumo, digests canónicos). R2: manifiesto y cargador del LOCKBOX resueltos perezosamente tras OOS favorable, con autorización humana explícita.
- Forma del registro intacta; protección en modelo de proceso confiable, sin tamper-evidence. Corrige la línea de procedencia de B7.4c (era inferencia).
- Pendiente: implementar/verificar R1 y R2 (no hecho). Sin commit ni push.

---

## Estado CR-024 I4 (2026-11-26)
- CR-024 I1–I3 implementado sin commit sobre HEAD `ce49bbf`. Verificación real: unit 1429 passed (0), security 3 passed (0), validadores gates/manifest/requirements OK (0/0/0); sin skips. Registro real intacto (md5 `8af8e3e0…`); sin `window_results/`.
- Recuperación explícita: `python -m swingpilot.research.cli recover-window-result --experiment <ID> --window {OOS|LOCKBOX} --confirm`. Almacén: `research/experiments/window_results/`. LOCKBOX autoritativamente bloqueado sin OOS favorable persistido (no EVIDENCE_ONLY).
- Limitaciones: confianza en proceso sin tamper-evidence; fixture favorable fabricado (`tests/unit/cr024_oos.py`), evidencia genuina en E2E i2c/i3; sin evaluación real; ET-8, B8/B9 sin iniciar; D3 abierta, D4 bloqueada.
- Obligatorio: QA independiente (sesión distinta, solo lectura) antes de cerrar FEAT. Sin commit ni push autorizados.
