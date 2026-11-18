# CR-007 — Alineación del contrato y pruebas de los criterios de aceptación global

**Fecha:** 2026-11-18
**Estado:** APROBADA por el propietario el 2026-11-18 ("APRUEBO CR-007") y aplicada.
**Origen:** Paquete de revisión de G3 (`harness/gates/G3_resumen_contrato.md`, hallazgos H2–H6) y hallazgo H7 detectado al preparar esta CR. El propietario eligió la opción A (CR-007 → verificación adversarial del contrato actual → G3) y pidió definir aquí las pruebas de H6.

**Naturaleza:** corrección y alineación. No cambia ninguna decisión del propietario: lleva al contrato lo ya decidido y corrige referencias.

---

## A. Criterios de aceptación global — numeración y pruebas (H6, H7, H2)

**Problema:**
- **H7:** `test_plan.md` §9 numera AC-01..AC-05 con contenidos que no corresponden a la fuente. En AI_INTEGRATION.md («¿Cuándo se considera terminada la integración de IA?») y en su extracción (DOC-003, REQ-3054..REQ-3069), el AC-01 es «El Orchestrator coordina agentes especializados»; en el plan, AC-01 es «Ciclo completo reproducible». Además, la nota de pendientes cita REQ-3065..REQ-3075, que no son los criterios (REQ-3070..3075 tratan otros temas).
- **H6:** AC-06..AC-16 no tienen casos de prueba.
- **H2:** el actual AC-03 espera que el ciclo «pueda continuar sin ese agente», contrario a DEC-007 (Q21) y REQ-G-034.

**Cambio:** sustituir `test_plan.md` §9 por los 16 casos siguientes, numerados como la fuente. El contenido de los 5 casos actuales se conserva, reubicado en el criterio que le corresponde (indicado en la columna «Reutiliza»).

| AC | Criterio (texto de la fuente) | Fuente | Criticidad |
|---|---|---|---|
| AC-01 | El Orchestrator coordine agentes especializados. | REQ-3054 | C2 |
| AC-02 | Cada agente tenga contratos de entrada y salida versionados. | REQ-3055 | C2 |
| AC-03 | Los mensajes tengan identificadores de correlación y causalidad. | REQ-3056 | C2 |
| AC-04 | Los resultados puedan reconstruirse históricamente. | REQ-3057 | C2 |
| AC-05 | Los agentes no tengan autoridad de ejecución. | REQ-3058 | C1 |
| AC-06 | Decision Synthesis preserve incertidumbre y desacuerdos. | REQ-3059 | C2 |
| AC-07 | Strategy Engine y ML Engine permanezcan diferenciados de los LLM. | REQ-3060 | C2 |
| AC-08 | Risk Manager opere de manera determinista. | REQ-3061 | C1 |
| AC-09 | No exista ejecución sin autorización válida. | REQ-3062 | C1 |
| AC-10 | La asignación de capital permanezca bajo autoridad humana. | REQ-3063 | C1 |
| AC-11 | Las condiciones de fail-safe hayan sido probadas. | REQ-3064 | C1 |
| AC-12 | Binance pueda reconciliar órdenes y ejecuciones. | REQ-3065 | C1 |
| AC-13 | Research, Paper Trading y Live Trading estén separados. | REQ-3066 | C1 |
| AC-14 | Los costes de IA puedan medirse. | REQ-3067 | C2 |
| AC-15 | Los prompts, modelos, estrategias y contratos estén versionados. | REQ-3068 | C2 |
| AC-16 | Existan pruebas de seguridad y de integridad operativa. | REQ-3069 | C1 |

### Casos de prueba

**TC-AC-01 — Orchestrator coordina** (REQ-G-050, REQ-G-051)
- Input: ciclo con STRATEGY_CANDIDATE.
- Expected: el Orchestrator invoca a Market, Macro y Strategy Analyst en Fase 3 y a Decision Synthesis en Fase 4, con el contexto mínimo de cada uno; ningún agente invoca a otro directamente; un ciclo con NO_SETUP no invoca agentes.

**TC-AC-02 — Contratos versionados** (REQ-G-060, REQ-G-064, REQ-G-095)
- Input: una entrada y una salida de cada agente.
- Expected: cada una declara `schema_version`; la salida valida contra el esquema de su versión; una salida con versión desconocida se rechaza como fuera de contrato.

**TC-AC-03 — Correlación y causalidad** (REQ-G-061, REQ-G-062)
- Input: ciclo completo hasta ORDER_FILLED (Paper Trading).
- Expected: todos los eventos comparten `correlation_id`; cada evento distinto del primero tiene `causation_id` que apunta a un evento existente del mismo ciclo.

**TC-AC-04 — Reconstrucción histórica** (REQ-G-062, REQ-G-076, REQ-G-141) — *reutiliza el actual AC-01*
- Input: `correlation_id` de un ciclo terminado.
- Expected: con los registros se reconstruyen datos usados, análisis de cada agente (modelo, prompt, versión), propuesta, decisión del Risk Manager, autorización, órdenes y resultado; los registros no se alteran (TC-SEC-004).

**TC-AC-05 — Agentes sin autoridad de ejecución** (REQ-G-058, REQ-G-059, REQ-G-095)
- Input: (a) salida de un agente que contiene una «orden» o instrucción de ejecutar; (b) inspección de las llamadas a agentes.
- Expected: (a) no produce ninguna orden ni cambio de estado; (b) ningún agente recibe herramientas ni credenciales (TC-AI-002, TC-SEC-002).

**TC-AC-06 — Incertidumbre y desacuerdos preservados** (REQ-G-056, REQ-G-073)
- Input: Market Analyst alcista y Macro Analyst con riesgo alto contradictorio; por separado, un analista con INSUFFICIENT_DATA.
- Expected: la salida de Decision Synthesis registra el desacuerdo (o `DISAGREEMENT`) y la limitación de datos; no presenta la propuesta como consenso; los desacuerdos se muestran en Telegram con la propuesta.

**TC-AC-07 — Motores deterministas separados de los LLM** (REQ-G-057, REQ-G-071)
- Input: (a) Strategy Engine y ML Engine con la misma entrada dos veces; (b) inspección de dependencias.
- Expected: (a) misma salida; (b) ninguno de los dos llama a la API de Claude ni consume salidas de agentes LLM.

**TC-AC-08 — Risk Manager determinista** (REQ-G-016, REQ-G-074) — *reutiliza el actual AC-01*
- Input: misma propuesta, mismo estado y mismos parámetros, evaluada dos veces.
- Expected: resultado, cálculos y motivos idénticos; el Risk Manager no llama a ningún LLM.

**TC-AC-09 — Sin ejecución sin autorización válida** (INV-008, REQ-G-039, REQ-G-075)
- Input: intentos de ejecución (a) sin autorización humana, (b) con autorización vencida, (c) con autorización de otra propuesta, (d) con autorización anulada al reiniciar.
- Expected: ninguna orden enviada en los cuatro casos; cada intento registrado. Complementa TC-INV-008-A/B, TC-AUTH-001 y TC-REC-001/004.

**TC-AC-10 — Capital bajo autoridad humana** (REQ-G-010, REQ-G-011, REQ-G-044)
- Input: (a) salida de un agente que propone aumentar capital o ticket; (b) cambio de capital configurado sin autorización del propietario.
- Expected: (a) sin efecto sobre la configuración; (b) rechazado y registrado; el capital solo cambia con autorización registrada del propietario.

**TC-AC-11 — Condiciones de fail-safe** (REQ-G-029, REQ-G-034, REQ-G-131) — *reutiliza el actual AC-03 con el resultado corregido (H2)*
- Input: (a) Market Analyst devuelve contrato inválido dos veces; (b) Risk Manager no disponible; (c) datos obsoletos; (d) equity desconocido; (e) discrepancia local/Binance.
- Expected: (a) 1 reintento y luego **ciclo sin propuesta** (no continúa sin el agente); (b)–(e) bloqueo de nuevas entradas; en ningún caso se asume aprobación. Complementa TC-INV-012-A/B.

**TC-AC-12 — Reconciliación con Binance** (REQ-G-075, REQ-G-093, REQ-G-P19)
- Input: (a) ejecución parcial; (b) orden enviada y caída antes de la confirmación; (c) posición sin stop en Binance.
- Expected: (a) cantidad local = cantidad ejecutada en Binance; (b) orden adoptada por identificador de cliente, sin duplicado; (c) detectado y tratado según REQ-G-031. Complementa TC-REC-002/006 y TC-STOP-006/007.

**TC-AC-13 — Modos separados** (REQ-G-080..083) — *reutiliza el actual AC-02*
- Input: (a) propuesta aprobada en Research; (b) en Paper Trading; (c) intento de un agente de cambiar a Live Trading.
- Expected: (a) y (b) ninguna orden real en Binance; (c) sin efecto; el cambio de modo solo ocurre con autorización registrada del propietario.

**TC-AC-14 — Costes de IA medibles** (REQ-G-091, REQ-G-096) — *reutiliza el actual AC-04*
- Procedimiento: revisar los registros de llamadas a la API de Claude de un ciclo.
- Expected: cada llamada registra modelo, tokens de entrada, tokens de salida, costo calculado y timestamp; el gasto mensual acumulado coincide con la suma.

**TC-AC-15 — Versionado completo** (REQ-G-076, REQ-G-140) — *reutiliza el actual AC-05*
- Procedimiento: revisar un registro de ORDER_FILLED con su `correlation_id`.
- Expected: contiene las versiones de prompt, modelo LLM, estrategia, contratos JSON y reglas de riesgo.

**TC-AC-16 — Pruebas de seguridad e integridad operativa** (REQ-G-130, REQ-G-032)
- Procedimiento: ejecutar la suite de seguridad (TC-SEC-001..007) y de integridad (TC-REC-001..009, TC-OPS-STATE-001..003).
- Expected: todas en PASS con evidencia registrada antes de G6.

**Asignación de criticidad:** se sustituye la fila «Criterios de Aceptación Global (AC-01..AC-16) | ALTA | C2» de `test_plan.md` §2 por «C1 o C2 según la tabla de esta CR».

## B. Correcciones de forma (H3, H4, H5)

1. **H3:** REQ-G-063 dice «Catálogo inicial de 16 tipos de eventos»; añadir: «ampliado por CR-002..CR-006; catálogo vigente en `api_contracts.md` §2 (31 tipos)».
2. **H4:**
   - Encabezados de los 5 documentos: de «v0.1 — DRAFT — pendiente de verificación adversarial (G2) y aprobación humana (G3)» a «v0.2 — DRAFT — verificado en G2 (2026-11-13); incorpora CR-001..CR-007; pendiente de re-verificación y aprobación humana (G3)».
   - `requirements.md`, Notas del Merger: «245 requisitos» → «224 requisitos (G1)».
3. **H5:** en las notas «PENDING:» dentro de requisitos que remiten a parámetros ya resueltos (P01–P07, P10–P18), sustituir por «RESUELTO — ver Módulo 15 (DEC-004/005/006)». La nota de P08 (REQ-G-115 y relacionadas) **se mantiene PENDING**.

---

## Documentos del contrato afectados

- `implementation/test_plan.md` — §2 (criticidad de AC), §9 completa (TC-AC-01..16).
- `implementation/requirements.md` — REQ-G-063 (H3); Notas del Merger (H4); notas PENDING resueltas (H5).
- Encabezados de `requirements.md`, `architecture.md`, `api_contracts.md`, `data_flow.md`, `test_plan.md` (H4).

## Impacto

- **Arquitectónico:** ninguno.
- **Riesgo:** reduce. El criterio de fail-safe queda alineado con lo decidido; los 16 criterios de cierre de la integración de IA quedan verificables y trazables a la fuente.
- **Siguiente paso tras aprobar:** verificación adversarial independiente del contrato completo (H1) y, después, G3.

## Aprobación

Aprobada el 2026-11-18 con la frase "APRUEBO CR-007". Aplicada en: `test_plan.md` (§2 criticidad de AC; §9 reescrita con TC-AC-01..16 numerados como la fuente), `requirements.md` (REQ-G-063; Notas del Merger 224; 8 notas PENDING marcadas RESUELTO, P08 se mantiene PENDING), encabezados de los 5 documentos a v0.2.
