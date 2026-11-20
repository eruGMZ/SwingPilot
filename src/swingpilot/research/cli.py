"""CLI de la snapshot (FEAT-015). Herramienta manual; nada se ejecuta automáticamente.

    python -m swingpilot.research.cli build-snapshot --id SNAP-0001 --confirm
    python -m swingpilot.research.cli verify-snapshot --id SNAP-0001

`build-snapshot` descarga datos públicos de Binance (sin credenciales ni costo de API) y fija
para siempre las fechas de corte de las particiones; por eso exige `--confirm`.
`verify-snapshot` solo recalcula el SHA-256 de `train_val` (OOS y LOCKBOX no se leen).
El identificador debe ser SNAP-NNNN; los LOCKBOX consumidos se leen del registro de experimentos.
"""
import argparse
import sys
from pathlib import Path

from swingpilot.market_data import BinancePublicClient

from .experiments import ExperimentRegistry
from .snapshot import build_snapshot, verify_snapshot

REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO / "var" / "snapshots"          # fuera de Git (DEC-017 Q46)
MANIFEST_DIR = REPO / "research" / "snapshots"  # en el repositorio
REGISTRY = REPO / "research" / "experiments" / "registry.jsonl"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="swingpilot.research.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-snapshot")
    b.add_argument("--id", required=True)
    b.add_argument("--confirm", action="store_true")
    v = sub.add_parser("verify-snapshot")
    v.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build-snapshot":
        if not a.confirm:
            print("build-snapshot fija las particiones de forma permanente: repetir con --confirm", file=sys.stderr)
            return 2
        consumed = ExperimentRegistry(REGISTRY).consumed_lockboxes()   # TC-ML-019 (QA3-15)
        res = build_snapshot(BinancePublicClient(), a.id, DATA_ROOT, MANIFEST_DIR, consumed_lockboxes=consumed)
        print(f"snapshot {a.id}: manifiesto {res.manifest_path}")
        for part, info in res.manifest["files"].items():
            print(f"  {part}: {info['rows']} filas, sha256 {info['sha256']}")
        return 0
    out = verify_snapshot(MANIFEST_DIR / f"{a.id}.json", DATA_ROOT)
    print(f"OK {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
