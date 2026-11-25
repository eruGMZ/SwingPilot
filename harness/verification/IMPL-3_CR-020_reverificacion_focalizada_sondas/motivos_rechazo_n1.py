import sys, copy, pytest
sys.path.insert(0, "src"); sys.path.insert(0, "tests/unit")
import test_n1_deviation_prewrite_validation as T
from test_qa_cr020_01 import frozen
from swingpilot.research.experiments import ExperimentRegistry
import tempfile, pathlib
for name, mut in T.CASES.items():
    d = pathlib.Path(tempfile.mkdtemp(dir=sys.argv[1]))
    reg = ExperimentRegistry(d / "registry.jsonl", decisions_dir=d / "dec")
    (d/"dec").mkdir()
    try:
        fz = frozen(reg); fz.begin_evaluation("A", registry=reg)
        rec = T.valid_record(fz, reg); mut(rec)
        T.call(reg, rec); print(f"{name:34s} ACCEPTED!")
    except Exception as e:
        print(f"{name:34s} {type(e).__name__}: {str(e)[:110]}")
