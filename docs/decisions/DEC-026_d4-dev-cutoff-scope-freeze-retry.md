# DEC-026 — D4: corte de desarrollo D_dev, política de Scope Freeze y capa de reintentos HTTP exclusiva de D4

**Fecha:** 2026-11-27
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario del 2026-11-27 («Execute D4-IMPL only»): aprobación explícita de los bloques A, B y C. La autorización D (descarga real) permanece **BLOQUEADA**.
**Línea base:** `d6830a3`; contrato v1.13. Esta decisión **no modifica el contrato ni decisiones históricas**.

## Decisión

| N.º | Elemento | Decisión |
|---|---|---|
| A | `D_dev` | `D_dev = 2026-11-01T00:00:00Z`, **exclusivo**, sujeto a compatibilidad contractual (REQ-G-109, CR-023 §C.1) y a la exclusión de ventanas reservadas por la fuente autoritativa. Los datos de desarrollo pueden incluir exposiciones previas inventariadas **sin** conceder independencia confirmatoria (CR-023 §C.7). |
| B | Scope Freeze | Permite correcciones de errores necesarias y ajustes operativos expresamente autorizados. Todo cambio de requisitos vinculantes exige aprobación separada del propietario. |
| C | Capa de reintentos | Una única capa HTTP de reintento **opt-in y exclusiva de D4** (`src/swingpilot/research/d4_build.py`): máximo 3 intentos totales por petición transitoria; espera de 1 s y luego 2 s; sin reinicio automático de la construcción completa; solo fallos de red/API explícitamente clasificados como transitorios (timeout, red, HTTP 500/502/503/504); nunca HTTP 429/418, permisos, integridad, fechas, corrupción ni límites. Agotados los reintentos se cancela la construcción completa conservando el rollback y el sellado vigentes. Sin estado ABORTED contractual, evento del registro ni cambio de esquema de snapshot. Comportamiento por defecto del cliente (incluidas la reconexión LIVE y las snapshots de evaluación) sin cambios. |
| C-diag | Diagnóstico | Evidencia operativa aislada en `var/diagnostics/d4/` (JSON Lines, campos cerrados: run ID, snapshot ID, D_dev, UTC, etapa, intento, clasificación, estado HTTP, tiempo transcurrido, código de salida). Sin credenciales, cabeceras, cuerpos, URL completas ni variables de entorno; fuera de snapshots, resultados experimentales y entradas del motor. |
| D | Descarga real | **BLOQUEADA.** Esta decisión no la autoriza; el punto de entrada real se niega sin `--confirm`, referencia de autorización y entorno libre de credenciales. |

## No autoriza

Descarga real, SNAP-0001, OOS, LOCKBOX, preregistro, evaluación confirmatoria, operaciones financieras, D5–D7, P5, O3/O4, cambios en CONF-010, cierres de FEAT, cambios de gates, commit ni push. El procedimiento futuro está preparado en `implementation/d4_execution_procedure.md` y **no se ejecuta**.

## Anexo — Aceptación de QA sintético (2026-11-27)

Hallazgo M-1 de D4-QA-SYNTHETIC (CONDITIONAL) resuelto y aceptado por el propietario; L-1 aceptada como limitación sin cambios de código. Detalle, causa raíz y hashes en `progress.md` (entrada D4-QA-CLOSE). Evidencia en `var/incident_evidence/D4-M1/`. Esta aceptación es **solo sintética**: no valida datos reales ni cierra D4. La decisión D permanece **BLOQUEADA**; el cuerpo de la decisión y el contrato v1.13 no cambian.

## Anexo — Campos de diagnóstico D4-OBS-FIX (2026-11-28)

Aprobado por el propietario (resoluciones A–E, 2026-11-28) tras el fallo `BUILD_REJECTED` de D4-EXEC (autorización `OWNER-D4-D-20261128-f4e4e43` consumida; causa original desconocida). La lista cerrada de campos de C-diag se amplía **solo** con `interval`, `error_type`, `root_error_type` y `reason_code`; `stage` admite etapas refinadas (`server_time`, `download`, `prepare`, `preflight`, `seal`, `write`, `reserved_windows`) y `UNKNOWN`. Los tipos de error provienen de una lista cerrada; `reason_code` de un vocabulario cerrado o la clasificación de transporte; la causa no reconocible fiablemente se registra como `UNKNOWN`. Se añade un resumen de una línea en stderr con esos campos. Prohibido registrar mensajes de excepción, credenciales, cabeceras, URL, cuerpos, entorno o datos de mercado. No cambia reintentos, autorización, sellado, rollback, ventanas reservadas, el cuerpo de la decisión ni el contrato v1.13. La descarga real (D) permanece **BLOQUEADA**.

**Cierre D4-OBS-CLOSE (2026-11-28).** **D4-OBS-QA: CONDITIONAL PASS (conservado); condiciones ACEPTADAS por el propietario (2026-11-28).** Limitaciones residuales aceptadas: L1 `reason_code` identifica la procedencia observable del fallo, no la causa raíz probada; L2 los vocabularios cerrados los imponen los llamadores de producción, no exhaustivamente el registrador; L3 los fallos de transporte pueden usar la etapa genérica `download`; L4 dependencia de la ruta del traceback y fallback `UNKNOWN` aceptados; L5 límite de profundidad de la cadena y recorrido exclusivo de `__cause__` aceptados. Evidencia: D4-OBS-FIX 261 pruebas focalizadas OK; D4-OBS-QA independiente 49 + 180 OK; tres validadores OK; cero hallazgos bloqueantes; cinco limitaciones aceptadas. SHA-256 evidencia del fallo `24c7dd7581bbd28c37f519718ec72f173bd91e6c4e02fbb21ff6e0b48d23eb12`; registro `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b`. **Causa original de `BUILD_REJECTED` sigue DESCONOCIDA.** Recuperación de observabilidad (D4-OBS-CLOSE): **ACEPTADA**, lista para consolidación Git manual por el propietario. Autorización D original **CONSUMIDA**; D4-EXEC-R1 **BLOQUEADA** (requiere nueva autorización independiente). La decisión original y el contrato v1.13 no se modifican.
