# IMPL-3 — QA-CR020-05: evaluación y prueba de caracterización (FEAT-017; CR-020 §C.4.3; CR-021)

**Fecha:** 2026-11-24
**Autor:** Orquestador de Desarrollo (evaluación y caracterización; no es una QA independiente).
**Autorización del propietario (2026-11-24):** acepta la evaluación de solo lectura de QA-CR020-05 y la disposición: el defecto funcional original quedó resuelto como consecuencia de CR-021, y la obligación vinculante del veredicto estructurado sigue siendo la de CR-020 §C.4.3. Autoriza **una** prueba de caracterización con la entrada original de P6. Sin cambios de código funcional ni enmiendas contractuales; si la prueba falla, detenerse e informar. Sin commit ni push.
**Base:** `45bc5407c8ad2acd02e4a4c44703552d4771e73d` (`develop` = `origin/develop`, árbol limpio).
**Hallazgo de origen:** `harness/verification/IMPL-3_CR-020_QA_independiente.md` §3 (QA-CR020-05, OBS) y sonda P6 de `IMPL-3_CR-020_QA_sondas.py`. Ambos se conservan sin cambios.
**Estado:** EVIDENCIA ACEPTADA POR EL PROPIETARIO (2026-11-24, §9). QA-CR020-05 RESUELTO POR SOLAPAMIENTO CON CR-021, VERIFICADO POR EL IMPLEMENTADOR Y ACEPTADO POR EL PROPIETARIO — PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE. CONF-009 y CONF-010 OPEN; CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS.

## 1. Trazabilidad contractual

| Obligación | Fuente | Exige | Comportamiento actual |
|---|---|---|---|
| Registro corrupto → **INCONCLUSIVE** (Fail-Closed, nunca ELIGIBLE) | CR-020 §C.4.3 (vigente; no sustituida por CR-021); REQ-G-P17 («conteo incoherente o incompleto → INCONCLUSIVE») | Veredicto estructurado INCONCLUSIVE | Cumple (§3, §4) |
| Registro corrupto → todo bloqueado; el evaluador nunca emite ELIGIBLE | CR-021 §F.2 P1 (DEC-023); REQ-G-104 v1.9; TC-ML-023 | «INCONCLUSIVE **o error**» | Cumple |

**Solapamiento con CR-021:** CR-021 §F.2 dice expresamente que QA-CR020-05 «no se trata aquí: también falla cerrando». Su política P1 es más débil que CR-020 §C.4.3, porque admite un error. No hay contradicción: rige la obligación más estricta, que sigue vigente. El comportamiento conforme es una consecuencia de CR-021, no una corrección propia: el lector validado (`experiments.py:239-240`, `_parse_registry`) rechaza toda línea que no es un objeto con `RegistryCorruptError`, y el evaluador lo convierte en `REGISTRY_UNREADABLE` (`trials.py:38-41`). `IMPL-3_CR-021_implementacion.md` ya registró este solapamiento (P6 → INCONCLUSIVE) sin cerrar el hallazgo.

## 2. Ruta de ejecución (inspección del código)

Los usos de `r.get` sin comprobar el tipo que cita el informe (hoy `trials.py:49`, `:92` y `:123`) siguen sin protección, pero son inalcanzables con una línea que no es un objeto:
- `reconcile` obtiene los registros solo de `registry.records()`, el lector validado (P1).
- `registry.trials_accounting` y `registry.accounting` reciben esos mismos registros validados.
- La segunda lectura del registro, en `confirmatory_findings` (`_replay`, `_registry_exposure`, `_preregistered_sha`, `_read`), convierte cualquier corrupción en `PreregistrationError`, que `reconcile` traduce a INCONCLUSIVE (`DEVIATIONS_INCOHERENT`).
- Después de `reconcile`, `acceptance.evaluate` no vuelve a leer el registro.

## 3. Evaluación de solo lectura (2026-11-24; evidencia conservada)

Script sintético en el directorio temporal de la sesión (no está en el repositorio). Reproduce los pasos de P6 (`ready`, añadir la línea, `evaluate`) sobre registros temporales. No se ejecutó el archivo de sondas completo, porque ejecuta P1–P11.

| Variante | Resultado |
|---|---|
| P6 literal: añadir `[1, 2]` al final | `Verdict` INCONCLUSIVE; `REGISTRY_UNREADABLE: … la línea 10 no es un objeto`; `trials_count` = `None`; archivo intacto |
| `[1, 2]` en medio del archivo | Igual («línea 5») |
| Cola `null`, `3`, `"x"`, `true`, `[]` | Igual en los cinco casos |
| Corrupción entre lecturas: se añade `[1, 2]` justo antes de que `confirmatory_findings` vuelva a leer el registro | `Verdict` INCONCLUSIVE con `DEVIATIONS_INCOHERENT` (otro código, también estructurado) |

**Pruebas existentes ejecutadas (3 passed):** fila `non_object_line` de la matriz P1 (`test_cr021_durability.py`), control de registro limpio y `test_tc_ml_024_unreadable_registry_is_inconclusive`.

**Hueco de cobertura confirmado:** la ruta del evaluador de la matriz P1 acepta cualquier texto que contenga «registro corrupto», así que también pasaría si `evaluate()` lanzara `RegistryCorruptError`. La prueba existente de registro ilegible exige INCONCLUSIVE, pero con una línea JSON no válida, no con una que no es un objeto.

## 4. Prueba de caracterización

`tests/unit/test_trials_accounting.py::test_qa_cr020_05_non_object_line_gives_structured_inconclusive_verdict` (añadida tras `test_tc_ml_024_unreadable_registry_is_inconclusive`; ninguna prueba existente cambia). Registro temporal sintético con la preparación `ready`; se añade la entrada original de P6 (`[1, 2]`). Aserciones:

1. `evaluate()` devuelve un `acceptance.Verdict` (no lanza).
2. `outcome` = INCONCLUSIVE.
3. Un motivo con el código `REGISTRY_UNREADABLE`.
4. `metrics["trials_count"]` es `None`.
5. El registro queda byte a byte igual tras la evaluación.

**Discriminación (mutante solo en una copia temporal de `src`):** si `reconcile` deja propagar el error del registro en lugar de devolver `REGISTRY_UNREADABLE`, la prueba nueva **falla** (`RegistryCorruptError`), mientras que la fila `non_object_line` de la matriz P1 sigue **pasando**. Esto confirma que la prueba nueva cubre el hueco de §3.

## 5. Resultados

- Prueba nueva: **1 passed**. Sin discrepancias.
- Suite: `.venv/bin/pytest -q -p no:cacheprovider tests` → **827 passed, 5 skipped** (826 + 1).
- Validadores: `python3 scripts/validate_{manifest,requirements,gates}.py` → OK.
- Registro real sin cambios (SHA-256 `07efad20…`).

## 6. Limitaciones residuales

1. **La conformidad depende del lector validado**, no de una protección en el evaluador: los `r.get` de `trials.py` siguen sin comprobar el tipo. Un cambio futuro que use registros sin pasar por `records()` reabriría el fallo. La prueba nueva lo detectaría para la ruta de `evaluate()`.
2. **Formulación de CR-021 P1** («INCONCLUSIVE o error») más débil que CR-020 §C.4.3. Rige la segunda; no se propone enmienda.
3. **Corrupción entre lecturas:** da INCONCLUSIVE con `DEVIATIONS_INCOHERENT`, no con `REGISTRY_UNREADABLE`. Solo se observó en la evaluación de solo lectura; no tiene prueba ejecutable.
4. **Caracterización, no regresión:** la prueba pasa con la base; protege el comportamiento conforme.

## 7. Obligación de reverificación independiente

Comprobar de forma independiente que, ante cualquier línea del registro que no es un objeto (en cualquier posición y de cualquier tipo JSON), `evaluate()` devuelve un veredicto estructurado INCONCLUSIVE sin lanzar, sin conteo y sin modificar el registro, también cuando la corrupción aparece entre lecturas; y que ninguna ruta del evaluador usa registros no validados.

## 8. Archivos

Modificado: `tests/unit/test_trials_accounting.py` (solo se añade una prueba). Nuevo: este documento. Actualizados: `progress.md`, `session-handoff.md`. Sin cambios en código funcional, contrato v1.10, aserciones existentes, registro real, informe y sondas de la QA original, `feature_list.json` ni gates. Sin commit ni push. Sub-agentes: 0.

## 9. Aceptación del propietario (2026-11-24)

El propietario aprueba la evidencia de caracterización de QA-CR020-05 y acepta:

- que el defecto funcional original quedó resuelto como consecuencia de CR-021;
- que la obligación vinculante del veredicto estructurado INCONCLUSIVE sigue siendo la de CR-020 §C.4.3 y REQ-G-P17;
- que la prueba de caracterización nueva cierra el hueco de cobertura demostrado;
- que la evidencia de mutantes confirma que la prueba nueva detecta una violación contractual que la matriz P1 no detecta;
- el resultado de la suite (827 passed, 5 skipped) y los tres validadores OK;
- las limitaciones residuales (§6) y la obligación de reverificación independiente (§7).

**Estado:** QA-CR020-05 RESUELTO POR SOLAPAMIENTO CON CR-021, VERIFICADO POR EL IMPLEMENTADOR Y ACEPTADO POR EL PROPIETARIO; PENDIENTE DE REVERIFICACIÓN INDEPENDIENTE.

**Naturaleza de la evidencia (se conserva la distinción):**
- **Evidencia automatizada (prueba ejecutable):** línea que no es un objeto (entrada original de P6) → veredicto estructurado INCONCLUSIVE, `REGISTRY_UNREADABLE`, `trials_count` = `None`, registro intacto (§4); discriminación frente al mutante que propaga el error (§4).
- **Observaciones de solo lectura (sin prueba ejecutable):** las variantes de posición y de tipo JSON, y la corrupción entre lecturas (INCONCLUSIVE con `DEVIATIONS_INCOHERENT`) de §3. Se observaron una vez en la evaluación; no las protege ninguna prueba.

**Commit autorizado:** los cuatro archivos de §8, con el mensaje «test(impl-3): characterize QA-CR020-05 structured corruption verdict», sin push; pruebas no reejecutadas para el commit. Sin cambios en contrato, código funcional, aserciones existentes, registro real, evidencia de QA original, sondas, `feature_list.json` ni gates. CONF-009 y CONF-010 OPEN; CONF-011 RESOLVED; FEAT-015 DONE; FEAT-017 IN_PROGRESS.
