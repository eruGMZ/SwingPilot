# harness/verification/ — Verificador Adversarial

## Propósito

Este directorio contiene el esquema de reportes del Verificador adversarial y los reportes producidos en FASE 1.

## Responsabilidades del Verificador

El Verificador es un agente **independiente del Merger** que audita el contrato técnico.

**Acceso del Verificador:**
- Documentos originales en `docs/context/` (solo lectura).
- Manifiesto en `harness/manifest.json`.
- Outputs de extracción en `harness/extraction/outputs/`.
- Contrato técnico en `implementation/`.

**Verifica:**
1. Cobertura documental completa.
2. Trazabilidad de cada requisito.
3. Ausencia de requisitos inventados.
4. Consistencia entre documentos.
5. Ausencia de contradicciones críticas sin resolver.
6. Correspondencia entre requisitos y módulos.
7. Correspondencia entre requisitos y funciones.
8. Correspondencia entre requisitos y pruebas.
9. Validez de parámetros y restricciones.
10. Integridad de contratos e interfaces.

**Emite:** reporte formal PASS / FAIL conforme a `verification.schema.json`.

## Restricciones

- El Verificador NO puede aprobar su propio trabajo.
- El Verificador NO puede heredar las conclusiones del Merger como evidencia.
- Si el veredicto es FAIL, el Merger corrige y el Verificador repite la auditoría.

## Estado actual

FASE 0 — sin actividad. Este directorio permanece vacío hasta FASE 1.
