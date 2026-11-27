"""CR-023 B7.4b — procedencia de los datos evaluados y progresión genuina OOS → LOCKBOX.

Sintético y sellado: las velas (tape.py) atraviesan el constructor real de snapshots, `load_final` (grant,
ET-5/ET-6, consumo), ET-7 y la conciliación de pruebas. Los casos de sustitución parten de datos genuinos ya
consumidos y los alteran DESPUÉS de la carga; el evaluador debe negarse. No se finaliza D6 (valores sintéticos)."""
import dataclasses
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_snapshot import _GENUINE, _loader, gdev, ggrant, grant  # noqa: E402,F401
from test_cr023_b6_context_reading import EID, consumed  # noqa: E402
from test_cr023_b7_e2e_window import (REF, ctx, evaluate, frozen_statistics, ready, w4)  # noqa: E402,F401
from test_cr023_b7_acceptance_window import Logic, MODEL  # noqa: E402
from tape import favorable_tape  # noqa: E402,F401
from swingpilot.research import evaluation_snapshot as E  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402
from swingpilot.research import window_evaluation as W  # noqa: E402
from swingpilot.research.snapshot import SNAPSHOT_INTERVALS  # noqa: E402


def _refuses(out):
    assert (out.verdict, out.nature, out.eligibility, out.metrics) == ("INCONCLUSIVE", "TECHNICAL",
                                                                      I.UNDETERMINABLE, None)
    assert "procedencia" in out.reasons[0] and out.trades == 0 and not out.retry_allowed


@pytest.fixture
def oos(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    return res, reg, loader, loader.load_final(ggrant(part="oos"), "oos")


def test_baseline_untouched_genuine_data_passes_provenance(oos):
    res, reg, loader, data = oos
    out = evaluate(res, reg, loader, data)
    assert out.eligibility == I.ELIGIBLE and out.metrics is not None


def test_bypass_prefiltered_or_synthetic_h4_series_is_refused(oos):
    """Reproduce el defecto B7.3: antes se aceptaba cualquier `FinalEvaluationData` (p. ej. solo H4, o velas
    inventadas con el `context` genuino) y el consumo/ET-7 se atribuían a datos que no eran los de la snapshot."""
    res, reg, loader, data = oos
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, data=w4(data))))          # recorte H4
    fake = w4(data).copy()
    fake["close"] = fake["close"] * 1.5
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, data=fake)))              # velas inventadas
    assert len(consumed(reg)) == 1                                                          # consumo intacto


@pytest.mark.parametrize("mutate", ["tamper_one_candle", "drop_one_row", "append_row", "reorder_ok"])
def test_bypass_partition_mutations(oos, mutate):
    res, reg, loader, data = oos
    d = data.data.copy()
    if mutate == "tamper_one_candle":
        d.loc[d.index[10], "high"] += 0.01
    elif mutate == "drop_one_row":
        d = d.drop(d.index[10]).reset_index(drop=True)
    elif mutate == "append_row":
        d = pd.concat([d, d.iloc[[-1]].assign(open_time=int(d["open_time"].max()) + 1)], ignore_index=True)
    else:                                       # el orden no es contenido: el digest canónico lo ignora
        d = d.sample(frac=1, random_state=1).reset_index(drop=True)
    out = evaluate(res, reg, loader, dataclasses.replace(data, data=d))
    if mutate == "reorder_ok":
        assert out.eligibility == I.ELIGIBLE and out.metrics is not None
    else:
        _refuses(out)


def test_bypass_context_substitution_and_partition_relabel_are_refused(oos):
    res, reg, loader, data = oos
    c = data.context.copy()
    c.loc[c.index[5], "close"] += 1.0
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, context=c)))             # contexto alterado
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, partition="lockbox")))   # etiqueta cambiada
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, context=data.context.iloc[:0])))


def test_forged_manifest_digest_matching_substituted_data_is_still_denied_by_et7(oos):
    """Quien sustituye datos Y reescribe el digest del manifiesto pasa la procedencia, pero ET-7 compara el
    manifiesto con el de la snapshot consumida (manifest_dir) y lo deniega: sin métricas."""
    res, reg, loader, data = oos
    import copy
    from swingpilot.research import snapshot as S
    d = data.data.copy()
    d.loc[d.index[10], "close"] += 1.0
    m = copy.deepcopy(res.manifest)
    m["files"]["oos"]["canonical_digest"] = S.canonical_content_digest(d)
    k = ctx(reg, loader)
    out = W.evaluate_window(dataclasses.replace(data, data=d), Logic(), MODEL, reg, loader.prereg_store, EID,
                            manifest=m, **k)
    assert out.metrics is None and out.verdict == "INCONCLUSIVE" and out.eligibility != I.ELIGIBLE


def _build_lockbox(tmp_path, reg, loader):
    import test_cr023_b5_evaluation_snapshot as B5
    cl, _ = B5._client(B5.LB_END + 10**9)
    lres = E.build_evaluation_snapshot(cl, "SNAP-0902", loader.data_dir.parent, loader.manifest_dir,
                                       registry=reg, store=loader.prereg_store, experiment_id=EID,
                                       window_id=f"{EID}/LOCKBOX", confirm=True)
    return lres, _loader(lres, tmp_path, reg)


def test_genuine_oos_to_lockbox_end_to_end(tmp_path, gdev):
    """OOS favorable → LOCKBOX con grant genuina, `load_final`, consumo real, ET-7 real, conciliación de pruebas
    real y velas selladas. El LOCKBOX no existe como snapshot hasta que el OOS está consumido (ET-4), y solo se
    carga tras el veredicto OOS favorable. Cada ventana verifica su propia procedencia."""
    res, reg, loader = ready(tmp_path, gdev, "oos")
    sha = PR._preregistered_sha(reg, EID)
    dec = reg.decisions_dir / "DEC-999_eval.md"
    dec.write_text(dec.read_text() + "AUTORIZA: EXP-0900 lockbox SNAP-0902\n"
                   f"AUTORIZA: ATESTACION {EID}/LOCKBOX SNAP-0902 SHA256={sha} "
                   "V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA\n")
    odata = loader.load_final(ggrant(part="oos"), "oos")
    oos, issued = W.evaluate_window_issued(odata, Logic(), MODEL, reg, loader.prereg_store, EID,   # FIX-D: una sola evaluación
                                           manifest=res.manifest, **ctx(reg, loader))
    assert oos.verdict == W.FAVORABLE and oos.eligibility == I.ELIGIBLE and oos.trades >= 30
    assert oos.metrics["trials_count"] is not None and oos.metrics["trials_accounting"] is not None
    assert [r["partition"] for r in consumed(reg)] == ["oos"]               # LOCKBOX aún no existe/consumido
    # CR-024 B.7: el LOCKBOX exige el OOS favorable autoritativo persistido (no el veredicto en memoria)
    from swingpilot.research import result_store as RST
    reg.persist_window_result(RST.for_registry(reg), issued, manifest_dir=loader.manifest_dir, actor="propietario")

    lres, lloader = _build_lockbox(tmp_path, reg, loader)
    ldata = lloader.load_final(grant(part="lockbox", sid="SNAP-0902", ref=REF), "lockbox")
    parts = sorted(r["partition"] for r in reg.consumed_partitions())
    assert parts == ["lockbox", "oos"]                                      # un consumo por ventana, sin más
    k = ctx(reg, lloader)
    lock = W.evaluate_window(ldata, Logic(), MODEL, reg, lloader.prereg_store, EID, manifest=lres.manifest, **k)
    assert lock.partition == "lockbox" and lock.eligibility == I.ELIGIBLE and lock.metrics is not None
    assert lock.verdict in ("REJECTED", W.FAVORABLE) and lock.verdict != "APPROVED"
    assert lock.metrics["window"] == "lockbox" and lock.trades >= 30
    assert lock.metrics["trials_count"] == oos.metrics["trials_count"]      # conciliación coherente entre ventanas
    # cruce: datos del LOCKBOX con el manifiesto del OOS (y al revés) → procedencia rechazada
    _refuses(W.evaluate_window(ldata, Logic(), MODEL, reg, lloader.prereg_store, EID, manifest=res.manifest, **k))
    _refuses(W.evaluate_window(odata, Logic(), MODEL, reg, lloader.prereg_store, EID, manifest=lres.manifest, **k))
    assert sorted(r["partition"] for r in reg.consumed_partitions()) == ["lockbox", "oos"]


# ---- B7.4d: evidencia de procedencia emitida por el cargador (precedente ConsumptionCheck) ----------------------
from swingpilot.research import partitions as P  # noqa: E402


def test_b74d_loader_issues_immutable_evidence_bound_to_grant_window_consumption_and_digests(oos):
    res, reg, loader, data = oos
    ev = data.provenance
    assert type(ev) is P.FinalWindowProvenance
    assert ev.grant[:3] == (EID, "oos", res.manifest["snapshot_id"]) and ev.window_id == res.manifest["window_id"]
    assert set(__import__("json").loads(ev.digests)) == {"context", "oos"}
    assert __import__("json").loads(ev.consumption) in reg.consumed_partitions()     # registro: forma intacta
    with pytest.raises(AttributeError):
        ev.window_id = "otra"
    with pytest.raises(AttributeError):
        del ev.digests


def test_b74d_bypass_missing_or_forged_evidence_is_refused(oos):
    res, reg, loader, data = oos
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, provenance=None)))
    with pytest.raises(P.PartitionAccessError):                  # no se puede construir fuera del cargador
        P.FinalWindowProvenance(object(), data.provenance.grant, data.provenance.window_id, {}, {})
    forged = type("X", (), {k: getattr(data.provenance, k) for k in data.provenance.__slots__})()
    _refuses(evaluate(res, reg, loader, dataclasses.replace(data, provenance=forged)))    # imitación por duck typing
    # el FinalEvaluationData construido a mano (sin cargador) tampoco pasa
    _refuses(evaluate(res, reg, loader, P.FinalEvaluationData("oos", data.data, data.context)))
    assert len(consumed(reg)) == 1


def test_b74d_bypass_evidence_from_another_window_or_unrecorded_consumption_is_refused(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    data = loader.load_final(ggrant(part="oos"), "oos")
    ev = data.provenance
    new = lambda **o: P.FinalWindowProvenance(P._PROVENANCE_KEY, o.get("grant", ev.grant),   # noqa: E731
                                              o.get("window_id", ev.window_id),
                                              o.get("consumption", __import__("json").loads(ev.consumption)),
                                              o.get("digests", __import__("json").loads(ev.digests)))
    rec = __import__("json").loads(ev.consumption)
    for bad in (new(window_id=f"{EID}/LOCKBOX"),                                    # otra ventana
                new(grant=(ev.grant[0], "lockbox") + ev.grant[2:]),                 # otra partición
                new(grant=ev.grant[:2] + ("SNAP-0999",) + ev.grant[3:]),            # otra snapshot
                new(digests={**__import__("json").loads(ev.digests), "oos": "0" * 64}),   # otro contenido
                new(consumption={**rec, "experiment_id": "EXP-0901"}),              # consumo de otro experimento
                new(consumption={**rec, "decision_ref": "DEC-000"})):               # consumo no registrado
        _refuses(evaluate(res, reg, loader, dataclasses.replace(data, provenance=bad)))
    assert len(consumed(reg)) == 1


def test_b74d_genuine_orchestration_resolves_lockbox_lazily_after_favorable_oos(tmp_path, gdev):
    res, reg, loader = ready(tmp_path, gdev, "oos")
    sha = PR._preregistered_sha(reg, EID)
    dec = reg.decisions_dir / "DEC-999_eval.md"
    dec.write_text(dec.read_text() + "AUTORIZA: EXP-0900 lockbox SNAP-0902\n"
                   f"AUTORIZA: ATESTACION {EID}/LOCKBOX SNAP-0902 SHA256={sha} "
                   "V1=CONFIRMADA V6=CONFIRMADA V7=CONFIRMADA\n")
    calls = []

    def resolve():
        calls.append("resolve")
        assert [r["partition"] for r in consumed(reg)] == ["oos"]            # el LOCKBOX no existía ni se consumió
        lres, lloader = _build_lockbox(tmp_path, reg, loader)
        return lres.manifest, lambda: lloader.load_final(grant(part="lockbox", sid="SNAP-0902", ref=REF), "lockbox")
    k = ctx(reg, loader)
    out = W.evaluate_final_windows(lambda: loader.load_final(ggrant(part="oos"), "oos"), resolve, Logic(), MODEL,
                                   reg, loader.prereg_store, EID, oos_manifest=res.manifest, **k)
    assert calls == ["resolve"] and out.lockbox_progression == "ATTEMPTED"
    assert out.oos.verdict == W.FAVORABLE and out.lockbox.eligibility == I.ELIGIBLE and out.lockbox.metrics
    assert out.lockbox.verdict != "APPROVED" and sorted(r["partition"] for r in reg.consumed_partitions()) == [
        "lockbox", "oos"]


def test_b74d_unfavorable_oos_never_resolves_lockbox_manifest_or_loader(tmp_path, gdev, favorable_tape):
    favorable_tape["mode"] = "calm"
    res, reg, loader = ready(tmp_path, gdev, "oos")
    out = W.evaluate_final_windows(
        lambda: loader.load_final(ggrant(part="oos"), "oos"), lambda: pytest.fail("LOCKBOX resuelto"), Logic(),
        MODEL, reg, loader.prereg_store, EID, oos_manifest=res.manifest, **ctx(reg, loader))
    assert out.lockbox is None and out.lockbox_progression == "NOT_ATTEMPTED"
    assert [r["partition"] for r in consumed(reg)] == ["oos"]
