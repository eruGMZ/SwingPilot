# DEC-006 — Parámetros operativos, bloque 3

**Fecha:** 2026-11-17
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Sesión de validación técnica en FASE 1 (respuestas del propietario Q14–Q17). Opciones y recomendaciones presentadas en la sesión; el propietario aceptó la recomendación en todas.
**Alcance:** Resuelve P07, P18, P25 y el nuevo P26 de `implementation/requirements.md`. NO constituye aprobación de G3 ni autoriza FASE 2.

---

## Decisiones

| Pregunta | Parámetro | Decisión |
|---|---|---|
| Q14 | P07 Fuente BCI | API del SIE de Banxico (token gratuito). Guardar valor, fecha de publicación y serie para poder recalcular. Pendiente con el contador (P08): si el tipo correcto es el FIX y qué tipo usar en días sin publicación. |
| Q15 | P18 Tiempos, límites y disponibilidad de API de IA | Tope de gasto de $5 USD/mes. La IA solo se invoca al cierre de vela H4 cuando los filtros deterministas detectan un posible setup. Timeout de 60 s por llamada; ciclo completo ≤ 5 min; si se excede, Fail-Closed. Sin SLA 24/7: una caída equivale a no operar. El gasto en API se descuenta del resultado neto en reportes. |
| Q16 | P25 Formato de la matriz de trazabilidad | JSON en el repositorio, con esquema y script de validación. |
| Q17 | P26 Recuperación ante fallos | Al reiniciar: reconciliar con Binance, entrar en modo seguro sin nuevas órdenes, avisar por Telegram y esperar confirmación del propietario para reanudar. Adición elegida: stop-loss colocado también en Binance al abrir cada posición (ver CR-002). |

## Notas

- Justificación de P18: con riesgo de $45 MXN por operación y expectancy mínimo de 0.10 R, la ganancia esperada es de ~$36 MXN/mes (~$2 USD). El tope de $5 USD se acepta como costo de validación del sistema, no como operación rentable desde el inicio.
- El stop-loss en Binance modifica el flujo de ejecución del contrato (`data_flow.md`, monitoreo de stop en software). Se tramita como CR-002; el contrato no se modifica hasta su aprobación formal.
- Con este bloque, todos los parámetros PENDING del Módulo 15 quedan resueltos excepto P08 (diferido por el propietario).
