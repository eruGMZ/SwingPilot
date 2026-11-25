"""Prepara un registro sintético y un preregistro serializado para la traza strace (CR-021).
Uso: python -I -B prepare_strace.py <directorio_de_trabajo_nuevo>"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

w = Path(sys.argv[1])
reg = C.new_reg(w)
fz = C.D.frozen(reg)
fz._registry = None
(w / "fz.pkl").write_bytes(pickle.dumps(fz))
