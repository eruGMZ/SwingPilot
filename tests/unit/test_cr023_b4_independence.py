"""CR-023 B4: independence_status, regla endurecida, V1–V8 por etapa y clasificación D.8 (datos sintéticos)."""
from __future__ import annotations

import os
import sys

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


def test_v7_mechanical_and_documentary_reference(env):
    _confirmatory_in(env, "PREREGISTERED")
    assert _chk(env, "ET-1")["V7m"][0] == I.OK
    (env.reg.decisions_dir / "DEC-902_v6.md").write_text("x")
    assert I._v6_v7d({"V6": "DEC-902_v6.md"}, "V6", env.reg.decisions_dir) is None
    with pytest.raises(I._Fail):
        I._v6_v7d({"V6": "../x.md"}, "V6", env.reg.decisions_dir)


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
