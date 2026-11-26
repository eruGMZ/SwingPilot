"""CR-023 B6.3: credencial de consumo obligatoria e inmutable; `claim_partition` la ejecuta dentro del
bloqueo sobre registros releídos (decisión 3, condición 1; precedente `FreezeCheck`)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from consumption_helpers import ok_consumption_check  # noqa: E402
from swingpilot.research import partitions as P  # noqa: E402
from swingpilot.research.experiments import (_CONSUMPTION_CHECK_KEY, ConsumptionCheck, ExperimentError,  # noqa: E402
                                              ExperimentRegistry, RegistryCorruptError)

KW = dict(snapshot_id="SNAP-TEST1", partition="oos", experiment_id="EXP-0101", snapshot_last_open_time=0,
          decision_ref="DEC-900_ok.md")


@pytest.fixture
def reg(tmp_path):
    return ExperimentRegistry(tmp_path / "reg.jsonl", tmp_path)


def test_credential_cannot_be_built_without_key_and_is_immutable():
    for key in (None, object(), "_CONSUMPTION_CHECK_KEY"):
        with pytest.raises(ExperimentError, match="build_consumption_check"):
            ConsumptionCheck(key, lambda *a: None)
    with pytest.raises(ExperimentError):
        ConsumptionCheck(_CONSUMPTION_CHECK_KEY, "no invocable")
    c = ok_consumption_check()
    with pytest.raises(AttributeError):
        c._fn = lambda *a: None
    with pytest.raises(AttributeError):
        c.extra = 1


@pytest.mark.parametrize("bad", [None, object(), lambda *a: None, "x"])
def test_claim_and_record_reject_missing_or_foreign_credential_without_writing(reg, bad):
    kw = dict(KW) if bad is None else {**KW, "consumption_check": bad}
    with pytest.raises(ExperimentError, match="consumption_check"):
        reg.claim_partition(**kw)
    with pytest.raises(ExperimentError, match="consumption_check"):
        reg.record_partition_consumed(**kw)
    assert reg.records() == []


def test_check_rejection_blocks_write_and_exception_is_wrapped(reg):
    with pytest.raises(ExperimentError, match="rechazó el consumo: motivo"):
        reg.claim_partition(**KW, consumption_check=ok_consumption_check(lambda *a: "motivo"))

    def boom(*a):
        raise RuntimeError("fallo")
    with pytest.raises(ExperimentError, match="fallo"):
        reg.claim_partition(**KW, consumption_check=ok_consumption_check(boom))
    assert reg.records() == []


def test_check_runs_under_lock_on_fresh_records(reg):
    seen = []

    def spy(records, snapshot_id, partition, experiment_id, decision_ref):
        seen.append(([r["kind"] for r in records], (snapshot_id, partition, experiment_id, decision_ref)))
        # el bloqueo es exclusivo: un segundo intento no bloqueante falla mientras se ejecuta la comprobación
        import fcntl
        with open(reg.path.with_name(reg.path.name + ".lock"), "a") as lk:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert reg.claim_partition(**KW, consumption_check=ok_consumption_check(spy)) is not None
    # otro proceso escribe entre llamadas: la siguiente comprobación ve el registro releído
    assert reg.claim_partition(**{**KW, "partition": "lockbox"}, consumption_check=ok_consumption_check(spy))
    assert seen[0][0] == [] and seen[1][0] == ["PARTITION_CONSUMED"]
    assert seen[0][1] == ("SNAP-TEST1", "oos", "EXP-0101", "DEC-900_ok.md")


def test_corrupt_registry_fails_closed_before_check_and_writes_nothing(reg):
    reg.path.write_bytes(b"{no json\n")
    before = reg.path.read_bytes()
    called = []
    with pytest.raises(RegistryCorruptError):
        reg.claim_partition(**KW, consumption_check=ok_consumption_check(lambda *a: called.append(1)))
    assert called == [] and reg.path.read_bytes() == before


def test_already_consumed_still_returns_none_then_record_raises(reg):
    assert reg.claim_partition(**KW, consumption_check=ok_consumption_check()) is not None
    assert reg.claim_partition(**KW, consumption_check=ok_consumption_check()) is None
    with pytest.raises(ExperimentError, match="ya consumido"):
        reg.record_partition_consumed(**KW, consumption_check=ok_consumption_check())
    assert len(reg.consumed_partitions()) == 1


def test_builder_returns_credential():
    assert type(P.build_consumption_check()) is ConsumptionCheck


def test_static_guard_consumption_credential_only_in_registry_and_partitions():
    root = Path(__file__).resolve().parents[2]
    allowed = {root / "src/swingpilot/research/experiments.py", root / "src/swingpilot/research/partitions.py"}
    offenders = []
    for base in (root / "src", root / "scripts"):
        for f in base.rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            if f not in allowed and ("_CONSUMPTION_CHECK_KEY" in text or "ConsumptionCheck(" in text):
                offenders.append(str(f.relative_to(root)))
    assert offenders == []
