# docs/ — Documentación del Proyecto SwingPilot

## Propósito

Este directorio contiene toda la documentación del proyecto SwingPilot organizada por tipo y jerarquía de autoridad.

## Jerarquía de autoridad documental

```
docs/decisions/   ← Autoridad máxima (decisiones humanas aprobadas)
docs/policies/    ← Restricciones no negociables
docs/context/     ← Fuente de verdad para FASE 1 (documentación original)
```

## Reglas sobre los documentos de docs/context/

Los documentos originales de SwingPilot depositados en `docs/context/`:
- **No deben sobrescribirse.**
- **No deben modificarse para facilitar la interpretación del agente.**
- **No deben resumirse y sustituirse por versiones generadas.**
- **Deben conservar su identidad, contenido y trazabilidad.**

Toda modificación posterior debe gestionarse mediante solicitud de cambio formal en `harness/change_requests/`.

## Estado actual

`docs/context/` está vacío. El propietario del proyecto depositará aquí la documentación original de SwingPilot antes de autorizar FASE 1.
