# DEC-009 — Modelos por agente y forma de orquestación de la IA

**Fecha:** 2026-11-18
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Validación de la integración con la API de Claude (sesión del 2026-11-18), a partir de un documento de reglas de costo de sub-agentes de construcción que no cubría los agentes de SwingPilot. Precios y comportamiento de caché verificados contra la referencia oficial de la API (cache: 2026-11-03). Preguntas Q26–Q27.
**Alcance:** Registra las decisiones. Los cambios al contrato técnico se tramitan en CR-006. NO constituye aprobación de G3 ni autoriza FASE 2.

---

## Decisiones

| Pregunta | Tema | Decisión |
|---|---|---|
| Q26 | Modelo por agente | **Opción B:** Claude Haiku 5.5 (`claude-haiku-5-5`) para Market Analyst, Macro Analyst, Strategy Analyst y Risk Analyst; Claude Sonnet 5.5 (`claude-sonnet-5-5`) para Decision Synthesis. El propietario pidió "la opción que se acerque a los $5 sin problema"; B es la que da más calidad al agente que decide sin exceder el tope en un mes realista. |
| Q27 | Forma de orquestación y controles de costo | Registrar en CR-006: Messages API orquestada por código determinista (AI Orchestrator) con salida estructurada validada por esquema; sin prompt caching; reintentos del SDK alineados con REQ-G-034; límite de gasto en la consola de Anthropic como respaldo, si la cuenta lo permite. |

## Estimación de costo (supuestos a medir en FASE 2)

Supuestos: ~5 000 tokens de entrada y ~1 500 de salida por llamada (el razonamiento se cobra como salida); precios por millón de tokens: Haiku 5.5 $0.10 / $0.50; Sonnet 5.5 $2 / $10.

| Concepto | Costo |
|---|---|
| Llamada Haiku 5.5 | ~$0.00125 |
| Llamada Sonnet 5.5 | ~$0.025 |
| Ciclo con setup (3 analistas Haiku + Synthesis Sonnet) | ~$0.029 |
| Risk Analyst (Haiku, solo con RISK_APPROVED) | ~$0.00125 |
| Peor caso teórico: setup en las 180 velas H4 del mes | ~$5.4 → el tope de $5 (REQ-G-034) corta las llamadas |
| 30–60 ciclos con setup al mes | ~$0.9–$1.8 |

Opciones descartadas: A (Haiku en los 5; ~$1 en el peor caso, menos calidad en la síntesis) y C (Sonnet en los 5; ~40 ciclos con setup agotan el tope).

## Condiciones

- Los valores de tokens son supuestos; el modo de prueba de FASE 2 mide el costo real por ciclo y la calidad de las propuestas.
- Cambiar el modelo de un agente requiere una nueva DEC.
- Si Haiku resulta insuficiente en algún analista, o Sonnet en Decision Synthesis excede el presupuesto, se revisa con datos medidos.
