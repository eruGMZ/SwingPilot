# CR-020 — Contabilidad de pruebas para la corrección por selección (`trials_count`) y procedencia de antecedentes

**Fecha:** 2026-11-24 (revisión 3, mismo día)
**Estado:** APROBADA por el propietario el 2026-11-24 (revisión 3; DEC-021) y APLICADA **solo contractualmente**: contrato v1.8 (REQ-G-P17, REQ-G-103, REQ-G-104; TC-ML-006 y TC-ML-020..024) y `feature_list.json` v1.17.0 (AC-017-3, AC-017-8, AC-017-13). La implementación de §D, los registros reales de procedencia y la verificación siguen PENDIENTES y requieren autorización expresa. Antes: PROPUESTA (revisiones 1–3).
**Origen:** CONF-010 (divergencia sobre la unidad y la fuente del conteo de pruebas; MEDIUM) y CONF-009 (procedencia de antecedentes; LOW), ambos OPEN en `implementation/conflict_register.md`. D2 es un identificador de revisión de FEAT-017, no una DEC.
**Alcance:** solo la contabilidad de pruebas de REQ-G-P17 y el mecanismo de registro que la soporta. No toca D3–D7: cortes de particiones, SNAP-0001, secuencia de exploración y preregistro, parámetros estadísticos (incluidos la varianza del Sharpe entre pruebas y el umbral del DSR) ni configuración del piloto.
**Historial:** revisión 1 (2026-11-24): propuesta inicial. Revisión 2 (2026-11-24): incorpora las decisiones del propietario de §B.2 y aclara doble conteo, registro duradero, actualización de procedencia, reconstrucción en cada congelación, distinción de resultados y pruebas posteriores. Revisión 3 (2026-11-24): incorpora R1–R4 con las condiciones del propietario (§B.3) y resuelve cuatro ambigüedades contractuales (§B.4).

## A. Problema

1. **Unidad.** DEC-005 Q11 y REQ-G-P17 hablan de «número de experimentos probados»; la política obligatoria (`docs/policies/PROFILE_AND_OPERATIONAL_POLICIES.md:250`) exige registrar «el número de configuraciones probadas» y contemplar el riesgo de selección estadística. El contrato no define «prueba».
2. **Fuente del conteo.** DEC-005 Q11 dice «usando el conteo del preregistro». La implementación usa el conteo vivo del registro al evaluar (`acceptance.py:182`, decisión de QA3-07); el campo `trials_count` del preregistro solo se comprueba por presencia (`preregistration.py:28`).
3. **Qué se cuenta.** `ExperimentRegistry.trials_count()` (`experiments.py:187-189`) cuenta identificadores de experimento (`CREATED` o `ANTECEDENT`), sin distinguir configuraciones, ideas no evaluadas ni ejecución desconocida. Con el registro real devuelve 2.
4. **Procedencia (CONF-009).** El registro no puede representar la resolución D1 (EXP-0001 documentado; ejecución y resultados desconocidos).

## B. Decisiones del propietario incorporadas

### B.1 Dirección metodológica de D2 (2026-11-24)

- Se cuentan configuraciones evaluadas, no identificadores de experimento.
- Cuentan las configuraciones rechazadas y aquellas cuya evaluación empezó y se abandonó.
- Se excluyen las ideas y las configuraciones confirmadas como nunca evaluadas.
- Antecedentes con ejecución desconocida: cota conservadora documentada.
- **Conteo histórico inicial conservador = 8:** 4 evaluaciones documentadas de Mean Reversion H1 (A, B, E1, E2) y 4 configuraciones preregistradas de EXP-0001 (A–D) contadas como cota. **No son 8 ejecuciones verificadas:** las verificadas documentalmente son 4.
- Se excluyen los escenarios puros de sensibilidad de costes y las corridas idénticas de reproducibilidad solo cuando no introducen selección adicional de configuraciones.
- No aprobada: la regla del máximo de ambos conteos.

### B.2 Decisiones para la revisión 2 (2026-11-24)

1. **Población:** todas las familias de investigación sobre BTC/USDT.
2. **Pruebas posteriores:** se conserva el conteo congelado; las pruebas posteriores de otros experimentos se informan sin sumarse automáticamente; las que influyan en la selección del experimento evaluado no pueden ignorarse en silencio; regla de conciliación basada en evidencia; si la influencia no puede determinarse, la evaluación es INCONCLUSIVE; la determinación no se delega en un LLM.
3. **Configuraciones planificadas:** siguen incluidas en el conteo congelado aunque nunca se evalúen. Se distingue el conteo histórico evaluado del conteo experimental congelado conservador.
4. **Cotas históricas:** solo se reducen con evidencia documental y aprobación explícita del propietario; el cambio es prospectivo (preregistros futuros); se conservan los registros históricos y los conteos congelados.
5. **CONF-009:** `ANTECEDENT_PROVENANCE` aprobado como solución propuesta, siempre que las consultas consolidadas distingan el estado original inmutable de la procedencia documental vigente. CONF-009 sigue OPEN hasta su implementación y verificación.
6. **CONF-010:** severidad MEDIUM confirmada.

### B.3 Decisiones R1–R4 (2026-11-24; para incluir en la propuesta)

- **R1:** `candidate_selection_rule` es un campo del preregistro obligatorio, congelado, determinista y reproducible (C.3.4). La regla concreta del piloto queda diferida a D7.
- **R2:** `informed_by` es obligatorio en los registros `DEVIATION` y de selección de candidata **nuevos**. Las referencias deben ser verificables. Un campo vacío no establece independencia. Los registros históricos se conservan sin reescribirse (C.4.2).
- **R3:** un experimento nativo que vuelve a evaluar una configuración de un antecedente cuenta como un par nuevo. Es una decisión contable conservadora, no una afirmación de independencia estadística (C.1).
- **R4:** gramática `AUTORIZA: PROCEDENCIA` con validación estricta de identificador, enteros, coincidencia exacta y evidencia documental, coherente con QA3R2-04 (C.3.1).

### B.4 Ambigüedades resueltas en la revisión 3 (2026-11-24)

1. Una solicitud de evaluación rechazada se distingue de una evaluación cuyo inicio quedó registrado de forma duradera; la solicitud rechazada no se presenta como configuración evaluada (C.3.2).
2. Aumentar `N_eval` no restaura el carácter confirmatorio perdido por una desviación o por incumplir la regla de selección congelada (C.4.2).
3. `CONFIGURATION_EVALUATED` duradero es el límite contable conservador de un inicio de evaluación autorizado, no prueba de ejecución completa; se conserva el Fail-Closed ante persistencia incierta (C.1, C.3.2).
4. Clasificar pruebas posteriores exige evidencia suficiente de las decisiones de selección relevantes; la falta de registros de decisión no prueba que no hubiera decisiones relevantes (C.4.2).

## C. Cambio propuesto

### C.1 Definiciones y conteos

| Término | Definición |
|---|---|
| **Configuración** | Combinación concreta de reglas y parámetros con identificador `config_id`, única dentro de su experimento. Un escenario de costes usado para elegir entre configuraciones es una configuración propia. |
| **Par de prueba** | (`experiment_id`, `config_id`). Es la unidad de conteo: cada par cuenta como máximo una vez. |
| **Configuración planificada** | Configuración listada en un preregistro congelado. |
| **Configuración evaluada** | Par con un registro `CONFIGURATION_EVALUATED` duradero (C.3.2), con independencia del resultado: rechazada, abandonada o completada. El registro duradero es el **límite contable conservador de un inicio de evaluación autorizado**: no prueba que la evaluación se ejecutara ni que se completara (B.4.3). |
| **Solicitud de evaluación rechazada** | Solicitud que no superó las validaciones previas a la escritura duradera (C.3.2). No es una configuración evaluada, no cuenta y no puede presentarse como tal (B.4.1). |
| **Prueba histórica** | Configuración de un antecedente declarado, con clase de evidencia `DOCUMENTED_EVALUATED`, `CONSERVATIVE_BOUND` o `DOCUMENTED_NOT_EVALUATED`. |
| **Cota conservadora** | Conteo de un antecedente con ejecución desconocida: el número de configuraciones documentadas. Se informa siempre como cota, nunca como ejecuciones verificadas. |
| **No cuentan** | Ideas y experimentos sin pares evaluados; configuraciones confirmadas como nunca evaluadas (`DOCUMENTED_NOT_EVALUATED`); escenarios puros de costes y corridas idénticas de reproducibilidad de un par ya contado que no seleccionan configuraciones. |

Conteos, calculados siempre reproduciendo el registro hasta un punto dado (el orden del archivo es la cronología):

| Conteo | Fórmula | Valor inicial |
|---|---|---|
| `H_doc(t)` — histórico evaluado documentado | configuraciones `DOCUMENTED_EVALUATED` de la procedencia vigente de cada antecedente en `t` | 4 (Mean Reversion H1) |
| `H_bound(t)` — cotas conservadoras | configuraciones `CONSERVATIVE_BOUND` de la procedencia vigente en `t` | 4 (EXP-0001) |
| `E(t)` — pares nativos evaluados | pares distintos con `CONFIGURATION_EVALUATED` hasta `t` | 0 |
| `G(t)` — conteo global de pruebas | `H_doc(t) + H_bound(t) + E(t)` | 8 (4 verificadas documentalmente + 4 de cota) |
| `N_pre(X)` — conteo experimental congelado de X | `G(t_freeze) + │P(X) \ E_X(t_freeze)│`, con `P(X)` las configuraciones planificadas de X y `E_X` los pares de X ya evaluados | — |

**Prevención del doble conteo:**
- Las configuraciones planificadas de X entran en `N_pre(X)` solo si su par no estaba ya evaluado al congelar; un par evaluado antes de la congelación ya está en `E(t_freeze)`.
- Cuando X evalúa después una configuración planificada, su par entra en `E` (para preregistros **futuros** de otros experimentos), pero `N_pre(X)` no cambia: ya lo incluía.
- `G(t)` no incluye configuraciones planificadas no evaluadas de otros experimentos: cuentan solo en el `N_pre` de su propio experimento (decisión B.2.3).
- Las corridas repetidas de un mismo par no suman. Un experimento nativo que vuelve a evaluar una configuración de un antecedente es un par distinto y cuenta (R3). Es una decisión contable conservadora, no una afirmación de independencia estadística entre ambas pruebas.

### C.2 Población

Todas las familias de investigación sobre BTC/USDT: experimentos nativos del registro y antecedentes declarados, sin partición por familia (B.2.1).

### C.3 Mecanismo de registro (append-only)

Tipos de registro nuevos en `research/experiments/registry.jsonl`. Los existentes (`CREATED`, `ANTECEDENT`, `TRANSITION`, `PARTITION_CONSUMED`, `DEVIATION`) conservan su significado.

#### C.3.1 `ANTECEDENT_PROVENANCE` (solución de CONF-009)

- **Campos:** `provenance_id`, `experiment_id` (antecedente existente), `documentary_status` (`DOCUMENTED` | `PENDING_DOCUMENTATION`), `execution_status` (`DOCUMENTED_EXECUTED` | `UNKNOWN` | `DOCUMENTED_NOT_EXECUTED`), `configurations` (lista de `{config_id, evidence_class}`), `evidence` (lista de `repositorio@commit:ruta`; no vacía), `decision_ref` (documento `DEC-NNN…md` en `docs/decisions`), `supersedes` (`provenance_id` anterior o `null`), `actor` = propietario.
- **Autorización (R4):** el documento de decisión debe contener la línea exacta `AUTORIZA: PROCEDENCIA <experiment_id> DOCUMENTADAS=<n> COTA=<m>`. No coincide con la gramática actual de `AUTORIZA: EXP-NNNN …`, así que no la amplía ni la debilita. Validación estricta, con los mismos criterios que QA3R2-04:
  - la línea está sola y al inicio de su línea, y se compara con `fullmatch` campo por campo, con igualdad exacta (mayúsculas incluidas); una línea que no siga la gramática no autoriza nada;
  - `<experiment_id>` cumple con `fullmatch` `EXP-[0-9]{4}` o `ANT-[A-Z0-9]+(-[A-Z0-9]+)*` (ASCII, sin espacios ni saltos de línea) y corresponde a un antecedente declarado existente;
  - `<n>` y `<m>` son enteros decimales ASCII sin signo ni ceros a la izquierda (salvo `0`), y deben coincidir exactamente con el número de configuraciones `DOCUMENTED_EVALUATED` y `CONSERVATIVE_BOUND` del registro;
  - `decision_ref` es un nombre `DEC-NNN…md` sin ruta, dentro de `docs/decisions`, que no es un enlace simbólico y se puede leer en UTF-8; si no, se deniega;
  - `evidence` no está vacía y cada elemento cumple `<repositorio>@<commit hexadecimal de 7 a 40 caracteres>:<ruta relativa>`; un registro sin evidencia válida se rechaza. El registro no verifica en línea el repositorio externo; la evidencia citada debe constar en un documento del Harness.
- **Actualización append-only:** un registro nuevo sustituye al anterior **solo para el conteo**, y solo si su `supersedes` apunta al vigente; todos se conservan. Una reducción de `DOCUMENTED_EVALUATED + CONSERVATIVE_BOUND` exige además que cada configuración que baja pase a `DOCUMENTED_NOT_EVALUATED` con evidencia documental citada (B.2.4). Un registro mal formado o con `supersedes` incoherente hace el conteo indeterminado (Fail-Closed).
- **Prospectivo:** el `N_pre` de un experimento ya congelado se recalcula siempre con los registros anteriores a su congelación, así que una actualización posterior no lo cambia.
- **Estado original inmutable:** el registro `ANTECEDENT` y su `state` no se reescriben. La consulta consolidada devuelve campos separados: `original_state` (el del registro `ANTECEDENT`; inmutable), `documentary_status`, `execution_status` y `provenance_id` vigentes, y `provenance_history`. Ningún informe puede presentar `original_state = PENDING_DOCUMENTATION` como la valoración documental vigente (B.2.5).

#### C.3.2 `CONFIGURATION_EVALUATED` (registro duradero antes de evaluar)

- **Campos:** `experiment_id` (nativo, `EXP-NNNN`), `config_id`, `preregistration_sha256` (si existe), `partition` (`train_val`), `actor`.
- **Validaciones previas (antes de escribir):** `experiment_id` nativo válido y existente; `config_id` con formato válido; el estado del experimento, las transiciones y los requisitos de autorización vigentes permiten la evaluación (condición de DEC-021: un estado no terminal no basta como autorización); registro legible; bloqueo obtenido. Si alguna falla, la **solicitud se rechaza**: no se escribe nada, la evaluación no empieza, el par no cuenta y no puede informarse como configuración evaluada (B.4.1).
- **Orden obligatorio:**
  1. Bajo el bloqueo exclusivo del registro: si el par ya está registrado, no se escribe nada (idempotente); si no, se escribe con `fsync`.
  2. Se relee el registro y se comprueba que el par consta.
  3. Solo entonces puede empezar la evaluación: el cargador de `train_val` exige que el par conste en el registro antes de entregar datos para esa configuración.
- **Escritura fallida o incierta:** la evaluación **no empieza** (`PersistenceUncertainError`, como en ORQ-017-01). Si el registro llegó a escribirse, el par cuenta: es conservador. El reintento es idempotente. Un registro ilegible bloquea toda evaluación hasta su conciliación (Fail-Closed). Una escritura incierta no es una solicitud rechazada: solo la relectura decide si el par consta.
- **Significado (B.4.3):** el registro es el límite contable conservador del inicio autorizado de una evaluación. Cuenta desde que es duradero, aunque la evaluación no llegue a ejecutarse, falle o se abandone. No es evidencia de ejecución completa ni de resultados, y ningún informe puede presentarlo así.
- **Configuración no planificada:** si X está congelado y el `config_id` no está en `P(X)`, el registro se escribe igualmente (la prueba cuenta) y se registra un `DEVIATION`. X deja de ser confirmatorio según las reglas vigentes de desviación.

#### C.3.3 Evidencia de la congelación

- La transición a `PREREGISTERED` se escribe dentro del mismo bloqueo en el que se calcula `G(t_freeze)`, y su evidencia añade `trials_accounting` = `{H_doc, H_bound, E, planned_config_ids, planned_new, N_pre, provenance_ids}`.
- La transición se rechaza si el `trials_count` declarado en el preregistro no coincide con el `N_pre` reconstruido, si algún antecedente carece de procedencia válida o si `planned_config_ids` está vacío o repite identificadores.
- Queda en el registro versionado, así que esta verificación no depende de recuperar el contenido del preregistro (O4). El preregistro congelado nunca se modifica.

#### C.3.4 Regla de selección congelada (R1)

- **Campo obligatorio del preregistro:** `candidate_selection_rule`, congelado con el preregistro (forma parte de su SHA-256 y de `DESIGN_FIELDS`), determinista y reproducible. Usa solo configuraciones de `P(X)` y solo resultados de Train+Val de X; no admite entradas externas, juicio humano ni LLM. Formas admitidas, validadas con `fullmatch` al congelar:
  - `PRIMARY <config_id>`: configuración primaria designada de antemano;
  - `ARGMAX <métrica> TIEBREAK <config_id>,<config_id>,…`: la métrica debe estar declarada en `metrics` del preregistro y el desempate enumera todas las configuraciones de `P(X)` exactamente una vez.

  Una regla mal formada, que cite configuraciones fuera de `P(X)` o métricas no declaradas, impide la congelación. La regla concreta del piloto se decide en D7.
- **Registro de la selección:** la transición a `OOS_EVALUATION` añade a su evidencia `selected_config_id`, `selection_inputs_sha256` (SHA-256 del archivo de resultados de Train+Val de X usado por la regla, conservado en el repositorio de investigación) e `informed_by` (C.4.2).
- Cambiar la regla o seleccionar una configuración distinta de la que da la regla es una desviación de un campo de diseño: el experimento deja de ser confirmatorio.

### C.4 Reglas de conciliación (sin LLM)

Todas son deterministas y se calculan solo a partir del registro, del preregistro congelado vinculado por su SHA-256 y de los resultados registrados de X. Ningún paso usa un LLM ni juicio no reproducible.

#### C.4.1 Conteo congelado

1. **Reconstrucción.** El evaluador recalcula `H_doc`, `H_bound`, `E` y `N_pre` con los registros anteriores a la transición `PREREGISTERED` de X y los compara con `trials_accounting`. Si no coinciden → INCONCLUSIVE (`TRIALS_COUNT_INCONSISTENT`).
2. **Uso.** El DSR usa `N_pre`, o `N_eval` si C.4.2 lo exige, nunca el conteo vivo.
3. **Configuraciones planificadas no evaluadas:** `N_pre` no baja (B.2.3).
4. **Configuraciones no planificadas evaluadas:** desviación (C.3.2). El veredicto es INCONCLUSIVE porque el experimento ya no es confirmatorio; el par cuenta igualmente en `G` para preregistros futuros.
5. **Selección distinta de la regla congelada:** desviación de un campo de diseño (C.3.4). El veredicto es INCONCLUSIVE.

#### C.4.2 Pruebas posteriores a la congelación

- **Definiciones:**
  - **Prueba posterior** `T`: un registro `CONFIGURATION_EVALUATED` de otro experimento `Y ≠ X`, escrito después de la transición `PREREGISTERED` de X.
  - **Puntos de decisión de X:** sus registros `DEVIATION` y su selección de candidata (`selected_config_id` en la transición a `OOS_EVALUATION`).
  - **`informed_by` (R2):** obligatorio en todo registro `DEVIATION` y de selección de candidata **nuevo**. Es la lista de pares (`experiment_id`, `config_id`) o de `provenance_id` cuyos resultados se consultaron; puede estar vacía. Cada referencia debe ser verificable: tiene que existir en el registro y ser anterior al registro que la cita. Una referencia inexistente o posterior hace que se rechace la escritura. Los registros `DEVIATION` históricos sin este campo se conservan sin reescribirse y se tratan como «`informed_by` ausente».
- **Reproducibilidad:** un punto de decisión es reproducible si el evaluador lo recalcula exactamente con la regla congelada (C.3.4) y el archivo de resultados de X cuyo SHA-256 coincide con `selection_inputs_sha256`. Una desviación nunca es reproducible por definición.
- **Evidencia suficiente de las decisiones (B.4.4):** la falta de registros de decisión no prueba que no hubiera decisiones relevantes. Solo puede afirmarse que una prueba posterior es NO RELEVANTE si constan **todas** estas evidencias positivas:
  1. registro legible;
  2. preregistro vinculado por su SHA-256 al de `PREREGISTERED`;
  3. registro de selección presente y reproducible, con el archivo de resultados recuperable y su hash coincidente;
  4. todos los pares evaluados de X están en `P(X)`;
  5. todos los puntos de decisión de X posteriores a `T` tienen `informed_by` válido.

  Si falta cualquiera, el caso es INDETERMINADO. Las decisiones tomadas fuera del registro y nunca registradas no son detectables por medios deterministas; es el mismo riesgo residual aceptado en ORQ-017-01 y CR-020 no lo amplía ni lo resuelve.
- **Clasificación de cada `T`:**

| Caso | Evidencia | Clase | Efecto |
|---|---|---|---|
| 1 | Constan las cinco evidencias anteriores y ningún punto de decisión de X posterior a `T` es una desviación ni cita `T` | **NO RELEVANTE** | Se informa en `trials_after_freeze`; `N_pre` no cambia |
| 2 | Algún punto de decisión de X posterior a `T` cita en `informed_by` el experimento o el par de `T` | **RELEVANTE** | `N_eval = N_pre + │pares relevantes│`; `N_pre` se conserva y se informan ambos; el DSR usa `N_eval` |
| 3 | Falta alguna de las cinco evidencias; o algún punto de decisión de X posterior a `T` no es reproducible y no cita `T`; o falta o está mal formado `informed_by` | **INDETERMINADA** | Veredicto INCONCLUSIVE (`SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`) |

- `informed_by` vacío no prueba la independencia (R2): una lista vacía en una decisión no reproducible posterior a `T` deja el caso como INDETERMINADO.
- **`N_eval` no restaura el carácter confirmatorio (B.4.2):** sumar pares relevantes solo corrige el conteo del DSR. Si X perdió el carácter confirmatorio por una desviación o por incumplir la regla de selección congelada, el veredicto es INCONCLUSIVE con cualquier `N_eval`. Ningún aumento del conteo lo devuelve a ELIGIBLE_FOR_HUMAN_REVIEW.

#### C.4.3 Evidencia incompleta

Cualquiera de estos casos → INCONCLUSIVE (Fail-Closed), nunca ELIGIBLE_FOR_HUMAN_REVIEW:
- registro ausente, ilegible o corrupto;
- procedencia ausente, mal formada o con `supersedes` incoherente;
- `trials_accounting` ausente o mal formado;
- `selected_config_id` o `selection_inputs_sha256` ausentes, o archivo de resultados irrecuperable o con hash distinto;
- `informed_by` ausente en un punto de decisión posterior a una prueba posterior, o con referencias no verificables.

### C.5 Resultados distintos (sin cambiar transiciones)

| Concepto | Qué es | Efecto |
|---|---|---|
| **Veredicto INCONCLUSIVE del evaluador** | Salida del evaluador de aceptación (`acceptance.py`): con la evidencia disponible no puede afirmarse ni rechazarse el cumplimiento | No cambia por sí solo el estado del experimento en el registro |
| **No elegibilidad para aprobación** | Consecuencia de cualquier veredicto distinto de ELIGIBLE_FOR_HUMAN_REVIEW: no se cumplen los requisitos estadísticos de REQ-G-P17 | Ya contractual: «sin cualquiera de ellos no se aprueba» (TC-ML-006). El propietario no puede aprobar contra ese criterio |
| **Revisión humana de incidencias** | Conciliación por el propietario de una escritura incierta, un registro ilegible, una incoherencia de conteo o un caso INDETERMINADO | Condición operativa como la de ORQ-017-01: el experimento afectado no avanza hasta conciliarla. Es distinta del estado `HUMAN_REVIEW` del ciclo de vida |
| **Estado terminal `INCONCLUSIVE` del registro** | Estado del ciclo de vida de REQ-G-104 | Solo mediante las transiciones vigentes |

**Sin cambios en las transiciones:** CR-020 no añade estados ni modifica la máquina de 12 estados de REQ-G-104, `OWNER_DECIDED` ni REQ-G-107. Que el evaluador bloquee en código la transición a `APPROVED` no se propone aquí.

### C.6 Texto contractual propuesto

**`requirements.md` Módulo 15, fila REQ-G-P17** (columna Descripción):
> **RESUELTO (DEC-005; concretado por DEC-0XX/CR-020):** IC bootstrap 95% expectancy > 0 + línea base ingenua + corrección por número de **configuraciones evaluadas** (Deflated Sharpe) con el **conteo experimental congelado** en el preregistro y reconstruido desde el registro de experimentos. Población: todas las familias de investigación sobre BTC/USDT, incluidos los antecedentes declarados. Cuentan las configuraciones cuya evaluación empezó (también rechazadas y abandonadas); los antecedentes con ejecución desconocida cuentan con una **cota conservadora** documentada, que se informa como cota y no como ejecuciones verificadas; las configuraciones planificadas en el preregistro cuentan aunque no se evalúen. No cuentan las ideas, las configuraciones confirmadas como no evaluadas, ni los escenarios puros de costes y las corridas idénticas de reproducibilidad que no seleccionan configuraciones. Una configuración cuenta desde que el inicio autorizado de su evaluación queda registrado de forma duradera, lo que no prueba que se ejecutara; una solicitud rechazada antes de ese registro no cuenta. La repetición nativa de una configuración de un antecedente cuenta como prueba nueva, por prudencia contable. Las pruebas posteriores a la congelación se informan; si influyeron en la selección se suman al conteo de evaluación sin alterar el congelado; si su influencia no puede determinarse con evidencia suficiente de las decisiones (la ausencia de registros de decisión no prueba que no las hubiera), o el conteo es incoherente o incompleto, el resultado es INCONCLUSIVE. Aumentar el conteo no restaura el carácter confirmatorio perdido. Las cotas solo se reducen con evidencia documental y aprobación del propietario, y solo para preregistros futuros. — ~~Requisitos estadísticos de aceptación de modelos ML~~

**`requirements.md` REQ-G-103**, añadir al final:
> **CR-020:** el preregistro congela la contabilidad de pruebas (REQ-G-P17): conteo histórico documentado, cotas conservadoras, configuraciones nativas ya evaluadas y configuraciones planificadas con su identificador, más una regla determinista y reproducible de selección de la configuración candidata (`candidate_selection_rule`), que solo usa configuraciones planificadas y resultados de Train+Val del propio experimento. No puede congelarse si el conteo no coincide con el reconstruido desde el registro, si algún antecedente carece de procedencia o si la regla está mal formada. Evaluar una configuración no planificada, o seleccionar una candidata distinta de la que da la regla, es una desviación y el experimento deja de ser confirmatorio. Los registros nuevos de desviación y de selección declaran en `informed_by` las pruebas consultadas, con referencias verificables; un campo vacío no establece independencia.

**`requirements.md` REQ-G-104**, añadir:
> **CR-020:** el registro de experimentos conserva, en modo append-only, la procedencia de los antecedentes declarados y el inicio de la evaluación de cada configuración, que debe quedar registrado de forma duradera antes de empezar; si la escritura falla o es incierta, la evaluación no empieza. Ese registro es el límite contable conservador de un inicio autorizado, no prueba de ejecución completa; una solicitud rechazada antes de escribirlo no se registra como evaluada. La procedencia solo se registra con una autorización `AUTORIZA: PROCEDENCIA` validada de forma estricta y evidencia documental. El estado original de un antecedente no se reescribe y las consultas lo distinguen de su procedencia documental vigente. No cambian los estados ni las transiciones.

**`test_plan.md` TC-ML-006**, nuevo resultado esperado:
> se calcula IC bootstrap 95% del expectancy (> 0), comparación con línea base ingenua y corrección por número de configuraciones evaluadas con el conteo congelado y reconstruido (REQ-G-P17, CR-020); sin cualquiera de ellos no se aprueba

**`test_plan.md`, casos nuevos:**
- **TC-ML-020 — Unidad y doble conteo:** ideas y configuraciones no evaluadas no cuentan; rechazadas y abandonadas cuentan; corrida idéntica o escenario puro de costes no suma; escenario de costes usado para seleccionar sí suma; un par planificado y luego evaluado cuenta una sola vez en `N_pre`; un par evaluado antes de congelar no se suma dos veces; la repetición nativa de una configuración de antecedente suma un par nuevo.
- **TC-ML-021 — Procedencia:** append-only; la consulta consolidada separa `original_state` de `documentary_status`; reducción sin decisión o sin evidencia → rechazada; actualización posterior no cambia el `N_pre` de un experimento ya congelado; `supersedes` incoherente → conteo indeterminado. Gramática `AUTORIZA: PROCEDENCIA` (R4): se rechazan identificador inválido o inexistente, enteros con signo, ceros a la izquierda o no ASCII, conteos que no coinciden, línea no exacta o incrustada, decisión con ruta, fuera de `docs/decisions`, enlace simbólico o ilegible, y evidencia vacía o mal formada.
- **TC-ML-022 — Conteo congelado y regla de selección:** congelación rechazada si el `trials_count` declarado no coincide con el reconstruido o si `candidate_selection_rule` está mal formada, cita configuraciones fuera de `P(X)` o métricas no declaradas; el evaluador usa `N_pre` y no el conteo vivo; configuraciones planificadas no evaluadas no bajan `N_pre`; `trials_accounting` alterado → INCONCLUSIVE; selección distinta de la regla → desviación e INCONCLUSIVE.
- **TC-ML-023 — Registro duradero:** solicitud rechazada por validación previa → sin registro, sin evaluación y no cuenta; escritura fallida o incierta → la evaluación no empieza y el cargador no entrega datos; registro presente tras una escritura incierta → cuenta aunque no haya ejecución; reintento idempotente; configuración no planificada → cuenta, `DEVIATION` e INCONCLUSIVE.
- **TC-ML-024 — Pruebas posteriores:** NO RELEVANTE solo con las cinco evidencias positivas (`N_pre` igual, prueba informada); RELEVANTE (`N_eval` = `N_pre` + pares, `N_pre` conservado); INDETERMINADA → INCONCLUSIVE si falta el registro de selección, el archivo de resultados o su hash, o si `informed_by` falta o tiene referencias inexistentes o posteriores; `informed_by` vacío en una desviación posterior → INDETERMINADA; registro `DEVIATION` histórico sin `informed_by` → se conserva sin reescribir y se trata como ausente; un `N_eval` mayor con desviación o selección fuera de la regla sigue siendo INCONCLUSIVE.

**Versión:** v1.7 → **v1.8** en los 5 documentos de `implementation/`.
**Decisión nueva:** DEC-0XX (número al aprobarse), que concreta DEC-005 Q11 sin editarla y contiene las líneas `AUTORIZA: PROCEDENCIA` de los dos antecedentes.

### C.7 Criterios de aceptación afectados (`feature_list.json`, solo tras la aprobación)

- **AC-017-3:** añadir la contabilidad de pruebas congelada y `candidate_selection_rule` a los campos del preregistro.
- **AC-017-8:** «corrección por nº de experimentos que incluye los antecedentes declarados» → «corrección por número de configuraciones evaluadas con el conteo congelado y reconstruido, incluidos los antecedentes declarados (REQ-G-P17, CR-020)»; añadir TC-ML-020..024.
- **AC-017-13:** «los cuenta en la corrección por número de experimentos» → «los cuenta por configuraciones con su clase de evidencia: Mean Reversion H1, 4 evaluadas documentadas; EXP-0001, 4 como cota conservadora, no verificadas (CR-020)».
- Sin cambios de estado de FEAT: FEAT-017 sigue IN_PROGRESS.

## D. Impacto

- **Riesgo y ejecución:** ninguno. Solo investigación, sin órdenes (REQ-G-081). El número de pruebas del DSR pasa de 2 a 8 más las configuraciones planificadas del piloto: el umbral efectivo del Sharpe sube (más conservador).
- **Código (tras la aprobación; IMPL-3):**
  - `src/swingpilot/research/experiments.py`: tipos nuevos; `trials_count()` sustituido por los conteos de C.1, con reproducción hasta un punto; consulta consolidada con `original_state` separado; `trials_accounting` en `PREREGISTERED` dentro del bloqueo; `selected_config_id` e `informed_by` en las transiciones y desviaciones correspondientes.
  - `src/swingpilot/research/preregistration.py`: tipo y desglose de `trials_count`; `candidate_selection_rule`; `informed_by` en `DEVIATION`.
  - `src/swingpilot/research/partitions.py`: el cargador de `train_val` exige el par registrado.
  - `src/swingpilot/research/acceptance.py`: `N_pre`/`N_eval` en lugar de `registry.trials_count()`; motivos `TRIALS_COUNT_INCONSISTENT` y `SUBSEQUENT_TRIAL_INFLUENCE_UNDETERMINED`; métricas del desglose.
  - `research/README.md`: semántica de los tipos nuevos.
- **Datos del registro real (tras la aprobación y con autorización expresa):** dos registros `ANTECEDENT_PROVENANCE`:
  - `ANT-MR-H1`: `DOCUMENTED`, `DOCUMENTED_EXECUTED`, A, B, E1 y E2 como `DOCUMENTED_EVALUATED`. Evidencia: `trading-bot@21c5f25:backtest/docs/REGISTRO_EXPERIMENTOS.md` y `trading-bot@25f0e3f:backtest/REPORTE_FASE0.md`. Su `original_state` `REJECTED` no cambia y no se afirma que se recuperaran los resultados originales.
  - `EXP-0001`: `DOCUMENTED`, `UNKNOWN`, A–D como `CONSERVATIVE_BOUND`. Evidencia: `trading-bot@21c5f25:backtest/experiments/EXP-0001/preregistration.md` y el registro de experimentos de ese commit. Resolución D1.
  - No hay experimentos nativos que migrar.
- **Pruebas:** TC-ML-006 actualizada y TC-ML-020..024 nuevas; se adaptan las pruebas actuales de `trials_count` (`tests/unit/test_research.py`, p. ej. líneas 236, 249, 744-753 y el `FakeReg` de la línea 1069). Cada regresión debe fallar con el código anterior.
- **Conflictos:** al aplicarse e implementarse con verificación, resolvería CONF-010 y CONF-009. La reevaluación obligatoria de CONF-009 antes del cierre formal de FEAT-017 sigue vigente.
- **Dependencias:** el piloto (D7) deberá declarar sus `config_id` planificadas y su regla de selección; el contenido de esa regla no se decide aquí. La varianza del Sharpe entre pruebas y el umbral del DSR siguen en D6.

## E. Alternativas consideradas

- **Contar experimentos (estado actual):** descartada en D2.
- **Contar solo ejecuciones verificadas:** descartada en D2 (no es Fail-Closed con EXP-0001).
- **Máximo de ambos conteos:** no aprobada. La sustituyen C.4.1 y C.4.2.
- **Sumar siempre todas las pruebas posteriores:** descartada (B.2.2); penalizaría experimentos cuya selección congelada no pudo verse afectada.
- **CONF-009 opción C (estado de antecedente nuevo):** no se propone. Mezclaría resultado y documentación en el mismo campo; la opción B, aprobada como solución propuesta, separa ambas dimensiones.

## F. Decisiones abiertas del propietario

Ninguna decisión metodológica abierta dentro del alcance de CR-020. R1–R4 están decididas (§B.3) y las ambigüedades de §B.4 están resueltas en el texto. Queda solo la aprobación final de la CR, que incluye estos detalles de redacción propuestos por el Orquestador sin decisión expresa previa del propietario:

- las dos formas cerradas de `candidate_selection_rule` (`PRIMARY`, `ARGMAX … TIEBREAK …`) de C.3.4;
- los patrones exactos de R4 (identificador de antecedente, formato de commit de la evidencia) de C.3.1;
- la lista de validaciones previas que rechazan una solicitud de evaluación (C.3.2).

Fuera del alcance (sin cambios): la regla concreta de selección del piloto (D7) y D3–D6.

## G. Aprobación

Requiere aprobación explícita del propietario y las decisiones de F. Al aprobarse:
1. Registrar la decisión (DEC-0XX).
2. Aplicar C.6 (contrato v1.8) y C.7 (`feature_list.json`).
3. Implementar D con pruebas de regresión.
4. Con autorización expresa, añadir los dos registros `ANTECEDENT_PROVENANCE` al registro real.
5. Verificar la implementación; solo entonces proponer el cierre de CONF-010 y CONF-009 y registrarlo en `progress.md`.

## H. Aprobación del propietario (2026-11-24)

- **Aprobada:** CR-020 revisión 3 y todas las decisiones metodológicas que recoge (§B), más los tres detalles contractuales de implementación: las formas `PRIMARY` y `ARGMAX` de `candidate_selection_rule`; la validación estricta de identificadores y referencias de procedencia; y las validaciones previas de una solicitud de evaluación. Para estas últimas rige la condición de que la evaluación la permitan el estado, las transiciones y las autorizaciones vigentes del experimento; un estado no terminal no basta (incorporada en §C.3.2).
- **Decisión:** DEC-021 (`docs/decisions/DEC-021_aprobacion-cr020-contabilidad-pruebas.md`), que concreta DEC-005 Q11 sin reescribirla.
- **Autorizado:** solo la aplicación contractual (§G pasos 1 y 2). **No autorizado todavía:** §G pasos 3–5 (implementación, registros reales de procedencia, verificación y cierre de conflictos). Las líneas `AUTORIZA: PROCEDENCIA` irán en una decisión posterior, porque DEC-021 no autoriza escribir esos registros.
- **D2:** resolución metodológica y contractual APROBADA; implementación y verificación PENDIENTES. CONF-009 y CONF-010 siguen OPEN. Estados y transiciones sin cambios.
- **Aprobación de la aplicación contractual (propietario, 2026-11-24):** aprueba la aplicación contractual de CR-020, el contrato v1.8, DEC-021 y `feature_list.json` v1.17.0. Aprueba también de forma expresa la inclusión de REQ-4036 como fuente extraída de la política en REQ-G-P17, y la omisión de las líneas `AUTORIZA: PROCEDENCIA` en DEC-021, que mantiene la autorización separada para los registros reales de procedencia.
- **Limitación de la verificación:** los validadores existentes (`scripts/validate_manifest.py`, `validate_requirements.py` y `validate_gates.py`) comprueban el manifiesto, las extracciones y el estado de los gates; no verifican la corrección semántica del texto del contrato.


## I. Nota de vigencia (2026-11-24, DEC-023)

El texto de esta CR se conserva sin cambios como evidencia aprobada (DEC-021). Desde DEC-023, `harness/change_requests/CR-021_durabilidad-autorizacion-evaluacion.md` (revisión 2) **sustituye** las siguientes obligaciones, sin alterar su significado histórico:
- §C.1, definición de «Configuración evaluada»: el cómputo conservador incluye las líneas `CONFIGURATION_EVALUATED` legibles y válidas mientras consten, deduplicadas por par lógico; la evidencia de toda evaluación con acceso autorizado es duradera (CR-021 §D.1, §F.1, §F.8).
- §C.3: se añade el tipo `EVALUATION_PERSISTED` (CR-021 §D.3).
- §C.3.2, «Orden obligatorio», paso 1 (idempotencia sin escritura) y paso 3 (condición del cargador): sustituidos por CR-021 §D.4 y §D.5.
- §C.3.2, «Escritura fallida o incierta» («Si el registro llegó a escribirse, el par cuenta») y «Significado (B.4.3)»: el cómputo vale mientras el registro conste; su pérdida antes de confirmarse no es un subconteo (CR-021 §F.8, §G.2).
- ORQ-017-01, unicidad de `deviation_id`: un duplicado byte a byte idéntico es una sola desviación lógica; uno distinto es incoherente (CR-021 §D.2, §G.3).

Las demás obligaciones de esta CR siguen vigentes. La implementación de CR-021 está PENDIENTE.
