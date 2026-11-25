"""Almacén recuperable de preregistros (CR-023 §C.4.1, B1). Contenido sintético, solo tmp_path."""
import ast
import hashlib
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swingpilot.research import prereg_store as ps  # noqa: E402
from swingpilot.research.prereg_store import (  # noqa: E402
    PreregContentConflict, PreregContentCorrupt, PreregContentMissing, PreregistrationStore,
    PreregStoreError, PreregStoreRejected, PreregStoreWriteUncertain)
from swingpilot.research.preregistration import canonical_json  # noqa: E402

EXP = "EXP-0001"


def _blob(content=None):
    content = content or {"experiment_id": EXP, "nota": "señal ñandú — 日本", "n": [1, 2, 3]}
    data = canonical_json(content).encode("utf-8")
    return content, data, hashlib.sha256(data).hexdigest()


@pytest.fixture
def store(tmp_path):
    return PreregistrationStore(tmp_path / "prereg")


def _snapshot(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")) if root.exists() else None


def test_round_trip_non_ascii_and_hash_matches_freeze_style(store):
    content, data, sha = _blob()
    path = store.write(EXP, data, sha)
    assert path == store.root / EXP / f"{sha}.json"
    assert store.read(EXP, sha) == data
    assert store.load(EXP, sha) == content
    assert hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest() == sha
    assert store.verify_cited(EXP, sha) == content
    assert "ñandú" in path.read_text(encoding="utf-8")


def test_write_frozen(store):
    content, data, sha = _blob()

    class F:
        pass
    f = F()
    f.content, f.sha256, f.experiment_id = content, sha, EXP
    assert store.write_frozen(f).read_bytes() == data


def test_file_mode_is_read_only(store):
    _, data, sha = _blob()
    path = store.write(EXP, data, sha)
    assert stat.S_IMODE(path.stat().st_mode) == 0o444


def test_idempotent_with_identical_bytes(store):
    _, data, sha = _blob()
    path = store.write(EXP, data, sha)
    mtime = path.stat().st_mtime_ns
    assert store.write(EXP, data, sha) == path
    assert path.stat().st_mtime_ns == mtime
    assert path.read_bytes() == data


def test_existing_file_with_different_bytes_is_corrupt_and_unchanged(store):
    _, data, sha = _blob()
    path = store.write(EXP, data, sha)
    # Simula una sustitución externa del contenido bajo el mismo nombre.
    os.chmod(path, 0o644)
    path.write_bytes(b"{}")
    with pytest.raises(PreregContentCorrupt):
        store.write(EXP, data, sha)
    assert path.read_bytes() == b"{}"


def test_tampered_file(store):
    _, data, sha = _blob()
    path = store.write(EXP, data, sha)
    os.chmod(path, 0o644)
    path.write_bytes(data + b" ")
    with pytest.raises(PreregContentCorrupt):
        store.read(EXP, sha)
    with pytest.raises(PreregContentCorrupt):
        store.load(EXP, sha)
    with pytest.raises(PreregContentCorrupt):
        store.verify_cited(EXP, sha)


def test_symlink_in_store_is_corrupt(store, tmp_path):
    _, data, sha = _blob()
    outside = tmp_path / "outside.json"
    outside.write_bytes(data)                      # mismo contenido: el hash coincidiría
    d = store.root / EXP
    d.mkdir(parents=True)
    (d / f"{sha}.json").symlink_to(outside)
    with pytest.raises(PreregContentCorrupt):
        store.read(EXP, sha)
    with pytest.raises(PreregContentCorrupt):
        store.verify_cited(EXP, sha)
    with pytest.raises(PreregContentCorrupt):      # tampoco sirve como «ya existente»
        store.write(EXP, data, sha)


def test_missing(store):
    _, _, sha = _blob()
    with pytest.raises(PreregContentMissing):
        store.read(EXP, sha)
    with pytest.raises(PreregContentMissing):
        store.verify_cited(EXP, sha)


def test_wrong_hash_name_is_corrupt(store):
    _, data, sha = _blob()
    other = "0" * 64
    d = store.root / EXP
    d.mkdir(parents=True)
    (d / f"{other}.json").write_bytes(data)
    with pytest.raises(PreregContentCorrupt):
        store.read(EXP, other)


def test_non_canonical_or_wrong_experiment_on_disk_is_corrupt(store):
    d = store.root / EXP
    d.mkdir(parents=True)
    noncanon = b'{"experiment_id": "EXP-0001"}'
    wrong = canonical_json({"experiment_id": "EXP-0002"}).encode()
    for blob in (noncanon, wrong, b"[1]", b"\xff\xfe"):
        sha = hashlib.sha256(blob).hexdigest()
        (d / f"{sha}.json").write_bytes(blob)
        assert store.read(EXP, sha) == blob  # el hash sí coincide
        with pytest.raises(PreregContentCorrupt):
            store.load(EXP, sha)


def test_cited_hash_conflict(store):
    _, data, sha = _blob()
    store.write(EXP, data, sha)
    d = store.root / EXP
    other = "a" * 64
    (d / f"{other}.json").write_bytes(data)  # contenido que hashea a sha, no a su nombre
    with pytest.raises(PreregContentCorrupt):
        store.verify_cited(EXP, other)
    # Dos contenidos para el mismo PREREGISTERED: el esperado difiere del citado → Conflict
    with pytest.raises(PreregContentConflict):
        store.verify_cited(EXP, sha, expected_sha256="b" * 64)
    assert store.verify_cited(EXP, sha, expected_sha256=sha)["experiment_id"] == EXP


def test_orphan_and_invalid_name_classification(store):
    _, data, sha = _blob()
    store.write(EXP, data, sha)
    _, data2, sha2 = _blob({"experiment_id": EXP, "otro": 1})
    store.write(EXP, data2, sha2)
    d = store.root / EXP
    (d / "notas.txt").write_text("x")
    (d / ("A" * 64 + ".json")).write_text("x")
    before = _snapshot(store.root)
    got = {e["name"]: e["status"] for e in store.entries(EXP, {sha})}
    assert got[f"{sha}.json"] == ps.CITED
    assert got[f"{sha2}.json"] == ps.ORPHAN
    assert got["notas.txt"] == ps.INVALID_NAME
    assert got["A" * 64 + ".json"] == ps.INVALID_NAME
    assert _snapshot(store.root) == before  # solo lectura
    assert store.entries("EXP-0009", set()) == []
    assert (d / f"{sha2}.json").exists()  # el huérfano se conserva


@pytest.mark.parametrize("exp,sha_kind,mutate", [
    ("EXP-1", "ok", None),
    ("exp-0001", "ok", None),
    (EXP, "short", None),
    (EXP, "upper", None),
    (EXP, "mismatch", None),
    (EXP, "ok", b"not json"),
    (EXP, "ok", b'{"experiment_id": "EXP-0001"}'),          # no canónico
    (EXP, "ok", b"[1]"),
    (EXP, "ok", canonical_json({"experiment_id": "EXP-0002"}).encode()),
])
def test_rejected_writes_nothing(store, exp, sha_kind, mutate):
    _, data, sha = _blob()
    if mutate is not None:
        data = mutate
        sha = hashlib.sha256(data).hexdigest()
    sha = {"ok": sha, "short": sha[:10], "upper": sha.upper(), "mismatch": "b" * 64}[sha_kind]
    with pytest.raises(PreregStoreRejected):
        store.write(exp, data, sha)
    assert not store.root.exists()


def test_import_and_constructor_do_not_create_default_root(tmp_path):
    PreregistrationStore(tmp_path / "x")
    assert not (tmp_path / "x").exists()
    assert ps.DEFAULT_ROOT.name == "preregistrations" and ps.DEFAULT_ROOT.parent.name == "research"
    PreregistrationStore(ps.DEFAULT_ROOT)
    assert not ps.DEFAULT_ROOT.exists()


# --- fallos inyectados -----------------------------------------------------------------------
def _is_dir_fd(fd):
    return stat.S_ISDIR(os.fstat(fd).st_mode)


def test_write_failure_is_uncertain_partial_stays_and_retry_is_corrupt(store, monkeypatch):
    _, data, sha = _blob()
    monkeypatch.setattr(os, "write", lambda fd, b: (_ for _ in ()).throw(OSError("disco lleno")))
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)
    monkeypatch.undo()
    path = store.root / EXP / f"{sha}.json"
    assert path.exists() and path.read_bytes() == b""  # el parcial se conserva
    with pytest.raises(PreregContentCorrupt):  # sin reparación automática
        store.write(EXP, data, sha)
    with pytest.raises(PreregContentCorrupt):
        store.read(EXP, sha)
    assert path.read_bytes() == b""


def test_short_writes_are_looped(store, monkeypatch):
    _, data, sha = _blob()
    real = os.write
    monkeypatch.setattr(os, "write", lambda fd, b: real(fd, bytes(b)[:3]))
    path = store.write(EXP, data, sha)
    assert path.read_bytes() == data


def test_file_fsync_failure_is_uncertain(store, monkeypatch):
    _, data, sha = _blob()
    real = os.fsync

    def fake(fd):
        if not _is_dir_fd(fd):
            raise OSError("fsync archivo")
        return real(fd)
    monkeypatch.setattr(os, "fsync", fake)
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)
    # Reintento con el fsync aún fallando: no informa éxito aunque los bytes estén completos.
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)
    monkeypatch.undo()
    # Con fsync correcto: el reintento es idempotente (mismos bytes, sin escribir) tras el fsync.
    assert store.write(EXP, data, sha).read_bytes() == data


def test_dir_fsync_failure_is_uncertain(store, monkeypatch):
    _, data, sha = _blob()
    # Crea el directorio del experimento antes, para que el único fsync de directorio sea el de escritura.
    (store.root / EXP).mkdir(parents=True)
    real = os.fsync

    def fake(fd):
        if _is_dir_fd(fd):
            raise OSError("fsync dir")
        return real(fd)
    monkeypatch.setattr(os, "fsync", fake)
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)
    monkeypatch.undo()
    assert store.write(EXP, data, sha).read_bytes() == data  # reintento idempotente


def test_reread_mismatch_is_uncertain(store, monkeypatch):
    _, data, sha = _blob()
    monkeypatch.setattr(ps, "_read_all", lambda *a, **k: b"otro")
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)


def test_all_errors_share_base():
    for e in (PreregStoreRejected, PreregContentMissing, PreregContentCorrupt,
              PreregContentConflict, PreregStoreWriteUncertain):
        assert issubclass(e, PreregStoreError) and issubclass(e, RuntimeError)


# --- estático --------------------------------------------------------------------------------
def test_module_has_no_delete_rename_replace_truncate_calls():
    src = Path(ps.__file__).read_text(encoding="utf-8")
    banned = {"unlink", "remove", "rename", "renames", "replace", "rmtree", "rmdir", "truncate",
              "ftruncate", "removedirs", "makedirs"}
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call):
            f = n.func
            names.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value == "w":
            raise AssertionError("no se admite open(..., 'w')")
    assert not (names & banned), names & banned
    assert "os.O_TRUNC" not in src


# --- revisión focalizada del propietario: frontera del almacén y durabilidad de directorios ----
def _outside_with(tmp_path, data, sha, *, tamper=False):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / f"{sha}.json").write_bytes(data + (b" " if tamper else b""))
    return outside


def test_symlinked_experiment_directory_is_corrupt_on_every_path(store, tmp_path):
    _, data, sha = _blob()
    outside = _outside_with(tmp_path, data, sha)       # contenido válido fuera del almacén
    store.root.mkdir()
    (store.root / EXP).symlink_to(outside, target_is_directory=True)
    before = _snapshot(outside)
    for call in (lambda: store.read(EXP, sha), lambda: store.load(EXP, sha),
                 lambda: store.verify_cited(EXP, sha), lambda: store.entries(EXP, {sha}),
                 lambda: store.write(EXP, data, sha)):
        with pytest.raises(PreregContentCorrupt):
            call()
    assert _snapshot(outside) == before


def test_symlinked_root_is_corrupt_and_nothing_written_outside(tmp_path):
    _, data, sha = _blob()
    outside = tmp_path / "outside"
    (outside / EXP).mkdir(parents=True)
    (outside / EXP / f"{sha}.json").write_bytes(data)
    (tmp_path / "prereg").symlink_to(outside, target_is_directory=True)
    store = PreregistrationStore(tmp_path / "prereg")
    before = _snapshot(outside)
    for call in (lambda: store.read(EXP, sha), lambda: store.verify_cited(EXP, sha),
                 lambda: store.entries(EXP, {sha}), lambda: store.write(EXP, data, sha)):
        with pytest.raises(PreregContentCorrupt):
            call()
    _, data2, sha2 = _blob({"experiment_id": EXP, "otro": 1})
    with pytest.raises(PreregContentCorrupt):
        store.write(EXP, data2, sha2)
    assert _snapshot(outside) == before


def test_experiment_path_that_is_a_file_is_corrupt(store):
    _, data, sha = _blob()
    store.root.mkdir()
    (store.root / EXP).write_bytes(b"x")
    with pytest.raises(PreregContentCorrupt):
        store.read(EXP, sha)
    with pytest.raises(PreregContentCorrupt):
        store.write(EXP, data, sha)


def test_root_parent_must_exist(tmp_path):
    _, data, sha = _blob()
    store = PreregistrationStore(tmp_path / "no" / "prereg")
    with pytest.raises(PreregStoreError):
        store.write(EXP, data, sha)
    assert not (tmp_path / "no").exists()
    with pytest.raises(PreregContentMissing):
        store.read(EXP, sha)
    assert store.entries(EXP, set()) == []


def _swap_dir_for_symlink(exp_dir: Path, outside: Path):
    os.rename(exp_dir, exp_dir.with_name(exp_dir.name + ".moved"))     # solo en la prueba
    exp_dir.symlink_to(outside, target_is_directory=True)


def test_no_check_then_use_race_on_write(store, tmp_path, monkeypatch):
    """El directorio del experimento se sustituye por un enlace simbólico justo después de
    abrirlo: la escritura sigue en el directorio abierto, nunca fuera del almacén."""
    _, data, sha = _blob()
    outside = tmp_path / "outside"
    outside.mkdir()
    real_open, swapped = os.open, []

    def racing_open(path, flags, *args, **kw):
        if path == f"{sha}.json" and "dir_fd" in kw and not swapped:
            swapped.append(True)
            _swap_dir_for_symlink(store.root / EXP, outside)
        return real_open(path, flags, *args, **kw)
    monkeypatch.setattr(os, "open", racing_open)
    store.write(EXP, data, sha)
    monkeypatch.undo()
    assert swapped and list(outside.iterdir()) == []
    assert (store.root / (EXP + ".moved") / f"{sha}.json").read_bytes() == data


def test_no_check_then_use_race_on_read(store, tmp_path, monkeypatch):
    _, data, sha = _blob()
    store.write(EXP, data, sha)
    outside = _outside_with(tmp_path, data, sha, tamper=True)
    real_open, swapped = os.open, []

    def racing_open(path, flags, *args, **kw):
        if path == f"{sha}.json" and "dir_fd" in kw and not swapped:
            swapped.append(True)
            _swap_dir_for_symlink(store.root / EXP, outside)
        return real_open(path, flags, *args, **kw)
    monkeypatch.setattr(os, "open", racing_open)
    assert store.read(EXP, sha) == data                 # el directorio abierto, no el de fuera
    monkeypatch.undo()
    assert swapped


def _record_fsync(monkeypatch, fail_on_inode=None):
    real, seen = os.fsync, []

    def fake(fd):
        st = os.fstat(fd)
        if stat.S_ISDIR(st.st_mode):
            if st.st_ino == fail_on_inode:
                raise OSError("fsync del padre de root")
            seen.append(st.st_ino)
        return real(fd)
    monkeypatch.setattr(os, "fsync", fake)
    return seen


def test_write_fsyncs_experiment_dir_root_and_root_parent(store, monkeypatch):
    _, data, sha = _blob()
    seen = _record_fsync(monkeypatch)
    store.write(EXP, data, sha)
    monkeypatch.undo()
    inodes = [os.stat(p).st_ino for p in (store.root / EXP, store.root, store.root.parent)]
    assert seen[-3:] == inodes


def test_retry_after_failed_directory_fsync_persists_parent_entries(store, monkeypatch):
    """Defecto demostrado: antes solo se hacía fsync del padre de un directorio creado en la misma
    llamada. Si el primer intento crea root y falla antes del fsync de su padre, el reintento
    encontraba root ya presente y no volvía a hacerlo, pero informaba éxito."""
    _, data, sha = _blob()
    parent_ino = os.stat(store.root.parent).st_ino
    _record_fsync(monkeypatch, fail_on_inode=parent_ino)
    with pytest.raises(PreregStoreWriteUncertain):
        store.write(EXP, data, sha)
    monkeypatch.undo()
    assert store.root.is_dir() and (store.root / EXP / f"{sha}.json").read_bytes() == data
    seen = _record_fsync(monkeypatch)
    assert store.write(EXP, data, sha).read_bytes() == data       # reintento idempotente
    monkeypatch.undo()
    assert parent_ino in seen and os.stat(store.root).st_ino in seen
