"""QA-CR020-01 / QA-CR020-03 independent probes. argv: workroot"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
from swingpilot.research.experiments import EvaluationRequestRejected, PersistenceUncertainError  # noqa: E402
from swingpilot.research.preregistration import EvaluationPersistenceUncertain  # noqa: E402

ROOT = Path(sys.argv[1])
HERE = Path(__file__).parent
PY = str(C.REPO / ".venv/bin/python")


def child(work, eid=C.X1, cfg="A"):
    out = subprocess.run([PY, "-I", "-B", str(HERE / "child_gate.py"), str(work), eid, cfg],
                         capture_output=True, text=True)
    return (out.stdout.strip() or out.stderr.strip()[-300:])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def section(t):
    print(f"\n=== {t}")


# ---- 01: invalid mandatory deviation evidence -------------------------------------------------
section("01-a invalid informed_by variants for unplanned Z: nothing written, no count, no access")
for i, bad in enumerate([[{"experiment_id": "EXP-0199", "config_id": "Q"}], [{"provenance_id": "b" * 32}],
                         [{"experiment_id": "EXP-0101", "config_id": "A", "x": 1}], "not-a-list", None,
                         [{"experiment_id": "EXP-0101", "config_id": "Z"}]]):   # self-reference (not prior)
    w = ROOT / f"01a-{i}"
    reg = C.new_reg(w)
    fz = C.D.frozen(reg)
    before = sha(reg.path)
    try:
        fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=bad)
        r = "ACCEPTED"
    except Exception as exc:  # noqa: BLE001
        r = type(exc).__name__
    print(f"bad={bad!r:60.60} -> {r}; file unchanged={sha(reg.path) == before}; "
          f"pairs={list(reg.accounting()['pairs'])}; gate={C.gate(reg, w, cfg='Z')[0][:8]}; child={child(w, cfg='Z')[:30]}")

section("01-b empty justification / missing builder")
w = ROOT / "01b"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
for kw in ({"justification": "  ", "informed_by": []}, {"justification": None, "informed_by": []}):
    try:
        fz.begin_evaluation("Z", registry=reg, **kw)
        print(kw, "ACCEPTED")
    except Exception as exc:  # noqa: BLE001
        print(kw, "->", type(exc).__name__, "| pairs:", list(reg.accounting()["pairs"]))
try:
    reg.begin_configuration_evaluation(C.X1, "Z", actor="o")
except Exception as exc:  # noqa: BLE001
    print("direct API without builder ->", type(exc).__name__)

section("01-c builder returning DEVIATION of another experiment with same config_id (direct API)")
w = ROOT / "01c"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
before = sha(reg.path)


def foreign_builder():
    return {"kind": "DEVIATION", "deviation_id": "c" * 32, "experiment_id": "EXP-0999", "config_id": "Z",
            "preregistration_sha256": "0" * 64, "field": "trials_count", "old": 1, "new": 2,
            "justification": "j", "after_oos": False, "access_log_evidence": [], "actor": "o",
            "authorizes_change": False, "informed_by": []}


try:
    reg.begin_configuration_evaluation(C.X1, "Z", actor="o", deviation_builder=foreign_builder)
    r = "SUCCESS"
except Exception as exc:  # noqa: BLE001
    r = f"{type(exc).__name__}: {str(exc)[:140]}"
print("result:", r)
print("file unchanged:", sha(reg.path) == before)
try:
    print("records readable after:", len(reg.records()))
except Exception as exc:  # noqa: BLE001
    print("records after: ", type(exc).__name__, str(exc)[:160])

# ---- 03: durability ---------------------------------------------------------------------------
section("03-a evidence fsync always failing: 3 attempts; same obj / new obj / separate process")
w = ROOT / "03a"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
calls, real = C.fsync_fail(lambda n: True)
for k in range(3):
    try:
        fz.begin_evaluation("A", registry=reg)
        print(f"attempt {k + 1}: SUCCESS (!!)")
    except Exception as exc:  # noqa: BLE001
        print(f"attempt {k + 1}: {type(exc).__name__}")
C.X.os.fsync = real
print("fsync calls:", calls["n"], "| kinds:", C.kinds(reg))
print("same obj gate:", C.gate(reg, w)[0][:60])
print("new obj gate:", C.gate(C.ExperimentRegistry(reg.path, reg.decisions_dir), w)[0][:60])
print(child(w))
section("03-b retry with fsync working after failures: copy + marker; count 1; access everywhere")
rec = fz.begin_evaluation("A", registry=reg)
print("retry ->", rec["kind"], "| kinds:", C.kinds(reg))
lines = reg.path.read_bytes().split(b"\n")
ce = [ln for ln in lines if b'"CONFIGURATION_EVALUATED"' in ln]
print("CE copies byte-identical:", len(set(ce)) == 1, "count:", len(ce), "| trials E:", reg.accounting()["E"])
mk = [json.loads(ln) for ln in lines if b'"EVALUATION_PERSISTED"' in ln][0]
print("marker certifies sha == CE line sha:", mk["certifies"][0]["line_sha256"] == hashlib.sha256(ce[0]).hexdigest())
print(child(w))
before = sha(reg.path)
fz.begin_evaluation("A", registry=reg)
print("second retry writes nothing:", sha(reg.path) == before)

section("03-c marker fsync failing only (2nd fsync): R2")
w = ROOT / "03c"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
calls, real = C.fsync_fail(lambda n: n == 2)
try:
    fz.begin_evaluation("A", registry=reg)
    print("original op: SUCCESS (!!)")
except Exception as exc:  # noqa: BLE001
    print("original op:", type(exc).__name__)
C.X.os.fsync = real
print("kinds:", C.kinds(reg), "|", child(w))
before = sha(reg.path)
fz.begin_evaluation("A", registry=reg)
print("idempotent retry success without writing:", sha(reg.path) == before)
# marker lost: synthetic copy without marker line
w2 = ROOT / "03c-lost"
reg2 = C.new_reg(w2)
w2.joinpath("registry.jsonl").write_bytes(b"".join(ln + b"\n" for ln in reg.path.read_bytes().split(b"\n")[:-1]
                                                   if b'"EVALUATION_PERSISTED"' not in ln))
print("marker lost -> ", child(w2), "| E:", reg2.accounting()["E"])

section("03-d unplanned Z: evidence fsync fail (CE+DEV one write) vs marker fsync fail")
for label, fail in (("evidence-fsync-fails", lambda n: n == 1), ("marker-fsync-fails", lambda n: n == 2)):
    w = ROOT / f"03d-{label}"
    reg = C.new_reg(w)
    fz = C.D.frozen(reg)
    calls, real = C.fsync_fail(fail)
    try:
        fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
        r = "SUCCESS (!!)"
    except Exception as exc:  # noqa: BLE001
        r = type(exc).__name__
    C.X.os.fsync = real
    print(f"{label}: op={r}; kinds={C.kinds(reg)}; {child(w, cfg='Z')}")

section("03-e marker never emitted after evidence fsync failure (file inspection)")
w = ROOT / "03e"
reg = C.new_reg(w)
fz = C.D.frozen(reg)
seq = []
real_wl = C.ExperimentRegistry._write_lines


def traced(self, lines):
    seq.append(("write", [json.loads(ln)["kind"] for ln in lines]))
    try:
        real_wl(self, lines)
        seq.append(("fsync-ok", None))
    except OSError:
        seq.append(("fsync-fail", None))
        raise


C.ExperimentRegistry._write_lines = traced
calls, real = C.fsync_fail(lambda n: n == 1)
try:
    fz.begin_evaluation("A", registry=reg)
except Exception:  # noqa: BLE001
    pass
C.X.os.fsync = real
fz.begin_evaluation("A", registry=reg)
C.ExperimentRegistry._write_lines = real_wl
print("sequence:", seq)
