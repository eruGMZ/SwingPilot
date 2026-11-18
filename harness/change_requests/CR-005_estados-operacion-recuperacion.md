# CR-005 — Máquina de estados de la operación, recuperación por estado, vigencia de autorización y cierre protector

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-005") y aplicada.
**Origen:** DEC-008 (Q23–Q25); documento externo de feedback `error-handling.md` ("Manejo de Fallos y Recuperación"), revisado contra el contrato el 2026-11-18. Del documento se adopta la estructura (estados de la operación y recuperación por estado); su contenido se reescribe para cumplir el contrato aprobado. Los puntos no adoptados figuran en §F.

---

## A. Estados de una operación (Q23)

Una **operación** nace cuando el Risk Manager recibe un TRADE_PROPOSAL y termina en un estado terminal. Las fases 1–4 del ciclo de decisión no crean operación ni ejecutan acciones externas; quedan cubiertas por el registro de auditoría (Fase 7). Estos estados son distintos de los 8 estados del Risk Manager (REQ-G-024) y coexisten con ellos.

| Estado | Significado | Transiciones permitidas | Disparador |
|---|---|---|---|
| `PROPOSED` | TRADE_PROPOSAL recibido por el Risk Manager | `RISK_APPROVED`, `RISK_REJECTED` | Evaluación del Risk Manager |
| `RISK_REJECTED` | Terminal | — | RISK_REJECTED |
| `RISK_APPROVED` | Invariantes cumplidos; Risk Analyst consultivo en curso | `AWAITING_AUTH`, `INVALIDATED` | Solicitud enviada a Telegram |
| `AWAITING_AUTH` | Solicitud de autorización enviada; vigencia 30 min (§C) | `AUTHORIZED`, `AUTH_REJECTED`, `AUTH_EXPIRED`, `INVALIDATED` | Respuesta del propietario / vencimiento / reinicio |
| `AUTH_REJECTED` | Terminal: el propietario rechazó | — | — |
| `AUTH_EXPIRED` | Terminal: sin respuesta dentro de la vigencia | — | — |
| `AUTHORIZED` | Autorización válida; re-verificación de riesgo previa a ejecución (REQ-G-075) | `ENTRY_PENDING`, `INVALIDATED` | Re-verificación superada / condiciones cambiaron / reinicio |
| `ENTRY_PENDING` | Estado persistido con identificador de cliente **antes** de enviar la compra (REQ-G-032); la orden puede o no haber llegado a Binance | `ENTRY_FILLED`, `ENTRY_FAILED`, `INVALIDATED` | Confirmación de Binance / rechazo / reinicio sin orden en Binance |
| `ENTRY_FAILED` | Terminal: orden rechazada o cancelada sin ejecución | — | ORDER_REJECTED / ORDER_CANCELLED |
| `ENTRY_FILLED` | Compra ejecutada (total o parcial); stop en Binance en colocación (REQ-G-031) | `POSITION_OPEN`, `EXIT_PENDING` | STOP_ORDER_PLACED / cierre protector (§D) |
| `POSITION_OPEN` | Posición con stop activo verificado en Binance | `EXIT_PENDING` | Stop ejecutado, take-profit, instrucción manual o cierre protector |
| `EXIT_PENDING` | Venta enviada o stop ejecutándose en Binance | `CLOSED`, `POSITION_OPEN` | Venta confirmada / venta no existente en Binance y precio sobre el stop |
| `CLOSED` | Terminal: venta confirmada y registrada en trades.db | — | ORDER_FILLED (SELL) |
| `INVALIDATED` | Terminal: operación anterior al envío anulada (reinicio o condiciones cambiadas) | — | AUTHORIZATION_INVALIDATED si había autorización |

**Reglas:**
1. Toda transición se persiste en almacenamiento durable **antes** de la acción externa asociada; si la escritura falla, la acción no se ejecuta (REQ-G-032).
2. Una transición no listada en la tabla es un error de programa: se rechaza, se registra y aplica Fail-Closed.
3. **No existe un estado `ERROR` genérico.** Ante un fallo, la operación conserva su último estado persistido con el error registrado, y el sistema aplica Fail-Closed mediante los estados del Risk Manager (DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW). Así la recuperación sabe exactamente en qué paso estaba la operación.
4. A lo sumo una operación puede estar en `AUTHORIZED`, `ENTRY_PENDING`, `ENTRY_FILLED`, `POSITION_OPEN` o `EXIT_PENDING` (INV-003).
5. Cada transición emite OPERATION_STATE_CHANGED (estado anterior, nuevo, motivo, `correlation_id`).

## B. Recuperación por estado al arrancar (Q23; amplía REQ-G-032 y P26)

Al arrancar, el sistema entra siempre en **modo seguro** (P26): sin nuevas entradas hasta confirmación del propietario. Durante la reconciliación de arranque solo se permiten acciones de protección (REQ-G-024).

| Estado encontrado | Acción |
|---|---|
| `PROPOSED`, `RISK_APPROVED` | → `INVALIDATED`. No se reenvía nada. |
| `AWAITING_AUTH`, `AUTHORIZED` | → `INVALIDATED` + AUTHORIZATION_INVALIDATED, aunque la vigencia no haya vencido (REQ-G-032 punto 2). Se requiere una propuesta y autorización nuevas. |
| `ENTRY_PENDING` | Consultar Binance por identificador de cliente. Ejecutada (total o parcial) → adoptar → `ENTRY_FILLED`. Abierta sin ejecución completa → cancelar el remanente (acción de protección) y adoptar lo ejecutado; sin ejecución → `ENTRY_FAILED`. No existe → `INVALIDATED`; **no se reenvía**. Binance no responde → se mantiene `ENTRY_PENDING`, EXCHANGE_DESYNC, nueva consulta en cada reconciliación (P19), sin enviar órdenes. |
| `ENTRY_FILLED`, `POSITION_OPEN` | Verificar en Binance que existe stop activo por la cantidad en posición. Existe → `POSITION_OPEN`. No existe y el precio está sobre el stop → colocarlo (STOP_ORDER_PLACED), sin nueva autorización. No existe y el precio está en o bajo el stop → cierre protector (§D). |
| `EXIT_PENDING` | Consultar la venta por identificador de cliente. Ejecutada → `CLOSED` y registro en trades.db. No existe y el precio está en o bajo el stop → cierre protector (§D). No existe y el precio está sobre el stop → `POSITION_OPEN` con stop verificado; si la salida era una instrucción manual del propietario, se le avisa para que la repita. |
| Terminales | Sin acción. |

Al terminar: STARTUP_RECONCILIATION_COMPLETED con el resultado por operación, informe por Telegram y espera de confirmación del propietario para salir del modo seguro.

## C. Vigencia de la autorización humana (Q24)

1. `valid_until_utc` = momento de envío de la solicitud por Telegram + **30 min**.
2. Una respuesta recibida por el backend de autorización después de `valid_until_utc` no tiene efecto: la operación pasa a `AUTH_EXPIRED`, se emite AUTHORIZATION_EXPIRED y se avisa al propietario. Los botones del mensaje vencido se desactivan o se ignoran.
3. La hora de referencia es la del backend de autorización, no la del teléfono.
4. **Propuesta de medición (FASE 2, modo de prueba):** registrar el tiempo entre el envío de la solicitud y la respuesta del propietario, para revisar la vigencia con datos reales mediante una DEC.
5. El valor solo cambia mediante una decisión registrada (DEC).

## D. Cierre protector (Q25; amplía REQ-G-031)

Aplica en la reconciliación de arranque, en la periódica (cada 5 min con posición abierta, P19) y en el monitoreo de segunda capa:

1. Si existe posición abierta, **no** hay stop activo en Binance y el precio actual está en o por debajo del stop autorizado: se envía de inmediato una venta a mercado por la cantidad en posición, con identificador de cliente determinista (REQ-G-032), y la operación pasa a `EXIT_PENDING`. Se emite PROTECTIVE_CLOSE_SUBMITTED.
2. No requiere nueva autorización: ejecuta la salida ya autorizada (INV-007). Disponible en cualquier estado del Risk Manager (REQ-G-024).
3. Tras el cierre: aviso por Telegram y estado MANUAL_REVIEW del Risk Manager (sin nuevas entradas) hasta que el propietario revise y libere.
4. Si el precio está sobre el stop: se recoloca el stop (STOP_ORDER_PLACED); si falla, rige STOP_ORDER_FAILED (REQ-G-031).
5. Si el precio no puede obtenerse: Fail-Closed (DATA_UNAVAILABLE), aviso inmediato por Telegram e intento de recolocar el stop; no se cierra a ciegas.

## E. Esquema de almacenamiento (referencia, no vinculante)

El esquema `operations` de `state.db` (SQLite) del documento externo se registra como referencia para el diseño de FASE 2, con estos ajustes: estados de §A; campo de identificador de cliente por orden (compra, stop, venta) con secuencia; campo `valid_until_utc`; campo `last_error`. El mecanismo concreto de almacenamiento durable sigue PENDING (REQ-G-032).

## F. Puntos del documento externo NO adoptados

| Punto del documento | Motivo |
|---|---|
| En recuperación, `RISK_APPROVED` → `retry_execution` (ese estado va antes de la autorización humana) | Viola INV-008 y REQ-G-032 punto 2: ejecutaría sin autorización. |
| `EXECUTING` sin order_id → volver a `RISK_APPROVED` y reintentar; `AWAITING_AUTH` < 2 h → reenviar solicitud | REQ-G-032 punto 2: se invalida y se requiere autorización nueva. |
| `RECOVERY` → `IDLE` / `POSITION_OPEN` automático | P26: modo seguro hasta confirmación del propietario. |
| Binance: 3 reintentos con backoff 1/5/25 s, incluidas órdenes | REQ-G-034: 1 reintento solo para lecturas; órdenes sin reintento ciego (REQ-G-032). |
| Latido cada 4 h, verificación cada 5 h, alerta a 4.5 h | REQ-G-035: latido mínimo cada 15 min, alerta a 30 min, servicio externo. |
| Verificación del OCO cada 15 min | P19: cada 5 min con posición abierta. |
| Timeout de Claude 30 s | P18 (DEC-006): 60 s. |
| `clientOrderId = SP_` + 8 caracteres del `correlation_id` | REQ-G-032 punto 3: incluye la secuencia de la orden; sin ella la compra y el stop del mismo ciclo colisionan. |
| OCO con take-profit y `reduceOnly` | Tipo de orden (stop-limit vs OCO) PENDING en REQ-G-031; `reduceOnly` no existe en Spot. |
| Numeración de invariantes (INV-001 = 1 posición; INV-012 = stop en Binance) | En el contrato: INV-003 = 1 posición; INV-012 = Fail-Closed; stop en Binance = REQ-G-031. |
| Estado `ERROR` alcanzable desde cualquier estado | Pierde el paso en que estaba la operación; ver §A regla 3. |

Adoptados por coincidir con el contrato (sin cambios): solo velas cerradas (REQ-G-070); fallo de IA → ciclo sin propuesta (REQ-G-034); restaurar stop con posición abierta sin reautorización (REQ-G-031).

---

## Documentos del contrato afectados

- `implementation/requirements.md`:
  - **REQ-G-037 (nuevo):** máquina de estados de la operación (§A).
  - **REQ-G-038 (nuevo):** recuperación por estado al arrancar (§B).
  - **REQ-G-039 (nuevo):** vigencia de autorización de 30 min (§C).
  - REQ-G-031 ampliado con el cierre protector (§D); se elimina "cierre o intervención del propietario" como alternativa abierta.
  - REQ-G-032: referencia a REQ-G-037/038; PENDING de almacenamiento con la referencia de §E.
  - REQ-G-075 y REQ-G-P26: referencias a REQ-G-038 y REQ-G-039.
- `implementation/data_flow.md` — §1 Fase 6 (vigencia 30 min); §2 ciclo de vida de posición alineado con los estados de §A; cierre protector.
- `implementation/api_contracts.md` — eventos nuevos: OPERATION_STATE_CHANGED, AUTHORIZATION_EXPIRED, PROTECTIVE_CLOSE_SUBMITTED; esquema de autorización: `valid_until_utc` = envío + 30 min.
- `implementation/architecture.md` — referencia a la máquina de estados de la operación en el Execution Engine / Trading Engine, si aplica.
- `implementation/test_plan.md` — pruebas nuevas:
  - TC-OPS-STATE-001 — Toda transición se persiste antes de la acción externa.
  - TC-OPS-STATE-002 — Transición no permitida → rechazada, registrada, Fail-Closed.
  - TC-OPS-STATE-003 — Nunca más de una operación en estados activos (INV-003).
  - TC-REC-004 — Reinicio en `RISK_APPROVED` → `INVALIDATED`; sin orden ni reintento.
  - TC-REC-005 — Reinicio en `ENTRY_PENDING` sin orden en Binance → `INVALIDATED`; sin reenvío.
  - TC-REC-006 — Reinicio en `ENTRY_PENDING` con ejecución parcial → adopta lo ejecutado, cancela remanente, coloca stop.
  - TC-REC-007 — Reinicio en `POSITION_OPEN` sin stop y precio sobre el stop → stop recolocado sin reautorización.
  - TC-REC-008 — Reinicio con Binance sin respuesta → `ENTRY_PENDING` conservado, EXCHANGE_DESYNC, sin órdenes.
  - TC-REC-009 — Tras la reconciliación, sin nuevas entradas hasta confirmación del propietario.
  - TC-AUTH-001 — Respuesta a los 29 min → válida; a los 31 min → AUTH_EXPIRED sin orden.
  - TC-AUTH-002 — Vencimiento medido con la hora del backend.
  - TC-STOP-007 — Sin stop y precio en o bajo el stop → venta a mercado, PROTECTIVE_CLOSE_SUBMITTED, aviso, MANUAL_REVIEW.
  - TC-STOP-008 — Sin stop y precio no disponible → Fail-Closed, aviso, sin cierre a ciegas.

## Impacto

- **Arquitectónico:** bajo-medio. No agrega componentes ni agentes; formaliza estados que REQ-G-032 ya exigía persistir y fija la conducta de recuperación.
- **Riesgo:** reduce. Cierra el hueco por el que una recuperación podía ejecutar sin autorización; acota la pérdida cuando falta la orden protectora.
- **Operativo:** propuestas sin respuesta en 30 min se pierden (aceptado en DEC-008).
- **Pendiente técnico (FASE 2):** mecanismo de almacenamiento durable; tipo de orden de stop (stop-limit vs OCO).

## Aprobación

Aprobada el 2026-11-18 con la frase "APRUEBO CR-005". Aplicada en: `requirements.md` (REQ-G-031 ampliado con cierre protector; REQ-G-032, REQ-G-075 y REQ-G-P26 con referencias; REQ-G-037, 038, 039 nuevos), `data_flow.md` (§1 Fase 6 vigencia 30 min; §2 cierre protector; §2.1 nueva correspondencia de estados), `api_contracts.md` (eventos OPERATION_STATE_CHANGED, AUTHORIZATION_EXPIRED, PROTECTIVE_CLOSE_SUBMITTED; regla de `valid_until_utc`), `architecture.md` (§3.4 Execution Engine), `test_plan.md` (TC-STOP-007..008, TC-REC-004..009, nueva §8.6 con TC-OPS-STATE-001..003 y TC-AUTH-001..002).
