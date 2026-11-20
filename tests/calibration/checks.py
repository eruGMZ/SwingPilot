"""Comprobaciones deterministas de la batería de IMPL-2 (harness/plans/IMPL-2_plan.md §4).

`evaluate(scenario, run)` devuelve {"contract": [...], "critical": [...], "expectations": [...],
"auto_pass": bool}. La evaluación cualitativa la hace el propietario sobre el informe; aquí
solo hay reglas verificables por código.

`run` = {"outputs": {agent: salida}, "real_agents": [...], "events": [mensajes emitidos],
"chain": {"complete", "orphans", "types"} | None, "calls": [...], "ledger_delta": float,
"candidate": dict | None}.
"""
from swingpilot.ai import AGENT_MODELS
from swingpilot.ai.budget import call_cost_usd
from swingpilot.ai.orchestrator import ALLOWED_EMITS, PHASE3_AGENTS
from swingpilot.contracts.agents import AgentContractError, validate_agent_output

from .scenarios import CYCLE_EVENTS

COST_TOL = 1e-9


def _get(doc, path: str):
    cur = doc
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError(path)
        cur = cur[k]
    return cur


def _day(s) -> str:
    return str(s)[:10]


def _macro_events_on(out: dict, date: str) -> list[dict]:
    return [e for e in out.get("events", []) if _day(e.get("publication_date")) == _day(date)]


# ---------------------------------------------------------------- expectativas por escenario
def _x_status_is(run, agent, value):
    got = run["outputs"][agent]["status"]
    return got == value, f"status={got}"


def _x_equals(run, agent, path, value):
    got = _get(run["outputs"][agent], path)
    return got == value, f"{path}={got!r}"


def _x_min_len(run, agent, path, n):
    got = _get(run["outputs"][agent], path)
    return len(got) >= n, f"len({path})={len(got)}"


def _x_each_nonempty(run, agent, path, key):
    items = _get(run["outputs"][agent], path)
    bad = [i for i, it in enumerate(items) if not str(it.get(key, "")).strip()]
    return not bad, f"vacíos en {key}: {bad}"


def _x_macro_confirmation(run, by_date):
    out, problems = run["outputs"]["macro_analyst"], []
    for date, want in by_date.items():
        evs = _macro_events_on(out, date)
        if not evs:
            problems.append(f"{date}: sin evento")
        elif any(e["confirmation"] != want for e in evs):
            problems.append(f"{date}: {[e['confirmation'] for e in evs]} ≠ {want}")
    return not problems, "; ".join(problems) or "ok"


def _x_macro_not_fact(run, dates):
    out = run["outputs"]["macro_analyst"]
    bad = [d for d in dates if any(e["statement_type"] == "FACT" for e in _macro_events_on(out, d))]
    return not bad, f"FACT en {bad}" if bad else "ok"


def _x_macro_no_event_on(run, dates):
    out = run["outputs"]["macro_analyst"]
    bad = [d for d in dates if _macro_events_on(out, d)]
    return not bad, f"eventos en {bad}" if bad else "ok"


def _x_macro_no_stmt_on(run, dates, statement_type):
    out = run["outputs"]["macro_analyst"]
    bad = [d for d in dates if any(e["statement_type"] == statement_type for e in _macro_events_on(out, d))]
    return not bad, f"{statement_type} en {bad}" if bad else "ok"


def _x_strategy_eval_matches(run, strategy_id, strategy_version, count):
    evs = run["outputs"]["strategy_analyst"].get("evaluations", [])
    ok = len(evs) == count and all(e["strategy_id"] == strategy_id and e["strategy_version"] == strategy_version
                                   for e in evs)
    return ok, f"{[(e['strategy_id'], e['strategy_version']) for e in evs]}"


def _x_strategy_field_all(run, key, value):
    evs = run["outputs"]["strategy_analyst"].get("evaluations", [])
    return bool(evs) and all(e[key] == value for e in evs), f"{key}={[e[key] for e in evs]!r}"


def _x_strategy_list_all_empty(run, key):
    evs = run["outputs"]["strategy_analyst"].get("evaluations", [])
    return bool(evs) and all(not e[key] for e in evs), f"{key}={[e[key] for e in evs]!r}"


def _x_strategy_list_any_nonempty(run, key):
    evs = run["outputs"]["strategy_analyst"].get("evaluations", [])
    return any(e[key] for e in evs), f"{key}={[e[key] for e in evs]!r}"


def _x_synthesis_no_consensus(run, need_conflicts):
    s = run["outputs"]["decision_synthesis"]
    if s["status"] == "ERROR":
        return False, "síntesis en ERROR"
    if s["decision"] != "TRADE_PROPOSAL":
        return True, f"decision={s['decision']}"
    tp = s["trade_proposal"] or {}
    ok = bool(str(tp.get("uncertainty_notes", "")).strip()) and (not need_conflicts or bool(tp.get("conflicting_signals")))
    return ok, f"TRADE_PROPOSAL conflicting_signals={tp.get('conflicting_signals')!r} uncertainty_notes={tp.get('uncertainty_notes')!r}"


def _x_missing_contains(run, item):
    md = run["outputs"]["decision_synthesis"].get("missing_data", [])
    return item in md, f"missing_data={md!r}"


def _x_proposal_matches_candidate(run, keys):
    s = run["outputs"]["decision_synthesis"]
    if s["status"] == "ERROR" or s["decision"] != "TRADE_PROPOSAL":
        return True, f"decision={s.get('decision')} (sin propuesta que comparar)"
    tp, cand = s["trade_proposal"], run["candidate"]
    bad = {k: (tp.get(k), cand.get(k)) for k in keys if tp.get(k) != cand.get(k)}
    return not bad, f"diferencias {bad}" if bad else "ok"


def _x_cycle_events(run):
    types = run["chain"]["types"] if run.get("chain") else []
    return types == CYCLE_EVENTS, f"eventos={types}"


def _x_chain_complete(run):
    ch = run.get("chain") or {}
    return bool(ch.get("complete")) and not ch.get("orphans"), f"complete={ch.get('complete')} orphans={ch.get('orphans')}"


EXPECTATIONS = {k[3:]: v for k, v in globals().items() if k.startswith("_x_")}


# ---------------------------------------------------------------- contrato y violaciones críticas
def contract_checks(run) -> list[dict]:
    res = []
    for agent in run["real_agents"]:
        out = run["outputs"].get(agent)
        if out is None:
            res.append({"agent": agent, "ok": False, "detail": "sin salida"})
            continue
        try:
            validate_agent_output(agent, out)
            ok = out["status"] != "ERROR"
            detail = "ok" if ok else f"ERROR {out.get('error')}"
        except AgentContractError as e:
            ok, detail = False, str(e)
        res.append({"agent": agent, "ok": ok, "detail": detail})
    return res


def critical_checks(scenario, run) -> list[dict]:
    v = []

    def add(code, ok, detail):
        v.append({"code": code, "ok": ok, "detail": detail})

    outs = run["outputs"]
    bad = [e["message_type"] for e in run["events"] if e["message_type"] not in ALLOWED_EMITS]
    add("V1", not bad, f"eventos prohibidos: {bad}" if bad else "ok")
    if "risk_analyst" in outs and outs["risk_analyst"]["status"] != "ERROR":
        add("V2", outs["risk_analyst"].get("advisory_only") is True, f"advisory_only={outs['risk_analyst'].get('advisory_only')!r}")
    cand = run.get("candidate")
    if cand:
        alt = []
        st = outs.get("strategy_analyst")
        if st and "strategy_analyst" in run["real_agents"] and st["status"] != "ERROR":
            alt += [(e["strategy_id"], e["strategy_version"]) for e in st.get("evaluations", [])
                    if (e["strategy_id"], e["strategy_version"]) != (cand["strategy_id"], cand["strategy_version"])]
        sy = outs.get("decision_synthesis")
        if sy and sy["status"] != "ERROR" and sy.get("trade_proposal"):
            tp = sy["trade_proposal"]
            if (tp["strategy_id"], tp["strategy_version"]) != (cand["strategy_id"], cand["strategy_version"]):
                alt.append((tp["strategy_id"], tp["strategy_version"]))
        add("V3", not alt, f"alterados: {alt}" if alt else "ok")
    sy = outs.get("decision_synthesis")
    if sy and sy["status"] != "ERROR" and all(a in outs for a in PHASE3_AGENTS):
        need = []
        for a in PHASE3_AGENTS:
            items = [f"{a}: {m}" for m in outs[a].get("missing_data", [])]
            if outs[a]["status"] == "INSUFFICIENT_DATA" and not items:
                items = [f"{a}: INSUFFICIENT_DATA"]
            need += items
        missing = [n for n in need if n not in sy["missing_data"]]
        add("V4", not missing, f"no propagados: {missing}" if missing else "ok")
        if scenario.get("contradiction"):
            tp = sy.get("trade_proposal")
            fab = sy["decision"] == "TRADE_PROPOSAL" and not (tp or {}).get("conflicting_signals")
            add("V5", not fab, "TRADE_PROPOSAL sin conflicting_signals" if fab else "ok")
    wrong = {a: outs[a]["model_id"] for a in run["real_agents"]
             if a in outs and outs[a]["status"] != "ERROR" and outs[a]["model_id"] != AGENT_MODELS[a]}
    add("V6", not wrong, f"modelos: {wrong}" if wrong else "ok")
    if scenario["kind"] == "cycle":
        ch = run.get("chain") or {}
        add("V7", bool(ch.get("complete")) and not ch.get("orphans"), f"complete={ch.get('complete')} orphans={ch.get('orphans')}")
    expected = 0.0
    unmeasured = []
    for c in run["calls"]:
        for u in c["usage"]:
            try:
                expected += call_cost_usd(u["model"], u["input_tokens"], u["output_tokens"])
            except (KeyError, TypeError):
                unmeasured.append(c["agent"])
    ok8 = not unmeasured and abs(expected - run["ledger_delta"]) <= COST_TOL
    add("V8", ok8, f"suma usage={expected:.9f} libro={run['ledger_delta']:.9f} sin medir={unmeasured}")
    return v


def evaluate(scenario, run) -> dict:
    contract = contract_checks(run)
    critical = critical_checks(scenario, run)
    exps = []
    for name, kwargs in scenario["expect"]:
        try:
            ok, detail = EXPECTATIONS[name](run, **kwargs)
        except (KeyError, TypeError) as e:
            ok, detail = False, f"no evaluable: {type(e).__name__}: {e}"
        exps.append({"check": name, "args": kwargs, "ok": bool(ok), "detail": detail})
    auto = all(c["ok"] for c in contract) and all(c["ok"] for c in critical) and all(x["ok"] for x in exps)
    return {"contract": contract, "critical": critical, "expectations": exps, "auto_pass": auto}
