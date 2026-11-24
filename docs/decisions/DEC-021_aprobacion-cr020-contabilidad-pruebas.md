# DEC-021 — Aprobación de CR-020 (contabilidad de pruebas de REQ-G-P17 y procedencia de antecedentes)

**Fecha:** 2026-11-24
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** mensaje del propietario en la sesión del 2026-11-24: aprobación formal de CR-020 revisión 3 y de todas las decisiones metodológicas que recoge, más los tres detalles contractuales orientados a la implementación. Antes: dirección metodológica de D2 (opción B), decisiones para las revisiones 2 y 3, y R1–R4 (registradas en CR-020 §B y en `progress.md`).
**Alcance:** aprueba `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` (revisión 3) y autoriza **solo su aplicación contractual**: contrato v1.7 → **v1.8**, criterios de aceptación y plan de pruebas. **No autoriza** implementar el mecanismo (CR-020 §D), escribir registros reales de procedencia, cambiar estados de FEAT, ejecutar la suite funcional ni hacer commit o push. Cada uno requiere una autorización posterior y expresa.
**Relación con DEC-005:** concreta DEC-005 Q11 (P17), «corrección por número de experimentos probados (p. ej. Deflated Sharpe), usando el conteo del preregistro», sin reescribirla. La unidad pasa a ser la configuración evaluada, con el conteo experimental congelado en el preregistro y reconstruido desde el registro de experimentos.

## Decisión

| Elemento | Decisión |
|---|---|
| Unidad y población (CR-020 §C.1, §C.2) | Configuraciones evaluadas de todas las familias de investigación sobre BTC/USDT, incluidos los antecedentes declarados. Aprobado |
| Conteo histórico inicial | 8 = 4 evaluaciones documentadas de Mean Reversion H1 + 4 configuraciones preregistradas de EXP-0001 como cota conservadora. **No son 8 ejecuciones verificadas.** Aprobado |
| Doble conteo y conteos `H_doc`, `H_bound`, `E`, `G`, `N_pre`, `N_eval` (§C.1) | Aprobado |
| `ANTECEDENT_PROVENANCE` (§C.3.1) | Solución de CONF-009, con el estado original separado de la procedencia vigente. Gramática `AUTORIZA: PROCEDENCIA` con validación estricta de identificador, enteros, coincidencia exacta y evidencia documental (R4). Aprobado |
| `CONFIGURATION_EVALUATED` (§C.3.2) | Registro duradero antes de evaluar; límite contable conservador de un inicio autorizado, no prueba de ejecución; Fail-Closed ante persistencia incierta; una solicitud rechazada no cuenta. Aprobado con la **condición** de abajo |
| Evidencia de congelación (§C.3.3) y `candidate_selection_rule` (§C.3.4, R1) | Formas `PRIMARY` y `ARGMAX … TIEBREAK …`. La regla del piloto queda en D7. Aprobado |
| Conciliación (§C.4) | Conteo congelado; pruebas posteriores NO RELEVANTE / RELEVANTE / INDETERMINADA con evidencia positiva suficiente y sin LLM; `informed_by` obligatorio en registros nuevos (R2); `N_eval` no restaura el carácter confirmatorio. Aprobado |
| Resultados distintos (§C.5) | Sin cambios en estados ni transiciones. Aprobado |
| Repetición nativa de configuración de antecedente (R3) | Par nuevo; decisión contable conservadora, no afirmación de independencia estadística. Aprobado |
| Texto contractual (§C.6) | REQ-G-P17, REQ-G-103, REQ-G-104, TC-ML-006 y TC-ML-020..024; contrato v1.8. Aprobado |
| Criterios de aceptación (§C.7) | AC-017-3, AC-017-8 y AC-017-13. Aprobado |

**Condición sobre las validaciones previas de una solicitud de evaluación (§C.3.2):** la evaluación solo se permite si el estado del experimento, las transiciones y los requisitos de autorización vigentes la permiten. Un estado no terminal **no** basta como autorización.

## Efectos

- **D2:** resolución metodológica y contractual APROBADA. Su implementación y verificación siguen PENDIENTES.
- **CONF-009 y CONF-010:** siguen OPEN hasta que se acepten la evidencia de implementación y la de verificación.
- **Estados y transiciones:** se conservan los de REQ-G-104, `OWNER_DECIDED` y REQ-G-107.
- **Líneas `AUTORIZA: PROCEDENCIA`:** CR-020 §C.6 preveía incluirlas en esta decisión. No se incluyen porque esta decisión no autoriza escribir registros reales de procedencia. Irán en un documento de decisión posterior cuando el propietario autorice expresamente esos registros.
- **Riesgo y ejecución:** ninguno. Solo investigación, sin órdenes (REQ-G-081).
- **Siguen vigentes** las restricciones de DEC-017 y DEC-018: sin OOS ni LOCKBOX, sin credenciales privadas, sin activar estrategias y sin consumo del presupuesto de IA. El commit y el push requieren la indicación del propietario.
