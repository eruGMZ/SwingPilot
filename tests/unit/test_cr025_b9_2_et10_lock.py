"""B9.2 (CR-025 B.7): bloqueo exclusivo de ET-10 con plazo único de 2 s (LOCK_NB + time.monotonic())."""
import fcntl
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from swingpilot.research import experiments as X  # noqa: E402


@pytest.fixture
def reg(tmp_path):
    return X.ExperimentRegistry(tmp_path / "reg" / "experiments.jsonl", decisions_dir=tmp_path / "d")


@pytest.fixture
def held(reg):
    """Mantiene el bloqueo desde otro descriptor (flock es por descripción de archivo abierta)."""
    reg.path.parent.mkdir(parents=True)
    lk = open(reg.path.with_name(reg.path.name + ".lock"), "a")
    fcntl.flock(lk, fcntl.LOCK_EX)
    yield lk
    lk.close()


def _fds():
    return len(os.listdir("/proc/self/fd"))


def test_timeout_constant_is_two_seconds():
    assert X.ET10_LOCK_TIMEOUT_S == 2.0


def test_uncontended_acquires_immediately_and_releases(reg):
    reg.path.parent.mkdir(parents=True)
    t0 = time.monotonic()
    with reg._locked_et10():
        probe = open(reg.path.with_name(reg.path.name + ".lock"), "a")
        with pytest.raises(BlockingIOError):                       # exclusivo mientras se mantiene
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        probe.close()
    assert time.monotonic() - t0 < 1.0
    with reg._locked():                                            # liberado: el escritor entra
        pass


def test_contention_times_out_with_distinct_error(reg, held, monkeypatch):
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 0.2)
    t0 = time.monotonic()
    with pytest.raises(X.RegistryLockTimeout, match="2 s"):
        with reg._locked_et10():
            pytest.fail("no debe adquirirse")
    assert 0.2 <= time.monotonic() - t0 < 1.5
    assert issubclass(X.RegistryLockTimeout, X.ExperimentError)
    assert not issubclass(X.RegistryLockTimeout, X.RegistryCorruptError)


def test_single_window_no_retry_after_deadline(reg, held, monkeypatch):
    calls = []
    real = fcntl.flock
    monkeypatch.setattr(X.fcntl, "flock", lambda f, op: (calls.append(op), real(f, op))[1])
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 0.1)
    monkeypatch.setattr(X, "ET10_LOCK_POLL_S", 0.01)
    t0 = time.monotonic()
    with pytest.raises(X.RegistryLockTimeout):
        with reg._locked_et10():
            pass
    elapsed = time.monotonic() - t0
    assert all(op == fcntl.LOCK_EX | fcntl.LOCK_NB for op in calls)  # nunca bloqueante
    assert len(calls) <= int(elapsed / 0.01) + 2 and elapsed < 1.0   # sin intentos tras el plazo
    n = len(calls)
    time.sleep(0.1)
    assert len(calls) == n


def test_acquires_when_released_within_window(reg, held, monkeypatch):
    import threading
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 2.0)
    threading.Timer(0.15, lambda: fcntl.flock(held, fcntl.LOCK_UN)).start()
    with reg._locked_et10():
        pass


def test_exception_inside_body_releases_and_closes(reg):
    reg.path.parent.mkdir(parents=True)
    before = _fds()
    with pytest.raises(RuntimeError, match="boom"):
        with reg._locked_et10():
            raise RuntimeError("boom")
    assert _fds() == before
    with reg._locked_et10():                                       # reutilizable
        pass


def test_timeout_closes_descriptor(reg, held, monkeypatch):
    monkeypatch.setattr(X, "ET10_LOCK_TIMEOUT_S", 0.05)
    before = _fds()
    with pytest.raises(X.RegistryLockTimeout):
        with reg._locked_et10():
            pass
    assert _fds() == before


def test_missing_directory_is_not_created_and_not_timeout(reg):
    with pytest.raises(FileNotFoundError):
        with reg._locked_et10():
            pass
    assert not reg.path.parent.exists()


def test_writers_keep_blocking_semantics_and_interoperate(reg):
    called = []
    with reg._locked():                                            # _locked sigue siendo bloqueante y LOCK_EX
        probe = open(reg.path.with_name(reg.path.name + ".lock"), "a")
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        probe.close()
        called.append(1)
    with pytest.raises(X.RegistryLockTimeout):                     # un escritor en curso bloquea a ET-10
        import unittest.mock as m
        with m.patch.object(X, "ET10_LOCK_TIMEOUT_S", 0.05), reg._locked():
            with reg._locked_et10():
                pass
    assert called
    with reg._locked_et10():                                       # y tras el escritor ET-10 entra
        pass
