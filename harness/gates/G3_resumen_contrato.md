# G3 — Resumen del contrato técnico para revisión del propietario

**Fecha:** 2026-11-18
**Preparado por:** Orquestador de Desarrollo (material de apoyo; no es autoridad documental)
**Fuente:** `implementation/` (contrato v0.3, CR-001..CR-008 aplicadas). Secciones 1–3 redactadas sobre v0.1+CR-006; la sección 7 resume el estado tras la opción A.
**Propósito:** facilitar la decisión de G3. No sustituye la lectura del contrato; ante cualquier diferencia, rige el contrato.

---

## 1. Qué aprueba G3

Aprobar G3 significa aceptar el contrato técnico como **referencia vinculante para FASE 2**: lo que se implemente se verifica contra él, y cualquier cambio posterior requiere una solicitud de cambio (CR) con tu aprobación.

G3 **no** autoriza por sí solo el inicio de FASE 2 (requiere además "AUTORIZO INICIO DE FASE 2"), ni operar con dinero real (Live Trading requiere autorización aparte, REQ-G-080/083), ni aprueba TRACEABILITY_MATRIX como documento (DEC-001).

## 2. El contrato en cifras

| Elemento | Cantidad |
|---|---|
| Requisitos extraídos de los 6 documentos fuente | 224 |
| Requisitos globales del contrato (REQ-G) | 100 en 15 módulos + 26 parámetros (P01–P26) |
| Invariantes de riesgo | 12 (INV-001..012) |
| Tipos de evento | 30 |
| Casos de prueba definidos | 85 casos TC + criterios de aceptación globales AC-01..05 (AC-06..16 sin casos definidos, ver H6) |
| Decisiones del propietario incorporadas | DEC-001..DEC-009 |
| Solicitudes de cambio aplicadas | CR-001..CR-006 |
| Conflictos entre documentos | 5 detectados, 5 resueltos |

## 3. Qué dice el contrato, por área

### 3.1 Alcance operativo
- Swing trading de 2 días a 2 semanas, **solo BTC/USDT en Binance Spot**, solo compras (Long), sin apalancamiento, margin, futuros, staking ni otros pares (REQ-G-001..008).
- Temporalidades: D1 contexto, H4 estructura y señal, H1 entrada.
- Máximo **1 posición abierta**, sin promediar a la baja, **máximo 8 operaciones al mes** (referencia, no objetivo).

### 3.2 Capital y riesgo
- Capital inicial **$3,000 MXN**; tickets habituales $500–$5,000 MXN.
- Riesgo por operación **1.5% del equity actual** (~$45 MXN al inicio), incluyendo comisiones (mínimo 0.10% por lado) y slippage (0.10%).
- Tamaño de posición por fórmula determinista; ningún agente puede aumentarlo.
- **Drawdown mensual máximo 5%** (~$150 MXN al inicio) → bloqueo de entradas hasta el mes siguiente.
- **3 pérdidas seguidas** → bloqueo preventivo.
- Ante cualquier dato de riesgo no verificable: **Fail-Closed** (no se abren operaciones).

### 3.3 Cómo se decide una operación (7 fases)
1. Datos de mercado (solo velas cerradas).
2. **Filtro determinista** (Regime, ML, Strategy Engine). Sin candidato → fin, **sin gastar en IA**.
3. Análisis en paralelo: Market, Macro y Strategy Analyst (**Haiku 5.5**).
4. Decision Synthesis (**Sonnet 5.5**) → propuesta o descarte.
5. **Risk Manager determinista** valida los 12 invariantes; si aprueba, el Risk Analyst (Haiku) da su opinión consultiva.
6. **Tu aprobación por Telegram** (vigencia **30 min**) → ejecución.
7. Registro completo y Fiscal Ledger.

La IA nunca aprueba, nunca ejecuta y no tiene credenciales. Tope de **$5 USD/mes** de IA, aviso a $4, sin llamadas si ya no puede haber entrada.

### 3.4 Ejecución y protección
- Stop-loss **colocado en Binance** al ejecutarse la compra; protege aunque SwingPilot esté apagado.
- Si falta el stop: se recoloca; si el precio ya lo cruzó, **cierre a mercado automático**, aviso y revisión manual.
- Cada operación sigue **14 estados** persistidos antes de cada acción; nunca dos órdenes para la misma decisión.

### 3.5 Resiliencia
- Producción en **Laptop B** (Linux Mint 22, encendida siempre); desarrollo e investigación en Laptop A.
- Latido cada 15 min a un **servicio externo**; alerta si pasan 30 min sin latido; reinicio automático.
- Al reiniciar: **modo seguro**, reconciliación con Binance, autorizaciones no enviadas anuladas, reanudación solo con tu confirmación.
- Si cambia la IP pública (p. ej. internet satelital): sin operaciones nuevas hasta que actualices la IP en Binance.

### 3.6 Seguridad
- Claves en `.env`; clave de Binance **sin permiso de retiro** y restringida por IP.
- El bot de Telegram solo acepta tus mensajes; cualquier otro remitente se registra como intento no autorizado.

### 3.7 Investigación y ML
- Ningún modelo entra a producción sin experimento preregistrado y tu aprobación.
- Datos 50/20/15/15 (Train/Val/OOS/LOCKBOX), sin mirar el futuro.
- Umbrales: Profit Factor ≥ 1.3, expectancy ≥ 0.10 R, drawdown ≤ 20%, Sharpe OOS ≥ 0.8, ≥ 100 trades en Train+Val y ≥ 30 en OOS y en LOCKBOX.

### 3.8 Fiscal
- `trades.db` (SQLite), método FIFO, tipo de cambio BCI de Banxico.
- Régimen 605 (DEC-003). **El cálculo fiscal queda bloqueado hasta la validación con contador (P08)**; el registro de operaciones sí se implementa.

### 3.9 Modos y pruebas
- Research → Paper Trading → Live Trading; cada cambio de modo requiere tu autorización.
- Una funcionalidad solo está completa con criterio, implementación, prueba ejecutada y evidencia registrada.

## 4. Hallazgos de esta revisión (antes de aprobar)

| # | Severidad | Hallazgo | Propuesta |
|---|---|---|---|
| H1 | **Alta** | La verificación adversarial de G2 es del 2026-11-13. Desde entonces CR-001..CR-006 cambiaron el contrato de forma sustancial (REQ-G-031..039, 095, 096; flujo reordenado; 3 secciones nuevas de pruebas). **Esos cambios no han pasado por verificación independiente.** | Repetir la verificación adversarial (Verificador independiente, solo lectura) sobre el contrato actual antes de G3. |
| H2 | Media | `test_plan.md` AC-03 dice que, si falla un agente, el ciclo "puede continuar sin ese agente". Contradice DEC-007 (Q21) y REQ-G-034: el ciclo termina sin propuesta. | Alinear AC-03 con REQ-G-034. |
| H3 | Baja | REQ-G-063 habla de "16 tipos de eventos"; el catálogo actual tiene 30 (corregido; ver VER-003). | Actualizar la referencia. |
| H4 | Baja | Los encabezados de los 5 documentos dicen "v0.1, DRAFT, pendiente de verificación (G2)"; requirements.md dice "245 requisitos" (son 224). | Corregir encabezados y cifra. |
| H5 | Baja | 8 notas "PENDING" dentro de requisitos (P01–P07, P10–P18) siguen sin marcar como resueltas, aunque la tabla del Módulo 15 sí las resuelve. | Marcarlas como resueltas con su DEC. |
| H6 | Media | `test_plan.md` §9 solo define casos para AC-01..AC-05; AC-06..AC-16 de AI_INTEGRATION.md (REQ-3065..3075) quedan "PENDING, definir en FASE 2". Son condición de G4. | Aceptarlo como pendiente de FASE 2, o definir sus casos antes de G3 (los textos fuente están en DOC-003). |

H2–H5 son de forma (no cambian decisiones), pero al tocar el contrato requieren CR según la política de cambios. H6 es una decisión tuya: aceptar o no ese pendiente.

## 5. Pendientes que NO bloquean G3

Se resuelven en FASE 2 con datos reales:
- Tipo de orden de stop (stop-limit u OCO) y huecos de precio.
- Formato del identificador de cliente y mecanismo de almacenamiento durable.
- Servicio externo de vigilancia y servicio de IP pública.
- Calibración de `effort` por agente, costo real por ciclo y límite de gasto en consola.

Diferido por ti: **P08** (validación fiscal con contador).

## 6. Opciones para G3

| Opción | Pasos | Comentario |
|---|---|---|
| **A (recomendada)** | CR-007 de alineación (H2–H5, y H6 si decides cerrarlo) → verificación adversarial del contrato actual (H1) → G3 | Apruebas un contrato consistente y verificado. Coste: una sesión de trabajo. |
| B | CR-007 (H2–H5) → G3 | Aceptas explícitamente que CR-001..006 no tienen verificación independiente. |
| C | G3 ahora | H1–H5 quedan registrados como deuda para corregir por CR en FASE 2. |

Frase de aprobación cuando decidas: **"APRUEBO EL CONTRATO TÉCNICO v1.0"**. Al aprobarse se actualiza `gate_status.json` (G3 = PASS, aprobado por el propietario, fecha y evidencia) y los encabezados pasan a v1.0 APROBADO.

---

## 7. Estado tras la opción A (actualizado 2026-11-18)

| Hallazgo | Resolución |
|---|---|
| H1 (cambios sin verificación independiente) | VER-003: re-verificación adversarial del contrato v0.2 (2 verificadores, sin críticos) y verificación de cierre de CR-008 (PASS_WITH_FINDINGS, solo BAJA). |
| H2–H7 | Corregidos en CR-007 (TC-AC-01..16 con numeración de la fuente). |
| Hallazgos de VER-003 (3 ALTA, 12 MEDIA, 10 BAJA) | Corregidos en CR-008; decisiones Q28/Q29 en DEC-010. |
| C-03 (BAJA) | Aplicado en CR-009 (REQ-G-024). |

Cambios relevantes para tu decisión desde la sección 3: contratos completos de los 5 agentes; salida «MANUAL» prohibida; bloqueo de 8 operaciones liberado automáticamente al cambiar de mes; aviso de presupuesto de IA una vez al mes; 5 pruebas de parámetros operativos y 7 de investigación nuevas.
