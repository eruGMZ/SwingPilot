# research/ — Material de investigación versionado (modo Research)

Trazabilidad: FEAT-015, FEAT-017 (`feature_list.json`); REQ-G-103, REQ-G-104, REQ-G-109, REQ-G-P17; DEC-013, DEC-017, DEC-018, DEC-021 (CR-020).

| Ruta | Contenido |
|---|---|
| `snapshots/<id>.json` | Manifiesto de cada snapshot: parámetros de descarga, cortes, filas, huecos, SHA-256 y versiones de librerías. Los Parquet viven fuera de Git en `var/snapshots/<id>/` (DEC-017 Q46). |
| `experiments/registry.jsonl` | Registro append-only de experimentos (12 estados), antecedentes declarados (EXP-0001, Mean Reversion H1), consumos de OOS/LOCKBOX (`PARTITION_CONSUMED`) y desviaciones del preregistro (`DEVIATION`). No se edita a mano. |

Reglas:
- Ninguna snapshot se reescribe; actualizar = nueva snapshot versionada.
- `lockbox.parquet` y `oos.parquet` no se cargan en desarrollo (DEC-018: no evaluar OOS ni LOCKBOX en IMPL-3).
- Crear la snapshot definitiva fija las fechas de corte de forma permanente: requiere indicación del propietario (`python -m swingpilot.research.cli build-snapshot --id <id> --confirm`).

Tipos de registro de `experiments/registry.jsonl`:

| `kind` | Contenido |
|---|---|
| `CREATED`, `ANTECEDENT`, `TRANSITION` | Experimentos, antecedentes declarados y transiciones de estado (REQ-G-104, REQ-G-107). |
| `PARTITION_CONSUMED` | Consumo de OOS/LOCKBOX, anotado antes de leer (QA3-06, QA3R2-03). Fuente de verdad de la exposición (QA3R2-07). |
| `DEVIATION` | Desviación del preregistro congelado (REQ-G-103; ORQ-017-01): `deviation_id`, `experiment_id`, `preregistration_sha256` (debe coincidir con el de su PREREGISTERED), `field`, `old`, `new`, `justification`, `after_oos`, `access_log_evidence`, `actor`, `authorizes_change: false`. Las desviaciones nuevas incluyen `informed_by` (CR-020, R2); las históricas sin ese campo se conservan y se tratan como «ausente». |
| `ANTECEDENT_PROVENANCE` | Procedencia documental de un antecedente (CR-020 §C.3.1): `provenance_id`, `experiment_id`, `documentary_status`, `execution_status`, `configurations` (`config_id`, `evidence_class`), `evidence` (`repo@commit:ruta`), `decision_ref`, `supersedes`, `actor: propietario`. No cambia el estado original del registro `ANTECEDENT`. |
| `CONFIGURATION_EVALUATED` | Inicio duradero de la evaluación de un par (`experiment_id`, `config_id`) sobre `train_val` (CR-020 §C.3.2), escrito ANTES de evaluar. Límite contable conservador de un inicio autorizado, no prueba de ejecución. |
| `EVALUATION_PERSISTED` | Certificación de durabilidad (CR-021, DEC-023): `marker_id`, `experiment_id`, `config_id`, `certifies` (SHA-256 de las líneas exactas de la evaluación y, si no está planificada, de su DEVIATION obligatoria), `actor`. Solo se escribe tras un `fsync` correcto de esa evidencia; debe vincularse a líneas anteriores. Condición del acceso a Train+Val. |

Reglas de las desviaciones (ORQ-017-01):
- Identidad (CR-021 §D.2, sustituye la unicidad de ORQ-017-01): una línea byte a byte idéntica con el mismo `deviation_id` es la misma desviación lógica, con la cronología de su primera aparición; un contenido distinto con el mismo `deviation_id` hace el registro corrupto.
- Se escriben con el mismo bloqueo exclusivo que `PARTITION_CONSUMED`: la exposición se calcula y el registro se escribe sin que otro proceso pueda intercalar un consumo. La cronología es el **orden del archivo**, no `at_utc`.
- `after_oos` debe coincidir con lo derivable: un consumo anterior del mismo experimento en el archivo o evidencia del registro de accesos copiada en `access_log_evidence`. Si no coincide, el registro es incoherente.
- Registrar una desviación **la documenta; no la autoriza**, no cambia el preregistro congelado ni da autoridad de decisión a la IA (REQ-G-107).
- El carácter confirmatorio se reconstruye desde el registro (`preregistration.confirmatory_status(registry, experiment_id)`) y se consulta en HUMAN_REVIEW. No cambia reglas de aprobación, transiciones ni el evaluador.
- Fail-Closed: registro ilegible o corrupto, `DEVIATION` mal formada (de cualquier experimento), hash distinto del de PREREGISTERED en el mismo experimento, desviación anterior a PREREGISTERED o `after_oos` incoherente → error; nunca se certifica «confirmatorio» por defecto. Las desviaciones válidas de otros experimentos se ignoran.
- Una escritura fallida después de empezar es **incierta** (el registro puede estar presente, ausente o a medias): no se informa éxito y el objeto deja de certificar; hay que reconstruir el estado desde el registro. Una línea a medias deja el registro ilegible para todos (Fail-Closed) hasta su revisión.
- **Requisito pendiente (O4, diferido):** el contenido del preregistro confirmatorio debe poder recuperarse (guardado y versionado) para comprobar su SHA-256 contra el de PREREGISTERED. Hoy solo se guarda el hash.

Contabilidad de pruebas (CR-020, DEC-021; REQ-G-P17 v1.8):
- Unidad: par (`experiment_id`, `config_id`) con `CONFIGURATION_EVALUATED`; cada par cuenta una vez. Las ideas y los experimentos sin pares evaluados no cuentan.
- Antecedentes: cuentan las configuraciones `DOCUMENTED_EVALUATED` y `CONSERVATIVE_BOUND` (cota, nunca ejecuciones verificadas) de su procedencia vigente. Un antecedente sin `ANTECEDENT_PROVENANCE` válida hace el conteo **indeterminado** (`TrialsAccountingError`): hoy es el caso del registro real, cuyos registros de procedencia requieren una autorización separada del propietario.
- Procedencia: append-only; cada registro nuevo apunta en `supersedes` al vigente y lo autoriza la línea exacta `AUTORIZA: PROCEDENCIA <id> DOCUMENTADAS=<n> COTA=<m>` de un documento de `docs/decisions`. Una reducción solo pasa configuraciones a `DOCUMENTED_NOT_EVALUATED`; ninguna desaparece.
- Evaluación: `CONFIGURATION_EVALUATED` solo en DEVELOPMENT o VALIDATION, con congelación válida; solicitud rechazada → nada escrito; escritura fallida o incierta → la evaluación no empieza. `PartitionLoader.load_train_val_for_configuration` es la única vía pública a Train+Val y exige el par en la evidencia validada del registro (A2). Configuración no planificada (QA-CR020-01): su DEVIATION obligatoria se valida antes de escribir nada (si no es válida → rechazo sin escritura); si solo consta la evaluación, el par cuenta pero el cargador deniega los datos hasta que conste la DEVIATION validada, y el reintento solo añade la DEVIATION. Es un control de las vías de la aplicación, no del sistema de archivos: `train_val.parquet` no está sellado y puede leerse directamente.
- Durabilidad (CR-021, DEC-023): una evaluación legible cuenta mientras conste (por par lógico), pero el acceso a Train+Val exige un `EVALUATION_PERSISTED` válido. Sin marcador, el reintento escribe copias byte a byte idénticas de la evidencia, hace `fsync` y solo entonces escribe el marcador; con marcador válido, éxito sin escribir. Si falla el `fsync` del marcador, la llamada informa incertidumbre, pero el marcador legible autoriza (la evidencia ya es duradera). Registro corrupto (línea no válida, vacía o que no es un objeto, cola sin salto de línea, duplicado conflictivo, marcador no vinculable) → toda lectura, escritura, acceso y evaluación fallan cerrando; ninguna línea se ignora y el archivo no se modifica ni se repara (P1–P5); la recuperación exige un procedimiento aprobado y autorización humana.
- Congelación: la transición a PREREGISTERED exige `trials_accounting` (H_doc, H_bound, E, planned_config_ids, planned_new, N_pre, provenance_ids), recalculado dentro del bloqueo. La selección de candidata (OOS_EVALUATION) exige `selected_config_id`, `selection_inputs_sha256` e `informed_by`.
- Evaluador: usa `N_pre` reconstruido (o `N_eval` con pruebas posteriores relevantes), nunca el conteo vivo; ver `src/swingpilot/research/trials.py`.
