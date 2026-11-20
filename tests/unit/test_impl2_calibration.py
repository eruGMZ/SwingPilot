"""IMPL-2 — infraestructura de calibración sin red ni coste (DEC-016 Q36-Q38;
harness/plans/IMPL-2_plan.md §2-§4): tope de experimentación, escenarios, comprobaciones y
corrida completa de la batería con un modelo simulado."""
import json
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from swingpilot.ai import AGENT_MODELS, AIBudget, AIProviderAdapter  # noqa: E402
from swingpilot.ai.budget import call_cost_usd  # noqa: E402
from swingpilot.audit import EventStore  # noqa: E402
from swingpilot.contracts.agents import BODY_SCHEMAS  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from tests.calibration import scenarios as S  # noqa: E402
from tests.calibration.checks import EXPECTATIONS, critical_checks, evaluate  # noqa: E402
from tests.calibration.experiment_budget import ExperimentBudget, ExperimentBudgetLocked  # noqa: E402
from tests.calibration.run_battery import report_md, run_battery  # noqa: E402

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"


@pytest.fixture
def budgets(tmp_path):
    inner = AIBudget(tmp_path / "ai.db")
    exp = ExperimentBudget(inner, tmp_path / "exp.db", run_label="t", on_warning=lambda *a: None)
    yield inner, exp
    exp.close()
    inner.close()


# ---------------------------------------------------------------- tope de experimentación (Q38)
def test_reservation_blocks_beyond_one_dollar(budgets):
    _, exp = budgets
    one_call = call_cost_usd(SONNET, 10_000, 16_000)  # ≈ $0.18
    rids = []
    while (rid := exp.try_reserve(SONNET, 10_000, 16_000)) is not None:
        rids.append(rid)
    assert len(rids) == int(1.0 // one_call)
    assert sum(call_cost_usd(SONNET, 10_000, 16_000) for _ in rids) <= 1.0
    for r in rids:
        exp.release(r)
    assert exp.try_reserve(SONNET, 10_000, 16_000) is not None  # liberadas, vuelve a caber


def test_settle_records_real_cost_in_both_ledgers(budgets):
    inner, exp = budgets
    rid = exp.try_reserve(HAIKU, 5000, 16000)
    cost = exp.settle(rid, "market_analyst", HAIKU, 4000, 800)
    assert cost == pytest.approx(call_cost_usd(HAIKU, 4000, 800))
    assert exp.spent() == pytest.approx(cost) and inner.spent_this_month() == pytest.approx(cost)


def test_cap_reached_blocks_and_warning_once_at_80_percent(tmp_path):
    inner = AIBudget(tmp_path / "ai.db")
    seen = []
    exp = ExperimentBudget(inner, tmp_path / "exp.db", cap=0.01, on_warning=lambda s, t, c: seen.append((s, t, c)))
    try:
        for _ in range(3):  # 3 × $0.003 = $0.009 ≥ 80% de $0.01
            rid = exp.try_reserve(SONNET, 100, 300)
            exp.settle(rid, "decision_synthesis", SONNET, 0, 300)
        assert len(seen) == 1 and seen[0][1] == pytest.approx(0.008)
        assert exp.try_reserve(SONNET, 100, 300) is None  # 0.009 + 0.0032 > 0.01
        rid = exp.try_reserve(HAIKU, 0, 1000)  # 0.0005 sí cabe
        exp.settle(rid, "market_analyst", HAIKU, 0, 1000)
        assert len(seen) == 1  # el aviso no se repite
    finally:
        exp.close()
        inner.close()


def test_spent_persists_across_processes_and_is_immutable(tmp_path):
    inner = AIBudget(tmp_path / "ai.db")
    exp = ExperimentBudget(inner, tmp_path / "exp.db", on_warning=lambda *a: None)
    exp.settle(exp.try_reserve(HAIKU, 100, 100), "macro_analyst", HAIKU, 100, 100)
    spent = exp.spent()
    exp.close()
    exp2 = ExperimentBudget(inner, tmp_path / "exp.db", on_warning=lambda *a: None)
    try:
        assert exp2.spent() == pytest.approx(spent)
        db = sqlite3.connect(tmp_path / "exp.db")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM experiment_usage")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE experiment_usage SET cost_usd=0")
        db.close()
    finally:
        exp2.close()
        inner.close()


def test_single_process_lock(budgets, tmp_path):
    inner, _ = budgets
    with pytest.raises(ExperimentBudgetLocked):
        ExperimentBudget(inner, tmp_path / "exp.db")


def test_parallel_reservations_are_atomic(tmp_path):
    inner = AIBudget(tmp_path / "ai.db")
    exp = ExperimentBudget(inner, tmp_path / "exp.db", cap=0.05, on_warning=lambda *a: None)
    got, lock = [], threading.Lock()

    def worker():
        for _ in range(20):
            r = exp.try_reserve(HAIKU, 1000, 16000)  # ≈ $0.0081 cada una
            if r is not None:
                with lock:
                    got.append(r)
    ts = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    try:
        assert len(got) * call_cost_usd(HAIKU, 1000, 16000) <= 0.05
        assert len(got) == int(0.05 // call_cost_usd(HAIKU, 1000, 16000))
    finally:
        exp.close()
        inner.close()


def test_monthly_cap_still_applies(tmp_path, monkeypatch):
    inner = AIBudget(tmp_path / "ai.db")
    exp = ExperimentBudget(inner, tmp_path / "exp.db", on_warning=lambda *a: None)
    monkeypatch.setattr(inner, "try_reserve", lambda *a: None)  # mes sin saldo
    try:
        assert exp.try_reserve(HAIKU, 10, 10) is None
        assert exp._inflight == {}
    finally:
        exp.close()
        inner.close()


def test_unmeasurable_cost_is_recorded_conservatively(budgets):
    _, exp = budgets
    rid = exp.try_reserve(HAIKU, 1000, 2000)
    with pytest.raises(ValueError):
        exp.settle(rid, "market_analyst", HAIKU, None, None)
    assert exp.spent() == pytest.approx(call_cost_usd(HAIKU, 1000, 2000))


# ---------------------------------------------------------------- escenarios (resultados esperados previos)
def test_battery_covers_every_impl2_feature_and_ids_are_unique():
    ids = [s["id"] for s in S.SCENARIOS]
    assert len(ids) == len(set(ids)) == 14
    assert {s["feat"] for s in S.SCENARIOS} == {"FEAT-008", "FEAT-009", "FEAT-010", "FEAT-011", "FEAT-012", "FEAT-014"}
    for s in S.SCENARIOS:
        assert s["expect"], s["id"]
        for name, _ in s["expect"]:
            assert name in EXPECTATIONS, (s["id"], name)


def test_fixture_outputs_satisfy_agent_body_contracts():
    for agent, body in (("market_analyst", S.F_MARKET_BULL), ("macro_analyst", S.F_MACRO_RISK),
                        ("macro_analyst", S.F_MACRO_CALM), ("macro_analyst", S.F_MACRO_INSUFF),
                        ("strategy_analyst", S.F_STRATEGY_OK)):
        Draft202012Validator(BODY_SCHEMAS[agent]).validate(body)


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@pytest.mark.parametrize("ctx", [S.market_context(S.UPTREND, "sintético"), S.binance_context()])
def test_candles_are_closed_before_data_ts_and_ordered(ctx):
    step = {"D1": 86400, "H4": 14400, "H1": 3600}
    for tf, cs in ctx["ohlcv"].items():
        opens = [_ts(c["timestamp"]).timestamp() for c in cs]
        assert opens == sorted(opens)
        assert opens[-1] + step[tf] <= _ts(S.DATA_TS).timestamp(), tf  # cierre ≤ DATA_TS
        for c in cs:
            assert c["low"] <= min(c["open"], c["close"]) and c["high"] >= max(c["open"], c["close"])
    assert ctx["indicators"]["D1"]["ema50"] and ctx["indicators"]["H4"]["rsi14"]


def test_synthetic_uptrend_is_actually_bullish():
    d1 = S.UPTREND["D1"]
    assert d1[-1]["close"] > S.indicators(d1)["ema50"] > d1[0]["close"]


def test_binance_candidate_is_coherent_with_snapshot():
    c = S.binance_candidate()
    assert c["stop_loss"] < c["entry_price"]
    assert c["strategy_version"] == S.CANDIDATE["strategy_version"]


def test_news_dates_are_distinct_days_for_matching():
    days = [n[3][:10] for n in (S.N_OFFICIAL, S.N_RUMOR, S.N_SPEC)]
    assert len(set(days)) == 3


# ---------------------------------------------------------------- comprobaciones
def _run(**kw):
    base = {"outputs": {}, "real_agents": [], "events": [], "chain": None, "calls": [], "ledger_delta": 0.0,
            "candidate": S.CANDIDATE}
    return {**base, **kw}


def test_v5_flags_fabricated_consensus_and_v3_altered_strategy():
    sc = next(s for s in S.SCENARIOS if s["id"] == "SYN-01")
    synth = {"status": "COMPLETED", "decision": "TRADE_PROPOSAL", "missing_data": [],
             "trade_proposal": {"strategy_id": "OTRA", "strategy_version": "9.9.9", "conflicting_signals": [],
                                "uncertainty_notes": ""}}
    outs = {"market_analyst": {**S.F_MARKET_BULL}, "macro_analyst": {**S.F_MACRO_RISK},
            "strategy_analyst": {**S.F_STRATEGY_OK}, "decision_synthesis": synth}
    v = {c["code"]: c["ok"] for c in critical_checks(sc, _run(outputs=outs))}
    assert v["V5"] is False and v["V3"] is False and v["V1"] is True


def test_v1_flags_forbidden_event_and_v8_cost_mismatch():
    sc = {"id": "X", "kind": "phase3", "expect": []}
    run = _run(events=[{"message_type": "ORDER_SUBMITTED"}],
               calls=[{"agent": "market_analyst", "usage": [{"model": HAIKU, "input_tokens": 10, "output_tokens": 10}]}],
               ledger_delta=0.5)
    v = {c["code"]: c["ok"] for c in critical_checks(sc, run)}
    assert v["V1"] is False and v["V8"] is False


def test_macro_expectations_detect_misclassification():
    out = {"events": [{"publication_date": S.N_RUMOR[3], "confirmation": "CONFIRMED", "statement_type": "FACT"}]}
    run = _run(outputs={"macro_analyst": out})
    ok, _ = EXPECTATIONS["macro_confirmation"](run, by_date={S.N_RUMOR[3]: "RUMOR"})
    assert not ok
    ok, _ = EXPECTATIONS["macro_not_fact"](run, dates=[S.N_RUMOR[3]])
    assert not ok


def test_unevaluable_expectation_fails_instead_of_passing():
    sc = {"id": "X", "kind": "phase3", "expect": [("equals", {"agent": "market_analyst", "path": "trend_assessment.D1", "value": "BULLISH"})]}
    ev = evaluate(sc, _run(outputs={"market_analyst": {"status": "ERROR"}}, real_agents=["market_analyst"]))
    assert ev["auto_pass"] is False and ev["expectations"][0]["ok"] is False


# ---------------------------------------------------------------- corrida completa con modelo simulado
def _ideal(agent: str, inp: dict) -> dict:
    """Modelo simulado que cumple las expectativas: prueba el cableado, no la calidad."""
    ctx, c = inp["context"], {"sources": ["simulado"], "missing_data": [], "status": "COMPLETED"}
    if agent == "market_analyst":
        if not ctx["ohlcv"].get("D1"):
            return {**c, "status": "INSUFFICIENT_DATA", "missing_data": ["velas D1 y H4"], "observations": [],
                    "key_levels": {"support": [], "resistance": []},
                    "trend_assessment": {"D1": "UNCLEAR", "H4": "UNCLEAR"}, "limitations": ["sin datos"]}
        return S.F_MARKET_BULL
    if agent == "macro_analyst":
        evs = []
        for src in ctx["news_sources"]:
            for it in src["items"]:
                s = src["source"].lower()
                conf, st = (("CONFIRMED", "FACT") if "oficial" in s else ("RUMOR", "INFERENCE") if "anónima" in s
                            else ("SPECULATION", "INFERENCE") if "opinión" in s else (None, None))
                if conf:
                    evs.append({"description": it["title"], "potential_impact": "bajo", "time_horizon": "días",
                                "source": src["source"], "publication_date": it["published"],
                                "confirmation": conf, "uncertainty": "MEDIUM", "statement_type": st})
        return {**c, "events": evs}
    if agent == "strategy_analyst":
        cand = ctx["strategy_candidates"][0]
        bad = cand["stop_loss"] >= cand["entry_price"]
        return {**c, "evaluations": [{"strategy_id": cand["strategy_id"], "strategy_version": cand["strategy_version"],
                "logic_assessment": "x", "activation_conditions_assessment": "x", "signal_invalidation_coherence": "x",
                "weakening_conditions": [], "comparison": None,
                "discard_reasons": ["stop sobre la entrada"] if bad else [], "statement_type": "INFERENCE"}]}
    if agent == "risk_analyst":
        p, st = ctx["proposal"], ctx["system_state"]
        entry = p.get("entry_price_target") or p["entry_zone"]["min"]
        tp = p.get("take_profit_price", p.get("take_profit"))
        return {**c, "hidden_risks": [], "operational_data_risks": [], "challenged_assumptions": [],
                "entry_stop_target_inconsistencies": ["objetivo bajo la entrada"] if tp is not None and tp < entry else [],
                "external_event_exposure": [e["event"] for e in st.get("upcoming_events", [])], "advisory_only": True}
    ins = ctx["inputs"]
    ids = [ins[a]["analysis_id"] for a in ("market_analyst", "macro_analyst", "strategy_analyst")]
    s = {"key_finding": "x", "confidence": "MEDIUM"}
    base = {**c, "input_analysis_ids": ids,
            "agent_summaries": {"market_analyst": s, "macro_analyst": s, "strategy_analyst": s}}
    risky = any(e["uncertainty"] == "HIGH" for e in ins["macro_analyst"].get("events", []))
    if risky or ins["macro_analyst"]["status"] == "INSUFFICIENT_DATA":
        return {**base, "decision": "DISAGREEMENT" if risky else "INSUFFICIENT_INFO", "trade_proposal": None}
    cand = ctx["phase2"]["strategy_candidate"][0]
    return {**base, "decision": "TRADE_PROPOSAL", "trade_proposal": {
        "asset": "BTC/USDT", "direction": "LONG", "entry_zone": {"min": cand["entry_price"], "max": cand["entry_price"]},
        "stop_loss": cand["stop_loss"], "take_profit": None, "strategy_id": cand["strategy_id"],
        "strategy_version": cand["strategy_version"], "rationale": "x", "conflicting_signals": [],
        "uncertainty_notes": "simulado"}}


class FakeClient:
    def __init__(self, fn=_ideal):
        self.fn, self.calls = fn, []
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        inp = json.loads(kw["messages"][0]["content"])
        self.calls.append((inp["agent"], kw))
        body = self.fn(inp["agent"], inp)
        return NS(stop_reason="end_turn", stop_details=None, model=AGENT_MODELS[inp["agent"]],
                  content=[NS(type="text", text=json.dumps(body))], usage=NS(input_tokens=1200, output_tokens=300))


def _battery(tmp_path, client, ids=None, cap=1.0):
    inner = AIBudget(tmp_path / "ai.db")
    exp = ExperimentBudget(inner, tmp_path / "exp.db", cap=cap, on_warning=lambda *a: None)
    store = EventStore(tmp_path / "audit.db")
    adapter = AIProviderAdapter(client, budget=exp, sleep=lambda s: None)
    try:
        return run_battery(S.by_id(ids), adapter, exp, store, label="sim", efforts={}), exp
    finally:
        store.close()


def test_full_battery_with_simulated_ideal_model_passes_all_checks(tmp_path):
    client = FakeClient()
    ev, exp = _battery(tmp_path, client)
    failing = {r["id"]: [x for x in r["contract"] + r["critical"] + r["expectations"] if not x["ok"]]
               for r in ev["results"] if not r["auto_pass"]}
    assert ev["auto_pass"], failing
    # Solo llegan a la API los agentes reales de cada escenario (las fixtures no cuestan)
    called = [a for a, _ in client.calls]
    assert called.count("decision_synthesis") == 3 + 2 and called.count("risk_analyst") == 2 + 2
    assert ev["cost_usd_run"] == pytest.approx(exp.spent())
    cyc = next(r for r in ev["results"] if r["id"] == "CYC-01")
    assert cyc["chain"]["types"] == S.CYCLE_EVENTS and cyc["chain"]["complete"]
    assert len(ev["battery_sha256"]) == 64 and ev["binance_fixture_sha256"]
    assert "MKT-01" in report_md(ev)


def test_battery_reports_failures_of_a_bad_model(tmp_path):
    def bad(agent, inp):
        out = _ideal(agent, inp)
        if agent == "macro_analyst":  # todo CONFIRMED/FACT: error de clasificación
            out = {**out, "events": [{**e, "confirmation": "CONFIRMED", "statement_type": "FACT"} for e in out["events"]]}
        return out
    ev, _ = _battery(tmp_path, FakeClient(bad), ["MAC-01", "MKT-01"])
    res = {r["id"]: r["auto_pass"] for r in ev["results"]}
    assert res == {"MAC-01": False, "MKT-01": True} and ev["auto_pass"] is False


def test_battery_stops_calling_when_experiment_cap_is_reached(tmp_path):
    client = FakeClient()
    ev, exp = _battery(tmp_path, client, ["SYN-01", "SYN-02", "SYN-03"], cap=0.15)
    # La reserva de Sonnet (costo máximo ≈ $0.17) no cabe en $0.15: ninguna llamada llega a la API.
    assert client.calls == [] and exp.spent() == 0
    assert ev["auto_pass"] is False
    assert all(r["outputs"]["decision_synthesis"]["error"]["code"] == "AI_BUDGET_CAP_REACHED" for r in ev["results"])


def test_battery_skips_scenarios_once_spent_reaches_cap(tmp_path, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(ExperimentBudget, "cap_reached", lambda self: True)
    ev, _ = _battery(tmp_path, client, ["MKT-01", "CYC-01"])
    assert client.calls == [] and [r.get("skipped") for r in ev["results"]] == ["tope alcanzado"] * 2
