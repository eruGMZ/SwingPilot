# SwingPilot — Requirements Contract v1.13

**Producido por:** MERGER — FASE 1  
**Fecha:** 2026-11-13  
**Estado:** v1.13 (CR-025, aprobada por el propietario el 2026-11-26: integridad autoritativa continua; V9 en ET-9 y ET-10 con la ligadura `approval_binding` persistida en la evidencia de APPROVED; REQ-G-104 y REQ-G-P23 modificados; ET-10 en el Strategy Engine diferido a B9) — v1.12 (CR-024, aprobada por el propietario el 2026-11-26: persistencia autoritativa de resultados OOS y LOCKBOX y `evaluation_hash`; REQ-G-104, REQ-G-106, REQ-G-109 y REQ-G-P23 modificados) — v1.11 (CR-023, DEC-025, 2026-11-25: particiones de evaluación prospectivas y frontera de independencia verificable; REQ-G-101, REQ-G-103, REQ-G-104, REQ-G-106, REQ-G-109, REQ-G-P10, REQ-G-P15 y REQ-G-P23 modificados) — v1.10 (CR-022, DEC-024, 2026-11-24: la influencia de una prueba posterior se acredita solo con la cita del par exacto; REQ-G-P17 ampliado) — v1.9 (CR-021, DEC-023, 2026-11-24: durabilidad confirmada como condición de acceso a datos; REQ-G-104 y REQ-G-P17 ampliados) — v1.8 (CR-020, DEC-021, 2026-11-24: contabilidad de pruebas de REQ-G-P17; REQ-G-103 y REQ-G-104 ampliados) — v1.7 (CR-019, DEC-020, 2026-11-20: evento PROPOSAL_NORMALIZATION_REJECTED) — v1.6 (CR-018, DEC-019) — v1.5 — v1.0 APROBADO por el propietario (G3, 2026-11-18: "APRUEBO EL CONTRATO TÉCNICO v1.0"); v1.1 aplicó CR-011 (DEC-011); v1.2 aplicó CR-012 (DEC-012); v1.3 aplicó CR-013 (DEC-013); v1.4 aplicó CR-015 (DEC-014) y v1.5 aplica CR-016 (DEC-015), todas aprobadas el 2026-11-19; incorpora CR-001..CR-013, CR-015 y CR-016. Cambios posteriores solo mediante solicitud de cambio aprobada y versionado  
**Autoridad documental aplicada:** DEC-001 (resoluciones de conflictos CONF-001, CONF-002)

---

## Notas del Merger

Este documento consolida los 224 requisitos (G1) extraídos de 6 documentos fuente (DOC-001..DOC-006) en requisitos globales con identificadores REQ-G-NNN. Se aplicaron las siguientes reglas:

1. Los requisitos idénticos o altamente solapados entre documentos se fusionan en un único REQ-G-NNN con todas las fuentes listadas.
2. Los requisitos PENDING conservan su estado; ningún valor se inventa.
3. Los parámetros aprobados operativamente por DEC-001 están marcados como `[APPROVED-DEC-001]`.
4. Los conflictos detectados durante el merge se registran al final del documento y en `conflict_register.md`.

**Nota sobre riesgo:** el límite es **1.5% máximo vinculante** (no un rango). La referencia "1–2%" de DOC-003 es incorrecta y se ignora (DEC-002 §2, CONF-004 RESUELTA).

---

## Módulo 1: Perfil Operativo y Restricciones de Instrumento

### REQ-G-001
**Descripción:** El sistema opera exclusivamente en modo Swing Trading en Binance Spot, con horizonte de 2 días a 2 semanas, dirección Long-only, instrumento BTC/USDT, sin futuros, derivados, margin ni apalancamiento.  
**Fuentes:** REQ-1002, REQ-1005, REQ-1012, REQ-1014, REQ-4001, REQ-5014, REQ-5038, REQ-5039  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema solo genera señales de compra (Long)
- El sistema solo opera sobre BTC/USDT en Binance Spot
- No existen rutas de código para futuros, perpetuos, margin ni posiciones cortas
- Las credenciales de Binance configuradas no incluyen permisos de margin ni futuros

### REQ-G-002
**Descripción:** El único exchange autorizado es Binance. Ningún otro exchange puede usarse sin autorización explícita del propietario.  
**Fuentes:** REQ-1005, REQ-4001  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema no conecta con ningún exchange distinto de Binance
- Cambiar el exchange requiere registro de autorización explícita del propietario

### REQ-G-003
**Descripción:** Las temporalidades de análisis son D1 (diario), H4 (4 horas) y H1 (1 hora) con roles diferenciados: D1=contexto de mercado, H4=estructura y señal, H1=evaluación de entrada. La selección de temporalidad para cada estrategia debe justificarse por la hipótesis experimental.  
**Fuentes:** REQ-1003, REQ-3071, REQ-4002  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema procesa datos en D1, H4 y H1
- Cada estrategia declara explícitamente su temporalidad
- No se extrapolan resultados de una temporalidad a otra sin validación

### REQ-G-004
**Descripción:** Frecuencia máxima de referencia: 8 operaciones mensuales. No es un objetivo de actividad. El sistema no genera operaciones artificiales para alcanzar una cuota. La ausencia de señales válidas es un resultado aceptable.  
**Fuentes:** REQ-1004, REQ-1020, REQ-3072, REQ-4003, REQ-5025, REQ-5037  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL (invariante INV-010)  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Al completar 8 operaciones en el mes, se bloquean nuevas entradas
- El sistema no produce señales artificiales para mantener actividad
- El sistema puede permanecer periodos sin señales sin indicar error ni degradación

### REQ-G-005
**Descripción:** Restricciones absolutas de instrumento: solo operaciones BUY y SELL sobre BTC/USDT spot. Quedan expresamente prohibidos: staking, Earn, airdrops, conversiones entre criptoactivos (swaps BTC→ETH), otras criptomonedas o pares. Los agentes no pueden incorporarlos por iniciativa propia. ETH/USDT nunca fue autorizado y queda fuera de todo alcance operativo (DEC-002 §3, CONF-005 RESUELTA).  
**Fuentes:** REQ-1012, REQ-1013, REQ-2011  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema solo ejecuta operaciones sobre BTC/USDT
- No existen operaciones sobre otros activos ni pares
- El sistema no ejecuta swaps entre criptoactivos

### REQ-G-006
**Descripción:** Restricciones absolutas de modalidad operativa: sin futuros ni contratos perpetuos; sin margin; sin apalancamiento (Leverage=1 siempre); sin posiciones short; sin copy trading; sin capital prestado. Se aplican globalmente a todos los componentes del sistema.  
**Fuentes:** REQ-1014, REQ-5014, REQ-5038, REQ-5039  
**Tipo:** CONSTRAINT (invariantes INV-004, INV-005)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existen rutas de código para margin, futuros o posiciones cortas
- El sistema rechaza cualquier operación Short

### REQ-G-007
**Descripción:** Máximo 1 posición abierta simultáneamente. La restricción es global (no por estrategia ni por agente). Una orden de entrada pendiente cuenta como exposición potencial. El sistema no puede abrir una nueva entrada mientras exista una posición pendiente de reconciliación o cierre.  
**Fuentes:** REQ-5012, REQ-5013, REQ-5037  
**Tipo:** CONSTRAINT (invariante INV-003)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema bloquea cualquier intento de abrir una segunda posición
- La verificación es global, no por estrategia
- El Risk Manager bloquea nuevas autorizaciones mientras exista una orden de entrada activa

### REQ-G-008
**Descripción:** El promediado a la baja está prohibido. No se puede aumentar la exposición de una posición que tiene pérdida flotante mediante nuevas entradas.  
**Fuentes:** REQ-5040, REQ-5001  
**Tipo:** CONSTRAINT (invariante INV-006)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema detecta posición perdedora y bloquea cualquier incremento de exposición

---

## Módulo 2: Capital, Equity y Position Sizing

### REQ-G-010
**Descripción:** Capital inicial autorizado: $3,000 MXN de origen personal. Los tickets por operación son $500–$5,000 MXN en condición habitual y hasta $10,000 MXN como máximo extraordinario. El ticket máximo no equivale a autorización de riesgo total.  
**Fuentes:** REQ-1006  
**Tipo:** DATA  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-011
**Descripción:** El sistema no puede: usar capital de WeirdCow, solicitar préstamos, usar fondos prestados, incrementar el capital disponible por iniciativa propia, ni interpretar el ticket máximo como autorización de riesgo. La asignación de capital es decisión exclusiva del operador humano.  
**Fuentes:** REQ-1007, REQ-3063, REQ-3073, REQ-4004  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existe flujo de código que modifique el capital configurado sin intervención humana
- El sistema rechaza cualquier intento de la IA de cambiar el capital

### REQ-G-012
**Descripción:** Definición dinámica del equity actual: `Equity_t = Cash_t + MarketValue_t`. Para BTC/USDT: `Equity_USDT = USDT_disponible + BTC_total * Precio_BTC`; `Equity_MXN = Equity_USDT * FX_USDT/MXN`. El equity se recalcula: antes de presentar operación para autorización, inmediatamente antes de ejecutar una orden, después de cerrar una posición, después de reconciliar con Binance, y cuando se detecten cambios relevantes en el valor de una posición abierta. No se usa equity histórico para autorizar una nueva operación.  
**Fuentes:** REQ-5004  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Dependencias:** REQ-G-010  
**Criterios de aceptación:**
- El equity se recalcula antes de cada autorización y ejecución
- La fórmula `Equity_t = Cash_t + MarketValue_t` está implementada
- La conversión USDT/MXN usa una fuente configurada y vigente
**RESUELTO — ver Módulo 15 (DEC-004):** fuente de conversión USDT/MXN (REQ-G-P01); antigüedad máxima del tipo de cambio (REQ-G-P02).

### REQ-G-013
**Descripción:** Presupuesto de riesgo por operación: `RiskBudget_t = Equity_t × 0.015`. El presupuesto se actualiza dinámicamente; no es fijo en $45 MXN. Si el equity disminuye, el presupuesto disminuye proporcionalmente.  
**Fuentes:** REQ-1008, REQ-5005, REQ-5006, REQ-5035  
**Tipo:** RISK_MANAGEMENT (invariante INV-001)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Dependencias:** REQ-G-012  
**Criterios de aceptación:**
- `RiskBudget_t = Equity_t × 0.015` implementado
- El presupuesto disminuye cuando el equity disminuye
- El sistema nunca ejecuta una operación donde `RiskEffective > RiskBudget_t`

### REQ-G-014
**Descripción:** El riesgo efectivo incluye todos los costes: `RiskEffective = PriceRisk + Fees + Slippage + OtherCosts`. La condición `RiskEffective <= RiskBudget_t` es obligatoria. Los costes no pueden contabilizarse fuera del límite del 1.5%.  
**Fuentes:** REQ-5007  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Dependencias:** REQ-G-013  
**Criterios de aceptación:**
- El sistema rechaza o reduce cualquier operación donde `RiskEffective > RiskBudget_t`
- Las comisiones y slippage son parte obligatoria del cálculo del riesgo efectivo
- El sistema bloquea entrada si no puede estimar costes razonablemente

### REQ-G-015
**Descripción:** Fórmula de position sizing para posición Long: `Q = (RiskBudget - FixedCosts) / ((P_e - P_s) + C_e + C_s + S)`. El sizing no se determina exclusivamente por el capital disponible. Después de calcular Q: redondear hacia abajo según stepSize del mercado; respetar minQty y minNotional; recalcular riesgo efectivo después del redondeo; rechazar si el mínimo de Binance excede el presupuesto. No se aumenta el presupuesto para satisfacer mínimos del exchange. **CR-011 (DEC-011):** el rechazo por minNotional/minQty/stepSize registra el presupuesto de riesgo (1.5% del equity actual), la cantidad y el riesgo efectivo calculados tras el redondeo, la cantidad y el riesgo que habría exigido el mínimo del exchange y el filtro que lo impidió; si tras redondear hacia abajo el riesgo efectivo es ≤ presupuesto se acepta y se registra el riesgo efectivo real. Solo el propietario puede cambiar el presupuesto (política de riesgo). Con el perfil aprobado (1 posición, long-only, 1 activo) no se requiere extensión de sizing (ni ATR, ni risk budgeting de portfolio, ni tope de exposición neta, ni kill switch de aplanar todo).  
**Fuentes:** REQ-5008, REQ-5009, REQ-1022; CR-011  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Dependencias:** REQ-G-013, REQ-G-014  
**Criterios de aceptación:**
- La fórmula está implementada
- La cantidad resultante siempre cumple `RiskEffective <= RiskBudget_t` incluso después del redondeo
- El sistema rechaza operaciones donde el mínimo de Binance excede el presupuesto
**RESUELTO — ver Módulo 15 (DEC-004):** comisión efectiva de Binance (REQ-G-P03); reserva de slippage (REQ-G-P04); stepSize/minQty/minNotional (REQ-G-P05).

### REQ-G-016
**Descripción:** El position sizing es estrictamente determinista y reproducible. Ningún agente puede incrementar la cantidad calculada por razones discrecionales: mayor confianza en la señal, alta probabilidad de éxito, oportunidad excepcional, recuperación de pérdidas anteriores, objetivo mensual, recomendación de otro agente.  
**Fuentes:** REQ-5010  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existe ninguna ruta en el sistema que permita incrementar Q por razones discrecionales

---

## Módulo 3: Risk Manager — Estados y Control de Drawdown

### REQ-G-020
**Descripción:** Drawdown mensual máximo: 5% del equity de referencia mensual. El límite del 5% sustituye explícitamente cualquier referencia anterior al 6%. El cálculo incluye pérdidas realizadas y no realizadas: `MonthlyDrawdown = (MonthlyBaseline - CurrentEquity) / MonthlyBaseline × 100`.  
**Fuentes:** REQ-1009, REQ-1021, REQ-1022, REQ-5016, REQ-5017, REQ-5018, REQ-5036  
**Tipo:** RISK_MANAGEMENT (invariante INV-002)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Dependencias:** REQ-G-012

### REQ-G-021
**Descripción:** El equity de referencia mensual (MonthlyBaseline) se congela al inicio de cada mes calendario. Para el primer periodo, la referencia inicial es $3,000 MXN si ese es el equity efectivo al iniciar la operativa.  
**Fuentes:** REQ-5017  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-022
**Descripción:** Al alcanzar `MonthlyDrawdown >= 5%`, el sistema ejecuta en este orden: (1) suspender nuevas operaciones, (2) cancelar órdenes de entrada pendientes, (3) mantener mecanismos de salida de posiciones abiertas activos, (4) registrar el evento de bloqueo, (5) solicitar revisión y autorización humana. El bloqueo NO se libera automáticamente. El cambio de mes NO libera ningún bloqueo activo.  
**Fuentes:** REQ-1010, REQ-5019, REQ-5020, REQ-5021  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Las 5 acciones se ejecutan al alcanzar `MonthlyDrawdown >= 5%`
- El bloqueo no se libera automáticamente
- Al inicio de un nuevo mes, los bloqueos activos permanecen hasta autorización humana explícita

### REQ-G-023
**Descripción:** Tres pérdidas consecutivas activan suspensión preventiva (LOSS_STREAK_LOCK). Una operación es perdedora si su resultado neto realizado es negativo después de comisiones. El contador se reinicia con una operación ganadora neta. Un resultado exactamente cero no incrementa ni reinicia el contador. La liberación requiere: revisión humana, verificación de estado de estrategia, revisión de eventos de ejecución y autorización humana explícita. El tiempo transcurrido no libera el bloqueo.  
**Fuentes:** REQ-5022, REQ-5038  
**Tipo:** RISK_MANAGEMENT (invariante INV-011)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Al alcanzar 3 pérdidas consecutivas el sistema activa LOSS_STREAK_LOCK
- El bloqueo requiere los 4 pasos de liberación

### REQ-G-024
**Descripción:** 8 estados del Risk Manager: ACTIVE, POSITION_OPEN, LOSS_STREAK_LOCK, MONTHLY_DRAWDOWN_LOCK, MONTHLY_TRADE_LIMIT_LOCK, DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW. Los estados pueden coexistir. Liberar un bloqueo no elimina automáticamente otros bloqueos activos. MONTHLY_TRADE_LIMIT_LOCK se libera automáticamente al inicio del mes calendario siguiente, con aviso por Telegram (DEC-010 Q28; CR-009); los demás bloqueos siguen sus propias reglas de liberación. Las acciones de protección y cierre de posiciones permanecen disponibles en todos los estados.  
**Fuentes:** REQ-5034  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema implementa los 8 estados
- El sistema mantiene un conjunto de causas de bloqueo activas (no un único estado)
- Las acciones de protección están disponibles en todos los estados bloqueados

### REQ-G-025
**Descripción:** Bajo cualquier bloqueo, las acciones de protección y cierre de posiciones abiertas siempre permanecen disponibles. Ningún bloqueo puede impedir cerrar o proteger una posición abierta. El sistema no puede abrir una nueva posición arguyendo proteger una existente.  
**Fuentes:** REQ-5026  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-026
**Descripción:** Toda operación requiere un mecanismo de salida verificable y cuantificable antes de ser autorizada. El mecanismo debe especificar: condición exacta de activación, precio o criterio de ejecución, método de detección, mecanismo de envío de la orden, comportamiento ante errores y riesgo estimado. Se rechaza una operación sin mecanismo de salida, sin verificabilidad, sin posibilidad de estimar riesgo, dependiente exclusivamente de decisión discrecional futura, o sin procedimiento de contingencia ante fallos.  
**Fuentes:** REQ-5011, REQ-5041  
**Tipo:** RISK_MANAGEMENT (invariante INV-007)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema rechaza cualquier operación sin mecanismo de salida verificable
- El Risk Manager verifica existencia y verificabilidad del mecanismo antes de RISK_APPROVED

### REQ-G-027
**Descripción:** Modificaciones del stop-loss post-entrada: solo se permiten para reducir riesgo o proteger capital/beneficios. Para posición Long: `P_stop_nuevo >= P_stop_inicial`. La restricción no aplica a diferencias de ejecución por slippage. Toda modificación de stop genera un evento de auditoría.  
**Fuentes:** REQ-5023, REQ-5024, REQ-5036  
**Tipo:** RISK_MANAGEMENT (invariante INV-009)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El sistema rechaza modificaciones de stop que lleven `P_stop_nuevo < P_stop_inicial`
- Toda modificación de stop genera un evento de auditoría

### REQ-G-028
**Descripción:** 12 invariantes de riesgo no modificables por ningún agente. Lista completa:
- INV-001: `RiskEffective <= Equity × 0.015`
- INV-002: `MonthlyDrawdown < 0.05` para permitir nuevas entradas
- INV-003: `OpenPositions <= 1`
- INV-004: `Leverage = 1`; solo Spot
- INV-005: Long-only; no Short
- INV-006: Sin promediado a la baja
- INV-007: Toda operación requiere mecanismo de salida verificable antes de autorización
- INV-008: Ninguna nueva operación sin autorización individual válida
- INV-009: `P_stop_nuevo >= P_stop_inicial` para posición Long
- INV-010: `MonthlyTradeCount <= 8`
- INV-011: 3 pérdidas consecutivas → LOSS_STREAK_LOCK
- INV-012: Incapacidad de verificar condición de riesgo → bloqueo de nuevas entradas (Fail-Closed)  
**Fuentes:** REQ-5035..REQ-5039  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existe ningún mecanismo en el código que permita a ningún agente sobreescribir ningún invariante

### REQ-G-029
**Descripción:** Comportamiento Fail-Closed (INV-012): ante imposibilidad de verificar cualquier condición de riesgo, el sistema bloquea nuevas entradas. Condiciones específicas de Fail-Closed: equity actual desconocido, riesgo efectivo incalculable, estado de posición desconocido, mecanismo de salida no verificable, discrepancia local/Binance, estado de bloqueo mensual desconocido. La ausencia de información no constituye autorización para operar.  
**Fuentes:** REQ-5003, REQ-5039, REQ-3032  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-030
**Descripción:** 16 criterios de implementación correcta del Risk Manager (REQ-5047 en DOC-005/RISK_POLICY.md). Cada criterio debe tener prueba automatizada y evidencia de validación. La cobertura de los 16 criterios debe estar confirmada antes de G4. Los 16 criterios, con el texto de RISK_POLICY.md «¿Cuándo se considera bien implementada esta política?» (CR-008): (1) el equity se calcula correctamente a partir de los saldos y posiciones reales; (2) el presupuesto del 1.5% se actualiza con el equity actual; (3) el position sizing incorpora precio, costes y reserva de slippage; (4) el redondeo de cantidades no permite exceder el presupuesto; (5) no pueden existir dos posiciones abiertas simultáneamente; (6) el sistema rechaza operaciones sin mecanismo de salida; (7) el sistema rechaza cualquier intento de promediar a la baja; (8) el drawdown incorpora pérdidas realizadas y no realizadas; (9) el bloqueo mensual se activa al alcanzar el 5%; (10) tres pérdidas consecutivas activan la suspensión; (11) los bloqueos requieren las autorizaciones correspondientes para su liberación; (12) los stops no pueden modificarse para ampliar el riesgo inicial; (13) el límite mensual de ocho operaciones se respeta; (14) los agentes no pueden ejecutar operaciones sin aprobación humana; (15) los errores de datos o sincronización producen un comportamiento restrictivo; (16) todos los eventos de riesgo quedan registrados y son auditables. Los test cases individuales TC-RM-01..TC-RM-16 se definen en FASE 2.  
**Fuentes:** REQ-5047  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-031
**Descripción:** Stop-loss colocado en el exchange. Al confirmarse la ejecución de una compra (ORDER_FILLED, incluidas ejecuciones parciales), el Execution Engine coloca de inmediato en Binance una orden de stop por la cantidad ejecutada y al precio de stop autorizado. El monitoreo del stop en software se mantiene como segunda capa. Toda modificación de stop permitida por REQ-G-027 se aplica cancelando y reemplazando la orden en Binance. Si la orden de stop no puede colocarse, el sistema emite STOP_ORDER_FAILED, avisa al propietario por Telegram y aplica Fail-Closed (bloqueo de nuevas entradas). La reconciliación verifica que toda posición abierta tenga su stop activo en Binance. **Cierre protector (CR-005, DEC-008 Q25):** en la reconciliación de arranque, en la periódica y en el monitoreo de segunda capa, si hay posición abierta sin stop activo en Binance: (a) con el precio sobre el stop, se recoloca el stop sin nueva autorización (STOP_ORDER_PLACED; si falla, STOP_ORDER_FAILED); (b) con el precio en o por debajo del stop, se envía de inmediato una venta a mercado por la cantidad en posición con identificador de cliente determinista (PROTECTIVE_CLOSE_SUBMITTED), sin nueva autorización por ejecutar la salida ya autorizada (INV-007); después, aviso por Telegram y MANUAL_REVIEW (sin nuevas entradas) hasta revisión del propietario; (c) si el precio no puede obtenerse, Fail-Closed (DATA_UNAVAILABLE), aviso inmediato e intento de recolocar el stop; nunca se cierra a ciegas.  
**Fuentes:** REQ-5011, REQ-5021; DEC-006 (Q17); CR-002; DEC-008 (Q25); CR-005 §D; CR-012  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-002; ampliado CR-005  
**Tipo de orden (CR-012, DEC-012):** OCO de Binance Spot con pierna de stop **STOP_LOSS de mercado** (no stop-limit) y, si hay take-profit, pierna TP limit (`TAKE_PROFIT_LIMIT` en una long; el tipo definitivo se fija en la implementación). Sin TP: orden `STOP_LOSS` individual (el OCO exige dos piernas). Al ejecutarse una pierna, la otra se cancela automáticamente. Modificar el stop = cancelar y reemplazar la lista OCO completa. Contingencia: si Binance no permitiera OCO con STOP_LOSS de mercado, documentar la limitación y usar STOP_LIMIT con precio límite a 0.5% del precio de stop (un hueco mayor a 0.5% lo cubre el cierre protector). La orden de mercado siempre llena pero no acota el deslizamiento: la pérdida queda acotada por «stop + slippage real»; el deslizamiento por encima de la reserva de sizing (REQ-G-P04) es riesgo residual aceptado y documentado, no cota dura. Verificar contra el exchange real en FASE 2.  
**Criterios de aceptación:**
- Tras cada compra ejecutada existe en Binance una orden de stop activa por la cantidad ejecutada
- Con SwingPilot detenido y una posición abierta, la orden de stop sigue activa en Binance
- Si falla la colocación del stop: STOP_ORDER_FAILED, aviso por Telegram y bloqueo de nuevas entradas
- La reconciliación detecta y reporta una posición abierta sin stop activo
- Sin stop y con el precio en o bajo el stop: venta a mercado, aviso y MANUAL_REVIEW
- Sin stop y sin precio disponible: no se cierra a ciegas; Fail-Closed y aviso

### REQ-G-032
**Descripción:** Persistencia de estado y reinicio seguro. (1) Todo cambio de estado de una operación se escribe en almacenamiento durable antes de ejecutar la acción externa asociada (enviar orden, colocar/reemplazar stop, cancelar); si la escritura falla, la acción no se ejecuta (Fail-Closed). (2) Al arrancar, toda autorización humana vigente cuya orden no conste como enviada y confirmada se invalida (AUTHORIZATION_INVALIDATED); requiere nueva autorización aunque `valid_until_utc` no haya vencido. (3) Cada orden enviada a Binance lleva un identificador de cliente derivado de forma determinista del `correlation_id` y de la secuencia de la orden en el ciclo; antes de reenviar tras una caída se consulta en Binance por ese identificador y, si la orden existe, se adopta su estado en lugar de enviar otra. (4) La reconciliación de arranque (REQ-G-P26) aplica los puntos 2 y 3 y registra su resultado (STARTUP_RECONCILIATION_COMPLETED). Los estados persistidos son los de REQ-G-037; la acción de recuperación por estado es la de REQ-G-038.  
**Fuentes:** REQ-G-062 (eventos idempotentes; REQ-3007, REQ-3009, REQ-3046), REQ-5041; DEC-006 (P26); CR-003 §A; CR-005  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-003  
**PENDING (FASE 2):** formato exacto del identificador de cliente según restricciones de Binance; mecanismo concreto de almacenamiento durable (referencia no vinculante: tabla `operations` en SQLite `state.db`, CR-005 §E, con estados de REQ-G-037, identificador de cliente por orden con secuencia, `valid_until_utc` y `last_error`).  
**Criterios de aceptación:**
- Ninguna acción externa ocurre sin que su estado previo esté persistido
- Tras un reinicio, una autorización no enviada no produce orden
- Un reintento tras caída nunca produce dos órdenes para la misma decisión

### REQ-G-033
**Descripción:** Seguridad del canal de aprobación humana (Telegram). El token del bot se trata como secreto con el mismo nivel que la clave de Binance: en `.env`, nunca en código fuente, registros ni mensajes a componentes LLM. El bot solo acepta acciones del identificador de usuario del propietario (DEC-004, Q5); cualquier otro remitente se ignora y se registra como evento de seguridad (UNAUTHORIZED_APPROVAL_ATTEMPT).  
**Fuentes:** REQ-5027; DEC-004 (Q5); CR-003 §B  
**Tipo:** SECURITY  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-003  
**Criterios de aceptación:**
- El token de Telegram no aparece en código fuente ni registros
- Un mensaje de aprobación de un usuario distinto al propietario no tiene efecto y queda registrado

### REQ-G-034
**Descripción:** Reintentos y fallo de agentes LLM. Cada llamada a un agente LLM admite 1 reintento tras pausa breve, solo ante errores transitorios (red, saturación, límite de tasa) o respuesta que no cumple el contrato JSON, siempre dentro del límite de 5 min del ciclo. Si un agente sigue fallando tras el reintento, el ciclo termina sin propuesta (Fail-Closed) y se registra su estado (ERROR/TIMEOUT). Si se alcanza el tope mensual de gasto de IA (REQ-G-P18), no se hacen llamadas y el ciclo termina sin propuesta. Las lecturas de datos de Binance admiten el mismo reintento único; las órdenes no (rige REQ-G-032). El reintento automático del SDK de Anthropic (2 por defecto) se configura para que el total por llamada sea 1 reintento, sea del SDK o propio, nunca ambos; timeout de 60 s configurado explícitamente en el cliente (CR-006).  
**Fuentes:** REQ-3047; DEC-006, DEC-007 (Q20, Q21); CR-004 §B  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-004  
**Criterios de aceptación:**
- Un error transitorio produce como máximo 1 reintento
- Un fallo persistente de cualquier agente termina el ciclo sin propuesta
- Con el tope mensual alcanzado no se realizan llamadas a LLM

### REQ-G-035
**Descripción:** Vigilancia del proceso y reinicio automático. SwingPilot emite un latido tras cada ciclo de reconciliación y como mínimo cada 15 min, sin saldo, posiciones ni credenciales. Un servicio externo de vigilancia, fuera de la red del propietario, alerta si pasan 30 min sin latido; la URL o clave de ping es secreta (`.env`) y el servicio no puede aprobar operaciones ni accede a credenciales. En la máquina de producción (Laptop B, DEC-007) el proceso se reinicia automáticamente si se cae y arranca en modo seguro (REQ-G-P26, REQ-G-032).  
**Fuentes:** DEC-007 (Q18, Q22); CR-004 §C  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-CR-004  
**PENDING (FASE 2):** elección del servicio externo de vigilancia.  
**Criterios de aceptación:**
- Sin latido durante 30 min, el propietario recibe alerta
- El proceso terminado se reinicia y entra en modo seguro

### REQ-G-036
**Descripción:** Verificación de IP pública. SwingPilot consulta su IP pública al arrancar y en cada ciclo. Si difiere de la IP registrada en la restricción de la clave de Binance (REQ-G-093) —por ejemplo, al pasar a internet satelital—, entra en Fail-Closed (sin operaciones nuevas) y avisa por Telegram antes de intentar operar. Reanudar requiere que el propietario actualice la IP en Binance y confirme. Las posiciones abiertas siguen protegidas por el stop en Binance (REQ-G-031).  
**Fuentes:** DEC-007 (Q22); CR-004 §D  
**Tipo:** SECURITY  
**Prioridad:** HIGH  
**Estado:** APPROVED-CR-004  
**PENDING (FASE 2):** servicio de consulta de IP pública.  
**Criterios de aceptación:**
- Con IP pública distinta a la registrada no se envían órdenes nuevas y el propietario recibe aviso

### REQ-G-037
**Descripción:** Máquina de estados de la operación. Una operación nace cuando el Risk Manager recibe un TRADE_PROPOSAL y termina en un estado terminal; es distinta de los estados del Risk Manager (REQ-G-024) y coexiste con ellos. Estados y transiciones permitidas: `PROPOSED` → `RISK_APPROVED` | `RISK_REJECTED`; `RISK_APPROVED` → `AWAITING_AUTH` | `INVALIDATED`; `AWAITING_AUTH` → `AUTHORIZED` | `AUTH_REJECTED` | `AUTH_EXPIRED` | `INVALIDATED`; `AUTHORIZED` → `ENTRY_PENDING` | `INVALIDATED`; `ENTRY_PENDING` → `ENTRY_FILLED` | `ENTRY_FAILED` | `INVALIDATED`; `ENTRY_FILLED` → `POSITION_OPEN` | `EXIT_PENDING`; `POSITION_OPEN` → `EXIT_PENDING`; `EXIT_PENDING` → `CLOSED` | `POSITION_OPEN`. Terminales: `RISK_REJECTED`, `AUTH_REJECTED`, `AUTH_EXPIRED`, `ENTRY_FAILED`, `CLOSED`, `INVALIDATED`. Reglas: (1) toda transición se persiste antes de la acción externa asociada (REQ-G-032); (2) una transición no listada se rechaza, se registra y aplica Fail-Closed; (3) no existe estado `ERROR` genérico: ante un fallo la operación conserva su último estado persistido con el error registrado y el sistema aplica Fail-Closed mediante los estados del Risk Manager (DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW); (4) a lo sumo una operación en `AUTHORIZED`, `ENTRY_PENDING`, `ENTRY_FILLED`, `POSITION_OPEN` o `EXIT_PENDING` (INV-003); (5) cada transición emite OPERATION_STATE_CHANGED. Significado de cada estado: CR-005 §A.  
**Fuentes:** REQ-G-032; REQ-G-024; DEC-008 (Q23); CR-005 §A  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-005  
**Criterios de aceptación:**
- Toda transición queda persistida antes de su acción externa
- Una transición no permitida se rechaza, se registra y aplica Fail-Closed
- Nunca hay más de una operación en estados activos

### REQ-G-038
**Descripción:** Recuperación por estado al arrancar. El sistema arranca siempre en modo seguro (REQ-G-P26): sin nuevas entradas hasta confirmación del propietario; durante la reconciliación solo se permiten acciones de protección (REQ-G-024). Por estado encontrado: `PROPOSED`, `RISK_APPROVED` → `INVALIDATED`, sin reenvío; `AWAITING_AUTH`, `AUTHORIZED` → `INVALIDATED` con AUTHORIZATION_INVALIDATED aunque la vigencia no haya vencido; `ENTRY_PENDING` → consulta en Binance por identificador de cliente: ejecutada (total o parcial) se adopta como `ENTRY_FILLED`, remanente abierto se cancela, sin ejecución → `ENTRY_FAILED`, inexistente → `INVALIDATED` sin reenvío, Binance sin respuesta → se conserva `ENTRY_PENDING` con EXCHANGE_DESYNC y nueva consulta en cada reconciliación sin enviar órdenes; `ENTRY_FILLED`, `POSITION_OPEN` → verificación del stop activo por la cantidad en posición y, si falta, cierre protector según REQ-G-031; `EXIT_PENDING` → consulta de la venta por identificador de cliente: ejecutada → `CLOSED` y registro en trades.db; inexistente → cierre protector según REQ-G-031 o, con el precio sobre el stop, `POSITION_OPEN` con stop verificado y aviso al propietario si la salida era manual; terminales → sin acción. Al terminar: STARTUP_RECONCILIATION_COMPLETED, informe por Telegram y espera de confirmación del propietario.  
**Fuentes:** REQ-G-032; REQ-G-P26 (DEC-006); DEC-008 (Q23); CR-005 §B  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-005  
**Criterios de aceptación:**
- Ninguna operación anterior al envío produce una orden tras el reinicio
- Una compra en curso se localiza por identificador de cliente y nunca se reenvía
- Tras la reconciliación no hay nuevas entradas sin confirmación del propietario

### REQ-G-039
**Descripción:** Vigencia de la autorización humana. `valid_until_utc` = momento de envío de la solicitud por Telegram + 30 min, medido con la hora del backend de autorización. Una respuesta recibida después no tiene efecto: la operación pasa a `AUTH_EXPIRED`, se emite AUTHORIZATION_EXPIRED, se avisa al propietario y los botones del mensaje vencido se desactivan o se ignoran. En el modo de prueba de FASE 2 se registra el tiempo entre solicitud y respuesta para revisar el valor con datos reales. El valor solo cambia mediante una decisión registrada (DEC).  
**Fuentes:** REQ-G-075; DEC-004 (Q5); DEC-008 (Q24); CR-005 §C  
**Tipo:** RISK_MANAGEMENT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-005  
**Criterios de aceptación:**
- Una respuesta dentro de 30 min es válida; una posterior no produce orden
- El vencimiento se mide con la hora del backend

---

## Módulo 4: Autorización Humana y Control de Acciones

### REQ-G-040
**Descripción:** Nivel 1 de autonomía — aprobación humana individual obligatoria para cada nueva operación. Los agentes pueden analizar y proponer; el Risk Manager puede calcular y validar; pero ninguna entrada puede ejecutarse sin autorización individual del propietario. Una recomendación nunca se convierte automáticamente en orden de ejecución.  
**Fuentes:** REQ-1016, REQ-5027, REQ-5042  
**Tipo:** CONSTRAINT (invariante INV-008)  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existe ninguna ruta de ejecución que omita la autorización individual del propietario
**RESUELTO — ver Módulo 15 (DEC-004):** mecanismo técnico de aprobación humana (REQ-G-P06).

### REQ-G-041
**Descripción:** Solo las operaciones que superan TODAS las restricciones del Risk Manager llegan al usuario para aprobación. El Risk Manager filtra operaciones inválidas antes de generar la solicitud de aprobación humana.  
**Fuentes:** REQ-5028  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- El Risk Manager rechaza operaciones inválidas antes de generar solicitud de aprobación

### REQ-G-042
**Descripción:** Una autorización previa puede invalidarse si las condiciones de riesgo cambian antes de la ejecución. El sistema verifica las condiciones en el momento de ejecutar, no solo al autorizar. Si los parámetros cambian materialmente, se solicita nueva autorización.  
**Fuentes:** REQ-5029  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-043
**Descripción:** Ningún agente puede crear excepciones a la política de riesgo ni auto-autorizarse. Las autorizaciones tienen origen externo del propietario, no del sistema mismo. Los agentes pueden proponer cambios, pero no implementarlos por iniciativa propia.  
**Fuentes:** REQ-1011, REQ-1022, REQ-5030, REQ-3031  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- No existe ningún mecanismo de excepción autónomo en ningún agente
- No existe ningún mecanismo de auto-autorización en el sistema

### REQ-G-044
**Descripción:** Acciones que requieren autorización expresa del propietario: incrementar capital, incorporar nuevos activos/pares, incorporar otro exchange, modificar riesgo por operación, modificar drawdown mensual, habilitar ejecución automática, incorporar derivados/margin/apalancamiento, modificar política fiscal o contable, habilitar Live Trading, aprobar cambios de límites de riesgo, aprobar nuevas políticas financieras.  
**Fuentes:** REQ-1020, REQ-3070  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-045
**Descripción:** Separación lógica y secuencial obligatoria entre etapas: 1) Investigación, 2) Validación experimental, 3) Generación de señales, 4) Recomendación operativa, 5) Autorización humana, 6) Ejecución real, 7) Registro y evaluación posterior. No existe camino que salte la autorización humana entre recomendación y ejecución.  
**Fuentes:** REQ-1017, REQ-4021  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001

---

## Módulo 5: Arquitectura de IA — Orchestrator y Agentes

### REQ-G-050
**Descripción:** SwingPilot implementa un AI Orchestrator central que coordina agentes especializados bajo demanda. No se permite red de agentes autónomos comunicándose libremente sin coordinación central. El Orchestrator no inventa señales ni sustituye a los motores deterministas.  
**Fuentes:** REQ-3001, REQ-3002  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001 (Principio D1 — AI_INTEGRATION.md)  
**Criterios de aceptación:**
- El Orchestrator puede coordinar una solicitud y recibir respuestas estructuradas, validadas y auditables

### REQ-G-051
**Descripción:** Responsabilidades del Orchestrator: recibir solicitudes de análisis; determinar qué agentes participan; preparar y distribuir contexto; administrar correlation_ids; coordinar análisis paralelos y secuenciales; validar respuestas contra contratos; enviar resultados a Decision Synthesis; registrar interacciones; gestionar errores, timeouts y respuestas incompletas. Fija los campos comunes de cada salida (api_contracts.md §3.0) y entrega a Market y Macro Analyst solo los campos de contexto de su contrato (§3.1, §3.4) (CR-016 E.1, E.3).  
**Fuentes:** REQ-3002, REQ-3003; CR-016  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-052
**Descripción:** Market Analyst (agente LLM): interpreta condiciones del mercado — analiza estructura de precios, tendencias, indicadores técnicos, zonas S/R, volatilidad/liquidez, coherencia entre temporalidades, rupturas y falsas rupturas. No puede autorizar operaciones. Entrada: datos de mercado, indicadores, temporalidades y contexto. Salida: análisis estructurado con observaciones, evidencia, confianza, limitaciones y timestamp de los datos.  
**Fuentes:** REQ-3013  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL

### REQ-G-053
**Descripción:** Macro Analyst (agente LLM): evalúa contexto macroeconómico — noticias económicas/financieras, eventos macro, regulatorios, institucionales, catalizadores de volatilidad, distingue confirmados de rumores. Salida: eventos relevantes, impacto potencial, horizonte temporal, fuentes, fecha de publicación y nivel de incertidumbre (contrato en api_contracts.md §3.5, CR-008). No puede convertir una noticia en una señal de entrada por sí sola.  
**Fuentes:** REQ-3014  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-054
**Descripción:** Strategy Analyst (agente LLM): analiza estrategias candidatas — evalúa lógica, condiciones de activación, coherencia señal/invalidación, condiciones que debiliten la oportunidad, comparación entre estrategias. Trabaja solo sobre estrategias formalmente definidas por Strategy Engine o Research. No puede modificar silenciosamente parámetros de estrategias aprobadas ni ejecutar operaciones.  
**Fuentes:** REQ-3015  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-055
**Descripción:** Risk Analyst (agente LLM): evaluación consultiva de riesgos — detecta riesgos no evidentes, señala inconsistencias, identifica exposición a eventos externos, evalúa riesgos operativos/datos, cuestiona supuestos. Su evaluación es informativa y no vinculante. No sustituye al Risk Manager determinista. No tiene autoridad para aprobar operaciones. **Momento de ejecución (CR-004):** corre en la Fase 5, solo después de RISK_APPROVED, sobre la propuesta aprobada y el estado del sistema; su evaluación se muestra al propietario junto con la propuesta en Telegram. No puede revertir ni modificar el resultado del Risk Manager. Decision Synthesis no integra su salida.  
**Fuentes:** REQ-3016; CR-004 §A  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-056
**Descripción:** Decision Synthesis (agente LLM): consolida resultados — integra análisis, identifica coincidencias y contradicciones, preserva desacuerdos, identifica datos faltantes, evalúa consistencia de evidencia, presenta escenarios. Genera TRADE_PROPOSAL cuando hay información suficiente. No fabrica consenso ni oculta incertidumbre. TRADE_PROPOSAL no es una orden ni una autorización.  
**Fuentes:** REQ-3017, REQ-3025, REQ-3059  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Decision Synthesis preserva incertidumbre y desacuerdos
- TRADE_PROPOSAL no puede llegar a ejecución sin pasar por Risk Manager

### REQ-G-057
**Descripción:** Componentes no-LLM (motores deterministas): Trading Engine, Market Intelligence, Regime Engine, Strategy Engine, ML Engine, Portfolio Manager, Risk Manager, Execution Engine, Fiscal Ledger, Research & Backtesting, Audit & Governance. Conservan lógica propia, verificable y reproducible. La IA puede interpretar sus resultados pero no sustituir sus cálculos críticos.  
**Fuentes:** REQ-3018  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Strategy Engine y ML Engine son componentes diferenciados de los LLM
- Risk Manager opera de manera determinista

### REQ-G-058
**Descripción:** Tabla de autoridad del sistema: interpretación de mercado→agentes IA; aprobación técnica→Risk Manager determinista; envío de órdenes→Execution Engine; capital/presupuesto→operador humano; cambio de modo operativo→operador autorizado; modificar políticas críticas→operador autorizado.  
**Fuentes:** REQ-3030, REQ-3031  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Agentes IA no tienen autoridad de ejecución
- La asignación de capital permanece bajo autoridad humana

### REQ-G-059
**Descripción:** Prohibiciones absolutas para todos los agentes: no cambiar límites de riesgo, no modificar capital configurado, no auto-autorizarse, no modificar reglas de ejecución, no eludir validaciones, no ejecutar herramientas financieras fuera de sus permisos, no transformar una recomendación en una orden, no alterar registros históricos (texto de AI_INTEGRATION.md, CR-008).  
**Fuentes:** REQ-3031, REQ-1016  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

---

## Módulo 6: Contratos de Mensajes y Eventos

### REQ-G-060
**Descripción:** Toda comunicación entre componentes inteligentes usa contratos de entrada/salida estructurados en JSON validado mediante esquemas versionados. No se acepta texto libre como único mecanismo de intercambio entre componentes críticos.  
**Fuentes:** REQ-3004, REQ-3005, REQ-3055  
**Tipo:** INTERFACE  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001 (Principio D2)  
**Criterios de aceptación:**
- Cada agente tiene contratos de entrada y salida versionados

### REQ-G-061
**Descripción:** Contrato universal de mensajes — todo evento/mensaje debe contener: message_id (uuid), correlation_id (uuid), causation_id (uuid-or-null), schema_version, source, destination, message_type, timestamp_utc, data_timestamp_utc, asset, timeframe, payload, status.  
**Fuentes:** REQ-3019, REQ-3008, REQ-3056  
**Tipo:** INTERFACE  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001 (Principio D3)  
**Criterios de aceptación:**
- Los mensajes tienen identificadores de correlación y causalidad

### REQ-G-062
**Descripción:** Comunicación orientada a eventos. El sistema puede reconstruir el ciclo completo de una operación a través de sus eventos mediante correlation_id y causation_id. Las operaciones sensibles son idempotentes. Los registros históricos son inmutables.  
**Fuentes:** REQ-3007, REQ-3009, REQ-3046  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Los resultados pueden reconstruirse históricamente
- Los registros históricos no se sobrescriben para aparentar uso de información retrospectiva

### REQ-G-063
**Descripción:** Catálogo inicial de 16 tipos de eventos del sistema (ampliado por CR-002..CR-006; catálogo vigente en `api_contracts.md` §2, 34 tipos; CR-015 añade STRATEGY_ANALYSIS_COMPLETED; CR-018 añade STRATEGY_EXIT_SIGNAL y STOP_ADJUSTMENT_REQUESTED; CR-019 añade PROPOSAL_NORMALIZATION_REJECTED): ANALYSIS_REQUESTED, MARKET_ANALYSIS_COMPLETED, MACRO_ANALYSIS_COMPLETED, ML_INFERENCE_COMPLETED, REGIME_CLASSIFIED, STRATEGY_CANDIDATE, DECISION_SYNTHESIS_COMPLETED, TRADE_PROPOSAL, RISK_APPROVED, RISK_REJECTED, RISK_REQUIRES_REVIEW, ORDER_SUBMITTED, ORDER_PARTIALLY_FILLED, ORDER_FILLED, ORDER_CANCELLED, ORDER_REJECTED. Los nombres definitivos se establecen en el catálogo del sistema.  
**Fuentes:** REQ-3021  
**Tipo:** INTERFACE  
**Prioridad:** HIGH

### REQ-G-064
**Descripción:** Cada contrato especializado debe documentar: nombre, versión, propósito, productor autorizado, consumidores autorizados, campos obligatorios/opcionales, tipos de datos, enumeraciones, reglas de validación, manejo de errores, ejemplos válidos y compatibilidad con versiones anteriores. Los cambios incompatibles requieren nueva versión.  
**Fuentes:** REQ-3020, REQ-3006  
**Tipo:** INTERFACE  
**Prioridad:** HIGH  
**Criterios de aceptación:**
- Prompts, modelos, estrategias y contratos están versionados

---

## Módulo 7: Flujo de Decisión Integral (7 fases)

### REQ-G-070
**Descripción:** Fase 1 — Captura y preparación de datos: Trading Engine y Market Intelligence validan integridad, identifican temporalidad/activo, registran fuente/timestamp, detectan datos faltantes/duplicados/obsoletos, mantienen separación entre tiempo de mercado y tiempo de procesamiento. Si los datos no cumplen condiciones mínimas, el análisis no produce propuesta ejecutable. **Solo velas cerradas (CR-003 §C):** el análisis en vivo usa exclusivamente velas cerradas en D1, H4 y H1; la vela en formación se descarta. Una vela se considera cerrada cuando su tiempo de cierre según Binance es anterior al tiempo actual del servidor de Binance (no del reloj local). Si la última vela cerrada esperada no está disponible: DATA_UNAVAILABLE.  
**Fuentes:** REQ-3022; CR-003 §C  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL

### REQ-G-071
**Descripción:** Fase 2 — Filtro determinista (CR-004): Regime Engine y ML Engine producen sus resultados; el Strategy Engine evalúa las estrategias aprobadas con ellos y produce STRATEGY_CANDIDATE. La salida del ML Engine la consume el Strategy Engine (familia ML-Based) y Decision Synthesis solo como contexto; no es un decisor paralelo. **Si no hay candidato: NO_SETUP y fin del ciclo sin ninguna llamada a LLM.** **Resolución de candidatos (CR-011, DEC-011):** la resolución es determinista y ocurre en el Strategy Engine, no en Decision Synthesis. La regla es binaria (candidato sí/no); no se usa puntuación de confianza para decidir ni ponderar en ninguna familia, incluida ML-Based. Dos o más candidatos de entrada (long) en el mismo ciclo (mismo `correlation_id`) → `NO_SETUP` (fail-closed), también cuando coinciden; no se suman tamaños, no se elige el «mejor» ni se reduce tamaño; se registran los candidatos descartados y el motivo. Entrada + señal de salida simultáneas: prevalece la salida; si queda un candidato de entrada válido, se re-evalúa en el siguiente ciclo. Las salidas por señal de estrategia y los cierres protectores son autónomos (sin autorización humana); solo las entradas requieren autorización individual (INV-008). Contratos de REGIME_CLASSIFIED, ML_INFERENCE_COMPLETED, STRATEGY_CANDIDATE, STRATEGY_EXIT_SIGNAL, STOP_ADJUSTMENT_REQUESTED, motivos de NO_SETUP y errores técnicos: `api_contracts.md` §3.8 (CR-018). Fase 3 — Análisis LLM paralelo: el Orchestrator distribuye contexto a Market Analyst, Macro Analyst y Strategy Analyst. Todos los resultados comparten correlation_id. Cada componente entrega resultado o estado explícito (error, indisponibilidad, insuficiencia).  
**Fuentes:** REQ-3023; CR-004 §A  
**Nota:** el orden original de DOC-003 (análisis paralelo antes de evaluación de estrategias) se ajusta por CR-004; DOC-003 no se modifica.  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL

### REQ-G-072
**Descripción:** Evaluación de estrategias (Fase 2 desde CR-004): Strategy Engine evalúa estrategias candidatas. Las familias (Trend Following, Momentum, Mean Reversion, Breakout, Volatility-Based, ML-Based) son referencias de investigación, no habilitadas automáticamente para producción. Cada estrategia requiere definición versionada, condiciones de entrada/salida, reglas de invalidación y evidencia experimental.  
**Fuentes:** REQ-3024  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-073
**Descripción:** Fase 4 — Síntesis: Decision Synthesis integra los resultados de las Fases 2 y 3 (no los del Risk Analyst, CR-004) y determina si generar TRADE_PROPOSAL, solicitar info adicional, descartar oportunidad o indicar desacuerdo. TRADE_PROPOSAL no es una orden ni autorización. Cita en `input_analysis_ids` exactamente los tres análisis de la Fase 3. Los datos faltantes declarados en la Fase 3 se propagan de forma determinista a la salida de la síntesis (api_contracts.md §3.3, CR-016). La TRADE_PROPOSAL se normaliza de forma determinista desde el STRATEGY_CANDIDATE (api_contracts.md §3.8 B.8, CR-018).  
**Fuentes:** REQ-3025  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL

### REQ-G-074
**Descripción:** Fase 5 — Validación determinista de riesgo: Risk Manager recibe la propuesta y ejecuta validaciones. Verifica mínimamente: capital disponible, riesgo monetario/porcentual, stop-loss, exposición agregada, posiciones simultáneas, límite mensual, instrumentos permitidos, liquidez, integridad de datos, versión de estrategia, duplicidad, consistencia de cantidades. Resultados posibles: RISK_APPROVED, RISK_REJECTED, RISK_REQUIRES_REVIEW. Ausencia de respuesta ≠ aprobación. Tras RISK_APPROVED corre el Risk Analyst (REQ-G-055); si RISK_REJECTED, no se invoca.  
**Fuentes:** REQ-3026  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Risk Manager opera de manera determinista
- No existe ejecución sin autorización válida

### REQ-G-075
**Descripción:** Fase 6 — Autorización y ejecución: las autorizaciones deben contener propuesta original, ID de autorización, instrumento, cantidad máxima autorizada, límites de precio, vigencia, versión de reglas de riesgo y estado. Execution Engine solo acepta autorizaciones válidas. Las autorizaciones expiradas, revocadas o que incumplan condiciones no pueden usarse. Vigencia: 30 min (REQ-G-039); estados de la operación y recuperación: REQ-G-037, REQ-G-038 (CR-005). Execution Engine reconcilia órdenes enviadas con ejecuciones reportadas por Binance. Las ejecuciones parciales son eventos independientes.  
**Fuentes:** REQ-3027, REQ-3028  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Binance puede reconciliar órdenes y ejecuciones

### REQ-G-076
**Descripción:** Fase 7 — Registro y retroalimentación: registro completo del ciclo — datos utilizados, análisis por agente, versiones de prompts/modelos, contratos/esquemas, propuestas, decisiones del Risk Manager, autorizaciones, órdenes/ejecuciones, comisiones, resultado y evaluación posterior. Los resultados originales no se alteran retroactivamente.  
**Fuentes:** REQ-3029  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

---

## Módulo 8: Modos Operativos

### REQ-G-080
**Descripción:** SwingPilot tiene 3 modos operativos: Research, Paper Trading, Live Trading. El cambio de modo está protegido, registrado y requiere autorización humana. Ningún agente LLM puede cambiar de Research o Paper Trading a Live Trading por sí solo.  
**Fuentes:** REQ-3033  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Research, Paper Trading y Live Trading están separados

### REQ-G-081
**Descripción:** Modo Research: sin ejecución de órdenes reales. Permite investigación, experimentación, backtesting y evaluación de modelos ML.  
**Fuentes:** REQ-3034  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

### REQ-G-082
**Descripción:** Modo Paper Trading: simula propuestas y operaciones, valida flujo completo, evalúa riesgo, simula ejecución y mide desempeño sin capital real. El ciclo completo puede probarse sin comprometer capital real.  
**Fuentes:** REQ-3035  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-083
**Descripción:** Modo Live Trading: operaciones reales en Binance. Requiere autorización explícita del operador, controles de riesgo activos, credenciales apropiadas y reconciliación de órdenes/ejecuciones.  
**Fuentes:** REQ-3036  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

---

## Módulo 9: Integración Tecnológica

### REQ-G-090
**Descripción:** Anthropic Claude es el proveedor LLM principal del runtime de SwingPilot. El runtime de producción usa Anthropic API con cuenta y facturación independiente de Claude Pro. Se implementa un AI Provider Adapter como capa de abstracción entre el Orchestrator y Anthropic. No se requieren múltiples proveedores LLM en v1.  
**Fuentes:** REQ-3010, REQ-3011, REQ-3012  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001 (Principio D4)

### REQ-G-091
**Descripción:** Integración Anthropic Claude: usar API para inferencia, API keys en .env (no en código fuente), aplicar límites de consumo, monitorear costes, registrar modelo/versión usados, controlar timeouts, validar respuestas, no asumir que respuesta en lenguaje natural es operativamente válida.  
**Fuentes:** REQ-3037  
**Tipo:** SECURITY  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Costes de IA son medibles
- Prompts, modelos, estrategias y contratos están versionados

**Ampliado por CR-006:** modelos, forma de invocación y caching en REQ-G-095; controles de costo en REQ-G-096.

### REQ-G-092
**Descripción:** Python es la base para modelos cuantitativos (pandas, NumPy, scikit-learn, XGBoost, PyTorch solo con justificación experimental). Los modelos requieren ID/versión, datos de entrenamiento identificados, métricas, separación Train/Validation/Test, evidencia backtesting, registro de inferencias y política de actualización. Salida de ML ≠ certeza ni autorización.  
**Fuentes:** REQ-3039  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-093
**Descripción:** Integración Binance: obtener datos de mercado, consultar balances, enviar órdenes autorizadas, consultar estado de órdenes, recuperar ejecuciones/comisiones, reconciliar. Credenciales con permisos mínimos. Los componentes IA no reciben credenciales de ejecución directa. **Permisos explícitos (CR-003 §B):** la clave de API de Binance tiene solo lectura y trading Spot; **sin permiso de retiro** y sin margin/futuros; con **restricción por IP** limitada al equipo donde corre SwingPilot; almacenada en `.env`, nunca en código ni registros. Al arrancar, el sistema verifica los permisos de la clave por API; si tiene permiso de retiro habilitado, no opera en modo Live (Fail-Closed).  
**Fuentes:** REQ-3040; CR-003 §B  
**Tipo:** SECURITY  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Con una clave que tenga permiso de retiro, el sistema no arranca en modo Live
- La clave está restringida por IP

### REQ-G-094
**Descripción:** Telegram es la interfaz de interacción y notificación. Muestra estado del sistema, análisis, propuestas, alertas, órdenes, resultados y solicitudes de intervención. Las acciones críticas requieren autorización/identidad/permisos del backend. Telegram no es fuente de autoridad independiente; el backend valida cada acción.  
**Fuentes:** REQ-3041  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-095
**Descripción:** Modelos y forma de invocación de los agentes LLM. Modelos: Market Analyst, Macro Analyst, Strategy Analyst y Risk Analyst → `claude-haiku-5-5`; Decision Synthesis → `claude-sonnet-5-5`. Se usan identificadores exactos, sin alias, y `model_id` registra el modelo efectivamente usado. El nivel de esfuerzo (`effort`) se fija explícitamente por agente (valor inicial `medium`, calibrado en el modo de prueba de FASE 2). Cada agente es una llamada independiente a la Messages API orquestada por el AI Orchestrator determinista; no se usan Claude Agent SDK, Managed Agents ni Batches API. Los agentes no reciben herramientas; su salida se obtiene como salida estructurada validada por esquema (`output_config.format`) contra el contrato JSON de `api_contracts.md` §3, y una salida que no valida cuenta como respuesta fuera de contrato (REQ-G-034). Una respuesta con `stop_reason: "refusal"` es fallo del agente (ciclo sin propuesta); no se usa cambio automático de modelo (`fallbacks`). No se usa prompt caching (`cache_control`): ciclos cada 4 h y prompts distintos por agente no generan reutilización. Cambiar el modelo de un agente o activar caching requiere una DEC.  
**Fuentes:** REQ-G-091 (REQ-3037); REQ-G-034; REQ-G-P18 (DEC-006); DEC-009 (Q26, Q27); CR-006 §A, §B, §D  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-006  
**PENDING (FASE 2):** calibración de `effort` por agente; costo real por ciclo.  
**Criterios de aceptación:**
- Cada agente usa el modelo asignado y lo registra en `model_id`
- Ninguna llamada a un agente incluye herramientas
- Una salida que no valida contra el esquema se trata como fuera de contrato
- Un rechazo del modelo termina el ciclo sin propuesta y sin cambio de modelo

### REQ-G-096
**Descripción:** Controles de costo de la IA. (1) Con el tope mensual de $5 USD alcanzado no hay llamadas a LLM (REQ-G-034). (2) Al alcanzar $4 de gasto en el mes, aviso por Telegram (AI_BUDGET_WARNING), una sola vez por mes calendario (DEC-010 Q29). (3) Antes de la Fase 3, si hay posición abierta (INV-003) o un bloqueo que impide nuevas entradas (LOSS_STREAK_LOCK, MONTHLY_DRAWDOWN_LOCK, MONTHLY_TRADE_LIMIT_LOCK, DATA_UNAVAILABLE, EXCHANGE_DESYNC, MANUAL_REVIEW o modo seguro), el ciclo termina sin llamadas a LLM; no afecta acciones de protección ni la gestión de la posición abierta. (4) Límite de gasto en la consola de Anthropic igual o ligeramente superior a $5 como respaldo, si la cuenta lo permite. (5) Se registra el uso de tokens (`usage`) de cada llamada para medir el costo real por ciclo.  
**Fuentes:** REQ-G-091; REQ-G-P18 (DEC-006); DEC-009 (Q27); CR-006 §E  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-CR-006  
**PENDING (FASE 2):** disponibilidad del límite de gasto en la consola de la cuenta.  
**Criterios de aceptación:**
- Con gasto mensual de $4 el propietario recibe AI_BUDGET_WARNING
- Con posición abierta o bloqueo de entradas activo no se realizan llamadas a LLM
- El costo de cada llamada queda registrado

---

### REQ-G-097
**Descripción:** Datos de mercado en vivo (CR-013, DEC-013; complementa REQ-G-070). Fuente: WebSocket de Binance `kline_4h` (señal), `kline_1d` (contexto) y `kline_1h` (evaluación de entrada, REQ-G-002); solo se consumen velas cerradas (flag `x`), nunca la vela en curso. Al reconectar, el sistema consulta por REST (`GET /api/v3/klines`) con `startTime` = `open_time` de la última vela persistida + 1, recupera todas las velas cerradas faltantes (no solo la última) y verifica el timestamp contra el último candle en memoria; hasta resincronizar aplica Fail-Closed (no se generan señales ni propuestas). Las velas recuperadas se persisten con la misma fuente y timestamp.  
**Fuentes:** DEC-013; CR-013 §A.6, §B.3, §B.4; REQ-G-070  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-CR-013  
**Dependencias:** REQ-G-070, REQ-G-002  
**Criterios de aceptación:**
- Una vela en formación nunca produce señal
- Tras una desconexión de más de un intervalo, se recuperan todas las velas faltantes antes de operar
- Mientras no se resincroniza, no se generan señales (Fail-Closed)

---

## Módulo 10: Investigación Cuantitativa y Framework ML

### REQ-G-100
**Descripción:** Principios obligatorios de investigación cuantitativa: (1) Hipótesis falsable antes de cualquier backtest confirmatorio; (2) Separación temporal estricta entre datos de desarrollo (Training) y de evaluación (OOS/LOCKBOX); (3) Reproducibilidad: mismos inputs → mismo output; (4) Trazabilidad completa de decisiones metodológicas; (5) Falsabilidad: experimentos incluyen criterios de rechazo; (6) Generalización como objetivo principal, no maximización histórica.  
**Fuentes:** REQ-4005..REQ-4010  
**Tipo:** CONSTRAINT  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001

### REQ-G-101
**Descripción:** Separación obligatoria de 4 particiones de datos con temporal aislamiento estricto: Training Set (ajuste de modelos), Validation Set (selección de configuraciones/hiperparámetros), OOS (evaluación no usada en desarrollo), LOCKBOX OOS (evaluación final, completamente aislado). El LOCKBOX no puede usarse para ninguna decisión de desarrollo (sin selección de características, sin modificar hiperparámetros, sin rediseñar modelos). La reutilización del LOCKBOX debe registrarse. **CR-023 (DEC-025):** OOS y LOCKBOX solo contienen datos posteriores a una frontera de independencia prospectiva válida (REQ-G-109); la ausencia de exposición documentada no establece independencia, y las restricciones de exposición se aplican a todas las hipótesis BTC/USDT. Detalle: `harness/change_requests/CR-023_particiones-prospectivas-frontera-independencia.md`.  
**Fuentes:** REQ-4006, REQ-4016, REQ-4030; CR-023  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**RESUELTO — ver Módulo 15 (DEC-005):** división Train/Validation/OOS/LOCKBOX (REQ-G-P10).

### REQ-G-102
**Descripción:** Prohibición absoluta de look-ahead bias: no usar información que no estuviera disponible en el momento histórico de la señal. Prohibición de data leakage: controles sobre variables derivadas del futuro, normalización sobre dataset completo, imputación con info futura, selección de características con datos OOS, etiquetas con info posterior, ventanas superpuestas, contaminación entre particiones. Las transformaciones y selección se ajustan solo con datos de la partición permitida.  
**Fuentes:** REQ-4017, REQ-4018  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001  
**Criterios de aceptación:**
- Las pruebas de auditoría verifican ausencia de look-ahead bias y leakage en las 7 categorías

### REQ-G-103
**Descripción:** Preregistro obligatorio antes de cualquier backtest confirmatorio o entrenamiento formal. El preregistro incluye: pregunta de investigación, hipótesis principal, hipótesis nula, justificación, universo de activos, temporalidad, periodo, variables, reglas de entrada/salida, modelo/configuración inicial, división de datos, métricas, costes, criterios de aceptación/rechazo y limitaciones. El preregistro se congela ANTES de la evaluación confirmatoria. Las desviaciones se documentan y justifican. **CR-011 (DEC-011):** el preregistro congela además la longitud de entrenamiento, la de prueba, el embargo, el step size, la frecuencia de roll y el número de ventanas Walk-Forward antes de cualquier evaluación OOS; cambiarlos tras ver resultados OOS es una desviación y el experimento deja de ser confirmatorio. Debe calcular y documentar el histórico mínimo de la región de desarrollo, `H_dev,min = max(38; 100/r)` meses, y la longitud de cada ventana prospectiva, `L_oos ≥ k·30/r` y `L_lb ≥ k·30/r` meses con `k ≥ 1` congelado, usando la tasa real de trades `r` observada en un backtest piloto estimada solo con datos de Train y no solo el máximo teórico de 8/mes (REQ-G-004) (CR-011, modificado por CR-023). Los datos y el modelo de ejecución siguen REQ-G-109 (CR-013, CR-023). Si la región de desarrollo no alcanza, el preregistro documenta la limitación y propone un ajuste (decisión del propietario); los mínimos no se relajan por sí solos y el experimento no pasa de DESIGN. **CR-020 (DEC-021):** el preregistro congela la contabilidad de pruebas (REQ-G-P17): conteo histórico documentado, cotas conservadoras, configuraciones nativas ya evaluadas y configuraciones planificadas con su identificador, más una regla determinista y reproducible de selección de la configuración candidata (`candidate_selection_rule`), que solo usa configuraciones planificadas y resultados de Train+Val del propio experimento. No puede congelarse si el conteo no coincide con el reconstruido desde el registro, si algún antecedente carece de procedencia o si la regla está mal formada. Evaluar una configuración no planificada, o seleccionar una candidata distinta de la que da la regla, es una desviación y el experimento deja de ser confirmatorio. Los registros nuevos de desviación y de selección declaran en `informed_by` las pruebas consultadas, con referencias verificables; un campo vacío no establece independencia. **CR-023 (DEC-025):** (1) **Piloto de tasa:** un experimento cuyo preregistro declara `independence_boundary = {confirmatory_eligible: false, purpose: TRADE_RATE_PILOT, access_scope: TRAIN_ONLY}` está exento del cálculo de histórico mínimo con `r`, solo accede a la porción Train de la snapshot de desarrollo, nunca es confirmatorio y sus pares cuentan según REQ-G-P17. (2) **Congelación completa antes de la frontera `B`** de un experimento confirmatorio: hipótesis y configuraciones planificadas; versiones y SHA-256 del código de estrategia y de cada configuración (`model_config`); `candidate_selection_rule`; modelo de ejecución y costes; umbrales de aceptación y rechazo; métricas y métodos estadísticos; reglas de selección y promoción; parámetros de régimen y versiones de modelos que condicionan la estrategia (`conditioning_components`); ventanas, regla de parada de calendario y tratamiento de las posiciones abiertas al cierre de ventana (`independence_boundary`); inventario de exposición (documentada, incierta y desconocida, con referencias versionadas, la limitación de familiaridad general y todos los `DEVIATION` de independencia existentes). (3) **Almacén recuperable:** el contenido exacto del preregistro se guarda, antes del registro PREREGISTERED, en `research/preregistrations/<experiment_id>/<sha256>.json` (creación exclusiva, sin sobrescritura ni borrado, verificación del SHA-256 en cada lectura); su falta o incoherencia es un fallo técnico (Fail-Closed). El almacén no satisface por sí solo la obligación O4. (4) **Regla endurecida:** en un experimento confirmatorio con frontera, un DEVIATION de cualquier campo posterior a PREREGISTERED lo hace no confirmatorio, haya o no consumo. (5) **Contaminación:** se registra con un DEVIATION del campo `independence_boundary` del experimento dueño de la ventana, con el periodo contaminado, la clase, la evidencia versionada y el inicio de la exposición (o `UNKNOWN`); afecta a todo experimento cuya evaluación final use datos de ese periodo, en cualquier estado, y el periodo no puede volver a ser ventana de evaluación para ninguna hipótesis BTC/USDT. Los DEVIATION de otros campos conservan su semántica. Comprobaciones por etapa y detalle: CR-023 §C.4–§C.9 y §D.  
**Fuentes:** REQ-4005, REQ-4013; CR-023  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001

### REQ-G-104
**Descripción:** Ciclo de vida de experimentos con 12 estados: IDEA → DESIGN → PREREGISTERED → DATA_VALIDATION → DEVELOPMENT → VALIDATION → OOS_EVALUATION → AUDIT → HUMAN_REVIEW → APPROVED / REJECTED / INCONCLUSIVE. Las transiciones entre estados están condicionadas al cumplimiento de requisitos verificables. La aceptación experimental no autoriza operar con capital real. **CR-020 (DEC-021):** el registro de experimentos conserva, en modo append-only, la procedencia de los antecedentes declarados y el inicio de la evaluación de cada configuración, que debe quedar registrado de forma duradera antes de empezar; si la escritura falla o es incierta, la evaluación no empieza. El inicio solo se registra si el estado del experimento, las transiciones y las autorizaciones vigentes permiten esa evaluación; un estado no terminal no basta. Ese registro es el límite contable conservador de un inicio autorizado, no prueba de ejecución completa; una solicitud rechazada antes de escribirlo no se registra como evaluada. La procedencia solo se registra con una autorización `AUTORIZA: PROCEDENCIA` validada de forma estricta y evidencia documental. El estado original de un antecedente no se reescribe y las consultas lo distinguen de su procedencia documental vigente. No cambian los estados ni las transiciones. **CR-021 (DEC-023; sustituye las obligaciones afectadas de CR-020 §C.3.2):** la contabilidad conservadora y la autorización de acceso a los datos son garantías separadas. El acceso a Train+Val para una configuración exige un registro `EVALUATION_PERSISTED` válido, escrito solo después del `fsync` correcto de la evidencia exacta que certifica (el `CONFIGURATION_EVALUATED` y, si la configuración no está planificada, su DEVIATION obligatoria), vinculado a ella por SHA-256; la autorización se basa en la durabilidad de esa evidencia, no en la del marcador. Una escritura o un `fsync` fallidos o inciertos de la evidencia certificada (no del marcador; véase el fallo del `fsync` del marcador más abajo) no autorizan el acceso, tampoco desde otro objeto ni desde otro proceso, y el reintento no informa éxito hasta que conste un marcador válido. La recuperación solo añade copias byte a byte idénticas de la primera aparición (se conservan el `deviation_id` y las identidades lógicas; la cronología es la de la primera aparición) y marcadores; un duplicado conflictivo es incoherente (Fail-Closed). Si falla el `fsync` del marcador, la operación informa incertidumbre; con un marcador válido legible se permiten el acceso y el reintento idempotente; si el marcador desaparece, el acceso se deniega sin eliminar ni duplicar la evidencia. Un registro corrupto (línea no válida o que no es un objeto, duplicado conflictivo, marcador no vinculable o cola sin salto de línea final) bloquea toda escritura, todo acceso a datos y todo veredicto favorable del evaluador; ninguna línea se ignora, el archivo original se conserva y no hay reparación automática: la recuperación exige un procedimiento aprobado y autorización humana explícita (CR-021 §F.2, P1–P5). Detalle: `harness/change_requests/CR-021_durabilidad-autorizacion-evaluacion.md`. **CR-023 (DEC-025):** un experimento con `confirmatory_eligible = false` (piloto de tasa) no transita a OOS_EVALUATION ni recibe autorizaciones de evaluación final, y su acceso a datos se limita a su `access_scope`. Un DEVIATION del campo `independence_boundary` se admite en cualquier estado posterior a PREREGISTERED, incluido un estado terminal; los registros de estado históricos (incluido APPROVED) no se reescriben. No cambian los estados ni las transiciones. **CR-024 (aprobada por el propietario, 2026-11-26; contrato v1.12; no modifica la semántica de CR-021 para Train+Val):** el resultado de la evaluación OOS y LOCKBOX se persiste de forma durable, inmutable y única: documento canónico (`schema` 1) en un almacén de evidencia separado y evento append-only `WINDOW_RESULT_PERSISTED`, ligados al preregistro congelado y al `PARTITION_CONSUMED`; `evaluation_hash` = SHA-256 de los bytes canónicos (excluye `at_utc` y `actor`). Solo `evaluate_window` emite el resultado persistible (`IssuedWindowResult`; procedencia dentro del modelo de proceso confiable). Estados de conciliación `NOT_CONSUMED`, `RESULT_VALID`, `CONSUMED_NO_RESULT`, `EVIDENCE_ONLY` y `CORRUPT`: `CONSUMED_NO_RESULT` bloquea el LOCKBOX, ET-8 y toda progresión, con disposición manual del propietario y sin reevaluación, reversión del consumo ni reconstrucción desde datos; `EVIDENCE_ONLY` solo se recupera con comando explícito del CLI que revalida la durabilidad de la evidencia; `CORRUPT` → `RegistryCorruptError` (P5 de CR-021 PENDIENTE). **Fallo de persistencia tras la emisión del resultado técnico:** el consumo es irreversible y el resultado (incluido el `TECHNICAL`/`UNDETERMINABLE` con `metrics = None` que sustituye a uno no canonicalizable) se emite antes de persistirse; si la escritura, el `fsync` o la relectura de la evidencia o del marcador fallan o son inciertos, se informa `PersistenceUncertainError`, nunca éxito; el resultado en memoria no es autoritativo, no se reevalúa ni se reintenta con datos nuevos y la ventana queda en `CONSUMED_NO_RESULT` o `EVIDENCE_ONLY`, que bloquean la progresión. Un OOS **favorable autoritativo** (`RESULT_VALID`, `verdict == ELIGIBLE_FOR_HUMAN_REVIEW`, `eligibility == ELIGIBLE` y `nature is None`, releído del registro y de la evidencia) es condición de ET-4, ET-5, ET-6 y `resolve_lockbox` del LOCKBOX; en ET-8, `OOS=` y `LOCKBOX=` de `AUTORIZA: APROBACION` son los `evaluation_hash` verificados de resultados favorables autoritativos. Sin cambios: `CONFIGURATION_EVALUATED` y `EVALUATION_PERSISTED` (solo Train+Val), forma de `PARTITION_CONSUMED`, CR-020, CR-022, D6. Detalle: `harness/change_requests/CR-024_persistencia-autoritativa-resultados-oos-lockbox.md`. **CR-025 (aprobada por el propietario, 2026-11-26; contrato v1.13; detalle: `harness/change_requests/CR-025_integridad-autoritativa-continua.md`):** la integridad de los resultados autoritativos de OOS y LOCKBOX es continua. La transición HUMAN_REVIEW → APPROVED persiste en su `evidence` la clave reservada `approval_binding` (esquema cerrado: `schema` 1, `prereg_sha256`, `oos_evaluation_hash`, `lockbox_evaluation_hash` y `attestation_sha256` = SHA-256 de los bytes UTF-8 exactos de la línea `AUTORIZA: APROBACION`, sin el salto final), escrita solo por la transición a partir del `ApprovalCheck` (una ligadura aportada por el llamador la rechaza); el registro es la autoridad y el texto de decisión editable no concede nada. La comprobación V9 (ET-9 y ET-10) verifica, sin atestación nueva, que los resultados OOS y LOCKBOX siguen `RESULT_VALID` y favorables autoritativos, que sus `evaluation_hash` y el SHA-256 del preregistro coinciden con la ligadura, el orden consumo < marcador < APPROVED y la atestación original contra `attestation_sha256`. Todo fallo es técnico (nunca metodológico). Un APPROVED sin ligadura es técnico salvo que conste en el conjunto cerrado `HISTORICAL_APPROVALS`, inicialmente vacío y ampliable solo por enmienda contractual. La verificación compartida de evidencia de ET-8 se separa de los controles de orden posteriores a la aprobación de V9. Sin cambios: estados y transiciones, tipos de registro, P5, O3/O4, D6.  
**Fuentes:** REQ-4037, REQ-4033; CR-023; CR-024  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001  
**RESUELTO — ver Módulo 15 (DEC-005):** umbrales de rentabilidad, drawdown, expectancy, Profit Factor y tamaño de muestra (REQ-G-P11..REQ-G-P15).

### REQ-G-105
**Descripción:** Un modelo ML no es por sí solo una estrategia completa. El flujo distingue 7 etapas en orden: generación de características → inferencia → interpretación de predicciones → generación de señales → evaluación de riesgo → autorización → ejecución. Una predicción favorable no implica automáticamente una orden de compra. Un resultado de IA no constituye aprobación humana.  
**Fuentes:** REQ-4021, REQ-4038  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-106
**Descripción:** Obligaciones metodológicas de robustez: Walk-Forward Analysis (6 pasos: entrenar en ventana histórica, evaluar en periodo posterior, desplazar ventana, repetir, consolidar, analizar estabilidad/degradación); pruebas de robustez en 8 dimensiones (parámetros, temporalidad, condiciones de mercado, costes, slippage, ventanas históricas, operaciones individuales, estabilidad temporal); Bootstrap, Bootstrap por bloques y Monte Carlo. **Estructura de validación (CR-011, DEC-011; modificada por CR-023, DEC-025):** el Walk-Forward opera dentro de Train+Val, que es la región de desarrollo; OOS es una evaluación final única y LOCKBOX se usa una sola vez al final, ambas prospectivas tras la frontera de independencia (REQ-G-109). **CR-024:** la evaluación única solo es autoritativa cuando su resultado consta persistido (`RESULT_VALID`, REQ-G-104); una ventana consumida sin resultado persistido no se reevalúa y bloquea el LOCKBOX y la aprobación; persistir un resultado no habilita su reutilización. Cada ventana: entrenamiento 24 m → embargo 2 m → prueba 6 m; paso 6 m (el embargo separa el fin del entrenamiento del inicio de la prueba y debe ser ≥ el horizonte máximo de las etiquetas). Mínimo: 2 ventanas de prueba Walk-Forward para aceptar un modelo. El mínimo de 30 trades OOS se evalúa sobre el agregado, no por ventana. Referencia de histórico mínimo (indicativa; el cálculo vinculante es el del preregistro, REQ-G-103): con 2 ventanas la región WF exige 24+2+6+6 = 38 meses dentro de la región de desarrollo; `H_dev,min = max(38; 100/r)` meses y cada ventana prospectiva `L ≥ k·30/r` meses, con `r` trades/mes y `k ≥ 1` (CR-023).  
**Fuentes:** REQ-4027, REQ-4028, REQ-4029; CR-011; CR-023; CR-024  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-DEC-001  
**RESUELTO — ver Módulo 15 (DEC-005):** ventanas Walk-Forward (REQ-G-P16); requisitos estadísticos de aceptación (REQ-G-P17; contabilidad de pruebas concretada por DEC-021/CR-020).

### REQ-G-107
**Descripción:** 7 restricciones absolutas para la IA en el contexto de investigación: (1) no modificar hipótesis congeladas, (2) no modificar criterios de aceptación post-observación de resultados, (3) no usar datos reservados para modificar entrenamiento, (4) no declarar aprobado un experimento por sí misma, (5) no modificar capital asignado, (6) no saltarse controles del Risk Manager, (7) no ejecutar operaciones sin autorización.  
**Fuentes:** REQ-4034  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-108
**Descripción:** Principio rector de investigación: ningún modelo, estrategia o resultado se considera válido únicamente por rentabilidad histórica. La aceptación requiere calidad metodológica + reproducibilidad + robustez + generalización OOS demostrada. La rentabilidad no se presupone: se investiga, se mide, se cuestiona y se valida.  
**Fuentes:** REQ-4036, REQ-4037  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Estado:** APPROVED-DEC-001

### REQ-G-109
**Descripción:** Datos históricos de investigación y snapshot (CR-013, DEC-013; modificado por CR-023, DEC-025). Fuente: Binance REST `GET /api/v3/klines`, BTC/USDT, intervalos `1d`, `4h` y `1h`, desde 2017-08-17, con paginación `limit=1000` iterando con `startTime`. **Snapshot de desarrollo** (`kind: development`): se descarga una vez al iniciar FASE 2, se guarda con timestamp de descarga y es fija para el backtest piloto y el Walk-Forward; contiene solo `train_val`, desde 2017-08-17 hasta el corte de desarrollo `D_dev` (exclusivo), con el corte Train:Validation 5:2 por fecha (REQ-G-P10); actualizar = nueva snapshot versionada; ninguna snapshot de desarrollo contiene datos de una ventana reservada que no esté consumida ni liberada. **Frontera de independencia (CR-023):** OOS = `[B, B + L_oos)` y LOCKBOX = `[B + L_oos, B + L_oos + L_lb)`; `B` es un instante a las 00:00 UTC fijado en el preregistro congelado y publicado en una declaración de frontera (`docs/decisions`) al menos 24 h antes (la publicación en Git es evidencia operativa, no sellado de tiempo certificado); `B` es posterior a `D_dev`, a toda exposición documentada o incierta inventariada y al fin de toda ventana anterior reservada, consumida o contaminada; un único experimento confirmatorio por frontera; ventanas de calendario fijas congeladas antes de `B`; mientras una ventana esté reservada, ninguna hipótesis BTC/USDT puede usar sus datos para desarrollo, selección, calibración ni decisiones experimentales. **Snapshots de evaluación** (`kind: evaluation`): una por ventana, descargada una sola vez tras su cierre (solo velas cerradas), con `context` (`[D_dev, inicio de la ventana)`, solo para calentar indicadores) y la partición (`oos` o `lockbox`), sin `train_val`; `context` y partición sellados (0o000) y autorizados y consumidos juntos; manifiesto con `window_id`, límites, referencia a la snapshot de desarrollo y un digest canónico de contenido por archivo e intervalo; la del LOCKBOX exige la OOS del mismo experimento consumida y que su contexto reproduzca los digests, filas y huecos registrados en el manifiesto de la OOS, sin abrir `oos` (discrepancia ⇒ construcción abortada y LOCKBOX bloqueado). Formato Parquet, cada archivo con su SHA-256 e inmutable una vez hasheado; cada archivo incluye una columna `interval`, y los cortes y límites se fijan una sola vez por fecha y se aplican igual a los tres intervalos. Las características de una ventana pueden leer el `train_val` de desarrollo y su `context` (datos pasados), nunca datos posteriores a la ventana; los resultados solo se generan con velas de la ventana; los cargadores de desarrollo solo aceptan snapshots de desarrollo, y nada de `oos`, `lockbox` ni `context` se carga durante el desarrollo, solo en la evaluación final única. Huecos: NaN sin interpolar; el backtest salta ese periodo. El preregistro (REQ-G-103) registra: hash de cada archivo y versión de la librería que lo escribió, conteo de huecos, tasa de trades observada, modelo de ejecución y declaración de régimen. **Modelo de ejecución (preregistrado):** señal sobre vela cerrada → entrada a la apertura de la vela siguiente, con comisión y slippage; stop tocado dentro de la vela → se llena al precio del stop con slippage 0.10% adverso (REQ-G-P04); hueco (apertura < stop) → se llena a la apertura, también con slippage adverso; mismo criterio para el take-profit; si una vela toca stop y TP se asume que se tocó primero el stop; la autorización humana se asume instantánea y la tolerancia de 0.5% (P20) se aplica como en vivo. **Posiciones al cierre de una ventana OOS o LOCKBOX (CR-023):** una señal cuya entrada caería en una vela posterior al fin de la ventana no se ejecuta; una posición abierta al cierre de la última vela cerrada de la ventana se cierra a ese precio de cierre con slippage adverso de 0.10% (REQ-G-P04) y comisión max(real, 0.10%) (REQ-G-P03), sin leer datos posteriores; si esa vela toca stop o TP prevalecen las reglas anteriores; la operación cuenta en las métricas y en P15 marcada `forced_window_close` y se informa por separado; el Walk-Forward no cambia. **Declaración de régimen:** el preregistro declara que el histórico incluye regímenes distintos al actual; el criterio de aceptación usa todas las ventanas Walk-Forward y las recientes se reportan por separado, salvo que el preregistro congele de antemano una ponderación por recencia. **LOCKBOX consumido:** un LOCKBOX evaluado queda registrado como consumido; en una snapshot nueva no puede volver a usarse como LOCKBOX y solo los datos posteriores al final de la snapshot anterior pueden constituir un LOCKBOX nuevo; un modelo evaluado en un LOCKBOX no se reevalúa en uno que lo contenga; una ventana consumida o contaminada nunca vuelve a ser ventana de evaluación (CR-023). **CR-024 (contrato v1.12):** la snapshot del LOCKBOX exige además que el OOS del mismo experimento conste como resultado favorable autoritativo (REQ-G-104), releído del registro y la evidencia y no de la memoria del proceso; la continuidad del contexto no cambia. **Codificación canónica del resultado (CR-024 §B.1):** tipos cerrados; `float` como objeto etiquetado `{"$f64":"<16 hex>"}` (binary64 big-endian; NaN único canónico; `-0.0` distinto de `0.0`; `±Infinity` rechazado); la clave `$f64` está **reservada**: solo el etiquetado de `float` puede producirla y un `dict` ordinario con la clave `$f64` en cualquier nivel se rechaza, de modo que un objeto con esa clave nunca es ambiguo con un `dict` de usuario. `evaluator_version` es una cadena derivada por el sistema (versión del contrato, `schema` y versiones de python, pandas y pyarrow) que **no** identifica ni garantiza el código de las fuentes del evaluador: dos ejecuciones con el mismo `evaluator_version` pueden provenir de fuentes distintas, por lo que no acredita reproducibilidad de código (hash de fuentes diferido). Las verificaciones de CR-023 §C.9 se amplían como indica CR-024 §B.7–B.8. Detalle de etapas, comprobaciones y contaminación: CR-023 §C y §D.  
**Fuentes:** DEC-013; CR-013 §A, §B.1, §B.2, §B.5, §B.6, §B.7; DEC-005 (P10, P15); REQ-G-103; CR-023 (DEC-025); CR-024  
**Tipo:** FUNCTIONAL  
**Prioridad:** HIGH  
**Estado:** APPROVED-CR-013; modificado por CR-023 (DEC-025) y CR-024  
**Dependencias:** REQ-G-102, REQ-G-103, REQ-G-106  
**Criterios de aceptación:**
- Cada archivo de partición tiene SHA-256 registrado en el preregistro y no se modifica después
- El LOCKBOX no se carga antes de la evaluación final única
- Las fechas de corte son idénticas para los tres intervalos
- Los huecos se marcan como NaN y no se interpolan; el conteo queda en el preregistro
- El modelo de ejecución del backtest está preregistrado y no cambia tras ver resultados OOS
- (CR-023) Ningún cargador de desarrollo acepta una snapshot de evaluación, y ninguna snapshot de desarrollo contiene datos de una ventana reservada
- (CR-023) La snapshot de evaluación del LOCKBOX solo se construye con la OOS consumida y el contexto coincidente con los digests de la OOS; una discrepancia la bloquea

---

## Módulo 11: Módulo Fiscal (trades.db)

### REQ-G-110
**Descripción:** El Fiscal Ledger usa SQLite como motor de base de datos, almacenado en el archivo trades.db. El motor es apropiado para un volumen estimado de menos de 1000 filas por año. No se autoriza otro motor sin aprobación del propietario.  
**Fuentes:** REQ-2003  
**Tipo:** DATA  
**Prioridad:** HIGH

### REQ-G-111
**Descripción:** Esquema de la tabla `trades` (DDL completo según DOC-002): id (PK AUTOINCREMENT), fecha_utc (TIMESTAMP NOT NULL), fecha_mxn (DATE NOT NULL), activo (VARCHAR(10) NOT NULL), accion (VARCHAR(4) NOT NULL CHECK IN 'BUY','SELL'), cantidad (DECIMAL(18,8) NOT NULL), precio_usdt (DECIMAL(18,6) NOT NULL), monto_usdt (DECIMAL(18,4) NOT NULL), tc_mxn_usd (DECIMAL(10,6) NOT NULL), monto_mxn (DECIMAL(18,4) NOT NULL), comisiones_mxn (DECIMAL(10,4) DEFAULT 0), costo_acum_mxn (DECIMAL(18,4)), ganancia_mxn (DECIMAL(18,4)), metodo_costo (VARCHAR(10) DEFAULT 'FIFO'), exchange (VARCHAR(20) DEFAULT 'Binance'), order_id (VARCHAR(64) UNIQUE NOT NULL). Con índices en fecha_mxn, activo y accion.  
**Fuentes:** REQ-2004  
**Tipo:** DATA  
**Prioridad:** HIGH  
**Criterios de aceptación:**
- El DDL se ejecuta sin errores en SQLite
- Se rechazan inserciones con accion distinto de BUY o SELL
- Se rechazan inserciones con order_id duplicado
- Los tres índices existen

### REQ-G-112
**Descripción:** Vistas obligatorias de trades.db: (1) `resumen_anual` — agrupa por año fiscal operaciones SELL y calcula ganancia_neta_mxn (SUM), total_ventas (COUNT), trades_ganancia y trades_perdida; (2) `posicion_abierta` — calcula para cada activo la cantidad neta (BUY - SELL) y costo acumulado en MXN bajo FIFO, solo muestra activos con cantidad_neta > 0.  
**Fuentes:** REQ-2005, REQ-2006  
**Tipo:** DATA  
**Prioridad:** HIGH

### REQ-G-113
**Descripción:** Método de costeo FIFO de forma consistente durante todo el ejercicio fiscal. Tipo de cambio: BCI (Banco de México) del día de la operación. El método FIFO no puede cambiarse a mitad del ejercicio fiscal.  
**Fuentes:** REQ-2002, REQ-2012  
**Tipo:** CONSTRAINT  
**Prioridad:** HIGH  
**RESUELTO — ver Módulo 15 (DEC-006, DEC-004):** fuente del BCI (REQ-G-P07); antigüedad máxima del tipo de cambio (REQ-G-P02). Tipo exacto de serie y días sin publicación: REQ-G-P08 (PENDING).

### REQ-G-114
**Descripción:** Campos críticos para auditoría SAT: fecha_utc, fecha_mxn, activo, accion, cantidad, precio_usdt, tc_mxn_usd, comisiones_mxn, costo_acum_mxn, ganancia_mxn, order_id y metodo_costo. Deben ser completos, correctos y auditables para toda operación registrada. Binance reporta operaciones al SAT vía CARF (desde 2023); el order_id garantiza trazabilidad. La omisión de declaración anual (aunque el ISR sea $0) está sujeta a multa de $2,050–$25,360 MXN.  
**Fuentes:** REQ-2007, REQ-2009, REQ-2010  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

### REQ-G-115
**Descripción:** Marco fiscal de referencia: régimen 605 — Sueldos y Salarios e Ingresos Asimilados a Salarios (DEC-003; régimen 616 del 29/06/2021 al 12/10/2025; régimen 605 con efecto desde el 13/10/2025; aviso al SAT presentado el 17/11/2026, por lo que el registro ante el SAT figura en 616 entre el 13/10/2025 y el 17/11/2026). CONTEXTO_FISCAL_OPERATIVO.md plantea la exención Art. 93 XIX b) LISR ($128,383.92 MXN/año para 2026). La obligación de declaración anual subsiste aunque el ISR sea $0. Declaración ante SAT entre 15 de febrero y 30 de abril en sección 'Enajenación de bienes'.   Si los tickets superan $50,000 MXN, reevaluar el riesgo de PFAE (CONTEXTO_FISCAL_OPERATIVO.md); el máximo extraordinario vigente es $10,000 MXN (REQ-G-010) (CR-008).  
**Condición:** OWNEW_CONTEXT.md establece que el sistema NO debe asumir exención de ISR ni ISR cero; el tratamiento fiscal de las operaciones debe validarse profesionalmente antes de fijar obligaciones, cálculos definitivos o declaraciones (REQ-G-P08). El marco de CONTEXTO_FISCAL_OPERATIVO.md es referencia de diseño.  
**Restricción de implementación:** El Fiscal Ledger debe implementarse con el régimen fiscal como parámetro configurable (no hardcodeado). La lógica de exención/cálculo de ISR debe ser modular y no debe deployarse en producción sin validación professional del régimen correcto.  
**Fuentes:** REQ-2001, REQ-2008, REQ-2009, REQ-1001  
**Tipo:** CONSTRAINT  
**Prioridad:** HIGH  
**PENDING:** Validación con contador especializado en criptomonedas — REQ-G-P08.

---

## Módulo 12: Sistema de Trazabilidad (TRACEABILITY_MATRIX)

### REQ-G-120
**Descripción:** La matriz de trazabilidad demuestra correspondencia completa entre lo especificado, lo implementado y lo efectivamente verificado para cada elemento del sistema. Abarca 10 categorías: requisitos funcionales, no funcionales, políticas, arquitectura, contratos API, seguridad, criterios de aceptación, implementación, verificación y evidencias.  
**Fuentes:** REQ-6001, REQ-6002  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** CRITICAL

### REQ-G-121
**Descripción:** Principios obligatorios de la matriz: (1) Trazabilidad integral — todo elemento tiene referencia de origen; (2) Bidireccionalidad — las relaciones recorren en ambas direcciones; (3) Evidencia objetiva — IMPLEMENTED ≠ VERIFIED; (4) Separación de responsabilidades — implementación y verificación son entidades distintas; (5) Conservación del origen — identificadores TRC-NNN no sustituyen los originales; (6) Fail-Closed documental — falta de información ≠ cumplimiento.  
**Fuentes:** REQ-6003..REQ-6007  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

### REQ-G-122
**Descripción:** Sistema de identificación TRC-NNN: formato estable durante toda la vida del elemento, no reutilizable una vez obsoleto. Los 25 campos mínimos de cada registro incluyen trace_id, source_id, source_document, source_section, source_version, element_type, description, priority, criticality, responsible_component, implementation_reference, verification_method, verification_criteria, test_references, evidence_references, dependencies, related_elements, conflicts, status, implemented_by, verified_by, approved_by, last_verified, change_reference, notes.  
**Fuentes:** REQ-6008, REQ-6009, REQ-6010  
**Tipo:** DATA  
**Prioridad:** HIGH

### REQ-G-123
**Descripción:** Sistema de criticidad de tres niveles: C1 (Crítico) — verificación independiente + aprobación humana obligatoria; C2 (Alto) — verificación independiente; C3 (Ordinario) — verificación automatizada o por agente. Candidatos C1: límites y restricciones de RISK_POLICY.md, autorización de operaciones, gestión de órdenes y posiciones, controles de seguridad sobre credenciales, mecanismos de bloqueo y protección, integridad de registros críticos.  
**Fuentes:** REQ-6012, REQ-6013  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL

### REQ-G-124
**Descripción:** 8 estados de trazabilidad: NOT_STARTED, IN_PROGRESS, IMPLEMENTED, VERIFICATION_PENDING, VERIFIED, FAILED, BLOCKED, NOT_APPLICABLE. Restricciones críticas: IMPLEMENTED ≠ VERIFIED; BLOCKED ≠ cumplimiento; FAILED no puede ocultarse con cambio directo de estado; NOT_APPLICABLE no puede eliminar requisitos incómodos; ningún agente puede declarar VERIFIED un elemento crítico sin su procedimiento de aprobación.  
**Fuentes:** REQ-6017, REQ-6018  
**Tipo:** FUNCTIONAL  
**Prioridad:** CRITICAL

---

## Módulo 13: Seguridad y Gobernanza

### REQ-G-130
**Descripción:** Requisitos de seguridad (1-10): (1) gestión segura de secretos en .env (nunca en código fuente); (2) separación de permisos read/análisis/ejecución; (3) autenticación y autorización de acciones; (4) validación de entradas y salidas; (5) protección contra prompt injection; (6) prohibición de que contenido externo modifique políticas del sistema; (7) registro de cambios en configs críticas; (8) versiones de prompts/modelos/contratos; (9) protección de datos sensibles; (10) auditoría por componente. Los agentes reciben contexto mínimo necesario. Datos externos son información no confiable, nunca instrucciones.  
**Fuentes:** REQ-3042, REQ-3043  
**Tipo:** SECURITY  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Existen pruebas de seguridad e integridad operativa

### REQ-G-131
**Descripción:** Comportamiento conservador ante 11 condiciones de fallo: Risk Manager indisponible (bloquear nuevas operaciones), datos obsoletos (bloquear propuestas ejecutables), datos inconsistentes (bloquear o revisar), agente sin respuesta (registrar, no asumir aprobación), Claude API indisponible (no eludir controles), contrato inválido (rechazar mensaje), autorización expirada (impedir ejecución), Binance indisponible (reconciliar, no asumir estado de orden), límite mensual alcanzado (rechazar nuevas operaciones), duplicidad detectada (evitar doble ejecución), inconsistencia de ejecución (suspender y reconciliar).  
**Fuentes:** REQ-3032  
**Tipo:** CONSTRAINT  
**Prioridad:** CRITICAL  
**Criterios de aceptación:**
- Condiciones de fail-safe probadas

### REQ-G-132
**Descripción:** 14 tipos de eventos obligatorios de auditoría del Risk Manager: actualización del equity, cálculo del presupuesto de riesgo, cálculo del tamaño de posición, validación de operación, rechazo de operación, autorización humana, ejecución de orden, modificación de stop-loss, cierre de posición, pérdida realizada, actualización del drawdown, activación de bloqueo, liberación de bloqueo, errores de sincronización con Binance. Cada evento contiene 12 campos mínimos (ver REQ-5032). Los registros no son modificables retroactivamente por los agentes ejecutores.  
**Fuentes:** REQ-5031, REQ-5032, REQ-5033  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** HIGH

---

## Módulo 14: Requisitos No Funcionales

### REQ-G-140
**Descripción:** 11 requisitos no funcionales del sistema: Modularidad (agentes/proveedores desacoplados), Validación (contratos JSON verificables), Versionado (prompts/modelos/esquemas/estrategias), Auditoría (ciclo completo reconstruible), Seguridad (permisos mínimos), Disponibilidad (manejo explícito de fallos externos), Idempotencia (sin duplicados), Consistencia (validación datos/estados), Escalabilidad (nuevos agentes sin rediseño integral), Costes (medición de consumo API), Reproducibilidad (registro contexto/versiones de cada análisis).  
**Fuentes:** REQ-3047  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** HIGH  
**RESUELTO — ver Módulo 15 (DEC-006, DEC-007, DEC-009):** tiempos de respuesta, límites de consumo, reintentos y disponibilidad (REQ-G-P18; REQ-G-034, REQ-G-095, REQ-G-096).

### REQ-G-141
**Descripción:** Observabilidad del sistema: debe poder responder (a) qué información provocó el análisis, qué agentes participaron, qué modelo/versión usaron, qué información recibió cada agente, qué resultados generaron, qué desacuerdos existieron; (b) qué estrategia/versión produjo la propuesta, qué reglas de riesgo se evaluaron, por qué se aprobó/rechazó, qué autorización permitió ejecutar, qué ocurrió en Binance, cuál fue el resultado neto.  
**Fuentes:** REQ-3044, REQ-3045  
**Tipo:** NON_FUNCTIONAL  
**Prioridad:** HIGH

### REQ-G-142
**Descripción:** Los backtests deben modelar condiciones reales: comisiones, spread, slippage, precio de ejecución, latencia (si relevante), restricciones de órdenes, disponibilidad de liquidez, deslizamientos adversos, capital disponible. Los resultados distinguen rendimiento bruto, costes y neto. Prohibido presentar un backtest como representativo si omite costes relevantes.  
**Fuentes:** REQ-4031  
**Tipo:** CONSTRAINT  
**Prioridad:** HIGH

---

## Módulo 15: Parámetros PENDING (No resolvibles por agentes)

Los siguientes parámetros técnicos están pendientes de definición. Ningún agente puede asumir ni inventar su valor.

| ID | Descripción | Fuente |
|---|---|---|
| REQ-G-P01 | **RESUELTO (DEC-004):** Binance USDT/MXN en tiempo real (sizing); fuente fiscal diferida a P08 — ~~Fuente de conversión USDT/MXN~~ | REQ-5004, REQ-5041 |
| REQ-G-P02 | **RESUELTO (DEC-004):** 5 minutos; excedido = Fail-Closed — ~~Antigüedad máxima aceptable del tipo de cambio~~ | REQ-5004, REQ-5041 |
| REQ-G-P03 | **RESUELTO (DEC-004):** comisión real por API; usar max(real, 0.10%) por lado — ~~Comisión efectiva de Binance (obtener de la cuenta real)~~ | REQ-5008, REQ-5041 |
| REQ-G-P04 | **RESUELTO (DEC-004):** 0.10% — ~~Reserva de slippage (configuración técnica conservadora)~~ | REQ-5008, REQ-5041 |
| REQ-G-P05 | **RESUELTO (DEC-004):** lectura dinámica de exchangeInfo, refresco diario — ~~Precisión de cantidades y precios (stepSize, minQty, minNotional de Binance)~~ | REQ-5009, REQ-5041 |
| REQ-G-P06 | **RESUELTO (DEC-004):** Telegram con botones Aprobar/Rechazar — ~~Mecanismo técnico de aprobación humana (Telegram u otro)~~ | REQ-5027, REQ-5041 |
| REQ-G-P07 | **RESUELTO (DEC-006):** API SIE de Banxico; guardar valor, fecha y serie (tipo exacto y días sin publicación: P08) — ~~API/fuente para obtener BCI automáticamente~~ | REQ-2002 |
| REQ-G-P08 | Validación fiscal con contador especializado en criptomonedas | REQ-1001, REQ-2001 |
| REQ-G-P09 | (cerrado — DEC-003) | REQ-1001 |
| REQ-G-P10 | **RESUELTO (DEC-005; modificado por CR-023/DEC-025):** cronológico; región de desarrollo Train:Validation 5:2 por fecha; OOS y LOCKBOX prospectivas tras la frontera de independencia (REQ-G-109); cada partición de evaluación alcanza P15. Sustituye a «50/20/15/15 cronológico (Train/Val/OOS/LOCKBOX)» (DEC-005 Q7, vigente hasta v1.10) — ~~Porcentajes exactos de división Train/Validation/OOS~~ | REQ-4016, REQ-4035 |
| REQ-G-P11 | **RESUELTO (DEC-005):** Sharpe OOS ≥ 0.8 neto; comparación vs comprar y mantener reportada — ~~Umbrales mínimos de rentabilidad para experimentos~~ | REQ-4033, REQ-4035 |
| REQ-G-P12 | **RESUELTO (DEC-005):** ≤ 20% — ~~Drawdown máximo permitido para experimentos~~ | REQ-4033, REQ-4035 |
| REQ-G-P13 | **RESUELTO (DEC-005):** ≥ 0.10 R neto — ~~Expectancy mínimo~~ | REQ-4033, REQ-4035 |
| REQ-G-P14 | **RESUELTO (DEC-005):** ≥ 1.3 neto — ~~Profit Factor mínimo~~ | REQ-4033, REQ-4035 |
| REQ-G-P15 | **RESUELTO (DEC-005; precisado por CR-023/DEC-025):** ≥ 100 trades Train+Val; ≥ 30 en OOS y en LOCKBOX. **CR-023:** los mínimos se evalúan por ventana prospectiva de calendario fija; sin ampliación, recorte ni reevaluación; insuficiente ⇒ INCONCLUSIVE y ventana consumida; las operaciones `forced_window_close` cuentan y se informan por separado — ~~Tamaño mínimo de muestra~~ | REQ-4033, REQ-4035 |
| REQ-G-P16 | **RESUELTO (DEC-005; concretado por DEC-011/CR-011: embargo 2m entre entrenamiento y prueba, mín. 2 ventanas de prueba, WF dentro de Train+Val):** móvil 24m entrenamiento / 6m prueba / paso 6m — ~~Duración y tamaño de ventanas Walk-Forward~~ | REQ-4027, REQ-4035 |
| REQ-G-P17 | **RESUELTO (DEC-005; concretado por DEC-021/CR-020 y DEC-023/CR-021):** IC bootstrap 95% expectancy > 0 + línea base ingenua + corrección por número de **configuraciones evaluadas** (Deflated Sharpe) con el **conteo experimental congelado** en el preregistro y reconstruido desde el registro de experimentos. Población: todas las familias de investigación sobre BTC/USDT, incluidos los antecedentes declarados. Cuentan las configuraciones cuya evaluación empezó (también rechazadas y abandonadas); los antecedentes con ejecución desconocida cuentan con una **cota conservadora** documentada, que se informa como cota y no como ejecuciones verificadas; las configuraciones planificadas en el preregistro cuentan aunque no se evalúen. No cuentan las ideas, las configuraciones confirmadas como no evaluadas, ni los escenarios puros de costes y las corridas idénticas de reproducibilidad que no seleccionan configuraciones. Una configuración cuenta desde que el inicio autorizado de su evaluación queda registrado de forma duradera, lo que no prueba que se ejecutara; una solicitud rechazada antes de ese registro no cuenta. La repetición nativa de una configuración de un antecedente cuenta como prueba nueva, por prudencia contable. Las pruebas posteriores a la congelación se informan; si influyeron en la selección se suman al conteo de evaluación sin alterar el congelado; si su influencia no puede determinarse con evidencia suficiente de las decisiones (la ausencia de registros de decisión no prueba que no las hubiera), o el conteo es incoherente o incompleto, el resultado es INCONCLUSIVE. **CR-022 (DEC-024):** la influencia se acredita solo con la referencia exacta del par evaluado en `informed_by`; citar una configuración no hace relevantes otras configuraciones, tampoco del mismo experimento, que se clasifican por separado y, si su influencia no puede determinarse, dan INCONCLUSIVE. No hay referencias a experimentos completos. Aumentar el conteo no restaura el carácter confirmatorio perdido. Las cotas solo se reducen con evidencia documental y aprobación del propietario, y solo para preregistros futuros. Detalle: `harness/change_requests/CR-020_contabilidad-pruebas-trials-count.md` §C. **CR-021 (DEC-023):** un inicio cuya durabilidad aún no está confirmada (sin `EVALUATION_PERSISTED`) cuenta de forma conservadora mientras conste en el registro; su pérdida antes de confirmarse no es un subconteo, porque nunca fue duradero ni recibió datos, y puede no detectarse si ocurre antes de cualquier congelación que lo incluya. Toda evaluación con acceso autorizado tiene evidencia contable duradera. Las copias de recuperación no suman. Detalle: `harness/change_requests/CR-021_durabilidad-autorizacion-evaluacion.md` §D.1, §F.1, §F.8. — ~~Requisitos estadísticos de aceptación de modelos ML~~ | REQ-4029, REQ-4035, REQ-4036 |
| REQ-G-P18 | **RESUELTO (DEC-006):** tope $5 USD/mes; IA solo al cierre H4 con setup; timeout 60 s; ciclo ≤ 5 min; sin SLA 24/7; reintentos y fallo de agentes: DEC-007 / REQ-G-034; modelos, invocación y controles de costo: DEC-009 / REQ-G-095, REQ-G-096 (CR-006) — ~~Tiempos máximos de respuesta, límites de consumo API, objetivos de disponibilidad~~ | REQ-3047 |
| REQ-G-P19 | **RESUELTO (DEC-004):** arranque + antes y después de cada ciclo de decisión + cada 5 min con posición abierta — ~~Frecuencia de reconciliación con Binance~~ | REQ-5041 |
| REQ-G-P20 | **RESUELTO (DEC-004):** 0.5% — ~~Tolerancia de desviación de precio~~ | REQ-5041 |
| REQ-G-P21 | **RESUELTO (DEC-005):** solo por drift o revisión semestral; nunca automático — ~~Política de reentrenamiento de modelos ML~~ | REQ-4035 |
| REQ-G-P22 | **RESUELTO (DEC-005):** expectancy últimos 20 trades < límite inferior IC OOS, o PSI > 0.25 → suspensión — ~~Umbrales de degradación del modelo (concept drift)~~ | REQ-4035 |
| REQ-G-P23 | **RESUELTO (DEC-005; ampliado por CR-023/DEC-025):** hash datos+código+parámetros; promoción solo HUMAN_REVIEW → APPROVED. **CR-023:** antes de toda promoción y de cada uso operativo con posible entrada nueva se recalcula la elegibilidad confirmatoria (`confirmatory_status`, `independence_status` y las comprobaciones de CR-023 §C.9, ET-9/ET-10) desde el registro y el almacén de preregistros. Una determinación metodológica válida de no elegibilidad excluye la estrategia o rechaza la promoción (en el Strategy Engine: `NO_SETUP` con `NO_APPROVED_STRATEGY` y `reason_detail = CONFIRMATORY_ELIGIBILITY_LOST` si no queda ninguna elegible). Un fallo técnico que impide determinarla (registro corrupto, evidencia requerida ilegible o incoherente, fallo interno) es un error técnico, no una ausencia ordinaria de estrategia elegible (`ERROR` con `ELIGIBILITY_UNDETERMINED`; promoción rechazada como fallo técnico). Ambos casos bloquean las entradas nuevas y quedan auditados con su clasificación; ninguno impide la gestión protectora obligatoria (stop en el exchange, REQ-G-031; cierres protectores; reconciliación y modo seguro, REQ-G-032 y REQ-G-P26) ni el cierre de las posiciones existentes, incluidas sus señales de salida. Los registros APPROVED históricos se conservan sin cambios; la pérdida de elegibilidad no es un estado nuevo. **CR-024:** la aprobación HUMAN_REVIEW → APPROVED (ET-8) exige los `evaluation_hash` de OOS y LOCKBOX verificados contra el marcador y la evidencia, con resultados `RESULT_VALID` favorables autoritativos; un hash ausente, no verificable o de un resultado no autoritativo impide la aprobación (Fail-Closed); ~~el recálculo de ET-9/ET-10 no cambia~~ (enmendado por CR-025: ET-9 y ET-10 incorporan V9). **CR-025 (contrato v1.13):** ET-9 y ET-10 añaden V9 (integridad autoritativa ligada a la aprobación): los resultados OOS y LOCKBOX deben seguir válidos, favorables y ligados a `approval_binding` (registro, no texto de decisión); cualquier fallo es técnico: promoción rechazada como fallo técnico (ET-9) o `ERROR`/`ELIGIBILITY_UNDETERMINED` sin entradas nuevas (ET-10); un APPROVED sin ligadura es técnico salvo que conste en `HISTORICAL_APPROVALS` (cerrado, inicialmente vacío). La gestión protectora (REQ-G-031, REQ-G-032, REQ-G-P26) y las señales de salida no se ven afectadas. ET-10 en el Strategy Engine queda diferido a B9. Detalle: CR-023 §D.8; CR-024 §B.8; CR-025 — ~~Política de versionado y promoción de modelos a producción~~ | REQ-4035 |
| REQ-G-P24 | **RESUELTO (DEC-005):** ninguno adicional (adición de revisión tras 2 meses en DD 5% retirada el 2026-11-18 por redundante con INV-011 y REQ-G-030 criterio 9) — ~~Límites cuantitativos adicionales del Risk Manager~~ | REQ-4035 |
| REQ-G-P25 | **RESUELTO (DEC-006):** JSON en repositorio con esquema y validador — ~~Formato definitivo de almacenamiento de la matriz de trazabilidad~~ | REQ-6010, REQ-6031 |
| REQ-G-P26 | **RESUELTO (DEC-006):** Recuperación ante fallos: reconciliar, modo seguro sin nuevas órdenes, aviso por Telegram, reanudar solo con confirmación del propietario. Stop-loss en Binance: CR-002 (APROBADA, REQ-G-031). Recuperación por estado: REQ-G-038 (CR-005) | REQ-5041, REQ-5021 |

---

## Conflictos Detectados por el Merger

### CONF-004 — Riesgo "1–2%" vs límite "1.5%"
- **Fecha:** 2026-11-13
- **Documentos:** DOC-003 (AI_INTEGRATION.md, sección "Límites operativos") vs DOC-001 (OWNEW_CONTEXT.md) y DOC-005 (RISK_POLICY.md)
- **Descripción:** DOC-003 indica riesgo objetivo "1–2% del capital". DOC-001 y DOC-005 establecen "1.5% máximo" como límite vinculante.
- **Decisión del propietario (DEC-002 §2):** 1.5% máximo vinculante; la referencia "1–2%" es incorrecta.
- **Aplicado en este contrato:** Límite = **1.5%** (REQ-G-013, REQ-G-028 INV-001).
- **Estado:** RESUELTA — 2026-11-15.

---

*Fin de requirements.md*
