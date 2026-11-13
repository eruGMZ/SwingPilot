# tests/ — Pruebas de SwingPilot

## Propósito

Este directorio contiene todas las pruebas del sistema SwingPilot, organizadas por tipo.

## Estructura

| Directorio | Tipo | Gate asociado |
|-----------|------|---------------|
| `unit/` | Pruebas unitarias | G4 |
| `integration/` | Pruebas de integración | G5 |
| `acceptance/` | Pruebas de aceptación | G4 |
| `regression/` | Pruebas de regresión | G5 |
| `security/` | Pruebas de seguridad | G6 |

## Reglas

- Toda funcionalidad en `src/` debe tener prueba asociada en este directorio.
- Las pruebas no pueden desactivarse para obtener un PASS.
- Los resultados de ejecución deben registrarse como evidencia en `feature_list.json`.
- Las pruebas de los controles de investigación cuantitativa (aislamiento Train/OOS, prevención de look-ahead, gestión de riesgo) deben respetar sus contratos específicos.

## Estado actual

FASE 0 — sin pruebas. Las pruebas se crean en FASE 2 según el `implementation/test_plan.md`.
