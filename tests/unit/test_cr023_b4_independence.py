"""CR-023 B4: independence_status, regla endurecida, V1–V8 por etapa y clasificación D.8 (datos sintéticos)."""
from __future__ import annotations

import os
import sys

from consumption_helpers import ok_consumption_check  # noqa: E402
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_cr023_b3_preregistration import (B_DEFAULT, EVIDENCE_REF, _confirmatory_in, dev_snap, env)  # noqa: E402,F401
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402

EID = "EXP-0201"


def _lines(env, sha=None, *, p="2027-02-20T12:00:00Z", res="VALIDA", extra_front=(), extra_pub=(), pub=True, front=True):
    sha = sha or PR._preregistered_sha(env.reg, EID)
    out = []
    if front:
        out.append(f"AUTORIZA: FRONTERA {EID} SHA256={sha} B={B_DEFAULT}")
    if pub:
        out.append(f"AUTORIZA: PUBLICACION {EID} SHA256={sha} B={B_DEFAULT} P={p} RESULTADO={res}")
    out += list(extra_front) + list(extra_pub)
    (env.reg.decisions_dir / "DEC-901_frontera.md").write_text("\n".join(out) + "\n")


def _status(env):
    return I.independence_status(env.reg, env.store, EID)


def _chk(env, stage, **kw):
    return I.stage_checks(env.reg, env.store, EID, stage, **kw)


def _dev(env, fz):
    return fz.record_independence_deviation([f"{EID}/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN",
                                            "x", registry=env.reg, informed_by=[])


def test_stage_matrix_matches_c9():
    assert I.STAGES["ET-1"] == ("V2", "V7m") and I.STAGES["ET-3"] == ("V1b",)
    assert "V4pre" in I.STAGES["ET-6"] and "V4post" in I.STAGES["ET-7"] and "V5" not in I.STAGES["ET-4"]
    assert set(I.STAGES["ET-5"]) == {"V1b", "V2", "V3", "V4pre", "V5", "V6", "V7m", "V7d", "V8"}
    assert "V1b" in I.STAGES["ET-8"] and "V1b" not in I.STAGES["ET-9"]


def test_independence_status_three_outcomes_and_read_only(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    before = env.records_bytes()
    assert _status(env) == I.INDEPENDENT
    assert env.records_bytes() == before
    _dev(env, fz)
    assert _status(env) == I.CONTAMINATED
    for f in (env.store.root).rglob("*.json"):
        f.unlink()
    assert _status(env) == I.INDETERMINATE                                   # contenido no recuperable (V2)


def test_pilot_and_unknown_experiment_are_indeterminate(env):
    env.pilot()
    assert I.independence_status(env.reg, env.store, "EXP-0200") == I.INDETERMINATE
    assert I.independence_status(env.reg, env.store, "EXP-0999") == I.INDETERMINATE
    assert I.independence_status(env.reg, None, "EXP-0200") == I.INDETERMINATE


def test_contamination_by_other_experiment_period_intersection(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    _dev(env, fz)
    # un experimento posterior con ventanas disjuntas no resulta afectado (D.3.3): se comprueba con la función de periodos
    assert I.independence_status(env.reg, env.store, EID) == I.CONTAMINATED


def test_d33_unaffected_experiment_with_disjoint_windows_stays_independent(env):
    """CR-023 D.3.3 (regresión positiva): un DEVIATION de EXP-0201 contamina solo a EXP-0201; EXP-0202, con
    ventanas disjuntas y posteriores (C.4.2.3), permanece INDEPENDENT y sin cambios."""
    fz1 = _confirmatory_in(env, "PREREGISTERED")
    env.design("EXP-0202")
    env.prereg(env.frozen("EXP-0202", b="2029-03-01T00:00:00Z"))       # [fin del LOCKBOX de EXP-0201, …)
    assert I.independence_status(env.reg, env.store, "EXP-0202") == I.INDEPENDENT
    _dev(env, fz1)                                                      # contamina OOS de EXP-0201 (dueño)
    assert _status(env) == I.CONTAMINATED
    assert I.independence_status(env.reg, env.store, "EXP-0202") == I.INDEPENDENT
    assert PR.confirmatory_findings(env.reg, "EXP-0202")["hardened_deviations"] == []


def test_hardened_rule_any_field_makes_it_non_confirmatory_without_consumption(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    assert PR.confirmatory_findings(env.reg, EID)["hardened_deviations"] == []
    _dev(env, fz)
    st = PR.confirmatory_findings(env.reg, EID)
    assert st["confirmatory"] is False and len(st["hardened_deviations"]) == 1 and not st["design_deviations_after_oos"]


def test_v1_et2_requires_exactly_one_matching_frontera(env):
    _confirmatory_in(env, "PREREGISTERED")
    assert _chk(env, "ET-2")["V1a"][0] == I.TECH                             # ausente
    _lines(env, pub=False)
    assert _chk(env, "ET-2")["V1a"][0] == I.OK
    _lines(env, pub=False, extra_front=[f"AUTORIZA: FRONTERA {EID} SHA256={'0' * 64} B={B_DEFAULT}"])
    assert _chk(env, "ET-2")["V1a"][0] == I.TECH                             # duplicada
    _lines(env, sha="a" * 64, pub=False)
    assert _chk(env, "ET-2")["V1a"][0] == I.TECH                             # hash distinto


@pytest.mark.parametrize("bad", ["{l} ", "{l}\r", "  {l}", "{l}  X=1"])
def test_v1_strict_grammar_rejects_near_misses(env, bad):
    _confirmatory_in(env, "PREREGISTERED")
    good = f"AUTORIZA: FRONTERA {EID} SHA256={PR._preregistered_sha(env.reg, EID)} B={B_DEFAULT}"
    (env.reg.decisions_dir / "DEC-901_frontera.md").write_bytes((bad.format(l=good) + "\n").encode())
    assert _chk(env, "ET-2")["V1a"][0] == I.TECH


@pytest.mark.parametrize("kw,nature", [
    ({}, I.OK),
    ({"p": "2027-02-28T12:00:00Z", "res": "INVALIDA"}, I.METHOD),            # P + 24 h > B
    ({"p": "NONE", "res": "INVALIDA"}, I.METHOD),                            # nunca se publicó
    ({"p": "NONE", "res": "VALIDA"}, I.TECH),
    ({"p": "2027-02-28T12:00:00Z", "res": "VALIDA"}, I.TECH),                # incoherente con B
    ({"p": "2020-01-01T00:00:00Z", "res": "VALIDA"}, I.TECH),                # anterior a PREREGISTERED
    ({"pub": False}, I.TECH),                                                # ausente
])
def test_v1_publication_attestation_classification(env, kw, nature):
    _confirmatory_in(env, "PREREGISTERED")
    _lines(env, **kw)
    assert _chk(env, "ET-3")["V1b"][0] == nature


def test_v3_and_v8_are_methodological_after_a_deviation(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    _lines(env)
    _dev(env, fz)
    c = _chk(env, "ET-4", manifest={})
    assert c["V3"][0] == I.METHOD and c["V8"][0] == I.METHOD


def test_eligibility_classification_and_precedence(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    _lines(env)
    ok = I.eligibility(env.reg, env.store, EID, "ET-2")
    assert ok["result"] in (I.ELIGIBLE, I.UNDETERMINABLE)                    # confirmatory_status puede ser «no verificable»
    _dev(env, fz)
    nok = I.eligibility(env.reg, env.store, EID, "ET-2")
    assert nok["result"] == I.NOT_ELIGIBLE and nok["nature"] == "METHODOLOGICAL"
    for f in env.store.root.rglob("*.json"):
        f.unlink()
    tech = I.eligibility(env.reg, env.store, EID, "ET-2")
    assert tech["result"] == I.UNDETERMINABLE and tech["nature"] == "TECHNICAL"   # precedencia técnica


def test_missing_evidence_is_never_not_applicable_and_unknown_stage_fails(env):
    _confirmatory_in(env, "PREREGISTERED")
    assert _chk(env, "ET-5")["V5"][0] == I.TECH and _chk(env, "ET-5")["V6"][0] == I.TECH
    assert _chk(env, "ET-7", manifest=None)["V4post"][0] == I.TECH
    with pytest.raises(ValueError):
        _chk(env, "ET-99")


def test_v7_mechanical_reference(env):
    _confirmatory_in(env, "PREREGISTERED")
    assert _chk(env, "ET-1")["V7m"][0] == I.OK


class _Grant:
    def __init__(self, ref="DEC-903_grant.md", snap="SNAP-0007", part="oos"):
        self.experiment_id, self.partition, self.snapshot_id, self.decision_ref = EID, part, snap, ref


_TAIL = "V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA"


def _att(env, *, sha=None, snap="SNAP-0007", win="OOS", doc="DEC-903_grant.md", tail=_TAIL):
    sha = sha or PR._preregistered_sha(env.reg, EID)
    line = f"AUTORIZA: ATESTACION {EID}/{win} {snap} SHA256={sha} {tail}"
    (env.reg.decisions_dir / doc).write_text(line + "\n")
    return line


def _v67(env, grant=None, window="OOS"):
    ctx = I._context(env.reg, env.store, EID)
    return I._v6_v7d(ctx, EID, env.reg.decisions_dir, grant, {"window_id": f"{EID}/{window}"})


def test_b61_attestation_bound_to_grant_passes(env):
    _confirmatory_in(env, "PREREGISTERED")
    _att(env)
    assert _v67(env, _Grant()) is None


@pytest.mark.parametrize("mut", [
    {"tail": "V1=CONFIRMADA V6=CONFIRMADA V7=NO"}, {"tail": _TAIL + " X=1"}, {"tail": _TAIL + " "},
    {"tail": "V1=confirmada V6=CONFIRMADA V7=CONFIRMADA"},
    {"snap": "SNAP-0008"}, {"sha": "0" * 64}, {"win": "LOCKBOX"}, {"doc": "DEC-904_other.md"}])
def test_b61_attestation_rejects_malformed_or_unbound(env, mut):
    _confirmatory_in(env, "PREREGISTERED")
    (env.reg.decisions_dir / "DEC-903_grant.md").write_text("nada\n")
    _att(env, **mut)
    with pytest.raises(I._Fail) as e:
        _v67(env, _Grant())
    assert e.value.nature == I.TECH


def test_b61_attestation_crlf_tab_and_uppercase_hash_rejected(env):
    _confirmatory_in(env, "PREREGISTERED")
    line = _att(env)
    sha = line.split("SHA256=")[1][:64]
    for bad in (line + "\r", line.replace(" V1", "\tV1"), line.replace(sha, sha.upper() if sha != sha.upper() else "A" * 64)):
        (env.reg.decisions_dir / "DEC-903_grant.md").write_bytes((bad + "\n").encode())
        with pytest.raises(I._Fail):
            _v67(env, _Grant())


def test_b61_attestation_must_be_unique_even_if_identical_and_present(env):
    _confirmatory_in(env, "PREREGISTERED")
    line = _att(env)
    (env.reg.decisions_dir / "DEC-905_dup.md").write_text(line + "\n")
    with pytest.raises(I._Fail):
        _v67(env, _Grant())
    (env.reg.decisions_dir / "DEC-905_dup.md").unlink()
    (env.reg.decisions_dir / "DEC-903_grant.md").write_text("")
    with pytest.raises(I._Fail):
        _v67(env, _Grant())


@pytest.mark.parametrize("g", [None, _Grant(ref="../x.md"), _Grant(ref="DEC-999_missing.md"), _Grant(part="lockbox")])
def test_b61_requires_grant_and_matching_window(env, g):
    _confirmatory_in(env, "PREREGISTERED")
    _att(env)
    with pytest.raises(I._Fail):
        _v67(env, g)


def test_b61_stage_checks_derives_v6_v7_from_grant_and_free_dict_is_gone(env):
    _confirmatory_in(env, "PREREGISTERED")
    _att(env)
    ok = _chk(env, "ET-5", grant=_Grant(), manifest={"window_id": f"{EID}/OOS"})
    assert ok["V6"][0] == I.OK and ok["V7d"][0] == I.OK
    assert _chk(env, "ET-5")["V6"][0] == I.TECH
    with pytest.raises(TypeError):
        _chk(env, "ET-5", attestations={"V6": "DEC-902_v6.md"})


def test_b61_attestation_does_not_replace_v1(env):
    _confirmatory_in(env, "PREREGISTERED")
    _att(env)                                                           # sin FRONTERA/PUBLICACION
    assert _chk(env, "ET-5", grant=_Grant(), manifest={"window_id": f"{EID}/OOS"})["V1b"][0] == I.TECH


def test_b4_01_et2_does_not_depend_on_the_publication_attestation(env):
    """Disposición aprobada: ET-2 solo exige la cita del SHA-256; PUBLICACION se exige desde ET-3."""
    _confirmatory_in(env, "PREREGISTERED")
    good = f"AUTORIZA: PUBLICACION {EID} SHA256={PR._preregistered_sha(env.reg, EID)} B={B_DEFAULT} P=NONE RESULTADO=INVALIDA"
    _lines(env, pub=False, extra_pub=[f"AUTORIZA: PUBLICACION {EID} mal formada", good, good])
    assert _chk(env, "ET-2")["V1a"][0] == I.OK                               # ni mal formada ni duplicada bloquean ET-2
    assert _chk(env, "ET-3")["V1b"][0] == I.TECH                             # desde ET-3 sí (Fail-Closed)


def test_b4_02_hardened_class_is_the_confirmatory_class_and_is_applied_on_every_status_path(env, monkeypatch):
    import inspect
    assert PR._HARDENED_CLASS == "CONFIRMATORY"                              # valor de producción (sin parche)
    assert "_HARDENED_CLASS =" not in inspect.getsource(I)                  # ningún camino sancionado lo cambia
    fz = _confirmatory_in(env, "PREREGISTERED")
    _lines(env)
    _dev(env, fz)
    assert PR.confirmatory_status(env.reg, EID)["confirmatory"] is False
    res = I.eligibility(env.reg, env.store, EID, "ET-2")
    assert res["result"] == I.NOT_ELIGIBLE and "confirmatory_status" in res["causes"]


# --- B6.2: resolvedor snapshot→ventana y V4 a nivel de ventana (decisión 3) -------------------------------

import json  # noqa: E402

from swingpilot.research import boundary as BD  # noqa: E402
from swingpilot.research import snapshot as SN  # noqa: E402

_REF = "DEC-903_grant.md"


@pytest.fixture
def mdir(env, tmp_path, monkeypatch):
    monkeypatch.setattr(SN, "validate_manifest", lambda m: m if isinstance(m, dict) else (_ for _ in ()).throw(ValueError("x")))
    d = tmp_path / "manifests"
    d.mkdir()
    return d


def _mf(env, mdir, sid, win="OOS", *, stem=None, eid=EID, **over):
    ctx = I._context(env.reg, env.store, EID)
    start, end = BD.windows(ctx["ib"], EID)[f"{EID}/{win}"]
    snap = ctx["content"]["snapshot"]
    m = {"snapshot_id": sid, "kind": SN.KIND_EVALUATION, "window_id": f"{eid}/{win}", "d_dev": snap["d_dev"],
         "window": {"start_ms": BD.to_ms(start), "end_exclusive_ms": BD.to_ms(end)},
         "development_snapshot": {"snapshot_id": snap["snapshot_id"], "train_val_sha256": snap["train_val_sha256"]}}
    m.update(over)
    (mdir / f"{stem or sid}.json").write_text(json.dumps(m))
    return m


def _favorable_oos(env, mdir):
    """CR-024 B.7: OOS favorable genuino persistido (camino real) antes de admitir el LOCKBOX."""
    from cr024_oos import persist_favorable_oos
    persist_favorable_oos(env.reg, mdir, EID)


def _claim(env, sid, part, ref=_REF, eid=EID):
    env.reg.claim_partition(snapshot_id=sid, partition=part, experiment_id=eid, snapshot_last_open_time=1,
                            decision_ref=ref, consumption_check=ok_consumption_check())


def _v4(env, mdir, stage, win="OOS", manifest=None, ref=_REF):
    return _chk(env, stage, manifest_dir=mdir, window_id=f"{EID}/{win}", decision_ref=ref, manifest=manifest)


def test_b62_pre_unconsumed_window_passes_and_post_requires_one_owner_consumption(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    m = _mf(env, mdir, "SNAP-0010")
    assert _v4(env, mdir, "ET-6", manifest=m)["V4pre"][0] == I.OK
    assert _v4(env, mdir, "ET-7", manifest=m)["V4post"][0] == I.TECH          # sin consumo
    _claim(env, "SNAP-0010", "oos")
    assert _v4(env, mdir, "ET-7", manifest=m)["V4post"] == (I.OK, "")
    assert _v4(env, mdir, "ET-6", manifest=m)["V4pre"][0] == I.TECH           # ya consumida
    assert _v4(env, mdir, "ET-7", manifest=m, ref="DEC-999_otra.md")["V4post"][0] == I.TECH


def test_b62_lockbox_requires_consumed_oos_in_pre_and_post(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    _mf(env, mdir, "SNAP-0010", "OOS")
    _mf(env, mdir, "SNAP-0011", "LOCKBOX")
    assert _v4(env, mdir, "ET-6", "LOCKBOX")["V4pre"][0] == I.TECH
    _claim(env, "SNAP-0010", "oos")
    assert _v4(env, mdir, "ET-6", "LOCKBOX")["V4pre"][0] == I.TECH            # CR-024 B.7: consumido, sin OOS favorable persistido
    _favorable_oos(env, mdir)
    assert _v4(env, mdir, "ET-6", "LOCKBOX")["V4pre"][0] == I.OK
    _claim(env, "SNAP-0011", "lockbox")
    assert _v4(env, mdir, "ET-7", "LOCKBOX")["V4post"][0] == I.OK


def test_b62_missing_ambiguous_or_invalid_manifests_fail_closed(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    assert _v4(env, mdir, "ET-6")["V4pre"][0] == I.TECH                       # 0 manifiestos
    _mf(env, mdir, "SNAP-0010")
    assert _v4(env, mdir, "ET-6")["V4pre"][0] == I.OK
    _mf(env, mdir, "SNAP-0012")                                               # duplicado de la ventana
    assert _v4(env, mdir, "ET-6")["V4pre"][0] == I.TECH
    (mdir / "SNAP-0012.json").unlink()
    (mdir / "SNAP-0013.json").write_text("{no json")                          # ilegible
    assert _v4(env, mdir, "ET-6")["V4pre"][0] == I.TECH
    (mdir / "SNAP-0013.json").unlink()
    _mf(env, mdir, "SNAP-0014", stem="SNAP-0015")                             # stem ≠ snapshot_id
    assert _v4(env, mdir, "ET-6")["V4pre"][0] == I.TECH
    assert _v4(env, None, "ET-6")["V4pre"][0] == I.TECH


def test_b62_inconsistent_consumption_evidence_fails_closed(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    _mf(env, mdir, "SNAP-0010")
    _claim(env, "SNAP-0099", "oos")                                           # huérfano de la ventana objetivo
    assert _v4(env, mdir, "ET-7")["V4post"][0] == I.TECH
    _mf(env, mdir, "SNAP-0099", "LOCKBOX")                                    # consumo oos sobre manifiesto lockbox
    assert _v4(env, mdir, "ET-7")["V4post"][0] == I.TECH


def test_b62_foreign_consumption_of_target_window_and_mismatched_manifest_arg(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    m = _mf(env, mdir, "SNAP-0010")
    _claim(env, "SNAP-0010", "oos", eid="EXP-0999")                           # otro experimento: no cuadra con la ventana
    assert _v4(env, mdir, "ET-7", manifest=m)["V4post"][0] == I.TECH
    assert _v4(env, mdir, "ET-6", manifest=dict(m, d_dev="1999-01-01"))["V4pre"][0] == I.TECH


def test_b62_resolver_is_read_only(env, mdir):
    import hashlib
    _confirmatory_in(env, "PREREGISTERED")
    _mf(env, mdir, "SNAP-0010")
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in mdir.iterdir()}
    reg_before = env.reg.path.read_bytes() if env.reg.path.exists() else b""
    _v4(env, mdir, "ET-6")
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in mdir.iterdir()}
    assert (env.reg.path.read_bytes() if env.reg.path.exists() else b"") == reg_before


def test_b62_et4_needs_no_target_manifest_but_rejects_an_existing_one_or_consumption(env, mdir):
    _confirmatory_in(env, "PREREGISTERED")
    stub = {"window_id": f"{EID}/OOS", "snapshot_id": None}
    assert _v4(env, mdir, "ET-4", manifest=stub)["V4pre"][0] == I.OK
    assert _chk(env, "ET-4", manifest=stub)["V4pre"][0] == I.TECH             # B6.4: sin fallback; manifest_dir obligatorio
    _mf(env, mdir, "SNAP-0010")
    assert _v4(env, mdir, "ET-4", manifest=stub)["V4pre"][0] == I.TECH        # ya existe un manifiesto
    (mdir / "SNAP-0010.json").unlink()
    _claim(env, "SNAP-0010", "oos")
    assert _chk(env, "ET-4", manifest=stub)["V4pre"][0] == I.TECH


# --- B6.4: comprobación de consumo de producción bajo bloqueo y publicación coordinada -----------------

@pytest.fixture
def et6_stubbed(monkeypatch):
    """Este env solo llega a PREREGISTERED: las comprobaciones V de ET-6 (cubiertas en sus propias pruebas) se
    sustituyen por «sin denegaciones». Ligadura, manifiesto único y OOS-antes-que-LOCKBOX siguen siendo REALES."""
    monkeypatch.setattr(I, "stage_checks", lambda *a, **k: {})


def _real_claim(env, mdir, sid, part, eid=EID, manifest=None):
    """Credencial de producción GENUINAMENTE ligada (grant + registro + manifiesto leído de `mdir`)."""
    from swingpilot.research import partitions as PT
    if manifest is None:     # el manifiesto ligado es el de la snapshot; si aún no hay archivo, el que se pediría
        f = mdir / f"{sid}.json"
        manifest = json.loads(f.read_text()) if f.exists() else {"snapshot_id": sid, "window_id": f"{eid}/{part.upper()}"}
    grant = _Grant(snap=sid, part=part)
    return env.reg.claim_partition(
        snapshot_id=sid, partition=part, experiment_id=eid, snapshot_last_open_time=1, decision_ref=_REF,
        consumption_check=PT.build_consumption_check(mdir, registry=env.reg, store=env.store,
                                                     decisions_dir=env.reg.decisions_dir, grant=grant,
                                                     manifest=manifest))


def test_b64_production_check_enforces_manifest_unique_window_and_oos_before_lockbox(env, mdir, et6_stubbed):
    from swingpilot.research.experiments import ExperimentError
    _confirmatory_in(env, "PREREGISTERED")
    with pytest.raises(ExperimentError, match="manifiestos"):                 # sin manifiesto
        _real_claim(env, mdir, "SNAP-0010", "oos")
    _mf(env, mdir, "SNAP-0010")
    _mf(env, mdir, "SNAP-0011")                                               # duplicado de la ventana
    with pytest.raises(ExperimentError, match="hay 2"):
        _real_claim(env, mdir, "SNAP-0010", "oos")
    (mdir / "SNAP-0011.json").unlink()
    _mf(env, mdir, "SNAP-0020", win="LOCKBOX")
    with pytest.raises(ExperimentError, match="OOS"):                         # LOCKBOX antes que OOS
        _real_claim(env, mdir, "SNAP-0020", "lockbox")
    assert env.reg.consumed_partitions() == []
    assert _real_claim(env, mdir, "SNAP-0010", "oos")["kind"] == "PARTITION_CONSUMED"
    assert _real_claim(env, mdir, "SNAP-0010", "oos") is None                 # ya consumida: contrato previo
    _favorable_oos(env, mdir)
    assert _real_claim(env, mdir, "SNAP-0020", "lockbox")["partition"] == "lockbox"


def test_b64_concurrent_claims_consume_once_under_lock(env, mdir, et6_stubbed):
    import threading
    _confirmatory_in(env, "PREREGISTERED")
    _mf(env, mdir, "SNAP-0010")
    res, bar = [], threading.Barrier(4)

    def go():
        bar.wait()
        try:
            res.append(_real_claim(env, mdir, "SNAP-0010", "oos"))
        except Exception as exc:
            res.append(exc)
    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(1 for r in res if isinstance(r, dict)) == 1 and not [r for r in res if isinstance(r, Exception)]
    assert len(env.reg.consumed_partitions()) == 1


def test_b64_et4_publication_under_lock_rejects_duplicate_manifest_and_consumed_window(env, mdir):
    from swingpilot.research.experiments import ExperimentError
    _confirmatory_in(env, "PREREGISTERED")
    wid, ran = f"{EID}/OOS", []

    def chk(records):
        I._v4({"records": records}, EID, None, False, None, mdir, wid, et4=True)
    env.reg.publish_under_lock(chk, lambda: ran.append(1))                    # ventana libre: publica
    _mf(env, mdir, "SNAP-0010")                                               # otro ET-4 ganó la carrera
    with pytest.raises(I._Fail, match="hay 1"):
        env.reg.publish_under_lock(chk, lambda: ran.append(2))
    (mdir / "SNAP-0010.json").unlink()
    _mf(env, mdir, "SNAP-0011")
    _claim(env, "SNAP-0011", "oos")
    (mdir / "SNAP-0011.json").unlink()
    with pytest.raises(I._Fail):                                              # consumo huérfano o ventana consumida
        env.reg.publish_under_lock(chk, lambda: ran.append(3))
    assert ran == [1]
    with pytest.raises(I._Fail, match="sin directorio"):                      # sin fallback: manifest_dir obligatorio
        I._v4({"records": []}, EID, None, False, None, None, wid, et4=True)
