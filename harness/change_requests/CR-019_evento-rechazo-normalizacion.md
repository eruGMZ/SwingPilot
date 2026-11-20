# CR-019 — Tipo de evento para el rechazo de la normalización de TRADE_PROPOSAL

**Fecha:** 2026-11-20
**Estado:** APROBADA por el propietario el 2026-11-20 («Apruebo CR-019»; DEC-020) y APLICADA: contrato v1.7; código y pruebas según la sección C. Antes: PROPUESTA (opción A de CONF-008, «redacta CR-019 opción A»).
**Origen:** CONF-008 (`implementation/conflict_register.md`), a partir del hallazgo QA3E-01 de la QA independiente de FEAT-018..022 (`harness/verification/IMPL-3_QA_engines.md`).
**Precedente:** CR-015, que resolvió CONF-007, un caso del mismo tipo: un paso de la cadena sin tipo en el catálogo.

## A. Problema

`api_contracts.md` §3.8 B.8 punto 2 (y TC-NORM-002) exige que, cuando la síntesis no es consistente con el candidato, «no se emite TRADE_PROPOSAL. `DECISION_SYNTHESIS_COMPLETED` se conserva y se registra la inconsistencia con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados». El punto 5 dice además que una propuesta que no valida contra §4.1 «no se emite (`OUT_OF_CONTRACT`)».

El catálogo cerrado de §2 (33 tipos; REQ-G-061/063/064) no define ningún tipo para registrar ese resultado:
- TRADE_PROPOSAL está prohibido en ese caso.
- E8 ya está registrado y el EventStore solo admite añadir.

Hoy la inconsistencia queda solo en memoria (`CycleReport.normalization`), y la cadena del EventStore termina en E8 sin rastro del motivo. La reconstrucción del ciclo (REQ-G-062, TC-AC-04) queda incompleta.

## B. Cambio propuesto

### B.1 `api_contracts.md` §2: una fila más en el catálogo (33 → 34 tipos)

| Tipo | Productor | Consumidor Principal | Descripción |
|---|---|---|---|
| PROPOSAL_NORMALIZATION_REJECTED | AI Orchestrator (normalizador determinista, §3.8 B.8) | Audit | La síntesis propuso operar pero no se emite TRADE_PROPOSAL: la síntesis es inconsistente con el candidato o la propuesta normalizada no cumple §4.1. Fin del ciclo; no es una decisión, no llega al Risk Manager ni autoriza nada (§3.8 B.10; CR-019) |

### B.2 `api_contracts.md` §3.8: nueva sección B.10 `PROPOSAL_NORMALIZATION_REJECTED`

- **Cuándo se emite:** solo si `DECISION_SYNTHESIS_COMPLETED` (E8) tiene `decision = TRADE_PROPOSAL` y la normalización termina en `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` (B.8 punto 2) o en `OUT_OF_CONTRACT` (B.8 punto 5). **No se emite** cuando la síntesis decide otra cosa o está en ERROR, ni cuando el candidato está en ERROR. Esos casos ya quedan registrados en E8 y en E4.
- **Posición en la cadena:** E9, en lugar de TRADE_PROPOSAL. E9 tiene, por tanto, dos tipos excluyentes. El ciclo termina aquí.
- **Sobre:** contrato universal (§1). `source` = `ai_orchestrator`; `destination` = `audit`; `correlation_id` = el del ciclo; `causation_id` = E8; `timeframe` y `data_timestamp_utc` = los de E8; `status` = `COMPLETED`: el normalizador terminó y el resultado es un rechazo (mismo criterio que B.0 punto 1).
- **Payload** (`schema_version` = `1.0.0`; `additionalProperties: false`):

| Campo | Tipo | Oblig. | Regla |
|---|---|---|---|
| `reason_code` | enum `PROPOSAL_INCONSISTENT_WITH_CANDIDATE \| OUT_OF_CONTRACT` | Sí | Motivo del rechazo (B.8 puntos 2 y 5) |
| `affected_fields` | lista de `{field, synthesis_value, candidate_value}` | Sí | `field` ∈ `strategy_id`, `strategy_version`, `stop_loss`, `entry_zone`, `take_profit`. Al menos un elemento si `reason_code = PROPOSAL_INCONSISTENT_WITH_CANDIDATE`; vacía si `OUT_OF_CONTRACT` |
| `validation_errors` | lista de cadenas | Sí | Errores de validación contra §4.1 v1.1.0. Al menos uno si `OUT_OF_CONTRACT`; vacía si `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` |
| `source_candidate_id` | uuid | Sí | `candidate_id` de E4 |
| `source_candidate_message_id` | uuid | Sí | `message_id` de E4 |
| `synthesis_message_id` | uuid | Sí | `message_id` de E8 (también es `causation_id`) |
| `synthesis_analysis_id` | uuid | Sí | `analysis_id` de la síntesis |
| `normalizer_version` | semver | Sí | Versión del normalizador |

- **Prohibido:** cualquier campo operativo de §4.1 (`proposal_id`, `entry_price_target`, `stop_loss_price`, `exit_mechanism`, etc.). El evento no puede confundirse con una propuesta ni usarse como tal.
- **Determinismo:** con el mismo E4 y el mismo E8 se obtiene el mismo payload (TC-AC-07).

### B.3 `api_contracts.md` §3.8 B.8: referencias

- Punto 2: «… y se registra la inconsistencia con el motivo `PROPOSAL_INCONSISTENT_WITH_CANDIDATE` y los campos afectados» → añadir «mediante `PROPOSAL_NORMALIZATION_REJECTED` (B.10)».
- Punto 5: «si no valida, no se emite (`OUT_OF_CONTRACT`)» → añadir «y se registra `PROPOSAL_NORMALIZATION_REJECTED` con `reason_code = OUT_OF_CONTRACT` (B.10)».

### B.4 `data_flow.md` §5

`E9  TRADE_PROPOSAL  (X, causation_id: E8) — normalizada desde E4 (CR-018 B.8)` → `E9  TRADE_PROPOSAL | PROPOSAL_NORMALIZATION_REJECTED  (X, causation_id: E8) — normalizada desde E4 (CR-018 B.8); el rechazo termina el ciclo (CR-019)`.

### B.5 `requirements.md` REQ-G-063

«catálogo vigente en `api_contracts.md` §2, 33 tipos» → «34 tipos», y añadir «CR-019 añade PROPOSAL_NORMALIZATION_REJECTED».

### B.6 `test_plan.md`

- **TC-NORM-002**, nuevo resultado esperado: «no se emite TRADE_PROPOSAL; se registra en el EventStore `PROPOSAL_NORMALIZATION_REJECTED` con `reason_code = PROPOSAL_INCONSISTENT_WITH_CANDIDATE`, `causation_id` = E8 y los campos afectados; la cadena del ciclo se reconstruye hasta E9».
- **TC-NORM-004** (nuevo): propuesta normalizada que no valida contra §4.1 → sin TRADE_PROPOSAL; `PROPOSAL_NORMALIZATION_REJECTED` con `reason_code = OUT_OF_CONTRACT` y `validation_errors` no vacío.
- **TC-NORM-005** (nuevo): síntesis con decisión distinta de TRADE_PROPOSAL, síntesis en ERROR o candidato en ERROR → ni TRADE_PROPOSAL ni `PROPOSAL_NORMALIZATION_REJECTED`.

### B.7 Versión del contrato

v1.6 → **v1.7** en los 5 documentos de `implementation/`.

## C. Impacto

- **Riesgo y ejecución:** ninguno. El evento es de auditoría, no lo consume el Risk Manager y no autoriza nada (REQ-G-073). Fail-Closed no cambia: en ambos casos sigue sin emitirse TRADE_PROPOSAL.
- **Código (tras aprobación; IMPL-3):**
  - `src/swingpilot/contracts/message.py`: un tipo más en `EVENT_TYPES` (la prueba que compara con §2 lo verifica).
  - `src/swingpilot/engines/schemas.py`: esquema de B.10.
  - `src/swingpilot/engines/normalizer.py`: devuelve `affected_fields` estructurados en lugar de texto libre y construye el mensaje.
  - `src/swingpilot/engines/cycle.py`: registra el mensaje en el EventStore.
- **Pruebas:** TC-NORM-002 actualizada, TC-NORM-004 y 005 nuevas, y la prueba del ciclo con síntesis inconsistente comprueba el EventStore (QA3E-01). Cada una debe fallar con el código anterior.
- **FEAT:** cierra QA3E-01 (FEAT-021, y FEAT-022 por la cadena). AC-021-2 y AC-021-3 se cumplen con registro y pasan a citar B.10. No cambia ningún otro criterio.
- **Compatibilidad:** cambio aditivo al catálogo. El esquema del mensaje no cambia de versión mayor; §4.1 sigue en v1.1.0.

## D. Alternativas consideradas (CONF-008)

- **B. Ampliar `NO_SETUP` con un motivo nuevo.** Se descarta: `NO_SETUP` lo produce el Strategy Engine con `causation_id` = E2 (B.7), así que mezclaría productores y posiciones en la cadena.
- **C. Registrar fuera del EventStore.** Se descarta: la cadena del ciclo quedaría incompleta (REQ-G-062, TC-AC-04).
- **Llevar el rechazo en TRADE_PROPOSAL con sobre FAILED.** Se descarta: B.8 prohíbe emitir TRADE_PROPOSAL en estos casos, y un consumidor que filtre por tipo podría tratarlo como propuesta.

## E. Aprobación

Requiere aprobación explícita del propietario. Al aprobarse:
1. Registrar la decisión (DEC-020).
2. Aplicar B.1–B.7 (contrato v1.7).
3. Implementar C con pruebas de regresión.
4. Marcar CONF-008 como RESUELTA y registrar en `progress.md`.
