# CR-017 — Fuente de noticias y de datos macro para el Macro Analyst

**Fecha:** 2026-11-20
**Estado:** PROPUESTA (borrador) — pendiente de completar y de aprobación del propietario. No aplicada; contrato sigue en v1.5.
**Origen:** DEC-016 Q37 («La fuente real queda pendiente de una CR») y decisión del propietario del 2026-11-20 («macro a la CR») sobre la observación de IMPL-2: el Macro Analyst responde `INSUFFICIENT_DATA` en casi todos los escenarios porque `macro_data` llega vacío.

## A. Problema

1. `api_contracts.md` §3.4 fija la forma de la entrada del Macro Analyst (`news_sources`, `macro_data`, `time_window`), pero el contrato no define de dónde salen las noticias ni los datos macro, quién los produce, con qué frecuencia ni cómo se validan (REQ-G-070 solo cubre datos de mercado de Binance).
2. Evidencia de IMPL-2 (`tests/calibration/results/IMPL2_*_final-{1,2}.json`): con `macro_data = {}` el Macro Analyst declara `INSUFFICIENT_DATA` (MAC-01..03, CYC-01/02), y Decision Synthesis lo arrastra hacia `INSUFFICIENT_INFO` (CYC-01). Sin fuente definida, en operación real esto podría impedir de forma sistemática las propuestas.
3. El contrato no define cuándo un agente debe usar `INSUFFICIENT_DATA` frente a `COMPLETED` con `missing_data` (REQ-G-071 solo exige «estado explícito … insuficiencia»).

## B. Cambio propuesto

PENDING — requiere decisiones del propietario. Puntos a decidir:

| ID | Decisión | Estado |
|---|---|---|
| B.1 | Fuente(s) de noticias: proveedor, acceso (público o con credencial; si hay credencial, ámbito en CredentialVault y TC-SEC), idioma, costo | PENDING |
| B.2 | Contenido de `macro_data` (indicadores, calendario de eventos) y su fuente | PENDING |
| B.3 | Componente productor (Market Intelligence, REQ-G-057) y validación: antigüedad máxima, duplicados, fuentes caídas (equivalente a REQ-G-070 para noticias) | PENDING |
| B.4 | Comportamiento sin noticias o sin `macro_data`: ¿bloquea la propuesta, o el Macro Analyst responde `COMPLETED` con `missing_data` y la síntesis decide? | PENDING |
| B.5 | Criterio general `INSUFFICIENT_DATA` vs `COMPLETED` + `missing_data` para todos los agentes (api_contracts.md §3.0) | PENDING |

## C. Impacto (preliminar)

- Contrato: api_contracts.md §3.0/§3.4; requirements.md (nuevo requisito de captura de noticias, REQ-G-053, REQ-G-071); data_flow.md Fase 1; test_plan.md (casos de datos de noticias).
- Código: productor de noticias (fase por definir); posible ajuste de prompts (nueva versión y DEC); batería de calibración (nueva congelación).
- Seguridad: si la fuente requiere credencial, nuevo ámbito y pruebas TC-SEC; el contenido externo sigue siendo dato no fiable (TC-SEC-003; evaluación amplia en G6).

## D. Lo que NO cambia mientras esté pendiente

En IMPL-2 las noticias son exclusivamente sintéticas (DEC-016 Q37) y el comportamiento actual del Macro Analyst se acepta como observación abierta. No se cambia el umbral de `INSUFFICIENT_DATA` por prompt sin esta CR.
