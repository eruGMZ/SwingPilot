"""CLI de la snapshot (FEAT-015). Herramienta manual; nada se ejecuta automáticamente.

    python -m swingpilot.research.cli build-snapshot --id SNAP-0001 --d-dev 2024-01-01 --confirm
    python -m swingpilot.research.cli verify-snapshot --id SNAP-0001

`build-snapshot` construye la snapshot de DESARROLLO [2017-08-17, D_dev) (CR-023): descarga datos
públicos de Binance (sin credenciales ni costo de API) y fija para siempre `D_dev` y el corte
Train:Validation 5:2; por eso exige `--d-dev` y `--confirm`. Antes de descargar obtiene las
ventanas reservadas activas de un proveedor; la fuente autoritativa de esas ventanas está
pendiente (B5), de modo que hoy el proveedor falla y el comando termina con código 1 sin descargar.
`verify-snapshot` es sensible a `kind`: en desarrollo recalcula el SHA-256 de `train_val`; en
evaluación solo comprueba el sellado (los archivos sellados no se leen).
El identificador debe ser SNAP-NNNN.
"""
import argparse
import re
import sys
import warnings
from pathlib import Path

from swingpilot.market_data import BinancePublicClient

from .snapshot import SealingError, SealingWarning, SnapshotError, build_snapshot, verify_snapshot

REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO / "var" / "snapshots"          # fuera de Git (DEC-017 Q46)
MANIFEST_DIR = REPO / "research" / "snapshots"  # en el repositorio
CLI_SNAPSHOT_ID = re.compile(r"SNAP-[0-9]{4}")   # con fullmatch; SNAP-TEST* solo en pruebas (QA3R2-08)


def reserved_windows_provider() -> list:
    """Ventanas reservadas ACTIVAS para `build_snapshot`. La fuente autoritativa no existe todavía
    (B5): falla cerrado en lugar de suponer que no hay ventanas."""
    raise SnapshotError("fuente autoritativa de ventanas reservadas pendiente (B5)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="swingpilot.research.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-snapshot")
    b.add_argument("--id", required=True)
    b.add_argument("--d-dev", required=True, dest="d_dev", help="YYYY-MM-DD (UTC, exclusivo)")
    b.add_argument("--confirm", action="store_true")
    v = sub.add_parser("verify-snapshot")
    v.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    if not CLI_SNAPSHOT_ID.fullmatch(a.id):
        print(f"identificador no válido: {a.id!r} (formato SNAP-NNNN)", file=sys.stderr)
        return 2
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", SealingWarning)
        try:
            code = _run(a)
        except SealingError as exc:                     # QA3R2-08: bloqueo explícito
            print(f"ERROR de sellado: {exc}", file=sys.stderr)
            code = 1
        except SnapshotError as exc:
            print(f"ERROR de snapshot: {exc}", file=sys.stderr)
            code = 1
    resealed = [str(w.message) for w in caught if issubclass(w.category, SealingWarning)]
    for note in resealed:
        print(f"AVISO de sellado: {note}", file=sys.stderr)
    return 1 if resealed and a.cmd == "verify-snapshot" else code


def _run(a) -> int:
    if a.cmd == "build-snapshot":
        if not a.confirm:
            print("build-snapshot fija las particiones de forma permanente: repetir con --confirm", file=sys.stderr)
            return 2
        windows = reserved_windows_provider()                          # antes de cualquier descarga
        res = build_snapshot(BinancePublicClient(), a.id, DATA_ROOT, MANIFEST_DIR, d_dev=a.d_dev,
                             reserved_windows=windows)
        print(f"snapshot {a.id}: manifiesto {res.manifest_path}")
        for part, info in res.manifest["files"].items():
            print(f"  {part}: {info['rows']} filas, sha256 {info['sha256']}")
        return 0
    out = verify_snapshot(MANIFEST_DIR / f"{a.id}.json", DATA_ROOT)
    print(f"OK {out}" if out else "OK sellado verificado (snapshot de evaluación: sin lectura ni hash)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
