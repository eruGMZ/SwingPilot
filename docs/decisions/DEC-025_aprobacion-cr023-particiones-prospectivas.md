# DEC-025 — Aprobación de CR-023 (particiones de evaluación prospectivas y frontera de independencia verificable; D3)

**Fecha:** 2026-11-25
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-25 («Owner Approval — CR-023 / DEC-025»): aprobación de la propuesta final de CR-023 con todas las disposiciones previas (D3.1–D3.8, P1–P8, R1–R5, U1–U2, F1–F4) y dos correcciones obligatorias antes de la aplicación contractual (C1, C2). Antes, en la misma fecha: diagnóstico D3 de solo lectura sobre `aca408e`, decisiones D3.1–D3.8, revisiones 1 y 2 y revisión final focalizada.
**Alcance:** aprueba `harness/change_requests/CR-023_particiones-prospectivas-frontera-independencia.md` y autoriza **solo su aplicación contractual y documental**: contrato v1.10 → **v1.11**, `feature_list.json` v1.22.0 → **v1.23.0**, criterios de aceptación, especificaciones de prueba y trazabilidad, y la reapertura focalizada de FEAT-015. **No autoriza** implementación funcional, cambios en pruebas ejecutables, ejecución de la suite o de sondas, modificaciones del registro de experimentos, acceso a datos de mercado, SNAP-0001, el inicio de D4–D7, cambios en los gates, el cierre formal de D3, commit ni push.
**Relación con decisiones anteriores:** CR-023 modifica el contrato derivado de DEC-005 Q7 (P10), DEC-011/CR-011 (estructura 70/15/15 y fórmula de histórico mínimo) y DEC-013/CR-013 (rango, particiones y snapshot única). **Esas decisiones no se reescriben**; sus notas de vigencia constan abajo. CR-020/DEC-021, CR-021/DEC-023 y CR-022/DEC-024 no cambian.

## Decisión

| N.º | Elemento | Decisión |
|---|---|---|
| 1 | Metodología (D3.1–D3.8) | OOS y LOCKBOX prospectivas tras una frontera de independencia verificable; independencia solo con evidencia positiva o aislamiento prospectivo; ámbito BTC/USDT; familiaridad general como limitación; LOCKBOX_OOS_001 incierto y excluido; fixture de IMPL-2 diferida; sin reabrir lo anterior a 2023; exposición externa documentada sin tipo de evento nuevo. Aprobado |
| 2 | P1–P8 (D3) | 5:2 en desarrollo; ventanas de calendario fijas (insuficiencia ⇒ INCONCLUSIVE); un experimento confirmatorio por frontera; ≥ 24 h y `B` a las 00:00 UTC con Git como evidencia operativa; cierre forzoso al cierre de ventana; una snapshot de evaluación por ventana; reapertura focalizada de FEAT-015; `DEVIATION` existente con semántica de independencia. Aprobado |
| 3 | R1–R5 | Niveles I1–I5 y piloto de tasa no confirmatorio; `context` separado de `train_val`; congelación completa; contaminación mecánica; cierre de D3 no solo documental. Aprobado |
| 4 | U1 | REQ-G-P23: elegibilidad recalculada antes de la promoción y del uso operativo; registros APPROVED históricos conservados; la pérdida de elegibilidad bloquea el uso sin impedir la gestión protectora ni el cierre de posiciones. Enmiendas de `api_contracts.md` §B.7, AC-019-2 y AC-020-2. Aprobado |
| 5 | U2 | Almacén recuperable de preregistros dentro de CR-023; **no resuelve O4**, que requiere evidencia, verificación y aceptación propias. Aprobado |
| 6 | F1–F4 | Lista V1–V8; alcance de la contaminación por periodo (el dueño, en cualquier estado); matriz de etapas ET-1..ET-10; digest canónico y continuidad del contexto del LOCKBOX. Aprobado |
| 7 | C1 (corrección obligatoria) | V4 depende de la etapa: V4-pre (ventana no consumida; para el LOCKBOX, OOS consumida) en ET-4..ET-6; V4-post (exactamente un consumo autorizado del dueño, sin reutilización prohibida) en ET-7..ET-10. Incorporada antes de la aplicación |
| 8 | C2 (corrección obligatoria) | Ineligibilidad metodológica válida ⇒ exclusión y `NO_SETUP` (`NO_APPROVED_STRATEGY`, `CONFIRMATORY_ELIGIBILITY_LOST`); fallo técnico que impide determinar la elegibilidad ⇒ `ERROR` (`ELIGIBILITY_UNDETERMINED`, B.7.1), nunca `NO_SETUP`. Ambos bloquean entradas nuevas; salidas, stop en el exchange, cierres protectores, reconciliación y modo seguro siguen disponibles. Incorporada antes de la aplicación |
| 9 | Aplicación | Contrato v1.11 (CR-023 §E); `feature_list.json` v1.23.0; FEAT-015 DONE → IN_PROGRESS (reapertura focalizada; DONE histórico bajo v1.10 conservado); FEAT-017, FEAT-019 y FEAT-020 IN_PROGRESS con criterios actualizados. Autorizada |

## Notas de vigencia (las decisiones históricas no se reescriben)

- **DEC-005 Q7 (P10, «Train 50% / Validation 20% / OOS 15% / LOCKBOX 15%»):** sustituido desde el contrato v1.11 por la región de desarrollo Train:Validation 5:2 y las ventanas prospectivas de REQ-G-109. Se conserva «cada partición de evaluación debe alcanzar el mínimo de P15». Q8 (P15) no cambia.
- **DEC-011 / CR-011 (WF dentro de Train+Val «70%», OOS «15%», LOCKBOX «15%», `H_min = max(38/0.70; 100/(0.70·r); 30/(0.15·r))`):** sustituidos por `H_dev,min = max(38; 100/r)` y `L ≥ k·30/r`. Se conservan 24/2/6/6, el embargo, ≥ 2 ventanas, el agregado de la OOS, la tasa real estimada solo con Train y la regla «no pasa de DESIGN».
- **DEC-013 / CR-013 (rango hasta la fecha de snapshot, tres Parquet en una sola snapshot descargada una vez al iniciar FASE 2, «~111 meses»):** sustituidos por una snapshot de desarrollo y snapshots de evaluación por ventana. Se conservan la fuente, los intervalos, la paginación, los huecos, el hash, el modelo de ejecución, la declaración de régimen y la regla del LOCKBOX consumido.
- **DEC-018 decisión 4:** sin cambio. AC-017-10 concreta «comprobar la integridad de las particiones» como I1 (cierre de D3) + I2 (snapshot de desarrollo verificada, D4). Siguen vigentes «no evaluar OOS ni LOCKBOX» y las demás restricciones.

## Efectos

- **D3 ABIERTA:** la condición 1 de CR-023 §L queda cumplida; siguen pendientes la implementación, la verificación independiente, la reapertura de FEAT-015 y el mecanismo de §D.
- **D4 bloqueada.** D5–D7 sin iniciar. SNAP-0001 no creada.
- **Sin cambios:** CONF-009 (RESOLVED, reevaluación obligatoria antes del cierre de FEAT-017); CONF-010 OPEN; O3 y O4 antes del pipeline; P5 de CR-021 PENDIENTE; S1–S4; N-2 y N-3; observación de `_marker_error`; requisitos de HUMAN_REVIEW; semántica de CR-020, CR-021 y CR-022; cierres de D1, D2 y D8; registro de experimentos; gates.
- **Riesgo y ejecución:** ninguno. Solo investigación, sin órdenes (REQ-G-081).
- El commit, el push y la implementación requieren la indicación expresa del propietario tras revisar la aplicación.
