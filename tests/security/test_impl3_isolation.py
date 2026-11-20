"""IMPL-3 — restricciones de DEC-017 / DEC-018 sobre los paquetes nuevos (FEAT-015/016/017/019).

- Sin credenciales privadas de Binance ni endpoints firmados (DEC-017 Q41; DEC-018).
- Los motores y la investigación no llaman a la API de Claude (REQ-G-057, TC-AC-07).
- Ninguna estrategia ni modelo activado (DEC-018).
"""
import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "swingpilot"
PACKAGES = ("market_data", "research", "ml", "engines")
FORBIDDEN_MODULES = {"anthropic", "swingpilot.security.credentials", "dotenv"}
# Los motores no importan la capa de IA; solo engines/cycle.py la orquesta (Fase 3/4).
AI_ALLOWED = {"cycle.py"}
FORBIDDEN_TEXT = [r"BINANCE_API_(KEY|SECRET)", r"X-MBX-APIKEY", r"/api/v3/order", r"/api/v3/account",
                  r"/sapi/", r"hmac", r"os\.environ", r"getenv", r"\.env\b"]


def _files():
    for pkg in PACKAGES:
        yield from (SRC / pkg).rglob("*.py")


def test_new_packages_import_no_llm_or_credentials():
    for py in _files():
        tree = ast.parse(py.read_text())
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        forbidden = FORBIDDEN_MODULES | ({"swingpilot.ai"} if py.name not in AI_ALLOWED or py.parent.name != "engines" else set())
        bad = {m for m in mods if any(m == f or m.startswith(f + ".") for f in forbidden)}
        assert not bad, f"{py}: {bad}"


def test_new_packages_have_no_private_endpoints_or_secrets():
    for py in _files():
        text = py.read_text()
        for pat in FORBIDDEN_TEXT:
            assert not re.search(pat, text), f"{py}: {pat}"


def test_no_strategy_definitions_in_impl3_packages():
    """DEC-018: no activar estrategias. No existe paquete de estrategias ni definiciones del piloto."""
    assert not (SRC / "strategies").exists()
    for py in _files():
        assert "TF_H4" not in py.read_text(), py
