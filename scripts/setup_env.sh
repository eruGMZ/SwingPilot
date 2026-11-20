#!/usr/bin/env bash
# setup_env.sh — crea el entorno de desarrollo reproducible de SwingPilot.
#
# Origen: ENV-01..04 (harness/verification/IMPL-3_entorno_reproducibilidad.md §6).
# Requisito del sistema: uv (https://docs.astral.sh/uv/). No requiere python3-venv,
# pip ni get-pip.py del sistema: uv descarga CPython (python-build-standalone,
# con verificación de checksum) y crea el venv.
#
# Uso: scripts/setup_env.sh        (recrea .venv si ya existe, previa confirmación)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY_VERSION="$(tr -d '[:space:]' < .python-version)"
LOCK="requirements-dev.lock"

command -v uv >/dev/null || { echo "ERROR: uv no está instalado" >&2; exit 1; }
[ -f "$LOCK" ] || { echo "ERROR: falta $LOCK" >&2; exit 1; }

if [ -d .venv ]; then
    read -r -p ".venv ya existe. ¿Recrearlo? [s/N] " ans
    [ "$ans" = "s" ] || { echo "Cancelado."; exit 1; }
    rm -rf .venv
fi

uv python install "$PY_VERSION"
uv venv --python "$PY_VERSION" .venv
# --require-hashes: cualquier distribución cuyo SHA-256 no esté en el lock se rechaza.
uv pip sync --python .venv/bin/python --require-hashes "$LOCK"
uv pip check --python .venv/bin/python

echo
echo "Python:     $(.venv/bin/python -c 'import platform; print(platform.python_version())')"
echo "Lock:       $(sha256sum "$LOCK" | cut -d' ' -f1)  $LOCK"
echo "Verificar:  .venv/bin/pytest -q -p no:cacheprovider tests"
