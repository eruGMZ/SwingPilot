"""Reproducción sintética de QA-CR020-03 (FEAT-017; CR-020 §C.3.2; TC-ML-023; propuesta CR-021).

Origen: sesión de corrección de QA-CR020-03 (2026-11-24), detenida por bloqueo contractual. Base de
la reproducción: `fde522c`. Artefacto de evidencia, no una prueba funcional: no forma parte de la
suite (`tests/`), no afirma nada (solo imprime lo observado) y no corrige nada.

Qué muestra (comportamiento de la base `fde522c`):
1. Par planificado con `fsync` fallando siempre: el primer intento informa persistencia incierta,
   pero los reintentos informan éxito sin ningún `fsync` correcto (sonda P4 de la QA independiente).
2. Un objeto de registro nuevo cuenta el par una sola vez y el cargador entrega Train+Val.
3. Un proceso separado ve el par en la evidencia validada (entregaría datos).
4. Configuración no planificada con fallo de `fsync` de la DEVIATION obligatoria: la DEVIATION
   queda legible y el cargador entrega datos.

Aislamiento: solo registros temporales sintéticos; no lee ni escribe el registro real, particiones
ni `docs/decisions`; no ejecuta experimentos ni llama a proveedores de IA. Reutiliza en modo lectura
los auxiliares de `tests/unit/test_qa_cr020_01.py`.

Reproducción (desde la raíz del repositorio, entorno de `scripts/setup_env.sh`):

    git checkout --detach fde522c
    .venv/bin/python -I -B harness/verification/IMPL-3_QA-CR020-03_reproduccion.py [DIRECTORIO_DE_TRABAJO]
    git status --porcelain                 # debe seguir vacío

`DIRECTORIO_DE_TRABAJO` es opcional (por defecto, `tempfile.mkdtemp()`). Este archivo se añadió
después de `fde522c`: para ejecutarlo sobre esa base, consérvelo sin seguimiento en la misma ruta.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests" / "unit")]

from swingpilot.research import experiments as X  # noqa: E402
from swingpilot.research.experiments import ExperimentRegistry  # noqa: E402
import test_qa_cr020_01 as Q  # noqa: E402  (auxiliares de preparación, solo lectura)

WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="qa-cr020-03-"))
WORK.mkdir(parents=True, exist_ok=True)
REAL_FSYNC = X.os.fsync


def reg_new():
    t = Path(tempfile.mkdtemp(dir=WORK))
    (t / "decisions").mkdir()
    return ExperimentRegistry(t / "registry.jsonl", t / "decisions"), t


def gate(reg, t, cfg):
    """Puerta del cargador con `_read` sintético: ENTREGA o DENIEGA."""
    loader = Q.loader_for(reg, t)
    try:
        loader.load_train_val_for_configuration(Q.EID, cfg)
        return "ENTREGA datos"
    except Exception:
        return "DENIEGA"


def failing(fd):
    raise OSError("EIO simulado")


print("=== 1-3. Par planificado; fsync falla en todos los intentos")
reg, t = reg_new()
fz = Q.frozen(reg)
X.os.fsync = failing
try:
    for i in range(3):
        try:
            fz.begin_evaluation("A", registry=reg)
            print(f"intento {i + 1}: ÉXITO informado con fsync fallando")
        except Exception as e:
            print(f"intento {i + 1}:", type(e).__name__)
finally:
    X.os.fsync = REAL_FSYNC
fresh = ExperimentRegistry(reg.path, reg.decisions_dir)
print("conteo (objeto nuevo):", fresh.trials_count(),
      "| líneas CONFIGURATION_EVALUATED:", sum(r["kind"] == "CONFIGURATION_EVALUATED" for r in fresh.records()))
print("cargador con objeto nuevo:", gate(fresh, t, "A"))
code = (f"import sys;sys.path[:0]=[{str(REPO / 'src')!r}];from pathlib import Path;"
        "from swingpilot.research.experiments import ExperimentRegistry as R;"
        f"r=R(Path({str(reg.path)!r}),Path({str(reg.decisions_dir)!r}));"
        "print('proceso separado: par en la evidencia validada =',('EXP-0101','A') in r.accounting()['pairs'])")
print(subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True).stdout.strip())

print("\n=== 4. Configuración no planificada; falla el fsync de la DEVIATION obligatoria")
reg, t = reg_new()
fz = Q.frozen(reg)
calls = {"n": 0}


def fail_second(fd):
    calls["n"] += 1
    if calls["n"] == 2:                      # 1.º fsync: CONFIGURATION_EVALUATED; 2.º: DEVIATION
        raise OSError("EIO simulado en el fsync de la DEVIATION")
    return REAL_FSYNC(fd)


X.os.fsync = fail_second
try:
    fz.begin_evaluation("Z", registry=reg, justification="j", informed_by=[])
except Exception as e:
    print("no planificada:", type(e).__name__)
finally:
    X.os.fsync = REAL_FSYNC
print("cargador tras DEVIATION incierta (legible):", gate(ExperimentRegistry(reg.path, reg.decisions_dir), t, "Z"))
print(f"\n(directorio de trabajo: {WORK})")
