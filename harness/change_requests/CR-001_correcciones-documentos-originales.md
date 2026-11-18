# CR-001 — Correcciones a documentos originales derivadas de DEC-002

**Fecha:** 2026-11-15
**Estado:** APROBADA por el propietario el 2026-11-17 y aplicada.
**Origen:** DEC-002, DEC-001 (CONF-001).
**Nota:** la corrección del régimen fiscal ya se aplicó a los originales por instrucción expresa del propietario (DEC-003); no forma parte de este CR.

| # | Documento | Corrección propuesta | Fuente |
|---|-----------|----------------------|--------|
| 1 | docs/policies/AI_INTEGRATION.md | Eliminar la referencia a riesgo "1–2%"; sustituir por límite máximo vinculante 1.5% | DEC-002 §2 |
| 2 | docs/policies/AI_INTEGRATION.md | Eliminar ETH/USDT como activo secundario de los alcances operativos | DEC-002 §3 |
| 3 | docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md | Eliminar "BTC/USDT o ETH/USDT" (el régimen ya se corrigió a 605 por DEC-003) | DEC-002 §3, DEC-003 |
| 4 | docs/policies/TRACEABILITY_MATRIX.md | Corregir fila de versión 1.0 "Aprobada" a BORRADOR | DEC-001 §1 |
| 5 | docs/decisions/CONTEXTO_FISCAL_OPERATIVO.md | Quitar 1–2% (incluido aunque el CR listaba solo AI_INTEGRATION) | Aprobación del propietario 2026-11-17 |

**Impacto:** solo documental; el contrato técnico (implementation/) ya refleja DEC-002. Hasta aprobación, DEC-002 prevalece sobre los textos originales contradictorios.
