# IMPL-3 — Revisión del entorno: procedencia de get-pip.py, versiones y reproducibilidad

**Fecha:** 2026-11-20
**Autor:** Orquestador de Desarrollo
**Origen:** instrucción del propietario del 2026-11-20 (punto 2).
**Alcance:** solo verificación y documentación. No se cambió `requirements-dev.txt` ni el entorno.

---

## 1. Cómo se creó el entorno

- Sistema: Python 3.14.4 (`/usr/bin/python3`). El sistema **no tiene** `python3.14-venv` (ensurepip) ni pip.
- Procedimiento: `python3 -m venv --without-pip .venv`; descarga de `https://bootstrap.pypa.io/get-pip.py`; `.venv/bin/python -I get-pip.py`; `pip install -r requirements-dev.txt pandas numpy pyarrow scikit-learn websockets`.
- Configuración de pip: ningún `pip.conf` ni variable `PIP_*`. Índice: solo PyPI por defecto (sin índices extra, así que no hay riesgo de confusión de dependencias por esa vía).

## 2. Procedencia de get-pip.py (verificada)

| Comprobación | Resultado |
|---|---|
| SHA-256 del get-pip.py descargado | `356e0d0de21cdc348c3394084d90939b85e4246c4d14c76aee6ca4f46646ea98` |
| Comparación con la fuente oficial `github.com/pypa/get-pip`, `public/get-pip.py` (último commit `c7135ee10cd1`, 2026-11-03) | **Idéntico byte a byte** |
| Versión de pip que contiene | 26.3 |
| pip instalado frente al wheel oficial `pip-26.3-py3-none-any.whl` de PyPI (SHA-256 `f3b60b20ffaadd44…`, publicado 2026-11-02) | **Idéntico** (`diff -r` sin diferencias, excluido `__pycache__`) |

**Riesgo residual (bajo):** get-pip.py no tiene firma. Su autenticidad descansa en TLS hacia `bootstrap.pypa.io` y en la coincidencia con el repositorio de PyPA. Ambos canales los controla la misma organización.

## 3. Versiones instaladas (pip freeze, 2026-11-20)

Declaradas en `requirements-dev.txt`: pytest 9.2.0, jsonschema 4.26.0, anthropic 2.11.0, pandas 3.1.1, numpy 2.5.5, pyarrow 26.0.1, websockets 17.4.
Transitivas relevantes: python-dateutil 4.0.0, tzdata 2026.6, pydantic 2.14.4, httpx2 2.16.2, referencing 0.37.0, rpds-py 2026.9.1.
Instaladas **sin declarar**: scikit-learn 1.9.1, con scipy 1.18.1, joblib 1.6.0 y threadpoolctl 3.8.0.

`pip check`: sin dependencias rotas.

## 4. Riesgos encontrados

| ID | Severidad | Riesgo | Evidencia | Corrección propuesta |
|---|---|---|---|---|
| ENV-01 | MAYOR | **`requirements-dev.txt` no es reproducible:** 7 paquetes sin versión (3 heredados de IMPL-1/2 y 4 añadidos en IMPL-3). Otra instalación puede resolver otras versiones de pandas/pyarrow/numpy, que afectan a los cálculos (indicadores, Parquet) y al SHA-256 de cualquier Parquet nuevo. Choca con REQ-G-100 (reproducibilidad) y REQ-G-140. | `requirements-dev.txt` actual | Añadir un archivo de bloqueo (`requirements-dev.lock`) con versiones exactas y hashes (`--require-hashes`), generado desde este entorno verificado, e instalar con él. Requiere tu visto bueno, porque cambia cómo se instala el entorno. |
| ENV-02 | MENOR | scikit-learn y sus dependencias están instalados pero no declarados ni usados. El entorno no coincide con lo declarado, y una prueba podría pasar aquí y fallar en una instalación limpia. | `pip inspect`: `scikit-learn` como solicitado; ningún `import sklearn` en `src/` (lo verifica `tests/unit/test_ml_registry.py`) | Desinstalarlo del `.venv` o declararlo cuando un preregistro lo justifique (DEC-017 Q44). |
| ENV-03 | MENOR | El entorno se creó con un procedimiento no estándar (get-pip.py) porque falta `python3.14-venv`. La procedencia está verificada (§2), pero no se puede repetir sin red ni sin ese paso manual. | §1 | Instalar el paquete del sistema (`sudo apt install python3.14-venv`, acción del propietario) y recrear el `.venv` con el archivo de bloqueo de ENV-01. |
| ENV-04 | MENOR | La versión de Python (3.14.4) no se declara en ningún sitio. Las pruebas de IMPL-1/2 se registraron sin versión de intérprete, así que no se sabe si coincide con el entorno donde se obtuvo aquella evidencia. | `feature_list.json`: las evidencias de IMPL-1/2 no registran la versión de Python | Registrar la versión de Python y el hash del archivo de bloqueo en cada evidencia de G4 y en el manifiesto de la snapshot (que ya registra Python, pandas y pyarrow). |
| ENV-05 | OBSERVACIÓN | El SHA-256 de un Parquet depende de la versión de pyarrow. No afecta a la verificación (se hashea el archivo escrito y luego no se reescribe), pero recrear la snapshot con otra versión daría otros hashes. | `snapshot.py` registra la versión escritora | Ninguna, salvo ENV-01. Está documentado en el manifiesto. |

## 5. Estado

Con las versiones de §3, la suite da 325 passed, 5 skipped. Las correcciones ENV-01..04 no se aplican sin indicación del propietario.

---

## 6. Corrección de ENV-01..04 (2026-11-20)

**Autorización del propietario (2026-11-20):** «Aplicar ENV-01..04: fijar dependencias con versiones y hashes, resolver la dependencia de scikit-learn, documentar la versión de Python y los paquetes del sistema. Entregar evidencia de instalación reproducible.» Y también: «si es necesario, actualiza Python». Commit base: `5c17e92`.

**Hecho al empezar:** este equipo (Ubuntu 24.04.5) **no era** el de §1–§3. Tenía Python 3.12.3 del sistema, y su `.venv` carecía de pandas, numpy, pyarrow y websockets y traía anthropic 2.10.0 en vez de 2.11.0. Es la deriva que describe ENV-01. El `.venv` anterior se conserva, sin uso, como `.venv-py312.bak` (ignorado por Git).

### 6.1 Cambios

| ID | Corrección | Archivos |
|---|---|---|
| ENV-01 | Las dependencias directas pasan a versión exacta (las de §3). Se añade un lock con **hashes SHA-256 de todas las distribuciones** (34 entradas, universal: Linux/Windows/macOS), generado con `uv pip compile --generate-hashes --universal --exclude-newer 2026-11-20T00:00:00Z`, con las transitivas de §3 como restricciones. La instalación se hace solo desde el lock con `--require-hashes`. | `requirements-dev.txt`, `requirements-dev.constraints.txt` (nuevo), `requirements-dev.lock` (nuevo) |
| ENV-02 | **scikit-learn excluido** (con scipy, joblib y threadpoolctl): DEC-017 Q44 limita FEAT-019 a la infraestructura, sin modelo entrenado, y `src/` no lo importa. Se declarará cuando un preregistro aprobado lo justifique. Una prueba impide reinstalarlo sin que se note. | `requirements-dev.txt` (comentario), `tests/regression/test_environment_lock.py` |
| ENV-03 | Procedimiento estándar con **uv** en lugar de get-pip.py y python3.14-venv (que Ubuntu 24.04 no trae). uv descarga CPython de python-build-standalone verificando su checksum y crea el venv sin pip del sistema. | `scripts/setup_env.sh` (nuevo) |
| ENV-04 | La versión de Python queda declarada (**3.14.4**, la misma de §1 y de la evidencia de IMPL-3). La prueba de regresión falla si el intérprete o cualquier paquete instalado se separa del lock. | `.python-version` (nuevo), `tests/regression/test_environment_lock.py` (nuevo) |

### 6.2 Sistema y artefactos (equipo de esta corrección)

| Elemento | Valor |
|---|---|
| SO | Ubuntu 24.04.5 LTS, Linux 7.0.0-43-generic x86_64, glibc 2.39-0ubuntu8.12 |
| Paquetes del sistema requeridos | Solo `uv` 0.12.5 (binario `~/.local/bin/uv`, SHA-256 `b65f23a4…de5f46`). No se usan `python3-venv`, `python3-pip` ni el Python del sistema (3.12.3). |
| Intérprete | CPython 3.14.4 (python-build-standalone, Clang 22.1.3), `~/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/bin/python3.14`, SHA-256 `4e7a6eeb…9f63ce`; OpenSSL 3.5.6; SQLite 3.50.4 |
| `requirements-dev.lock` | SHA-256 `6396aa4cb2132f280637cbd8a907b11645b592643fc0b6a3139da41bae240fc9` |
| `requirements-dev.txt` | SHA-256 `f8210c78…40fe6fe` |
| `requirements-dev.constraints.txt` | SHA-256 `b9155009…0655d` |
| Paquetes instalados (32 en Linux) | annotated-types 0.8.0, anthropic 2.11.0, anyio 4.16.0, attrs 26.1.0, docstring-parser 0.18.0, h11 0.16.0, httpcore2 2.16.2, httpx2 2.16.2, idna 3.20, iniconfig 2.3.1, jiter 0.19.0, jsonschema 4.26.0, jsonschema-specifications 2025.9.1, numpy 2.5.5, opentelemetry-api 1.45.2, packaging 26.3, pandas 3.1.1, pluggy 1.7.0, pyarrow 26.0.1, pydantic 2.14.4, pydantic-core 2.50.5, pygments 2.21.0, pytest 9.2.0, python-dateutil 4.0.0, referencing 0.37.0, rpds-py 2026.9.1, sniffio 1.3.1, truststore 0.10.5, typing-extensions 4.16.0, typing-inspection 0.4.5, tzdata 2026.6, websockets 17.4 |

### 6.3 Evidencia de instalación reproducible

| # | Prueba | Resultado |
|---|---|---|
| E1 | `.venv` recreado: `uv venv --python 3.14.4` + `uv pip sync --require-hashes requirements-dev.lock`; `uv pip check` | 32 paquetes, todos compatibles; `import sklearn` → ModuleNotFoundError |
| E2 | Segunda instalación desde cero en otra ruta, **sin caché** (`--no-cache`, todo descargado y verificado por hash) | `pip freeze` idéntico al de `.venv` (32 paquetes, `diff` vacío) |
| E3 | Lock alterado: los hashes de websockets se sustituyen por `ffff…` | Instalación **rechazada** (exit 1, «hash mismatch»; hash calculado `ef03fb4b…9caa`) |
| E4 | `tests/regression/test_environment_lock.py` en el `.venv` nuevo | 5 passed |
| E5 | La misma prueba con el intérprete del `.venv` anterior (3.12.3) | **2 failed** (versión de Python y paquetes distintos del lock), 3 passed: la prueba detecta la deriva |
| E6 | Suite completa `.venv/bin/pytest -q -p no:cacheprovider tests` antes de añadir la prueba nueva | 426 passed, 5 skipped (el mismo resultado registrado para IMPL-3); validadores OK |

### 6.4 Riesgo residual

- uv no está en el lock: se registra su versión y hash (§6.2). Otra versión de uv puede generar un lock con otro formato, pero instala los mismos hashes.
- Laptop B (producción) y cualquier otro equipo deben recrear `.venv` con `scripts/setup_env.sh`. Hasta entonces, la prueba de regresión fallará allí, que es lo que se busca.
- Los hashes de Parquet siguen dependiendo de la versión de pyarrow (ENV-05), que ahora queda fijada por el lock.
