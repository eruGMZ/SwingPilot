"""CR-023 B5: ET-4, snapshot de evaluación, contexto sellado, digests, continuidad del LOCKBOX y fuente
autoritativa de ventanas reservadas (TC-ML-019, TC-ML-025 ET-4, TC-ML-027, C.4.2.3, C.7.4). Sintético; Binance simulado."""
from __future__ import annotations

import os
import shutil
import stat
import sys
import urllib.parse
from datetime import datetime, timezone

from consumption_helpers import ok_consumption_check  # noqa: E402
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_cr023_b3_preregistration import _confirmatory_in, dev_snap, env  # noqa: E402,F401
from test_cr023_b4_independence import EID, _lines  # noqa: E402
from swingpilot.market_data import BinancePublicClient, interval_ms  # noqa: E402
from swingpilot.research import evaluation_snapshot as E  # noqa: E402
from swingpilot.research import independence as I  # noqa: E402
from swingpilot.research import snapshot as S  # noqa: E402
from swingpilot.research.snapshot import SnapshotError  # noqa: E402

START = int(datetime(2017, 8, 17, tzinfo=timezone.utc).timestamp() * 1000)


def _ms(y, m, d=1):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


class Fake:
    """Binance simulado: velas deterministas; `tweak` altera el precio en [lo, hi) (discrepancia de contexto)."""
    def __init__(self, server, tweak=None):
        self.server, self.tweak, self.calls = server, tweak, 0

    def __call__(self, url):
        self.calls += 1
        u = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/api/v3/time":
            return {"serverTime": self.server}
        step = interval_ms(q["interval"])
        t = max((int(q["startTime"]) + step - 1) // step * step, START)
        end, rows = int(q.get("endTime", self.server)), []
        while t <= min(end, self.server) and len(rows) < int(q["limit"]):
            p = 1000 + (t // step) % 50 + (7 if self.tweak and self.tweak[0] <= t < self.tweak[1] else 0)
            rows.append([t, str(p), str(p + 5), str(p - 5), str(p + 1), "3.5", t + step - 1, "0", 1, "0", "0", "0"])
            t += step
        return rows


def _client(server, **kw):
    f = Fake(server, **kw)
    return BinancePublicClient(transport=f), f


OOS_END, LB_END = _ms(2028, 3), _ms(2029, 3)


@pytest.fixture
def ready(env):
    env._fz = _confirmatory_in(env, "PREREGISTERED")
    _lines(env)
    yield env
    keep = env.res.manifest["snapshot_id"]                                  # la snapshot de desarrollo es de módulo
    for p in env.res.manifest_path.parent.glob("*"):
        if p.name != f"{keep}.json":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    for d in env.data_root.iterdir():
        if d.name != keep:
            S._remove_tree(d)


def _build(env, sid, wid, client, **kw):
    kw.setdefault("confirm", True)
    return E.build_evaluation_snapshot(client, sid, env.data_root, env.res.manifest_path.parent, registry=env.reg,
                                       store=env.store, experiment_id=EID, window_id=wid, **kw)


def _no_trace(env, sid):
    assert not (env.data_root / sid).exists() and not (env.res.manifest_path.parent / f"{sid}.json").exists()
    assert not [p for p in env.data_root.iterdir() if p.name.startswith(".tmp-")]


@pytest.fixture(scope="module")
def _oos_cache():
    return {}


def _dec(env, *lines):
    (env.reg.decisions_dir / "DEC-902_b5.md").write_text("\n".join(lines) + "\n")


def _consume_oos(env, sid, last):
    from test_cr023_b3_preregistration import ACTOR, _oos_ev
    if env.reg.state(EID) == "PREREGISTERED":                               # registro coherente (QA3R2-07)
        env.to_validation(EID)
        env._fz.begin_evaluation("A", registry=env.reg)
        env.reg.transition(EID, "OOS_EVALUATION", actor="propietario", evidence=_oos_ev(EID))
    env.reg.claim_partition(snapshot_id=sid, partition="oos", experiment_id=EID, snapshot_last_open_time=last,
                            decision_ref="DEC-900_ok.md", consumption_check=ok_consumption_check())


def test_et4_requires_confirm_and_checks_before_download(ready):
    cl, f = _client(OOS_END + 10**9)
    with pytest.raises(SnapshotError, match="--confirm"):
        _build(ready, "SNAP-TESTE1", f"{EID}/OOS", cl, confirm=False)
    (ready.reg.decisions_dir / "DEC-901_frontera.md").unlink()              # V1 ausente → ET-4 bloqueada
    with pytest.raises(SnapshotError, match="ET-4 bloqueada"):
        _build(ready, "SNAP-TESTE1", f"{EID}/OOS", cl)
    assert f.calls == 0
    _no_trace(ready, "SNAP-TESTE1")


def test_et4_rejects_foreign_window_and_open_window_with_rollback(ready):
    cl, f = _client(OOS_END + 10**9)
    with pytest.raises(SnapshotError, match="no es una ventana"):
        _build(ready, "SNAP-TESTE1", "EXP-0999/OOS", cl)
    cl, f = _client(_ms(2027, 9))                                           # ventana aún no cerrada
    with pytest.raises(SnapshotError, match="no ha cerrado"):
        _build(ready, "SNAP-TESTE1", f"{EID}/OOS", cl)
    _no_trace(ready, "SNAP-TESTE1")


def test_oos_snapshot_sealed_with_digests_and_v5(ready):
    cl, _ = _client(OOS_END + 10**9)
    res = _build(ready, "SNAP-TESTE1", f"{EID}/OOS", cl)
    m = res.manifest
    assert m["kind"] == "evaluation" and m["window_id"] == f"{EID}/OOS" and m["lockbox_continuity"] is None
    assert set(m["files"]) == {"context", "oos"} and m["context_start_ms"] == m["d_dev_ms"]
    for name in ("context", "oos"):
        assert set(m["files"][name]["canonical_digest"]) == {"1d", "4h", "1h"}
        assert stat.S_IMODE(os.stat(res.data_dir / f"{name}.parquet").st_mode) == 0
    assert m["window"]["end_exclusive_ms"] == OOS_END and m["files"]["oos"]["per_interval"]["1d"]["rows"] == 366
    assert S.load_manifest(res.manifest_path) == m
    assert I.stage_checks(ready.reg, ready.store, EID, "ET-6", manifest=m)["V5"] == (I.OK, "")
    assert S.verify_snapshot(res.manifest_path, ready.data_root) == {}      # sellado efectivo, sin leer
    with pytest.raises(SnapshotError, match="ya existe"):
        _build(ready, "SNAP-TESTE1", f"{EID}/OOS", cl)                      # no se reescribe
    _consume_oos(ready, "SNAP-TESTE1", m["range"]["last_open_time_ms"])
    with pytest.raises(SnapshotError, match="V4-pre|ET-4 bloqueada"):       # ventana consumida: no se reconstruye
        _build(ready, "SNAP-TESTE2", f"{EID}/OOS", cl)
    _no_trace(ready, "SNAP-TESTE2")


def test_lockbox_requires_consumed_oos_and_continuity(ready, monkeypatch):
    cl, _ = _client(LB_END + 10**9)
    with pytest.raises(SnapshotError, match="ET-4 bloqueada"):              # sin OOS consumida (V4-pre)
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    oos = _build(ready, "SNAP-TESTO1", f"{EID}/OOS", cl)
    _consume_oos(ready, "SNAP-TESTO1", oos.manifest["range"]["last_open_time_ms"])
    import pyarrow.parquet as pq
    monkeypatch.setattr(pq, "read_table", lambda *a, **k: pytest.fail("oos.parquet no se abre"))
    bad, _ = _client(LB_END + 10**9, tweak=(_ms(2027, 6), _ms(2027, 6, 3)))   # discrepancia en [B, B+L_oos)
    with pytest.raises(SnapshotError, match="continuidad C.6.5.*oos"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", bad)
    _document_all(ready)
    bad, _ = _client(LB_END + 10**9, tweak=(_ms(2024, 1), _ms(2024, 1, 3)))   # discrepancia en [D_dev, B)
    with pytest.raises(SnapshotError, match="continuidad C.6.5.*context"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", bad)
    _no_trace(ready, "SNAP-TESTL1")
    _document_all(ready)
    lb = _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    m = lb.manifest
    assert m["lockbox_continuity"] == {"oos_snapshot_id": "SNAP-TESTO1", "verified": True}
    assert m["window"]["start_ms"] == OOS_END and m["window"]["end_exclusive_ms"] == LB_END
    assert m["files"]["context"]["rows"] == oos.manifest["files"]["context"]["rows"] + oos.manifest["files"]["oos"]["rows"]
    assert not (oos.data_dir / "oos.parquet").stat().st_mode & 0o777


def test_lockbox_needs_single_valid_oos_manifest(ready):
    cl, _ = _client(LB_END + 10**9)
    oos = _build(ready, "SNAP-TESTO1", f"{EID}/OOS", cl)
    _consume_oos(ready, "SNAP-TESTO1", 1)
    oos.manifest_path.rename(oos.manifest_path.with_suffix(".moved"))       # manifiesto de la OOS ausente
    with pytest.raises(SnapshotError, match="exactamente un manifiesto|ET-4 bloqueada"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    _no_trace(ready, "SNAP-TESTL1")


def test_authoritative_reserved_windows_and_build_snapshot(ready):
    src = E.reserved_windows_source(ready.reg, ready.store)
    ws = {w.window_id: w for w in src()}
    assert set(ws) == {f"{EID}/OOS", f"{EID}/LOCKBOX"} and ws[f"{EID}/OOS"].start_ms == _ms(2027, 3)
    with pytest.raises(SnapshotError, match="alcanza la ventana"):          # C.7.4/C.6.5: desarrollo no toca la ventana
        S.check_reserved_windows({"1d": ws[f"{EID}/OOS"].start_ms}, src())
    cl, _ = _client(OOS_END + 10**9)
    oos = _build(ready, "SNAP-TESTO1", f"{EID}/OOS", cl)
    _consume_oos(ready, "SNAP-TESTO1", 1)
    assert [w.window_id for w in src()] == [f"{EID}/LOCKBOX"]               # la OOS consumida deja de estar activa
    res = S.build_snapshot(cl, "SNAP-TESTD2", ready.data_root, ready.res.manifest_path.parent, d_dev="2018-01-01",
                           reserved_windows=[], reserved_windows_source=src)
    assert f"{EID}/LOCKBOX" in res.manifest["reserved_windows_checked"]
    with pytest.raises(SnapshotError, match="no verificable"):
        S.build_snapshot(cl, "SNAP-TESTD3", ready.data_root, ready.res.manifest_path.parent, d_dev="2018-01-01",
                         reserved_windows=[], reserved_windows_source=lambda: 1 / 0)


def test_authoritative_source_fails_closed_on_unreadable_store(ready):
    for f in ready.store.root.rglob("*.json"):
        f.unlink()
    with pytest.raises(SnapshotError, match="no verificable"):
        E.reserved_windows_source(ready.reg, ready.store)()


def test_b5_01_build_snapshot_without_authoritative_source_fails_closed(ready):
    cl, f = _client(OOS_END + 10**9)
    with pytest.raises(SnapshotError, match="falta reserved_windows_source"):
        S.build_snapshot(cl, "SNAP-TESTD4", ready.data_root, ready.res.manifest_path.parent, d_dev="2018-01-01",
                         reserved_windows=[])
    assert f.calls == 0


def test_b5_01_cli_provider_uses_real_authority_read_only(ready, monkeypatch):
    from swingpilot.research import cli
    monkeypatch.setattr(cli, "REGISTRY_PATH", ready.reg.path)
    monkeypatch.setattr("swingpilot.research.prereg_store.DEFAULT_ROOT", ready.store.root)
    before = ready.records_bytes()
    assert {w.window_id for w in cli.reserved_windows_provider()} == {f"{EID}/OOS", f"{EID}/LOCKBOX"}
    assert ready.records_bytes() == before


# --- disposiciones del propietario (B5-02, B5-03A, B5-03B) ---------------------------------------------

def _document_all(env):
    _dec(env, *[f"AUTORIZA: REINTENTO {EID}/LOCKBOX EVIDENCIA={S.sha256_file(e)}"
                for e in E._discrepancies(env.res.manifest_path.parent, EID)])


def _setup_lockbox(env):
    cl, _ = _client(LB_END + 10**9)
    oos = _build(env, "SNAP-TESTO1", f"{EID}/OOS", cl)
    _consume_oos(env, "SNAP-TESTO1", oos.manifest["range"]["last_open_time_ms"])
    return cl


def test_b5_02_discrepancy_evidence_requires_documentation_before_retry(ready):
    cl = _setup_lockbox(ready)
    bad, _ = _client(LB_END + 10**9, tweak=(_ms(2027, 6), _ms(2027, 6, 3)))
    with pytest.raises(SnapshotError, match="evidencia"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", bad)
    _no_trace(ready, "SNAP-TESTL1")
    evs = E._discrepancies(ready.res.manifest_path.parent, EID)
    assert len(evs) == 1 and b"market" not in evs[0].read_bytes()
    with pytest.raises(SnapshotError, match="discrepancia sin documentar"):      # reintento sin documentar
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    kept = evs[0].read_bytes()
    _dec(ready, f"AUTORIZA: REINTENTO {EID}/LOCKBOX EVIDENCIA={S.sha256_file(evs[0])}")
    with pytest.raises(SnapshotError, match="evidencia"):                         # persiste: sin tope de reintentos
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", bad)
    assert evs[0].read_bytes() == kept and len(E._discrepancies(ready.res.manifest_path.parent, EID)) == 2
    _dec(ready, f"AUTORIZA: REINTENTO {EID}/LOCKBOX EVIDENCIA={S.sha256_file(evs[0])}")   # la 2.ª sin documentar
    with pytest.raises(SnapshotError, match="discrepancia sin documentar"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    _dec(ready, *[f"AUTORIZA: REINTENTO {EID}/LOCKBOX EVIDENCIA={S.sha256_file(e)}"
                  for e in E._discrepancies(ready.res.manifest_path.parent, EID)])
    assert _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl).manifest["lockbox_continuity"]["verified"]


def test_b5_02_owner_inconclusive_disposition_blocks_permanently(ready):
    cl = _setup_lockbox(ready)
    _dec(ready, f"AUTORIZA: DISPOSICION {EID}/LOCKBOX INCONCLUSIVE")
    with pytest.raises(SnapshotError, match="INCONCLUSIVE"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    _dec(ready, f"AUTORIZA: DISPOSICION {EID}/LOCKBOX INCONCLUSIVE ")             # gramática estricta
    with pytest.raises(SnapshotError, match="ET-4 bloqueada"):
        _build(ready, "SNAP-TESTL1", f"{EID}/LOCKBOX", cl)
    _no_trace(ready, "SNAP-TESTL1")


def test_b5_03b_release_is_strict_frees_window_and_is_permanent(ready):
    sha = I.PR._preregistered_sha(ready.reg, EID) if hasattr(I, "PR") else __import__(
        "swingpilot.research.preregistration", fromlist=["x"])._preregistered_sha(ready.reg, EID)
    src = E.reserved_windows_source(ready.reg, ready.store)
    cl, f = _client(OOS_END + 10**9)
    for bad in (f"AUTORIZA: LIBERACION {EID}/OOS SHA256={sha.upper()}", f"AUTORIZA: LIBERACION {EID}/OOS SHA256={sha} ",
                f"AUTORIZA: LIBERACION {EID}/OOS SHA256={'0' * 64}"):
        _dec(ready, bad)
        with pytest.raises(SnapshotError, match="no verificable"):                 # Fail-Closed
            src()
    _dec(ready, f"AUTORIZA: LIBERACION {EID}/OOS SHA256={sha}")
    assert [w.window_id for w in src()] == [f"{EID}/LOCKBOX"]                       # dato de desarrollo (C.7.3)
    with pytest.raises(SnapshotError, match="liberada"):                            # nunca vuelve a evaluarse
        _build(ready, "SNAP-TESTO1", f"{EID}/OOS", cl)
    assert f.calls == 0
    assert I.eligibility(ready.reg, ready.store, EID, "ET-5")["result"] != I.ELIGIBLE


def test_b5_03a_cli_build_evaluation(ready, monkeypatch, capsys):
    from swingpilot.research import cli
    monkeypatch.setattr(cli, "REGISTRY_PATH", ready.reg.path)
    monkeypatch.setattr("swingpilot.research.prereg_store.DEFAULT_ROOT", ready.store.root)
    monkeypatch.setattr(cli, "DATA_ROOT", ready.data_root)
    monkeypatch.setattr(cli, "MANIFEST_DIR", ready.res.manifest_path.parent)
    monkeypatch.setattr("swingpilot.research.experiments.REPO_DECISIONS_DIR", ready.reg.decisions_dir)
    cl, f = _client(OOS_END + 10**9)
    monkeypatch.setattr(cli, "BinancePublicClient", lambda *a, **k: cl)
    base = ["build-evaluation", "--id", "SNAP-0007", "--experiment", EID, "--window", "OOS"]
    assert cli.main(base) == 2 and f.calls == 0                                     # --confirm obligatorio
    assert cli.main(base + ["--confirm"]) == 0
    assert "SNAP-0007" in capsys.readouterr().out
    assert cli.main(base + ["--confirm"]) == 1                                      # no se reescribe


def test_injected_only_is_test_only(ready, monkeypatch):
    cl, f = _client(OOS_END + 10**9)
    monkeypatch.delitem(sys.modules, "pytest")
    with pytest.raises(SnapshotError, match="solo es válido en pruebas"):
        S.build_snapshot(cl, "SNAP-TESTD5", ready.data_root, ready.res.manifest_path.parent, d_dev="2018-01-01",
                         reserved_windows=[], injected_only=True)
    assert f.calls == 0
