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
