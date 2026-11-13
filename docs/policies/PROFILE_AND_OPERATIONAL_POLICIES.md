# Perfil del Operador y Política de Investigación Cuantitativa y Machine Learning (SwingPilot)

**Tipo:** Documento fundacional  
**Proyecto:** SwingPilot  
**Versión:** 1.0  
**Estado:** Propuesta documental para aprobación  
**Clasificación:** Privado — Uso interno  
**Ámbito:** Perfil operativo, investigación cuantitativa, Machine Learning (ML, aprendizaje automático a partir de datos), validación experimental y gobernanza.

---

## ¿Para qué existe este documento?

Este apartado fija el perfil operativo del usuario de SwingPilot y los principios metodológicos que deberán gobernar la investigación, desarrollo, entrenamiento, evaluación y validación de estrategias cuantitativas y modelos de ML.

El documento busca que SwingPilot opere bajo un enfoque sistemático, reproducible y basado en evidencia, evitando decisiones sustentadas únicamente en intuiciones, resultados históricos aislados o modelos aparentemente rentables que no hayan demostrado capacidad de generalización (comportamiento estable en datos no usados durante el desarrollo).

En consecuencia, la metodología deberá permitir investigar distintas familias de estrategias de trading y formular hipótesis verificables; diseñar experimentos independientes; construir conjuntos de datos (*datasets*) trazables y reproducibles; entrenar y evaluar modelos de ML; detectar sobreajuste (*overfitting*, ajuste excesivo al histórico), *leakage* (fuga de información entre particiones) y sesgos experimentales; validar la robustez de los resultados; y evaluar estrategias bajo condiciones realistas de mercado. Una vez cumplidos esos controles, deberá ser posible determinar cuándo una estrategia o modelo merece avanzar a una siguiente etapa, manteniendo siempre control humano sobre el capital y la autorización de operaciones.

**Principio rector:** ningún modelo, estrategia o resultado experimental deberá considerarse válido únicamente por presentar rentabilidad histórica. Su aceptación dependerá de la calidad metodológica, reproducibilidad, robustez y capacidad de generalización demostrada.

---

## ¿Cuál es el perfil operativo del usuario?

Aquí se define cómo opera el usuario en el mercado, con qué instrumentos y bajo qué límites de actividad y capital; estos límites se enlazan con la gobernanza de IA descrita más adelante.

### ¿Cómo se clasifica el operador?

El perfil operativo inicial queda definido de la siguiente manera:

| Dimensión           | Clasificación                           |
| ------------------- | --------------------------------------- |
| Estilo operativo    | Swing Trading                           |
| Horizonte habitual  | Días a semanas                          |
| Instrumento         | Spot Trading (compra/venta al contado, sin apalancamiento en el activo subyacente) |
| Exchange inicial    | Binance                                 |
| Activo prioritario  | BTC/USDT                                |
| Dirección operativa | Long-only                               |
| Estrategia          | No restringida a una familia específica |
| Enfoque             | Sistemático y basado en evidencia       |
| Apalancamiento      | No permitido                            |
| Futuros y derivados | Fuera del alcance inicial               |

El perfil corresponde a un operador que busca capturar movimientos relevantes del mercado sin depender de una supervisión constante ni de operaciones intradía frecuentes. Por lo tanto, la plataforma deberá priorizar oportunidades que puedan desarrollarse durante varios días o semanas, respetando las condiciones particulares de cada estrategia.

### ¿Qué temporalidades admite el análisis?

SwingPilot deberá admitir distintas temporalidades dependiendo de la hipótesis y estrategia investigada. Las temporalidades contempladas inicialmente son H1 (1 hora), H4 (4 horas) y 1D (diario).

No deberá imponerse una temporalidad universal para todas las estrategias: la selección deberá justificarse mediante la hipótesis experimental y evaluarse durante la investigación. Como resultado, una estrategia diseñada para H4 no deberá considerarse automáticamente válida para H1 o 1D.

### ¿Con qué frecuencia puede operarse?

Se establece como referencia un máximo de 8 operaciones mensuales. Este límite representa una restricción operativa, no un objetivo de actividad; por lo tanto, SwingPilot no deberá generar operaciones artificiales para alcanzar una cantidad determinada. Si las condiciones de mercado no presentan oportunidades válidas, la decisión correcta será no operar.

### ¿Quién controla el capital?

La asignación de capital constituye una decisión exclusiva del operador. La inteligencia artificial podrá analizar escenarios, estimar exposición, evaluar riesgos, proponer distribuciones y presentar escenarios de pérdida potencial; sin embargo, no podrá modificar autónomamente el capital autorizado, incrementar la exposición aprobada ni reasignar fondos. Toda modificación de capital deberá contar con autorización humana explícita (véase también los límites de IA en «¿Qué puede hacer la IA y dónde se detiene?»).

---

## ¿Qué principios rigen toda investigación cuantitativa?

Las siguientes reglas aplican a cualquier investigación; su materialización práctica aparece en registro de experimentos, datos, auditoría y criterios de aceptación.

### Hipótesis antes de resultados

Cada investigación deberá comenzar con una pregunta concreta y una hipótesis falsable (capaz de ser refutada con evidencia). No se permitirá modificar retrospectivamente una hipótesis para justificar resultados obtenidos.

### Separación entre investigación y validación

Los datos utilizados para desarrollar una estrategia no podrán confundirse con aquellos destinados a evaluar su capacidad de generalización.

### Reproducibilidad

Cada experimento deberá poder ejecutarse nuevamente bajo las mismas condiciones, utilizando los mismos datos, configuraciones, versiones y procedimientos. La verificación en auditoría se detalla en «¿Qué comprueba una auditoría?».

### Trazabilidad

Cada decisión metodológica, transformación de datos, configuración y resultado deberá quedar documentado. Los requisitos sobre *datasets* y expedientes experimentales amplían este principio en las secciones correspondientes.

### Falsabilidad

Los experimentos deberán contemplar condiciones que permitan rechazar una hipótesis. No se considerará válida una metodología que únicamente busque demostrar que una estrategia funciona.

### Generalización

El objetivo no será maximizar el rendimiento histórico, sino identificar estrategias y modelos capaces de mantener un comportamiento aceptable frente a datos no utilizados durante su desarrollo.

---

## ¿Cómo se diseña y registra un experimento?

Cada estrategia o modelo de ML deberá constituir una entidad experimental independiente; no se deberán mezclar resultados de diferentes experimentos para construir artificialmente una conclusión favorable.

### ¿Qué debe constar en el expediente?

Cada investigación deberá contar con un identificador único y un expediente documental. Los experimentos deberán contar con control de versiones; una modificación sustancial de hipótesis, arquitectura, *dataset* o configuración deberá quedar registrada como una nueva versión o investigación independiente, según su alcance.

Como mínimo deberá registrar lo siguiente.

**Contexto del experimento:**

- Identificador del experimento.
- Nombre de la hipótesis.
- Familia de estrategia.
- Activo y mercado.
- Exchange y tipo de instrumento.
- Temporalidad.
- Periodo histórico.

**Datos, configuración y modelo:**

- Fuente de datos.
- Fecha de descarga.
- Hash SHA-256 (resumen criptográfico de integridad) de los archivos.
- Configuración experimental.
- Indicadores y características utilizadas.
- Modelo de ML, cuando corresponda.
- Parámetros de entrenamiento.

**Resultados y gobierno:**

- Métricas de evaluación.
- Resultados.
- Limitaciones.
- Conclusión.
- Estado y responsable de aprobación.

### ¿Qué exige el preregistro antes de evaluar?

Antes de ejecutar un *backtest* confirmatorio o entrenar un modelo destinado a evaluación formal, deberá existir un preregistro. El preregistro deberá congelarse antes de la evaluación confirmatoria; cualquier desviación deberá documentarse y justificarse.

El documento de preregistro deberá contener, como mínimo:

**Pregunta, hipótesis y diseño:**

- Pregunta de investigación.
- Hipótesis principal.
- Hipótesis nula, cuando corresponda.
- Justificación de la estrategia.
- Universo de activos.
- Temporalidad.
- Periodo de investigación.

**Variables, reglas y evaluación:**

- Variables y características previstas.
- Reglas de entrada y salida.
- Modelo y configuración inicial.
- División de datos.
- Métricas principales y secundarias.
- Costes operativos.
- Criterios de aceptación y rechazo.
- Limitaciones conocidas.

---

## ¿Cómo se tratan los datos?

La calidad de los datos constituye una condición fundamental para la validez de cualquier investigación.

### ¿Qué metadatos exige cada dataset?

Todo *dataset* deberá registrar fuente de adquisición, fecha de descarga, fecha inicial y final, zona horaria, frecuencia, activo, *exchange*, tipo de datos, formato, integridad, tratamiento aplicado y hash SHA-256.

Los archivos originales deberán conservarse sin modificaciones. Las transformaciones deberán producir *datasets* derivados, manteniendo relación verificable con su fuente.

### ¿Cómo se valida integridad y calidad?

Deberán verificarse datos faltantes, duplicados, velas incompletas, errores de *timestamp*, desorden cronológico, valores inconsistentes, saltos anormales y diferencias entre fuentes.

Las anomalías no deberán corregirse silenciosamente; cada tratamiento deberá documentarse.

### ¿Cómo se aíslan entrenamiento, validación y evaluación?

La investigación deberá separar temporalmente Training Set, Validation Set, Out-of-Sample (OOS, datos no usados en desarrollo) y LOCKBOX OOS (reserva para evaluación final sin participación previa en decisiones de modelado).

El conjunto de entrenamiento se utilizará para ajustar modelos y aprender patrones. *Validation* permitirá seleccionar configuraciones y ajustar hiperparámetros. OOS permitirá evaluar el comportamiento sobre datos no utilizados durante el desarrollo. LOCKBOX OOS deberá permanecer aislado y reservado para una evaluación final; no se permitirá utilizar información del LOCKBOX para seleccionar características, modificar hiperparámetros o rediseñar modelos.

La distribución y los periodos específicos deberán definirse por experimento. La evaluación final sobre LOCKBOX se desarrolla en «¿Cómo se prueba robustez y evaluación final OOS?».

---

## ¿Qué sesgos y fugas de información se prohíben?

Estos controles complementan el aislamiento de datos y se verifican en auditoría.

### Look-ahead bias

Queda prohibido utilizar información que no habría estado disponible en el momento histórico en que se habría generado una señal. Las características, indicadores y decisiones deberán respetar la disponibilidad temporal real de la información.

### Data leakage

Se deberá prevenir cualquier transferencia indebida de información entre conjuntos de entrenamiento, validación y evaluación. Los controles deberán cubrir variables derivadas del futuro, normalización sobre el *dataset* completo, imputación utilizando información futura, selección de características con datos OOS, etiquetas que incorporen información posterior a la fecha de decisión, ventanas temporales superpuestas y contaminación entre observaciones de entrenamiento y evaluación.

En particular, las transformaciones y procesos de selección deberán ajustarse exclusivamente con los datos permitidos en cada partición.

### Sesgo de supervivencia

Cuando la investigación involucre múltiples activos, deberá contemplarse el sesgo de supervivencia y evitar construir universos históricos únicamente con activos que siguen existiendo actualmente.

### Sesgo de selección

No se permitirá seleccionar únicamente los experimentos exitosos para presentar conclusiones generales. El registro deberá conservar también los experimentos rechazados y sus motivos.

---

## ¿Cómo se usa Machine Learning sin confundirlo con la estrategia?

Esta sección adapta los controles experimentales al ciclo de vida de modelos predictivos.

### Separación entre predicción y decisión operativa

Un modelo de ML no constituye por sí mismo una estrategia completa. El flujo deberá distinguir, en orden:

1. Generación de características.
2. Inferencia del modelo.
3. Interpretación de predicciones.
4. Generación de señales.
5. Evaluación de riesgo.
6. Autorización de operación.
7. Ejecución.

Una predicción favorable no implica automáticamente una orden de compra. El modelo deberá producir resultados que puedan ser interpretados y evaluados por los componentes posteriores de SwingPilot.

### Modelos candidatos

La investigación podrá considerar diferentes familias de modelos. Como punto de partida: Random Forest, XGBoost, otros modelos basados en árboles, modelos de series temporales y redes neuronales recurrentes, incluyendo LSTM, cuando exista justificación experimental.

La selección no deberá realizarse por popularidad o complejidad. Cada modelo deberá demostrar una mejora verificable frente a un *baseline* apropiado. La incorporación de modelos más complejos deberá justificarse mediante resultados reproducibles y capacidad de generalización.

### Feature Engineering

Cada característica deberá contar con nombre, definición, fórmula, fuente, temporalidad, momento de disponibilidad, tratamiento y justificación de inclusión.

Deberá evaluarse si cada variable aporta información adicional y si puede calcularse sin utilizar información futura. Las características deberán quedar versionadas para garantizar reproducibilidad.

### Etiquetado de datos

Las etiquetas (*labels*) deberán responder a una hipótesis explícita. Se deberá documentar el evento que determina la etiqueta, el horizonte de predicción, las condiciones de éxito o fracaso, el tratamiento de resultados ambiguos, la ventana temporal utilizada y los posibles solapamientos.

No se deberán diseñar etiquetas utilizando información futura que después termine filtrándose inadvertidamente hacia las características del modelo.

### Entrenamiento y selección

El entrenamiento deberá respetar la naturaleza temporal del mercado; se deberá evitar la partición aleatoria convencional cuando esta produzca contaminación temporal. La selección de hiperparámetros deberá realizarse dentro de los conjuntos permitidos.

Cuando se comparen numerosos modelos, deberá registrarse el número de configuraciones probadas y contemplarse el riesgo de selección estadística.

### Evaluación predictiva y económica

Los modelos deberán evaluarse desde dos perspectivas diferentes.

| Perspectiva            | Métricas |
| ---------------------- | -------- |
| Rendimiento predictivo | Accuracy (cuando sea pertinente), Precision, Recall, F1-score, matriz de confusión, ROC-AUC (cuando sea apropiado), PR-AUC (cuando exista desbalance de clases), Brier Score y calibración probabilística (cuando el modelo produzca probabilidades). |
| Rendimiento operativo  | PnL neto, Expectancy, Profit Factor, Maximum Drawdown, Sharpe Ratio, Sortino Ratio, Calmar Ratio, cantidad de operaciones, exposición, costes operativos. |

Un modelo con buenas métricas predictivas no deberá considerarse automáticamente rentable. La utilidad económica de sus predicciones deberá comprobarse mediante una simulación de estrategia que incorpore las reglas de operación y costes reales.

---

## ¿Cómo se prueba robustez y evaluación final OOS?

### Walk-Forward Analysis

Se deberá incorporar evaluación Walk-Forward (entrenar en una ventana histórica, evaluar en un periodo posterior, desplazar la ventana y repetir) para estudiar la estabilidad del modelo y su comportamiento ante cambios temporales. El procedimiento deberá:

1. Entrenar utilizando una ventana histórica.
2. Evaluar sobre un periodo posterior.
3. Desplazar la ventana temporal.
4. Repetir el procedimiento.
5. Consolidar resultados.
6. Analizar estabilidad y degradación.

La configuración de ventanas deberá establecerse según la estrategia y temporalidad investigadas.

### Robustez

Los resultados deberán someterse a pruebas que permitan determinar si dependen excesivamente de una configuración particular. Se deberán investigar sensibilidad a parámetros, variaciones de temporalidad, diferentes condiciones de mercado, cambios en costes, variaciones de *slippage*, diferentes ventanas históricas, dependencia de determinadas operaciones y estabilidad entre periodos.

### Monte Carlo y Bootstrap

Se incorporarán métodos estadísticos para evaluar la incertidumbre de los resultados: *Bootstrap*, *Bootstrap* por bloques (cuando corresponda), simulación Monte Carlo, reordenamiento de secuencias de operaciones bajo supuestos explícitos, distribuciones de resultados y estimación de escenarios adversos.

Las simulaciones deberán respetar, en la medida pertinente, la dependencia temporal y las características de las operaciones. No deberán utilizarse para convertir una muestra insuficiente en evidencia estadística de rentabilidad.

### LOCKBOX OOS

La evaluación final deberá realizarse utilizando datos que no hayan participado en el desarrollo ni selección del modelo (véase aislamiento en «¿Cómo se aíslan entrenamiento, validación y evaluación?»). El acceso a estos datos deberá controlarse.

Una vez utilizados para tomar decisiones de desarrollo, dejarán de ser un conjunto de evaluación completamente virgen; su reutilización deberá quedar registrada y requerirá definir un nuevo periodo de evaluación independiente si se necesita evidencia confirmatoria adicional.

---

## ¿Qué debe modelar un backtest?

Todos los *backtests* deberán aproximarse a las condiciones reales de operación. Como mínimo deberán contemplar comisiones del *exchange*, *spread*, *slippage*, precio de ejecución, latencia (cuando sea relevante), restricciones de órdenes, disponibilidad de liquidez, deslizamientos adversos y capital disponible.

Los resultados deberán distinguir entre rendimiento bruto, costes operativos y rendimiento neto. No se permitirá presentar un *backtest* como representativo de resultados reales si omite costes relevantes. También deberán contemplarse escenarios adversos para determinar cuánto se degrada el rendimiento ante condiciones menos favorables.

---

## ¿Qué comprueba una auditoría?

Cada experimento deberá contar con evidencia suficiente para permitir una auditoría independiente. Los hallazgos deberán clasificarse, documentarse y resolverse antes de avanzar cuando afecten la validez metodológica.

Un resultado producido por un agente de IA no constituye una aprobación humana.

La auditoría deberá verificar, como mínimo:

**Diseño y datos:**

1. Integridad del preregistro.
2. Correspondencia entre hipótesis y ejecución.
3. Integridad de los *datasets*.
4. Correcta separación temporal.

**Sesgos, implementación y economía:**

5. Ausencia de *leakage*.
6. Ausencia de *look-ahead bias*.
7. Reproducibilidad del entrenamiento.
8. Correcta implementación del *backtest*.
9. Inclusión de costes.

**Métricas y decisión:**

10. Consistencia de métricas.
11. Robustez de resultados.
12. Cumplimiento de criterios de aceptación.

---

## ¿Cuándo se acepta, rechaza o deja inconcluso un experimento?

Cada experimento deberá definir criterios antes de su evaluación confirmatoria. Los criterios deberán considerar integridad metodológica, calidad de datos, capacidad predictiva, rentabilidad neta, riesgo, robustez, generalización, estabilidad temporal y reproducibilidad.

Se deberán contemplar al menos cuatro resultados posibles:

| Estado               | Significado |
| -------------------- | ----------- |
| **ACEPTADO**         | Cumple los criterios establecidos y puede solicitar autorización para avanzar a la siguiente etapa. |
| **RECHAZADO**        | Incumple criterios fundamentales o presenta evidencia insuficiente. |
| **INCONCLUSO**       | No existe evidencia suficiente para aceptar o rechazar la hipótesis. |
| **REQUIERE REVISIÓN** | Existen hallazgos que necesitan investigación o corrección antes de emitir una conclusión. |

La aceptación experimental no equivale a autorización para operar con capital real. Los umbrales numéricos de aceptación deberán definirse y aprobarse individualmente antes de ejecutar cada experimento formal.

---

## ¿Qué puede hacer la IA y dónde se detiene?

La inteligencia artificial constituye un componente de asistencia, investigación y análisis. Podrá participar en investigación de hipótesis, revisión documental, análisis de mercado, diseño de características, desarrollo de modelos, entrenamiento, *backtesting*, evaluación estadística, auditoría, generación de reportes, identificación de anomalías y propuestas de mejora.

Sin embargo, deberá respetar los siguientes límites:

1. No podrá modificar unilateralmente hipótesis congeladas.
2. No podrá modificar criterios de aceptación después de observar resultados para justificar un modelo.
3. No podrá utilizar datos reservados para modificar el entrenamiento.
4. No podrá declarar aprobado un experimento por autoridad propia.
5. No podrá modificar el capital asignado por el operador.
6. No podrá saltarse los controles del Risk Manager.
7. No podrá ejecutar operaciones sin cumplir las autorizaciones y reglas establecidas.

La IA podrá recomendar, pero la autoridad de aprobación corresponderá al operador.

---

## ¿Quién decide qué en la arquitectura de riesgo?

Se establece la siguiente separación de responsabilidades:

| Componente       | Responsabilidad                                  |
| ---------------- | ------------------------------------------------ |
| AI / Research    | Investigar, analizar y proponer.                 |
| Strategy Engine  | Generar señales conforme a reglas aprobadas.     |
| Model Engine     | Ejecutar inferencias de modelos validados.       |
| Risk Manager     | Evaluar y autorizar o rechazar operaciones.      |
| Execution Engine | Ejecutar operaciones autorizadas.                |
| Human Operator   | Aprobar estrategias, capital y cambios críticos. |

El Risk Manager deberá implementar controles deterministas. Una señal generada por una estrategia o modelo deberá pasar por este componente antes de llegar al motor de ejecución; la arquitectura deberá garantizar que ninguna recomendación de IA pueda omitir este proceso.

---

## ¿Cómo se exploran familias de estrategias?

SwingPilot deberá permitir investigar distintas familias de estrategias sin comprometer la independencia experimental descrita en «¿Cómo se diseña y registra un experimento?».

Entre las familias potenciales: Trend Following, Range Trading, Breakout Trading, Mean Reversion, Momentum, estrategias híbridas y estrategias asistidas por Machine Learning.

Cada familia deberá contar con hipótesis, condiciones de entrada y salida, características, temporalidades y criterios de evaluación propios. La incorporación de una nueva estrategia no deberá modificar retrospectivamente los resultados de investigaciones anteriores. La plataforma deberá permitir comparar estrategias bajo condiciones equivalentes cuando la metodología lo permita.

---

## ¿Por qué estados pasa un experimento?

Se propone el siguiente ciclo de vida; la transición entre estados deberá estar condicionada al cumplimiento de requisitos verificables.

1. **IDEA:** propuesta de investigación.
2. **DESIGN:** diseño de hipótesis y metodología.
3. **PREREGISTERED:** preregistro congelado.
4. **DATA_VALIDATION:** verificación de datos.
5. **DEVELOPMENT:** desarrollo y entrenamiento.
6. **VALIDATION:** evaluación y selección.
7. **OOS_EVALUATION:** evaluación fuera de muestra.
8. **AUDIT:** auditoría metodológica.
9. **HUMAN_REVIEW:** revisión y decisión del operador.
10. **APPROVED:** aprobación para avanzar a la siguiente etapa.
11. **REJECTED:** investigación rechazada.
12. **INCONCLUSIVE:** investigación sin evidencia concluyente.

---

## ¿Qué está aprobado y qué falta definir?

Para evitar interpretaciones incorrectas, se establece la siguiente clasificación entre decisiones ya adoptadas y parámetros aún abiertos.

### Decisiones aprobadas

- Swing Trading como perfil operativo.
- Binance Spot como instrumento inicial.
- BTC/USDT como activo prioritario.
- Enfoque long-only.
- Exclusión inicial de futuros, shorts y apalancamiento.
- Capital y asignación bajo autoridad exclusiva del operador.
- Máximo de referencia de 8 operaciones mensuales, sin obligación de alcanzarlo.
- Temporalidades H1, H4 y 1D disponibles según la estrategia.
- IA como asistente de investigación y análisis.
- Risk Manager con autoridad determinista de autorización o rechazo.
- Aprobación humana para estrategias, capital y decisiones críticas.
- Investigación experimental independiente para cada estrategia.
- Incorporación de preregistro, trazabilidad, validación OOS, LOCKBOX, Walk-Forward, robustez, Monte Carlo, Bootstrap y auditoría.

### Decisiones pendientes de definición

Los siguientes elementos no deberán interpretarse como decisiones definitivas. Cada elemento deberá resolverse mediante documentación, análisis y aprobación explícita.

**Partición de datos y validación:**

- Porcentajes exactos de división Train / Validation / OOS.
- Duración y tamaño de ventanas Walk-Forward.
- Requisitos estadísticos de aceptación.
- Tamaño mínimo de muestra.

**Umbrales de desempeño y riesgo:**

- Umbrales mínimos de rentabilidad.
- Drawdown máximo permitido.
- Expectancy mínimo.
- Profit Factor mínimo.

**Modelos en producción:**

- Configuración definitiva de modelos ML.
- Política de reentrenamiento.
- Detección de *concept drift*.
- Umbrales de degradación del modelo.
- Política de versionado y promoción de modelos a producción.

**Operación con capital real:**

- Política definitiva de dimensionamiento de posiciones.
- Límites cuantitativos del Risk Manager.
- Condiciones de autorización para operar con capital real.

---

## ¿Cuál es la filosofía de cierre?

SwingPilot deberá construirse bajo una filosofía de investigación cuantitativa rigurosa, donde la complejidad tecnológica no sustituya la evidencia. La incorporación de Machine Learning deberá incrementar la capacidad analítica y predictiva del sistema sin comprometer la integridad experimental.

El éxito de SwingPilot no deberá medirse por la cantidad de operaciones, modelos entrenados o señales generadas, sino por su capacidad para identificar, validar y gestionar estrategias con evidencia reproducible, control de riesgo y generalización fuera de muestra.

**La rentabilidad no se presupone: se investiga, se mide, se cuestiona y se valida.**

---

**Fin del documento.**

**Estado documental:** Propuesta para revisión y aprobación del operador.

**Restricción:** Este documento define principios y controles fundacionales. No constituye por sí solo un contrato técnico de implementación ni autoriza entrenamiento, despliegue o ejecución de estrategias con capital real.
