"""Separate process: fresh registry object, real loader gate decision. argv: workdir eid cfg"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

work, eid, cfg = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
reg = C.ExperimentRegistry(work / "registry.jsonl", work / "decisions")
res, reads = C.gate(reg, work, eid, cfg)
try:
    cnt = reg.trials_count()
except Exception as exc:  # noqa: BLE001
    cnt = f"ERR {type(exc).__name__}"
print(f"child pid-sep: {res} | reads={reads} | trials_count={cnt}")
