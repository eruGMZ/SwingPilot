# CR-025 — Integridad autoritativa continua de la evaluación (V9 en ET-9 y ET-10)

**Fecha:** 2026-11-26 (revisión 3, definitiva)
**Estado:** **APROBADA por el propietario (2026-11-26; revisión 3 íntegra, con las seis disposiciones de conflictos pendientes) y APLICADA contractualmente** (contrato v1.13; `feature_list.json` v1.25.0). La implementación, las pruebas ejecutables, la verificación independiente y el cierre de FEAT siguen **PENDIENTES**; el cableado de ET-10 en el Strategy Engine queda **diferido a B9**. Sin commit ni push.
**Origen:** opción **C** aprobada por el propietario: extender la integridad autoritativa de CR-024 a ET-9 y ET-10.
**Vinculada a:** CR-024 (resultados, marcador, `evaluation_hash`, favorable autoritativo, ET-8), CR-023 (§C.9, §D.8, decisión 5), CR-021 (S1–S4, `RegistryCorruptError`).
**Alcance mínimo:** exigir que los resultados persistidos de OOS y LOCKBOX sigan siendo válidos, favorables y ligados a la aprobación ET-8 original en cada promoción y en cada ciclo con posible entrada nueva.
**Fuera de alcance (conservado):** P5 de CR-021 (PENDIENTE), O3/O4, D6 diferida (sin umbrales ni métodos estadísticos), D3 ABIERTA, D4 bloqueada, CONF-010. Sin tipos de registro nuevos, estados nuevos, atestaciones nuevas (ni por ciclo) ni códigos de error nuevos.

---

## A. Problema

CR-024 exige resultados favorables autoritativos en ET-4..ET-6, `resolve_lockbox` y ET-8, y su texto afirmaba que «el recálculo de ET-9/ET-10 no cambia». Tras `APPROVED`, un resultado persistido podía desaparecer o corromperse, o dejar de coincidir con lo aprobado, sin que ET-9 ni ET-10 (V2, V3, V4post, V5, V8 y RELEASE) lo detectaran.

## B. Cambio

### B.1 Comprobación V9 («integridad autoritativa ligada a la aprobación»)

V9 se añade a ET-9 y ET-10. Su resultado es `OK`, `TECH` o `HISTORICAL`. Todo fallo es `TECH` (**nunca** `METHOD`): la pérdida de integridad no es una determinación metodológica. En la precedencia de CR-023 §D.8, `UNDETERMINABLE` prevalece. V9 solo se evalúa si el estado del experimento es `APPROVED`; en otro estado devuelve `TECH`.

### B.2 Ligadura persistida en la evidencia de `APPROVED` (autoridad = registro append-only)

La transición `HUMAN_REVIEW → APPROVED` escribe en su `evidence` la clave reservada `approval_binding` (único cambio de esquema; sin tipo de registro nuevo ni clave de nivel superior nueva):

```
approval_binding = {
  "schema": 1,
  "prereg_sha256": "<64 hex minúsculas>",
  "oos_evaluation_hash": "<64 hex>",
  "lockbox_evaluation_hash": "<64 hex>",
  "attestation_sha256": "<64 hex>" }
```

- Conjunto de claves **cerrado**; `schema == 1`; hex en minúsculas de exactamente 64 caracteres; los dos `evaluation_hash` distintos entre sí. Cualquier otra clave, tipo o longitud → `TECH`.
- `attestation_sha256` = SHA-256 de los bytes UTF-8 exactos de la única línea `AUTORIZA: APROBACION …` del experimento, **sin el salto de línea final**.
- **Quién la escribe:** solo `transition()`, dentro del bloqueo, a partir del valor que devuelve `ApprovalCheck` (contrato de retorno `(motivo, ligadura)`), construido con los `evaluation_hash` de los marcadores verificados, el SHA-256 del preregistro congelado y la huella de la línea validada. Una `approval_binding` aportada por el llamador, o un check que no la devuelve, rechaza la transición (Fail-Closed).
- **Autoridad:** el registro. El texto de decisión es editable y no concede nada; solo puede hacer fallar V9 (B.4).

### B.3 Separación de verificadores

| Módulo | Contenido | Usan |
|---|---|---|
| **`verify_result_evidence(records, store, eid, partition)`** (compartido) | Un único marcador (copia idéntica = el mismo); evidencia con SHA-256 = `evaluation_hash` y lectura estricta; consumo único del dueño con `consumed_line_sha256` coincidente; `prereg_sha256` vigente; favorable autoritativo (CR-024 B.4). Devuelve `evaluation_hash` y `consumed_line_sha256`. | ET-8 y V9 |
| **ET-8 (`_approval`)** | Gramática y unicidad de la línea `APROBACION`; línea en el `decision_ref` de la aprobación; SHA y hashes citados = los del módulo compartido; V4-post del dueño; construye y devuelve `approval_binding`. | Solo ET-8 |
| **V9 (post-aprobación)** | Exactamente una transición `APPROVED`; `approval_binding` válido por esquema cerrado, o transición en `HISTORICAL_APPROVALS`; por partición, módulo compartido y `evaluation_hash` recalculado = el de la ligadura; `prereg_sha256` de la ligadura = congelado; orden: consumo < marcador por partición, OOS completo < consumo LOCKBOX, LOCKBOX completo < `APPROVED`; atestación original (B.4). | Solo ET-9 y ET-10 |

### B.4 V9 verifica la atestación original (sin aprobación nueva)

V9 localiza el documento de `evidence.decision_ref` de la transición `APPROVED` con las reglas de `_decision_text` (nombre `DEC-NNN…md`, dentro de `docs/decisions`, sin enlace simbólico), exige exactamente una línea `APROBACION` del experimento, la parsea con la gramática estricta y comprueba: (a) su SHA-256 = `attestation_sha256`; (b) el SHA-256 del preregistro y los dos hashes de la línea = `prereg_sha256`, `oos_evaluation_hash` y `lockbox_evaluation_hash` de la ligadura. Documento ausente, ilegible, línea ausente, duplicada o alterada, o discrepancia → `TECH`. La huella cubre solo esa línea: el resto del documento puede editarse sin efecto. No se pide atestación nueva ni por ciclo.

### B.5 Aprobaciones históricas: conjunto cerrado, inicialmente vacío

`HISTORICAL_APPROVALS` es un conjunto cerrado de SHA-256 de los bytes exactos de la línea `TRANSITION → APPROVED` del registro (sin salto final), fijado en el contrato y en una constante de código. Está **vacío** en v1.13 (el registro real no contiene ningún `APPROVED`). Solo se amplía con una enmienda contractual aprobada por el propietario; nunca por detección estructural, ausencia de línea o atestación, ni parámetro del llamador. Un `APPROVED` sin `approval_binding` y fuera del conjunto → `TECH`: **la ausencia de ligadura nunca otorga exención**. Dentro del conjunto, V9 devuelve `HISTORICAL` y se aplican solo los controles existentes de ET-9/ET-10.

### B.6 Efectos

- **ET-9:** `TECH` → promoción rechazada como fallo técnico, con causa «V9: …». Corre dentro del bloqueo de `promote` mediante `PromotionCheck`; no hay ventana ni bloqueo anidado.
- **ET-10:** `TECH` → `STRATEGY_CANDIDATE` con `result_status = ERROR`, `error.code = ELIGIBILITY_UNDETERMINED`, `stage = STRATEGY_EVALUATION` y sobre `FAILED`; sin entradas nuevas ni llamadas a LLM; nunca `NO_SETUP`. La causa «V9: …» consta en el mensaje y en la auditoría; sin código de error nuevo.
- **Protección intacta:** `STRATEGY_EXIT_SIGNAL`, `STOP_ADJUSTMENT_REQUESTED`, el stop en el exchange (REQ-G-031), los cierres protectores, la reconciliación y el modo seguro (REQ-G-032, REQ-G-P26) no dependen de V9 ni se suprimen. Ningún registro se reescribe; no hay reparación automática.

### B.7 ET-10: lectura coherente y sincronización

- **Una vez** por ciclo con posible entrada nueva; **sin caché** entre ciclos; V9 es de solo lectura.
- La instantánea se toma **bajo el bloqueo exclusivo del registro**, solo para leer: `_load`, evidencia de ambas particiones, documento de decisión y V9; después se libera. Esto evita la cola parcial de una escritura concurrente (`records()` no toma el bloqueo).
- **Plazo de adquisición: 2 s** medidos con `time.monotonic()`, `flock` con `LOCK_NB` consultado hasta vencer; **una sola ventana** de adquisición por ciclo y **sin reintentos adicionales**. Vencimiento → `TECH` («V9: bloqueo del registro no obtenido en 2 s»). Es una variante nueva y exclusiva de ET-10; `_locked` y los escritores conservan su semántica bloqueante; ET-9 no cambia. ET-10 no se invoca dentro de otro bloqueo del mismo registro.
- Un cambio posterior a la instantánea se detecta en el ciclo siguiente; no hay recomprobación antes de emitir el candidato (ventana residual documentada).
- `decisions_dir` debe estar disponible para ET-10; si no, `TECH`.
- **Diferido a B9:** el cableado de ET-10 en el Strategy Engine (hoy ningún código del motor llama a `eligibility` para ET-10; parte de AC-020-2). CR-025 solo lo especifica.

### B.8 Enmienda expresa de CR-024

Quedan sustituidas, con nota de vigencia (texto original conservado): CR-024 §B.8 y la frase final de REQ-G-P23 «el recálculo de ET-9/ET-10 no cambia» → «ET-9 y ET-10 incorporan V9 (CR-025)». CR-024 §F gana la limitación continua. CR-023 §C.9 (matriz: V9 en ET-9/ET-10), §D.8 (la tabla `UNDETERMINABLE` añade «V9») y §H (sin tipos de registro nuevos) llevan nota de vigencia.

## C. Identificadores afectados (verificados; contrato v1.12 → v1.13)

- **Requisitos modificados:** REQ-G-104, REQ-G-P23. **Sin cambios:** REQ-G-103, REQ-G-106, REQ-G-109, REQ-G-P17, REQ-G-031, REQ-G-032, REQ-G-P26.
- **Documentos del contrato:** `requirements.md`, `architecture.md`, `api_contracts.md` (§B.7, causas de `ELIGIBILITY_UNDETERMINED`), `data_flow.md` (§3), `test_plan.md`.
- **Criterios:** AC-017-1, AC-017-15, AC-019-2 y AC-020-2 enmendados; **AC-017-16** nuevo.
- **Pruebas:** TC-ML-009 y TC-ML-028 enmendadas; **TC-ML-030** nueva (`tests/unit/test_cr025_continuous_integrity.py`).
- **Código (autorización separada):** `independence.py` (`verify_result_evidence`, V9, `STAGES`, `_approval`); `experiments.py` (contrato de retorno de `ApprovalCheck`, inyección y rechazo de `approval_binding`, variante de bloqueo con plazo); `ml/registry.py` (ET-9); Strategy Engine (cableado de ET-10, **B9**).

## D. Pruebas

- Las fixtures históricas (`seed_historical_approval`) pueden usar **parches de módulo solo de pruebas** de `HISTORICAL_APPROVALS`, por prueba (`monkeypatch`), en casos de compatibilidad aislada que lo declaran. Sin parámetro de producción ni variable de entorno.
- Las pruebas genuinas de ET-8, ET-9 y ET-10 y las de vías de esquiva ejercitan los controles reales: sin parches ni fixtures históricas.
- Una prueba de guarda comprueba que el conjunto está vacío en el código entregado, y otra que un `APPROVED` sin ligadura y fuera del conjunto es `TECH`.

## E. Disposiciones del propietario (2026-11-26)

D1 V9 técnica; D2 una vez por ciclo con lectura coherente bajo bloqueo y plazo de 2 s; D3 ligadura persistida con `attestation_sha256` y conjunto histórico cerrado y vacío; D4 enmienda expresa de CR-024; D5 B8.1–B8.3 sin commit conservados e integración de CR-025 antes del cierre de B8; ET-10 diferido a B9. Conflictos: (1) V9 relee texto editable (solo puede hacer fallar V9; aceptado); (2) `decisions_dir` en ET-10; (3) ET-10 sin cablear; (4) «sin reintentos adicionales» = una sola ventana de 2 s; (5) contrato de `ApprovalCheck` y pruebas B8.2; (6) reconciliación de `session-handoff.md`: todos resueltos como se indica arriba.

## F. Limitaciones residuales

Modelo de proceso confiable (registro no tamper-evident); ventana de un ciclo en ET-10 entre instantánea y emisión; editar o borrar la línea `APROBACION` o su documento bloquea promoción y entradas nuevas como `TECH` hasta restaurarlo o enmendar el contrato; ampliar el conjunto histórico exige enmienda; P5, O3/O4 y D6 sin resolver.

## G. Aplicación contractual (2026-11-26)

Contrato v1.12 → **v1.13**; `feature_list.json` v1.24.0 → **v1.25.0**. Sin cambios de código, pruebas, registro ni gates. **Pendientes:** implementación y pruebas (autorización separada; ET-10 en B9), verificación independiente, P5, O3/O4, D6; B8 permanece abierta hasta integrar CR-025.


**[Nota de vigencia 2026-11-27, documental; texto original conservado]:** el cableado de ET-10 «diferido a B9» está implementado (B9.1–B9.4, sin commit) y verificado (`pytest tests/unit tests/security` → 1537 passed, 0 skipped, 0 failed; validadores 0/0/0). B8 y la integración de CR-025 en ET-8/ET-9 constan en `eb034dc`. Siguen PENDIENTES: verificación independiente, cableado de producción del `EvidenceProvider`, verificación del aislamiento RESEARCH, deuda de dependencia de `cli._approve_inputs`, CLI de promoción ML (diferida), P5, O3/O4, D3, D4, D6.
