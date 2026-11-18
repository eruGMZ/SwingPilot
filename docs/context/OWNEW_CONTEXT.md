# Contexto del propietario y política operativa (SwingPilot)

**Versión:** 1.0  
**Fecha:** 11 de noviembre de 2026  
**Estado:** Aprobado como fuente de contexto operativo  
**Propietario:** Erick Uriel Reyes Gómez

---

## ¿Para qué sirve este documento y quién tiene la última palabra?

Este apartado define el contexto del propietario de SwingPilot: situación fiscal documentada, perfil operativo, capital autorizado, límites de riesgo, instrumentos permitidos y nivel de autonomía.

Es la fuente de verdad para los agentes, módulos y componentes de SwingPilot respecto a las decisiones personales y operativas del propietario. Los agentes no pueden modificar estos parámetros por inferencia, optimización o conveniencia técnica; cualquier modificación requiere autorización expresa del propietario.

---

## ¿Cuál es la situación fiscal y laboral documentada?

La siguiente tabla resume la evidencia registrada en el sistema.

| Campo | Información |
|---|---|
| País de residencia fiscal | México |
| Régimen fiscal (efectivo según el propietario) | 605 — Sueldos y Salarios e Ingresos Asimilados a Salarios, desde 13/10/2025 |
| Régimen anterior | 616 — Sin obligaciones fiscales (29/06/2021 – 12/10/2025) |
| Aviso de cambio de régimen ante el SAT | Presentado el 17/11/2026 (DEC-003) |
| Asesoría fiscal especializada en criptomonedas | No consultada |
| Asesoría fiscal general | No consultada |

### ¿Qué advertencia fiscal está pendiente?

El propietario percibe ingresos laborales bajo el régimen 605.

SwingPilot no debe asumir que el propietario está exento de ISR (Impuesto Sobre la Renta) por operar criptomonedas, que las ganancias de trading tienen ISR cero, que existe una exención anual automática aplicable ni que la clasificación fiscal de todas las operaciones está resuelta.

Por lo tanto, el tratamiento fiscal de las operaciones deberá validarse profesionalmente antes de establecer obligaciones, cálculos definitivos o declaraciones.

---

## ¿Cómo opera el propietario en el mercado?

Este perfil acota estilo, mercado, frecuencia y exchange; se alinea con los límites de instrumentos descritos más adelante.

| Parámetro | Decisión |
|---|---|
| Estilo | Swing Trading |
| Horizonte habitual | 2 días a 2 semanas |
| Mercado inicial | Spot |
| Orientación | Long-only |
| Temporalidades de análisis | D1 y H4/H1 |
| Frecuencia máxima de referencia | 8 operaciones mensuales |
| Frecuencia mínima | Ninguna |
| Exchange | Binance exclusivamente |

El propietario no busca operar constantemente: la ausencia de señales válidas es un resultado aceptable. El sistema debe priorizar la calidad de las oportunidades, la preservación del capital y la disciplina operativa sobre la frecuencia de ejecución.

---

## ¿Cuánto capital está autorizado?

| Parámetro | Valor |
|---|---:|
| Capital inicial | $3,000 MXN |
| Ticket habitual por operación | $500–$5,000 MXN |
| Ticket extraordinario máximo | $10,000 MXN |
| Origen del capital | Personal |

El capital inicial y los tickets no son equivalentes. Una vez definido el riesgo permitido, el tamaño de cada posición debe calcularse según la distancia al mecanismo de salida y los costes de ejecución.

El sistema no tiene autorización para utilizar capital de WeirdCow, solicitar préstamos o utilizar fondos prestados, incrementar el capital disponible por iniciativa propia ni interpretar el ticket máximo como autorización para arriesgar esa cantidad. Cualquier aportación adicional requiere autorización del propietario (véase también «¿Qué cambios exigen autorización expresa?»).

---

## ¿Qué política de riesgo aplica?

Los límites numéricos de esta sección son vinculantes; ningún agente puede ampliarlos ni ignorar una suspensión (véase «¿Qué puede y no puede hacer SwingPilot?»).

### ¿Cuál es el riesgo máximo por operación?

**Límite máximo: 1.5% del capital de referencia.**

Este porcentaje representa la pérdida máxima presupuestada para una operación, no el tamaño de la posición. Con un capital inicial de $3,000 MXN, el presupuesto máximo inicial de pérdida es $45 MXN por operación. El cálculo deberá considerar comisiones y costes de ejecución cuando sea posible.

### ¿Qué ocurre con el drawdown mensual?

<badge color="danger">Límite estricto: 5%</badge>

El drawdown (caída acumulada respecto al pico o referencia definida) mensual se medirá respecto al capital de referencia al inicio de cada mes. El cálculo debe considerar pérdidas realizadas, pérdidas flotantes, comisiones y costes de operación.

Con un capital de referencia de $3,000 MXN, el límite inicial equivale a $150 MXN. **El límite del 5% sustituye cualquier referencia anterior al 6%.**

Al alcanzar el límite, el sistema deberá, en este orden:

1. Suspender nuevas operaciones.
2. Invalidar señales pendientes de ejecución.
3. Mantener los registros y análisis.
4. No reanudar operaciones automáticamente.
5. Exigir autorización expresa del propietario para reanudar.

### ¿Qué principio prima sobre las oportunidades?

La protección del capital tiene prioridad sobre la generación de oportunidades. Ningún agente puede ampliar los límites de riesgo, ignorar una suspensión o cambiar los parámetros para recuperar pérdidas.

---

## ¿Qué instrumentos y operaciones están permitidos?

### Instrumento y operaciones autorizadas

- **Instrumento autorizado:** BTC/USDT.
- **Operaciones autorizadas:** comprar BTC utilizando USDT; vender BTC a cambio de USDT.

### ¿Qué queda fuera del alcance inicial?

Otras criptomonedas, conversiones entre criptoactivos, staking, Earn, airdrops y movimientos adicionales quedan fuera de la validación inicial. No deben incorporarse al alcance por iniciativa de los agentes.

### Restricciones operativas

- Binance Spot exclusivamente.
- Sin futuros ni contratos perpetuos.
- Sin margin.
- Sin apalancamiento.
- Sin posiciones short.
- Sin copy trading.
- Sin capital prestado.
- Sin operaciones fuera de los instrumentos autorizados.

---

## ¿Qué puede y no puede hacer SwingPilot?

<badge color="success">Nivel 1 — Asistido</badge>

En este nivel de autonomía, SwingPilot puede analizar el mercado, investigar y comparar estrategias, detectar oportunidades, generar señales, calcular entradas, salidas y riesgo estimado, presentar recomendaciones y escenarios, monitorear posiciones y condiciones de riesgo, y registrar resultados y evidencias.

Sin embargo, SwingPilot no puede ejecutar órdenes reales sin autorización individual del propietario, comprar o vender por iniciativa propia, modificar el capital autorizado, alterar los límites de riesgo, reanudar operaciones después de una suspensión sin autorización ni convertir una recomendación en una orden ejecutable sin aprobación humana.

**La autorización humana es obligatoria para cada operación real.**

---

## ¿Cómo se separa investigación de ejecución?

El sistema debe mantener separación entre las siguientes etapas, en secuencia lógica:

1. Investigación de estrategias.
2. Validación experimental.
3. Generación de señales.
4. Recomendación operativa.
5. Autorización humana.
6. Ejecución real.
7. Registro y evaluación posterior.

Las estrategias no se consideran aprobadas por el simple hecho de producir resultados positivos en *backtesting* (simulación sobre histórico). Los agentes deben conservar trazabilidad, documentar supuestos y distinguir evidencia experimental de decisiones aprobadas.

SwingPilot puede investigar distintas familias de estrategias sin heredar automáticamente hipótesis, parámetros o estrategias de otros proyectos.

---

## ¿Qué cambios exigen autorización expresa del propietario?

Las siguientes decisiones requieren autorización expresa del propietario:

- Incrementar el capital.
- Incorporar nuevos activos o pares.
- Incorporar otro exchange.
- Modificar el riesgo por operación.
- Modificar el drawdown mensual.
- Habilitar ejecución automática.
- Incorporar derivados, margin o apalancamiento.
- Modificar la política fiscal o contable.

Ningún agente puede interpretar una sugerencia, resultado experimental o recomendación propia como autorización.

---

## ¿Cuál es la regla final del sistema?

**Regla final:** SwingPilot es un sistema de investigación y apoyo a decisiones de trading bajo control del propietario. La autonomía técnica nunca equivale a autoridad para disponer del capital.
