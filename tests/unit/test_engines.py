"""FEAT-018..022 — motores de la Fase 2, normalización y ciclo hasta E9 (api_contracts.md §3.8, contrato v1.6).

TC-MSG-004/005, TC-FLOW-001, 004..007, 009..011, TC-AI-007, TC-NORM-001..003, TC-AC-01/03/04/07.
Sin red ni costo: velas sintéticas y el cliente LLM simulado de test_orchestrator. Las
estrategias y el clasificador de régimen de este archivo son dobles de prueba: no son
estrategias ni parámetros aprobados (DEC-018).
"""
import copy
import sys
import uuid
from pathlib import Path

import pytest
from historical_approval import legacy_promotion_check, seed_historical_approval  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from test_orchestrator import RoutingClient, orch, synthesis  # noqa: E402

from swingpilot.audit import EventStore  # noqa: E402
from swingpilot.contracts import new_message  # noqa: E402
from swingpilot.engines import (DecisionCycle, EnginePayloadError, EntryEvaluation, EntryProposal,  # noqa: E402
                                ExitProposal, MarketInput, MLEngine, OpenPosition, RegimeEngine, RegimeState,
                                StopProposal, StrategyEngine, normalize, validate_engine_payload,
                                validate_trade_proposal)
from swingpilot.engines.normalizer import INCONSISTENT  # noqa: E402
from swingpilot.market_data.candles import Candle, interval_ms  # noqa: E402
from swingpilot.ml import ModelRegistry  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402

DAY, H = 86_400_000, 3_600_000
T0 = 1_700_000_000_000 // DAY * DAY
SERVER = T0 + 300 * DAY + 5 * H + 7


def series(interval, n, server=SERVER, drop_last=False, price=lambda k: 100.0 + k % 9):
    iv = interval_ms(interval)
    last = (server // iv) * iv - iv
    first = last - (n - 1) * iv
    out = []
    for k in range(n):
        t = first + k * iv
        p = price(k)
        out.append(Candle(interval, t, t + iv - 1, p, p + 2, p - 2, p + 1, 5.0))
    return out[:-1] if drop_last else out


def market(drop=None, n=250):
    return MarketInput({"D1": series("1d", n, drop_last=drop == "D1"), "H4": series("4h", n, drop_last=drop == "H4"),
                        "H1": series("1h", n, drop_last=drop == "H1")}, source="snapshot", server_time_ms=SERVER,
                       snapshot_id="SNAP-TEST")


def e1(mk=None):
    m = mk or market()
    return new_message(source="trading_engine", destination="ai_orchestrator", message_type="ANALYSIS_REQUESTED",
                       data_timestamp_utc=m.data_timestamp("H4"), timeframe="H4", status="COMPLETED",
                       payload={"market_context": {}, "macro_context": {}})


@pytest.fixture
def regs(tmp_path):
    dec = tmp_path / "dec"
    dec.mkdir()
    (dec / "DEC-900_x.md").write_text("AUTORIZA: EXP-0301 OOS_EVALUATION\nAUTORIZA: EXP-0301 APPROVED\n")
    exps = ExperimentRegistry(tmp_path / "r.jsonl", dec)
    mr = ModelRegistry(tmp_path / "m.db", exps)
    yield exps, mr
    mr.close()


# ---------------------------------------------------------------- dobles de prueba
class FakeStrategy:
    def __init__(self, sid="S1", version="1.0.0", family="TREND_FOLLOWING", status="APPROVED", exp="EXP-9",
                 regimes=None, entry=True, exit_=None, trail=None, boom=False, bad=False, stop=90.0):
        self.strategy_id, self.version, self.family, self.status = sid, version, family, status
        self.experiment_ref = exp if status == "APPROVED" else None
        self.signal_timeframe, self.required_regimes = "H4", regimes
        self._entry, self._exit, self._trail, self._boom, self._bad, self._stop = entry, exit_, trail, boom, bad, stop

    def evaluate_entry(self, mk, regime, ml):
        if self._boom:
            raise RuntimeError("fallo interno")
        if not self._entry:
            return EntryEvaluation(None, ["cond_x no se cumple"])
        cond = [{"condition_id": "c1", "description": "prueba", "timeframe": "H4", "observed_value": 1.0,
                 "threshold": 0.5, "operator": ">", "satisfied": True}]
        return EntryEvaluation(EntryProposal(
            conditions=[] if self._bad else cond, entry_zone={"min": 100.0, "max": 102.0}, entry_reference_price=101.0,
            stop_loss={"price": self._stop, "method": "TEST", "parameters": {}},
            exit_mechanism={"type": "STOP_LOSS", "trigger_condition": "precio ≤ stop", "execution_method": "stop en Binance",
                            "failure_procedure": "cierre protector"},
            invalidation_conditions=["cierre bajo la zona"]))

    def evaluate_exit(self, mk, pos):
        return self._exit

    def trailing_stop(self, mk, pos):
        return self._trail


class FakeSpec:
    classifier_id, version, timeframe = "test-vol", "0.0.1", "D1"
    labels = ("LOW", "HIGH")
    min_bars, persistence_bars = 20, 2

    def __init__(self, seq=None):
        self.seq = list(seq or [])

    def measure(self, bars):
        return {"range_mean": sum(b.high - b.low for b in bars[-10:]) / 10}

    def classify(self, m, current):
        return self.seq.pop(0) if self.seq else "LOW"

    def margins(self, m):
        return {"range_mean": 0.0}


def phase2(regs, mk=None, strategies=(), mode="PAPER", block=None, position=None, spec=None, ml=None):
    mk = mk or market()
    req = e1(mk)
    r, _ = RegimeEngine(spec).run(req, mk)
    m = (ml or MLEngine(regs[1])).run(req, mk)
    return req, r, m, StrategyEngine(list(strategies)).run(r, m, mk, mode=mode, block=block, position=position)


# ---------------------------------------------------------------- FEAT-018 Regime Engine
def test_regime_without_spec_is_unclassified(regs):
    req = e1()
    msg, st = RegimeEngine().run(req, market())
    p = msg["payload"]
    assert p["regime_label"] == "UNCLASSIFIED" and p["spec_version"] is None and p["measurements"] == {}
    assert msg["causation_id"] == req["message_id"] and msg["status"] == "COMPLETED"


def test_regime_missing_last_d1_is_error(regs):
    msg, _ = RegimeEngine().run(e1(), market(drop="D1"))
    assert msg["payload"]["result_status"] == "ERROR" and msg["payload"]["error"]["code"] == "DATA_UNAVAILABLE"
    assert msg["status"] == "FAILED" and msg["payload"]["regime_label"] == "UNCLASSIFIED"


def test_regime_spec_insufficient_persistence_and_determinism():
    mk = market()
    short = MarketInput({**mk.candles, "D1": mk.bars("D1")[-10:]}, "snapshot", SERVER, "SNAP-TEST")
    m, _ = RegimeEngine(FakeSpec()).run(e1(), short)
    assert m["payload"]["result_status"] == "INSUFFICIENT_DATA" and m["payload"]["missing_data"]
    eng = RegimeEngine(FakeSpec(["LOW", "LOW", "HIGH", "HIGH"]))
    labels, st = [], RegimeState()
    for _ in range(4):
        msg, st = eng.run(e1(), mk, st)
        labels.append((msg["payload"]["regime_label"], msg["payload"]["candidate_label"]))
    assert labels == [("TRANSITION", "LOW"), ("LOW", None), ("TRANSITION", "HIGH"), ("HIGH", None)]
    a, _ = RegimeEngine(FakeSpec(["LOW"])).run(e1(), mk)
    b, _ = RegimeEngine(FakeSpec(["LOW"])).run(e1(), mk)
    assert a["payload"] == b["payload"]   # TC-AC-07


# ---------------------------------------------------------------- FEAT-019 ML Engine (AC-019-4)
def test_ml_no_active_model(regs):
    msg = MLEngine(regs[1]).run(e1(), market())
    p = msg["payload"]
    assert p["inference_status"] == "NO_ACTIVE_MODEL" and p["prediction"] is None and p["advisory_only"] is True
    assert p["model_id"] is None


def legacy_freeze_check():
    """Solo pruebas heredadas (CR-020/CR-021): congelación sin las comprobaciones de ET-1, construida
    deliberadamente con la credencial privada (B3-01: el registro ya no acepta un invocable arbitrario)."""
    from swingpilot.research.experiments import _FREEZE_CHECK_KEY, FreezeCheck
    return FreezeCheck(_FREEZE_CHECK_KEY, lambda records, experiment_id, evidence: None)


def _approve(exps, eid="EXP-0301"):
    exps.create(eid, "x", actor="orquestador")
    for to, ev in [("DESIGN", {}), ("PREREGISTERED", None),
                   ("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})]:
        exps.transition(eid, to, actor="orquestador", evidence=_cr020_freeze_ev(exps, eid) if ev is None else ev,
                        **({"freeze_check": legacy_freeze_check()} if to == "PREREGISTERED" else {}))  # CR-023 ET-1
    exps.transition(eid, "OOS_EVALUATION", actor="propietario", evidence=_cr020_oos_ev(exps, eid, "DEC-900_x.md"))
    exps.transition(eid, "AUDIT", actor="orquestador")
    exps.transition(eid, "HUMAN_REVIEW", actor="orquestador")
    seed_historical_approval(exps, eid, "DEC-900_x.md")   # B8.2: histórico sembrado


class FakePredictor:
    model_id, model_version, feature_set_version, timeframe = "M1", "1.0.0", "1.0.0", "H4"

    def predict(self, mk):
        return {"target": "ret_6", "horizon_bars": 6, "timeframe": "H4", "value": 0.01, "value_type": "regression"}, "f" * 64


def test_ml_active_suspended_and_missing_predictor(regs):
    exps, mr = regs
    _approve(exps)
    mr.register("M1", "1.0.0", data_hash="d" * 64, code_hash="c" * 64, params={}, experiment_id="EXP-0301")
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))
    assert MLEngine(mr).run(e1(), market())["payload"]["error"]["code"] == "SPEC_NOT_FOUND"
    p = MLEngine(mr, FakePredictor()).run(e1(), market())["payload"]
    assert p["inference_status"] == "INFERENCE_AVAILABLE" and p["approval_ref"] == "EXP-0301" and p["prediction"]["value"] == 0.01
    mr.check_degradation("M1", "1.0.0", last_trades_net_r=[-1.0] * 20, ic_lower_bound_oos=0.1, psi_by_feature={})
    p = MLEngine(mr, FakePredictor()).run(e1(), market())["payload"]
    assert p["inference_status"] == "MODEL_SUSPENDED" and p["prediction"] is None and p["drift"]["suspended_reason"]


# ---------------------------------------------------------------- TC-MSG-004 / TC-MSG-005
def test_tc_msg_004_payloads_validate_and_missing_fields_are_rejected(regs):
    req, r, m, out = phase2(regs, strategies=[FakeStrategy()])
    cand = out[-1]
    for msg in (r, m, cand):
        validate_engine_payload(msg["message_type"], msg["payload"])
        for k in ("engine", "result_status", "data_refs"):
            bad = copy.deepcopy(msg["payload"])
            del bad[k]
            with pytest.raises(EnginePayloadError):
                validate_engine_payload(msg["message_type"], bad)
    bad = copy.deepcopy(cand["payload"])
    bad["confidence"] = 0.9   # CR-011: no existe
    with pytest.raises(EnginePayloadError):
        validate_engine_payload("STRATEGY_CANDIDATE", bad)
    err = {**{k: cand["payload"][k] for k in ("engine", "engine_version", "spec_version", "data_refs",
                                                 "missing_data", "regime_message_id", "ml_inference_message_id")},
           "result_status": "ERROR", "error": {"code": "INTERNAL_ERROR", "message": "x", "stage": "INTERNAL",
                                               "upstream_message_id": None, "strategy_id": None, "strategy_version": None}}
    validate_engine_payload("STRATEGY_CANDIDATE", err)
    with pytest.raises(EnginePayloadError):   # B.7.1: con ERROR los campos de candidato están prohibidos
        validate_engine_payload("STRATEGY_CANDIDATE", {**err, "entry_reference_price": 101.0})


@pytest.mark.parametrize("case", ["condicion_no_satisfecha", "tp_igual_al_max", "tp_dentro_de_zona", "tp_bajo_zona"])
def test_qa3e_10_b4_candidate_rules_are_enforced(regs, case):
    """QA3E-10: B.4 exige condiciones satisfechas y take_profit por encima de la zona de entrada."""
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]["payload"]   # zona [100, 102]
    validate_engine_payload("STRATEGY_CANDIDATE", {**cand, "take_profit": 110.0})   # control válido
    bad = copy.deepcopy(cand)
    if case == "condicion_no_satisfecha":
        bad["conditions"][0]["satisfied"] = False
    else:
        bad["take_profit"] = {"tp_igual_al_max": 102.0, "tp_dentro_de_zona": 101.0, "tp_bajo_zona": 95.0}[case]
    with pytest.raises(EnginePayloadError):
        validate_engine_payload("STRATEGY_CANDIDATE", bad)


def test_tc_msg_005_market_time_differs_from_processing_time(regs):
    mk = market()
    _, r, m, out = phase2(regs, mk=mk, strategies=[FakeStrategy()])
    for msg in (r, m, out[-1]):
        assert msg["data_timestamp_utc"] != msg["timestamp_utc"]
        ref = next(iter(msg["payload"]["data_refs"].values()))
        assert ref["bars_used"] == 250 and ref["snapshot_id"] == "SNAP-TEST"
    assert out[-1]["data_timestamp_utc"] == mk.data_timestamp("H4")


# ---------------------------------------------------------------- FEAT-020 Strategy Engine
def reason(out):
    return out[-1]["message_type"], out[-1]["payload"].get("reason_code"), out[-1]["payload"].get("reason_detail")


def test_tc_flow_009_no_approved_strategy_in_paper_and_research_allows_research(regs):
    assert reason(phase2(regs)[3])[:2] == ("NO_SETUP", "NO_APPROVED_STRATEGY")
    research = FakeStrategy(status="RESEARCH")
    assert reason(phase2(regs, strategies=[research], mode="LIVE")[3])[1] == "NO_APPROVED_STRATEGY"
    out = phase2(regs, strategies=[research], mode="RESEARCH")[3]
    assert out[-1]["message_type"] == "STRATEGY_CANDIDATE" and out[-1]["payload"]["operating_mode"] == "RESEARCH"


def test_tc_flow_001_no_candidate_zero_llm(regs):
    out = phase2(regs, strategies=[FakeStrategy(entry=False)])[3]
    assert reason(out)[:2] == ("NO_SETUP", "NO_CANDIDATE") and out[-1]["payload"]["llm_calls"] == 0
    assert out[-1]["payload"]["evaluated_strategies"][0]["failed_conditions"] == ["cond_x no se cumple"]


def test_tc_flow_004_005_multiple_candidates_and_single(regs):
    out = phase2(regs, strategies=[FakeStrategy("S1"), FakeStrategy("S2")])[3]
    assert reason(out)[:2] == ("NO_SETUP", "MULTIPLE_ENTRY_CANDIDATES")
    disc = out[-1]["payload"]["discarded_candidates"]
    assert {d["discard_reason"] for d in disc} == {"CONFLICT_MULTIPLE_ENTRIES"} and len(disc) == 2
    req, r, m, out = phase2(regs, strategies=[FakeStrategy("S1")])
    c = out[-1]
    assert c["message_type"] == "STRATEGY_CANDIDATE" and c["causation_id"] == r["message_id"]
    assert c["payload"]["ml_inference_message_id"] == m["message_id"] and "confidence" not in c["payload"]


def test_tc_flow_006_exit_has_priority_and_stop_request(regs):
    pos = OpenPosition(str(uuid.uuid4()), "S1", "1.0.0", 95.0)
    ex = ExitProposal("EXIT_CONDITION", [], 99.0)
    out = phase2(regs, strategies=[FakeStrategy(exit_=ex), FakeStrategy("S2")], position=pos)[3]
    assert [o["message_type"] for o in out] == ["STRATEGY_EXIT_SIGNAL", "NO_SETUP"]
    assert out[-1]["payload"]["reason_code"] == "EXIT_SIGNAL_PRIORITY"
    assert out[-1]["payload"]["exit_signal_ref"] == out[0]["message_id"] and out[0]["destination"] == "execution_engine"
    up = phase2(regs, strategies=[FakeStrategy(trail=StopProposal(96.5, "TEST", {}))], position=pos)[3]
    assert [o["message_type"] for o in up] == ["STOP_ADJUSTMENT_REQUESTED", "NO_SETUP"]
    assert up[0]["payload"]["requested_stop"] == 96.5 and up[0]["destination"] == "risk_manager"
    assert reason(up)[1:] == ("PRE_PHASE3_BLOCK", "OPEN_POSITION")
    with pytest.raises(EnginePayloadError, match="INVALID_STOP_REQUEST"):
        validate_engine_payload("STOP_ADJUSTMENT_REQUESTED", {**up[0]["payload"], "requested_stop": 95.0})


@pytest.mark.parametrize("requested", [94.0, 95.0])   # bajar o mantener el stop actual (95)
def test_qa3e_02_invalid_stop_request_is_recorded_as_error(regs, requested):
    """B.6: `requested_stop ≤ current_stop` no se emite y queda registrada como ERROR INVALID_STOP_REQUEST."""
    pos = OpenPosition(str(uuid.uuid4()), "S1", "1.0.0", 95.0)
    out = phase2(regs, strategies=[FakeStrategy(trail=StopProposal(requested, "TEST", {}))], position=pos)[3]
    assert [o["message_type"] for o in out] == ["STRATEGY_CANDIDATE"]          # sin STOP_ADJUSTMENT_REQUESTED
    msg = out[0]
    assert msg["status"] == "FAILED" and msg["payload"]["result_status"] == "ERROR"
    err = msg["payload"]["error"]
    assert err["code"] == "INVALID_STOP_REQUEST" and err["stage"] == "STRATEGY_EVALUATION"
    assert err["strategy_id"] == "S1" and "entry_reference_price" not in msg["payload"]


def _with(tf, bars):
    mk = market()
    return MarketInput({**mk.candles, tf: bars}, "snapshot", SERVER, "SNAP-TEST")


def _dup(bars, i=-5):
    return bars[:i] + [bars[i]] + bars[i:]


def _gap(bars, n=10):
    return bars[:-(n + 1)] + bars[-1:]


def _swap(bars):
    return bars[:-3] + [bars[-2], bars[-3]] + bars[-1:]


@pytest.mark.parametrize("case,mk", [
    ("D1_duplicada", lambda: _with("D1", _dup(series("1d", 250)))),
    ("D1_hueco_10_dias", lambda: _with("D1", _gap(series("1d", 250)))),
    ("D1_fuera_de_orden", lambda: _with("D1", _swap(series("1d", 250))))])
def test_qa3e_03_regime_inconsistent_candles_are_data_inconsistent(case, mk):
    msg, _ = RegimeEngine().run(e1(), mk())
    p = msg["payload"]
    assert msg["status"] == "FAILED" and p["result_status"] == "ERROR", (case, p)
    assert p["error"]["code"] == "DATA_INCONSISTENT" and p["regime_label"] == "UNCLASSIFIED"


@pytest.mark.parametrize("case,mk", [
    ("H4_duplicada", lambda: _with("H4", _dup(series("4h", 250)))),
    ("H4_hueco", lambda: _with("H4", _gap(series("4h", 250), 3))),
    ("H4_fuera_de_orden", lambda: _with("H4", _swap(series("4h", 250))))])
def test_qa3e_03_strategy_and_ml_inconsistent_candles(regs, case, mk):
    out = phase2(regs, mk=mk(), strategies=[FakeStrategy()])[3]
    p = out[-1]["payload"]
    assert out[-1]["message_type"] == "STRATEGY_CANDIDATE" and p["result_status"] == "ERROR", (case, p)
    assert p["error"]["code"] == "DATA_INCONSISTENT" and p["error"]["stage"] == "INPUT_VALIDATION"
    exps, mr = regs
    _approve(exps)
    mr.register("M1", "1.0.0", data_hash="d" * 64, code_hash="c" * 64, params={}, experiment_id="EXP-0301")
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))
    pm = MLEngine(mr, FakePredictor()).run(e1(), mk())["payload"]
    assert pm["result_status"] == "ERROR" and pm["error"]["code"] == "DATA_INCONSISTENT", (case, pm)
    assert pm["prediction"] is None


def test_qa3e_03_consistent_series_still_completes(regs):
    # Control: la serie sintética contigua no se marca como inconsistente.
    assert all(market().inconsistency(tf) is None for tf in ("D1", "H4", "H1"))
    msg, _ = RegimeEngine().run(e1(), market())
    assert msg["payload"]["result_status"] == "COMPLETED"


def test_qa3e_05_strategy_timeframe_must_match_engine():
    s = FakeStrategy()
    s.signal_timeframe = "D1"
    with pytest.raises(ValueError, match="signal_timeframe"):
        StrategyEngine([s])                                  # motor H4
    assert StrategyEngine([s], signal_timeframe="D1").signal_timeframe == "D1"


def test_qa3e_06_e2_e3_from_different_cycles_is_recorded_error(regs):
    mk = market()
    r, _ = RegimeEngine().run(e1(mk), mk)
    m = MLEngine(regs[1]).run(e1(mk), mk)                    # otro ANALYSIS_REQUESTED → otro ciclo
    assert r["correlation_id"] != m["correlation_id"]
    out = StrategyEngine([FakeStrategy()]).run(r, m, mk, mode="PAPER")
    assert [o["message_type"] for o in out] == ["STRATEGY_CANDIDATE"]
    msg = out[0]
    assert msg["status"] == "FAILED" and msg["correlation_id"] == r["correlation_id"]
    err = msg["payload"]["error"]
    assert err["code"] == "INTERNAL_ERROR" and err["stage"] == "INPUT_VALIDATION"
    assert err["upstream_message_id"] == m["message_id"]


def test_tc_ai_007_pre_phase3_block(regs):
    for b in ("LOSS_STREAK_LOCK", "SAFE_MODE", "AI_BUDGET_CAP", "DATA_UNAVAILABLE"):
        assert reason(phase2(regs, strategies=[FakeStrategy()], block=b)[3])[1:] == ("PRE_PHASE3_BLOCK", b)
    with pytest.raises(ValueError):
        phase2(regs, block="CUALQUIERA")


def test_tc_flow_010_ml_based_not_eligible_without_inference(regs):
    out = phase2(regs, strategies=[FakeStrategy(family="ML_BASED")])[3]
    assert reason(out)[1] == "NO_CANDIDATE"
    assert out[-1]["payload"]["evaluated_strategies"][0]["result"] == "NOT_ELIGIBLE"


def test_required_regime_not_met_is_not_eligible(regs):
    out = phase2(regs, strategies=[FakeStrategy(regimes=("LOW",))])[3]   # régimen UNCLASSIFIED
    assert out[-1]["payload"]["evaluated_strategies"][0]["result"] == "NOT_ELIGIBLE"


def test_tc_flow_007_binary_rule_no_confidence(regs):
    exps, mr = regs
    p = MLEngine(mr)
    a = phase2(regs, strategies=[FakeStrategy("S1"), FakeStrategy("S2")], ml=p)[3][-1]["payload"]["reason_code"]
    assert a == "MULTIPLE_ENTRY_CANDIDATES"   # sin desempate por confianza ni por ML


def test_upstream_insufficient(regs):
    mk = market()
    short = MarketInput({**mk.candles, "D1": mk.bars("D1")[-10:]}, "snapshot", SERVER, "SNAP-TEST")
    out = phase2(regs, mk=short, strategies=[FakeStrategy()], spec=FakeSpec())[3]
    assert reason(out)[1] == "UPSTREAM_INSUFFICIENT_DATA" and out[-1]["payload"]["result_status"] == "INSUFFICIENT_DATA"


@pytest.mark.parametrize("case,code,stage", [
    ("upstream", "UPSTREAM_ERROR", "REGIME_INPUT"), ("boom", "INTERNAL_ERROR", "STRATEGY_EVALUATION"),
    ("bad", "INVALID_CANDIDATE", "CANDIDATE_VALIDATION"), ("stop", "INVALID_CANDIDATE", "CANDIDATE_VALIDATION"),
    ("nodata", "DATA_UNAVAILABLE", "INPUT_VALIDATION")])
def test_tc_flow_011_technical_errors_are_error_not_no_setup(regs, case, code, stage):
    kw = {"upstream": dict(mk=market(drop="D1")), "boom": dict(strategies=[FakeStrategy(boom=True)]),
          "bad": dict(strategies=[FakeStrategy(bad=True)]), "stop": dict(strategies=[FakeStrategy(stop=101.5)]),
          "nodata": dict(mk=MarketInput({**market().candles, "H4": series("4h", 250, drop_last=True)}, "snapshot",
                                        SERVER, "SNAP-TEST"), strategies=[FakeStrategy()])}[case]
    out = phase2(regs, **kw)[3]
    msg = out[-1]
    assert msg["message_type"] == "STRATEGY_CANDIDATE" and msg["status"] == "FAILED"
    assert msg["payload"]["result_status"] == "ERROR" and msg["payload"]["error"]["code"] == code
    assert msg["payload"]["error"]["stage"] == stage and "entry_reference_price" not in msg["payload"]


def test_engine_rejects_invalid_definitions():
    with pytest.raises(ValueError, match="experiment_ref"):
        StrategyEngine([FakeStrategy(exp=None)])
    with pytest.raises(ValueError, match="duplicada"):
        StrategyEngine([FakeStrategy(), FakeStrategy()])


# ---------------------------------------------------------------- FEAT-021 Normalización
def _synth_msg(cand, proposal_overrides=None, decision="TRADE_PROPOSAL"):
    c = cand["payload"]
    tp = {"asset": "BTC/USDT", "direction": "LONG", "entry_zone": {"min": 100.5, "max": 101.5},
          "stop_loss": c["stop_loss"]["price"], "take_profit": None, "strategy_id": c["strategy_id"],
          "strategy_version": c["strategy_version"], "rationale": "r", "conflicting_signals": [], "uncertainty_notes": "u"}
    tp.update(proposal_overrides or {})
    from swingpilot.contracts import derive_message
    body = {**synthesis([str(uuid.uuid4())] * 3, decision, tp), "analysis_id": str(uuid.uuid4())}
    return derive_message(cand, source="decision_synthesis", destination="ai_orchestrator",
                          message_type="DECISION_SYNTHESIS_COMPLETED", data_timestamp_utc=cand["data_timestamp_utc"],
                          timeframe="H4", payload=body, status="COMPLETED")


def test_tc_norm_001_proposal_takes_operative_fields_from_candidate(regs):
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    s = _synth_msg(cand)
    res = normalize(cand, s)
    p = res.proposal_message["payload"]
    assert res.status == "EMITTED" and res.proposal_message["causation_id"] == s["message_id"]
    assert p["entry_price_target"] == 101.0 and p["stop_loss_price"] == 90.0
    assert p["exit_mechanism"] == cand["payload"]["exit_mechanism"] and p["entry_zone"] == cand["payload"]["entry_zone"]
    assert p["source_candidate_message_id"] == cand["message_id"] and p["schema_version"] == "1.1.0"


_OPERATIVE_4_1 = {"proposal_id", "entry_price_target", "stop_loss_price", "exit_mechanism", "asset", "direction",
                  "take_profit_price"}


def _assert_rejection(res, cand, synth, reason):
    """B.10 (CR-019): E9 de rechazo, causado por E8, hacia Audit, sin campos operativos de §4.1."""
    from swingpilot.contracts import validate_message
    from swingpilot.engines.normalizer import validate_rejection_payload
    rej = res.rejection_message
    assert res.proposal_message is None and rej is not None and res.e9 is rej
    validate_message(rej)
    validate_rejection_payload(rej["payload"])
    assert rej["message_type"] == "PROPOSAL_NORMALIZATION_REJECTED" and rej["status"] == "COMPLETED"
    assert rej["causation_id"] == synth["message_id"] and rej["correlation_id"] == synth["correlation_id"]
    assert rej["source"] == "ai_orchestrator" and rej["destination"] == "audit"
    p = rej["payload"]
    assert p["reason_code"] == reason and not _OPERATIVE_4_1 & set(p)
    assert p["source_candidate_message_id"] == cand["message_id"] and p["synthesis_message_id"] == synth["message_id"]
    assert p["source_candidate_id"] == cand["payload"]["candidate_id"]
    return p


@pytest.mark.parametrize("over,field", [({"stop_loss": 89.0}, "stop_loss"), ({"strategy_id": "OTRA"}, "strategy_id"),
                                        ({"entry_zone": {"min": 99.0, "max": 101.0}}, "entry_zone"),
                                        ({"take_profit": 120.0}, "take_profit")])
def test_tc_norm_002_inconsistent_synthesis_yields_no_proposal(regs, over, field):
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    synth = _synth_msg(cand, over)
    res = normalize(cand, synth)
    assert res.status == INCONSISTENT and res.problems
    p = _assert_rejection(res, cand, synth, INCONSISTENT)
    assert [a["field"] for a in p["affected_fields"]] == [field] and p["validation_errors"] == []
    a = p["affected_fields"][0]
    assert a["synthesis_value"] == next(iter(over.values())) and a["candidate_value"] != a["synthesis_value"]


def test_tc_norm_004_proposal_out_of_contract_is_recorded(regs):
    cand = copy.deepcopy(phase2(regs, strategies=[FakeStrategy()])[3][-1])
    cand["payload"]["exit_mechanism"]["type"] = "MANUAL"        # fuera del enum de §4.1
    synth = _synth_msg(cand)
    res = normalize(cand, synth)
    assert res.status == "OUT_OF_CONTRACT"
    p = _assert_rejection(res, cand, synth, "OUT_OF_CONTRACT")
    assert p["affected_fields"] == [] and p["validation_errors"]


def test_tc_norm_005_no_rejection_without_a_proposal(regs):
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    other = normalize(cand, _synth_msg(cand, decision="DISAGREEMENT"))
    synth_err = _synth_msg(cand)
    synth_err["payload"]["status"] = "ERROR"
    cand_err = {**copy.deepcopy(cand), "status": "FAILED"}
    for res in (other, normalize(cand, synth_err), normalize(cand_err, _synth_msg(cand))):
        assert res.status == "NOT_A_PROPOSAL"
        assert res.proposal_message is None and res.rejection_message is None and res.e9 is None


def test_cr019_rejection_schema_forbids_operative_fields_and_enforces_conditionals(regs):
    from swingpilot.engines.normalizer import ProposalContractError, validate_rejection_payload
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    p = normalize(cand, _synth_msg(cand, {"stop_loss": 89.0})).rejection_message["payload"]
    for bad in ({**p, "stop_loss_price": 89.0}, {**p, "affected_fields": []},
                {**p, "validation_errors": ["x"]}, {**p, "reason_code": "OUT_OF_CONTRACT"},
                {**p, "affected_fields": [{"field": "precio", "synthesis_value": 1, "candidate_value": 2}]}):
        with pytest.raises(ProposalContractError):
            validate_rejection_payload(bad)


def test_normalize_non_proposal_decisions(regs):
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    assert normalize(cand, _synth_msg(cand, decision="DISAGREEMENT")).status == "NOT_A_PROPOSAL"


def test_tc_norm_003_versions(regs):
    cand = phase2(regs, strategies=[FakeStrategy()])[3][-1]
    p = normalize(cand, _synth_msg(cand)).proposal_message["payload"]
    validate_trade_proposal(p)
    v10 = {k: p[k] for k in ("proposal_id", "correlation_id", "timestamp_utc", "asset", "direction",
                             "entry_price_target", "stop_loss_price", "strategy_id", "strategy_version", "exit_mechanism")}
    validate_trade_proposal({**v10, "schema_version": "1.0.0"})
    from swingpilot.engines.normalizer import ProposalContractError
    with pytest.raises(ProposalContractError):
        validate_trade_proposal({**v10, "schema_version": "1.1.0"})


# ---------------------------------------------------------------- FEAT-022 ciclo hasta E9
def synth_from_candidate(inp):
    ids = [v["analysis_id"] for v in inp["context"]["inputs"].values()]
    c = inp["context"]["phase2"]["strategy_candidate"][0]
    tp = {"asset": "BTC/USDT", "direction": "LONG", "entry_zone": c["entry_zone"], "stop_loss": c["stop_loss"]["price"],
          "take_profit": None, "strategy_id": c["strategy_id"], "strategy_version": c["strategy_version"],
          "rationale": "r", "conflicting_signals": [], "uncertainty_notes": "u"}
    return synthesis(ids, "TRADE_PROPOSAL", tp)


def build_cycle(tmp_path, regs, strategies, synth=synth_from_candidate):
    store = EventStore(tmp_path / "audit.db")
    client = RoutingClient(decision_synthesis=synth)
    cyc = DecisionCycle(RegimeEngine(), MLEngine(regs[1]), StrategyEngine(strategies), orch(client, store), store,
                        bars_per_timeframe=30)
    return cyc, client, store


def test_feat_022_full_cycle_e1_to_e9_reconstructible(tmp_path, regs):
    cyc, client, store = build_cycle(tmp_path, regs, [FakeStrategy(status="RESEARCH")])
    rep = cyc.run(market(), mode="RESEARCH")
    assert rep.outcome == "PROPOSAL_EMITTED" and rep.llm_calls == 4
    assert rep.types() == ["ANALYSIS_REQUESTED", "REGIME_CLASSIFIED", "ML_INFERENCE_COMPLETED", "STRATEGY_CANDIDATE",
                           "MARKET_ANALYSIS_COMPLETED", "MACRO_ANALYSIS_COMPLETED", "STRATEGY_ANALYSIS_COMPLETED",
                           "DECISION_SYNTHESIS_COMPLETED", "TRADE_PROPOSAL"]
    chain = store.get_chain(rep.correlation_id)                    # TC-AC-03/04 (alcance IMPL-3)
    assert chain.complete and len(chain.messages) == 9
    assert not any(t.startswith(("RISK_", "ORDER_")) for t in rep.types())   # termina en E9
    p = rep.events[-1]["payload"]
    cand = rep.events[3]
    # Relación con estrategia, inferencia y evidencia reproducible (architecture.md §7 fila 3)
    assert (p["strategy_id"], p["strategy_version"]) == (cand["payload"]["strategy_id"], cand["payload"]["strategy_version"])
    assert cand["payload"]["ml_inference_message_id"] == rep.events[2]["message_id"]
    assert cand["payload"]["data_refs"]["H4"]["snapshot_id"] == "SNAP-TEST"
    mc = client.calls[0][2]["context"] if client.calls[0][0] == "market_analyst" else \
        next(c[2]["context"] for c in client.calls if c[0] == "market_analyst")
    assert len(mc["ohlcv"]["H4"]) == 30


def test_feat_022_no_setup_cycle_makes_zero_llm_calls(tmp_path, regs):
    cyc, client, store = build_cycle(tmp_path, regs, [])
    rep = cyc.run(market(), mode="PAPER")
    assert rep.outcome == "NO_SETUP" and client.calls == [] and rep.llm_calls == 0
    assert store.get_chain(rep.correlation_id).complete


def test_feat_022_strategy_error_stops_before_llm(tmp_path, regs):
    cyc, client, _ = build_cycle(tmp_path, regs, [FakeStrategy(boom=True)])
    rep = cyc.run(market(), mode="PAPER")
    assert rep.outcome == "STRATEGY_ENGINE_ERROR" and client.calls == []


@pytest.mark.parametrize("payload_from,envelope", [
    ("boom", "FAILED"),          # caso original: sobre FAILED y payload ERROR
    ("ok", "FAILED"),            # QA3E-04: sobre FAILED con payload COMPLETED
    ("boom", "COMPLETED")])      # QA3E-04: sobre COMPLETED con payload ERROR
def test_orchestrator_rejects_error_candidate_in_phase3(tmp_path, regs, payload_from, envelope):
    client = RoutingClient()
    req = e1()
    _, r, m, out = phase2(regs, strategies=[FakeStrategy(boom=payload_from == "boom")])
    # se re-derivan con el correlation_id de la petición
    from swingpilot.contracts import derive_message
    r2 = derive_message(req, source="regime_engine", destination="ai_orchestrator", message_type="REGIME_CLASSIFIED",
                        data_timestamp_utc=r["data_timestamp_utc"], timeframe="D1", payload=r["payload"], status="COMPLETED")
    m2 = derive_message(req, source="ml_engine", destination="ai_orchestrator", message_type="ML_INFERENCE_COMPLETED",
                        data_timestamp_utc=m["data_timestamp_utc"], timeframe="H4", payload=m["payload"], status="COMPLETED")
    c2 = derive_message(r2, source="strategy_engine", destination="ai_orchestrator", message_type="STRATEGY_CANDIDATE",
                        data_timestamp_utc=out[-1]["data_timestamp_utc"], timeframe="H4", payload=out[-1]["payload"],
                        status=envelope)
    res = orch(client).run_cycle(req, [r2, m2, c2])
    assert res.outcome == "NOT_RUN" and res.reason == "STRATEGY_ENGINE_ERROR" and client.calls == []


def test_feat_022_inconsistent_synthesis_no_proposal(tmp_path, regs):
    def bad(inp):
        b = synth_from_candidate(inp)
        b["trade_proposal"]["stop_loss"] = 1.0
        return b
    cyc, _, store = build_cycle(tmp_path, regs, [FakeStrategy(status="RESEARCH")], synth=bad)
    rep = cyc.run(market(), mode="RESEARCH")
    assert rep.outcome == "PROPOSAL_REJECTED" and rep.normalization.status == INCONSISTENT
    assert "TRADE_PROPOSAL" not in rep.types()
    assert rep.types()[-2:] == ["DECISION_SYNTHESIS_COMPLETED", "PROPOSAL_NORMALIZATION_REJECTED"]
    # QA3E-01 / CONF-008: la inconsistencia queda en el EventStore y la cadena se reconstruye hasta E9.
    chain = store.get_chain(rep.correlation_id)
    assert chain.complete and len(chain.messages) == 9
    stored = [m for m in chain.messages if m["message_type"] == "PROPOSAL_NORMALIZATION_REJECTED"]
    e8 = next(m for m in chain.messages if m["message_type"] == "DECISION_SYNTHESIS_COMPLETED")
    assert len(stored) == 1 and stored[0]["causation_id"] == e8["message_id"]
    assert stored[0]["payload"]["affected_fields"][0]["field"] == "stop_loss"


def test_tc_ac_07_deterministic_part_is_reproducible(tmp_path, regs):
    def strip(m):
        p = dict(m["payload"])
        for k in ("candidate_id", "regime_message_id", "ml_inference_message_id"):
            p.pop(k, None)
        return m["message_type"], p
    a = [strip(x) for x in phase2(regs, strategies=[FakeStrategy()])[1:3]] + [strip(phase2(regs, strategies=[FakeStrategy()])[3][-1])]
    b = [strip(x) for x in phase2(regs, strategies=[FakeStrategy()])[1:3]] + [strip(phase2(regs, strategies=[FakeStrategy()])[3][-1])]
    assert a == b


def test_cycle_requires_same_store(tmp_path, regs):
    store = EventStore(tmp_path / "a.db")
    with pytest.raises(ValueError, match="mismo EventStore"):
        DecisionCycle(RegimeEngine(), MLEngine(regs[1]), StrategyEngine([]), orch(RoutingClient()), store,
                      bars_per_timeframe=10)


def _cr020_freeze_ev(exps, eid, sha="a" * 64):
    """CR-020: la congelación exige el «trials_accounting» recalculado desde el registro."""
    # CR-023 (B3): la congelación declara su clase de independencia (ET-1).
    return {"preregistration_sha256": sha, "min_history_ok": True, "independence_class": "CONFIRMATORY",
            "trials_accounting": exps.trials_accounting(eid, ["A"])}


def _cr020_oos_ev(exps, eid, ref):
    """CR-020: inicio duradero de la evaluación de «A» y registro de la selección de candidata."""
    import hashlib
    exps.begin_configuration_evaluation(eid, "A", actor="orquestador")
    inputs = ('{"experiment_id":"%s","results":{"A":{"sharpe":1.0}}}' % eid).encode()
    return {"decision_ref": ref, "selected_config_id": "A",
            "selection_inputs_sha256": hashlib.sha256(inputs).hexdigest(), "informed_by": []}
