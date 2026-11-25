# IMPL-3 — Reverificación independiente consolidada de CR-020 (QA-CR020-01..06, O3, O4)

**Fecha:** 2026-11-25
**Autor:** revisor de QA independiente (sesión distinta de la del implementador). No aprueba su propio trabajo ni cierra conflictos, estados o hallazgos (AGENTS.md).
**Base verificada:** `2625ee971bcf36e0966762575f8af1f4774e962a` (`develop` = `origin/develop` según la referencia local; árbol limpio antes y después). Contrato v1.10; `feature_list.json` v1.21.1.
**Veredicto del revisor:** **CONFORME CON OBSERVACIONES**. Ninguna disconformidad frente al contrato v1.10 en los ocho elementos; tres incidencias nuevas (N-1..N-3) y cinco inconsistencias documentales (D-1..D-5), todas sin resolver.
**Estado:** el propietario acepta la recepción del informe (2026-11-25); **no** es el cierre final de los hallazgos, de D2 ni de ningún conflicto. Esta preservación no cambia ningún estado.

## 0. Clasificación del contenido de este documento

| Clase | Dónde |
|---|---|
| **Evidencia histórica original** (no modificada) | `IMPL-3_CR-020_QA_independiente.md`, `IMPL-3_CR-020_QA_sondas.py`, `IMPL-3_QA-CR020-0{1,2,3,5}_*`, `IMPL-3_CR-02{1,2}_*`, `IMPL-3_QA-CR020-O{3,4}_evaluacion.md`. Solo se ejecutaron (P1–P11 y la reproducción de QA-CR020-03), sin modificarlos |
| **Evidencia nueva de esta reverificación** | §2 (resultados), §3 (sondas nuevas), §4 (strace), `IMPL-3_CR-020_reverificacion_sondas/` |
| **Recomendaciones del revisor** (no son decisiones) | §6 |
| **Decisiones del propietario pendientes** | §7 |

Toda la evidencia nueva se produjo con registros sintéticos temporales; no es evidencia original del implementador ni reconstruye evidencia histórica faltante.

## 1. Alcance y método

Lectura de AGENTS.md, `session-handoff.md`, el informe original, los documentos de corrección y evaluación, CR-020/021/022, DEC-021..024, REQ-G-103/104/P17, TC-ML-020..024 (v1.10) y el código de `src/swingpilot/research/`. Se registró el SHA-256 del registro real antes y después. Sin modificar archivos del repositorio, sin subagentes, sin servicios en vivo, sin commit durante la verificación.

## 2. Veredicto por hallazgo

| Hallazgo | Veredicto | Evidencia nueva |
|---|---|---|
| QA-CR020-01 | Conforme con observaciones (N-1) | Seis variantes inválidas de `informed_by` (par inexistente, procedencia inexistente, claves de más, no lista, `None`, autorreferencia): todas rechazadas; archivo idéntico byte a byte, par sin contar, cargador deniega en proceso y en proceso separado. Justificación vacía y falta de constructor: rechazadas. 11 pruebas de `test_qa_cr020_01.py` pasan |
| QA-CR020-02 | Conforme | Matriz de 11 escenarios evaluador frente a `confirmatory_status`: coherentes en las cuatro causas de pérdida; preregistro ajeno o alterado y entradas manipuladas → no verificable; pérdida demostrada → `False` aunque falte otra evidencia; tras la selección ninguna ruta devolvió `True` sin preregistro vinculado y entradas con hash coincidente |
| QA-CR020-03 | Conforme con observaciones (N-2) | Strace (§4): evidencia en descriptor nuevo `O_APPEND`, `write` y `fsync` sobre ese mismo descriptor, marcador en otro descriptor posterior, todo dentro de un único `flock(LOCK_EX)`. Con `fsync` de la evidencia fallando 3 veces: 3 copias idénticas, ningún marcador, acceso denegado (mismo objeto, objeto nuevo, proceso separado). Reintento correcto: copia + marcador, SHA del marcador = SHA de la línea, conteo 1, acceso concedido; segundo reintento no escribe. R2 (solo falla el `fsync` del marcador): la operación informa incertidumbre, otro proceso accede, el reintento no escribe; marcador perdido → denegado, conteo 1. No planificada: evaluación + DEVIATION en una sola escritura y un `fsync`. 22 pruebas de `test_cr021_durability.py` pasan (incluida la matriz P1) |
| QA-CR020-04 | Conforme | Cita de par exacto; caso 3 prevalece (`informed_by` vacío; DEVIATION que cita solo al hermano; prueba posterior a la selección → INCONCLUSIVE); `provenance_id` nunca cita (N_eval = N_pre = 9); un par citado por tres puntos cuenta una vez (N_eval = N_pre + 2); línea congelada intacta; DSR con `N_eval` |
| QA-CR020-05 | Conforme con observaciones (N-3) | 9 tipos JSON × cabeza/medio/cola → INCONCLUSIVE estructurado (`REGISTRY_UNREADABLE`; `{}` → `DEVIATIONS_INCOHERENT`), `trials_count` = `None`, archivo intacto. Corrupción añadida en cada una de las 11 lecturas de `evaluate()` (dos formas) → INCONCLUSIVE estructurado, sin excepción ni veredicto favorable |
| QA-CR020-06 | Conforme con observaciones (D-1..D-5) | Sin cambios de estado de FEAT desde `9026797`; `evidence.covered` idéntico; demás FEAT idénticas; el registro de conflictos solo añade notas; commits citados existentes; código idéntico entre `fde522c` y `f48114c`; informe/sondas/correcciones con un solo commit cada uno |
| QA-CR020-O3 | Conforme con observaciones | Las cuatro disposiciones son válidas y fieles. Registro real sin reducciones (`supersedes` = `None`, H_doc 4, H_bound 4, E 0, G 8, sin cambios desde `f2f05a9`). Unicode (caracterización nueva, **no certificación**): aceptados NBSP/U+3000 finales y separadores U+2028, U+0085, `\x0c`; rechazados espacio inicial y dígitos de ancho completo o arabigoíndicos. El borde sigue sin verificarse contractualmente |
| QA-CR020-O4 | Conforme (disposición) | Caracterización nueva: el cargador entrega un par certificado en OOS_EVALUATION y en REJECTED; el registro del inicio se rechaza fuera de DEVELOPMENT/VALIDATION; recuperaciones repetidas dejan E = 1; repetir el mismo `config_id` no escribe nada y el registro no incluye huella del contenido. No se confunde con la O4 antigua. La obligación operativa sigue abierta, no implementada. El registro del propietario describe su evidencia como inspección de código; esta ejecución no la modifica |

## 3. Pruebas y sondas

- Dirigidas (cinco archivos CR-020/021/022): 130 passed. Suite completa (una vez): **827 passed, 5 skipped** (133 s). Los 5 skips son pruebas en vivo (Anthropic ×3, Binance ×2) por falta de variable de activación; **no se ejecutaron y no cuentan como superadas**.
- Validadores `validate_{manifest,requirements,gates}.py` → código 0 (no verifican semántica contractual). `feature_list.json` es JSON válido.
- Sondas originales P1–P11 y `IMPL-3_QA-CR020-03_reproduccion.py`, sin modificar: P1 rechazada; P2 `False`; P3 no verificable (la sonda no aporta preregistro ni entradas); P5 `N_eval` 2; P6 INCONCLUSIVE; P9 una línea con 6 procesos; P10 y P11 aceptadas (O3). La línea «puerta» de P4 solo comprueba el predicado de conteo, no el acceso real; la sección 4 de la reproducción cae hoy en el caso R2 aprobado.
- **Sondas nuevas** (directorio `IMPL-3_CR-020_reverificacion_sondas/`):

| Archivo | Cubre |
|---|---|
| `common.py`, `child_gate.py` | Auxiliares; decisión real de `load_train_val_for_configuration` con `_read` sintético; proceso separado |
| `p_durability.py` | QA-CR020-01 (01-a..c) y QA-CR020-03 (03-a..e) |
| `p_builder.py` | N-1; byte-identidad de copias de la evaluación |
| `p_eval.py` | QA-CR020-02 (matriz), 04, 05-a/b/c (incluye N-3), O4, O3-P11 |
| `p_concurrency.py` | N-2 (lectores sin bloqueo frente a escritor) |
| `p_strace_child.py`, `prepare_strace.py` | Traza de CR-021 |

## 4. Evidencia de llamadas al sistema (CR-021)

Archivo: `IMPL-3_CR-020_reverificacion_sondas/strace_CR-021_orden_escritura_fsync.txt` (rutas sustituidas por `<TMP>`). Orden observado, con `begin_evaluation` de una configuración planificada (A) y una no planificada (Z):

1. `openat(registry.jsonl.lock, O_APPEND)` → `flock(LOCK_EX)`.
2. A: `openat(registry.jsonl, O_WRONLY|O_CREAT|O_APPEND)` (fd 6) → `write` 261 B → `fsync(6)` = 0; nuevo `openat` (fd 6) → `write` 322 B (marcador) → `fsync(6)` = 0; `flock(LOCK_UN)`.
3. Z: un `openat` → `write` 836 B (evaluación + DEVIATION en una sola escritura) → `fsync` = 0; otro `openat` → `write` 480 B (marcador) → `fsync` = 0; `flock(LOCK_UN)`.

Las lecturas (`O_RDONLY`) ocurren con el bloqueo tomado en las rutas de escritura. Las lecturas del cargador y de `records()` no toman el bloqueo (N-2). Ejecución en ext4, kernel 7.0.0-44, Python 3.14.4.

## 5. Incidencias nuevas y observaciones documentales (SIN RESOLVER)

| ID | Sev. | Descripción |
|---|---|---|
| **N-1** | MENOR (latente) | `begin_configuration_evaluation` solo comprueba `kind` y `config_id` del registro devuelto por el constructor. Un `deviation_id` ausente, un SHA del preregistro erróneo o un `informed_by` no verificable dan éxito de la llamada con acceso denegado después; un `experiment_id` ajeno o un `field` ≠ `trials_count` dejan **todo el registro corrupto** (bloqueo total hasta una conciliación manual aún PENDING). El único llamador en `src/` y `scripts/`, `begin_evaluation`, valida en su constructor; la vía sancionada no se ve afectada. La corrección de QA-CR020-01 afirma que la DEVIATION se valida antes de escribir; a nivel de esta API no se cumple |
| **N-2** | OBS | Las lecturas no toman el `flock`. Un lector concurrente puede ver una escritura en curso y notificar «cola sin salto de línea» (falsa corrupción transitoria): un par certificado se deniega (Fail-Closed) puntualmente. Reproducido con líneas de 5 KB y, con líneas de ~150 B de relleno, 2 denegaciones en ~5.500 llamadas en una ejecución y 0 en otra. Riesgo: iniciar una recuperación manual (P5) sobre un registro sano |
| **N-3** | OBS | `evaluate()` lee el registro varias veces; el paso 4 usa los registros de la primera lectura validados frente a una lectura posterior. Escenario conservado (`p_eval.py`, sección 05-c): se añade a un registro válido una DEVIATION de X mal formada (`informed_by` = `"abc"`); entre la 1.ª y la 2.ª lectura el archivo se **reescribe** (sustitución completa por la versión sin esa línea) → el evaluador devuelve **ELIGIBLE_FOR_HUMAN_REVIEW** (`trials_count` = 1) sobre una vista mixta. **Limitación explícita:** solo ocurre con una reescritura destructiva fuera del protocolo append-only aprobado (I4, P3); las inyecciones por añadido (05-b) dan siempre INCONCLUSIVE. Matiza la afirmación «ninguna ruta del evaluador usa registros no validados» |
| D-1 | BAJA | `feature_list.json`, FEAT-017, entrada de evidencia de A2: «QA-CR020-O3, sin resolver» (el texto de origen es histórico) |
| D-2 | BAJA | `conflict_register.md`, última nota de CONF-010: «QA-CR020-O3 y O4 sin resolver»; sin nota posterior |
| D-3 | BAJA | `evidence.pending` de FEAT-017 enumera QA-CR020-01..05 como pendientes de reverificación y omite 06 |
| D-4 | BAJA | `feature_list.json` `metadata.last_updated` = 2026-11-24, pero v1.21.0 y v1.21.1 son del 2026-11-25 |
| D-5 | BAJA | `session-handoff.md` indica «1 commit por delante de `origin/develop`»; la referencia local mostraba `develop` = `origin/develop` |

## 6. Recomendaciones del revisor (no son decisiones)

- **D2:** puede considerarse «verificada con observaciones» tras decidir N-1 (corregir o aceptar) y N-2 (aceptar o bloqueo consistente en lectura), y tras tratar D-1..D-5.
- **CONF-009 (LOW):** sin defecto en la procedencia ni en el registro real; sin obstáculo técnico para proponer su cierre. La reevaluación obligatoria antes del cierre de FEAT-017 sigue vigente.
- **CONF-010 (MEDIUM):** mantener OPEN hasta que el propietario decida si las obligaciones operativas previas al pipeline de O3 y O4 son condición de cierre; añadir una nota que corrija «O3 y O4 sin resolver».

## 7. Decisiones del propietario pendientes (PENDING)

Disposición de N-1, N-2, N-3 y D-1..D-5; estado de cada hallazgo QA-CR020-01..06, O3 y O4 tras esta reverificación; estado de D2; cierre o no de CONF-009 y CONF-010; cierre de FEAT-017. Obligaciones abiertas que se conservan: verificación de la contabilidad de escenarios de coste (O3) y de modificaciones sustantivas bajo un `config_id` existente (O4) antes de habilitar el pipeline de evaluación; supuestos S1–S4 en el despliegue (G6, Laptop B); procedimiento de conciliación manual (PENDING); `confirmatory_status(..., selection_inputs=…)` obligatorio en HUMAN_REVIEW.

## 8. Limitaciones de la evidencia

- Los fallos de disco se simularon sustituyendo `os.fsync` en el proceso; no son fallos reales del dispositivo.
- El cargador es el real salvo `_read`, sintético: sin snapshot ni sellado reales.
- Las salidas observadas de las sondas se transcriben en este informe; **no se conservaron como archivos de salida en bruto**. Las sondas se reejecutan con las instrucciones de abajo.
- La traza strace original contenía rutas de la máquina y no se conserva; el archivo preservado es una **regeneración** del mismo procedimiento sobre el mismo código (`2625ee9`), saneada, con idéntico orden de eventos.
- Las sondas nuevas reutilizan en solo lectura auxiliares de `tests/unit/` (`test_cr021_durability.py`, `test_trials_accounting.py`) y no son parte de la suite.
- Las sondas de concurrencia son probabilísticas; el resultado puede variar entre ejecuciones. En la ejecución con líneas realistas se usaron 1.500 líneas de ~150 B (la etiqueta impresa decía 300; ahora el número impreso es el real).
- Las sondas de reescritura (05-c) y de constructores no conformes (N-1) usan escenarios fuera del protocolo, deliberadamente.
- Verificado solo en ext4 local, Linux, Python 3.14.4; S4 (éxito falso de `fsync`) no verificable aquí.

## 9. Reproducción

Desde la raíz del repositorio, con `.venv` de `scripts/setup_env.sh`; `W` es un directorio temporal nuevo:

```
W=$(mktemp -d); D=harness/verification/IMPL-3_CR-020_reverificacion_sondas
.venv/bin/python -I -B $D/p_durability.py $W/d       # 01-a..c, 03-a..e
.venv/bin/python -I -B $D/p_builder.py   $W/b       # N-1
.venv/bin/python -I -B $D/p_eval.py      $W/e       # 02, 04, 05 (N-3), O4, O3-P11
.venv/bin/python -B     $D/p_concurrency.py $W/c 150 1500   # N-2 (líneas realistas); sin argumentos: 5000 B × 300
.venv/bin/python -I -B $D/prepare_strace.py $W/s
strace -f -y -e trace=openat,write,fsync,flock,close -o $W/raw.txt .venv/bin/python -I -B $D/p_strace_child.py $W/s
git status --porcelain; sha256sum research/experiments/registry.jsonl   # sin cambios
```

Dependencias: Python 3.14, `pandas`, `numpy`, `pytest` (para importar los auxiliares de pruebas), `strace` (solo la traza). Sin secretos ni rutas absolutas; solo registros sintéticos temporales. `p_concurrency.py` debe ejecutarse sin `-I` (multiprocessing). Variable opcional `FULL=1` en `common.py`: mensajes de denegación completos.

## 10. Estado

Sin cambios en el informe original, las sondas originales, las correcciones previas, `feature_list.json`, código, pruebas, contratos, conflictos, estados de FEAT, gates ni el registro real (SHA-256 `07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b`, igual antes y después). Sub-agentes: 0.
