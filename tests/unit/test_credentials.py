"""FEAT-007 — REQ-G-058, REQ-G-059, REQ-G-093, REQ-G-033; TC-SEC-001, TC-SEC-002, TC-SEC-006, TC-AC-05."""
import ast
import json
import pickle
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from swingpilot.ai import AIOrchestrator, AIProviderAdapter  # noqa: E402
from swingpilot.ai.orchestrator import ALLOWED_EMITS  # noqa: E402
from swingpilot.contracts import new_message  # noqa: E402
from swingpilot.security import (  # noqa: E402
    COMPONENT_SCOPES, CredentialError, CredentialVault, Secret, process_env_violations,
)
from test_orchestrator import SYNTH, RoutingClient, make_cycle  # noqa: E402

VALUES = {"ANTHROPIC_API_KEY": "sk-ant-test-AAAAAAAAAAAA", "BINANCE_API_KEY": "binKEY1234567890",
          "BINANCE_API_SECRET": "binSECRET0987654321", "TELEGRAM_BOT_TOKEN": "123456:telegramTOKENxyz"}


@pytest.fixture
def vault(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentario\n" + "\n".join(f'{k}="{v}"' for k, v in VALUES.items())
                   + "\nOTRA_VARIABLE=ignorada\n", encoding="utf-8")
    return CredentialVault.from_env_file(env)


# TC-SEC-002: ámbitos
def test_execution_engine_is_the_only_holder_of_binance_credentials(vault):
    ex = vault.for_component("execution_engine")
    assert set(ex) == {"BINANCE_API_KEY", "BINANCE_API_SECRET"}
    holders = [c for c, names in COMPONENT_SCOPES.items() if names & {"BINANCE_API_KEY", "BINANCE_API_SECRET"}]
    assert holders == ["execution_engine"]


@pytest.mark.parametrize("component", ["ai_orchestrator", "market_analyst", "macro_analyst",
                                       "strategy_analyst", "decision_synthesis", "risk_analyst",
                                       "risk_manager", "unknown"])
def test_llm_and_other_components_get_no_credentials(vault, component):
    with pytest.raises(CredentialError):
        vault.for_component(component)


def test_ai_provider_gets_only_anthropic_key(vault):
    assert set(vault.for_component("ai_provider")) == {"ANTHROPIC_API_KEY"}


def test_scoped_view_is_read_only(vault):
    creds = vault.for_component("ai_provider")
    with pytest.raises(TypeError):
        creds["BINANCE_API_KEY"] = Secret("x")


def test_missing_credentials_fail_closed():
    with pytest.raises(CredentialError, match="BINANCE_API_SECRET"):
        CredentialVault({"BINANCE_API_KEY": "k"}).for_component("execution_engine")


def test_unrelated_variables_are_not_loaded(vault):
    assert "OTRA_VARIABLE" not in repr(vault)


# Secret no se filtra por repr/str/JSON/pickle (TC-SEC-006)
def test_secret_does_not_leak_through_representations(vault):
    s = vault.for_component("telegram_bot")["TELEGRAM_BOT_TOKEN"]
    assert VALUES["TELEGRAM_BOT_TOKEN"] not in repr(s) + str(s) + f"{s}" + repr(vault)
    with pytest.raises(TypeError):
        json.dumps({"t": s})
    with pytest.raises(TypeError):
        pickle.dumps(s)
    assert s != VALUES["TELEGRAM_BOT_TOKEN"] and s.reveal() == VALUES["TELEGRAM_BOT_TOKEN"]


def test_loading_env_file_does_not_touch_process_env(tmp_path, monkeypatch):
    for k in VALUES:
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text("\n".join(f"{k}={v}" for k, v in VALUES.items()), encoding="utf-8")
    CredentialVault.from_env_file(env)
    import os
    assert not any(k in os.environ for k in VALUES)


def test_process_env_with_binance_or_telegram_is_a_violation():
    assert process_env_violations({"BINANCE_API_SECRET": "x", "TELEGRAM_BOT_TOKEN": "y", "PATH": "/"}) == \
        ["BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN"]
    assert process_env_violations({"ANTHROPIC_API_KEY": "x"}) == []


def test_redact_and_contains_secret(vault):
    text = f"error con clave {VALUES['BINANCE_API_SECRET']}"
    assert vault.contains_secret(text)
    assert vault.redact(text) == "error con clave ***"


# Fugas hacia el LLM: la llamada no se envía
def test_adapter_blocks_call_when_secret_in_content(vault):
    c = RoutingClient()
    a = AIProviderAdapter(c, sleep=lambda s: None, leak_check=vault.contains_secret)
    r = a.call_agent("market_analyst", system="s",
                     user_content=json.dumps({"agent": "market_analyst", "x": VALUES["BINANCE_API_KEY"]}),
                     output_schema={"type": "object"})
    assert r.error["code"] == "SECRET_LEAK_BLOCKED" and c.calls == []


def test_cycle_with_leaked_secret_fails_closed_without_sending(vault):
    c = RoutingClient(**SYNTH)
    req, p2 = make_cycle()
    req = new_message(source="trading_engine", destination="ai_orchestrator",
                      message_type="ANALYSIS_REQUESTED", data_timestamp_utc=req["data_timestamp_utc"],
                      timeframe="H4", correlation_id=req["correlation_id"],
                      payload={"market_context": {"note": VALUES["BINANCE_API_SECRET"]}, "macro_context": {}})
    o = AIOrchestrator(AIProviderAdapter(c, sleep=lambda s: None, leak_check=vault.contains_secret))
    r = o.run_cycle(req, p2)
    assert r.outcome == "FAILED" and r.outputs["market_analyst"]["error"]["code"] == "SECRET_LEAK_BLOCKED"
    assert "market_analyst" not in c.agents_called()
    assert VALUES["BINANCE_API_SECRET"] not in json.dumps(r.events)


def test_from_vault_builds_client_with_scoped_key(vault):
    a = AIProviderAdapter.from_vault(vault)
    assert a._client.api_key == VALUES["ANTHROPIC_API_KEY"]
    assert a._client.max_retries == 0 and a._leak_check is not None


# REQ-G-058/059, TC-AC-05: la capa de IA no puede emitir órdenes ni decisiones
def test_ai_layer_may_emit_only_analysis_events():
    assert ALLOWED_EMITS == {"MARKET_ANALYSIS_COMPLETED", "MACRO_ANALYSIS_COMPLETED",
                             "STRATEGY_ANALYSIS_COMPLETED", "DECISION_SYNTHESIS_COMPLETED",
                             "RISK_ANALYSIS_COMPLETED"}


@pytest.mark.parametrize("etype", ["ORDER_SUBMITTED", "TRADE_PROPOSAL", "RISK_APPROVED",
                                   "AUTHORIZATION_EXPIRED", "OPERATION_STATE_CHANGED"])
def test_orchestrator_refuses_to_emit_authority_events(etype):
    o = AIOrchestrator(AIProviderAdapter(RoutingClient(), sleep=lambda s: None))
    msg = new_message(source="ai_orchestrator", destination="x", message_type=etype,
                      data_timestamp_utc="2026-11-19T12:00:00Z", payload={})
    from swingpilot.ai.orchestrator import CycleResult
    with pytest.raises(PermissionError):
        o._emit(CycleResult(correlation_id=msg["correlation_id"], outcome="NOT_RUN"), msg)


# Aislamiento estático: la capa de IA no importa exchange, ejecución ni credenciales
ALLOWED_AI_IMPORTS = {"swingpilot.contracts", "swingpilot.audit", "swingpilot.ai", "anthropic", "jsonschema"}
STDLIB_OK = {"json", "time", "uuid", "copy", "re", "sqlite3", "threading", "concurrent", "dataclasses",
             "datetime", "typing", "pathlib", "zoneinfo", "__future__"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                yield f"swingpilot.{path.parent.name}"  # import relativo dentro del mismo paquete
            else:
                yield node.module


@pytest.mark.parametrize("path", sorted((ROOT / "src" / "swingpilot" / "ai").glob("*.py")) +
                         [ROOT / "src" / "swingpilot" / "contracts" / "agents.py"], ids=lambda p: p.name)
def test_ai_modules_import_nothing_outside_allowlist(path):
    bad = [m for m in _imports(path)
           if m.split(".")[0] not in STDLIB_OK
           and not any(m == a or m.startswith(a + ".") for a in ALLOWED_AI_IMPORTS)]
    assert bad == [], f"{path.name} importa {bad}"


def test_ai_modules_do_not_reference_security_module():
    for p in (ROOT / "src" / "swingpilot" / "ai").glob("*.py"):
        assert "swingpilot.security" not in p.read_text(encoding="utf-8")


def test_env_example_has_names_but_no_values():
    lines = [l for l in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
             if l and not l.startswith("#")]
    assert {l.split("=")[0] for l in lines} == set(VALUES)
    assert all(l.endswith("=") for l in lines)
