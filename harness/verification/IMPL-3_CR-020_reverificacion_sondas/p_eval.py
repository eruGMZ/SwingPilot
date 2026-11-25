"""QA-CR020-02 / 04 / 05 / O4 / O3 independent probes (synthetic temp registries only). argv: workroot"""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
import test_trials_accounting as T  # noqa: E402  (read-only reuse of helpers)
from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.preregistration import (ConfirmatoryStatusUnverifiable, confirmatory_status,  # noqa: E402
                                                 freeze)

ROOT = Path(sys.argv[1])
N = {"i": 0}


def new_reg():
    N["i"] += 1
    w = ROOT / f"e{N['i']:03d}"
    dec = w / "decisions"
    dec.mkdir(parents=True)
    lines = [f"AUTORIZA: {e} {s}" for e in ("EXP-0101", "EXP-0102", "EXP-0103") for s in ("OOS_EVALUATION", "APPROVED")]
    (dec / "DEC-900_ok.md").write_text("\n".join(lines) + "\n")
    (dec / T.PROV_DEC).write_text("# p\n\nAUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=4 COTA=0\n"
                                  "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4\n")
    return ExperimentRegistry(w / "registry.jsonl", dec), w


def code(v):
    return v.outcome if v.outcome != "INCONCLUSIVE" else "INCONCLUSIVE/" + v.reasons[0].split(":")[0]


def query(reg, eid, **kw):
    try:
        st = confirmatory_status(reg, eid, **kw)
        return f"{st['confirmatory']}" + (f" (unverified={len(st['unverified'])})" if st["unverified"] else "")
    except ConfirmatoryStatusUnverifiable:
        return "UNVERIFIABLE"
    except Exception as exc:  # noqa: BLE001
        return f"ERR {type(exc).__name__}"


def section(t):
    print(f"\n=== {t}")


# ============================== QA-CR020-02 ========================================================
section("02 consistency matrix: evaluator vs confirmatory_status (with prereg+inputs | without inputs)")
ARG = "ARGMAX sharpe TIEBREAK A,B"
RES = {"A": {"sharpe": 1.0}, "B": {"sharpe": 2.0}}


def scenario(name, *, sel="B", unplanned=False, dev=None, exposure=False, tamper_inputs=False, prereg="own"):
    reg, w = new_reg()
    fz = T.frozen_experiment(reg, planned=("A", "B"), rule=ARG)
    res = dict(RES)
    for c in ("A", "B"):
        fz.begin_evaluation(c, registry=reg)
    if unplanned:
        fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
        res["Z"] = {"sharpe": 0.1}
    if dev:
        ah = [{"allowed": True, "partition": "oos", "experiment_id": "EXP-0101"}] if exposure else None
        fz.record_deviation(dev, "changed", "j", registry=reg, informed_by=[], access_history=ah)
        fz = copy.copy(fz); fz._registry = None; fz.deviations = []; fz._persistence_uncertain = None
    inputs = T.inputs_for("EXP-0101", res)
    T.select(reg, "EXP-0101", sel, inputs)
    given = inputs if not tamper_inputs else inputs + b" "
    pr = fz
    if prereg == "foreign":
        c2 = copy.deepcopy(fz.content); c2["limitations"] = "<other>"
        pr = freeze(c2)
    elif prereg == "altered":
        pr = copy.deepcopy(fz); pr.content["limitations"] = "<tampered>"
    v = A.evaluate(T.evidence(), reg, preregistration=pr, selection_inputs=given)
    q_full = query(reg, "EXP-0101", preregistration=pr, selection_inputs=given)
    q_none = query(reg, "EXP-0101")
    print(f"{name:42} evaluator={code(v):45} query(full)={q_full:28} query(no inputs)={q_none}")


scenario("clean, selection follows rule")
scenario("selection against rule (P3)", sel="A")
scenario("unplanned Z with DEVIATION (P2)", unplanned=True)
scenario("rule-change deviation before exposure", dev="candidate_selection_rule")
scenario("design deviation after exposure (costs)", dev="costs", exposure=True)
scenario("design deviation before exposure (costs)", dev="costs")
scenario("non-design deviation (limitations)", dev="limitations")
scenario("tampered selection inputs", tamper_inputs=True)
scenario("foreign (unbound) preregistration", prereg="foreign")
scenario("altered preregistration content", prereg="altered")
scenario("unplanned Z + tampered inputs", unplanned=True, tamper_inputs=True)

# ============================== QA-CR020-04 ========================================================
section("04 exact-pair relevance, case-3 precedence, provenance separation, dedup, frozen count preserved")
YA, YB = T.YA, T.YB


def rel(name, sel_ib, devs=(), with_hist=False, t_after_selection=False):
    reg, w = new_reg()
    if with_hist:
        T.historical(reg)
    fx = T.frozen_experiment(reg, "EXP-0101", planned=("A",))
    fx.begin_evaluation("A", registry=reg)
    pre_line = [ln for ln in reg.path.read_bytes().split(b"\n") if b'"to": "PREREGISTERED"' in ln
                and b"EXP-0101" in ln][0]
    inputs = T.inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    fy = None
    if not t_after_selection:
        fy = T.frozen_experiment(reg, "EXP-0102", planned=("YA", "YB"), rule="PRIMARY YA")
        fy.begin_evaluation("YA", registry=reg)
        fy.begin_evaluation("YB", registry=reg)
    ib = sel_ib(reg) if callable(sel_ib) else sel_ib
    T.select(reg, "EXP-0101", "A", inputs, informed_by=ib)
    if t_after_selection:
        fy = T.frozen_experiment(reg, "EXP-0102", planned=("YA", "YB"), rule="PRIMARY YA")
        fy.begin_evaluation("YA", registry=reg)
        fy.begin_evaluation("YB", registry=reg)
    for d in devs:
        fx.record_deviation("limitations", "x", "j", registry=reg, informed_by=d)
        fx._persistence_uncertain = None
    fx2 = copy.copy(fx); fx2._registry = None
    v = A.evaluate(T.evidence(), reg, preregistration=fx2, selection_inputs=inputs)
    acc = v.metrics["trials_accounting"]
    still = pre_line in reg.path.read_bytes().split(b"\n")
    frozen_acc = json.loads(pre_line)["evidence"]["trials_accounting"]
    print(f"{name:52} {code(v):50} rel={[r['config_id'] for r in acc['relevant']]} "
          f"undet={[r['config_id'] for r in acc['undetermined']]} N_pre={acc['N_pre']} N_eval={acc['N_eval']} "
          f"tc={v.metrics['trials_count']} frozenN_pre={frozen_acc['N_pre']} frozen_line_intact={still}")


rel("sel cites YB only", [YB])
rel("sel cites YA+YB", [YA, YB])
rel("sel cites YB; later DEV cites YB (dedup)", [YB], devs=([YB],))
rel("sel cites YA+YB; later DEV informed_by=[] (case 3)", [YA, YB], devs=([],))
rel("sel cites YA+YB; later DEV cites YB only (case 3 YA)", [YA, YB], devs=([YB],))
rel("sel cites provenance_id only", lambda r: [{"provenance_id": r.accounting()["provenance_ids"][0]}],
    with_hist=True)
rel("sel []; later DEV cites provenance_id only (case 3)", [],
    devs=(None,), with_hist=True) if False else None
rel("T evaluated after selection, no later points", [], t_after_selection=True)
rel("T after selection; later DEV cites YA", [], devs=([YA],), t_after_selection=True)

# ============================== QA-CR020-05 ========================================================
section("05-a non-object JSON lines, every type, head/middle/tail")
reg0, w0 = new_reg()
fz0, inp0 = T.ready(reg0)
base = reg0.path.read_bytes().split(b"\n")[:-1]
for tok in (b"[1, 2]", b"[]", b"null", b"3", b"1.5", b'"x"', b"true", b"false", b"{}"):
    for pos, idx in (("head", 0), ("middle", len(base) // 2), ("tail", len(base))):
        reg, w = new_reg()
        lines = base[:idx] + [tok] + base[idx:]
        reg.path.write_bytes(b"".join(ln + b"\n" for ln in lines))
        before = reg.path.read_bytes()
        try:
            v = A.evaluate(T.evidence(), reg, preregistration=fz0, selection_inputs=inp0)
            r = f"{code(v)} tc={v.metrics['trials_count']}"
        except Exception as exc:  # noqa: BLE001
            r = f"RAISED {type(exc).__name__}"
        print(f"{tok.decode():8} {pos:6} -> {r:60} file intact={reg.path.read_bytes() == before}")

section("05-b corruption appended between reads: inject at the k-th registry read during evaluate()")
orig_load = ExperimentRegistry._load
for tail in (b"[1, 2]\n", b'{"kind": "TRUNC'):
    for k in range(1, 16):
        reg, w = new_reg()
        fz, inp = T.ready(reg)
        cnt = {"n": 0}

        def load(self, _k=k, _tail=tail, _cnt=cnt):
            _cnt["n"] += 1
            if _cnt["n"] == _k:
                with open(self.path, "ab") as fh:
                    fh.write(_tail)
            return orig_load(self)
        ExperimentRegistry._load = load
        try:
            v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inp)
            r = f"{code(v)} tc={v.metrics['trials_count']}"
        except Exception as exc:  # noqa: BLE001
            r = f"RAISED {type(exc).__name__}: {str(exc)[:60]}"
        finally:
            ExperimentRegistry._load = orig_load
        print(f"tail={tail!r:18} inject@read{k:2} (reads={cnt['n']:2}) -> {r}")
        if cnt["n"] < k:
            break

section("05-c out-of-protocol NON-append rewrite between reads (removes a malformed X DEVIATION)")
reg, w = new_reg()
fz, inp = T.ready(reg)
good = reg.path.read_bytes()
bad_dev = {"kind": "DEVIATION", "deviation_id": "d" * 32, "experiment_id": "EXP-0101", "informed_by": "abc"}
reg.path.write_bytes(good + json.dumps(bad_dev).encode() + b"\n")
cnt = {"n": 0}


def load_rw(self):
    cnt["n"] += 1
    if cnt["n"] == 2:
        self.path.write_bytes(good)            # destructive rewrite (violates I4/P3) between reads
    return orig_load(self)


ExperimentRegistry._load = load_rw
try:
    v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inp)
    print("result:", code(v), "tc=", v.metrics["trials_count"])
except Exception as exc:  # noqa: BLE001
    print("result: RAISED", type(exc).__name__, str(exc)[:120])
finally:
    ExperimentRegistry._load = orig_load

# ============================== QA-CR020-O4 ========================================================
section("O4 loader vs lifecycle; repeated retrieval; same config_id re-run")
reg, w = new_reg()
fz = T.frozen_experiment(reg, planned=("A", "B"), rule="PRIMARY A")
fz.begin_evaluation("A", registry=reg)
inputs = T.inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
print("VALIDATION        gate A:", C.gate(reg, w, "EXP-0101", "A")[0][:9], "| E =", reg.accounting()["E"])
T.select(reg, "EXP-0101", "A", inputs)
print("OOS_EVALUATION    gate A:", C.gate(reg, w, "EXP-0101", "A")[0][:9])
for c in ("B", "A"):
    try:
        fz.begin_evaluation(c, registry=reg)
        print(f"  register {c} in OOS_EVALUATION: SUCCESS")
    except Exception as exc:  # noqa: BLE001
        print(f"  register {c} in OOS_EVALUATION: {type(exc).__name__}")
reg.transition("EXP-0101", "REJECTED", actor="orquestador", reason="r")
for _ in range(3):
    g = C.gate(reg, w, "EXP-0101", "A")[0][:9]
print("REJECTED (terminal) gate A x3:", g, "| E =", reg.accounting()["E"], "| B gate:",
      C.gate(reg, w, "EXP-0101", "B")[0][:40])
reg2, w2 = new_reg()
fz2 = T.frozen_experiment(reg2, planned=("A",))
fz2.begin_evaluation("A", registry=reg2)
b = reg2.path.read_bytes()
fz2.begin_evaluation("A", registry=reg2)      # 'substantively modified' A: indistinguishable by design
print("re-run of same config_id: writes nothing =", reg2.path.read_bytes() == b, "| gate:",
      C.gate(reg2, w2, "EXP-0101", "A")[0][:9], "| E =", reg2.accounting()["E"],
      "| CE record fields:", sorted(k for k in reg2.records()[-2] if k != "at_utc"))

# ============================== QA-CR020-O3 (characterization only) ==============================
section("O3-P11 characterization (NEW evidence, not certification): AUTORIZA: PROCEDENCIA line variants")
reg, w = new_reg()
L = "AUTORIZA: PROCEDENCIA ANT-QA DOCUMENTADAS=1 COTA=0"
for name, text in (("exact", L + "\n"), ("trailing space", L + " \n"), ("CRLF", L + "\r\n"),
                   ("trailing NBSP U+00A0", L + " \n"), ("trailing U+3000", L + "　\n"),
                   ("U+2028 as separator", "intro " + L + "\n"), ("\\x0c as separator", "x\x0c" + L + "\n"),
                   ("U+0085 as separator", "x\u0085" + L + "\n"), ("leading space", " " + L + "\n"),
                   ("fullwidth digit", L.replace("=1", "=１") + "\n"), ("arabic-indic digit", L.replace("=1", "=١") + "\n")):
    (reg.decisions_dir / "DEC-951_v.md").write_text(text, encoding="utf-8")
    why = reg._provenance_decision_error("DEC-951_v.md", "ANT-QA", 1, 0)
    print(f"{name:24} -> {'ACCEPTED' if why is None else 'rejected'}")
