# research/ — Material de investigación versionado (modo Research)

Trazabilidad: FEAT-015, FEAT-017 (`feature_list.json`); REQ-G-103, REQ-G-104, REQ-G-109; DEC-013, DEC-017, DEC-018.

| Ruta | Contenido |
|---|---|
| `snapshots/<id>.json` | Manifiesto de cada snapshot: parámetros de descarga, cortes, filas, huecos, SHA-256 y versiones de librerías. Los Parquet viven fuera de Git en `var/snapshots/<id>/` (DEC-017 Q46). |
| `experiments/registry.jsonl` | Registro append-only de experimentos (12 estados) y antecedentes declarados (EXP-0001, Mean Reversion H1). No se edita a mano. |

Reglas:
- Ninguna snapshot se reescribe; actualizar = nueva snapshot versionada.
- `lockbox.parquet` y `oos.parquet` no se cargan en desarrollo (DEC-018: no evaluar OOS ni LOCKBOX en IMPL-3).
- Crear la snapshot definitiva fija las fechas de corte de forma permanente: requiere indicación del propietario (`python -m swingpilot.research.cli build-snapshot --id <id> --confirm`).
