# DEC-005 — Parámetros de investigación y ML, bloque 2

**Fecha:** 2026-11-17
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Sesión de validación técnica en FASE 1 (respuestas del propietario Q7–Q13). Opciones y recomendaciones presentadas en la sesión; el propietario aceptó la recomendación en todas.
**Alcance:** Resuelve P10–P17 y P21–P24 de `implementation/requirements.md`. NO constituye aprobación de G3 ni autoriza FASE 2.
**Congelamiento:** estos criterios se fijan antes de cualquier experimento. Modificarlos después de observar resultados está prohibido; cualquier cambio requiere change request.

---

## Decisiones

| Pregunta | Parámetro | Decisión |
|---|---|---|
| Q7 | P10 División de datos | Cronológica: Train 50% / Validation 20% / OOS 15% / LOCKBOX 15%. Cada partición de evaluación debe alcanzar el mínimo de P15. |
| Q8 | P15 Tamaño mínimo de muestra | ≥ 100 trades en Train+Validation; ≥ 30 trades en OOS y ≥ 30 en LOCKBOX. |
| Q9 | P11 Rentabilidad mínima | Sharpe OOS ≥ 0.8, neto de comisión y slippage (DEC-004). Comparación contra comprar y mantener BTC: reporte obligatorio, no filtro. |
| Q9 | P12 Drawdown máximo de experimentos | ≤ 20%. |
| Q9 | P13 Expectancy mínimo | ≥ 0.10 R (neto de costos), donde R = riesgo por operación. |
| Q9 | P14 Profit Factor mínimo | ≥ 1.3 (neto de costos). |
| Q10 | P16 Walk-Forward | Ventana móvil: 24 meses de entrenamiento, 6 meses de prueba, paso de 6 meses. |
| Q11 | P17 Requisitos estadísticos ML | (1) IC bootstrap 95% del expectancy en OOS completamente > 0; (2) superar una línea base ingenua; (3) corrección por número de experimentos probados (p. ej. Deflated Sharpe), usando el conteo del preregistro. |
| Q12 | P21 Reentrenamiento | Solo por degradación detectada o en revisión semestral. Nunca automático. |
| Q12 | P22 Umbrales de drift | Expectancy en vivo de los últimos 20 trades por debajo del límite inferior del IC de OOS, o PSI > 0.25 en variables de entrada. Al dispararse: modelo suspendido, no se opera (Fail-Closed). |
| Q12 | P23 Versionado y promoción | Cada modelo con hash de datos + código + parámetros. Promoción a producción solo tras HUMAN_REVIEW → APPROVED. |
| Q13 | P24 Límites adicionales del Risk Manager | **Ninguno adicional.** (La adición original —revisión tras dos meses consecutivos en drawdown de 5%— fue retirada por el propietario el 2026-11-18 por redundante; ver Notas.) |

## Notas

- Todos los umbrales se miden en OOS y netos de costos, salvo que se indique otra cosa.
- Justificación de P24: con 1.5% por operación, tres pérdidas suman ~4.4%; el presupuesto de riesgo restante bajo el 5% mensual ya bloquea una cuarta. Límites adicionales serían redundantes.
- **Aclaración (2026-11-17, detectada por el asistente tras la decisión):** la justificación de P24 omitió que el contrato ya incluye un bloqueo por 3 pérdidas consecutivas (INV-011, LOSS_STREAK_LOCK) y que el bloqueo por drawdown mensual no se libera automáticamente con el cambio de mes (REQ-G-030, criterio 9). Por tanto, la adición "revisión tras 2 meses consecutivos en DD 5%" es probablemente redundante. **Resolución (2026-11-18):** el propietario retiró la adición ("si P24 hace mucho ruido, retíralo"). P24 queda como ninguno adicional; INV-011 y REQ-G-030 (criterio 9) ya cubren el caso.
- No resuelve: P07, P18, P25 ni el procedimiento de recuperación ante fallos (bloque 3). P08 sigue diferido.
