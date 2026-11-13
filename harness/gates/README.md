# harness/gates/ — Gates de Control

## Propósito

Los gates son puntos de control obligatorios que deben superarse secuencialmente para avanzar entre fases.

## Reglas

- **Ningún gate puede aprobarse mediante declaración del agente.**
- Los gates G3 y G7 requieren **aprobación humana explícita**.
- El estado de los gates se gestiona en `gate_status.json`.
- El script `scripts/validate_gates.py` verifica la consistencia del archivo de gates.

## Gates definidos

| Gate | Fase | Descripción | Requiere humano |
|------|------|-------------|----------------|
| G0 | FASE 1 | Integridad y registro documental | No |
| G1 | FASE 1 | Cobertura de extracción | No |
| G2 | FASE 1 | Consistencia y trazabilidad del contrato | No |
| G3 | FASE 1 | Aprobación humana del contrato | **Sí** |
| G4 | FASE 2 | Pruebas de implementación | No |
| G5 | FASE 2 | Integración y regresión | No |
| G6 | FASE 2 | Seguridad | No |
| G7 | FASE 2 | Aprobación de release | **Sí** |
