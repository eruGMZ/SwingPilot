# DEC-008 — Estados de la operación, vigencia de la autorización y cierre protector

**Fecha:** 2026-11-18
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Revisión de un documento externo de feedback (`error-handling.md`, "Manejo de Fallos y Recuperación"), comparado con el contrato técnico (REQ-G-031..036, DEC-004, DEC-006 P26, DEC-007). Preguntas Q23–Q25; opciones y recomendaciones presentadas en la sesión.
**Alcance:** Registra las decisiones. Los cambios al contrato técnico que derivan de ellas se tramitan en CR-005. NO constituye aprobación de G3 ni autoriza FASE 2. El documento externo no se incorpora a `docs/` ni tiene autoridad documental.

---

## Decisiones

| Pregunta | Tema | Decisión |
|---|---|---|
| Q23 | Máquina de estados de la operación en el contrato | **Opción A:** CR-005 completa. El contrato define los estados de una operación, sus transiciones permitidas y la acción de recuperación por estado al arrancar. El esquema concreto de almacenamiento (p. ej. `state.db`) queda como referencia de diseño para FASE 2. |
| Q24 | Vigencia de la autorización humana (`valid_until_utc`) | **30 minutos** desde el envío de la solicitud por Telegram. El propietario estaba entre 15 y 60 min; se eligió el punto intermedio. |
| Q25 | Precio ya cruzó el stop y no existe orden protectora en Binance | **Opción A:** cierre a mercado automático, aviso por Telegram y bloqueo de nuevas entradas hasta revisión del propietario. |

## Justificación registrada

- **Q23:** sin estados definidos, REQ-G-032 ("ninguna acción externa sin estado persistido") no es verificable; la conducta tras una caída es una decisión de riesgo que debe aprobar el propietario antes del código, no el implementador.
- **Q24:** en swing H4, 30 min de diferencia en la entrada no altera la estrategia; el precio queda protegido por la tolerancia de 0.5% al ejecutar (P20, DEC-004). Una vigencia más larga deja envejecer el análisis (contexto macro, noticias) sin que la tolerancia de precio lo detecte. Vencer sin respuesta equivale a no operar (Fail-Closed).
- **Q25:** el stop forma parte de la operación ya autorizada (INV-007); esperar con el precio bajo el stop puede llevar la pérdida más allá del 1.5% (INV-001). En Spot long-only sin apalancamiento, vender solo cierra la posición existente; no abre exposición nueva. Coherente con `data_flow.md` §2 ("Stop alcanzado sin ejecución en Binance → ORDER_SUBMITTED (SELL)").

## Condiciones

- **Q24:** el propietario indicó que casi siempre está atento al celular y que puede apoyarse en un agente propio de análisis visual de gráficos. Ese agente es una herramienta personal del propietario: **no forma parte de SwingPilot**, no se integra al sistema y nunca puede aprobar operaciones (INV-008). Integrarlo requeriría un CR nuevo.
- **Q24:** el valor puede ajustarse más adelante solo mediante una decisión registrada (DEC), con base en los tiempos de respuesta medidos en el modo de prueba de FASE 2 (propuesto en CR-005).
- **Q25:** el cierre protector no requiere nueva autorización, igual que reponer un stop. Abrir cualquier posición nueva sigue requiriendo autorización individual (INV-008).

## Puntos del documento externo NO adoptados

Registrados en CR-005 §F con su motivo (contradicen REQ-G-031, REQ-G-032, REQ-G-034, REQ-G-035, P19, P18 o INV-008).
