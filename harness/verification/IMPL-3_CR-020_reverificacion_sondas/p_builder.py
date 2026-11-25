"""Follow-up of 01-c: which nonconforming builder outputs reach the file? argv: workroot"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

ROOT = Path(sys.argv[1])

# 03-b recheck: byte identity of CE copies (parse kinds properly)
w = ROOT / "03b-recheck"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
calls, real = C.fsync_fail(lambda n: n <= 3)
for _ in range(3):
    try:
        fz.begin_evaluation("A", registry=reg)
    except Exception:  # noqa: BLE001
        pass
C.X.os.fsync = real
fz.begin_evaluation("A", registry=reg)
raw = reg.path.read_bytes().split(b"\n")[:-1]
ce = [ln for ln in raw if json.loads(ln)["kind"] == "CONFIGURATION_EVALUATED"]
mk = [json.loads(ln) for ln in raw if json.loads(ln)["kind"] == "EVALUATION_PERSISTED"]
print(f"03-b recheck: CE lines={len(ce)} byte-identical={len(set(ce)) == 1}; markers={len(mk)}; "
      f"E={reg.accounting()['E']}; marker sha matches={mk[0]['certifies'][0]['line_sha256'] == hashlib.sha256(ce[0]).hexdigest()}")

base = {"kind": "DEVIATION", "deviation_id": "c" * 32, "experiment_id": C.X1, "config_id": "Z",
        "field": "trials_count", "old": 1, "new": 2, "justification": "j", "after_oos": False,
        "access_log_evidence": [], "actor": "o", "authorizes_change": False, "informed_by": []}
variants = {
    "foreign experiment_id": {"experiment_id": "EXP-0999"},
    "field != trials_count": {"field": "metrics"},
    "deviation_id missing": {"deviation_id": None},
    "wrong preregistration_sha256": {},          # filled below with zeros
    "informed_by unverifiable": {"informed_by": [{"experiment_id": "EXP-0199", "config_id": "Q"}]},
}
for name, patch in variants.items():
    w = ROOT / ("bld-" + name.replace(" ", "_").replace("!=", "ne"))
    reg = C.new_reg(w)
    fz = C.D.frozen(reg)
    rec = dict(base, preregistration_sha256=fz.sha256 if name != "wrong preregistration_sha256" else "0" * 64)
    rec.update({k: v for k, v in patch.items()})
    if rec.get("deviation_id") is None:
        rec.pop("deviation_id")
    before = reg.path.read_bytes()
    try:
        reg.begin_configuration_evaluation(C.X1, "Z", actor="o", deviation_builder=lambda r=rec: dict(r))
        res = "SUCCESS"
    except Exception as exc:  # noqa: BLE001
        res = type(exc).__name__
    written = reg.path.read_bytes() != before
    try:
        reg.records()
        state = "readable"
    except Exception as exc:  # noqa: BLE001
        state = "CORRUPT (P1 total block)"
    g = C.gate(reg, w, cfg="Z")[0][:70]
    print(f"{name:30} -> {res:28} written={written!s:5} registry={state:24} gate={g}")
