"""Runs under strace: begin_evaluation of planned A and unplanned Z on a prepared registry. argv: workdir"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

w = Path(sys.argv[1])
reg = C.ExperimentRegistry(w / "registry.jsonl", w / "decisions")
fz = pickle.loads((w / "fz.pkl").read_bytes())
sys.stderr.write("@@BEGIN-A\n"); sys.stderr.flush()
fz.begin_evaluation("A", registry=reg)
sys.stderr.write("@@BEGIN-Z\n"); sys.stderr.flush()
fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
sys.stderr.write("@@END\n"); sys.stderr.flush()
