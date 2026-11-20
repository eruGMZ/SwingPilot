# DEC-017 — Plan de IMPL-3 «Integración cuantitativa» (Q41–Q47)

**Fecha:** 2026-11-20
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensaje del propietario en la sesión del 2026-11-20 («Apruebo la planificación de IMPL-3 con las siguientes decisiones del propietario»), en respuesta a las preguntas Q41–Q47 de `feature_list.json` → `impl3_plan`.
**Alcance:** Aprueba la planificación de IMPL-3 y registra las decisiones Q41–Q47. NO aprueba CR-018 (solo su elaboración), NO decide Q42, NO modifica el contrato v1.5 y NO autoriza la implementación de los componentes que dependen de CR-018 o de Q42.

---

## Decisiones

| Pregunta | Tema | Decisión |
|---|---|---|
| Q41 | Captura en vivo (FEAT-016) | **APROBADA.** Implementar y probar en IMPL-3 la captura por WebSocket de Binance, solo con velas cerradas y recuperación de las velas faltantes al reconectar. Sin credenciales privadas ni operaciones. La puesta en marcha continua en Laptop B se difiere a IMPL-5. |
| Q42 | Regime Engine (FEAT-018) | **PENDIENTE DE DECISIÓN.** No inventar clases, indicadores, umbrales ni metodología. El Orquestador presenta alternativas cuantitativas, definiciones operacionales, criterios de transición, tratamiento de la incertidumbre y método de validación. Se espera aprobación explícita antes de implementar la clasificación. |
| Q43 | Estrategia inicial (FEAT-017/020) | **APROBADA.** Primer piloto preregistrado: **Trend Following H4**, con EXP-0001 como antecedente: EMA200, ADX14 > 25 y trailing stop basado en ATR. Los parámetros son hipótesis de investigación, no configuración aprobada para producción. **Mean Reversion H1 permanece rechazada.** IMPL-3 no requiere una estrategia APPROVED para cerrar; sin estrategia aprobada el sistema produce `NO_SETUP`. |
| Q44 | ML Engine (FEAT-019) | **APROBADO.** Solo infraestructura de versionado, trazabilidad, promoción y degradación. Sin modelo entrenado ni inferencias productivas. |
| Q45 | CR-018 | **APROBADA PARA ELABORACIÓN.** CR-018 con los contratos de REGIME_CLASSIFIED, ML_INFERENCE_COMPLETED, STRATEGY_CANDIDATE, señal de salida y motivos estructurados de NO_SETUP, con trazabilidad, correlación, versionado, timestamps, errores e insuficiencia de datos. Debe aprobarse antes de implementar los componentes que dependan de esos contratos. El contrato vigente no se modifica sin CR aprobada. |
| Q46 | Snapshots (FEAT-015) | **APROBADA.** Parquet fuera de Git. En el repositorio se guardan manifiestos, metadatos y hashes SHA-256 para la reproducibilidad. LOCKBOX permanece bloqueado. |
| Q47 | Presupuesto de IA (FEAT-022) | **APROBADO CON CONDICIONES.** Límite incremental de USD 0.50 para las llamadas experimentales de IA de IMPL-3: aviso a USD 0.40, bloqueo a USD 0.50, reserva atómica que incluya reintentos y llamadas paralelas. No se consume presupuesto automáticamente. Las pruebas cuantitativas y de integración se ejecutan localmente cuando sea posible. |

## Condiciones generales

1. Se mantienen los modelos aprobados (DEC-009, DEC-016) y la arquitectura de autoridad (architecture.md §6).
2. No se habilitan operaciones reales, endpoints privados de Binance ni ejecución de órdenes.
3. G5, G6 y G7 siguen en PENDING hasta demostrar sus criterios.
4. Ninguna FEAT pasa a DONE sin evidencia, revisión independiente y la aprobación correspondiente.
5. No se inicia el código de los motores que dependen de CR-018 o de Q42 hasta que sus contratos estén resueltos.
6. FEAT-022 valida la integración de las fases 1 a 4 sin adelantar la cadena de ejecución de IMPL-5.
7. No se hace commit ni push sin autorización.

## Observaciones del Orquestador al registrar la decisión (no modifican la decisión)

- **EXP-0001 y Mean Reversion H1 no constan en el repositorio.** Ningún archivo del Harness ni de `docs/` contiene EXP-0001 ni el rechazo de Mean Reversion H1. Se registran como declaración del propietario. Para preregistrar el piloto hace falta la documentación de EXP-0001: periodo y datos usados, parámetros (incluido el multiplicador del ATR) y resultados. Motivo: (a) si EXP-0001 usó datos que caen en el OOS o el LOCKBOX de la nueva snapshot, esas particiones ya no están limpias para esta hipótesis y hay que declararlo (REQ-G-101, REQ-G-102); (b) la corrección por número de experimentos (REQ-G-P17) debe contar EXP-0001 y Mean Reversion H1. Queda **PENDING** hasta que el propietario lo aporte.
- **Parámetros del piloto no fijados:** multiplicador y periodo del ATR del trailing stop, regla de salida distinta del stop (si existe), papel de D1 (contexto) y H1 (evaluación de entrada) según REQ-G-002, y la vela de entrada en el modelo de ejecución (REQ-G-109). Se fijan en el preregistro, con aprobación del propietario, antes de cualquier evaluación confirmatoria.
