# CR-003 — Persistencia y reinicio, seguridad explícita de credenciales, solo velas cerradas

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-003") y aplicada.
**Origen:** Revisión de un feedback externo del sistema (`~/Descargas/feedback.md`, puntos 3, 4 y 5), contrastado contra el contrato por el Orquestador de Desarrollo. Los puntos D (heartbeat externo), E (ubicación de Strategy Analyst y Risk Analyst en el flujo) y F (política de reintentos) quedan fuera de este CR.

---

## A. Persistencia de estado y reinicio

**Problema:** P26 (DEC-006) define qué hacer al reiniciar y CR-002 protege la posición abierta, pero el contrato no dice (1) cuándo se persiste el estado, (2) qué pasa con una autorización aprobada y no enviada si el proceso muere, ni (3) cómo evitar una orden duplicada si se reintenta tras una caída. Escenario: el proceso muere entre `RISK_APPROVED`/autorización humana y el envío a Binance.

**Cambio propuesto — nuevo REQ-G-032 (Módulo 3/ejecución):**
1. **Persistir antes de actuar:** todo cambio de estado de una operación se escribe en almacenamiento durable (el registro de eventos/estado local, p. ej. SQLite) **antes** de ejecutar la acción externa asociada (enviar orden, colocar/reemplazar stop, cancelar).
2. **Invalidación al reiniciar:** al arrancar, toda autorización humana vigente cuya orden no conste como enviada y confirmada se marca como inválida. Requiere nueva autorización; nunca se envía automáticamente, aunque `valid_until_utc` no haya vencido.
3. **Idempotencia de órdenes:** cada orden enviada a Binance lleva un identificador de cliente derivado de forma determinista del `correlation_id` (y de la secuencia de la orden dentro del ciclo). Antes de reenviar tras una caída, el sistema consulta en Binance por ese identificador; si la orden existe, adopta su estado en vez de enviar otra.
4. La reconciliación de arranque (P26) incorpora los puntos 2 y 3 y registra el resultado como evento de auditoría.

**Criterios de aceptación:**
- Ninguna acción externa ocurre sin que su estado previo esté persistido.
- Tras un reinicio, una autorización no enviada no produce orden.
- Un reintento tras caída nunca produce dos órdenes para la misma decisión.

**Pruebas nuevas (test_plan.md):**
- TC-REC-001 — Caída tras autorización y antes del envío → al reiniciar, la autorización queda inválida y no se envía orden.
- TC-REC-002 — Caída tras el envío y antes de recibir la confirmación → al reiniciar, la orden se localiza por identificador de cliente y se adopta su estado; no hay orden duplicada.
- TC-REC-003 — Fallo de escritura del estado → la acción externa no se ejecuta (Fail-Closed).

## B. Seguridad explícita de credenciales

**Problema:** REQ-G-093 dice "credenciales con permisos mínimos", que es ambiguo. El canal de aprobación (Telegram) no tiene requisitos de seguridad propios, aunque quien controle el bot puede suplantar la aprobación humana (INV-008).

**Cambio propuesto — ampliar REQ-G-093 y REQ-G-091; agregar requisito de Telegram en REQ-G-093 o requisito nuevo REQ-G-033:**
1. Clave de API de Binance **sin permiso de retiro** y sin margin/futuros; solo lectura y trading Spot.
2. **Restricción por IP** activada en la clave de Binance, limitada a la IP del equipo donde corre SwingPilot.
3. Token del bot de Telegram tratado como secreto con el mismo nivel que la clave de Binance: en `.env`, nunca en código, registros ni mensajes a componentes LLM.
4. El bot solo acepta órdenes del identificador de usuario del propietario (ya decidido en DEC-004, Q5; se eleva a requisito).
5. Al arrancar, el sistema verifica los permisos de la clave de Binance por API; si tiene permiso de retiro habilitado, se niega a operar (Fail-Closed).

**Pruebas nuevas:**
- TC-SEC-005 — Clave de Binance con permiso de retiro → el sistema no arranca en modo Live.
- TC-SEC-006 — Token de Telegram ausente de código fuente y registros (análisis estático + búsqueda en logs).
- TC-SEC-007 — Mensaje de aprobación desde un usuario distinto al propietario → ignorado y registrado como evento de seguridad.

**Fuera de alcance de este CR:** rotación periódica de claves (puede proponerse después).

## C. Solo velas cerradas

**Problema:** el contrato prohíbe look-ahead en investigación (Módulo 10), pero no dice explícitamente que en operación en vivo se ignora la vela en formación. Una vela H4 incompleta puede producir una señal que desaparece al cerrar.

**Cambio propuesto — ampliar REQ-G-070 (Fase 1) y `data_flow.md` Fase 1:**
1. El análisis en vivo usa exclusivamente velas cerradas en D1, H4 y H1. La vela en formación se descarta.
2. Se considera cerrada una vela cuyo tiempo de cierre según Binance es anterior al tiempo actual del servidor de Binance (no del reloj local).
3. Si la última vela cerrada esperada no está disponible, se aplica `DATA_UNAVAILABLE` (comportamiento existente de Fase 1).

**Pruebas nuevas:**
- TC-DATA-001 — Respuesta de Binance que incluye la vela en formación → se excluye del análisis.
- TC-DATA-002 — Falta la última vela H4 cerrada → `DATA_UNAVAILABLE`, sin propuesta.

---

## Documentos del contrato afectados

- `implementation/requirements.md` — REQ-G-032 (nuevo), REQ-G-033 (nuevo, si se separa Telegram), REQ-G-070, REQ-G-091, REQ-G-093 (ampliados).
- `implementation/data_flow.md` — Fase 1 (velas cerradas); §2 ciclo de vida de posición (persistencia antes de actuar, reinicio).
- `implementation/api_contracts.md` — identificador de cliente en órdenes; evento de auditoría de reconciliación de arranque.
- `implementation/test_plan.md` — TC-REC-001..003, TC-SEC-005..007, TC-DATA-001..002.

## Impacto

- **Arquitectónico:** bajo. No agrega componentes; usa el registro de eventos y la reconciliación existentes. Descartado Redis: SQLite/registro local es suficiente para una sola posición y un solo proceso.
- **Riesgo:** reduce el riesgo de órdenes duplicadas, de ejecución tras caída sin autorización vigente, de abuso de credenciales y de señales falsas por velas incompletas.
- **Pendiente técnico (FASE 2):** formato exacto del identificador de cliente según las restricciones de Binance; mecanismo de almacenamiento durable concreto.

## Aprobación

Aprobada el 2026-11-18 con la frase "APRUEBO CR-003". Aplicada en: `requirements.md` (REQ-G-032 y REQ-G-033 nuevos; REQ-G-070 y REQ-G-093 ampliados), `data_flow.md` (Fase 1 velas cerradas; Fase 6 persistencia e identificador de cliente), `api_contracts.md` (eventos STARTUP_RECONCILIATION_COMPLETED, AUTHORIZATION_INVALIDATED, UNAUTHORIZED_APPROVAL_ATTEMPT; nota de identificador de cliente), `test_plan.md` (TC-SEC-005..007, TC-REC-001..003, TC-DATA-001..002). REQ-G-091 no requirió cambio: la seguridad de Telegram quedó en REQ-G-033.
