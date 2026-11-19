"""FEAT-006 — REQ-G-096, REQ-G-034; TC-AI-006, TC-AI-007, TC-AC-14."""
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from swingpilot.ai import (  # noqa: E402
    AIBudget, AIOrchestrator, AIProviderAdapter, EntryGate, budget_warning_emitter,
)
from swingpilot.ai.budget import call_cost_usd, UnknownModelPrice  # noqa: E402
from swingpilot.audit import EventStore  # noqa: E402
from test_orchestrator import SYNTH, RoutingClient, make_cycle  # noqa: E402


class Clock:
    def __init__(self, t): self.t = t
    def __call__(self): return self.t


NOV = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)


@pytest.fixture
def clock():
    return Clock(NOV)


@pytest.fixture
def budget(tmp_path, clock):
    b = AIBudget(tmp_path / "b.db", now=clock)
    yield b
    b.close()


# Precios DEC-009
def test_cost_formula_matches_dec009_prices():
    assert call_cost_usd("claude-haiku-5-5", 5000, 1500) == pytest.approx(0.00125)
    assert call_cost_usd("claude-sonnet-5-5", 5000, 1500) == pytest.approx(0.025)


def test_haiku_long_prompt_uses_higher_rate():
    assert call_cost_usd("claude-haiku-5-5", 200_000, 0) == pytest.approx(0.10)


def test_unknown_model_has_no_price():
    with pytest.raises(UnknownModelPrice):
        call_cost_usd("claude-opus-5-5", 1, 1)


# (5) registro y medición — TC-AC-14
def test_usage_is_recorded_and_summed(budget):
    budget.record("market_analyst", "claude-haiku-5-5", 5000, 1500)
    budget.record("decision_synthesis", "claude-sonnet-5-5", 5000, 1500)
    assert budget.spent_this_month() == pytest.approx(0.02625)


def test_incomplete_usage_rejected(budget):
    with pytest.raises(ValueError):
        budget.record("market_analyst", "claude-haiku-5-5", None, 10)


def test_usage_table_is_append_only(tmp_path, clock):
    b = AIBudget(tmp_path / "b.db", now=clock)
    b.record("market_analyst", "claude-haiku-5-5", 10, 10)
    b.close()
    raw = sqlite3.connect(tmp_path / "b.db")
    with pytest.raises(sqlite3.DatabaseError):
        raw.execute("DELETE FROM ai_usage")
    with pytest.raises(sqlite3.DatabaseError):
        raw.execute("UPDATE ai_usage SET cost_usd=0")


def test_spend_persists_across_restart(tmp_path, clock):
    b = AIBudget(tmp_path / "b.db", now=clock)
    b.record("x", "claude-sonnet-5-5", 0, 100_000)  # $1
    b.close()
    assert AIBudget(tmp_path / "b.db", now=clock).spent_this_month() == pytest.approx(1.0)


# (1) tope de $5
def test_cap_reached_at_five_dollars(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 499_999)
    assert budget.can_call()
    budget.record("x", "claude-sonnet-5-5", 0, 1)
    assert budget.cap_reached() and not budget.can_call()


def test_new_calendar_month_resets_spend(budget, clock):
    budget.record("x", "claude-sonnet-5-5", 0, 500_000)
    assert budget.cap_reached()
    clock.t = datetime(2026, 12, 1, 6, 0, 1, tzinfo=timezone.utc)  # 00:00:01 en Ciudad de México
    assert budget.spent_this_month() == 0 and budget.can_call()


def test_default_month_is_mexico_city(budget, clock):
    from zoneinfo import ZoneInfo
    assert budget._tz == ZoneInfo("America/Mexico_City")  # DEC-014 Q31
    clock.t = datetime(2026, 12, 1, 5, 59, tzinfo=timezone.utc)  # 30-nov 23:59 en CDMX
    assert budget._month() == "2026-11"
    clock.t = datetime(2026, 12, 1, 6, 0, tzinfo=timezone.utc)   # 1-dic 00:00 en CDMX
    assert budget._month() == "2026-12"


def test_month_boundary_follows_configured_timezone(tmp_path, clock):
    mx = timezone(timedelta(hours=-6))
    clock.t = datetime(2026, 12, 1, 3, tzinfo=timezone.utc)  # 30-nov 21:00 en UTC-6
    b = AIBudget(tmp_path / "b.db", now=clock, tz=mx)
    b.record("x", "claude-sonnet-5-5", 0, 100_000)
    clock.t = datetime(2026, 11, 30, 12, tzinfo=timezone.utc)
    assert b.spent_this_month() == pytest.approx(1.0)


# (2) TC-AI-006: aviso a $4, una sola vez por mes
def test_warning_once_per_month(tmp_path, clock):
    seen = []
    b = AIBudget(tmp_path / "b.db", now=clock, on_warning=lambda m, s: seen.append((m, s)))
    b.record("x", "claude-sonnet-5-5", 0, 390_000)  # $3.90
    assert seen == []
    b.record("x", "claude-sonnet-5-5", 0, 10_000)   # $4.00
    b.record("x", "claude-sonnet-5-5", 0, 10_000)   # $4.10
    assert [m for m, _ in seen] == ["2026-11"]
    b.close()
    b2 = AIBudget(tmp_path / "b.db", now=clock, on_warning=lambda m, s: seen.append((m, s)))
    b2.record("x", "claude-sonnet-5-5", 0, 10_000)  # tras reinicio: no repite
    assert len(seen) == 1
    clock.t = datetime(2026, 12, 2, 12, tzinfo=timezone.utc)
    b2.record("x", "claude-sonnet-5-5", 0, 400_000)  # nuevo mes: nuevo aviso
    assert [m for m, _ in seen] == ["2026-11", "2026-12"]


def test_warning_emitted_as_event(tmp_path, clock):
    store = EventStore(tmp_path / "a.db")
    b = AIBudget(tmp_path / "b.db", now=clock, on_warning=budget_warning_emitter(store))
    b.record("x", "claude-sonnet-5-5", 0, 400_000)
    rows = store._db.execute("SELECT message_json FROM audit_events").fetchall()
    evts = [json.loads(r[0]) for r in rows]
    assert [e["message_type"] for e in evts] == ["AI_BUDGET_WARNING"]
    assert evts[0]["destination"] == "telegram_bot" and evts[0]["payload"]["month"] == "2026-11"


# (3) TC-AI-007: EntryGate
STATE_OK = {"open_position": False, "locks": ["ACTIVE"], "safe_mode": False}


@pytest.mark.parametrize("state,reason", [
    (STATE_OK, None),
    ({**STATE_OK, "open_position": True}, "OPEN_POSITION"),
    ({**STATE_OK, "locks": ["POSITION_OPEN"]}, "OPEN_POSITION"),
    ({**STATE_OK, "locks": ["LOSS_STREAK_LOCK"]}, "ENTRY_LOCK:LOSS_STREAK_LOCK"),
    ({**STATE_OK, "locks": ["MONTHLY_DRAWDOWN_LOCK", "EXCHANGE_DESYNC"]}, "ENTRY_LOCK:EXCHANGE_DESYNC,MONTHLY_DRAWDOWN_LOCK"),
    ({**STATE_OK, "locks": ["MONTHLY_TRADE_LIMIT_LOCK"]}, "ENTRY_LOCK:MONTHLY_TRADE_LIMIT_LOCK"),
    ({**STATE_OK, "locks": ["DATA_UNAVAILABLE"]}, "ENTRY_LOCK:DATA_UNAVAILABLE"),
    ({**STATE_OK, "locks": ["MANUAL_REVIEW"]}, "ENTRY_LOCK:MANUAL_REVIEW"),
    ({**STATE_OK, "safe_mode": True}, "SAFE_MODE"),
    ({**STATE_OK, "locks": ["SOMETHING_NEW"]}, "UNKNOWN_STATE:SOMETHING_NEW"),
    ({"locks": []}, "STATE_UNAVAILABLE"),
    ({**STATE_OK, "open_position": "no"}, "STATE_UNAVAILABLE"),
])
def test_entry_gate(budget, state, reason):
    assert EntryGate(lambda: state, budget)() == reason


def test_entry_gate_state_provider_failure_blocks(budget):
    def boom(): raise RuntimeError("risk manager caído")
    assert EntryGate(boom, budget)() == "STATE_UNAVAILABLE"


def test_entry_gate_blocks_on_cap(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 500_000)
    assert EntryGate(lambda: STATE_OK, budget)() == "AI_BUDGET_CAP_REACHED"


# Integración con orquestador y adaptador
def _orch(client, budget, state=STATE_OK):
    adapter = AIProviderAdapter(client, sleep=lambda s: None, budget=budget)
    return AIOrchestrator(adapter, precheck=EntryGate(lambda: state, budget))


def test_blocked_cycle_makes_zero_llm_calls(budget):
    c = RoutingClient(**SYNTH)
    r = _orch(c, budget, {**STATE_OK, "open_position": True}).run_cycle(*make_cycle())
    assert r.outcome == "BLOCKED" and c.calls == [] and budget.spent_this_month() == 0


def test_full_cycle_records_cost_of_every_call(budget):
    c = RoutingClient(**SYNTH)
    r = _orch(c, budget).run_cycle(*make_cycle())
    assert r.outcome == "COMPLETED"
    n = budget._db.execute("SELECT COUNT(*) FROM ai_usage").fetchone()[0]
    assert n == len(c.calls) == 4
    # RoutingClient: 10 in / 5 out por llamada
    expected = 3 * call_cost_usd("claude-haiku-5-5", 10, 5) + call_cost_usd("claude-sonnet-5-5", 10, 5)
    assert budget.spent_this_month() == pytest.approx(expected)


def test_cap_reached_mid_cycle_stops_further_calls(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 499_999)  # justo bajo el tope

    def pricey(inp):  # la síntesis nunca debería llamarse
        raise AssertionError("no debe invocarse")

    class Spender(RoutingClient):
        def _create(self, **kw):
            r = super()._create(**kw)
            return NS(**{**vars(r), "usage": NS(input_tokens=0, output_tokens=100)})

    c = Spender(decision_synthesis=pricey)
    r = _orch(c, budget).run_cycle(*make_cycle())
    assert r.outcome == "FAILED"
    assert "decision_synthesis" not in c.agents_called()


def test_adapter_refuses_call_when_cap_reached(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 500_000)
    c = RoutingClient()
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    r = adapter.call_agent("market_analyst", system="s", user_content=json.dumps({"agent": "market_analyst"}),
                           output_schema={"type": "object"})
    assert r.error["code"] == "AI_BUDGET_CAP_REACHED" and c.calls == []


def test_unpriced_model_response_fails_closed(budget):
    c = RoutingClient(market_analyst=[NS(stop_reason="end_turn", stop_details=None, model="claude-unknown",
                                         content=[NS(type="text", text="{}")],
                                         usage=NS(input_tokens=1, output_tokens=1))])
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    r = adapter.call_agent("market_analyst", system="s", user_content=json.dumps({"agent": "market_analyst"}),
                           output_schema={"type": "object"})
    assert r.status == "ERROR" and r.error["code"] == "COST_UNMEASURABLE"
