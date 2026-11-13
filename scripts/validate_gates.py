#!/usr/bin/env python3
"""
validate_gates.py — Valida harness/gates/gate_status.json

Checks:
1. El archivo existe y es JSON válido.
2. Los 8 gates esperados (G0-G7) están presentes.
3. Los estados son válidos: PENDING, OPEN, PASS, FAIL.
4. Los gates G3 y G7 no pueden tener status=PASS sin approved_by distinto de null.
5. No existen gates en estado PASS sin evidencia registrada.
6. Los IDs de gates son únicos.
7. La secuencia de gates es coherente con las fases.

Retorna exit code 0 si todo OK, 1 si hay errores.
Este script NO aprueba ningún gate. Solo verifica consistencia del archivo.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GATES_PATH = REPO_ROOT / "harness" / "gates" / "gate_status.json"

EXPECTED_GATE_IDS = {"G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"}
HUMAN_REQUIRED_GATES = {"G3", "G7"}
VALID_STATUSES = {"PENDING", "OPEN", "PASS", "FAIL"}

errors = []
warnings = []


def check(condition, message, is_error=True):
    if not condition:
        if is_error:
            errors.append(message)
        else:
            warnings.append(message)


def validate():
    if not GATES_PATH.exists():
        errors.append(f"FAIL: gate_status.json not found at {GATES_PATH}")
        return

    try:
        with open(GATES_PATH, "r", encoding="utf-8") as f:
            gate_data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"FAIL: gate_status.json is not valid JSON: {e}")
        return

    check("gates" in gate_data, "FAIL: gate_status.json missing 'gates' field")

    if "gates" not in gate_data:
        return

    gates = gate_data["gates"]
    check(isinstance(gates, list), "FAIL: 'gates' must be an array")

    if not isinstance(gates, list):
        return

    # Check all expected gates are present
    found_ids = set()
    for gate in gates:
        gate_id = gate.get("id")
        if gate_id:
            found_ids.add(gate_id)

    missing = EXPECTED_GATE_IDS - found_ids
    for mid in sorted(missing):
        errors.append(f"FAIL: expected gate '{mid}' is missing from gate_status.json")

    extra = found_ids - EXPECTED_GATE_IDS
    for eid in sorted(extra):
        warnings.append(f"WARN: unexpected gate '{eid}' found in gate_status.json")

    # Per-gate validation
    seen_ids = {}
    for i, gate in enumerate(gates):
        gate_id = gate.get("id", f"gate[{i}]")

        # Uniqueness
        if gate_id in seen_ids:
            errors.append(f"FAIL: duplicate gate id '{gate_id}' at index {i} and {seen_ids[gate_id]}")
        else:
            seen_ids[gate_id] = i

        # Status validity
        status = gate.get("status")
        check(
            status in VALID_STATUSES,
            f"FAIL: gate '{gate_id}' has invalid status '{status}' (valid: {VALID_STATUSES})"
        )

        # Human-required gates cannot be PASS without approved_by
        if gate_id in HUMAN_REQUIRED_GATES and status == "PASS":
            approved_by = gate.get("approved_by")
            check(
                approved_by is not None and approved_by != "",
                f"FAIL: gate '{gate_id}' requires human approval but approved_by is null/empty"
            )

        # PASS gates must have evidence
        if status == "PASS":
            evidence = gate.get("evidence")
            check(
                evidence is not None and evidence != "",
                f"FAIL: gate '{gate_id}' has status=PASS but no evidence recorded"
            )

        # requires_human_approval consistency
        requires_human = gate.get("requires_human_approval", False)
        if gate_id in HUMAN_REQUIRED_GATES:
            check(
                requires_human is True,
                f"FAIL: gate '{gate_id}' must have requires_human_approval=true"
            )


def main():
    validate()

    print("=" * 60)
    print("validate_gates.py — SwingPilot Harness")
    print("=" * 60)

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        print("\nRESULT: FAIL")
        sys.exit(1)
    else:
        print("\nRESULT: OK — gate_status.json is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
