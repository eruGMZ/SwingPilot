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
