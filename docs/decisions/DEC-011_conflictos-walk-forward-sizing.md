# DEC-011 — Candidatos en conflicto, estructura Walk-Forward y confirmación de sizing

**Fecha:** 2026-11-19
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Mensajes del propietario en la sesión del 2026-11-19, previos a "AUTORIZO INICIO DE FASE 2": definición de resolución de señales en conflicto, estructura de validación Walk-Forward y sizing/riesgo de portfolio. Opciones y observaciones presentadas en la sesión; ver `harness/change_requests/CR-011_conflictos-walk-forward-sizing.md`.
**Alcance:** Registra las decisiones. Se aplican al contrato mediante CR-011 (contrato v1.1). NO autoriza FASE 2 ni modifica DEC-005 (P10, P15, P16, P17 siguen vigentes; esta decisión los concreta).

---

## Decisiones

| Tema | Decisión |
|---|---|
| Candidatos de entrada en conflicto | Dos o más candidatos de entrada (long) en el mismo ciclo → `NO_SETUP` (fail-closed). Sin suma de tamaños, sin elegir «el mejor», sin reducir tamaño. |
| Consenso | Confirmado: que dos familias coincidan en entrada también produce `NO_SETUP` (perfil de «cazador de divergencias»). |
| Entrada + salida simultáneas | La señal de salida tiene prioridad; si queda un candidato de entrada válido, se re-evalúa en el siguiente ciclo. |
| «Confianza» en estrategias no-ML | No se usa. La regla es binaria (candidato sí/no), no ponderada. |
| Autorización | Solo las entradas requieren autorización humana. Los cierres protectores y las salidas por señal de estrategia son autónomos. Contrato sin cambios respecto a DEC-008 Q25. |
| Embargo Walk-Forward | 2 meses, **interpretación A**: entre el fin del entrenamiento y el inicio de la prueba de cada ventana (24 m entrenamiento → 2 m embargo → 6 m prueba; paso 6 m). |
| Estructura de validación | El Walk-Forward opera **dentro de Train+Val**. OOS = evaluación final única. LOCKBOX = una sola vez al final. |
| Mínimo de ventanas | 2 ventanas de prueba del Walk-Forward (dentro de Train+Val). |
| Mínimo de 30 trades OOS | Sobre el agregado, no por ventana. |
| Preregistro | Congela longitud de entrenamiento, de prueba, embargo, step size, frecuencia de roll y número de ventanas antes de cualquier evaluación OOS. |
| Histórico mínimo | Se calcula con la tasa real de trades observada en el backtest piloto (estimada solo con datos de Train), no solo con el máximo teórico de 8/mes. Si no alcanza para 2 ventanas WF + OOS + LOCKBOX, se documenta la limitación y se propone un ajuste (decisión del propietario). |
| Sizing y riesgo de portfolio | Con el perfil aprobado (1 posición, long-only, 1 activo) no se requiere extensión de sizing. |
| minNotional / minQty / stepSize | No se ajusta el presupuesto de riesgo; se rechaza y se documenta el riesgo efectivo real y el que habría exigido el mínimo del exchange. |
| MONTHLY_DRAWDOWN_LOCK | Sin cambio: bloquea entradas y no cierra la posición abierta; su pérdida está acotada por el stop en Binance (CR-002) e INV-001. |

## Justificación registrada

- **Candidatos:** con una posición única y long-only, sumar tamaños o ponderar por confianza no es posible (INV-003, prohibición de sizing discrecional). La resolución determinista en el Strategy Engine mantiene a Decision Synthesis (LLM) fuera de la elección entre candidatos.
- **Embargo (interpretación A):** con ventana móvil 24/6 y paso 6, el entrenamiento k+1 incluye la prueba k; un hueco literal «entre test y siguiente train» sería incompatible con DEC-005 P16.
- **Autorización de cierres:** exigir una respuesta humana (vigencia de 30 min, DEC-008 Q24) a un cierre protector debilitaría la protección; el propietario confirmó que fue un error de redacción y que el contrato no cambia.
- **Histórico mínimo:** el máximo de 8 operaciones/mes es un tope, no una tasa esperada; la tasa real determina si los mínimos de DEC-005 P15 son alcanzables.

## Pendiente no cubierto por esta decisión

- Tipo de orden del stop en Binance (stop-limit vs OCO): sigue `PENDING` de FASE 2 (REQ-G-031).
- Esquema del evento de «señal de salida» del Strategy Engine: `PENDING`, se define al implementar en FASE 2.
