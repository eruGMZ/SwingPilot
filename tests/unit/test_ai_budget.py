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


# ---------------- QA ronda 1, hallazgo 3: tope duro y atómico ----------------
import threading  # noqa: E402


def test_reservation_refuses_call_that_could_exceed_cap(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 490_000)  # $4.90
    # Sonnet con max_tokens 16000 puede costar hasta $0.16 → no cabe
    assert budget.try_reserve("claude-sonnet-5-5", 1000, 16000) is None
    # Haiku hasta ~$0.008 → cabe
    assert budget.try_reserve("claude-haiku-5-5", 1000, 16000) is not None


def test_inflight_reservations_count_against_cap(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 480_000)  # $4.80
    r1 = budget.try_reserve("claude-sonnet-5-5", 0, 16000)  # $0.16 → 4.96
    assert r1 is not None
    assert budget.try_reserve("claude-sonnet-5-5", 0, 16000) is None  # 5.12 > 5
    budget.release(r1)
    assert budget.try_reserve("claude-sonnet-5-5", 0, 16000) is not None


def test_parallel_calls_never_exceed_cap(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 498_000)  # $4.98: caben 2 reservas Haiku de ~$0.0081
    barrier = threading.Barrier(3, timeout=5)

    class WorstCase(RoutingClient):
        def _create(self, **kw):
            r = super()._create(**kw)
            return NS(**{**vars(r), "usage": NS(input_tokens=1000, output_tokens=16000)})

    c = WorstCase()
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    results = {}

    def run(agent):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        results[agent] = adapter.call_agent(agent, system="s", user_content=json.dumps({"agent": agent}),
                                            output_schema={"type": "object"})

    ts = [threading.Thread(target=run, args=(a,)) for a in ("market_analyst", "macro_analyst", "strategy_analyst")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    refused = [a for a, r in results.items() if r.error and r.error["code"] == "AI_BUDGET_CAP_REACHED"]
    assert len(c.calls) == 3 - len(refused) and refused
    assert budget.spent_this_month() <= 5.0


def test_sequential_calls_stop_before_exceeding_cap(budget):
    budget.record("x", "claude-sonnet-5-5", 0, 450_000)  # $4.50

    class WorstCase(RoutingClient):
        def _create(self, **kw):
            r = super()._create(**kw)
            return NS(**{**vars(r), "usage": NS(input_tokens=5000, output_tokens=16000)})

    adapter = AIProviderAdapter(WorstCase(decision_synthesis=lambda inp: {}), sleep=lambda s: None, budget=budget)
    for _ in range(10):
        r = adapter.call_agent("decision_synthesis", system="s",
                               user_content=json.dumps({"agent": "decision_synthesis"}),
                               output_schema={"type": "object"})
        if r.error and r.error["code"] == "AI_BUDGET_CAP_REACHED":
            break
    else:
        raise AssertionError("se esperaba rechazo por tope")
    assert budget.spent_this_month() <= 5.0


def test_reservation_released_after_failed_call(budget):
    import anthropic
    import httpx2 as httpx
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.InternalServerError("x", response=httpx.Response(529, request=req), body=None)
    c = RoutingClient(market_analyst=[err, err])
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    adapter.call_agent("market_analyst", system="s", user_content=json.dumps({"agent": "market_analyst"}),
                       output_schema={"type": "object"})
    assert budget._inflight == {} and len(c.calls) == 2


def test_reservation_released_on_unexpected_exception(budget):
    c = RoutingClient(market_analyst=[RuntimeError("boom")])
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    with pytest.raises(RuntimeError):
        adapter.call_agent("market_analyst", system="s", user_content=json.dumps({"agent": "market_analyst"}),
                           output_schema={"type": "object"})
    assert budget._inflight == {}


# ---------------- QA ronda 2 ----------------
# Menor 1: COST_UNMEASURABLE registra el costo máximo reservado como estimado
def test_unmeasurable_cost_records_conservative_estimate(budget):
    c = RoutingClient(market_analyst=[NS(stop_reason="end_turn", stop_details=None, model="claude-unknown",
                                         content=[NS(type="text", text="{}")],
                                         usage=NS(input_tokens=1, output_tokens=1))])
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    r = adapter.call_agent("market_analyst", system="s", user_content=json.dumps({"agent": "market_analyst"}),
                           output_schema={"type": "object"})
    assert r.error["code"] == "COST_UNMEASURABLE"
    row = budget._db.execute("SELECT model, output_tokens, cost_usd, estimated FROM ai_usage").fetchone()
    assert row[0] == "claude-haiku-5-5" and row[1] == 16000 and row[3] == 1
    assert row[2] >= call_cost_usd("claude-haiku-5-5", 0, 16000)
    assert budget.spent_this_month() == pytest.approx(row[2]) and budget._inflight == {}


def test_incomplete_usage_records_conservative_estimate(budget):
    c = RoutingClient(decision_synthesis=[NS(stop_reason="end_turn", stop_details=None, model="claude-sonnet-5-5",
                                             content=[NS(type="text", text="{}")],
                                             usage=NS(input_tokens=None, output_tokens=5))])
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    r = adapter.call_agent("decision_synthesis", system="s",
                           user_content=json.dumps({"agent": "decision_synthesis"}), output_schema={"type": "object"})
    assert r.error["code"] == "COST_UNMEASURABLE"
    assert budget._db.execute("SELECT estimated FROM ai_usage").fetchone()[0] == 1
    assert budget.spent_this_month() >= call_cost_usd("claude-sonnet-5-5", 0, 16000)


def test_measured_calls_are_not_marked_estimated(budget):
    budget.record("x", "claude-haiku-5-5", 10, 10)
    assert budget._db.execute("SELECT estimated FROM ai_usage").fetchone()[0] == 0


def test_old_database_is_migrated(tmp_path, clock):
    path = tmp_path / "old.db"
    raw = sqlite3.connect(path)
    raw.executescript("""CREATE TABLE ai_usage (seq INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT NOT NULL,
        recorded_at_utc TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL, cost_usd REAL NOT NULL);
        INSERT INTO ai_usage(month,recorded_at_utc,agent,model,input_tokens,output_tokens,cost_usd)
        VALUES ('2026-11','x','a','claude-haiku-5-5',1,1,0.5);""")
    raw.commit(); raw.close()
    b = AIBudget(path, now=clock)
    assert b.spent_this_month() == pytest.approx(0.5)
    b.record("x", "claude-haiku-5-5", 10, 10)
    assert [r[0] for r in b._db.execute("SELECT estimated FROM ai_usage ORDER BY seq")] == [0, 0]


# Menor 2: cota de tokens de entrada por byte UTF-8
from swingpilot.ai.provider import _max_input_tokens  # noqa: E402


@pytest.mark.parametrize("text,min_bytes", [("a" * 1000, 1000), ("ñ" * 1000, 2000),
                                            ("漢" * 1000, 3000), ("🙂" * 1000, 4000)])
def test_input_bound_counts_utf8_bytes(text, min_bytes):
    assert _max_input_tokens("", text, {}) >= min_bytes + 2000


def test_input_bound_includes_system_and_schema():
    schema = {"type": "object", "properties": {"campo_largo_" * 20: {"type": "string"}}}
    base = _max_input_tokens("", "", {})
    assert _max_input_tokens("x" * 500, "", schema) >= base + 500 + len("campo_largo_" * 20)


def test_reservation_grows_with_non_ascii_content(budget):
    c = RoutingClient()
    adapter = AIProviderAdapter(c, sleep=lambda s: None, budget=budget)
    seen = []
    orig = budget.try_reserve
    budget.try_reserve = lambda m, i, o: seen.append(i) or orig(m, i, o)
    for text in ("a" * 3000, "漢" * 3000):
        adapter.call_agent("market_analyst", system="s",
                           user_content=json.dumps({"agent": "market_analyst", "t": text}, ensure_ascii=False),
                           output_schema={"type": "object"})
    assert seen[1] - seen[0] >= 6000  # 3 bytes por carácter CJK frente a 1
