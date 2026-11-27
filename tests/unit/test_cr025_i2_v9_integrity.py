"""CR-025 I2: V9 en ET-9 bajo el bloqueo de promoción; consumed_line_sha256 en el verificador compartido (sintético)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr024_b8_3_promotion_eligibility import (AREF, EID, approved, promo_for, rejected, ModelRegistryError,  # noqa: E402,F401
                                                   approve, approval_doc, check_for, gdev, human_review, ggrant,
                                                   grant, make_genuine, ready, frozen_statistics, favorable_tape, ctx,
                                                   _GENUINE, GSID, models)
from historical_approval import seed_historical_approval  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import result_store as RST  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402


def _v9(reg, c):
    ck = I.stage_checks(reg, c["pstore"], EID, "ET-9", decisions_dir=reg.decisions_dir)
    return ck["V9"]


def _rewrite(reg, fn):
    lines = reg.path.read_bytes().split(b"\n")
    reg.path.write_bytes(b"\n".join(fn(lines)))


def test_production_historical_set_is_empty():
    assert I.HISTORICAL_APPROVALS == frozenset()


def test_genuine_et9_with_v9_ok_promotes(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    assert _v9(reg, c) == (I.OK, "")
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    assert mr.state("M1", "1.0.0") == "ACTIVE"
    mr.close()


def test_missing_binding_is_tech_and_blocks_promotion(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    def strip(lines):
        out = []
        for ln in lines:
            r = json.loads(ln) if ln else None
            if r and r.get("to") == "APPROVED":
                del r["evidence"]["approval_binding"]
                ln = json.dumps(r, ensure_ascii=False, sort_keys=True).encode()
            out.append(ln)
        return out
    _rewrite(reg, strip)
    assert _v9(reg, c)[0] == I.TECH
    with pytest.raises(ModelRegistryError, match="V9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    rejected(mr)
    mr.close()


def test_historical_set_exempts_only_exact_line_and_is_not_caller_controlled(tmp_path, gdev, monkeypatch):
    reg, store, wins, c = human_review(tmp_path, gdev)
    (reg.decisions_dir / AREF).write_text(f"AUTORIZA: {EID} APPROVED\n")
    seed_historical_approval(reg, EID, AREF)
    assert _v9(reg, c)[0] == I.TECH                                  # sin binding y fuera del conjunto
    line = [ln for ln in reg.path.read_bytes().split(b"\n") if b'"to": "APPROVED"' in ln][0]
    monkeypatch.setattr(I, "HISTORICAL_APPROVALS", frozenset({hashlib.sha256(line).hexdigest()}))
    assert _v9(reg, c) == (I.OK, "HISTORICAL")
    monkeypatch.setattr(I, "HISTORICAL_APPROVALS", frozenset({hashlib.sha256(line + b" ").hexdigest()}))
    assert _v9(reg, c)[0] == I.TECH
    with pytest.raises(TypeError):
        I.stage_checks(reg, c["pstore"], EID, "ET-9", historical_approvals={"x"})


def test_attestation_line_tampered_or_duplicated_is_tech(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    doc = reg.decisions_dir / AREF
    orig = doc.read_text()
    doc.write_text(orig + "texto libre añadido\n")                    # el resto del documento es editable
    assert _v9(reg, c) == (I.OK, "")
    doc.write_text(orig.replace("V7=CONFIRMADA", "V7=CONFIRMADA "))   # línea alterada (no gramatical)
    assert _v9(reg, c)[0] == I.TECH
    doc.write_text(orig + orig.split("\n")[1] + "\n")                 # duplicada
    assert _v9(reg, c)[0] == I.TECH
    doc.unlink()
    assert _v9(reg, c)[0] == I.TECH
    with pytest.raises(ModelRegistryError, match="V9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    mr.close()


def test_result_evidence_missing_or_corrupt_after_approval_is_tech(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    marks = reg.window_results()
    rs = RST.for_registry(reg)
    path = next(p for p in Path(rs.__dict__.get("root", reg.path.parent)).rglob("*")
                if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == marks[0]["evaluation_hash"])
    path.parent.chmod(0o755)
    path.chmod(0o644)                                              # el almacén es de solo lectura
    path.write_bytes(path.read_bytes() + b" ")
    assert _v9(reg, c)[0] == I.TECH
    path.unlink()
    assert _v9(reg, c)[0] == I.TECH
    with pytest.raises(ModelRegistryError, match="V9|ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    mr.close()


def test_shared_verifier_binds_exact_raw_consumed_line(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    ctx_ = I._context(reg, c["pstore"], EID)
    rs, sha = RST.for_registry(reg), ctx_["sha"]
    I.verify_result_evidence(ctx_["records"], rs, EID, "oos", prereg_sha=sha, lines=ctx_["lines"])
    i = next(k for k, r in enumerate(ctx_["records"]) if r.get("kind") == "PARTITION_CONSUMED" and r["partition"] == "oos")
    bad = list(ctx_["lines"])
    bad[i] = bad[i] + b" "
    with pytest.raises(I._Fail, match="consumed_line_sha256"):
        I.verify_result_evidence(ctx_["records"], rs, EID, "oos", prereg_sha=sha, lines=bad)
    with pytest.raises(TypeError):
        I.verify_result_evidence(ctx_["records"], rs, EID, "oos", prereg_sha=sha)      # `lines` obligatorio
    mr.close()


def _swap(ctx_, i, j):
    for k in ("records", "lines"):
        ctx_[k] = list(ctx_[k])
        ctx_[k][i], ctx_[k][j] = ctx_[k][j], ctx_[k][i]


def _idx(ctx_, kind, part=None, to=None):
    return [k for k, r in enumerate(ctx_["records"]) if r.get("kind") == kind and (part is None or r.get("partition") == part)
            and (to is None or r.get("to") == to)]


def test_event_ordering_violations_are_tech(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    base = I._context(reg, c["pstore"], EID)
    base["results"] = RST.for_registry(reg)
    assert I._v9(base, reg, EID, reg.decisions_dir) is None
    cases = [(("PARTITION_CONSUMED", "oos"), (X.RESULT_KIND, "oos")),            # consumo < marcador
             ((X.RESULT_KIND, "oos"), ("PARTITION_CONSUMED", "lockbox")),        # OOS completo < consumo LOCKBOX
             ((X.RESULT_KIND, "lockbox"), ("TRANSITION", None))]                 # LOCKBOX completo < APPROVED
    for (k1, p1), (k2, p2) in cases:
        cx = copy.copy(base)
        a = _idx(cx, k1, p1)[0]
        b = _idx(cx, k2, p2, to="APPROVED" if k2 == "TRANSITION" else None)[0]
        _swap(cx, a, b)
        with pytest.raises(I._Fail):
            I._v9(cx, reg, EID, reg.decisions_dir)
    mr.close()


def test_bypass_without_promotion_check_or_with_lambda_still_denied(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    for chk in (None, lambda *a: None):
        with pytest.raises(ModelRegistryError):
            mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=chk)
    rejected(mr, 2)
    mr.close()


# --- FIX-E (QA-C3-01 / sonda C): V9 lee la atestación del directorio autoritativo del registro -----------

def _alt_dir_check(reg, c, alt):
    return I.stage_checks(reg, c["pstore"], EID, "ET-9", decisions_dir=alt)["V9"]


def _clean_alt(tmp_path, reg):
    alt = tmp_path / "alt_decisions"
    alt.mkdir()
    (alt / AREF).write_text((reg.decisions_dir / AREF).read_text())     # copia limpia (original)
    return alt


def test_fixe_caller_dir_cannot_conceal_altered_authoritative_attestation(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    alt = _clean_alt(tmp_path, reg)
    assert _alt_dir_check(reg, c, alt) == (I.OK, "")                    # camino válido con directorio alterno limpio
    doc = reg.decisions_dir / AREF
    doc.write_text(doc.read_text().replace("V7=CONFIRMADA", "V7=CONFIRMADA "))   # altera la atestación autoritativa
    assert _alt_dir_check(reg, c, alt)[0] == I.TECH                     # el alterno limpio ya no la oculta
    assert _v9(reg, c)[0] == I.TECH
    with pytest.raises(ModelRegistryError, match="V9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    mr.close()


def test_fixe_alternative_dir_with_forged_line_cannot_validate_altered_original(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    doc = reg.decisions_dir / AREF
    orig = doc.read_text()
    alt = _clean_alt(tmp_path, reg)
    doc.write_text(orig + orig.split("\n")[1] + "\n")                   # duplicada en el directorio autoritativo
    assert _alt_dir_check(reg, c, alt)[0] == I.TECH
    mr.close()


def test_fixe_valid_promotion_and_none_dir_unchanged(tmp_path, gdev):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    assert I.stage_checks(reg, c["pstore"], EID, "ET-9")["V9"] == (I.OK, "")
    mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    assert mr.state("M1", "1.0.0") == "ACTIVE"
    mr.close()


# ---- FIX-QA GAP-01/GAP-02: estados de resultado tras la aprobación (fixtures genuinas; V9 solo TECH) -----------

def _drop_marker(reg, part):
    def fn(lines):
        keep = []
        for ln in lines:
            r = json.loads(ln) if ln else None
            if r and r.get("kind") == X.RESULT_KIND and r.get("partition") == part:
                continue
            keep.append(ln)
        return keep
    _rewrite(reg, fn)


def _assert_tech_not_method(reg, c, mr, wins):
    ck = I.stage_checks(reg, c["pstore"], EID, "ET-9", decisions_dir=reg.decisions_dir)["V9"]
    assert ck[0] == I.TECH and ck[0] != I.METHOD
    with pytest.raises(ModelRegistryError, match="V9|ET-9"):
        mr.promote("M1", "1.0.0", requested_by="orquestador", promotion_check=promo_for(reg, wins, c))
    rejected(mr)


@pytest.mark.parametrize("part", ["oos", "lockbox"])
@pytest.mark.parametrize("state", ["EVIDENCE_ONLY", "CONSUMED_NO_RESULT"])
def test_gap01_evidence_only_and_consumed_no_result_after_approval_are_tech(tmp_path, gdev, part, state):
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    rs = RST.for_registry(reg)
    _drop_marker(reg, part)
    if state == "CONSUMED_NO_RESULT":
        p = rs.path_for(EID, part)
        p.parent.chmod(0o755)
        p.chmod(0o644)
        p.unlink()
    assert reg.window_result_state(rs, EID, part) == state                  # estado genuino, no simulado
    _assert_tech_not_method(reg, c, mr, wins)
    mr.close()


@pytest.mark.parametrize("part", ["oos", "lockbox"])
def test_gap02_authoritative_unfavorable_result_after_approval_is_tech(tmp_path, gdev, part):
    from swingpilot.research.result_serialization import evaluation_hash
    reg, store, wins, c, mr = approved(tmp_path, gdev)
    rs = RST.for_registry(reg)
    p = rs.path_for(EID, part)
    old = p.read_bytes()
    data = old.replace(b'"verdict":"ELIGIBLE_FOR_HUMAN_REVIEW"', b'"verdict":"NOT_ELIGIBLE"') \
              .replace(b'"eligibility":"ELIGIBLE"', b'"eligibility":"NOT_ELIGIBLE"')
    assert data != old                                                      # la evidencia genuina se vuelve desfavorable
    h = evaluation_hash(data)
    p.parent.chmod(0o755)
    p.chmod(0o644)
    p.write_bytes(data)                                                     # evidencia, marcador y ligadura coherentes

    def fn(lines):
        out = []
        for ln in lines:
            r = json.loads(ln) if ln else None
            if r and r.get("kind") == X.RESULT_KIND and r.get("partition") == part:
                r.update(verdict="NOT_ELIGIBLE", eligibility="NOT_ELIGIBLE", evaluation_hash=h)
                ln = X._serialize(r) if hasattr(X, "_serialize") else json.dumps(r, sort_keys=True).encode()
            elif r and r.get("to") == "APPROVED":
                r["evidence"]["approval_binding"][f"{part}_evaluation_hash"] = h
                ln = X._serialize(r) if hasattr(X, "_serialize") else json.dumps(r, sort_keys=True).encode()
            out.append(ln.rstrip(b"\n") if isinstance(ln, bytes) else ln)
        return out
    _rewrite(reg, fn)
    assert reg.window_result_favorable(rs, EID, part) is False
    ck = I.stage_checks(reg, c["pstore"], EID, "ET-9", decisions_dir=reg.decisions_dir)["V9"]
    assert ck[0] == I.TECH and "no es favorable" in ck[1]
    _assert_tech_not_method(reg, c, mr, wins)
    mr.close()
