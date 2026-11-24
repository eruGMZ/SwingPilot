# DEC-023 — Aprobación de CR-021 (durabilidad confirmada como condición de acceso a datos; `EVALUATION_PERSISTED`)

**Fecha:** 2026-11-24
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-24: aprobación expresa de CR-021 revisión 2 y autorización de su aplicación documental al contrato de requisitos v1.9. Antes: bloqueo contractual de QA-CR020-03 aceptado, preparación de CR-021 autorizada, aceptación provisional del diseño conceptual y revisión 2 sobre R1–R3 (CR-021 §B.1).
**Alcance:** aprueba `harness/change_requests/CR-021_durabilidad-autorizacion-evaluacion.md` (revisión 2) y autoriza **solo su aplicación documental**: contrato v1.8 → **v1.9**, criterios de aceptación, especificaciones de prueba y referencias de trazabilidad. **No autoriza** implementar CR-021, adaptar pruebas ejecutables, modificar el registro real, cambiar estados de FEAT ni hacer commit o push. Cada uno requiere una autorización posterior y expresa.
**Relación con CR-020 / DEC-021:** CR-021 **sustituye** las obligaciones afectadas de CR-020 (§C.1, definición de «configuración evaluada»; §C.3, tipos de registro; §C.3.2, paso 1 del orden obligatorio, «Escritura fallida o incierta» y «Significado») y de ORQ-017-01 (unicidad de `deviation_id`), sin reescribir su texto ni su significado histórico. CR-020 y DEC-021 se conservan como evidencia aprobada.

## Decisión

| N.º | Elemento | Decisión |
|---|---|---|
| 1 | `EVALUATION_PERSISTED` (CR-021 §D.3) | Registro append-only de certificación, vinculado por SHA-256 a las líneas exactas que certifica y escrito solo tras un `fsync` correcto de esa evidencia. Aprobado |
| 2 | Invariantes I2a / I2b (§F.1, §F.8) | Aprobados, con las enmiendas de REQ-G-P17, CR-020 §C.3.2 y TC-ML-023 |
| 3 | Cómputo conservador de intentos legibles no confirmados (§D.1, §F.8) | Cuentan mientras consten en el registro; se acepta la posibilidad documentada de su pérdida no detectada antes de cualquier congelación cuando nunca se autorizó el acceso a datos. Aprobado |
| 4 | Interpretación R2 (§F.4) | El acceso depende de la durabilidad de la evidencia certificada, no de la del marcador. Aprobado |
| 5 | Fallo del `fsync` del marcador (§F.4) | La operación original informa incertidumbre; con un marcador válido legible se permiten el acceso y el reintento idempotente sin escritura. Aprobado |
| 6 | Desaparición del marcador (§F.4) | Acceso denegado, sin eliminar ni duplicar la evidencia duradera de la evaluación. Aprobado |
| 7 | Recuperación (§D.2, §D.4) | Copias byte a byte idénticas; conservación del `deviation_id` y de las identidades lógicas; cronología de la primera aparición. Aprobado |
| 8 | Duplicados conflictivos (§D.2, §F.3) | Rechazo Fail-Closed. Aprobado |
| 9 | Política de corrupción P1–P5 (§F.2) | Completa, incluida la cola sin salto de línea final. Aprobado |
| 10 | Conciliación manual (§F.2 P5, §F.6) | Procedimiento diferido; sin reparación automática destructiva; toda recuperación operativa futura exige un procedimiento aprobado y autorización humana explícita. Aprobado |
| 11 | Limitaciones residuales (§I) | Aceptadas, sujetas a los supuestos S1–S4 del sistema de archivos y a la verificación posterior en el despliegue (G6, Laptop B). Aprobado |

**Condición de implementación:** la implementación deberá demostrar P1 en todas las rutas afectadas de lectura, escritura, acceso y evaluación. Comprobar solo el salto de línea final no establece la conformidad.

## Efectos

- **Contrato v1.9:** REQ-G-P17, REQ-G-104 (párrafo de CR-020 y adición de CR-021), TC-ML-020 y TC-ML-023; versión v1.9 en los cinco documentos de `implementation/`.
- **QA-CR020-03:** sigue **sin resolver** hasta la implementación y su verificación. Reproducción: `harness/verification/IMPL-3_QA-CR020-03_reproduccion.py`.
- **CONF-009 y CONF-010:** siguen OPEN. **FEAT-015:** DONE. **FEAT-017:** IN_PROGRESS.
- **Riesgo y ejecución:** ninguno. Solo investigación, sin órdenes (REQ-G-081).
- **Siguen vigentes** las restricciones de DEC-017 y DEC-018. El commit y el push requieren la indicación del propietario.

## Aceptación de la aplicación documental (propietario, 2026-11-24)

El propietario acepta la aplicación documental de CR-021 revisión 2 bajo esta decisión y autoriza congelar el contrato de requisitos v1.9. Acepta las enmiendas contractuales, las actualizaciones de trazabilidad, `feature_list.json` v1.18.0, la conservación de CR-020 como evidencia histórica (nota de vigencia §I) y el artefacto de reproducción sintética de QA-CR020-03.

**Comprobación semántica previa al commit (autorizada):** en REQ-G-104, la frase «Una escritura o un `fsync` de la evidencia fallidos o inciertos no autorizan el acceso» admitía leer «de la evidencia» como referida solo al `fsync`; así, «una escritura incierta» podría abarcar la del marcador y contradecir la interpretación R2 aprobada (punto 4). Aclaración mínima aplicada: «Una escritura o un `fsync` fallidos o inciertos de la evidencia certificada (no del marcador; véase el fallo del `fsync` del marcador más abajo) no autorizan el acceso». Sin otro cambio de significado. Validadores → OK.

Commit autorizado de los 13 archivos de la aplicación documental, sin push. El commit congela el contrato v1.9 **sin implementar** sus requisitos. QA-CR020-03 sigue sin resolver; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
