"""Shared helpers for independent reverification probes (synthetic temp registries only)."""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]   # raíz del repositorio (portable)
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests" / "unit")]

import pandas as pd  # noqa: E402

from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import PartitionAccessError, PartitionLoader  # noqa: E402

import test_cr021_durability as D  # noqa: E402  (read-only reuse of setup helpers)

X1, Y1 = "EXP-0101", "EXP-0102"


def new_reg(work: Path) -> ExperimentRegistry:
    work.mkdir(parents=True, exist_ok=True)
    dec = work / "decisions"
    dec.mkdir(exist_ok=True)
    (dec / "DEC-900_ok.md").write_text("AUTORIZA: EXP-0101 OOS_EVALUATION\nAUTORIZA: EXP-0102 OOS_EVALUATION\n"
                                       "AUTORIZA: EXP-0101 oos SNAP-TEST\n")
    return ExperimentRegistry(work / "registry.jsonl", dec)


def gate(reg, logdir: Path, eid=X1, cfg="A"):
    """Real `load_train_val_for_configuration` decision logic; only `_read` is synthetic."""
    loader = PartitionLoader.__new__(PartitionLoader)
    loader.registry, loader.access_log = reg, Path(logdir) / f"access-{os.getpid()}.jsonl"
    loader.manifest = {"snapshot_id": "SNAP-TEST"}
    reads = []
    loader._read = lambda part: reads.append(part) or pd.DataFrame({"interval": ["1d"]})
    try:
        loader.load_train_val_for_configuration(eid, cfg)
        return "DELIVERED", reads
    except PartitionAccessError as exc:
        return "DENIED: " + str(exc)[:110] if "FULL" not in os.environ else "DENIED: " + str(exc), reads


def kinds(reg):
    return [(r["kind"], r.get("config_id")) for r in reg.records()
            if r["kind"] in ("CONFIGURATION_EVALUATED", "DEVIATION", "EVALUATION_PERSISTED")]


def fsync_fail(fail):
    real, calls = X.os.fsync, {"n": 0}

    def fsync(fd):
        calls["n"] += 1
        if fail(calls["n"]):
            raise OSError(5, "EIO simulado")
        return real(fd)
    X.os.fsync = fsync
    return calls, real
