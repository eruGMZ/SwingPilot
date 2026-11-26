"""CR-024 v1.12 CR24-I2a — almacén inmutable de resultados (sintético)."""
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import result_store as S  # noqa: E402
from swingpilot.research.result_serialization import canonical_bytes, evaluation_hash  # noqa: E402

DATA = canonical_bytes({"a": 1, "m": 0.5})
OTHER = canonical_bytes({"a": 2})


@pytest.fixture
def store(tmp_path):
    return S.ResultStore(tmp_path / "results")


def test_write_read_path_and_mode(store):
    p = store.write("EXP-0001", "oos", DATA)
    assert p == store.root / "EXP-0001" / "oos.result.json"
    assert p.read_bytes() == DATA and store.read("EXP-0001", "oos") == DATA
    assert stat.S_IMODE(p.stat().st_mode) == 0o444
    assert evaluation_hash(store.read("EXP-0001", "oos")) == evaluation_hash(DATA)
    store.write("EXP-0001", "lockbox", OTHER)


def test_idempotent_and_conflict_preserves(store):
    p = store.write("EXP-0001", "oos", DATA)
    assert store.write("EXP-0001", "oos", DATA) == p
    with pytest.raises(S.ResultStoreConflict):
        store.write("EXP-0001", "oos", OTHER)
    assert p.read_bytes() == DATA


@pytest.mark.parametrize("exp,part,data", [
    ("EXP-1", "oos", DATA), ("../x", "oos", DATA), ("EXP-0001", "TRAIN", DATA), ("EXP-0001", "OOS", DATA),
    ("EXP-0001", "Oos", DATA), ("EXP-0001", "LockBox", DATA), ("EXP-0001", "oos ", DATA), ("EXP-0001", None, DATA),
    ("EXP-0001", "../OOS", DATA), ("EXP-0001", "oos", "str"),
    ("EXP-0001", "oos", b'{"b": 1}'), ("EXP-0001", "oos", b'{"a":1.5}'), ("EXP-0001", "oos", b"nope"),
])
def test_rejects_invalid_nothing_written(store, exp, part, data):
    with pytest.raises(S.ResultStoreRejected):
        store.write(exp, part, data)
    assert not store.root.exists()


def test_symlinked_file_is_not_followed(store, tmp_path):
    store.write("EXP-0001", "lockbox", OTHER)
    target = tmp_path / "outside.json"
    target.write_bytes(DATA)
    link = store.root / "EXP-0001" / "oos.result.json"
    link.symlink_to(target)
    with pytest.raises(S.ResultStoreCorrupt):
        store.read("EXP-0001", "oos")
    with pytest.raises(S.ResultStoreCorrupt):
        store.write("EXP-0001", "oos", DATA)
    assert target.read_bytes() == DATA and link.is_symlink()


def test_symlinked_dirs_are_not_followed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "results").symlink_to(outside)
    with pytest.raises(S.ResultStoreCorrupt):
        S.ResultStore(tmp_path / "results").write("EXP-0001", "oos", DATA)
    assert list(outside.iterdir()) == []
    root = tmp_path / "r2"
    root.mkdir()
    (root / "EXP-0001").symlink_to(outside)
    with pytest.raises(S.ResultStoreCorrupt):
        S.ResultStore(root).write("EXP-0001", "oos", DATA)
    assert list(outside.iterdir()) == []


def test_read_missing_and_noncanonical(store):
    with pytest.raises(S.ResultStoreMissing):
        store.read("EXP-0001", "oos")
    store.write("EXP-0001", "lockbox", OTHER)
    with pytest.raises(S.ResultStoreMissing):
        store.read("EXP-0001", "oos")
    f = store.root / "EXP-0001" / "oos.result.json"
    f.write_bytes(b'{"a": 1}')
    with pytest.raises(S.ResultStoreCorrupt):
        store.read("EXP-0001", "oos")


def test_partial_file_kept_conflict_not_repair(store):
    store.write("EXP-0001", "lockbox", OTHER)
    f = store.root / "EXP-0001" / "oos.result.json"
    f.write_bytes(DATA[:3])
    with pytest.raises(S.ResultStoreConflict):
        store.write("EXP-0001", "oos", DATA)
    assert f.read_bytes() == DATA[:3]


def test_durability_order_and_failure_uncertain(store, monkeypatch):
    calls = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(stat.S_ISREG(os.fstat(fd).st_mode)), real(fd))[1])
    store.write("EXP-0001", "oos", DATA)
    assert calls == [True, False, False, False]          # archivo, experimento, root, padre
    calls.clear()
    store.write("EXP-0001", "oos", DATA)                  # idempotente: vuelve a hacer fsync
    assert calls == [True, False, False, False]

    def boom(fd):
        raise OSError("disco")
    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(S.ResultStoreWriteUncertain):
        store.write("EXP-0001", "lockbox", OTHER)
    assert (store.root / "EXP-0001" / "lockbox.result.json").read_bytes() == OTHER   # conservado
    with pytest.raises(S.ResultStoreWriteUncertain):
        store.write("EXP-0001", "oos", DATA)
