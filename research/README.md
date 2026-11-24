# research/ — Material de investigación versionado (modo Research)

Trazabilidad: FEAT-015, FEAT-017 (`feature_list.json`); REQ-G-103, REQ-G-104, REQ-G-109; DEC-013, DEC-017, DEC-018.

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
| `DEVIATION` | Desviación del preregistro congelado (REQ-G-103; ORQ-017-01): `deviation_id`, `experiment_id`, `preregistration_sha256` (debe coincidir con el de su PREREGISTERED), `field`, `old`, `new`, `justification`, `after_oos`, `access_log_evidence`, `actor`, `authorizes_change: false`. |

Reglas de las desviaciones (ORQ-017-01):
- Se escriben con el mismo bloqueo exclusivo que `PARTITION_CONSUMED`: la exposición se calcula y el registro se escribe sin que otro proceso pueda intercalar un consumo. La cronología es el **orden del archivo**, no `at_utc`.
- `after_oos` debe coincidir con lo derivable: un consumo anterior del mismo experimento en el archivo o evidencia del registro de accesos copiada en `access_log_evidence`. Si no coincide, el registro es incoherente.
- Registrar una desviación **la documenta; no la autoriza**, no cambia el preregistro congelado ni da autoridad de decisión a la IA (REQ-G-107).
- El carácter confirmatorio se reconstruye desde el registro (`preregistration.confirmatory_status(registry, experiment_id)`) y se consulta en HUMAN_REVIEW. No cambia reglas de aprobación, transiciones ni el evaluador.
- Fail-Closed: registro ilegible o corrupto, `DEVIATION` mal formada (de cualquier experimento), hash distinto del de PREREGISTERED en el mismo experimento, desviación anterior a PREREGISTERED o `after_oos` incoherente → error; nunca se certifica «confirmatorio» por defecto. Las desviaciones válidas de otros experimentos se ignoran.
- Una escritura fallida después de empezar es **incierta** (el registro puede estar presente, ausente o a medias): no se informa éxito y el objeto deja de certificar; hay que reconstruir el estado desde el registro. Una línea a medias deja el registro ilegible para todos (Fail-Closed) hasta su revisión.
- **Requisito pendiente (O4, diferido):** el contenido del preregistro confirmatorio debe poder recuperarse (guardado y versionado) para comprobar su SHA-256 contra el de PREREGISTERED. Hoy solo se guarda el hash.
