# harness/ — SwingPilot Engineering Harness Core

Este directorio contiene la infraestructura operativa del Harness Engineering.

## Estructura

| Directorio | Propósito |
|-----------|-----------|
| `extraction/` | Esquemas y outputs de los agentes extractores (FASE 1) |
| `merge/` | Workspace del agente Merger (FASE 1) |
| `verification/` | Esquemas y reportes del Verificador adversarial (FASE 1) |
| `gates/` | Estado de los gates de control de calidad |
| `change_requests/` | Solicitudes de cambio formales |
| `manifest.json` | Inventario de fuentes documentales con SHA-256 |

## Estado actual: FASE 0

El manifiesto está vacío. Los documentos originales de SwingPilot serán registrados en FASE 1 tras su depósito en `docs/context/`.
