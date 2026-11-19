"""Prevención de fugas de credenciales a registros — REQ-G-033, REQ-G-091, REQ-G-093;
TC-SEC-004, TC-SEC-006 (parcial); FEAT-003, FEAT-007."""
import json
import logging
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import anthropic
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from swingpilot.ai import AIOrchestrator, AIProviderAdapter  # noqa: E402
from swingpilot.audit import EventStore, SecretLeakError  # noqa: E402
from swingpilot.contracts import new_message  # noqa: E402
from swingpilot.security import CredentialVault, startup_violations  # noqa: E402
from test_orchestrator import SYNTH, RoutingClient, make_cycle  # noqa: E402

SECRET = "binSECRET0987654321"
VAULT = CredentialVault({"BINANCE_API_KEY": "binKEY1234567890", "BINANCE_API_SECRET": SECRET,
                         "ANTHROPIC_API_KEY": "sk-ant-test-AAAAAAAAAAAA"})


def msg(payload):
    return new_message(source="trading_engine", destination="ai_orchestrator",
                       message_type="ANALYSIS_REQUESTED", data_timestamp_utc="2026-11-19T12:00:00Z",
                       timeframe="H4", payload=payload)


def rows(path):
    return sqlite3.connect(path).execute("SELECT message_json FROM audit_events").fetchall()


# 1. Registro de auditoría: un mensaje con credencial no se escribe
def test_event_store_rejects_message_with_secret(tmp_path):
    s = EventStore(tmp_path / "a.db", secret_check=VAULT.contains_secret)
    with pytest.raises(SecretLeakError):
        s.append(msg({"nota": f"clave {SECRET}"}))
    assert s.count() == 0
    s.close()
    assert not any(SECRET in r[0] for r in rows(tmp_path / "a.db"))


def test_event_store_rejects_secret_in_any_field(tmp_path):
    s = EventStore(tmp_path / "a.db", secret_check=VAULT.contains_secret)
    m = msg({})
    m["source"] = SECRET
    with pytest.raises(SecretLeakError):
        s.append(m)
    assert s.count() == 0


def test_event_store_accepts_clean_messages(tmp_path):
    s = EventStore(tmp_path / "a.db", secret_check=VAULT.contains_secret)
    assert s.append(msg({"precio": 97000}))


def test_cycle_with_leaking_request_stops_before_writing(tmp_path):
    store = EventStore(tmp_path / "a.db", secret_check=VAULT.contains_secret)
    req, p2 = make_cycle()
    with pytest.raises(SecretLeakError):
        store.append(msg({"market_context": {"x": SECRET}}))
    o = AIOrchestrator(AIProviderAdapter(RoutingClient(**SYNTH), sleep=lambda s: None,
                                         leak_check=VAULT.contains_secret), store, redact=VAULT.redact)
    o.run_cycle(req, p2)  # ciclo limpio en el mismo almacén
    store.close()
    assert not any(SECRET in r[0] for r in rows(tmp_path / "a.db"))


# 2. Mensajes de error redactados antes de registrarse
def test_error_messages_are_redacted_in_events(tmp_path):
    store = EventStore(tmp_path / "a.db", secret_check=VAULT.contains_secret)
    # El modelo devuelve texto que no es JSON y contiene la credencial (caso hipotético)
    bad = NS(stop_reason="end_turn", stop_details=None, model="claude-haiku-5-5",
             content=[NS(type="text", text=f"no-json {SECRET}")], usage=NS(input_tokens=1, output_tokens=1))
    c = RoutingClient(market_analyst=[bad, bad], **SYNTH)
    o = AIOrchestrator(AIProviderAdapter(c, sleep=lambda s: None), store, redact=VAULT.redact)
    req, p2 = make_cycle()
    r = o.run_cycle(req, p2)
    assert r.outcome == "FAILED"
    store.close()
    assert not any(SECRET in r[0] for r in rows(tmp_path / "a.db"))


def test_out_of_contract_message_with_secret_value_is_redacted():
    leaky = {"agent": "x", "status": SECRET}  # valor inválido que jsonschema cita en el error
    bad = NS(stop_reason="end_turn", stop_details=None, model="claude-haiku-5-5",
             content=[NS(type="text", text=json.dumps(leaky))], usage=NS(input_tokens=1, output_tokens=1))
    c = RoutingClient(macro_analyst=[bad, bad], **SYNTH)
    o = AIOrchestrator(AIProviderAdapter(c, sleep=lambda s: None), redact=VAULT.redact)
    r = o.run_cycle(*make_cycle())
    err = r.outputs["macro_analyst"]["error"]
    assert err["code"] == "OUT_OF_CONTRACT" and SECRET not in err["message"]


# 3. Comprobaciones de arranque
@pytest.fixture
def env_file(tmp_path):
    p = tmp_path / ".env"
    p.write_text("ANTHROPIC_API_KEY=x\n", encoding="utf-8")
    p.chmod(0o600)
    return p


def test_clean_startup(env_file):
    assert startup_violations(env_file, "LIVE", {}) == []


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660])
def test_env_readable_by_others_blocks(env_file, mode):
    env_file.chmod(mode)
    assert startup_violations(env_file, "PAPER", {}) == [f"ENV_FILE_PERMISSIONS:{oct(mode)}"]


def test_env_400_is_accepted(env_file):
    env_file.chmod(0o400)
    assert startup_violations(env_file, "LIVE", {}) == []


def test_missing_env_blocks(tmp_path):
    assert startup_violations(tmp_path / "nope", "RESEARCH", {}) == ["ENV_FILE_MISSING"]


def test_secret_in_process_env_blocks(env_file):
    assert startup_violations(env_file, "RESEARCH", {"BINANCE_API_SECRET": "x"}) == \
        ["SECRET_IN_PROCESS_ENV:BINANCE_API_SECRET"]


@pytest.mark.parametrize("mode,expected", [("LIVE", ["ANTHROPIC_DEBUG_LOG_IN_LIVE"]), ("PAPER", []), ("RESEARCH", [])])
def test_debug_log_forbidden_only_in_live(env_file, mode, expected):
    assert startup_violations(env_file, mode, {"ANTHROPIC_LOG": "DEBUG"}) == expected


def test_unknown_mode_blocks(env_file):
    assert startup_violations(env_file, "live", {}) == ["MODE_UNKNOWN:live"]


# 4. Logs del SDK de Anthropic en nivel debug no contienen la clave (verificación local)
def test_sdk_debug_logs_do_not_contain_api_key(caplog):
    key = "sk-ant-FAKE-LEAKCHECK-123"
    caplog.set_level(logging.DEBUG)
    client = anthropic.Anthropic(api_key=key, base_url="http://127.0.0.1:9", max_retries=0, timeout=2)
    with pytest.raises(anthropic.APIConnectionError) as e:
        client.messages.create(model="claude-haiku-5-5", max_tokens=1,
                               messages=[{"role": "user", "content": "hi"}])
    assert caplog.records, "se esperaban logs de depuración"
    assert key not in caplog.text and key not in str(e.value) + repr(e.value) + repr(client)
