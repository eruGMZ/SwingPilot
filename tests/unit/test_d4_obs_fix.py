"""D4-OBS-FIX: observabilidad de fallos de D4 (campos permitidos, resumen stderr saneado). Solo sintético, sin red."""
import json
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_d4_impl_retry import Scripted, diag, http, run  # noqa: E402
from test_snapshot import D_DEV_MS, SmallBinance  # noqa: E402

from swingpilot.research import d4_build as D4  # noqa: E402
from swingpilot.research import snapshot as S  # noqa: E402

SECRET = "ZZ-SECRET-ZZ"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("red prohibida"))


class Custom(SmallBinance):
    def __init__(self, time=None, klines=None, **kw):
        super().__init__(**kw)
        self.time, self.klines = time, klines

    def __call__(self, url):
        if "/time" in url and self.time is not None:
            return self.time
        if "/klines" in url and self.klines is not None:
            return self.klines(url)
        return super().__call__(url)


def last(tmp):
    return diag(tmp)[-1]


def check(tmp, capsys, stage, reason, error_type, root, interval=None, cls=D4.BUILD_REJECTED):
    row = last(tmp)
    assert (row["classification"], row["stage"], row["reason_code"], row["error_type"], row["root_error_type"],
            row["interval"], row["exit_code"]) == (cls, stage, reason, error_type, root, interval, 1)
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and err.startswith("D4 BUILD_FAILED run_id=D4-RUN-TEST")
    assert f"reason_code={reason}" in err and "exit_code=1" in err
    for banned in (SECRET, "https", "http:", "serverTime", "Traceback", "/api/"):
        assert banned not in err and banned not in json.dumps(row)


def test_invalid_server_time(tmp_path, capsys):
    assert run(tmp_path, Custom(time={"serverTime": SECRET}))[0] == 1
    check(tmp_path, capsys, "server_time", "INVALID_SERVER_TIME", "PublicApiError", "ValueError")


def test_unexpected_klines_response(tmp_path, capsys):
    assert run(tmp_path, Custom(klines=lambda u: {"msg": SECRET}))[0] == 1
    check(tmp_path, capsys, "download", "UNEXPECTED_KLINES_RESPONSE", "SnapshotError", "PublicApiError", "1d")


def test_candle_conversion_error(tmp_path, capsys):
    assert run(tmp_path, Custom(klines=lambda u: [[0, SECRET, "1", "1", "1", "1", 1]]))[0] == 1
    check(tmp_path, capsys, "download", "CANDLE_CONVERSION_ERROR", "SnapshotError", "ValueError", "1d")


def test_incomplete_download(tmp_path, capsys):
    assert run(tmp_path, Custom(truncate_1h_after=5))[0] == 1
    check(tmp_path, capsys, "download", "KLINES_RANGE_INVALID_OR_INCOMPLETE", "SnapshotError", "PublicApiError", "1h")


def test_reserved_window_rejection_and_rollback(tmp_path, capsys):
    w = S.ReservedWindow("EXP-0001/OOS", D_DEV_MS - 86_400_000, D_DEV_MS + 86_400_000)
    assert run(tmp_path, Scripted(), source=lambda: [w])[0] == 1
    check(tmp_path, capsys, "prepare", "RESERVED_WINDOW_OVERLAP", "SnapshotError", "SnapshotError")
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()
    assert not list((tmp_path / "var" / "snapshots").glob(".tmp-*"))


def test_reserved_window_source_failure(tmp_path, capsys):
    def boom():
        raise RuntimeError(SECRET)
    assert run(tmp_path, Scripted(), source=boom)[0] == 1
    check(tmp_path, capsys, "reserved_windows", "RESERVED_WINDOW_SOURCE_FAILURE", "SnapshotError", "RuntimeError")


def test_d_dev_after_server_time(tmp_path, capsys):
    assert run(tmp_path, Scripted(), d_dev="2999-01-01")[0] == 1
    check(tmp_path, capsys, "prepare", "DOWNLOAD_PREPARE_CHECK_FAILED", "SnapshotError", "SnapshotError")


def test_write_error_rolls_back(tmp_path, capsys, monkeypatch):
    def boom(*a, **k):
        raise OSError(SECRET)
    monkeypatch.setattr(S.pq, "write_table", boom)
    assert run(tmp_path, Scripted())[0] == 1
    check(tmp_path, capsys, "write", "WRITE_ERROR", "OSError", "OSError")
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()
    assert not list((tmp_path / "var" / "snapshots").glob(".tmp-*"))


def test_sealing_error(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(S.os, "geteuid", lambda: 0)
    assert run(tmp_path, Scripted())[0] == 1
    check(tmp_path, capsys, "seal", "SEALING_FAILURE", "SealingError", "SealingError", cls=D4.SEALING_ERROR)


def test_unknown_exception_falls_back_to_unknown(tmp_path, capsys, monkeypatch):
    class Weird(Exception):
        pass

    def boom(*a, **k):
        raise Weird(SECRET)
    monkeypatch.setattr(S, "_manifest", boom)
    assert run(tmp_path, Scripted())[0] == 1
    check(tmp_path, capsys, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN")
    assert not (tmp_path / "research" / "snapshots" / "SNAP-TEST.json").exists()


def test_transport_failures_keep_retry_counts_and_report_classification(tmp_path, capsys):
    t = Scripted({1: http(503), 2: http(503), 3: http(503)})
    code, sleeps = run(tmp_path, t)
    assert code == 1 and sleeps == [1.0, 2.0] and t.calls == 3
    check(tmp_path, capsys, "download", D4.RETRIES_EXHAUSTED, "D4TransportError", "HTTPError", cls=D4.RETRIES_EXHAUSTED)
    t = Scripted({1: http(429)})
    code, sleeps = run(tmp_path / "x", t)
    assert code == 1 and sleeps == [] and t.calls == 1
    assert "https" not in capsys.readouterr().err


def test_rejections_do_not_retry_and_success_is_silent(tmp_path, capsys):
    t = Scripted()
    assert run(tmp_path, t)[0] == 0
    assert capsys.readouterr().err == ""
    assert all(r["reason_code"] is None for r in diag(tmp_path))
    sleeps = run(tmp_path / "y", Custom(time={"serverTime": 1}), sid="SNAP-TEST")[1]
    assert sleeps == []


def test_authorization_refusal_unchanged_and_no_registry_touch(monkeypatch):
    assert D4.main(["--id", "SNAP-0001"]) == D4.EXIT_REFUSED
    reg = Path(__file__).resolve().parents[2] / "research" / "experiments" / "registry.jsonl"
    import hashlib
    assert hashlib.sha256(reg.read_bytes()).hexdigest() == "07efad206971a8efd0467f94961268bf6b04ba4391cc22610387bb4cec665e4b"
