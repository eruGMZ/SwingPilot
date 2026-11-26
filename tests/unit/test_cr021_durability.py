"""CR-021 (DEC-023; contrato v1.9): durabilidad confirmada como condición de acceso a datos.
REQ-G-104, REQ-G-P17; TC-ML-020, TC-ML-023. Origen: QA-CR020-03.

- Acceso a Train+Val solo con un EVALUATION_PERSISTED válido (escrito tras el `fsync` correcto de la
  evidencia exacta que certifica); contabilidad conservadora separada (I2a / I2b).
- Recuperación con copias byte a byte idénticas; identidades lógicas y cronología de la primera
  aparición; duplicados conflictivos → Fail-Closed.
- R2: el `fsync` fallido del marcador no impide el acceso si el marcador válido es legible; la
  operación original informa incertidumbre.
- P1–P5: un registro corrupto bloquea TODAS las rutas (lectura, escritura, acceso y evaluación),
  ninguna línea se ignora y el archivo queda intacto.

Solo registros temporales sintéticos: ningún registro real, partición real ni decisión real. Las
«pérdidas» por caída se simulan en copias sintéticas del archivo. Las pruebas solo usan interfaces
que ya existían en la base `f48114c`, para que sus fallos con esa base sean de comportamiento.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from consumption_helpers import ok_consumption_check  # noqa: E402
import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research import partitions as P  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
from swingpilot.research.partitions import FinalEvaluationGrant, PartitionAccessError, PartitionLoader  # noqa: E402
from swingpilot.research.preregistration import confirmatory_status, freeze  # noqa: E402
from test_cr023_b3_preregistration import cr023_fields, freeze_in_registry, store_for  # noqa: E402  (CR-023)
from swingpilot.research.trials import reconcile  # noqa: E402

WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}
X1, Y1 = "EXP-0101", "EXP-0102"


# --- preparación -------------------------------------------------------------------------------

@pytest.fixture
def reg(tmp_path):
    dec = tmp_path / "decisions"
    dec.mkdir()
    (dec / "DEC-900_ok.md").write_text("AUTORIZA: EXP-0101 OOS_EVALUATION\nAUTORIZA: EXP-0101 oos SNAP-TEST\n")
    (dec / "DEC-950_p.md").write_text("AUTORIZA: PROCEDENCIA ANT-QA DOCUMENTADAS=1 COTA=0\n"
                                      "AUTORIZA: PROCEDENCIA ANT-QA DOCUMENTADAS=0 COTA=0\n")
    return ExperimentRegistry(tmp_path / "registry.jsonl", dec)


def frozen(reg, eid=X1, planned=("A",)):
    reg.create(eid, "x", actor="orquestador")
    reg.transition(eid, "DESIGN", actor="orquestador")
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "model_config", "data_split",
                               "costs", "acceptance_criteria", "rejection_criteria", "limitations",
                               "execution_model", "regime_declaration", "sharpe_definition")}
    p.update(experiment_id=eid, timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1,
             antecedents=["-"], statistical_tests={"dsr_min_probability": 0.95},
             metrics=["sharpe"], trials_count=reg.trials_accounting(eid, list(planned)),
             candidate_selection_rule=f"PRIMARY {planned[0]}")
    p.update(cr023_fields(planned))                                # CR-023 §C.5
    fz = freeze(p)
    freeze_in_registry(reg, fz)                                    # CR-023: almacén + clase + freeze_check
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        reg.transition(eid, st, actor="orquestador", evidence=ev)
    return fz


def inputs_for(eid, results):
    return json.dumps({"experiment_id": eid, "results": results}, sort_keys=True).encode()


def select(reg, eid, cfg, inputs):
    reg.transition(eid, "OOS_EVALUATION", actor="propietario",
                   evidence={"decision_ref": "DEC-900_ok.md", "selected_config_id": cfg,
                             "selection_inputs_sha256": hashlib.sha256(inputs).hexdigest(), "informed_by": []})


def evidence():
    net = list(np.random.default_rng(3).normal(0.6, 1.0, 40))
    eq = list(np.cumprod([1.0] + [1 + 0.01 * x for x in net]))
    rets = list(np.diff(eq) / np.array(eq[:-1]))
    return A.ExperimentEvidence(trades={"train_val": 120, "oos": len(net), "lockbox": 35}, oos_net_r=net,
                                oos_equity=eq, oos_period_returns=rets, periods_per_year=52,
                                sr_variance_across_trials=0.01, buy_and_hold_report={"return": 0.3},
                                baseline_beaten=True, dsr_min_probability=0.95,
                                bootstrap={"n_resamples": 2000, "seed": 7, "block_size": 1})


def fsync_policy(monkeypatch, fail):
    """Sustituye `os.fsync` del registro: `fail(n)` decide si la n-ésima llamada falla (EIO)."""
    real, calls = X.os.fsync, {"n": 0}

    def fsync(fd):
        calls["n"] += 1
        if fail(calls["n"]):
            raise OSError(5, "EIO simulado")
        return real(fd)
    monkeypatch.setattr(X.os, "fsync", fsync)
    return calls


def gate(reg, tmp, eid=X1, cfg="A"):
    """Puerta del cargador de Train+Val con `_read` sintético: (resultado, motivo, lecturas)."""
    loader = PartitionLoader.__new__(PartitionLoader)
    loader.registry, loader.access_log = reg, Path(tmp) / f"access-{eid}-{cfg}.jsonl"
    loader.prereg_store = store_for(reg)                           # CR-023 §C.3.3
    loader.manifest = {"snapshot_id": "SNAP-TEST", "kind": "development"}
    reads = []
    loader._read = lambda part: reads.append(part) or pd.DataFrame({"interval": ["1d"]})
    try:
        loader.load_train_val_for_configuration(eid, cfg)
        return "DELIVERED", None, reads
    except PartitionAccessError as exc:
        assert loader.access_history()[-1]["allowed"] is False
        return "DENIED", str(exc), reads


def proc_gate(reg, eid=X1, cfg="A"):
    """La misma puerta desde un proceso separado (sin estado compartido salvo el archivo)."""
    code = (f"import sys;sys.path.insert(0,{str(SRC)!r});from pathlib import Path;import pandas as pd;"
            "from swingpilot.research.experiments import ExperimentRegistry as R;"
            "from swingpilot.research.partitions import PartitionLoader as L;"
            "from swingpilot.research.prereg_store import PreregistrationStore as S;"
            f"r=R(Path({str(reg.path)!r}),Path({str(reg.decisions_dir)!r}));l=L.__new__(L);l.registry=r;"
            f"l.prereg_store=S(Path({str(reg.path.parent / 'preregistrations')!r}));"
            f"l.access_log=Path({str(reg.path.parent / 'proc-access.jsonl')!r});l.manifest={{'snapshot_id':'SNAP-TEST','kind':'development'}};"
            "l._read=lambda p: pd.DataFrame({'interval':['1d']})\n"
            f"try:\n l.load_train_val_for_configuration({eid!r},{cfg!r});print('DELIVERED')\n"
            "except Exception:\n print('DENIED')")
    out = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def kinds(reg, eid=X1, cfg="A"):
    return [r["kind"] for r in reg.records() if r.get("experiment_id") == eid and r.get("config_id") == cfg]


def lines_of(reg, kind, eid=X1, cfg="A"):
    return [ln for ln, r in zip(reg.path.read_bytes().splitlines(), reg.records())
            if r["kind"] == kind and r.get("experiment_id") == eid and r.get("config_id") == cfg]


def copy_without(reg, tmp, name, drop):
    """Copia sintética del archivo sin las líneas cuyo índice cumpla `drop(i, rec)` (pérdida simulada)."""
    raw = reg.path.read_bytes().splitlines()
    kept = [ln for i, (ln, r) in enumerate(zip(raw, reg.records())) if not drop(i, r)]
    path = Path(tmp) / name
    path.write_bytes(b"".join(ln + b"\n" for ln in kept))
    return ExperimentRegistry(path, reg.decisions_dir)


# --- P4 y fallos repetidos del fsync de la evidencia ------------------------------------------

def test_p4_repeated_fsync_failures_never_report_success_nor_grant_access(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: True)                     # el almacenamiento falla siempre
    outcomes = []
    for _ in range(3):
        try:
            reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
            outcomes.append("SUCCESS")
        except Exception as exc:
            outcomes.append(type(exc).__name__)
    monkeypatch.undo()
    assert outcomes == ["PersistenceUncertainError"] * 3          # base: 1 incierto y 2 éxitos falsos (P4)
    assert reg.trials_count() == 1                                 # legible: cuenta una vez (I2b)
    assert "EVALUATION_PERSISTED" not in kinds(reg)
    fresh = ExperimentRegistry(reg.path, reg.decisions_dir)
    assert gate(reg, tmp_path)[0] == gate(fresh, tmp_path)[0] == "DENIED"
    assert proc_gate(reg) == "DENIED"


def test_readable_record_after_fsync_failure_counts_once_but_grants_no_access(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: n == 1)
    with pytest.raises(Exception, match="incierta"):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    assert reg.trials_count() == 1 and len(lines_of(reg, "CONFIGURATION_EVALUATED")) == 1
    result, reason, reads = gate(ExperimentRegistry(reg.path, reg.decisions_dir), tmp_path)
    assert result == "DENIED" and reads == [] and "EVALUATION_PERSISTED" in reason
    assert proc_gate(reg) == "DENIED"


# --- conciliación duradera ---------------------------------------------------------------------

def test_durable_reconciliation_writes_identical_copy_and_marker_without_double_count(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: n <= 2)                   # dos intentos fallidos
    for _ in range(2):
        with pytest.raises(Exception):
            reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    reg.begin_configuration_evaluation(X1, "A", actor="orquestador")             # reintento con éxito
    ce = lines_of(reg, "CONFIGURATION_EVALUATED")
    assert len(ce) == 3 and len(set(ce)) == 1                     # copias byte a byte idénticas
    assert reg.trials_count() == 1 and kinds(reg).count("EVALUATION_PERSISTED") == 1
    marker = [r for r in reg.records() if r["kind"] == "EVALUATION_PERSISTED"][0]
    assert marker["certifies"] == [{"kind": "CONFIGURATION_EVALUATED",
                                    "line_sha256": hashlib.sha256(ce[0]).hexdigest()}]
    assert gate(ExperimentRegistry(reg.path, reg.decisions_dir), tmp_path)[0] == "DELIVERED"
    assert proc_gate(reg) == "DELIVERED"
    before = reg.path.read_bytes()
    reg.begin_configuration_evaluation(X1, "A", actor="orquestador")             # certificado: sin escribir
    assert reg.path.read_bytes() == before


# --- DEVIATION obligatoria incierta ------------------------------------------------------------

def test_uncertain_mandatory_deviation_blocks_access_until_both_are_certified(reg, tmp_path, monkeypatch):
    fz = frozen(reg)
    fsync_policy(monkeypatch, lambda n: n == 1)
    with pytest.raises(Exception, match="incierta"):
        fz.begin_evaluation("Z", registry=reg, justification="exploración", informed_by=[])
    monkeypatch.undo()
    assert kinds(reg, cfg="Z") == ["CONFIGURATION_EVALUATED", "DEVIATION"]       # legibles, no confirmadas
    assert gate(reg, tmp_path, cfg="Z")[0] == "DENIED" and proc_gate(reg, cfg="Z") == "DENIED"
    dev_id = [r for r in reg.records() if r["kind"] == "DEVIATION"][0]["deviation_id"]
    fz.begin_evaluation("Z", registry=reg, justification="conciliación", informed_by=[])
    devs = lines_of(reg, "DEVIATION", cfg="Z")
    assert len(devs) == 2 and devs[0] == devs[1]                  # copia idéntica, mismo deviation_id
    assert [d["deviation_id"] for d in confirmatory_status(reg, X1)["deviations"]] == [dev_id]   # una lógica
    marker = [r for r in reg.records() if r["kind"] == "EVALUATION_PERSISTED"][0]
    assert {c["kind"] for c in marker["certifies"]} == {"CONFIGURATION_EVALUATED", "DEVIATION"}
    assert [c["deviation_id"] for c in marker["certifies"] if c["kind"] == "DEVIATION"] == [dev_id]
    assert reg.trials_count() == 1 and gate(reg, tmp_path, cfg="Z")[0] == "DELIVERED"


# --- R2: fsync del marcador fallido ------------------------------------------------------------

def test_r2_marker_fsync_failure_reports_uncertainty_but_certified_evidence_grants_access(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: n == 2)                   # evidencia correcta; falla el del marcador
    with pytest.raises(Exception, match="marcador"):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"]     # marcador legible y válido
    assert gate(ExperimentRegistry(reg.path, reg.decisions_dir), tmp_path)[0] == "DELIVERED"   # otro objeto
    assert proc_gate(reg) == "DELIVERED"                                                      # otro proceso
    before = reg.path.read_bytes()
    reg.begin_configuration_evaluation(X1, "A", actor="orquestador")             # reintento: éxito sin escribir
    assert reg.path.read_bytes() == before


def test_r2_lost_marker_denies_access_keeps_count_and_retry_recertifies(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: n == 2)
    with pytest.raises(Exception):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    lost = copy_without(reg, tmp_path, "lost-marker.jsonl", lambda i, r: r["kind"] == "EVALUATION_PERSISTED")
    assert lost.trials_count() == 1                                # la evaluación duradera sigue contando
    assert gate(lost, tmp_path)[0] == "DENIED" and proc_gate(lost) == "DENIED"
    lost.begin_configuration_evaluation(X1, "A", actor="orquestador")
    assert kinds(lost) == ["CONFIGURATION_EVALUATED", "CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"]
    assert lost.trials_count() == 1 and gate(lost, tmp_path)[0] == "DELIVERED"


# --- I2a / I2b: pérdidas simuladas -------------------------------------------------------------

def test_i2b_unconfirmed_attempt_lost_before_any_freeze_is_not_detected(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: True)
    with pytest.raises(Exception):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    assert reg.trials_count() == 1
    lost = copy_without(reg, tmp_path, "lost-attempt.jsonl", lambda i, r: r["kind"] == "CONFIGURATION_EVALUATED")
    assert lost.trials_count() == 0                                # pérdida admitida y no detectada (CR-021 §F.8)


def test_i2b_unconfirmed_attempt_lost_after_a_freeze_counted_it_is_inconclusive(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: True)
    with pytest.raises(Exception):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    fy = frozen(reg, Y1, ("B",))                                   # Y congela contando el intento de X
    assert fy.content["trials_count"]["E"] == 1
    lost = copy_without(reg, tmp_path, "lost-counted.jsonl",
                        lambda i, r: r["kind"] == "CONFIGURATION_EVALUATED" and r["experiment_id"] == X1)
    rec = reconcile(lost, fy, None)
    assert not rec["ok"] and any("TRIALS_COUNT_INCONSISTENT" in r for r in rec["reasons"])


def test_i2a_authorized_evaluation_survives_loss_of_its_unconfirmed_original(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: n == 1)
    with pytest.raises(Exception):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    reg.begin_configuration_evaluation(X1, "A", actor="orquestador")             # copia certificada
    first = next(i for i, r in enumerate(reg.records()) if r["kind"] == "CONFIGURATION_EVALUATED")
    lost = copy_without(reg, tmp_path, "lost-original.jsonl", lambda i, r: i == first)
    assert lost.trials_count() == 1 and gate(lost, tmp_path)[0] == "DELIVERED"


# --- concurrencia ------------------------------------------------------------------------------

def _race(reg, n=6):
    code = (f"import sys;sys.path.insert(0,{str(SRC)!r});from pathlib import Path;"
            "from swingpilot.research.experiments import ExperimentRegistry as R;"
            f"R(Path({str(reg.path)!r}),Path({str(reg.decisions_dir)!r})).begin_configuration_evaluation("
            f"{X1!r},'A',actor='p')")
    procs = [subprocess.Popen([sys.executable, "-I", "-B", "-c", code]) for _ in range(n)]
    return [p.wait(timeout=60) for p in procs]


def test_concurrent_starts_produce_one_logical_evaluation_and_one_marker(reg, tmp_path):
    frozen(reg)
    assert _race(reg) == [0] * 6
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"] and reg.trials_count() == 1
    assert gate(reg, tmp_path)[0] == "DELIVERED"


def test_concurrent_recovery_writes_one_copy_and_one_marker(reg, tmp_path, monkeypatch):
    frozen(reg)
    fsync_policy(monkeypatch, lambda n: True)
    with pytest.raises(Exception):
        reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    monkeypatch.undo()
    assert _race(reg) == [0] * 6
    assert kinds(reg) == ["CONFIGURATION_EVALUATED", "CONFIGURATION_EVALUATED", "EVALUATION_PERSISTED"]
    assert reg.trials_count() == 1


# --- P1–P5: corrupción en todas las rutas --------------------------------------------------------

def _base(tmp_path, reg):
    reg.register_antecedent("ANT-QA", "antecedente sintético", "REJECTED", source="s", note="n")
    prov = reg.register_provenance("ANT-QA", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                                   configurations=[{"config_id": "A", "evidence_class": "DOCUMENTED_EVALUATED"}],
                                   evidence=["tb@abc1234:a.md"], decision_ref="DEC-950_p.md", supersedes=None)
    fz = frozen(reg)
    fz.begin_evaluation("A", registry=reg)
    fz.record_deviation("limitations", "nota", "aclaración", registry=reg, informed_by=[])
    inputs = inputs_for(X1, {"A": {"sharpe": 1.0}})
    select(reg, X1, "A", inputs)
    return fz, inputs, prov


def _middle(raw: bytes, line: bytes) -> bytes:
    lines = raw[:-1].split(b"\n")
    lines.insert(len(lines) // 2, line)
    return b"\n".join(lines) + b"\n"


def _variant(raw: bytes, recs: list, kind: str, change: dict) -> bytes:
    line = raw[:-1].split(b"\n")[next(i for i, r in enumerate(recs) if r["kind"] == kind)]
    return raw + json.dumps({**json.loads(line), **change}, ensure_ascii=False, sort_keys=True).encode() + b"\n"


CORRUPTIONS = {
    "truncated_tail": lambda raw, recs: raw + b'{"kind": "CONFIGURATION_EVAL',
    "no_final_newline": lambda raw, recs: raw + b'{"kind": "NOTE"}',
    "invalid_middle_line": lambda raw, recs: _middle(raw, b"{corrupto"),
    "blank_middle_line": lambda raw, recs: _middle(raw, b""),
    "non_object_line": lambda raw, recs: raw + b"[1, 2]\n",
    "conflicting_evaluation": lambda raw, recs: _variant(raw, recs, "CONFIGURATION_EVALUATED", {"actor": "otro"}),
    "conflicting_deviation": lambda raw, recs: _variant(raw, recs, "DEVIATION", {"justification": "otra"}),
    "unbindable_marker": lambda raw, recs: _variant(
        raw, recs, "EVALUATION_PERSISTED",
        {"marker_id": "f" * 32, "certifies": [{"kind": "CONFIGURATION_EVALUATED", "line_sha256": "0" * 64}]}),
    "duplicate_marker_id": lambda raw, recs: raw + raw[:-1].split(b"\n")[
        next(i for i, r in enumerate(recs) if r["kind"] == "EVALUATION_PERSISTED")] + b"\n",
}


def _paths(reg, fz, inputs, prov, tmp_path, monkeypatch):
    """Todas las rutas de TC-ML-023 (P1): cada una devuelve el texto del fallo cerrado."""
    def raised(fn):
        try:
            out = fn()
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"
        return f"NO FALLÓ: {out!r}"

    def final_loader():
        monkeypatch.setattr(P, "enforce_sealing", lambda *a, **k: None)   # aísla la puerta del registro
        loader = PartitionLoader.__new__(PartitionLoader)
        loader.registry, loader.access_log, loader.owner = reg, tmp_path / "final.jsonl", "propietario"
        loader.manifest = {"snapshot_id": "SNAP-TEST", "files": {}, "range": {"last_open_time_ms": 0}}
        loader.data_dir = tmp_path
        loader._read = lambda part: (_ for _ in ()).throw(AssertionError("leyó datos"))
        loader.load_final(FinalEvaluationGrant(X1, "oos", "SNAP-TEST", "propietario", "DEC-900_ok.md"), "oos")

    def train_val():
        result, reason, reads = gate(reg, tmp_path)
        assert reads == []
        if result == "DENIED":
            raise PermissionError(reason)
        return result

    def evaluator():
        v = A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs)
        assert v.outcome != "ELIGIBLE_FOR_HUMAN_REVIEW"
        raise RuntimeError(f"{v.outcome}: {v.reasons}")

    return {
        "read.records": raised(reg.records),
        "read.accounting": raised(reg.trials_count),
        "read.confirmatory_status": raised(lambda: confirmatory_status(reg, X1)),
        "write.create": raised(lambda: reg.create("EXP-0109", "x", actor="o")),
        "write.register_antecedent": raised(lambda: reg.register_antecedent("ANT-NEW", "t", "REJECTED", source="s",
                                                                            note="n")),
        "write.transition": raised(lambda: reg.transition(X1, "AUDIT", actor="orquestador")),
        "write.register_provenance": raised(lambda: reg.register_provenance(
            "ANT-QA", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
            configurations=[{"config_id": "A", "evidence_class": "DOCUMENTED_NOT_EVALUATED"}],
            evidence=["tb@abc1234:a.md"], decision_ref="DEC-950_p.md", supersedes=prov["provenance_id"])),
        "write.begin_evaluation": raised(lambda: reg.begin_configuration_evaluation(X1, "A", actor="o")),
        "write.record_deviation": raised(lambda: fz.record_deviation("limitations", "y", "z", registry=reg,
                                                                     informed_by=[])),
        "write.claim_partition": raised(lambda: reg.claim_partition(
            snapshot_id="SNAP-TEST", partition="oos", experiment_id=X1, snapshot_last_open_time=0,
            decision_ref="DEC-900_ok.md", consumption_check=ok_consumption_check())),
        "access.train_val": raised(train_val),
        "access.oos_lockbox": raised(final_loader),
        "evaluation.evaluate": raised(evaluator),
    }


def test_p1_control_clean_registry_allows_every_path(reg, tmp_path, monkeypatch):
    """Control: sin corrupción, las mismas rutas no fallan por el registro (la puerta funciona)."""
    fz, inputs, _ = _base(tmp_path, reg)
    assert gate(reg, tmp_path)[0] == "DELIVERED"
    assert A.evaluate(evidence(), reg, preregistration=fz, selection_inputs=inputs).outcome == \
        "ELIGIBLE_FOR_HUMAN_REVIEW"
    st = confirmatory_status(reg, X1, preregistration=fz, selection_inputs=inputs)   # QA-CR020-02: entradas de verificación
    assert reg.trials_count() == 2 and len(st["deviations"]) == 1


@pytest.mark.parametrize("corruption", sorted(CORRUPTIONS))
def test_p1_corruption_blocks_every_path_skips_no_line_and_preserves_the_file(reg, tmp_path, monkeypatch,
                                                                              corruption):
    fz, inputs, prov = _base(tmp_path, reg)
    corrupt = CORRUPTIONS[corruption](reg.path.read_bytes(), reg.records())
    reg.path.write_bytes(corrupt)
    results = _paths(reg, fz, inputs, prov, tmp_path, monkeypatch)
    not_closed = {k: v for k, v in results.items() if "registro corrupto" not in v}
    assert not_closed == {}, not_closed                            # P1 + P2: todas fallan por la corrupción
    assert reg.path.read_bytes() == corrupt                        # P3/P4: archivo intacto, sin reparación


def test_identical_evaluation_copy_is_one_logical_record(reg):
    frozen(reg)
    reg.begin_configuration_evaluation(X1, "A", actor="orquestador")
    line = lines_of(reg, "CONFIGURATION_EVALUATED")[0]
    with open(reg.path, "ab") as fh:
        fh.write(line + b"\n")
    assert reg.trials_count() == 1 and len(lines_of(reg, "CONFIGURATION_EVALUATED")) == 2
