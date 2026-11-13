# harness/merge/ — Workspace del Merger

## Propósito

Este directorio es el workspace del agente Merger en FASE 1.

## Responsabilidades del Merger

El Merger recibe los outputs estructurados de todos los extractores y construye el contrato técnico en `implementation/`:

1. `requirements.md`
2. `architecture.md`
3. `api_contracts.md`
4. `data_flow.md`
5. `test_plan.md`
6. `conflict_register.md`

## Reglas de integración

- Las decisiones humanas aprobadas (`docs/decisions/`) prevalecen sobre cualquier otra fuente.
- Las políticas obligatorias (`docs/policies/`) deben respetarse sin excepción.
- Las contradicciones entre fuentes de igual autoridad deben escalarse, no resolverse unilateralmente.
- No se eliminan requisitos por conveniencia.
- No se inventan funcionalidades.
- Los requisitos derivados deben identificarse explícitamente como DERIVED.
- Toda decisión pendiente permanece explícitamente pendiente.

## Estado actual

FASE 0 — sin actividad. Este directorio permanece vacío hasta FASE 1.
