# CR-011 — Candidatos en conflicto, Walk-Forward (embargo, ventanas OOS, histórico mínimo) y confirmación de sizing

**Fecha:** 2026-11-19
**Estado:** APROBADA por el propietario el 2026-11-19 y APLICADA (contrato v1.1; DEC-011). Las aclaraciones abiertas se resolvieron el mismo día.
**Origen:** solicitud del propietario (sesión 2026-11-19, previa a "AUTORIZO INICIO DE FASE 2") de definir tres puntos implícitos o ausentes. Los valores de las secciones A y B provienen textualmente del propietario; no se han inventado valores.
**Procedimiento previsto (precedente CR-006/DEC-009):** tras la aprobación se registra DEC-011 con los valores del propietario, se aplican los cambios a los documentos listados, el contrato pasa a v1.1 y se registra en `progress.md`.

---

## A. Candidatos en conflicto (Strategy Engine, Fase 2)

### Hechos vigentes (sin cambio)
- Long-only, una posición global, sin Short (INV-003, INV-005). Una señal "SELL" solo puede significar **salida de una posición abierta**, nunca una venta en corto.
- El sizing no depende de la confianza (RISK_POLICY §Prohibición de sizing discrecional).
- Sin candidato → `NO_SETUP`, fin de ciclo, sin llamadas a LLM (REQ-G-071, CR-004).

### Cambio propuesto (valores del propietario)
1. **La resolución es determinista y ocurre en el Strategy Engine**, antes de Decision Synthesis. Decision Synthesis no resuelve conflictos entre candidatos ni modifica el tamaño.
2. **Regla binaria.** Cada estrategia produce candidato sí/no. No se usa puntuación de confianza para decidir ni para ponderar, en ninguna familia (incluida ML-Based).
3. **Dos o más candidatos de entrada (long) en el mismo ciclo (mismo `correlation_id`) → `NO_SETUP` (fail-closed).** No se suman tamaños, no se elige el "mejor" y no se reduce tamaño.
4. **Candidato de entrada + señal de salida simultáneas → prevalece la salida.** Se procesa primero la salida; si tras ella queda un candidato de entrada válido, se re-evalúa en el **siguiente ciclo** (no se ejecuta en el mismo).
5. El `NO_SETUP` por conflicto registra los candidatos descartados y el motivo (trazabilidad).

### Decisiones del propietario (2026-11-19)
- **Consenso ⇒ NO_SETUP: confirmado.** Que dos familias coincidan en entrada produce `NO_SETUP`, igual que si discreparan (perfil de "cazador de divergencias").
- **Salida por señal de estrategia: autónoma, sin autorización humana.** Se ejecuta sin solicitud por Telegram. Las entradas siguen requiriendo autorización individual (INV-008). Ver la aclaración abierta 1 sobre los cierres protectores.
- Con una posición abierta, un candidato de entrada ya queda bloqueado por INV-003; la regla 4 aplica a la señal de salida del mismo ciclo.

**Afecta:** `requirements.md` (REQ-G-071, REQ-G-072), `data_flow.md` (Fase 2), `api_contracts.md` (motivo de `NO_SETUP`), `test_plan.md` (pruebas nuevas: 2 candidatos long, entrada+salida, un solo candidato, sin candidatos; numeración a asignar).

---

## B. Walk-Forward y validación

### Hechos vigentes (sin cambio, DEC-005)
Ventana móvil 24 m entrenamiento / 6 m prueba / paso 6 m; división cronológica 50/20/15/15 (Train/Val/OOS/LOCKBOX); ≥100 trades en Train+Val, ≥30 en OOS y ≥30 en LOCKBOX; IC bootstrap 95% > 0, línea base ingenua y corrección por nº de experimentos; preregistro congelado antes de la evaluación confirmatoria (REQ-G-103).

### Cambio propuesto (valores del propietario)
1. **Embargo: 2 meses** entre test y entrenamiento.
   - **Colocación (interpretación A, confirmada por el propietario):** hueco de 2 meses **entre el fin del entrenamiento y el inicio de la prueba de cada ventana** (entrenamiento 24 m → embargo 2 m → prueba 6 m; paso 6 m). El texto original ("entre test y siguiente train") no era compatible con DEC-005 P16, porque con paso 6 el entrenamiento k+1 incluye la prueba k.
   - El embargo debe ser ≥ el horizonte máximo de las etiquetas (REQ de etiquetas, PROFILE §Etiquetas); si el horizonte supera 2 meses, el preregistro lo declara y el experimento no puede usar ese horizonte con embargo de 2 meses.
2. **Estructura de validación (decisión del propietario).** El Walk-Forward opera **dentro de Train+Val** (70% del histórico). **OOS (15%) es una evaluación final única** y **LOCKBOX (15%) se usa una sola vez al final**. El mínimo de 30 trades en OOS se evalúa sobre el **agregado**, no por ventana.
   - **Mínimo de ventanas: 2 ventanas de prueba del Walk-Forward** (dentro de Train+Val), no 2 ventanas OOS. Motivo: al ser el OOS una evaluación única, la formulación anterior "2 ventanas OOS" quedaba sin sentido. Cada ventana debe cumplir el criterio de estabilidad que fije el preregistro; el criterio de aceptación estadístico de DEC-005 P17 se aplica en el OOS final.
   - Ver la aclaración abierta 2 sobre esta reformulación.
3. **El preregistro congela** longitud de entrenamiento, longitud de prueba, embargo, step size, frecuencia de roll y número de ventanas, antes de cualquier evaluación OOS. Cambiarlos tras ver resultados OOS es una desviación documentada y el experimento deja de ser confirmatorio (REQ-G-103). El conteo del preregistro alimenta la corrección por experimentos (DEC-005 P17).
4. **Histórico mínimo requerido:** cada preregistro calcula y documenta el histórico mínimo necesario para cumplir los mínimos de trades en **todas** las particiones y ventanas, con la tasa de trades observada o estimada del experimento. Si el histórico disponible es menor, el experimento no pasa de DESIGN (no se relajan los mínimos).
   - Cotas de referencia derivadas del contrato (no sustituyen el cálculo del preregistro): el máximo es 8 operaciones/mes (REQ-G-004), por lo que ≥100 trades en Train+Val requieren **≥12.5 meses** aun a la tasa máxima, y ≥30 en OOS o LOCKBOX **≥3.75 meses** cada uno. La tasa real será menor; meses = N_trades_mínimo / tasa_mensual.
   - **Tasa real, no solo el máximo teórico (decisión del propietario).** El cálculo usa la tasa de trades observada en el **backtest piloto**. Si con esa tasa no se alcanzan **2 ventanas de prueba WF + OOS + LOCKBOX** con sus mínimos, el preregistro documenta la limitación y propone un ajuste (más histórico, otra temporalidad o ventanas más cortas); el ajuste es una decisión del propietario y no relaja por sí mismo los mínimos de DEC-005.
   - **Cautela de leakage:** la tasa del piloto debe estimarse solo con datos de la partición Train; el piloto no puede mirar OOS ni LOCKBOX.
   - **Fórmula de referencia** (partición cronológica por tiempo, tasa `r` trades/mes): con 2 ventanas WF y la interpretación A, la región WF exige 24 + 2 + 6 + 6 = **38 meses**, que es el 70% del histórico, es decir ≥ 54.3 meses. Entonces `H_min = max( 38/0.70 ; 100/(0.70·r) ; 30/(0.15·r) )` meses. Para `r` ≥ ~3.7 trades/mes el mínimo es ≈ 54 meses; por debajo, domina `200/r` (OOS y LOCKBOX de ≥30 trades cada uno). Ejemplo: `r` = 2 → 100 meses. La fórmula es indicativa; el cálculo vinculante es el del preregistro.
   - **Vacío resuelto:** la combinación 50/20/15/15 con el Walk-Forward queda fijada por el propietario (WF dentro de Train+Val; OOS única; LOCKBOX única).

**Afecta:** `requirements.md` (REQ-G-103, REQ-G-106, nota de Módulo 15 P16/P17), `test_plan.md` (verificación del contenido del preregistro y del cálculo de histórico mínimo; numeración a asignar). Sin cambios en DEC-005.

---

## C. Position sizing y riesgo de portfolio

### Confirmación (sin cambio de comportamiento)
Con el perfil aprobado (1 posición, long-only, 1 activo, apalancamiento 1, BTC/USDT), **no se requiere ni se introduce** extensión de sizing: ni sizing por volatilidad (ATR), ni risk budgeting de portfolio, ni tope de exposición neta por dirección, ni kill switch de "aplanar todo". El sizing es risk-based por distancia al stop (REQ-G-015). Cualquiera de esas extensiones requeriría antes ampliar el perfil (activos, posiciones, margin), lo que exige autorización expresa del propietario y un CR nuevo.

### Cambio propuesto (valor del propietario)
Si `minNotional` / `minQty` / `stepSize` del par impiden ejecutar el 1.5% como tal:
1. **No se ajusta el presupuesto** (REQ-G-015 y RISK_POLICY ya lo prohíben; INV-001). La operación se rechaza antes de enviarse.
2. El rechazo **registra**: presupuesto de riesgo (1.5% del equity actual), cantidad y riesgo efectivo calculados tras redondeo, la cantidad y el riesgo que habría exigido el mínimo del exchange, y el filtro que lo impidió.
3. Si, tras redondear hacia abajo a `stepSize`, el riesgo efectivo es menor que el presupuesto (pero ≤ presupuesto), se acepta y se registra el riesgo efectivo real.
4. Aumentar el presupuesto para alcanzar el mínimo del exchange solo es posible por una decisión del propietario que modifique la política de riesgo; no la puede tomar ningún agente.

**Afecta:** `requirements.md` (REQ-G-015, criterios de aceptación), `test_plan.md` (prueba: rechazo con registro de riesgo efectivo; numeración a asignar).

### Aclaración sobre MONTHLY_DRAWDOWN_LOCK (documental, sin cambio de comportamiento)
La decisión vigente (RISK_POLICY §Tratamiento de posiciones abiertas) es bloquear entradas y **no** cerrar la posición abierta. La pérdida de esa posición está acotada por su stop colocado en Binance (CR-002) y por INV-001 (≤ 1.5% del equity): la pérdida mensual no puede crecer sin límite mientras haya posición, y el exceso sobre el 5% queda acotado por el riesgo restante de la posición. La cota se rompe solo si el stop falla o hay hueco de precio; para ello rigen STOP_ORDER_FAILED (CR-002) y el cierre protector a mercado (DEC-008 Q25). Esta aclaración no cambia la política; si el propietario desea que el lock cierre la posición, es un cambio de política de riesgo y se tramita aparte.

---

## Impacto
- **Arquitectónico:** bajo. Concreta una regla en el Strategy Engine y añade contenido obligatorio al preregistro; no añade componentes.
- **Riesgo:** reduce ambigüedad; ninguna regla amplía exposición ni toca los límites de RISK_POLICY.
- **Pruebas:** nuevas pruebas en `test_plan.md` (A, B, C) y cobertura de aceptación en `feature_list.json` en FASE 2.
- **FASE 2:** sin efecto hasta la aprobación del CR y la autorización de FASE 2.

## Decisiones resueltas por el propietario (2026-11-19)
Embargo: interpretación A. Consenso ⇒ NO_SETUP: confirmado. Salida por estrategia: autónoma. WF dentro de Train+Val; OOS y LOCKBOX de evaluación única. 30 trades OOS: agregado. Histórico mínimo con tasa real del backtest piloto.

## Aclaraciones resueltas (2026-11-19)
1. **Cierres protectores:** (a) error de redacción. Solo las entradas requieren autorización; los cierres protectores y las salidas por señal de estrategia son autónomos. Contrato sin cambios respecto a DEC-008 Q25 / RISK_POLICY.
2. **«2 ventanas OOS» → «2 ventanas de prueba WF»:** reformulación confirmada.

## Aprobación y aplicación
Aprobada por el propietario el 2026-11-19 ("Aprobado con estos valores"; aclaraciones 1 y 2 confirmadas; "Aplica el CR-011, registra DEC-011, actualiza a contrato v1.1"). Aplicada en: `docs/decisions/DEC-011_conflictos-walk-forward-sizing.md` (nuevo); `requirements.md` (REQ-G-071, REQ-G-015, REQ-G-103, REQ-G-106, nota de REQ-G-P16); `data_flow.md` (Fase 2 y ciclo de vida de posición); `api_contracts.md` (NO_SETUP); `test_plan.md` (TC-FLOW-004..008, TC-PS-005..006, TC-ML-011..014); `architecture.md` (solo versión). Los cinco documentos pasan a v1.1.

Pendientes que NO cubre este CR (siguen PENDING de FASE 2): tipo de orden del stop (stop-limit vs OCO, REQ-G-031); esquema del evento de señal de salida; nombres definitivos de los motivos de `NO_SETUP`.
