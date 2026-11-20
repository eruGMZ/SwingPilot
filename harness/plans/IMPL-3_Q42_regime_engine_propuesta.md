# IMPL-3 — Q42: propuesta para el Regime Engine

**Fecha:** 2026-11-20
**Estado:** PROPUESTA — PENDIENTE DE DECISIÓN DEL PROPIETARIO (DEC-017 Q42)
**Autor:** Orquestador de Desarrollo
**Alcance:** Presenta alternativas para que el propietario decida. No fija clases, indicadores, umbrales ni metodología. Los valores numéricos que aparecen son **convenciones de referencia** que el propietario puede adoptar, cambiar o descartar; ninguno queda aprobado por aparecer aquí.

---

## 1. Lo que el contrato ya fija

| Fuente | Restricción |
|---|---|
| REQ-G-057 | Motor determinista, no-LLM, verificable y reproducible. |
| REQ-G-071, data_flow.md §1 Fase 2 | Corre en el filtro determinista. Su salida la usan el Strategy Engine (al evaluar las estrategias aprobadas) y Decision Synthesis como contexto. **No es un decisor**: no genera ni veta operaciones por sí mismo. |
| REQ-G-071, DEC-011 | La resolución de candidatos es binaria y no usa puntuaciones de confianza. Un régimen solo influye en la decisión si es una **condición explícita** de la definición versionada de una estrategia. |
| REQ-G-001/002 | D1 = contexto, H4 = estructura y señal, H1 = evaluación de entrada. |
| REQ-G-070, REQ-G-102 | Solo velas cerradas, sin look-ahead; los parámetros se ajustan solo con datos de la partición permitida. |
| REQ-G-104, REQ-G-108 | Si el régimen se usa como filtro de una estrategia, forma parte del preregistro de esa estrategia y de su validación. |
| data_flow.md §5 | Evento E2 `REGIME_CLASSIFIED` (causa: E1). |

**Consecuencia práctica:** el piloto aprobado (Trend Following H4: EMA200, ADX14 > 25) ya contiene su propio filtro de tendencia. Si el Regime Engine usa los mismos indicadores, el filtro de régimen es **redundante** con las condiciones de la estrategia y no aporta información independiente. Es un criterio importante para elegir alternativa.

## 2. Preguntas que el propietario debe responder

1. **¿Para qué sirve el régimen en v1?** (a) solo contexto descriptivo para la síntesis y la auditoría; (b) condición de elegibilidad de estrategias (p. ej., «Trend Following solo en régimen X»); (c) ambas.
2. **¿Qué ejes clasifica?** dirección/tendencia, volatilidad, o ambos.
3. **¿Sobre qué temporalidad?** D1 (contexto, REQ-G-001) es lo coherente con el contrato; H4 duplicaría la temporalidad de la señal.
4. **¿Qué método?** (alternativas en §3).
5. **¿Qué valores?** periodos, umbrales e histéresis (o el procedimiento para fijarlos solo con Train).

## 3. Alternativas

### Alternativa A — Reglas sobre dos ejes en D1 (dirección × volatilidad)

- **Definición operacional (referencia):**
  - Eje de dirección, sobre velas D1 cerradas: `ALCISTA` si el cierre está por encima de una media móvil larga y su pendiente sobre N velas es positiva; `BAJISTA` si ocurre lo contrario; `LATERAL` en otro caso. Alternativa de fuerza: ADX(D1) bajo un umbral → `LATERAL`.
  - Eje de volatilidad: ATR(D1)/cierre (ATR%) comparado con sus percentiles **calculados en ventana expandida, solo con el pasado** → `BAJA`, `NORMAL`, `ALTA`.
  - Etiqueta = combinación (p. ej., `ALCISTA_NORMAL`), es decir, 9 clases como máximo.
- **Parámetros que el propietario fija:** tipo y periodo de la media, ventana de pendiente, umbral de ADX (si se usa), periodo del ATR y percentiles de corte.
- **Ventajas:** simple, interpretable, determinista, barata y fácil de probar sin look-ahead.
- **Inconvenientes:** si usa EMA200/ADX coincide con el piloto (redundancia, §1); los umbrales fijos son arbitrarios; 9 clases fragmentan una muestra ya pequeña (≥ 100 trades en Train+Val, P15).

### Alternativa B — Solo volatilidad en D1

- **Definición operacional (referencia):** volatilidad realizada (desviación de retornos logarítmicos D1 en N días) o ATR%, clasificada en `BAJA`, `NORMAL` y `ALTA` por percentiles de ventana expandida (solo pasado).
- **Ventajas:** es **ortogonal** al piloto (que ya filtra la tendencia), tiene solo 3 clases y la volatilidad es la variable con más persistencia y evidencia de utilidad para el riesgo y el tamaño del stop.
- **Inconvenientes:** no describe la dirección; la síntesis la obtiene del Market Analyst y de la propia estrategia.

### Alternativa C — Modelo estadístico (HMM o mezcla gaussiana sobre retornos y volatilidad)

- **Definición operacional:** estados latentes ajustados con datos de Train; inferencia **filtrada** (solo pasado; nunca la suavizada, que usa el futuro).
- **Ventajas:** los umbrales no son arbitrarios; la incertidumbre es natural (probabilidad de cada estado).
- **Inconvenientes:** es un **modelo ML** y queda bajo todo el régimen de FEAT-019 y DEC-005 (preregistro, hash, HUMAN_REVIEW → APPROVED, drift). Eso contradice Q44 (sin modelo entrenado en IMPL-3). Además tiene etiquetas intercambiables entre ajustes, depende de la semilla y es más difícil de auditar. **No recomendada para IMPL-3.**

### Alternativa D — Solo mediciones, sin etiqueta (mínima)

- **Definición operacional:** el Regime Engine publica mediciones descriptivas (p. ej., ATR%, pendiente y posición respecto de una media D1), con `regime_label = UNCLASSIFIED`, hasta que exista evidencia para definir clases.
- **Ventajas:** no inventa una taxonomía; completa la cadena E2 y da contexto a la síntesis; es compatible con el piloto.
- **Inconvenientes:** no puede servir de condición de elegibilidad de estrategias hasta que se definan clases.

## 4. Criterios de transición (aplican a A y B)

- **Evaluación solo al cierre de vela D1**; entre cierres la etiqueta no cambia.
- **Histéresis:** la entrada a una clase usa un umbral y la salida otro, separados por una banda, para evitar oscilaciones en el borde.
- **Persistencia mínima:** el cambio de clase se confirma cuando la condición se mantiene durante K velas D1 cerradas consecutivas. Mientras tanto la etiqueta es `TRANSITION`, con la clase anterior y la candidata registradas.
- **Registro:** cada cambio lleva la etiqueta anterior, la nueva, las velas en el régimen y la fecha de inicio (campos previstos en CR-018 §B.2).
- **Valores K y banda:** los fija el propietario, o se fijan solo con Train según un procedimiento preregistrado.

## 5. Incertidumbre e insuficiencia de datos

- **Sin puntuación de confianza para decidir** (DEC-011). La incertidumbre se expresa así:
  - `TRANSITION` mientras no se cumple la persistencia;
  - **márgenes descriptivos** (distancia de cada medición a su umbral), solo informativos y nunca usados para ponderar;
  - `INSUFFICIENT_DATA` cuando no hay historial suficiente para el indicador más largo (p. ej., menos velas D1 cerradas que el periodo de la media) o falta la última vela D1 cerrada esperada (REQ-G-070);
  - `ERROR` estructurado ante datos inconsistentes.
- Si una estrategia exige un régimen y el régimen está en `TRANSITION`, `INSUFFICIENT_DATA` o `ERROR`, la estrategia **no es elegible** en ese ciclo (Fail-Closed, INV-012).

## 6. Método de validación propuesto (para cualquier alternativa elegida)

1. **Determinismo:** misma serie → misma etiqueta (TC-AC-07).
2. **Sin look-ahead:** prueba de truncado. La etiqueta en t calculada con la serie completa es igual a la calculada con la serie cortada en t (extensión de TC-ML-002).
3. **Ajuste solo con Train:** percentiles, umbrales e histéresis se calculan o eligen solo con `train_val` (la parte Train). No se carga `lockbox` (TC-ML-016).
4. **Estabilidad descriptiva (Train):** distribución de clases, duración media de cada régimen y transiciones por año. Criterio a preregistrar, p. ej.: ninguna clase con menos de X% del tiempo y una duración media de al menos Y días.
5. **Utilidad informativa (Train+Val, sin OOS):** el régimen debe separar algo observable hacia adelante, p. ej., la volatilidad realizada de las N velas siguientes difiere entre clases (prueba preregistrada). Si no separa nada, el régimen se queda en contexto descriptivo (alternativa D).
6. **Si se usa como filtro de una estrategia:** entra en el preregistro de esa estrategia y se valida con ella (Walk-Forward, OOS y LOCKBOX únicos); nunca se ajusta tras ver el OOS (REQ-G-103).

## 7. Recomendación del Orquestador

**B (volatilidad D1) como clasificación, más las mediciones descriptivas de D**, con histéresis y persistencia (§4) y la validación de §6. Uso en v1: **solo contexto** (respuesta 1a). Si el piloto preregistrado quiere usar el régimen como filtro, se decide en su preregistro.

Motivos: no duplica el filtro de tendencia del piloto, tiene 3 clases (no fragmenta la muestra), no es un modelo ML (respeta Q44) y es auditable.

## 8. Lo que el propietario debe aprobar explícitamente

- Alternativa (A, B, C, D o combinación) y uso en v1 (contexto, elegibilidad o ambos).
- Temporalidad de cálculo.
- Indicadores y periodos.
- Umbrales o procedimiento de fijación con Train; histéresis (banda) y persistencia (K).
- Criterios de estabilidad y de utilidad del §6.

Hasta esa aprobación, FEAT-018 solo puede avanzar en la parte que no depende de la clasificación: esquema del evento (tras CR-018), `INSUFFICIENT_DATA`/`ERROR` y la cadena E2, con `regime_label = UNCLASSIFIED`.
