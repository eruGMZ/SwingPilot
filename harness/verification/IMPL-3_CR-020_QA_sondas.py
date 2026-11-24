"""Sondas sintéticas de la QA independiente de CR-020 (FEAT-017; P1–P11).

Origen: verificación independiente de CR-020 (2026-11-24), informe
`harness/verification/IMPL-3_CR-020_QA_independiente.md`. Base verificada: `f2f05a9`.
Es un artefacto de evidencia, no una prueba funcional: no forma parte de la suite (`tests/`),
no afirma nada (solo imprime lo observado) y no corrige nada.

Aislamiento:
- Solo registros temporales y decisiones sintéticas en un directorio de trabajo temporal.
- No lee ni escribe el registro real (`research/experiments/registry.jsonl`), ni particiones,
  ni `docs/decisions`; no ejecuta experimentos ni llama a proveedores de IA.
- Reutiliza en modo lectura los auxiliares de `tests/unit/test_trials_accounting.py`.

Reproducción (desde la raíz del repositorio, con el entorno de `scripts/setup_env.sh`):

    git checkout --detach f2f05a9          # o cualquier árbol idéntico a esa base
    .venv/bin/python -I -B harness/verification/IMPL-3_CR-020_QA_sondas.py [DIRECTORIO_DE_TRABAJO]

- `-I` aísla el intérprete; `-B` evita escribir `__pycache__` en el repositorio.
- `DIRECTORIO_DE_TRABAJO` es opcional; por defecto se crea uno nuevo con `tempfile.mkdtemp()`.
- Tras ejecutar, `git status --porcelain` debe seguir vacío.
- Los resultados esperados con `f2f05a9` están en el informe, §4.
"""
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests" / "unit"))

from swingpilot.research import acceptance as A  # noqa: E402
from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry, PersistenceUncertainError  # noqa: E402
from swingpilot.research.preregistration import confirmatory_status, freeze  # noqa: E402
from swingpilot.research.trials import reconcile  # noqa: E402
import test_trials_accounting as T  # noqa: E402  (auxiliares de preparación, solo lectura)

WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="qa-cr020-"))
WORK.mkdir(parents=True, exist_ok=True)


def new_reg():
    """Registro temporal aislado con decisiones sintéticas (nunca docs/decisions)."""
    tmp = Path(tempfile.mkdtemp(dir=WORK))
    dec = tmp / "decisions"
    dec.mkdir()
    lines = [f"AUTORIZA: {e} {s}" for e in ("EXP-0101", "EXP-0102", "EXP-0103") for s in ("OOS_EVALUATION", "APPROVED")]
    (dec / "DEC-900_ok.md").write_text("\n".join(lines) + "\n")
    (dec / T.PROV_DEC).write_text("AUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=4 COTA=0\n"
                                  "AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4\n")
    return ExperimentRegistry(tmp / "registry.jsonl", dec), tmp


def probe(name):
    def deco(fn):
        print(f"\n=== {name}")
        try:
            fn()
        except Exception:
            traceback.print_exc(limit=3)
        return fn
    return deco


@probe("P1 configuración no planificada con informed_by no verificable: ¿registro escrito antes de validar la DEVIATION?")
def _p1():
    reg, _ = new_reg()
    fz = T.frozen_experiment(reg, planned=("A",))
    try:
        fz.begin_evaluation("Z", registry=reg, justification="j",
                            informed_by=[{"experiment_id": "EXP-0199", "config_id": "Q"}])
        print("sin excepción")
    except Exception as e:
        print("excepción:", type(e).__name__, str(e)[:110])
    kinds = [(r["kind"], r.get("config_id")) for r in reg.records() if r["kind"] in ("CONFIGURATION_EVALUATED", "DEVIATION")]
    print("registros:", kinds, "| pares en la contabilidad validada:", list(reg.accounting()["pairs"]))
    print("confirmatory_status.confirmatory =", confirmatory_status(reg, "EXP-0101")["confirmatory"])


@probe("P2 configuración no planificada válida (con DEVIATION): confirmatory_status frente al evaluador")
def _p2():
    reg, _ = new_reg()
    fz = T.frozen_experiment(reg, planned=("A",))
    fz.begin_evaluation("A", registry=reg)
    fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
    st = confirmatory_status(reg, "EXP-0101")
    print("confirmatory_status.confirmatory =", st["confirmatory"], "| desviaciones:", [d["field"] for d in st["deviations"]])
    inputs = T.inputs_for("EXP-0101", {"A": {"sharpe": 1.0}, "Z": {"sharpe": 2.0}})
    T.select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inputs)
    print("evaluador:", v.outcome, v.reasons[:1])


@probe("P3 selección fuera de la regla congelada: confirmatory_status frente al evaluador")
def _p3():
    reg, _ = new_reg()
    res = {"A": {"sharpe": 0.5}, "B": {"sharpe": 1.2}}
    fz, inputs = T.ready(reg, planned=("A", "B"), rule="ARGMAX sharpe TIEBREAK A,B", results=res, sel="A")
    print("confirmatory_status.confirmatory =", confirmatory_status(reg, "EXP-0101")["confirmatory"])
    v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inputs)
    print("evaluador:", v.outcome, [r[:40] for r in v.reasons])


@probe("P4 fallo de fsync: cargador antes del reintento y reintento sin ningún fsync correcto")
def _p4():
    reg, _ = new_reg()
    T.frozen_experiment(reg)
    calls = {"n": 0}
    real = X.os.fsync

    def bad(fd):
        calls["n"] += 1
        raise OSError("EIO simulado")
    X.os.fsync = bad
    try:
        try:
            reg.begin_configuration_evaluation("EXP-0101", "A", actor="o")
        except PersistenceUncertainError as e:
            print("primera llamada:", type(e).__name__)
        # mismo predicado que load_train_val_for_configuration, ANTES de cualquier reintento
        print("la puerta del cargador entregaría datos antes del reintento:", ("EXP-0101", "A") in reg.accounting()["pairs"])
        rec = reg.begin_configuration_evaluation("EXP-0101", "A", actor="o")   # fsync sigue fallando
        print("el reintento devuelve éxito con fsync fallando:", rec["kind"], "| intentos de fsync:", calls["n"])
    finally:
        X.os.fsync = real


@probe("P5 prueba posterior: la selección cita (Y,YB) pero no (Y,YA) -> clasificación de (Y,YA)")
def _p5():
    reg, _ = new_reg()
    fx = T.frozen_experiment(reg, "EXP-0101", planned=("A",))
    fx.begin_evaluation("A", registry=reg)
    fy = T.frozen_experiment(reg, "EXP-0102", planned=("YA", "YB"), rule="PRIMARY YA")
    fy.begin_evaluation("YA", registry=reg)
    fy.begin_evaluation("YB", registry=reg)
    inputs = T.inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    T.select(reg, "EXP-0101", "A", inputs, informed_by=[{"experiment_id": "EXP-0102", "config_id": "YB"}])
    rec = reconcile(reg, fx, inputs)
    print("ok", rec["ok"], "N_pre", rec["N_pre"], "N_eval", rec["N_eval"], "relevant", rec["relevant"],
          "after_freeze", rec["trials_after_freeze"])


@probe("P6 línea JSON válida que no es un objeto: ¿evaluate() devuelve INCONCLUSIVE o lanza?")
def _p6():
    reg, _ = new_reg()
    fz, inputs = T.ready(reg)
    with open(reg.path, "a") as fh:
        fh.write("[1, 2]\n")
    try:
        v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inputs)
        print("evaluador:", v.outcome, v.reasons[:1])
    except Exception as e:
        print("evaluate() lanzó:", type(e).__name__, e)
    try:
        reg.begin_configuration_evaluation("EXP-0101", "A", actor="o")
    except Exception as e:
        print("begin_configuration_evaluation:", type(e).__name__)


@probe("P7 congelación por transición directa con trials_accounting distinto del contenido del preregistro")
def _p7():
    reg, _ = new_reg()
    reg.create("EXP-0101", "x", actor="o")
    reg.transition("EXP-0101", "DESIGN", actor="o")
    fz = freeze(T.content(reg, planned=("A", "B"), rule="PRIMARY A"))
    reg.transition("EXP-0101", "PREREGISTERED", actor="o", evidence={
        "preregistration_sha256": fz.sha256, "min_history_ok": True,
        "trials_accounting": reg.trials_accounting("EXP-0101", ["A"])})   # coherente con el registro, ≠ contenido
    for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
        reg.transition("EXP-0101", st, actor="o", evidence=ev)
    fz.begin_evaluation("A", registry=reg)
    inputs = T.inputs_for("EXP-0101", {"A": {"sharpe": 1.0}})
    T.select(reg, "EXP-0101", "A", inputs)
    v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inputs)
    print("evaluador:", v.outcome, v.reasons[:1])


@probe("P8 documento de decisión eliminado tras la congelación -> Fail-Closed")
def _p8():
    reg, tmp = new_reg()
    T.historical(reg)
    fz, inputs = T.ready(reg)
    (tmp / "decisions" / T.PROV_DEC).unlink()
    v = A.evaluate(T.evidence(), reg, preregistration=fz, selection_inputs=inputs)
    print("evaluador:", v.outcome, v.reasons[0][:60])


@probe("P9 concurrencia: 6 procesos inician el mismo par -> exactamente un registro")
def _p9():
    reg, tmp = new_reg()
    T.frozen_experiment(reg, planned=("A",))
    code = (f"import sys;sys.path.insert(0,{str(REPO / 'src')!r});from pathlib import Path;"
            f"from swingpilot.research.experiments import ExperimentRegistry as R;"
            f"r=R(Path({str(reg.path)!r}),Path({str(tmp / 'decisions')!r}));"
            f"r.begin_configuration_evaluation('EXP-0101','A',actor='p')")
    ps = [subprocess.Popen([sys.executable, "-I", "-B", "-c", code]) for _ in range(6)]
    print("códigos de salida:", [p.wait() for p in ps],
          "| líneas CONFIGURATION_EVALUATED:", sum(r["kind"] == "CONFIGURATION_EVALUATED" for r in reg.records()))


@probe("P10 procedencia: reducción que reutiliza la misma lista de evidencia")
def _p10():
    reg, tmp = new_reg()
    mr, _ = T.historical(reg)
    (tmp / "decisions" / "DEC-951_r.md").write_text("AUTORIZA: PROCEDENCIA ANT-MR-H1 DOCUMENTADAS=3 COTA=0\n")
    cf = T._cfgs(["A", "B", "E1"], "DOCUMENTED_EVALUATED") + T._cfgs(["E2"], "DOCUMENTED_NOT_EVALUATED")
    reg.register_provenance("ANT-MR-H1", documentary_status="DOCUMENTED", execution_status="DOCUMENTED_EXECUTED",
                            configurations=cf, evidence=T.EV_MR, decision_ref="DEC-951_r.md",
                            supersedes=mr["provenance_id"])
    print("reducción aceptada con la MISMA evidencia; G =", reg.trials_count())


@probe("P11 espacio final / CRLF en la línea AUTORIZA: PROCEDENCIA")
def _p11():
    reg, tmp = new_reg()
    reg.register_antecedent("EXP-0001", "t", "PENDING_DOCUMENTATION", source="s", note="n")
    (tmp / "decisions" / "DEC-952_p.md").write_bytes(b"AUTORIZA: PROCEDENCIA EXP-0001 DOCUMENTADAS=0 COTA=4 \r\n")
    try:
        reg.register_provenance("EXP-0001", documentary_status="DOCUMENTED", execution_status="UNKNOWN",
                                configurations=T._cfgs(list("ABCD"), "CONSERVATIVE_BOUND"), evidence=T.EV_TF,
                                decision_ref="DEC-952_p.md", supersedes=None)
        print("aceptada (se tolera el espacio final, como en la gramática de QA3R2-04)")
    except Exception as e:
        print("rechazada:", e)


print(f"\n(directorio de trabajo: {WORK})")
