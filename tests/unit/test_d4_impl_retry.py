"""D4-IMPL (DEC-026): capa de reintentos HTTP opt-in, diagnóstico aislado y D_dev aprobado.

Solo transportes sintéticos y fixtures temporales: sin red, sin credenciales, sin descargas reales.
"""
import json
import socket
import ssl
import sys
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_snapshot import D_DEV as T_DEV, SmallBinance  # noqa: E402

from swingpilot.market_data import BinancePublicClient  # noqa: E402
from swingpilot.market_data import binance_public as BP  # noqa: E402
from swingpilot.research import d4_build as D4  # noqa: E402
from swingpilot.research.snapshot import SnapshotError, load_manifest, parse_d_dev, verify_snapshot  # noqa: E402

FIXED_NOW = lambda: datetime(2018, 8, 1, tzinfo=timezone.utc)  # noqa: E731


def http(code):
    return urllib.error.HTTPError("https://secret.example/path?apikey=XYZ", code, "msg", {"X-Hdr": "v"}, None)


class Scripted:
    """Transporte sintético: delega en SmallBinance y falla según un guion {n.º de petición (1..): excepción}."""
    def __init__(self, script=None, only_stage=None):
        self.inner, self.script, self.only_stage = SmallBinance(), dict(script or {}), only_stage
        self.calls, self.counted = 0, 0
        self.urls = []

    def __call__(self, url):
        self.calls += 1
        self.urls.append(url)
        if self.only_stage is None or D4.stage_from_url(url) == self.only_stage:
            self.counted += 1
            exc = self.script.get(self.counted)
            if exc is not None:
                raise exc
        return self.inner(url)


def run(tmp, inner, sleeps=None, sid="SNAP-TEST", d_dev=T_DEV, source=lambda: []):
    sleeps = [] if sleeps is None else sleeps
    code = D4.run_d4_build(snapshot_id=sid, data_root=tmp / "var" / "snapshots", manifest_dir=tmp / "research" / "snapshots",
                           diagnostics_dir=tmp / "var" / "diagnostics" / "d4", inner_transport=inner,
                           reserved_windows_source=source, d_dev=d_dev, sleep=sleeps.append, run_id="D4-RUN-TEST",
                           now=FIXED_NOW)
    return code, sleeps


def diag(tmp):
    p = tmp / "var" / "diagnostics" / "d4" / "D4-RUN-TEST.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


# --- política de reintentos -------------------------------------------------------------------------------------
def retry(inner, sleeps):
    return D4.D4RetryTransport(inner, sleep=sleeps.append)


def counting(excs):
    state = {"n": 0}

    def fn(url):
        state["n"] += 1
        if state["n"] <= len(excs):
            raise excs[state["n"] - 1]
        return {"ok": True}
    return fn, state


URL = "https://data-api.binance.vision/api/v3/time"


@pytest.mark.parametrize("exc", [http(500), http(502), http(503), http(504), urllib.error.URLError("net"),
                                 socket.timeout("t"), TimeoutError("t"), ConnectionResetError("r")])
def test_transient_recovers_with_exact_backoff(exc):
    fn, st = counting([exc, exc])
    sleeps = []
    assert retry(fn, sleeps)(URL) == {"ok": True}
    assert st["n"] == 3 and sleeps == [1.0, 2.0]


def test_single_transient_failure_waits_one_second():
    fn, st = counting([http(503)])
    sleeps = []
    assert retry(fn, sleeps)(URL) == {"ok": True}
    assert st["n"] == 2 and sleeps == [1.0]


def test_exhaustion_is_three_attempts_two_sleeps():
    fn, st = counting([http(503)] * 10)
    sleeps = []
    with pytest.raises(D4.D4TransportError) as ei:
        retry(fn, sleeps)(URL)
    assert st["n"] == 3 and sleeps == [1.0, 2.0]
    assert (ei.value.classification, ei.value.http_status, ei.value.attempts) == (D4.RETRIES_EXHAUSTED, 503, 3)
    assert "http" not in str(ei.value).lower() and "secret" not in str(ei.value).lower()


@pytest.mark.parametrize("exc,cls", [
    (http(429), D4.RATE_LIMITED), (http(418), D4.RATE_LIMITED),
    (http(401), D4.PERMISSION), (http(403), D4.PERMISSION), (http(451), D4.PERMISSION),
    (http(400), D4.PERMANENT_HTTP), (http(404), D4.PERMANENT_HTTP),
    (json.JSONDecodeError("bad", "x", 0), D4.CORRUPTION), (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"), D4.CORRUPTION),
    (urllib.error.URLError(ssl.SSLError("tls")), D4.TLS_ERROR),
    (ValueError("integridad"), D4.UNCLASSIFIED), (BP.PublicApiError("límite"), D4.UNCLASSIFIED),
])
def test_never_retried(exc, cls):
    fn, st = counting([exc] * 5)
    sleeps = []
    with pytest.raises(D4.D4TransportError) as ei:
        retry(fn, sleeps)(URL)
    assert st["n"] == 1 and sleeps == [] and ei.value.classification == cls


def test_transient_after_permanent_not_masked_and_ok_first_try_no_sleep():
    fn, st = counting([])
    sleeps = []
    assert retry(fn, sleeps)(URL) == {"ok": True} and st["n"] == 1 and sleeps == []


# --- construcción completa ---------------------------------------------------------------------------------------
def test_d_dev_approved_value():
    assert D4.D_DEV == "2026-11-01"
    assert parse_d_dev(D4.D_DEV) == int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)


def test_transient_recovery_equals_clean_build(tmp_path):
    clean, flaky = tmp_path / "clean", tmp_path / "flaky"
    assert run(clean, Scripted())[0] == 0
    sc = Scripted({1: http(503), 5: urllib.error.URLError("net")})
    code, sleeps = run(flaky, sc)
    assert code == 0 and sleeps == [1.0, 1.0]
    m1, m2 = (load_manifest(t / "research" / "snapshots" / "SNAP-TEST.json") for t in (clean, flaky))
    assert m1["files"]["train_val"]["canonical_digest"] == m2["files"]["train_val"]["canonical_digest"]
    assert m1["files"]["train_val"]["rows"] == m2["files"]["train_val"]["rows"]
    verify_snapshot(flaky / "research" / "snapshots" / "SNAP-TEST.json", flaky / "var" / "snapshots")
    events = [(r["event"], r["stage"], r["attempt"], r["classification"], r["http_status"]) for r in diag(flaky)]
    assert ("ATTEMPT_FAILED", "server_time", 1, D4.TRANSIENT_HTTP_5XX, 503) in events
    assert diag(flaky)[-1]["event"] == "BUILD_OK" and diag(flaky)[-1]["exit_code"] == 0


def test_pagination_recovery_mid_pages(tmp_path):
    sc = Scripted({3: http(502), 4: http(502)}, only_stage="klines:1h")    # 1h pagina en ≥ 8 páginas
    code, sleeps = run(tmp_path, sc)
    assert code == 0 and sleeps == [1.0, 2.0]
    assert sum(1 for r in diag(tmp_path) if r["stage"] == "klines:1h" and r["event"] == "ATTEMPT_FAILED") == 2
    clean = tmp_path / "c"
    run(clean, Scripted())
    a = load_manifest(tmp_path / "research" / "snapshots" / "SNAP-TEST.json")["files"]["train_val"]["canonical_digest"]
    b = load_manifest(clean / "research" / "snapshots" / "SNAP-TEST.json")["files"]["train_val"]["canonical_digest"]
    assert a == b


def test_exhaustion_cancels_whole_build_without_restart_and_rolls_back(tmp_path):
    sc = Scripted({n: http(503) for n in range(1, 50)}, only_stage="klines:4h")
    code, sleeps = run(tmp_path, sc)
    assert code == 1 and sleeps == [1.0, 2.0]
    assert sum(1 for u in sc.urls if D4.stage_from_url(u) == "server_time") == 1      # sin reinicio completo
    assert sum(1 for u in sc.urls if D4.stage_from_url(u) == "klines:4h") == 3
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()
    snaps = tmp_path / "var" / "snapshots"
    assert not snaps.exists() or list(snaps.iterdir()) == []                         # rollback sin residuos
    last = diag(tmp_path)[-1]
    assert (last["event"], last["classification"], last["http_status"], last["exit_code"], last["stage"]) == \
           ("BUILD_FAILED", D4.RETRIES_EXHAUSTED, 503, 1, "download")


@pytest.mark.parametrize("code_", [429, 418])
def test_rate_limit_rejected_without_retry(tmp_path, code_):
    sc = Scripted({2: http(code_)})
    code, sleeps = run(tmp_path, sc)
    assert code == 1 and sleeps == [] and sc.calls == 2
    last = diag(tmp_path)[-1]
    assert last["classification"] == D4.RATE_LIMITED and last["http_status"] == code_


def test_permission_error_and_build_rejection_classified(tmp_path):
    code, sleeps = run(tmp_path, Scripted({1: http(403)}))
    assert code == 1 and sleeps == [] and diag(tmp_path)[-1]["classification"] == D4.PERMISSION
    other = tmp_path / "o"
    code, _ = run(other, Scripted(), d_dev="2999-01-01")                  # fecha posterior a la hora del servidor
    assert code == 1
    last = diag(other)[-1]
    assert (last["classification"], last["stage"], last["http_status"]) == (D4.BUILD_REJECTED, "build", None)


def test_reserved_window_failure_rolls_back(tmp_path):
    from swingpilot.research.snapshot import ReservedWindow
    from test_snapshot import D_DEV_MS
    code, _ = run(tmp_path, Scripted(), source=lambda: [ReservedWindow("EXP-0001/OOS", D_DEV_MS - 86_400_000, D_DEV_MS + 86_400_000)])
    assert code == 1 and not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()


# --- diagnóstico -------------------------------------------------------------------------------------------------
def test_diagnostics_fields_and_no_sensitive_content(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_ENV_SECRET", "ZZ-SECRET-VALUE-ZZ")
    run(tmp_path, Scripted({2: http(503), 3: http(429)}))
    raw = (tmp_path / "var" / "diagnostics" / "d4" / "D4-RUN-TEST.jsonl").read_text()
    rows = [json.loads(x) for x in raw.splitlines()]
    assert rows and all(tuple(r) == D4.DiagnosticsRecorder.FIELDS for r in rows)
    assert all(r["run_id"] == "D4-RUN-TEST" and r["snapshot_id"] == "SNAP-TEST" and r["d_dev"] == T_DEV for r in rows)
    assert all(r["timestamp_utc"].endswith("Z") and isinstance(r["elapsed_ms"], int) for r in rows)
    assert rows[-1]["exit_code"] == 1
    for banned in ("https", "http:", "secret.example", "apikey", "X-Hdr", "ZZ-SECRET-VALUE-ZZ", "SENTINEL_ENV_SECRET",
                   "serverTime", "data-api", "Authorization"):
        assert banned.lower() not in raw.lower(), banned


def test_diagnostics_isolated_from_snapshots_and_research(tmp_path):
    assert run(tmp_path, Scripted({1: http(503)}))[0] == 0
    snap_dir = tmp_path / "var" / "snapshots" / "SNAP-TEST"
    assert not any("diag" in p.name or p.suffix == ".jsonl" for p in snap_dir.rglob("*"))
    manifest = (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").read_text()
    assert "D4-RUN-TEST" not in manifest and "ATTEMPT_FAILED" not in manifest
    assert not list((tmp_path / "research").rglob("*.jsonl"))
    for root in (tmp_path / "var" / "snapshots", tmp_path / "research" / "snapshots", tmp_path / "research"):
        with pytest.raises(SnapshotError):
            D4.DiagnosticsRecorder(root / "d", "R", "SNAP-TEST", T_DEV, forbidden_roots=[root])


def test_diagnostics_write_failure_does_not_change_outcome(tmp_path):
    blocker = tmp_path / "var" / "diagnostics"
    blocker.parent.mkdir(parents=True)
    blocker.write_text("archivo, no directorio")
    assert run(tmp_path, Scripted())[0] == 0


# --- sin cambios en el comportamiento por defecto ----------------------------------------------------------------
def test_default_client_and_live_paths_unchanged(tmp_path):
    assert BinancePublicClient()._transport is BP._urllib_transport
    calls = []

    def failing(url):
        calls.append(url)
        raise http(503)
    with pytest.raises(BP.PublicApiError):
        BinancePublicClient(transport=failing).server_time_ms()
    assert len(calls) == 1                                   # sin reintentos fuera de D4
    for mod in ("swingpilot/market_data/binance_public.py", "swingpilot/research/snapshot.py",
                "swingpilot/research/evaluation_snapshot.py", "swingpilot/research/cli.py"):
        assert "d4_build" not in (Path(__file__).resolve().parents[2] / "src" / mod).read_text()
    live = [p for p in (Path(__file__).resolve().parents[2] / "src").rglob("*.py")
            if p.name != "d4_build.py" and "d4_build" in p.read_text()]
    assert live == []


# --- punto de entrada real (BLOQUEADO) ---------------------------------------------------------------------------
def test_main_refuses_without_confirmation_or_authorization(monkeypatch):
    monkeypatch.setattr(D4, "_urllib_transport", lambda *a, **k: pytest.fail("red prohibida"))
    assert D4.main(["--id", "SNAP-0001"]) == D4.EXIT_REFUSED
    assert D4.main(["--id", "SNAP-0001", "--confirm"]) == D4.EXIT_REFUSED
    assert D4.main(["--id", "SNAP-0001", "--confirm", "--authorization-ref", "  "]) == D4.EXIT_REFUSED
    assert "os.environ" not in Path(D4.__file__).read_text()
