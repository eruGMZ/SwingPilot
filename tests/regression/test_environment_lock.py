"""Regresión ENV-01..04: el entorno de pruebas coincide con el lock con hashes.

Origen: harness/verification/IMPL-3_entorno_reproducibilidad.md (ENV-01..04),
autorizado por el propietario el 2026-11-20. Si una de estas pruebas falla, la
evidencia de la suite no es comparable con la registrada: recrear el entorno con
scripts/setup_env.sh.
"""

from __future__ import annotations

import platform
import re
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "requirements-dev.lock"
DIRECT = REPO / "requirements-dev.txt"

_PIN = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s;\\]+)\s*(;\s*([^\\]+?))?\s*\\?$")


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _lock_entries() -> list[tuple[str, str, str | None]]:
    out = []
    for line in LOCK.read_text().splitlines():
        m = _PIN.match(line)
        if m:
            out.append((_norm(m.group(1)), m.group(2), m.group(4)))
    return out


def _marker_applies(marker: str | None) -> bool:
    if marker is None:
        return True
    m = re.fullmatch(r"sys_platform\s*(==|!=)\s*'([^']+)'", marker.strip())
    assert m, f"marcador no soportado por la prueba: {marker!r}"
    import sys

    return (sys.platform == m.group(2)) == (m.group(1) == "==")


def test_python_version_matches_python_version_file():
    expected = (REPO / ".python-version").read_text().strip()
    assert platform.python_version() == expected


def test_every_lock_entry_has_sha256_hashes():
    lines = LOCK.read_text().splitlines()
    for i, line in enumerate(lines):
        if _PIN.match(line):
            assert i + 1 < len(lines) and "--hash=sha256:" in lines[i + 1], line


def test_direct_dependencies_are_exactly_pinned_and_locked():
    locked = {name: ver for name, ver, _ in _lock_entries()}
    direct = [
        ln.strip() for ln in DIRECT.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    assert direct, "requirements-dev.txt sin dependencias"
    for req in direct:
        assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[^\s]+", req), f"sin versión exacta: {req}"
        name, ver = req.split("==")
        assert locked.get(_norm(name)) == ver, f"{req} no coincide con el lock"


def test_installed_distributions_match_lock_exactly():
    expected = {name: ver for name, ver, mk in _lock_entries() if _marker_applies(mk)}
    installed = {
        _norm(d.metadata["Name"]): d.version
        for d in metadata.distributions()
    }
    # pip puede existir en un venv sin estar en el lock; no se usa para instalar.
    installed.pop("pip", None)
    assert installed == expected


def test_scikit_learn_not_installed():
    # DEC-017 Q44: sin modelo entrenado; scikit-learn excluido (ENV-02).
    names = {_norm(d.metadata["Name"]) for d in metadata.distributions()}
    assert not names & {"scikit-learn", "scipy", "joblib", "threadpoolctl"}
