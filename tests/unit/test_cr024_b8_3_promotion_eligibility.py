"""B8.3 (CR-023 ET-9, DEC-025 U1): la promoción ML exige APPROVED + ET-9 ELIGIBLE recalculada (sintético)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from test_snapshot import _GENUINE, GSID, gdev, ggrant, grant, make_genuine  # noqa: E402,F401
from test_cr023_b7_e2e_window import REF, ctx, frozen_statistics, ready  # noqa: E402,F401
from tape import favorable_tape  # noqa: E402,F401
from test_cr024_b8_2_approval_transition import (  # noqa: E402
    AREF, EID, approval_doc, approve, check_for, human_review)
from historical_approval import legacy_promotion_check, seed_historical_approval  # noqa: E402
from swingpilot.ml import ModelRegistry, ModelRegistryError  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402

D, C = "d" * 64, "c" * 64


def promo_for(reg, wins, c):
    return I.build_promotion_check(reg, c["pstore"], wins, decisions_dir=reg.decisions_dir,
                                   preregistration=c["preregistration"], selection_inputs=c["selection_inputs"])


def models(tmp_path, reg):
    mr = ModelRegistry(tmp_path / "models.db", reg)
    mr.register("M1", "1.0.0", data_hash=D, code_hash=C, params={}, experiment_id=EID)
    return mr


def approved(tmp_path, gdev, historical=False):
    reg, store, wins, c = human_review(tmp_path, gdev)
    if historical:
        seed_historical_approval(reg, EID, "DEC-998_aprobacion.md") if _doc(reg) else None
    else:
        approval_doc(reg, store)
        approve(reg, check_for(reg, store, wins, c))
    return reg, store, wins, c, models(tmp_path, reg)


def _doc(reg):
    (reg.decisions_dir / AREF).write_text(f"AUTORIZA: {EID} APPROVED\n")
    return True


def rejected(mr, n=1):
    ev = [e[2] for e in mr.events("M1")]
    assert ev == ["REGISTERED"] + ["PROMOTION_REJECTED"] * n and mr.active_model() is None
    assert mr.state("M1", "1.0.0") == "REGISTERED"


def test_genuine_et9_promotes_and_leaves_registry_untouched(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    before = reg.path.read_bytes()
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    assert mr.state("M1", "1.0.0") == "ACTIVE" and reg.path.read_bytes() == before
    mr.close()


def test_historical_approval_preserved_but_needs_et9(tmp_path, gdev, monkeypatch):
    import hashlib
    reg, store, wins, c, mr = approved(tmp_path, gdev, historical=True)
    line = [ln for ln in reg.path.read_bytes().split(b"\n") if b'"to": "APPROVED"' in ln][0]
    assert reg.state(EID) == "APPROVED"
    with pytest.raises(ModelRegistryError, match="promotion_check"):
        mr.promote("M1", "1.0.0", requested_by="orquestador")
    rejected(mr)
    with pytest.raises(ModelRegistryError, match="V9"):     # CR-025: sin binding y fuera del conjunto vacío → TECH
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    monkeypatch.setattr(I, "HISTORICAL_APPROVALS", frozenset({hashlib.sha256(line).hexdigest()}))   # solo fixture
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    assert mr.state("M1", "1.0.0") == "ACTIVE" and reg.state(EID) == "APPROVED"
    mr.close()


def test_bypass_paths_denied(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    other = X.ExperimentRegistry(tmp_path / "otro.jsonl", reg.decisions_dir)
    bad = (None, lambda r, e: None, object(), X.FreezeCheck(X._FREEZE_CHECK_KEY, lambda *a: None),
           I.build_approval_check(reg, c["pstore"], wins), I.build_promotion_check(other, c["pstore"], wins),
           legacy_promotion_check(other))
    for b in bad:
        with pytest.raises(ModelRegistryError, match="promotion_check"):
            mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=b)
    with pytest.raises(X.ExperimentError):
        X.PromotionCheck(object(), lambda *a: None, reg)
    with pytest.raises(AttributeError):
        promo_for(reg, wins, c).registry = None
    rejected(mr, len(bad))
    mr.close()


def test_technical_loss_blocks_with_fresh_recompute(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    check = promo_for(reg, wins, c)                       # construida cuando era elegible
    wins[1]["manifest"] = wins[0]["manifest"]             # manifiesto de la ventana ya no verificable (V4post/V5)
    with pytest.raises(ModelRegistryError, match="ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=check)
    rejected(mr)
    assert reg.state(EID) == "APPROVED"                   # el APPROVED histórico no se modifica
    mr.close()


def test_methodological_loss_blocks(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    # una liberación previa del OOS al evaluador contamina la independencia (ET-9: RELEASE/V8)
    (reg.decisions_dir / "DEC-996_lib.md").write_text(f"AUTORIZA: LIBERACION {EID}/OOS SHA256={'a' * 64}\n")
    with pytest.raises(ModelRegistryError, match="ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    rejected(mr)
    mr.close()


def test_missing_window_or_unverifiable_inputs_block(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    with pytest.raises(ModelRegistryError, match="ventanas"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins[:1], c))
    broken = [{**wins[0], "manifest": None}, wins[1]]
    with pytest.raises(ModelRegistryError, match="UNDETERMINABLE|ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, broken, c))
    rejected(mr, 2)
    mr.close()


def test_registry_corruption_blocks_promotion(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    check = promo_for(reg, wins, c)
    with open(reg.path, "ab") as fh:
        fh.write(b"{no es json\n")
    with pytest.raises(ModelRegistryError, match="no verificable|ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=check)
    rejected(mr)
    mr.close()


def test_not_approved_and_existing_requirements_unchanged(tmp_path, gdev):
    reg, store, wins, c = human_review(tmp_path, gdev)           # HUMAN_REVIEW, sin APPROVED
    mr = models(tmp_path, reg)
    with pytest.raises(ModelRegistryError, match="APPROVED"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    with pytest.raises(ModelRegistryError, match="no registrado"):
        mr.promote("M9", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    rejected(mr)
    mr.close()


def test_concurrent_promotions_yield_a_single_active_model(tmp_path):
    """Dos conexiones (como dos procesos) al mismo models.db promueven a la vez: el bloqueo del registro de
    experimentos serializa gate+PROMOTED, así que a lo sumo uno queda ACTIVE y el otro se rechaza registrado."""
    import threading
    from test_ml_registry import approve as legacy_approve
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-901_ok.md").write_text("".join(f"AUTORIZA: EXP-0201 {s}\n" for s in ("OOS_EVALUATION", "APPROVED")))
    exps = X.ExperimentRegistry(tmp_path / "registry.jsonl", dec)
    legacy_approve(exps, "EXP-0201")
    seed = ModelRegistry(tmp_path / "models.db", exps)
    for i in range(6):
        seed.register(f"M{i}", "1.0.0", data_hash=D, code_hash=C, params={"i": i}, experiment_id="EXP-0201")
    seed.close()
    barrier, out = threading.Barrier(6), []

    def worker(i):
        mr = ModelRegistry(tmp_path / "models.db", exps)        # conexión propia por hilo
        try:
            barrier.wait()
            mr.promote(f"M{i}", "1.0.0", requested_by="orquestador", promotion_check=legacy_promotion_check(exps))
            out.append("ok")
        except ModelRegistryError:
            out.append("rejected")
        finally:
            mr.close()
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    chk = ModelRegistry(tmp_path / "models.db", exps)
    active = [i for i in range(6) if chk.state(f"M{i}", "1.0.0") == "ACTIVE"]
    ev = [e[2] for e in chk.events()]
    chk.close()
    assert sorted(out) == ["ok"] + ["rejected"] * 5 and len(active) == 1
    assert ev.count("PROMOTED") == 1 and ev.count("PROMOTION_REJECTED") == 5
