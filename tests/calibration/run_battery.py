"""Ejecutor de la batería de IMPL-2 (harness/plans/IMPL-2_plan.md §2-§4). Herramienta de desarrollo.

Uso real (coste; requiere RUN_ANTHROPIC_LIVE=1 y .env con permisos 600):
    RUN_ANTHROPIC_LIVE=1 .venv/bin/python -m tests.calibration.run_battery --label base \
        [--scenarios MKT-01 SYN-01 ...] [--effort market_analyst=low ...]

Usa el adaptador, el orquestador y el EventStore reales. Los agentes de la Fase 3 que no son
objeto de un escenario se sustituyen por salidas fijas (marcadas «fixture» en la evidencia):
no llegan a la API ni consumen presupuesto. Cada llamada real reserva contra el tope de IMPL-2
(USD 1.00) y el mensual ($5). Escribe tests/calibration/results/IMPL2_<fecha>_<label>.json y .md.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from jsonschema import Draft202012Validator  # noqa: E402

from swingpilot.ai import AGENT_MODELS, PROMPTS, AgentCallResult, AIOrchestrator, EntryGate  # noqa: E402
from swingpilot.ai.provider import DEFAULT_EFFORT  # noqa: E402
from swingpilot.audit import EventStore  # noqa: E402
from swingpilot.contracts import derive_message, new_message  # noqa: E402

from . import scenarios as S  # noqa: E402
from .checks import evaluate  # noqa: E402

RESULTS = ROOT / "tests" / "calibration" / "results"


class RoutingAdapter:
    """Envía a la API solo los agentes reales; los demás devuelven su salida fija.
    Registra cada AgentCallResult real (usage, intentos) para la comprobación de costo."""

    def __init__(self, real, fixtures: dict):
        self._real, self._fixtures, self.calls = real, fixtures, []

    def call_agent(self, agent, *, system, user_content, output_schema, deadline=None):
        fx = self._fixtures.get(agent)
        if fx is None:
            t0 = time.monotonic()
            r = self._real.call_agent(agent, system=system, user_content=user_content,
                                      output_schema=output_schema, deadline=deadline)
            self.calls.append({"agent": agent, "status": r.status, "attempts": r.attempts,
                               "model_id": r.model_id, "error": r.error, "usage": r.usage,
                               "latency_s": round(time.monotonic() - t0, 2)})
            return r
        body = fx(json.loads(user_content)) if callable(fx) else fx
        Draft202012Validator(output_schema).validate(body)
        return AgentCallResult(agent=agent, status="COMPLETED", model_id=AGENT_MODELS[agent],
                               output=body, attempts=0)


def _synthesis_fixture(inp: dict) -> dict:
    ids = [inp["context"]["inputs"][a]["analysis_id"] for a in ("market_analyst", "macro_analyst", "strategy_analyst")]
    s = {"key_finding": "fixture", "confidence": "LOW"}
    return {"sources": ["fixture"], "missing_data": [], "status": "COMPLETED", "decision": "INSUFFICIENT_INFO",
            "trade_proposal": None, "input_analysis_ids": ids,
            "agent_summaries": {"market_analyst": s, "macro_analyst": s, "strategy_analyst": s}}


def _phase_msgs(sc: dict, market: dict):
    req = new_message(source="trading_engine", destination="ai_orchestrator", message_type="ANALYSIS_REQUESTED",
                      data_timestamp_utc=S.DATA_TS, timeframe="H4",
                      payload={"market_context": market, "macro_context": sc.get("macro", S.news(S.N_CPI))})
    k = dict(destination="ai_orchestrator", data_timestamp_utc=S.DATA_TS, timeframe="H4")
    regime = derive_message(req, source="regime_engine", message_type="REGIME_CLASSIFIED", payload=S.REGIME, **k)
    ml = derive_message(req, source="ml_engine", message_type="ML_INFERENCE_COMPLETED", payload=S.ML, **k)
    cand = derive_message(regime, source="strategy_engine", message_type="STRATEGY_CANDIDATE",
                          payload=sc["candidate"], **k)
    return req, [regime, ml, cand]


def _approve(cause: dict) -> dict:
    return derive_message(cause, source="risk_manager", destination="telegram_bot", message_type="RISK_APPROVED",
                          data_timestamp_utc=S.DATA_TS, timeframe="H4",
                          payload={"note": "RISK_APPROVED sintético (no lo emite la IA; IMPL-2)"})


def _proposal_from(cand: dict, note: str) -> dict:
    entry, stop = cand["entry_price"], cand["stop_loss"]
    return {"asset": "BTC/USDT", "direction": "LONG", "entry_price_target": entry, "stop_loss_price": stop,
            "take_profit_price": round(entry + 3 * (entry - stop), 2), "strategy_id": cand["strategy_id"],
            "strategy_version": cand["strategy_version"], "note": note}


def run_scenario(sc: dict, real_adapter, budget, store: EventStore) -> dict:
    sc = S.resolve(sc)
    kind, fixtures, real_agents = sc["kind"], {}, []
    if kind == "phase3":
        real_agents = [sc["agent"]]
        fixtures = {a: b for a, b in (("market_analyst", S.F_MARKET_BULL), ("macro_analyst", S.F_MACRO_CALM),
                                      ("strategy_analyst", S.F_STRATEGY_OK)) if a != sc["agent"]}
        fixtures["decision_synthesis"] = _synthesis_fixture
    elif kind == "synthesis":
        real_agents, fixtures = ["decision_synthesis"], dict(sc["fixtures"])
    elif kind == "risk":
        real_agents = ["risk_analyst"]
    elif kind == "cycle":
        real_agents = ["market_analyst", "macro_analyst", "strategy_analyst", "decision_synthesis", "risk_analyst"]
    adapter = RoutingAdapter(real_adapter, fixtures)
    state = sc.get("state", S.STATE_CALM)
    orch = AIOrchestrator(adapter, store, precheck=EntryGate(
        lambda: {"open_position": False, "locks": ["ACTIVE"], "safe_mode": False}, budget))
    spent0 = budget.spent()
    events, outputs, cid, chain_root = [], {}, None, []

    if kind == "risk":
        root = new_message(source="trading_engine", destination="ai_orchestrator", message_type="ANALYSIS_REQUESTED",
                           data_timestamp_utc=S.DATA_TS, timeframe="H4", payload={"note": "raíz sintética (RSK)"})
        appr = _approve(root)
        for m in (root, appr):
            store.append(m)
        rr = orch.run_risk_analysis(appr, sc["proposal"], state)
        events, outputs, cid = rr.events, rr.outputs, root["correlation_id"]
        outcome = rr.outcome
    else:
        req, p2 = _phase_msgs(sc, sc.get("market") or S.market_context(S.UPTREND, "sintético"))
        for m in (req, *p2):
            store.append(m)
        r = orch.run_cycle(req, p2)
        events, outputs, cid, outcome = list(r.events), dict(r.outputs), req["correlation_id"], r.outcome
        if kind == "cycle" and r.outcome == "COMPLETED":
            sy = r.outputs["decision_synthesis"]
            proposal = sy["trade_proposal"] if sy["decision"] == "TRADE_PROPOSAL" else _proposal_from(
                sc["candidate"], f"sintética: la síntesis decidió {sy['decision']}")
            appr = _approve(r.events[-1])
            store.append(appr)
            rr = orch.run_risk_analysis(appr, proposal, state)
            events += rr.events
            outputs.update(rr.outputs)
            outcome = rr.outcome
    ch = store.get_chain(cid)
    run = {"outputs": outputs, "real_agents": real_agents, "events": events,
           "chain": {"complete": ch.complete, "orphans": ch.orphans, "types": [m["message_type"] for m in ch.messages]},
           "calls": adapter.calls, "ledger_delta": round(budget.spent() - spent0, 12),
           "candidate": sc.get("candidate")}
    ev = evaluate(sc, run)
    return {"id": sc["id"], "feat": sc["feat"], "kind": kind, "outcome": outcome, "correlation_id": cid,
            "real_agents": real_agents, "fixture_agents": sorted(fixtures), "calls": adapter.calls,
            "cost_usd": run["ledger_delta"], "chain": run["chain"],
            "outputs": {a: outputs[a] for a in outputs}, **ev}


def run_battery(scs: list[dict], real_adapter, budget, store: EventStore, *, label: str, efforts: dict) -> dict:
    results = []
    for sc in scs:
        if budget.cap_reached():
            results.append({"id": sc["id"], "feat": sc["feat"], "skipped": "tope alcanzado", "auto_pass": False})
            continue
        results.append(run_scenario(sc, real_adapter, budget, store))
    return {
        "label": label, "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "RESEARCH", "battery_sha256": S.battery_sha256(),
        "binance_fixture_sha256": _fixture_sha(),
        "prompt_versions": {a: p.version for a, p in PROMPTS.items()},
        "efforts": {a: efforts.get(a, DEFAULT_EFFORT) for a in AGENT_MODELS},
        "models": dict(AGENT_MODELS),
        "scenarios_run": [s["id"] for s in scs],
        "auto_pass": all(r.get("auto_pass") for r in results),
        "cost_usd_run": round(sum(r.get("cost_usd", 0) for r in results), 6),
        "experiment_spent_usd": round(budget.spent(), 6),
        "experiment_cap_usd": budget.cap, "experiment_warnings": budget.warnings,
        "results": results,
    }


def _fixture_sha() -> str | None:
    import hashlib
    p = S.FIXTURES / "binance_btcusdt_klines.json"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def report_md(ev: dict) -> str:
    L = [f"# IMPL-2 — corrida «{ev['label']}»", "",
         f"- Fecha: {ev['executed_at_utc']} · modo {ev['mode']} · batería sha256 `{ev['battery_sha256'][:16]}…`",
         f"- Prompts: {ev['prompt_versions']}", f"- effort: {ev['efforts']}",
         f"- Costo de la corrida: ${ev['cost_usd_run']:.6f} · gasto acumulado IMPL-2: ${ev['experiment_spent_usd']:.6f} de ${ev['experiment_cap_usd']:.2f}",
         f"- **Comprobaciones automáticas: {'PASAN' if ev['auto_pass'] else 'FALLAN'}** (la evaluación cualitativa es del propietario)", "",
         "| Escenario | FEAT | Contrato | Críticas | Expectativas | Costo |", "|---|---|---|---|---|---|"]
    for r in ev["results"]:
        if r.get("skipped"):
            L.append(f"| {r['id']} | {r['feat']} | — | — | omitido: {r['skipped']} | — |")
            continue
        c = "ok" if all(x["ok"] for x in r["contract"]) else "FALLA"
        k = "ok" if all(x["ok"] for x in r["critical"]) else "FALLA " + ",".join(x["code"] for x in r["critical"] if not x["ok"])
        e = f"{sum(x['ok'] for x in r['expectations'])}/{len(r['expectations'])}"
        L.append(f"| {r['id']} | {r['feat']} | {c} | {k} | {e} | ${r['cost_usd']:.6f} |")
    for r in ev["results"]:
        if r.get("skipped"):
            continue
        L += ["", f"## {r['id']} ({r['feat']}) — resultado {r['outcome']}", "",
              f"Agentes reales: {r['real_agents']} · fixture: {r['fixture_agents']}", ""]
        for x in r["contract"] + r["critical"]:
            if not x["ok"]:
                L.append(f"- ✗ {x.get('code', 'contrato ' + str(x.get('agent')))}: {x['detail']}")
        for x in r["expectations"]:
            L.append(f"- {'✓' if x['ok'] else '✗'} {x['check']}: {x['detail']}")
        for a in r["real_agents"]:
            if a in r["outputs"]:
                body = {k: v for k, v in r["outputs"][a].items()
                        if k not in ("analysis_id", "correlation_id", "causation_id", "schema_version")}
                L += ["", f"<details><summary>{a}</summary>", "", "```json",
                      json.dumps(body, ensure_ascii=False, indent=2), "```", "</details>"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--scenarios", nargs="*")
    ap.add_argument("--effort", nargs="*", default=[], help="agente=valor")
    a = ap.parse_args(argv)
    if os.environ.get("RUN_ANTHROPIC_LIVE") != "1":
        print("Corrida con costo real: requiere RUN_ANTHROPIC_LIVE=1", file=sys.stderr)
        return 2
    efforts = dict(e.split("=", 1) for e in a.effort)
    unknown = set(efforts) - set(AGENT_MODELS)
    if unknown:
        raise SystemExit(f"agentes desconocidos en --effort: {unknown}")
    from swingpilot.ai import AIBudget, AIProviderAdapter
    from swingpilot.security import CredentialVault, startup_violations

    from .experiment_budget import ExperimentBudget
    env = ROOT / ".env"
    if v := startup_violations(env, "RESEARCH"):
        raise SystemExit(f"arranque bloqueado: {v}")
    vault = CredentialVault.from_env_file(env)
    (ROOT / "var").mkdir(exist_ok=True)
    inner = AIBudget(ROOT / "var" / "ai_budget.db")
    budget = ExperimentBudget(inner, ROOT / "var" / "impl2_experiment_budget.db", run_label=a.label)
    try:
        adapter = AIProviderAdapter.from_vault(vault, budget=budget, efforts=efforts)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
        rundir = ROOT / "var" / "impl2_runs" / f"{stamp}_{a.label}"
        rundir.mkdir(parents=True, exist_ok=True)
        store = EventStore(rundir / "audit.db", secret_check=vault.contains_secret)
        try:
            ev = run_battery(S.by_id(a.scenarios), adapter, budget, store, label=a.label, efforts=efforts)
        finally:
            store.close()
        ev["audit_db"] = str((rundir / "audit.db").relative_to(ROOT))
        out = json.dumps(ev, ensure_ascii=False, indent=2)
        md = report_md(ev)
        if vault.contains_secret(out) or vault.contains_secret(md):
            raise SystemExit("la evidencia contiene un secreto: no se escribe")
        RESULTS.mkdir(parents=True, exist_ok=True)
        base = RESULTS / f"IMPL2_{stamp}_{a.label}"
        base.with_suffix(".json").write_text(out + "\n", encoding="utf-8")
        base.with_suffix(".md").write_text(md, encoding="utf-8")
        print(f"{base}.json · auto_pass={ev['auto_pass']} · costo ${ev['cost_usd_run']:.6f} · "
              f"acumulado IMPL-2 ${ev['experiment_spent_usd']:.6f}")
        return 0 if ev["auto_pass"] else 1
    finally:
        budget.close()
        inner.close()


if __name__ == "__main__":
    raise SystemExit(main())
