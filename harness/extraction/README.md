# harness/extraction/ — Extracción Documental

## Propósito

Este directorio contiene los esquemas de salida para los agentes extractores y los outputs de extracción producidos en FASE 1.

## Reglas de los extractores

- Cada extractor analiza **un único documento** asignado.
- El extractor recibe exclusivamente: su documento, su versión, un task brief y el esquema de salida.
- **No puede** consultar documentos de otros extractores.
- **No puede** inventar requisitos, resolver contradicciones ni suponer decisiones faltantes.
- **No puede** alterar el sentido de las fuentes.
- Debe producir un output estructurado conforme a `schemas/extraction.schema.json`.
- Los campos desconocidos se marcan como `PENDING`.

## Contenido

| Ruta | Descripción |
|------|-------------|
| `schemas/extraction.schema.json` | Esquema JSON obligatorio para todos los outputs |
| `outputs/` | Outputs de extracción (vacío hasta FASE 1) |
