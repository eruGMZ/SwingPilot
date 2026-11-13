#!/usr/bin/env python3
"""
validate_manifest.py — Valida harness/manifest.json

Checks:
1. El archivo existe y es JSON válido.
2. Cumple la estructura esperada (metadata + documents).
3. Cada documento tiene los campos obligatorios.
4. Los SHA-256 tienen el formato correcto (64 hex chars).
5. Los IDs de documentos son únicos.
6. Las rutas referenciadas existen en el repositorio (si status no es PENDING).
7. Coherencia entre processing_status y los outputs en harness/extraction/outputs/.

Retorna exit code 0 si todo OK, 1 si hay errores.
No aprueba ningún gate: solo informa el estado.
"""

import json
import sys
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = REPO_ROOT / "harness" / "manifest.json"
EXTRACTION_OUTPUTS = REPO_ROOT / "harness" / "extraction" / "outputs"

REQUIRED_DOC_FIELDS = [
    "id", "name", "path", "type", "version",
    "sha256", "registered_at", "integrity_status", "processing_status"
]

SHA256_PATTERN = re.compile(r'^[a-f0-9]{64}$')

VALID_INTEGRITY_STATUSES = {"PENDING", "VERIFIED", "FAILED", "MISSING"}
VALID_PROCESSING_STATUSES = {"PENDING", "EXTRACTED", "MERGED", "VERIFIED"}

errors = []
warnings = []


def check(condition, message, is_error=True):
    if not condition:
        if is_error:
            errors.append(message)
        else:
            warnings.append(message)


def validate():
    # 1. File existence and JSON validity
    if not MANIFEST_PATH.exists():
        errors.append(f"FAIL: manifest.json not found at {MANIFEST_PATH}")
        return

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"FAIL: manifest.json is not valid JSON: {e}")
        return

    # 2. Top-level structure
    check("metadata" in manifest, "FAIL: manifest.json missing 'metadata' field")
    check("documents" in manifest, "FAIL: manifest.json missing 'documents' field")

    if "documents" not in manifest:
        return

    documents = manifest["documents"]
    check(isinstance(documents, list), "FAIL: 'documents' must be an array")

    if not isinstance(documents, list):
        return

    # Empty manifest is valid in FASE 0
    if len(documents) == 0:
        print("INFO: manifest.json has 0 documents (expected in FASE 0 — OK)")
        return

    # 3. Per-document validation
    seen_ids = {}
    for i, doc in enumerate(documents):
        doc_ref = doc.get("id", f"document[{i}]")

        for field in REQUIRED_DOC_FIELDS:
            check(
                field in doc,
                f"FAIL: document '{doc_ref}' missing required field '{field}'"
            )

        if "id" in doc:
            if doc["id"] in seen_ids:
                errors.append(f"FAIL: duplicate document id '{doc['id']}' at index {i} and {seen_ids[doc['id']]}")
            else:
                seen_ids[doc["id"]] = i

        # 4. SHA-256 format
        if "sha256" in doc:
            sha = doc["sha256"]
            if sha != "PENDING":
                check(
                    bool(SHA256_PATTERN.match(sha)),
                    f"FAIL: document '{doc_ref}' has invalid sha256 format: '{sha}'"
                )

        # 5. Integrity status values
        if "integrity_status" in doc:
            check(
                doc["integrity_status"] in VALID_INTEGRITY_STATUSES,
                f"FAIL: document '{doc_ref}' has unknown integrity_status '{doc['integrity_status']}'"
            )

        # 6. Processing status values
        if "processing_status" in doc:
            check(
                doc["processing_status"] in VALID_PROCESSING_STATUSES,
                f"FAIL: document '{doc_ref}' has unknown processing_status '{doc['processing_status']}'"
            )

        # 7. Path existence check (only if integrity_status is VERIFIED)
        if doc.get("integrity_status") == "VERIFIED" and "path" in doc:
            full_path = REPO_ROOT / doc["path"]
            check(
                full_path.exists(),
                f"FAIL: document '{doc_ref}' has integrity_status=VERIFIED but path does not exist: {doc['path']}"
            )

        # 8. Output coherence check
        if doc.get("processing_status") == "EXTRACTED":
            output_file = EXTRACTION_OUTPUTS / f"{doc.get('id', 'unknown')}.json"
            check(
                output_file.exists(),
                f"WARN: document '{doc_ref}' has processing_status=EXTRACTED but no output found at {output_file}",
                is_error=False
            )


def main():
    validate()

    print("=" * 60)
    print("validate_manifest.py — SwingPilot Harness")
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
        print("\nRESULT: OK — manifest.json is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
