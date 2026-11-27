"""B9.4 (CR-023/024/025 v1.13): ET-10 cableado en el Strategy Engine (paso 6), genuino y sintético.
La elegibilidad real (V9, bloqueo con plazo, tampering) la resuelve `resolve_et10` sin parches."""
import fcntl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from test_engines import FakeStrategy, market, e1, regs  # noqa: E402,F401
from test_cr025_b9_3_et10_resolver import approved, gdev, ggrant, grant, make_genuine, _GENUINE, GSID  # noqa: E402,F401
from test_cr023_b7_e2e_window import frozen_statistics  # noqa: E402,F401  (autouse: estadísticos sintéticos)
from tape import favorable_tape  # noqa: E402,F401
from test_cr023_b6_context_reading import EID  # noqa: E402
EVIDENCE_REF = "SwingPilot@abc1234:docs/decisions/DEC-999_prueba.md"
from swingpilot.engines.regime import RegimeEngine  # noqa: E402
from swingpilot.engines.ml import MLEngine  # noqa: E402
from swingpilot.engines.strategy import StrategyEngine  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import operational_eligibility as O  # noqa: E402


def _sub(tmp_path):
    """`regs` ya usa tmp_path: el experimento genuino vive en un subdirectorio propio."""
    d = tmp_path / "et10"
    d.mkdir()
    return d


def run(regs, strategies, provider, mode="PAPER", **kw):
    mk = market()
    req = e1(mk)
    r, _ = RegimeEngine(None).run(req, mk)
    m = MLEngine(regs[1]).run(req, mk)
    return StrategyEngine(list(strategies), evidence_provider=provider).run(r, m, mk, mode=mode, **kw)


def strat(sid="S1", exp=EID, **kw):
    s = FakeStrategy(sid=sid, **kw)
    s.experiment_ref = exp
    return s


def test_eligible_approved_strategy_emits_candidate(regs, tmp_path, gdev):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    out = run(regs, [strat()], prov)
    assert out[-1]["message_type"] == "STRATEGY_CANDIDATE" and out[-1]["payload"]["result_status"] == "COMPLETED"


def test_missing_provider_is_eligibility_undetermined_failed(regs):
    out = run(regs, [strat()], None)
    m = out[-1]
    assert m["message_type"] == "STRATEGY_CANDIDATE" and m["status"] == "FAILED"
    e = m["payload"]["error"]
    assert m["payload"]["result_status"] == "ERROR" and e["code"] == "ELIGIBILITY_UNDETERMINED"
    assert e["stage"] == "STRATEGY_EVALUATION" and (e["strategy_id"], e["strategy_version"]) == ("S1", "1.0.0")


def test_timeout_is_undetermined_never_no_setup(regs, tmp_path, gdev, monkeypatch):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 0.05)
    lk = open(reg.path.with_name(reg.path.name + ".lock"), "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        out = run(regs, [strat()], prov)
    finally:
        lk.close()
    m = out[-1]
    assert m["message_type"] == "STRATEGY_CANDIDATE" and m["payload"]["error"]["code"] == "ELIGIBILITY_UNDETERMINED"
    assert "RegistryLockTimeout" in m["payload"]["error"]["message"]
    assert run(regs, [strat()], prov)[-1]["payload"]["result_status"] == "COMPLETED"   # recupera sin caché


def test_tampering_is_undetermined_and_never_evaluates_entries(regs, tmp_path, gdev):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    p = store.path_for(EID, "oos")
    p.chmod(0o644)
    p.write_bytes(p.read_bytes() + b" ")
    s = strat()
    calls = []
    s.evaluate_entry = lambda *a: calls.append(1)
    out = run(regs, [s], prov)
    assert out[-1]["payload"]["error"]["code"] == "ELIGIBILITY_UNDETERMINED" and not calls


def test_technical_precedence_over_eligible_and_shared_refs(regs, tmp_path, gdev):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    prov2 = O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], {EID: selp, "EXP-9999": selp})
    a, b = strat("S1"), strat("S2", exp="EXP-9999")
    out = run(regs, [a, b], prov2)                       # S1 elegible, S2 no determinable → error de S2
    e = out[-1]["payload"]["error"]
    assert e["code"] == "ELIGIBILITY_UNDETERMINED" and e["strategy_id"] == "S2"


def test_shared_experiment_reference_resolved_once(regs, tmp_path, gdev, monkeypatch):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    seen = []
    import swingpilot.engines.strategy as S
    real = S.resolve_et10
    monkeypatch.setattr(S, "resolve_et10", lambda p, ids: (seen.append(list(ids)), real(p, ids))[1])
    out = run(regs, [strat("S1", entry=False), strat("S2", entry=False)], prov)
    assert seen == [[EID]]                               # una sola resolución, referencia única
    assert out[-1]["payload"]["reason_code"] == "NO_CANDIDATE"


def test_methodological_loss_after_approval_excludes_and_reports(regs, tmp_path, gdev):
    from swingpilot.research.preregistration import _preregistered_sha, freeze
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    fz = freeze(c["pstore"].load(EID, _preregistered_sha(reg, EID)))
    fz.record_independence_deviation([f"{EID}/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN", "x",
                                     registry=reg, informed_by=[])
    out = run(regs, [strat()], prov)
    p = out[-1]["payload"]
    assert out[-1]["message_type"] == "NO_SETUP", p
    assert (p["reason_code"], p["reason_detail"]) == ("NO_APPROVED_STRATEGY", "CONFIRMATORY_ELIGIBILITY_LOST")
    assert p["evaluated_strategies"][0]["result"] == "NOT_ELIGIBLE" and p["llm_calls"] == 0


def test_none_approved_detail_and_research_mode_not_gated(regs):
    p = run(regs, [], None)[-1]["payload"]
    assert (p["reason_code"], p["reason_detail"]) == ("NO_APPROVED_STRATEGY", "NONE_APPROVED")
    out = run(regs, [FakeStrategy(status="RESEARCH")], None, mode="RESEARCH")      # no es uso operativo
    assert out[-1]["payload"]["result_status"] == "COMPLETED"


def test_protection_flows_preserved_when_eligibility_undetermined(regs):
    import uuid
    from swingpilot.engines.strategy import OpenPosition, ExitProposal, StopProposal
    pos = OpenPosition(str(uuid.uuid4()), "S1", "1.0.0", 95.0)
    out = run(regs, [strat(exit_=ExitProposal("EXIT_CONDITION", [], 99.0))], None, position=pos)   # sin proveedor
    assert [m["message_type"] for m in out] == ["STRATEGY_EXIT_SIGNAL", "NO_SETUP"]
    assert out[-1]["payload"]["reason_code"] == "EXIT_SIGNAL_PRIORITY"
    out = run(regs, [strat(trail=StopProposal(96.0, "TEST", {}))], None, position=pos)
    assert [m["message_type"] for m in out][0] == "STOP_ADJUSTMENT_REQUESTED"         # stop emitido, ET-10 no aplica
    assert out[-1]["payload"]["reason_code"] == "PRE_PHASE3_BLOCK"                    # OPEN_POSITION (INV-003)
    out = run(regs, [strat()], None, block="SAFE_MODE")
    assert out[-1]["payload"]["reason_code"] == "PRE_PHASE3_BLOCK"                    # bloqueo previo intacto


def test_provider_requires_absolute_paths(tmp_path, gdev):
    reg, store, c, selp, prov = approved(_sub(tmp_path), gdev)
    for sel in ({EID: Path("rel/sel.json")}, {EID: "rel.json"}):
        with pytest.raises(ValueError, match="absoluta"):
            O.EvidenceProvider(reg, c["pstore"], c["manifest_dir"], sel)
    with pytest.raises(ValueError, match="absoluta"):
        O.EvidenceProvider(reg, c["pstore"], Path("rel"), {EID: selp})
    with pytest.raises(ValueError, match="obligatorio"):
        O.EvidenceProvider(None, c["pstore"], c["manifest_dir"], {EID: selp})
