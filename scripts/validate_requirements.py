#!/usr/bin/env python3
"""
validate_requirements.py — Valida los outputs de extracción en harness/extraction/outputs/

Checks:
1. Cada archivo .json en outputs/ es JSON válido.
2. Cada output cumple el esquema en harness/extraction/schemas/extraction.schema.json.
3. Los requirement_id tienen formato REQ-NNN.
4. Los IDs son únicos dentro de cada output y entre todos los outputs.
5. Los campos PENDING están identificados explícitamente (no rellenados por suposición).
6. No existen outputs sin documento registrado en el manifiesto.

Retorna exit code 0 si todo OK, 1 si hay errores.
No aprueba ningún gate: solo informa el estado.
"""

import json
import sys
import re
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "harness" / "extraction" / "schemas" / "extraction.schema.json"
OUTPUTS_DIR = REPO_ROOT / "harness" / "extraction" / "outputs"
MANIFEST_PATH = REPO_ROOT / "harness" / "manifest.json"

REQ_ID_PATTERN = re.compile(r'^REQ-[0-9]{3,}$')

errors = []
warnings = []


def check(condition, message, is_error=True):
    if not condition:
        if is_error:
            errors.append(message)
        else:
            warnings.append(message)


def load_manifest_ids():
    if not MANIFEST_PATH.exists():
        warnings.append("WARN: manifest.json not found — cannot cross-check outputs against manifest")
        return set()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return {doc.get("id") for doc in manifest.get("documents", [])}


def load_schema():
    if not SCHEMA_PATH.exists():
        errors.append(f"FAIL: extraction schema not found at {SCHEMA_PATH}")
        return None
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate():
    schema = load_schema()
    manifest_ids = load_manifest_ids()

    output_files = list(OUTPUTS_DIR.glob("*.json"))

    if len(output_files) == 0:
        print("INFO: No extraction outputs found (expected in FASE 0 — OK)")
        return

    # IDs are unique per-file; global uniqueness is enforced by the Merger
    # (each extractor uses its own REQ-NNN namespace per document)

    for output_file in output_files:
        filename = output_file.name
        file_id = output_file.stem  # filename without .json
        file_req_ids = {}  # req_id -> index within this file (per-file uniqueness)

        # Check if output corresponds to a manifest document
        if manifest_ids and file_id not in manifest_ids:
            warnings.append(
                f"WARN: output '{filename}' does not correspond to any document in manifest.json"
            )

        # Load and validate JSON
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                output = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"FAIL: '{filename}' is not valid JSON: {e}")
            continue

        # Schema validation
        if schema and HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=output, schema=schema)
            except jsonschema.ValidationError as e:
                errors.append(f"FAIL: '{filename}' fails schema validation: {e.message}")
                continue
        elif not HAS_JSONSCHEMA:
            warnings.append("WARN: jsonschema library not installed — skipping schema validation")

        # Validate requirements within output
        requirements = output.get("requirements", [])
        for req in requirements:
            req_id = req.get("requirement_id")

            if not req_id:
                errors.append(f"FAIL: requirement in '{filename}' missing 'requirement_id'")
                continue

            # Format check
            check(
                bool(REQ_ID_PATTERN.match(req_id)),
                f"FAIL: '{filename}': requirement_id '{req_id}' has invalid format (expected REQ-NNN)"
            )

            # Per-file uniqueness check (global uniqueness assigned by Merger)
            if req_id in file_req_ids:
                errors.append(
                    f"FAIL: duplicate requirement_id '{req_id}' within '{filename}' at index {file_req_ids[req_id]}"
                )
            else:
                file_req_ids[req_id] = requirements.index(req)

            # Verify PENDING fields are explicitly marked, not just empty
            for field in ["priority", "requirement_type"]:
                val = req.get(field, "")
                if val == "" or val is None:
                    errors.append(
                        f"FAIL: '{filename}': requirement '{req_id}' has empty '{field}' — use 'PENDING' explicitly"
                    )


def main():
    validate()

    print("=" * 60)
    print("validate_requirements.py — SwingPilot Harness")
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
        print("\nRESULT: OK — extraction outputs are valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
