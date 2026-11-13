# Política de Gestión de Riesgo (SwingPilot)

| Propiedad | Valor |
|---|---|
| Proyecto | SwingPilot |
| Documento | RISK_POLICY.md |
| Versión | 1.0 |
| Estado | BORRADOR — pendiente de aprobación humana |
| Clasificación | Privado — uso interno |
| Autoridad de aprobación | Propietario del sistema |
| Alcance | Todos los agentes, estrategias y módulos de ejecución |
| Mercado inicial | Binance Spot |
| Par inicial | BTC/USDT |

---

## ¿Para qué existe esta política?

Este documento establece la política central de gestión de riesgo de SwingPilot y convierte las decisiones de riesgo aprobadas por el propietario en restricciones cuantificables, verificables y obligatorias para todos los componentes del sistema.

En concreto, la política determina cuánto capital puede exponerse al riesgo; cómo calcular el presupuesto de pérdida por operación; cómo determinar el tamaño máximo de una posición; qué costes deben incluirse en el cálculo; cuándo debe bloquearse una nueva operación; cómo deben protegerse las posiciones abiertas; y qué autoridad tiene cada componente del sistema.

**Principio fundamental:** ninguna estrategia, agente de inteligencia artificial, módulo de ejecución o componente externo puede modificar, ignorar o sobrepasar los límites establecidos en esta política. La gestión de riesgo tiene prioridad sobre cualquier objetivo de rentabilidad.

---

## ¿Qué parámetros están aprobados?

Los siguientes parámetros constituyen la configuración inicial autorizada. Estos valores no pueden ser modificados por agentes autónomos ni por configuraciones particulares de una estrategia.

| Parámetro | Valor |
|---|---:|
| Capital inicial | $3,000 MXN |
| Riesgo máximo por operación | 1.5% del equity actual |
| Presupuesto inicial por operación | $45 MXN |
| Drawdown mensual máximo | 5% |
| Pérdida mensual inicial equivalente | $150 MXN |
| Mercado | Binance Spot |
| Par inicial | BTC/USDT |
| Dirección operativa | Long-only |
| Apalancamiento | No permitido |
| Posiciones simultáneas | 1 |
| Promediado a la baja | Prohibido |
| Autorización | Nivel 1 — aprobación humana individual |
| Frecuencia máxima | 8 operaciones mensuales |
| Pérdidas consecutivas preventivas | 3 |
| Enfriamiento tras racha | Suspensión hasta revisión humana |

---

## ¿Qué manda sobre el resto del sistema?

La política de riesgo constituye una restricción superior a cualquier instrucción operativa. Una instrucción de menor jerarquía nunca puede invalidar una restricción de mayor jerarquía.

Orden de precedencia:

1. RISK_POLICY.md.
2. Configuración global de riesgo autorizada.
3. Contrato técnico del sistema.
4. Políticas particulares de cada estrategia.
5. Instrucciones de los agentes de IA.
6. Solicitudes de ejecución.

### ¿Qué significa Fail-Closed?

Cuando SwingPilot no pueda verificar una condición necesaria para determinar el riesgo de una operación, deberá adoptar el comportamiento restrictivo.

Ejemplos: no se conoce el equity actual (bloquear nuevas entradas); no se puede calcular el riesgo efectivo (rechazar la operación); no se conoce el estado de una posición (impedir nuevas entradas); no se puede verificar el mecanismo de salida (rechazar la operación); existe una discrepancia entre el estado local y Binance (bloquear nuevas entradas hasta reconciliar); no se conoce el estado del bloqueo mensual (impedir nuevas entradas).

La ausencia de información no constituye autorización para operar. Este comportamiento se formaliza también en el invariante INV-012.

---

## ¿Cómo se define el capital y el equity?

### Capital inicial

El capital inicial autorizado es de $3,000 MXN. Este valor representa el punto de partida del sistema y sirve como referencia para los cálculos iniciales. No constituye un límite permanente de equity (patrimonio neto de la cuenta en el instante de cálculo).

### Equity actual

El riesgo por operación se calculará utilizando el equity actual de la cuenta.

\[
Equity_t = Cash_t + MarketValue_t
\]

Donde `Cash` es saldo disponible en efectivo o activos de cotización; `MarketValue` es valoración de las posiciones abiertas; y `t` es el instante de cálculo.

Para el mercado BTC/USDT:

\[
Equity_{USDT} =
USDT_{disponible} +
BTC_{total}\times Precio_{BTC}
\]

La valoración debe contemplar los saldos efectivamente atribuibles a SwingPilot, evitando duplicar fondos bloqueados en órdenes abiertas. Los activos externos a la cuenta o subcuenta operativa no se contabilizarán.

### Conversión monetaria

El capital de referencia se expresa en MXN, mientras que el par operativo BTC/USDT utiliza USDT.

\[
Equity_{MXN} =
Equity_{USDT}\times FX_{USDT/MXN}
\]

La fuente de conversión y su política de actualización deberán establecerse en la configuración técnica. Si el tipo de cambio no está disponible o su antigüedad supera el umbral configurado, el sistema bloqueará nuevas entradas.

### Actualización del equity

El equity deberá recalcularse antes de presentar una operación para autorización; inmediatamente antes de ejecutar una orden; después de cerrar una posición; después de reconciliar saldos con Binance; y cuando se detecten cambios relevantes en el valor de una posición abierta.

No se utilizará un equity histórico para autorizar una operación nueva.

---

## ¿Cuál es el presupuesto de riesgo por operación?

### Límite máximo

Cada operación tendrá un presupuesto máximo de riesgo equivalente al 1.5% del equity actual.

\[
RiskBudget_t = Equity_t \times 0.015
\]

Ejemplo inicial:

\[
3,000 \times 0.015 = 45\ MXN
\]

<escape>**Presupuesto inicial: $45 MXN por operación.**</escape>

El presupuesto se actualizará dinámicamente conforme cambie el equity.

### Reducción del presupuesto

Si el equity disminuye, el presupuesto de riesgo también deberá disminuir. El sistema no podrá mantener automáticamente el presupuesto original de $45 MXN cuando el equity haya disminuido.

| Equity | Riesgo máximo |
|---:|---:|
| $3,000 MXN | $45 MXN |
| $2,900 MXN | $43.50 MXN |
| $2,800 MXN | $42 MXN |
| $2,500 MXN | $37.50 MXN |
| $2,000 MXN | $30 MXN |

### Riesgo efectivo

El presupuesto de riesgo contempla, en conjunto:

1. Pérdida estimada por movimiento adverso del precio.
2. Comisión estimada de entrada.
3. Comisión estimada de salida.
4. Reserva de slippage.
5. Otros costes de ejecución directamente atribuibles a la operación, cuando correspondan.

\[
RiskEffective =
PriceRisk + Fees + Slippage + OtherCosts
\]

Condición obligatoria:

\[
RiskEffective \leq RiskBudget_t
\]

Si el riesgo efectivo supera el presupuesto disponible, la operación deberá rechazarse o reducir su tamaño. Los costes no podrán contabilizarse fuera del límite del 1.5%.

---

## ¿Cómo se calcula el tamaño de posición?

### Principio

El tamaño de posición (*position sizing*) no será determinado exclusivamente por el capital disponible. Deberá calcularse a partir del equity actual, presupuesto de riesgo disponible, precio de entrada, precio de salida por protección, comisiones, slippage estimado y precisión y restricciones de Binance.

### Fórmula general

Para una posición Long:

\[
Q =
\frac{RiskBudget - FixedCosts}
{(P_e-P_s)+C_e+C_s+S}
\]

| Variable | Definición |
|---|---|
| \(Q\) | Cantidad de BTC |
| \(P_e\) | Precio de entrada |
| \(P_s\) | Precio de stop o salida |
| \(C_e\) | Coste de entrada por unidad |
| \(C_s\) | Coste de salida por unidad |
| \(S\) | Reserva de slippage por unidad |
| \(FixedCosts\) | Otros costes fijos estimados |
| \(RiskBudget\) | Presupuesto disponible de riesgo |

Los costes variables deberán expresarse en la misma unidad monetaria que el movimiento del precio. El cálculo deberá incorporar las tasas reales o conservadoras configuradas para la cuenta.

### Restricciones de ejecución

Una vez calculada la cantidad, el sistema deberá redondear hacia abajo conforme al `stepSize` del mercado; respetar `minQty` y `minNotional`; verificar saldo suficiente; recalcular el riesgo después del redondeo; y rechazar cualquier cantidad cuyo riesgo efectivo supere el presupuesto.

Si el tamaño mínimo permitido por Binance excede el presupuesto de riesgo, SwingPilot no deberá ejecutar la operación. No se aumentará el presupuesto para satisfacer los requisitos mínimos del exchange.

### Prohibición de sizing discrecional

Ningún agente podrá incrementar la cantidad calculada argumentando mayor confianza en la señal, alta probabilidad de éxito, oportunidad excepcional, recuperación de pérdidas anteriores, objetivo de rentabilidad mensual o recomendación de otro agente.

El position sizing debe ser determinista y reproducible.

---

## ¿Qué exige un stop o mecanismo de salida?

### Mecanismo obligatorio

Toda operación deberá contar con un mecanismo de salida definido antes de su autorización humana. Se admiten stop-loss convencional y mecanismo alternativo de salida cuantificable y verificable.

La política no obliga a todas las estrategias a utilizar una misma implementación técnica de stop. Sin embargo, cualquier alternativa deberá definir, como mínimo:

1. Condición exacta de activación.
2. Precio o criterio de ejecución.
3. Método de detección.
4. Mecanismo de envío de la orden.
5. Comportamiento ante errores.
6. Riesgo estimado de la salida.

### Condición de rechazo

Una operación será rechazada cuando no tenga mecanismo de salida; el mecanismo no sea verificable; no permita estimar el riesgo; dependa exclusivamente de una decisión discrecional futura; o no exista un procedimiento de contingencia ante fallos.

### Riesgo de ejecución

El stop-loss no garantiza el precio exacto de salida. Por ello, el cálculo deberá incorporar una reserva de slippage y contemplar que una ejecución real puede diferir del precio previsto.

El límite del 1.5% representa el riesgo estimado autorizado, no una garantía absoluta frente a eventos extraordinarios.

---

## ¿Cuánta exposición simultánea se permite?

### Una posición abierta

SwingPilot podrá mantener una sola posición abierta simultáneamente. No se permite abrir una segunda posición sobre BTC, acumular entradas independientes, dividir artificialmente operaciones para eludir límites, mantener entradas simultáneas mediante diferentes agentes ni ejecutar una nueva entrada mientras exista una posición pendiente de reconciliación o cierre.

La restricción se aplica globalmente, no por estrategia o agente.

### Órdenes pendientes

Una orden de entrada pendiente deberá considerarse una exposición potencial. Mientras exista una orden de entrada activa, no podrá autorizarse otra entrada; deberá contabilizarse su exposición potencial; y se verificará su estado real en Binance antes de cualquier nueva acción.

Las órdenes parciales deberán contabilizarse conforme a la cantidad efectivamente ejecutada y la cantidad restante pendiente.

### Apalancamiento

La configuración inicial corresponde exclusivamente a Binance Spot. Quedan prohibidos Margin Trading, Futures, Perpetual Contracts, préstamos de activos para incrementar exposición, posiciones Short y cualquier mecanismo de apalancamiento.

---

## ¿Cómo entran comisiones, slippage y otros costes?

### Inclusión obligatoria

Las comisiones y costes estimados deberán formar parte del presupuesto de riesgo. No se permitirá calcular el position sizing utilizando únicamente la diferencia entre entrada y salida.

### Fuente de costes

La configuración técnica deberá obtener o mantener comisión de entrada, comisión de salida, tipo de orden, reserva de slippage y otros costes aplicables. Las tasas deberán corresponder a la cuenta y modalidad de ejecución utilizadas.

No se asumirán comisiones promocionales ni descuentos por uso de BNB sin verificar que estén efectivamente disponibles.

### Fallos de estimación

Si los costes no pueden calcularse de forma razonable, no se autorizará la nueva entrada; se registrará el motivo del bloqueo; y se solicitará actualización de la configuración.

---

## ¿Cómo funciona el drawdown mensual?

### Límite aprobado

El drawdown mensual máximo será del 5%. Con un equity inicial de $3,000 MXN:

\[
MonthlyLossLimit = 3000 \times 0.05
\]

\[
MonthlyLossLimit = 150\ MXN
\]

### Equity de referencia mensual

El sistema registrará el equity al inicio de cada mes calendario.

\[
MonthlyBaseline = Equity_{inicio\ de\ mes}
\]

El valor quedará congelado durante ese mes. Para el primer periodo, la referencia inicial será de $3,000 MXN, siempre que ese sea el equity efectivo al iniciar la operativa.

### Cálculo del drawdown mensual

\[
MonthlyLoss =
MonthlyBaseline - CurrentEquity
\]

\[
MonthlyDrawdown =
\frac{MonthlyBaseline-CurrentEquity}
{MonthlyBaseline}\times100
\]

La medición deberá incorporar pérdidas realizadas y no realizadas. Las ganancias y pérdidas de las posiciones abiertas deberán valorarse de forma consistente con el equity actual.

### Condición de bloqueo

\[
MonthlyDrawdown \geq 5\%
\]

Cuando se alcance o supere este umbral:

1. Bloquear nuevas entradas.
2. Cancelar órdenes de entrada pendientes.
3. Mantener los mecanismos de salida de posiciones abiertas.
4. Registrar el evento de bloqueo.
5. Solicitar revisión y autorización humana antes de reanudar entradas.

### Tratamiento de posiciones abiertas

La activación del drawdown mensual no obliga al cierre inmediato de una posición abierta.

Se aplicará la decisión aprobada:

**Bloquear nuevas entradas y permitir que las posiciones existentes continúen bajo sus mecanismos de protección y salida previamente definidos.**

No se podrán ampliar posiciones ni incrementar su riesgo inicial.

### Restablecimiento mensual

El cambio de mes no deberá interpretarse como una autorización automática para reanudar operaciones. El sistema podrá inicializar una nueva referencia mensual, pero cualquier bloqueo preventivo o de seguridad pendiente deberá resolverse conforme a su mecanismo de revisión.

El bloqueo por drawdown requerirá autorización humana para su liberación.

---

## ¿Qué pasa tras tres pérdidas seguidas?

### Umbral preventivo

\[
LossStreak \geq 3
\]

Al alcanzarlo, el sistema suspenderá nuevas entradas; registrará la secuencia de pérdidas; generará un evento de revisión; solicitará evaluación humana; y mantendrá la protección de cualquier posición abierta.

### Operación perdedora

Una operación se considerará perdedora cuando su resultado neto realizado sea negativo después de comisiones y costes atribuibles. El resultado de una operación se determinará una vez completado su cierre y reconciliación.

### Reinicio del contador

El contador de pérdidas consecutivas se reiniciará cuando una operación cerrada registre un resultado neto positivo. Una operación con resultado exactamente igual a cero no incrementará el contador ni lo reiniciará.

### Liberación del bloqueo

El bloqueo por tres pérdidas consecutivas no tendrá una duración automática. Su liberación requerirá:

1. Revisión humana de la secuencia.
2. Verificación del estado de la estrategia.
3. Revisión de los eventos de ejecución.
4. Autorización humana explícita.

Una nueva operación no podrá ejecutarse únicamente porque haya transcurrido determinado tiempo.

---

## ¿Se puede modificar el stop después de entrar?

### Modificaciones permitidas

Se permite modificar el stop-loss después de abrir una posición únicamente para reducir el riesgo de pérdida, proteger el capital, proteger beneficios, implementar un trailing stop o mejorar el nivel de salida sin ampliar la pérdida máxima inicialmente autorizada.

### Restricción absoluta

Para posiciones Long, el nuevo nivel de stop no podrá encontrarse por debajo del nivel de stop inicialmente autorizado.

\[
P_{stop\ nuevo} \geq P_{stop\ inicial}
\]

La condición se aplica a modificaciones del nivel de protección, no a diferencias de ejecución provocadas por slippage.

### Modificaciones prohibidas

Queda prohibido alejar el stop para evitar una pérdida; incrementar el riesgo inicial; eliminar el mecanismo de salida sin sustituirlo por otro mecanismo válido; cambiar el stop para justificar una operación que excedería el presupuesto autorizado; o permitir que un agente amplíe discrecionalmente el riesgo.

Cualquier modificación deberá quedar registrada y ser verificable.

---

## ¿Cuál es el límite de operaciones al mes?

\[
MonthlyTradeCount \leq 8
\]

Se establece una frecuencia máxima de referencia de ocho operaciones por mes calendario. El contador considerará operaciones completadas, no mensajes de señal ni intentos de análisis.

Una operación parcialmente ejecutada que posteriormente se cierre contará como una operación. Las entradas canceladas sin ejecución no se contabilizarán como operaciones completadas, aunque deberán registrarse como eventos.

Al alcanzar ocho operaciones completadas, el sistema bloqueará nuevas entradas durante el periodo; mantendrá la gestión de posiciones abiertas; permitirá únicamente las operaciones de salida y protección; y requerirá autorización humana para cualquier cambio de la política en periodos posteriores.

Este límite no constituye un objetivo de actividad. SwingPilot no debe operar para consumir su cuota mensual.

---

## ¿Cómo se protegen posiciones abiertas bajo bloqueo?

Las restricciones de nuevas entradas no deberán interferir con las acciones necesarias para reducir o cerrar el riesgo existente.

Se consideran acciones de protección: ejecutar un stop-loss; ejecutar un mecanismo alternativo de salida autorizado; cerrar total o parcialmente una posición para reducir exposición; cancelar órdenes de entrada pendientes; reconciliar el estado de las órdenes; y ejecutar acciones de contingencia ante fallos.

La protección de una posición abierta tiene prioridad sobre la suspensión de nuevas entradas. Ningún bloqueo de riesgo deberá impedir una acción necesaria para cerrar una posición o limitar su exposición.

La política tampoco autoriza al sistema a abrir una nueva posición bajo el argumento de proteger una existente.

---

## ¿Cómo funciona la autorización humana?

SwingPilot operará bajo Nivel 1: aprobación humana individual. Los agentes pueden analizar y proponer operaciones; el Risk Manager puede calcular y validar el riesgo; los agentes pueden preparar solicitudes de ejecución; el propietario debe autorizar individualmente cada nueva operación; y ninguna entrada podrá ejecutarse sin autorización válida.

### Validación previa

Antes de solicitar aprobación humana, la operación deberá superar todas las restricciones de riesgo. El usuario no deberá recibir solicitudes de aprobación para operaciones que ya incumplan la política.

### Alcance de la autorización

La autorización humana no sustituye la validación técnica. Una operación autorizada por el usuario deberá rechazarse si, en el momento de ejecución, el equity cambió de forma relevante; el riesgo efectivo excede el presupuesto; existe otra posición abierta; se alcanzó el drawdown mensual; se activó una suspensión preventiva; se alcanzó el límite de operaciones; o la orden no cumple las restricciones del mercado.

La operación deberá recalcularse y requerir una nueva autorización cuando sus parámetros hayan cambiado materialmente.

### Prohibición de excepciones autónomas

Ningún agente podrá crear excepciones a esta política. La modificación de un límite requiere una revisión documental y una aprobación humana explícita. Los agentes podrán proponer cambios, pero no implementarlos por iniciativa propia.

---

## ¿Qué se registra para auditoría?

Todas las decisiones relevantes del Risk Manager deberán ser auditables.

### Eventos obligatorios

Se deberán registrar:

- Actualización del equity.
- Cálculo del presupuesto de riesgo.
- Cálculo del tamaño de posición.
- Validación de una operación.
- Rechazo de una operación.
- Autorización humana.
- Ejecución de una orden.

Y también:

- Modificación del stop-loss.
- Cierre de posición.
- Pérdida realizada.
- Actualización del drawdown.
- Activación de un bloqueo.
- Liberación de un bloqueo.
- Errores de sincronización con Binance.

### Información mínima por evento

| Campo | Descripción |
|---|---|
| `event_id` | Identificador único |
| `timestamp` | Fecha y hora |
| `event_type` | Tipo de evento |
| `operation_id` | Operación relacionada |
| `equity` | Equity utilizado |
| `risk_budget` | Presupuesto calculado |
| `effective_risk` | Riesgo efectivo estimado |
| `position_size` | Tamaño calculado |
| `decision` | APPROVED / REJECTED / BLOCKED |
| `reason` | Motivo de la decisión |
| `actor` | Componente responsable |
| `policy_version` | Versión de política aplicada |

Los registros deberán conservar suficiente información para reconstruir por qué una operación fue autorizada, rechazada o bloqueada.

### Integridad

Los registros de riesgo no deberán ser modificables retroactivamente por los agentes que participan en la ejecución. Las correcciones deberán generar nuevos eventos que preserven el historial original.

---

## ¿En qué estados puede estar el Risk Manager?

| Estado | Descripción | Nuevas entradas |
|---|---|---|
| `ACTIVE` | Sin bloqueos y con límites disponibles | Permitidas bajo validación y aprobación humana |
| `POSITION_OPEN` | Existe una posición abierta | Bloqueadas |
| `LOSS_STREAK_LOCK` | Tres pérdidas consecutivas | Bloqueadas |
| `MONTHLY_DRAWDOWN_LOCK` | Drawdown mensual ≥ 5% | Bloqueadas |
| `MONTHLY_TRADE_LIMIT_LOCK` | Ocho operaciones completadas | Bloqueadas |
| `DATA_UNAVAILABLE` | Datos críticos no verificables | Bloqueadas |
| `EXCHANGE_DESYNC` | Estado local y exchange no coinciden | Bloqueadas |
| `MANUAL_REVIEW` | Se requiere revisión humana | Bloqueadas |

Los estados de bloqueo podrán coexistir. El sistema deberá conservar todas las causas activas. La liberación de un bloqueo no deberá eliminar automáticamente otros bloqueos que continúen vigentes.

Las salidas y acciones de protección permanecerán disponibles cuando técnicamente sea posible.

---

## ¿Cuáles son los invariantes de riesgo?

Los siguientes invariantes son restricciones fundamentales del sistema. No podrán ser modificados por estrategias ni agentes.

**INV-001 — Riesgo máximo**

\[
RiskEffective \leq Equity \times 0.015
\]

**INV-002 — Drawdown mensual**

\[
MonthlyDrawdown < 0.05
\]

para permitir nuevas entradas.

**INV-003 — Posición única**

\[
OpenPositions \leq 1
\]

**INV-004 — Sin apalancamiento**

\[
Leverage = 1
\]

Operativa exclusivamente Spot, sin financiación externa.

**INV-005 — Long-only**

No se permiten operaciones Short.

**INV-006 — Sin promediado a la baja**

No se permite aumentar la exposición de una posición perdedora mediante nuevas entradas.

**INV-007 — Salida definida**

Toda operación requiere un mecanismo de salida verificable antes de su autorización.

**INV-008 — Aprobación humana**

Ninguna nueva operación se ejecuta sin autorización individual válida.

**INV-009 — Riesgo de stop invariable**

No se permite ampliar la pérdida máxima inicialmente autorizada mediante modificaciones del stop.

**INV-010 — Frecuencia**

\[
MonthlyTradeCount \leq 8
\]

**INV-011 — Racha de pérdidas**

Tres pérdidas consecutivas activan suspensión preventiva.

**INV-012 — Fail-Closed**

La imposibilidad de verificar una condición de riesgo bloquea nuevas entradas.

---

## ¿Cuándo se considera bien implementada esta política?

La implementación de esta política se considerará técnicamente aceptable únicamente cuando se demuestre que:

1. El equity se calcula correctamente a partir de los saldos y posiciones reales.
2. El presupuesto del 1.5% se actualiza con el equity actual.
3. El position sizing incorpora precio, costes y reserva de slippage.
4. El redondeo de cantidades no permite exceder el presupuesto.
5. No pueden existir dos posiciones abiertas simultáneamente.
6. El sistema rechaza operaciones sin mecanismo de salida.
7. El sistema rechaza cualquier intento de promediar a la baja.
8. El drawdown incorpora pérdidas realizadas y no realizadas.
9. El bloqueo mensual se activa al alcanzar el 5%.
10. Tres pérdidas consecutivas activan la suspensión.
11. Los bloqueos requieren las autorizaciones correspondientes para su liberación.
12. Los stops no pueden modificarse para ampliar el riesgo inicial.
13. El límite mensual de ocho operaciones se respeta.
14. Los agentes no pueden ejecutar operaciones sin aprobación humana.
15. Los errores de datos o sincronización producen un comportamiento restrictivo.
16. Todos los eventos de riesgo quedan registrados y son auditables.

Cada criterio deberá contar con pruebas automatizadas y evidencia de validación.

---

## ¿Qué falta definir a nivel técnico?

Los límites de riesgo ya están aprobados. Los siguientes elementos son parámetros de implementación que deberán definirse durante el contrato técnico, sin modificar las decisiones del propietario.

| Parámetro | Tratamiento |
|---|---|
| Fuente de conversión USDT/MXN | Por definir |
| Antigüedad máxima del tipo de cambio | Por definir |
| Comisión efectiva de Binance | Obtener de la cuenta |
| Reserva de slippage | Configuración técnica conservadora |
| Tolerancia de desviación de precio | Por definir |
| Precisión de cantidades y precios | Obtener de filtros del mercado |
| Frecuencia de reconciliación | Por definir |
| Persistencia de bloqueos | Obligatoria |
| Mecanismo de aprobación humana | Contrato técnico |
| Procedimiento de recuperación ante fallos | Contrato técnico |

Estos parámetros no podrán configurarse de manera que permitan superar los límites aprobados.

---

## ¿Cómo se cambia esta política?

Cualquier modificación de esta política deberá quedar documentada. Toda modificación deberá incluir identificador del cambio, versión anterior, versión propuesta, motivo del cambio, impacto sobre el riesgo, componentes afectados, pruebas requeridas y aprobación humana explícita.

Ninguna modificación podrá aplicarse retroactivamente a operaciones ya autorizadas sin un procedimiento de migración y reconciliación documentado.
