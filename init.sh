#!/usr/bin/env bash
# init.sh — SwingPilot Engineering Harness
# Punto de entrada para verificar el estado del entorno.
# Uso: ./init.sh
# Retorna exit code 0 si todo OK, 1 si alguna comprobación obligatoria falla.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=1
EXIT_CODE=0

echo "============================================================"
echo " SwingPilot Engineering Harness — Environment Check"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# Función auxiliar
# ---------------------------------------------------------------------------
check_file() {
    local path="$1"
    local label="$2"
    if [ -f "$path" ]; then
        echo "  [OK] $label"
    else
        echo "  [FAIL] $label — NOT FOUND: $path"
        EXIT_CODE=1
    fi
}

check_dir() {
    local path="$1"
    local label="$2"
    if [ -d "$path" ]; then
        echo "  [OK] $label"
    else
        echo "  [FAIL] $label — NOT FOUND: $path"
        EXIT_CODE=1
    fi
}

# ---------------------------------------------------------------------------
# 1. Verificación de dependencias
# ---------------------------------------------------------------------------
echo ">> 1. Dependencias"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    echo "  [OK] python3 — $PY_VERSION"
else
    echo "  [FAIL] python3 — NOT FOUND (required for validation scripts)"
    EXIT_CODE=1
fi

if command -v git &>/dev/null; then
    echo "  [OK] git — $(git --version)"
else
    echo "  [WARN] git — not found"
fi
echo ""

# ---------------------------------------------------------------------------
# 2. Validación estructural — archivos raíz
# ---------------------------------------------------------------------------
echo ">> 2. Estructura raíz"
check_file "$REPO_ROOT/AGENTS.md"            "AGENTS.md"
check_file "$REPO_ROOT/README.md"            "README.md"
check_file "$REPO_ROOT/feature_list.json"    "feature_list.json"
check_file "$REPO_ROOT/progress.md"          "progress.md"
check_file "$REPO_ROOT/session-handoff.md"   "session-handoff.md"
echo ""

# ---------------------------------------------------------------------------
# 3. Validación estructural — harness/
# ---------------------------------------------------------------------------
echo ">> 3. Estructura harness/"
check_dir  "$REPO_ROOT/harness"                                   "harness/"
check_file "$REPO_ROOT/harness/README.md"                        "harness/README.md"
check_file "$REPO_ROOT/harness/manifest.json"                    "harness/manifest.json"
check_dir  "$REPO_ROOT/harness/extraction"                        "harness/extraction/"
check_file "$REPO_ROOT/harness/extraction/README.md"             "harness/extraction/README.md"
check_file "$REPO_ROOT/harness/extraction/schemas/extraction.schema.json" \
           "harness/extraction/schemas/extraction.schema.json"
check_dir  "$REPO_ROOT/harness/extraction/outputs"                "harness/extraction/outputs/"
check_dir  "$REPO_ROOT/harness/merge"                             "harness/merge/"
check_file "$REPO_ROOT/harness/merge/README.md"                  "harness/merge/README.md"
check_dir  "$REPO_ROOT/harness/verification"                      "harness/verification/"
check_file "$REPO_ROOT/harness/verification/README.md"           "harness/verification/README.md"
check_file "$REPO_ROOT/harness/verification/verification.schema.json" \
           "harness/verification/verification.schema.json"
check_dir  "$REPO_ROOT/harness/gates"                             "harness/gates/"
check_file "$REPO_ROOT/harness/gates/README.md"                  "harness/gates/README.md"
check_file "$REPO_ROOT/harness/gates/gate_status.json"           "harness/gates/gate_status.json"
check_dir  "$REPO_ROOT/harness/change_requests"                   "harness/change_requests/"
echo ""

# ---------------------------------------------------------------------------
# 4. Validación estructural — docs/
# ---------------------------------------------------------------------------
echo ">> 4. Estructura docs/"
check_dir  "$REPO_ROOT/docs"                   "docs/"
check_file "$REPO_ROOT/docs/README.md"         "docs/README.md"
check_dir  "$REPO_ROOT/docs/context"           "docs/context/"
check_file "$REPO_ROOT/docs/context/README.md" "docs/context/README.md"
check_dir  "$REPO_ROOT/docs/decisions"         "docs/decisions/"
check_dir  "$REPO_ROOT/docs/policies"          "docs/policies/"
echo ""

# ---------------------------------------------------------------------------
# 5. Validación estructural — implementation/, scripts/, tests/, release/
# ---------------------------------------------------------------------------
echo ">> 5. Estructura implementation/ scripts/ tests/ release/"
check_dir  "$REPO_ROOT/implementation"                      "implementation/"
check_file "$REPO_ROOT/implementation/requirements.md"      "implementation/requirements.md"
check_file "$REPO_ROOT/implementation/architecture.md"      "implementation/architecture.md"
check_file "$REPO_ROOT/implementation/api_contracts.md"     "implementation/api_contracts.md"
check_file "$REPO_ROOT/implementation/data_flow.md"         "implementation/data_flow.md"
check_file "$REPO_ROOT/implementation/test_plan.md"         "implementation/test_plan.md"
check_file "$REPO_ROOT/implementation/conflict_register.md" "implementation/conflict_register.md"
check_dir  "$REPO_ROOT/scripts"                             "scripts/"
check_file "$REPO_ROOT/scripts/validate_manifest.py"        "scripts/validate_manifest.py"
check_file "$REPO_ROOT/scripts/validate_requirements.py"    "scripts/validate_requirements.py"
check_file "$REPO_ROOT/scripts/validate_gates.py"           "scripts/validate_gates.py"
check_dir  "$REPO_ROOT/tests"                               "tests/"
check_dir  "$REPO_ROOT/tests/unit"                         "tests/unit/"
check_dir  "$REPO_ROOT/tests/integration"                  "tests/integration/"
check_dir  "$REPO_ROOT/tests/acceptance"                   "tests/acceptance/"
check_dir  "$REPO_ROOT/tests/regression"                   "tests/regression/"
check_dir  "$REPO_ROOT/tests/security"                     "tests/security/"
check_dir  "$REPO_ROOT/src"                                "src/"
check_dir  "$REPO_ROOT/release"                            "release/"
echo ""

# ---------------------------------------------------------------------------
# 6. Verificar que no existe código funcional de SwingPilot en src/
# ---------------------------------------------------------------------------
echo ">> 6. Control: ausencia de código funcional en src/"
SRC_FILES=$(find "$REPO_ROOT/src" -type f ! -name ".gitkeep" 2>/dev/null | wc -l)
if [ "$SRC_FILES" -eq 0 ]; then
    echo "  [OK] src/ vacío (correcto para FASE 0)"
else
    echo "  [WARN] src/ contiene $SRC_FILES archivo(s) — verificar si están autorizados"
fi
echo ""

# ---------------------------------------------------------------------------
# 7. Ejecución de scripts de validación
# ---------------------------------------------------------------------------
echo ">> 7. Scripts de validación"

if command -v python3 &>/dev/null; then
    echo "  Running validate_manifest.py..."
    if python3 "$REPO_ROOT/scripts/validate_manifest.py"; then
        echo "  [OK] validate_manifest.py"
    else
        echo "  [FAIL] validate_manifest.py"
        EXIT_CODE=1
    fi

    echo "  Running validate_requirements.py..."
    if python3 "$REPO_ROOT/scripts/validate_requirements.py"; then
        echo "  [OK] validate_requirements.py"
    else
        echo "  [FAIL] validate_requirements.py"
        EXIT_CODE=1
    fi

    echo "  Running validate_gates.py..."
    if python3 "$REPO_ROOT/scripts/validate_gates.py"; then
        echo "  [OK] validate_gates.py"
    else
        echo "  [FAIL] validate_gates.py"
        EXIT_CODE=1
    fi
else
    echo "  [SKIP] python3 not found — skipping validation scripts"
fi
echo ""

# ---------------------------------------------------------------------------
# 8. Resumen de gates
# ---------------------------------------------------------------------------
echo ">> 8. Estado de gates"
if command -v python3 &>/dev/null && [ -f "$REPO_ROOT/harness/gates/gate_status.json" ]; then
    python3 - <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(__file__).parent if '__file__' in dir() else Path('.')
gates_path = Path(sys.argv[0]).parent.parent / "harness" / "gates" / "gate_status.json" if len(sys.argv) > 0 else Path("harness/gates/gate_status.json")

import os
gates_path = Path(os.environ.get('REPO_ROOT', '.')) / "harness" / "gates" / "gate_status.json"
with open(gates_path) as f:
    data = json.load(f)
for g in data.get("gates", []):
    marker = "(*)" if g.get("requires_human_approval") else "   "
    print(f"  {marker} {g['id']:3s} | {g['status']:8s} | {g['name']}")
print("  (*) = requiere aprobación humana")
PYEOF
else
    echo "  [SKIP] python3 not available"
fi
echo ""

# ---------------------------------------------------------------------------
# Resultado final
# ---------------------------------------------------------------------------
echo "============================================================"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo " RESULT: OK — Harness environment is ready"
else
    echo " RESULT: FAIL — One or more checks failed (see above)"
fi
echo "============================================================"

exit "$EXIT_CODE"
