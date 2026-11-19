"""FEAT-007 — arranque de la capa de IA (REQ-G-033, REQ-G-093, REQ-G-096; INV-012)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from swingpilot.audit import SecretLeakError  # noqa: E402
from swingpilot.bootstrap import StartupError, build_ai_stack  # noqa: E402
from swingpilot.contracts import new_message  # noqa: E402
from test_orchestrator import SYNTH, RoutingClient, make_cycle  # noqa: E402

KEY = "sk-ant-test-BOOTSTRAP-123"
STATE = {"open_position": False, "locks": ["ACTIVE"], "safe_mode": False}


@pytest.fixture
def env(tmp_path):
    p = tmp_path / ".env"
    p.write_text(f"ANTHROPIC_API_KEY={KEY}\n", encoding="utf-8")
    p.chmod(0o600)
    return p


def build(env, tmp_path, client=None, state=STATE, mode="RESEARCH", environ=None):
    return build_ai_stack(env_path=env, mode=mode, data_dir=tmp_path / "var",
                          system_state=lambda: state, client=client or RoutingClient(**SYNTH),
                          environ={} if environ is None else environ)


def test_startup_violation_blocks(env, tmp_path):
    env.chmod(0o644)
    with pytest.raises(StartupError, match="ENV_FILE_PERMISSIONS"):
        build(env, tmp_path)
    assert not (tmp_path / "var").exists()  # nada se crea si no arranca


def test_secret_in_process_env_blocks(env, tmp_path):
    with pytest.raises(StartupError, match="SECRET_IN_PROCESS_ENV"):
        build(env, tmp_path, environ={"BINANCE_API_SECRET": "x"})


def test_debug_log_in_live_blocks(env, tmp_path):
    with pytest.raises(StartupError, match="ANTHROPIC_DEBUG_LOG_IN_LIVE"):
        build(env, tmp_path, mode="LIVE", environ={"ANTHROPIC_LOG": "debug"})


def test_stack_runs_a_cycle_with_all_protections_wired(env, tmp_path):
    s = build(env, tmp_path)
    req, p2 = make_cycle()
    for m in [req, *p2]:
        s.store.append(m)
    r = s.orchestrator.run_cycle(req, p2)
    assert r.outcome == "COMPLETED"
    assert s.store.get_chain(req["correlation_id"]).complete
    assert s.budget.spent_this_month() > 0  # el costo se registra
    s.close()


def test_store_rejects_secrets_when_wired(env, tmp_path):
    s = build(env, tmp_path)
    with pytest.raises(SecretLeakError):
        s.store.append(new_message(source="x", destination="y", message_type="ANALYSIS_REQUESTED",
                                   data_timestamp_utc="2026-11-19T12:00:00Z", payload={"k": KEY}))
    s.close()


def test_adapter_leak_check_wired(env, tmp_path):
    c = RoutingClient(**SYNTH)
    s = build(env, tmp_path, client=c)
    r = s.adapter.call_agent("market_analyst", system="s",
                             user_content=json.dumps({"agent": "market_analyst", "k": KEY}),
                             output_schema={"type": "object"})
    assert r.error["code"] == "SECRET_LEAK_BLOCKED" and c.calls == []
    s.close()


def test_entry_gate_wired_blocks_with_open_position(env, tmp_path):
    c = RoutingClient(**SYNTH)
    s = build(env, tmp_path, client=c, state={**STATE, "open_position": True})
    r = s.orchestrator.run_cycle(*make_cycle())
    assert r.outcome == "BLOCKED" and c.calls == []
    s.close()


def test_budget_warning_goes_to_audit_store(env, tmp_path):
    s = build(env, tmp_path)
    s.budget.record("x", "claude-sonnet-5-5", 0, 400_000)  # $4
    rows = [json.loads(r[0]) for r in s.store._db.execute("SELECT message_json FROM audit_events")]
    assert [m["message_type"] for m in rows] == ["AI_BUDGET_WARNING"]
    s.close()


def test_redact_wired_into_orchestrator(env, tmp_path):
    from types import SimpleNamespace as NS
    bad = NS(stop_reason="end_turn", stop_details=None, model="claude-haiku-5-5",
             content=[NS(type="text", text=json.dumps({"agent": "x", "status": KEY}))],
             usage=NS(input_tokens=1, output_tokens=1))
    s = build(env, tmp_path, client=RoutingClient(macro_analyst=[bad, bad], **SYNTH))
    r = s.orchestrator.run_cycle(*make_cycle())  # sin redact, el EventStore lanzaría SecretLeakError
    assert r.outcome == "FAILED" and KEY not in r.outputs["macro_analyst"]["error"]["message"]
    s.close()


def test_real_client_built_from_vault(env, tmp_path):
    s = build_ai_stack(env_path=env, mode="RESEARCH", data_dir=tmp_path / "var",
                       system_state=lambda: STATE, environ={})
    assert s.adapter._client.api_key == KEY and s.adapter._client.max_retries == 0
    s.close()
