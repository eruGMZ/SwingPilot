# CR-021 — Durabilidad confirmada como condición de acceso a datos (`EVALUATION_PERSISTED`), vinculada a CR-020

**Fecha:** 2026-11-24 (revisión 2, mismo día)
**Estado:** **APROBADA** por el propietario el 2026-11-24 (revisión 2; **DEC-023**) y APLICADA **solo documentalmente**: contrato v1.9 (REQ-G-P17, REQ-G-104, TC-ML-020, TC-ML-023) y `feature_list.json`. La implementación, la adaptación de pruebas ejecutables y la verificación siguen PENDIENTES y requieren autorización expresa (§L). Antes: PROPUESTA (revisiones 1 y 2; diseño conceptual aceptado provisionalmente, §B.1).
**Historial:** revisión 1 (2026-11-24): propuesta inicial. Revisión 2 (2026-11-24): revisión documental autorizada sobre tres puntos del propietario: R1 (garantía frente al subconteo silencioso, §F.1 y §F.8), R2 (persistencia del marcador y semántica del reintento, §F.4) y R3 (conciliación manual, §F.2 y §F.6). Resumen de cambios en §K.
**Origen:** QA-CR020-03 (`harness/verification/IMPL-3_CR-020_QA_independiente.md` §3, sonda P4) y el bloqueo contractual detectado al intentar corregirlo (2026-11-24). Reproducción: `harness/verification/IMPL-3_QA-CR020-03_reproduccion.py` sobre `fde522c`.
**Vinculada a:** CR-020 (DEC-021; contrato v1.8). Modifica cláusulas de CR-020 §C.1 y §C.3.2, REQ-G-P17, REQ-G-104 y TC-ML-023, y la regla de unicidad de `deviation_id` de ORQ-017-01.
**Alcance:** solo la persistencia del inicio de evaluación (`CONFIGURATION_EVALUATED`), su DEVIATION obligatoria cuando la configuración no está planificada, y la autorización de acceso a Train+Val. No toca D3–D7, el evaluador, la selección, la procedencia, el consumo de OOS/LOCKBOX ni QA-CR020-02, 04, 05, 06, O3 y O4.
**Estado de los conflictos y funcionalidades:** QA-CR020-03 sin resolver; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## A. Problema

1. **Defecto reproducido** (`fde522c`): con `fsync` fallando, el primer intento informa persistencia incierta, pero los reintentos informan éxito sin ningún `fsync` correcto; un objeto de registro nuevo y un proceso separado conceden el acceso a Train+Val; una DEVIATION obligatoria cuyo `fsync` falló, pero que es legible, también desbloquea los datos.
2. **Causa:** el registro solo distingue líneas legibles. Una línea cuyo `fsync` falló es indistinguible, para otro objeto u otro proceso, de una cuyo `fsync` tuvo éxito.
3. **Bloqueo contractual:** una corrección sólida exige (a) un registro que solo se escriba después de un `fsync` correcto, que no existe entre los tipos de CR-020 §C.3; y (b) volver a escribir la evidencia en el reintento, que CR-020 §C.3.2, paso 1, prohíbe («si el par ya está registrado, no se escribe nada (idempotente)»).

## B. Interpretación y requisitos del propietario (2026-11-24)

- **Interpretación adoptada:** una línea legible no es evidencia suficiente de persistencia duradera. La contabilidad conservadora de pruebas y la autorización de acceso a datos son garantías **separadas**.
- **Requisitos:**
  1. Separar la contabilidad conservadora del acceso autorizado por durabilidad confirmada.
  2. Registro append-only `EVALUATION_PERSISTED`, si es la solución mínima sólida.
  3. Modificar la idempotencia para permitir las escrituras de recuperación necesarias sin duplicar evaluaciones lógicas ni conteos.
  4. Conservar el `deviation_id` original en la recuperación: las copias idénticas representan una sola desviación lógica; un contenido distinto con la misma identidad se rechaza.
  5. Evidencia duradera para `CONFIGURATION_EVALUATED` y, cuando aplique, para su DEVIATION obligatoria.
  6. Fail-Closed con objetos de registro nuevos, procesos separados y recuperación tras caídas.
- **Aceptado provisionalmente por el propietario:** la pérdida de un marcador de persistencia como resultado Fail-Closed, siempre que no produzca acceso no autorizado ni subconteo; el éxito falso de `fsync` informado por la infraestructura de almacenamiento como limitación residual, sujeta a verificación en el despliegue.

### B.1 Aceptación provisional del diseño conceptual (2026-11-24)

El propietario acepta **provisionalmente** el diseño conceptual: `EVALUATION_PERSISTED`, copias de recuperación byte a byte idénticas, conservación de las identidades lógicas y cronología de la primera aparición. **No** es la aprobación final de CR-021. Autoriza solo la revisión documental 2 sobre:
- **R1:** reevaluar el invariante I2. Distinguir la pérdida de un intento contado de forma conservadora y nunca autorizado de la pérdida de la evidencia contable de una evaluación con acceso autorizado; definir la garantía exacta de cada caso sin afirmar que la conciliación del conteo congelado detecta toda desaparición; explicar si la pérdida de un intento no confirmado ni autorizado es coherente con la unidad de CR-020 o exige una enmienda explícita.
- **R2:** definir el comportamiento cuando el `fsync` de la evidencia tiene éxito, el marcador es legible y válido y falla el `fsync` del marcador: acceso desde otro proceso, resultado de la operación original, reintento idempotente sin escritura y desaparición posterior del marcador; distinguir la durabilidad de la evidencia de la del marcador, sin reproducir la ambigüedad original de QA-CR020-03.
- **R3:** el propietario acepta provisionalmente diferir el procedimiento de reparación manual, siempre que la corrupción del registro bloquee todo acceso y evaluación, las líneas corruptas no se ignoren en silencio, el archivo original se conserve como evidencia y no se permita ninguna reparación automática destructiva. Cualquier recuperación operativa futura exige un procedimiento aprobado y la autorización humana explícita.

## C. Supuestos del sistema de archivos

La garantía de §D se apoya **solo** en estos supuestos; fuera de ellos no se afirma:

| ID | Supuesto | Fuente o verificación |
|---|---|---|
| S1 | Linux ≥ 4.13: los errores de escritura diferida se informan con `errseq` a todo descriptor abierto antes del error; un `fsync` que devuelve 0 en un descriptor recién abierto garantiza que los datos **escritos por ese descriptor** llegaron al almacenamiento | Núcleo de los equipos del proyecto; verificación en el despliegue (G6, Laptop B) |
| S2 | Sistema de archivos local POSIX con `flock` (ext4, xfs o btrfs); no red ni FUSE | Ya exigido por QA3R2-03 y A2 |
| S3 | El archivo del registro ya existe de forma duradera (está versionado); su creación y la entrada del directorio no forman parte de este protocolo | Registro real versionado en git |
| S4 | El almacenamiento respeta las órdenes de vaciado (cache flush/FUA): no informa éxito de `fsync` falso | **No verificable aquí:** limitación residual aceptada provisionalmente (§I) |
| S5 | Tras un error de escritura diferida, el núcleo puede marcar las páginas como limpias y conservarlas en caché: la línea sigue legible aunque no esté en disco; un `fsync` posterior puede devolver 0 sin haberla escrito | Comportamiento documentado de Linux (caso «fsyncgate», PostgreSQL 2018); motivo de §E |

## D. Cambio propuesto

### D.1 Separación de garantías

| Garantía | Base | Efecto |
|---|---|---|
| **Contabilidad conservadora** (REQ-G-P17) | Toda línea `CONFIGURATION_EVALUATED` **legible y válida**, deduplicada por par lógico | El par cuenta en `E`, `G` y en los `N_pre` que se congelen **mientras la línea conste**, aunque su durabilidad no esté confirmada |
| **Autorización de acceso a Train+Val** (REQ-G-104) | Un `EVALUATION_PERSISTED` válido que certifique la evidencia exacta del par (§D.3) | Sin marcador válido, el cargador deniega, lo anota y no lee |

Las dos garantías tienen alcances distintos (§F.1, invariantes I2a e I2b): la evidencia contable de toda evaluación con acceso autorizado es duradera; un intento no confirmado ni autorizado cuenta mientras conste, pero puede perderse tras una caída, y esa pérdida **no siempre se detecta** (§F.8).

### D.2 Identidad lógica y duplicados

| Tipo | Identidad lógica | Copia idéntica | Contenido distinto con la misma identidad |
|---|---|---|---|
| `CONFIGURATION_EVALUATED` | par (`experiment_id`, `config_id`) | Línea **byte a byte idéntica** a la primera aparición: una sola evaluación lógica; no suma | Registro incoherente → conteo indeterminado (Fail-Closed); conciliación manual |
| `DEVIATION` | `deviation_id` | Línea byte a byte idéntica: una sola desviación lógica | Registro incoherente (Fail-Closed); conciliación manual |
| `EVALUATION_PERSISTED` | `marker_id` | — (cada marcador es único) | `marker_id` repetido → incoherente |

- Las copias de recuperación se escriben con los **bytes leídos** de la línea original, sin volver a serializar, para garantizar la identidad byte a byte (incluido `at_utc`).
- **Cronología:** la de una evaluación o desviación lógica es la de su **primera aparición** en el archivo. Las copias no cambian la posición usada en la clasificación de pruebas posteriores (CR-020 §C.4.2), ni en `after_oos` y en la anterioridad de `informed_by` (ORQ-017-01, R2); solo se validan como idénticas a la primera.

### D.3 Registro `EVALUATION_PERSISTED` (nuevo, append-only)

- **Campos:** `marker_id` (32 hexadecimales, único); `experiment_id` (nativo); `config_id`; `certifies`: lista de `{"kind": "CONFIGURATION_EVALUATED", "line_sha256": …}` y, si la configuración no está planificada, `{"kind": "DEVIATION", "deviation_id": …, "line_sha256": …}`; `actor`; `at_utc`.
- **`line_sha256`:** SHA-256 de los bytes exactos de la línea certificada, sin el salto de línea final.
- **Vinculación:** el marcador es válido solo si, **antes** de él en el archivo, existe una línea del tipo indicado, del mismo par (y, para la DEVIATION, con el `deviation_id` indicado, `field` = `trials_count` y validada por la reproducción de ORQ-017-01) cuyos bytes producen exactamente ese `line_sha256`. Un marcador que no se pueda vincular → registro incoherente (Fail-Closed).
- **Condición de escritura:** solo se escribe después de que el proceso, en la misma operación y bajo el mismo bloqueo, haya escrito las líneas que certifica (originales o copias) **y** haya obtenido 0 de `fsync` en el descriptor con el que las escribió (S1). Nunca se escribe para certificar líneas que el proceso no escribió en esa operación.
- **Significado:** «existe en el archivo una copia de esta evidencia cuyo `fsync` tuvo éxito». No certifica su propia durabilidad (§F.4).

### D.4 Protocolo de inicio y recuperación (bajo el bloqueo exclusivo existente)

1. **Validaciones previas** de CR-020 §C.3.2 y de QA-CR020-01 (incluida la DEVIATION obligatoria construida y validada antes de escribir). Rechazo → nada escrito.
2. **Comprobación de la cola:** si el archivo no está vacío y no termina en salto de línea, el registro está corrupto (§F.2, P1): la lectura común (`records()`) falla, así que no se escribe nada y todo queda bloqueado hasta la conciliación manual. Un `append` uniría la línea nueva a una línea truncada. Como todas las escrituras de `_write` terminan en salto de línea dentro de la misma llamada, una cola sin él solo puede venir de una escritura incompleta.
3. **Si ya existe un marcador válido** para el par que certifica toda la evidencia exigida → no se escribe nada; éxito (idempotente).
4. **Si no:** se escriben, en un descriptor nuevo:
   - la evaluación: la línea nueva si el par no consta; si consta, una **copia idéntica** de su primera aparición;
   - si la configuración no está planificada: la DEVIATION nueva validada (paso 1) si no consta; si consta, una copia idéntica de su primera aparición;
   - `fsync` de ese descriptor. Error → `PersistenceUncertainError`; no se escribe el marcador; la evaluación no empieza.
5. Con `fsync` correcto, se escribe `EVALUATION_PERSISTED` (§D.3) y `fsync`. Error → `PersistenceUncertainError`; no se informa éxito.
6. **Relectura:** solo se informa éxito si el registro releído contiene un marcador válido para el par.

Cada reintento repite 2–6. Con fallos continuos de `fsync`, cada intento añade una copia, nunca un marcador, y el acceso sigue denegado.

### D.5 Cargador

`load_train_val_for_configuration` entrega datos solo si (a) el par está en la evidencia validada (A2), (b) se cumple QA-CR020-01 (DEVIATION validada para un par no planificado) y (c) existe un `EVALUATION_PERSISTED` válido que certifica la evaluación y, si aplica, esa DEVIATION. Todo se calcula desde el archivo en cada llamada; no usa estado del proceso, así que vale igual para objetos nuevos y procesos separados.

## E. Por qué el mecanismo es necesario

1. **Evidencia compartida:** objetos nuevos y procesos separados solo comparten el archivo; un indicador del proceso no sirve (requisito del propietario).
2. **Legible ≠ duradero (S5):** ninguna regla que solo mire líneas legibles distingue un `fsync` correcto de uno fallido.
3. **Volver a llamar a `fsync` no basta (S1, S5):** tras un error, las páginas pueden haberse marcado limpias; un `fsync` posterior, sobre todo en un descriptor nuevo, puede devolver 0 sin haber escrito esos bytes. Solo una escritura nueva seguida de un `fsync` correcto en su descriptor prueba durabilidad: por eso la recuperación **escribe copias**.
4. **Hace falta un testigo persistente posterior:** el éxito del `fsync` solo lo conoce el proceso que lo obtuvo; para que otros lo sepan debe quedar escrito después, condicionado a ese éxito. Es el marcador. Un campo dentro de la propia línea de evidencia no sirve, porque se escribe antes de conocer el resultado.
5. **Alternativas descartadas** (§H): todas dejan la decisión en una línea legible, en estado del proceso o en un segundo origen de verdad.

## F. Por qué es suficiente (bajo S1–S4) y análisis de fallos

### F.1 Invariantes

- **I1 (sin acceso no autorizado):** marcador válido legible ⇒ algún proceso escribió una copia de cada línea certificada y obtuvo 0 de `fsync` en ese descriptor ⇒ (S1) esa copia está en el almacenamiento ⇒ la evidencia es duradera. Por tanto, el acceso solo se concede sobre evidencia duradera, aunque el marcador mismo no lo sea.
- **I2a (sin subconteo de evaluaciones autorizadas):** si en algún momento constó un marcador válido para un par (y, por tanto, pudo concederse el acceso a sus datos), entonces, bajo S1–S4, existe en el almacenamiento una copia duradera de su `CONFIGURATION_EVALUATED` (y de su DEVIATION obligatoria): ninguna caída puede hacer que esa evaluación deje de contarse en silencio. El único modo de perder su evidencia es una corrupción del archivo, que bloquea todo (R3, §F.2), nunca un registro legible sin ella.
- **I2b (intentos no confirmados ni autorizados):** una línea `CONFIGURATION_EVALUATED` legible sin marcador cuenta de forma conservadora **mientras conste**. Puede desaparecer tras una caída (no era duradera). Si desaparece después de que un preregistro congelado la contara, la reconstrucción de ese `N_pre` falla → INCONCLUSIVE (`TRIALS_COUNT_INCONSISTENT`), detectado. Si desaparece **antes** de cualquier congelación que la incluya, la pérdida **no se detecta**: los `N_pre` posteriores se calculan sin ella. La CR **no** afirma que la conciliación del conteo congelado detecte toda desaparición. La garantía para este caso es más débil y se justifica en §F.8.
- **I3 (sin doble conteo):** las copias idénticas son la misma evaluación o desviación lógica (§D.2); `E` cuenta pares lógicos.
- **I4 (append-only):** la recuperación solo añade líneas (copias y marcadores); nunca modifica, trunca ni borra. El historial conserva el original, cada copia y cada marcador.

### F.2 Escrituras parciales y registros JSONL truncados

| Caso | Efecto | Clase |
|---|---|---|
| Línea final truncada (caída durante la escritura, sin `fsync`) | `records()` falla: registro ilegible; toda escritura y todo acceso se bloquean | **Conciliación manual** |
| Línea final completa sin salto de línea | Legible, pero un `append` la corrompería: el paso 2 de §D.4 impide escribir | **Conciliación manual** |
| Hueco o bytes no válidos en medio del archivo tras una caída (página perdida bajo S5 y líneas posteriores duraderas) | Registro ilegible; todo bloqueado | **Conciliación manual** |

**Política ante la corrupción (R3; condiciones del propietario):**

- **P1 — Bloqueo total:** si cualquier línea no es JSON válido, no es un objeto, es incoherente (§F.3), o la cola no termina en salto de línea, el registro se considera corrupto. Todas las operaciones que lo leen fallan cerrando: ninguna escritura (inicio de evaluación, transición, consumo de partición, procedencia, desviación), ningún acceso a Train+Val ni a OOS/LOCKBOX, y el evaluador no emite ELIGIBLE (INCONCLUSIVE o error, nunca un veredicto favorable).
- **P2 — Ninguna línea se ignora en silencio:** ningún lector omite, salta ni «tolera» una línea corrupta, ni siquiera la última; no hay modo de lectura parcial. El error identifica la posición afectada.
- **P3 — El archivo original se conserva como evidencia:** el protocolo nunca reescribe, trunca, renombra ni borra el registro, ni le añade líneas mientras esté corrupto (P1).
- **P4 — Sin reparación automática destructiva:** ningún componente repara, recorta ni reconstruye el registro automáticamente.
- **P5 — Recuperación operativa futura:** solo mediante un procedimiento aprobado por el propietario (con su propia decisión) y su autorización humana explícita para cada aplicación. Ese procedimiento queda **PENDING**, fuera de esta CR. Cualquier propuesta futura deberá conservar el archivo corrupto como evidencia (por ejemplo, continuando en un segmento nuevo) en lugar de modificarlo.

Estado actual frente a esta política: P2–P4 ya se cumplen (las lecturas usan `json.loads` línea a línea y fallan ante cualquier error; ninguna ruta reescribe el archivo). P1 se cumple para las líneas no válidas; la comprobación de la cola sin salto de línea es nueva (§D.4, paso 2). La excepción en lugar de INCONCLUSIVE ante una línea que no es objeto (QA-CR020-05) no se trata aquí: también falla cerrando.

### F.3 Duplicados

Copias idénticas → una entidad lógica (recuperable). Contenido distinto con la misma identidad, marcador no vinculable o `marker_id` repetido → incoherente, Fail-Closed (conciliación manual).

### F.4 Fallo al escribir el marcador o en su `fsync` (R2)

**Dos hechos distintos:**
- **Durabilidad de la evidencia certificada:** la establece el `fsync` correcto del paso 4 de §D.4, **antes** de escribir el marcador. Es la única base de la autorización de acceso.
- **Durabilidad del marcador:** la establecería el `fsync` del paso 5. La CR **no** la exige ni la afirma: el marcador es un testigo de un hecho ya ocurrido, y su contenido es verdadero aunque él mismo no sea duradero.

**Caso: `fsync` de la evidencia correcto, marcador escrito, legible y válido, `fsync` del marcador fallido.**

| Pregunta | Comportamiento definido |
|---|---|
| ¿Puede otro proceso (u objeto nuevo) autorizar el acceso? | **Sí.** Un marcador válido legible solo existe si el `fsync` de la evidencia que certifica tuvo éxito (§D.3): el acceso se concede sobre evidencia duradera (I1). |
| ¿Qué informa la operación original? | **Incertidumbre** (`PersistenceUncertainError`), nunca éxito: una operación de escritura cuyo `fsync` falla no informa éxito. La incertidumbre se refiere a la persistencia del marcador, no a la de la evidencia. La propia llamada no inicia la evaluación. |
| ¿Puede un reintento idempotente informar éxito sin escribir? | **Sí**, si al releer (bajo el bloqueo) encuentra un marcador válido que certifica toda la evidencia exigida. El éxito significa «la evidencia del par es duradera y consta certificada ahora», no «el marcador es duradero». |
| ¿Qué ocurre si el marcador desaparece después (caída)? | El acceso vuelve a denegarse (Fail-Closed, aceptado provisionalmente). La evaluación sigue contándose, porque su evidencia es duradera (I2a). El siguiente reintento no encuentra marcador y repite los pasos 2–6 de §D.4 (copias redundantes pero inocuas y marcador nuevo). Los datos entregados antes de la caída lo fueron sobre evidencia duradera: no hubo acceso no autorizado. |

**Por qué no reproduce la ambigüedad de QA-CR020-03:** el defecto original consistía en tratar una línea legible como prueba de **su propia** durabilidad y conceder acceso o informar éxito sin que ningún `fsync` de esa evidencia hubiera tenido éxito (P4). Aquí, ni el acceso ni el éxito del reintento dependen de la durabilidad de ninguna línea legible no confirmada: dependen de un hecho, el `fsync` correcto de la evidencia, que el marcador solo puede atestiguar si ocurrió (porque se escribe después y condicionado a él). Que el marcador se lea desde la caché no importa: su contenido es verdadero aunque no sea duradero. Con `fsync` fallando de forma continua en el paso 4 nunca hay marcador, nunca hay éxito y nunca hay acceso.

**Relación con el requisito «una operación de persistencia fallida o incierta no autoriza el acceso»:** se cumple en este sentido: lo que autoriza es la operación de persistencia **de la evidencia**, que tuvo éxito; la operación fallida (el `fsync` del marcador) no autoriza nada por sí misma, y su resultado se informa como incierto. Esta lectura requiere la confirmación expresa del propietario (§J, decisión 2). Del mismo modo, el requisito «los fallos continuos de `fsync` mantienen el acceso bloqueado» se cumple para los fallos del `fsync` de la evidencia (paso 4: nunca hay marcador); un fallo que afecte **solo** al `fsync` del marcador, después de un `fsync` correcto de la evidencia, no bloquea el acceso que ese marcador legible certifica.

**Otros fallos del marcador:**
- **Escritura del marcador fallida antes de llegar al archivo:** no hay marcador; acceso denegado; el reintento repite los pasos 2–6. Recuperable.
- **Marcador escrito de forma incompleta (caída a mitad de la línea):** cola truncada o sin salto de línea → registro corrupto, todo bloqueado (§F.2, P1). Conciliación manual.

**Regresión infinita evitada:** exigir la durabilidad del propio marcador requeriría otro marcador posterior, y así sin fin; tampoco serviría un registro de «revocación» escrito por el proceso que vio fallar el `fsync`, porque esa escritura podría fallar igual. La CR no la exige; la pérdida del marcador solo produce denegación.

### F.5 Terminación del proceso y caída del sistema

| Momento | Tras reiniciar | Clase |
|---|---|---|
| Antes del paso 4 | Nada escrito; la solicitud no tuvo éxito; no cuenta | Recuperable (reintento normal) |
| Durante el paso 4, sin `fsync` | Las líneas pueden faltar, estar completas o truncadas. Completas: cuentan mientras consten, sin marcador, acceso denegado, el reintento escribe copias. Faltan: intento no confirmado perdido (I2b, §F.8). Truncadas: §F.2 | Recuperable / manual |
| Tras `fsync` del paso 4, antes del marcador | Evidencia duradera, sin marcador: cuenta, acceso denegado; el reintento escribe copias (redundantes pero inocuas) y el marcador | Recuperable |
| Tras escribir el marcador, antes de su `fsync` | El marcador puede faltar (denegado, reintento) o constar (acceso; evidencia duradera, I1) | Recuperable |
| Original no duradero perdido y copia duradera presente | La primera aparición pasa a ser la copia: cambia la cronología. Para la evaluación: conteo intacto; un `N_pre` congelado que dependía del orden puede volverse incoherente → INCONCLUSIVE. Para la DEVIATION: su `after_oos` puede dejar de coincidir con la cronología → incoherente | **Conciliación manual** si hay incoherencia; si no, recuperable |

### F.6 Condiciones que exigen conciliación manual (resumen)

Registro ilegible (truncado o con hueco); cola sin salto de línea; línea que no es objeto; duplicado conflictivo; marcador no vinculable o `marker_id` repetido; incoherencia de cronología tras perder un original; `N_pre` congelado no reconstruible (incluida la pérdida detectada de un intento no confirmado, I2b); DEVIATION mal formada para el par (QA-CR020-01). Todas son Fail-Closed con la política P1–P5 de §F.2: bloqueo total, ninguna línea ignorada, archivo original conservado, sin reparación automática y recuperación solo con procedimiento aprobado y autorización humana explícita.

### F.7 Condiciones recuperables (resumen)

Evaluación o DEVIATION legible sin marcador; marcador ausente o perdido; fallos repetidos de `fsync` (el acceso sigue denegado mientras persistan); `fsync` del marcador fallido (§F.4); terminación del proceso en cualquier punto que deje líneas completas; pérdida de un intento no confirmado ni autorizado antes de cualquier congelación que lo incluya (I2b: no requiere acción, pero no se detecta; §F.8).

### F.8 Pérdida de un intento no confirmado y unidad contable de CR-020 (R1)

**Los dos casos:**

| Caso | Qué se pierde | Garantía del protocolo |
|---|---|---|
| A. Intento contado de forma conservadora, **nunca autorizado** (legible, sin marcador; el cargador nunca entregó datos por la vía de la aplicación) | Una línea `CONFIGURATION_EVALUATED` no duradera | Cuenta mientras conste. Si un `N_pre` congelado la incluía → INCONCLUSIVE (detectado). Si desaparece antes de cualquier congelación → **pérdida no detectada**; los conteos posteriores no la incluyen |
| B. Evaluación con **acceso autorizado** (constó un marcador válido) | — | Su evidencia contable es duradera (I2a): no puede perderse en silencio bajo S1–S4. Solo una corrupción del archivo la hace inaccesible, y eso bloquea todo (§F.2) |

**Por qué el caso A es admisible.** La corrección por selección (REQ-G-P17) protege frente a configuraciones cuyos resultados pudieron influir en la selección. Un intento del caso A nunca recibió Train+Val por la vía de la aplicación, así que, dentro de los controles de la aplicación, no pudo producir resultados que influyeran en ninguna selección. Su pérdida no reduce el conteo de ninguna configuración que viera datos. Queda fuera de esta garantía el acceso directo al archivo `train_val.parquet`, que no está sellado (limitación de A2 ya aceptada).

**Coherencia con CR-020.** El texto aprobado no es uniforme:
- CR-020 §C.1 («Configuración evaluada: par con un registro `CONFIGURATION_EVALUATED` **duradero**»), B.4.3 y REQ-G-P17 («cuenta desde que el inicio autorizado de su evaluación queda registrado **de forma duradera**») definen la unidad por la durabilidad. Con esa definición, un intento del caso A nunca fue una configuración evaluada, y su pérdida no es un subconteo.
- CR-020 §C.3.2 («Si el registro llegó a escribirse, el par cuenta: es conservador») y TC-ML-023 («registro presente tras escritura incierta → cuenta aunque no haya ejecución») cuentan además la línea legible, y se leen como si ese conteo fuera permanente.

Por tanto, la pérdida del caso A es coherente con la **unidad** de CR-020 (definida por la durabilidad), pero contradice la lectura permanente de §C.3.2 y TC-ML-023. Exige una **enmienda explícita** que diga que el conteo conservador de una línea no confirmada vale mientras conste y que su pérdida antes de confirmarse no es un subconteo (§G.1, §G.2). Sin esa enmienda, la garantía de esta CR sería más débil que lo que el contrato vigente parece prometer.

## G. Cláusulas, criterios y pruebas que requieren modificación (tras la aprobación)

### G.1 Contrato (`implementation/requirements.md`, `implementation/test_plan.md`; v1.8 → v1.9)

| Cláusula | Texto vigente afectado | Cambio propuesto |
|---|---|---|
| REQ-G-P17 (Módulo 15) | «Una configuración cuenta desde que el inicio autorizado de su evaluación queda registrado de forma duradera, lo que no prueba que se ejecutara» | «…queda registrado de forma duradera, lo que no prueba que se ejecutara. Un inicio cuya durabilidad aún no está confirmada cuenta de forma conservadora mientras conste en el registro; su pérdida antes de confirmarse no es un subconteo, porque nunca fue duradero ni recibió datos. Toda evaluación con acceso autorizado tiene evidencia contable duradera. Las copias de recuperación no suman» |
| REQ-G-104 (párrafo CR-020) | «…debe quedar registrado de forma duradera antes de empezar; si la escritura falla o es incierta, la evaluación no empieza» | Añadir: «El acceso a los datos exige un registro `EVALUATION_PERSISTED` válido, escrito solo después del `fsync` correcto de la evidencia exacta que certifica (incluida la DEVIATION obligatoria cuando aplique); la autorización se basa en la durabilidad de esa evidencia, no en la del marcador. La recuperación solo añade copias idénticas y marcadores. Un registro corrupto bloquea todo acceso y toda evaluación; no se ignora ninguna línea, se conserva el archivo y no hay reparación automática: la recuperación exige un procedimiento aprobado y autorización humana explícita» |
| TC-ML-023 | «…escritura fallida o incierta → la evaluación no empieza y el cargador no entrega datos; registro presente tras escritura incierta → cuenta aunque no haya ejecución; reintento idempotente…» | «…escritura o `fsync` de la evidencia fallidos o inciertos → la evaluación no empieza y el cargador no entrega datos, tampoco desde un objeto nuevo ni desde otro proceso; registro legible sin marcador → cuenta una vez mientras conste; reintento con fallos → ni éxito ni acceso; reintento con éxito → copias idénticas y marcador, sin doble conteo; DEVIATION obligatoria incluida en el marcador; `fsync` del marcador fallido → la operación informa incertidumbre, otro proceso puede acceder y un reintento informa éxito sin escribir; marcador perdido → acceso denegado y la evaluación sigue contando; registro corrupto (truncado, sin salto de línea final, línea no válida) → todo bloqueado, archivo intacto…» |
| TC-ML-020 | «…un par evaluado antes de congelar no se suma dos veces» | Añadir: «las copias de recuperación de una evaluación no suman» |

### G.2 CR-020 (anotación de vigencia, sin reescribir el texto aprobado)

- §C.1, definición de «Configuración evaluada» («Par con un registro `CONFIGURATION_EVALUATED` duradero»): pasa a «legible y válido, deduplicado por par lógico».
- §C.3: añadir el tipo `EVALUATION_PERSISTED`.
- §C.3.2, «Orden obligatorio», paso 1 («si el par ya está registrado, no se escribe nada (idempotente)»): sustituido por §D.4 de esta CR. Paso 3 («el cargador … exige que el par conste»): añade el marcador (§D.5).
- §C.3.2, «Escritura fallida o incierta»: el reintento ya no es una no-operación cuando falta el marcador. La frase «Si el registro llegó a escribirse, el par cuenta: es conservador» pasa a «…cuenta de forma conservadora mientras conste; su pérdida antes de confirmarse no es un subconteo» (§F.8).
- §C.3.2, «Significado (B.4.3)»: «Cuenta desde que es duradero» se conserva para las evaluaciones confirmadas; se añade el cómputo conservador de las no confirmadas mientras consten.

### G.3 ORQ-017-01 (semántica de DEVIATION)

- `deviation_id` duplicado → hoy siempre incoherente (`_replay`); pasa a: duplicado byte a byte idéntico = una sola desviación lógica; distinto → incoherente.
- Cronología de `after_oos` e `informed_by`: la de la primera aparición (§D.2).
- La condición operativa de ORQ-017-01 (no continuar tras `DeviationPersistenceUncertain` hasta conciliar) no cambia para las desviaciones de `record_deviation`; esta CR solo añade marcador a la DEVIATION obligatoria de una evaluación.

### G.4 Criterios de aceptación (`feature_list.json`)

Sin cambio de redacción en AC-017-3, AC-017-8 ni AC-017-13. AC-017-8 añade la referencia a CR-021 junto a TC-ML-020 y TC-ML-023. FEAT-017 sigue IN_PROGRESS.

### G.5 Pruebas existentes que cambiarían (con autorización)

| Prueba | Motivo |
|---|---|
| `tests/unit/test_trials_accounting.py::test_tc_ml_023_uncertain_write_blocks_start_record_present_counts` | Afirma que el reintento con el registro legible tiene éxito y deja 1 línea; pasaría a exigir marcador, copia idéntica y una sola evaluación lógica |
| `tests/unit/test_trials_accounting.py::test_tc_ml_023_failed_write_before_bytes_is_uncertain_and_does_not_count` | Debe comprobar además el marcador tras el reintento correcto |
| `tests/unit/test_qa_cr020_01.py` (`valid_unplanned…`, `partial_persistence…`, `planned_configuration…`) | Sus listas de tipos por configuración incluirían `EVALUATION_PERSISTED` y, en la persistencia parcial, la copia |
| `tests/unit/test_research.py::test_tc_ml_010_…` | Cuenta líneas del registro (11 → 12 por el marcador) |
| `tests/unit/test_research.py::test_orq_017_01_chronology_and_duplicate_inconsistencies_fail_closed` (bloque «deviation_id duplicado», l. 672-678) | Añade dos veces la misma DEVIATION y espera «duplicado» (incoherente). Con §D.2, si las dos líneas son idénticas byte a byte serían una sola desviación lógica: el caso debe pasar a contenido distinto con el mismo `deviation_id`, y añadirse el caso idéntico como aceptado |

Pruebas nuevas previstas (sintéticas), con su resultado esperado:

| Grupo | Resultado esperado |
|---|---|
| Reproducción de P4; reintentos fallidos repetidos | Ningún éxito ni acceso mientras falle el `fsync` de la evidencia; una copia por intento; conteo 1 |
| Línea legible tras fallo de `fsync` | Cuenta 1 (I2b); acceso denegado desde el mismo objeto, un objeto nuevo y otro proceso |
| Conciliación duradera | Copias idénticas + marcador; conteo 1; acceso concedido; un reintento posterior no escribe nada |
| DEVIATION obligatoria incierta | Acceso denegado hasta que un marcador certifique evaluación y DEVIATION; una sola desviación lógica |
| `fsync` del marcador fallido (R2) | La operación informa incertidumbre; otro proceso accede; un reintento informa éxito sin escribir; si se elimina el marcador (simulación de pérdida en una copia sintética del archivo), acceso denegado, conteo intacto y el reintento escribe copia y marcador nuevos |
| Pérdida de un intento no confirmado (R1, I2b) | En una copia sintética sin la línea no confirmada: el conteo baja sin error si ninguna congelación la incluía; INCONCLUSIVE (`TRIALS_COUNT_INCONSISTENT`) si un `N_pre` congelado la incluía |
| Evaluación autorizada (I2a) | Tras eliminar en una copia sintética la línea original no duradera, la copia certificada mantiene el conteo |
| Duplicados | Idénticos aceptados como una entidad lógica (evaluación, DEVIATION); conflictivos, marcador no vinculable y `marker_id` repetido → bloqueo |
| Corrupción (R3) | Cola truncada, cola sin salto de línea, línea no válida en medio: todas las operaciones fallan cerrando (escrituras, cargador, evaluador no ELIGIBLE); el archivo queda byte a byte intacto; ninguna lectura omite la línea |
| Conservación | Comportamiento válido, concurrente (6 procesos, 1 evaluación lógica) y de QA-CR020-01 |

Las «pérdidas» se simulan en copias sintéticas del archivo; nunca sobre el registro real. Cada regresión de comportamiento debe fallar con `fde522c`.

### G.6 Código afectado (tras la aprobación)

`src/swingpilot/research/experiments.py` (tipo nuevo; `records()` falla ante una cola sin salto de línea, §F.2 P1; validación de duplicados y marcadores en `accounting`; protocolo de §D.4), `preregistration.py` (`_replay`: duplicados idénticos; `evaluation_evidence_error`: marcador), `partitions.py` (sin cambio de interfaz), `research/README.md`.

## H. Alternativas consideradas

| Alternativa | Motivo del descarte |
|---|---|
| Volver a llamar a `fsync` sin reescribir | No prueba la durabilidad de bytes cuyo `fsync` anterior falló (S5) |
| Indicador en memoria del proceso | No vale para objetos nuevos ni procesos separados |
| Campo de confirmación dentro de la propia línea | Se escribe antes de conocer el resultado del `fsync` |
| Lectura con `O_DIRECT` para comprobar lo que hay en disco | Depende del sistema de archivos (tmpfs no lo admite), no cubre la caché del dispositivo y no es una garantía del contrato |
| Archivo de confirmación aparte (temporal, `fsync`, `rename`, `fsync` del directorio) | Crea un segundo origen de verdad fuera del registro contractual |
| Aceptar QA-CR020-03 como riesgo residual sin cambios | Posible; no cumple la interpretación adoptada por el propietario |

## I. Limitaciones residuales

1. **Éxito falso de `fsync` del almacenamiento (S4):** fuera del alcance; aceptado provisionalmente, sujeto a verificación en el despliegue (G6, Laptop B). Si S4 no se cumple, I1 e I2a dejan de valer.
2. **Durabilidad del propio marcador:** no garantizada (§F.4); su pérdida deniega el acceso sin afectar al conteo (Fail-Closed aceptado provisionalmente). El proceso que vio fallar el `fsync` del marcador informa incertidumbre mientras otros procesos pueden acceder (§F.4).
3. **Pérdida no detectada de intentos no confirmados ni autorizados (I2b, §F.8):** si desaparecen tras una caída antes de cualquier congelación que los incluya, los conteos posteriores no los incluyen y nada lo señala. Admisible porque nunca recibieron datos por la vía de la aplicación; exige la enmienda de §G.1/§G.2.
4. **Acceso directo al archivo `train_val.parquet`:** fuera de la garantía (limitación de A2 ya aceptada); un intento del caso A que leyera los datos por otra vía no queda cubierto.
5. **Crecimiento del registro:** cada reintento con fallo añade una copia; acotado por el número de reintentos.
6. **Reparación de archivos (R3):** truncados, huecos, colas sin salto de línea y duplicados conflictivos bloquean todo hasta una conciliación manual con procedimiento aprobado y autorización humana explícita; el procedimiento queda PENDING (aceptado provisionalmente). Mientras tanto, una sola línea corrupta detiene todo el registro de investigación.
5. **Fuera de alcance:** creación duradera del archivo del registro y de su entrada de directorio (S3); el resto de escrituras del registro (`CREATED`, `TRANSITION`, `PARTITION_CONSUMED`, procedencia, desviaciones de `record_deviation`) conservan su tratamiento actual; las decisiones tomadas fuera del registro.

## J. Decisiones del propietario requeridas

Ya aceptado provisionalmente (§B, §B.1): diseño conceptual; pérdida del marcador como Fail-Closed sin acceso no autorizado ni subconteo; éxito falso de `fsync` como limitación residual; diferir el procedimiento de reparación con las condiciones P1–P5.

Decisiones pendientes:
1. **Aprobación final** de CR-021 (revisión 2), incluida la introducción de `EVALUATION_PERSISTED` y la sustitución del paso 1 de CR-020 §C.3.2.
2. **R2:** confirmar que la autorización se basa en la durabilidad de la evidencia certificada y no en la del marcador; en particular, que otro proceso puede acceder con un marcador legible cuyo `fsync` falló, que la operación original informa incertidumbre y que un reintento informa éxito sin escribir (§F.4).
3. **R1:** confirmar la garantía diferenciada I2a/I2b y aprobar la enmienda explícita de REQ-G-P17, CR-020 §C.3.2 y TC-ML-023 sobre el cómputo conservador «mientras conste» (§F.8, §G.1, §G.2).
4. **R3:** confirmar la política P1–P5, incluida la nueva regla de que una cola sin salto de línea hace el registro corrupto para todas las operaciones (§F.2, §D.4).
5. Confirmar la identidad y los duplicados de §D.2 (byte a byte; cronología de la primera aparición), ya aceptados provisionalmente.
6. Autorizar, por separado, la aplicación contractual (v1.9), la implementación y la modificación de las pruebas de §G.5.
7. Número de la decisión (DEC-0XX) al aprobarse.

## K. Cambios de la revisión 2

| Punto | Secciones | Cambio |
|---|---|---|
| R1 | §D.1, §F.1 (I2 → I2a, I2b), §F.6, §F.7, §F.8 (nueva), §G.1, §G.2, §I.3, §I.4 | Se retira la afirmación de que nunca hay subconteo silencioso. Garantía fuerte para evaluaciones autorizadas (I2a); garantía más débil y explícita para intentos no confirmados (I2b), con su coherencia con CR-020 y la enmienda necesaria |
| R2 | §F.4 (reescrita), §G.1 (TC-ML-023), §I.2 | Durabilidad de la evidencia frente a la del marcador; acceso desde otro proceso, resultado de la operación, reintento sin escritura y pérdida del marcador; por qué no reproduce QA-CR020-03 |
| R3 | §F.2 (política P1–P5), §D.4 paso 2, §F.6, §G.1 (REQ-G-104), §G.6, §I.6 | Bloqueo total ante corrupción, ninguna línea ignorada, archivo conservado, sin reparación automática, recuperación solo con procedimiento aprobado y autorización humana; cola sin salto de línea tratada como corrupción en la lectura común |
| — | §B.1, §J | Aceptación provisional del propietario; decisiones pendientes actualizadas |

Sin mecanismos de almacenamiento adicionales respecto a la revisión 1: el único registro nuevo sigue siendo `EVALUATION_PERSISTED`.

## L. Aprobación del propietario (2026-11-24)

- **Aprobada:** CR-021 revisión 2 y todas las decisiones de §J, en los once puntos que recoge `docs/decisions/DEC-023_aprobacion-cr021-durabilidad-autorizacion.md`: `EVALUATION_PERSISTED`; I2a/I2b con sus enmiendas; cómputo conservador de intentos no confirmados mientras consten, con la posible pérdida no detectada antes de congelar cuando nunca hubo acceso; interpretación R2; incertidumbre de la operación original ante el fallo del `fsync` del marcador, con acceso y reintento idempotente si el marcador sigue legible y válido; denegación si el marcador desaparece, sin eliminar ni duplicar la evidencia; copias idénticas, `deviation_id` e identidades conservadas, cronología de la primera aparición; rechazo Fail-Closed de duplicados conflictivos; política P1–P5 completa, incluida la cola sin salto de línea; conciliación manual diferida sin reparación automática destructiva; limitaciones residuales de §I bajo S1–S4 y sujetas a verificación en el despliegue.
- **Decisión:** DEC-023.
- **Autorizado:** solo la aplicación documental al contrato v1.9, a los criterios de aceptación, a las especificaciones de prueba y a la trazabilidad. **No autorizado todavía:** implementación, adaptación de pruebas ejecutables (§G.5), verificación y cambios en el registro real.
- **Sustitución, no reescritura:** CR-020 se conserva como evidencia aprobada; las obligaciones afectadas (§G.2) quedan sustituidas por esta CR, y así lo indica una nota de vigencia añadida al final de CR-020.
- **Condición de implementación:** demostrar P1 en todas las rutas afectadas de lectura, escritura, acceso y evaluación; comprobar solo el salto de línea final no basta.
- **Estado:** QA-CR020-03 sin resolver; CONF-009 y CONF-010 OPEN; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
