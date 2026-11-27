"""CLI de la snapshot (FEAT-015). Herramienta manual; nada se ejecuta automáticamente.

    python -m swingpilot.research.cli build-snapshot --id SNAP-0001 --d-dev 2024-01-01 --confirm
    python -m swingpilot.research.cli verify-snapshot --id SNAP-0001

`build-snapshot` construye la snapshot de DESARROLLO [2017-08-17, D_dev) (CR-023): descarga datos
públicos de Binance (sin credenciales ni costo de API) y fija para siempre `D_dev` y el corte
Train:Validation 5:2; por eso exige `--d-dev` y `--confirm`. Antes de descargar obtiene las
ventanas reservadas activas de un proveedor; la fuente autoritativa de esas ventanas está
`reserved_windows_source` (B5: registro y almacén reales, solo lectura); si no es verificable, el comando
termina con código 1 sin descargar. `build-evaluation` ejecuta ET-4 con `--confirm` obligatorio y todas las comprobaciones del constructor.
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
REGISTRY_PATH = REPO / "research" / "experiments" / "registry.jsonl"
OWNER_ACTOR = "propietario"
CLI_SNAPSHOT_ID = re.compile(r"SNAP-[0-9]{4}")   # con fullmatch; SNAP-TEST* solo en pruebas (QA3R2-08)


def reserved_windows_provider() -> list:
    """Ventanas activas de la fuente autoritativa (registro y almacén reales, solo lectura); Fail-Closed."""
    from .evaluation_snapshot import reserved_windows_source
    from .experiments import ExperimentRegistry
    from .prereg_store import DEFAULT_ROOT, PreregistrationStore
    return reserved_windows_source(ExperimentRegistry(REGISTRY_PATH), PreregistrationStore(DEFAULT_ROOT))()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="swingpilot.research.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-snapshot")
    b.add_argument("--id", required=True)
    b.add_argument("--d-dev", required=True, dest="d_dev", help="YYYY-MM-DD (UTC, exclusivo)")
    b.add_argument("--confirm", action="store_true")
    e = sub.add_parser("build-evaluation")                      # ET-4 (B5)
    e.add_argument("--id", required=True)
    e.add_argument("--experiment", required=True)
    e.add_argument("--window", required=True, choices=("OOS", "LOCKBOX"))
    e.add_argument("--confirm", action="store_true")
    v = sub.add_parser("verify-snapshot")
    v.add_argument("--id", required=True)
    r = sub.add_parser("recover-window-result")                 # CR-024 B.6: EVIDENCE_ONLY, solo explícito
    r.add_argument("--experiment", required=True)
    r.add_argument("--window", required=True, choices=("OOS", "LOCKBOX"))
    r.add_argument("--confirm", action="store_true")
    p = sub.add_parser("approve")                                # CR-023 dec. 5 / CR-025 B.2: HUMAN_REVIEW → APPROVED
    p.add_argument("--experiment", required=True)
    p.add_argument("--decision-ref", required=True, dest="decision_ref", help="documento DEC-NNN_*.md de la aprobación")
    p.add_argument("--selection-inputs", required=True, dest="selection_inputs", help="archivo de resultados de la selección")
    p.add_argument("--confirm", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "recover-window-result":
        return _recover(a)
    if a.cmd == "approve":
        return _approve(a)
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


def _recover(a, registry_path=None, manifest_dir=None) -> int:
    """Recuperación EXPLÍCITA de EVIDENCE_ONLY (CR-024 B.6): relee solo la evidencia (sin datos de mercado),
    revalida su durabilidad y la ligadura bajo el bloqueo del registro y escribe el marcador. Exige --confirm."""
    from .experiments import ExperimentError, ExperimentRegistry, PersistenceUncertainError
    from .result_store import for_registry
    if not a.confirm:
        print("recover-window-result escribe un marcador permanente: repetir con --confirm", file=sys.stderr)
        return 2
    reg = ExperimentRegistry(registry_path or REGISTRY_PATH)
    try:
        rec = reg.recover_evidence_only(for_registry(reg), a.experiment, a.window.lower(), actor=OWNER_ACTOR,
                                    manifest_dir=manifest_dir or MANIFEST_DIR)
    except PersistenceUncertainError as exc:
        print(f"ERROR persistencia incierta (sin éxito): {exc}", file=sys.stderr)
        return 1
    except ExperimentError as exc:                       # incluye RegistryCorruptError
        print(f"ERROR de recuperación: {exc}", file=sys.stderr)
        return 1
    print(f"OK {a.experiment}/{a.window}: WINDOW_RESULT_PERSISTED evaluation_hash {rec['evaluation_hash']}")
    return 0


def _approve_inputs(reg, store, pstore, eid, selection_path, manifest_dir):
    """Resuelve, solo de fuentes verificadas, lo que exige ET-8: grants (de los PARTITION_CONSUMED únicos), manifiestos
    (del directorio de manifiestos, ligados a snapshot y ventana), preregistro congelado (almacén, SHA citado por
    PREREGISTERED) y selection_inputs (SHA citado por OOS_EVALUATION). Ausente, ambiguo o dispar → ExperimentError."""
    import hashlib

    from .experiments import ExperimentError
    from .partitions import FinalEvaluationGrant
    from .preregistration import _preregistered_sha, freeze
    from .snapshot import load_manifest
    records = reg.records()
    marks = reg.verified_window_results(store)                  # evidencia releída y verificada (CR-024)
    if {m["partition"] for m in marks if m["experiment_id"] == eid} != {"oos", "lockbox"}:
        raise ExperimentError(f"{eid}: faltan resultados autoritativos de OOS y LOCKBOX")
    wins = []
    for part in ("oos", "lockbox"):
        cons = {tuple(sorted(r.items())) for r in records
                if r.get("kind") == "PARTITION_CONSUMED" and r.get("experiment_id") == eid and r.get("partition") == part}
        if len(cons) != 1:
            raise ExperimentError(f"{eid}/{part}: consumo ausente o ambiguo ({len(cons)})")
        c = dict(next(iter(cons)))
        mpath = Path(manifest_dir) / f"{c['snapshot_id']}.json"
        try:
            manifest = load_manifest(mpath)
        except Exception as exc:
            raise ExperimentError(f"{eid}/{part}: manifiesto ilegible: {exc!r}") from exc
        wid = f"{eid}/{part.upper()}"
        if manifest.get("snapshot_id") != c["snapshot_id"] or manifest.get("window_id") != wid:
            raise ExperimentError(f"{wid}: el manifiesto no corresponde al consumo")
        wins.append({"grant": FinalEvaluationGrant(eid, part, c["snapshot_id"], OWNER_ACTOR, c["decision_ref"]),
                     "manifest": manifest, "manifest_dir": Path(manifest_dir), "window_id": wid})
    sha = _preregistered_sha(reg, eid)
    frozen = freeze(pstore.load(eid, sha))
    if frozen.sha256 != sha:
        raise ExperimentError(f"{eid}: el preregistro del almacén no reproduce el SHA-256 citado")
    cited = {(r.get("evidence") or {}).get("selection_inputs_sha256") for r in records
             if r.get("kind") == "TRANSITION" and r.get("experiment_id") == eid and r.get("to") == "OOS_EVALUATION"}
    sel = Path(selection_path).read_bytes()
    if len(cited) != 1 or hashlib.sha256(sel).hexdigest() not in cited:
        raise ExperimentError(f"{eid}: selection_inputs no coincide con el SHA-256 citado por OOS_EVALUATION")
    return wins, frozen, sel


def _approve(a, registry_path=None, manifest_dir=None, decisions_dir=None, prereg_root=None) -> int:
    """HUMAN_REVIEW → APPROVED (REQ-G-107): única vía de producción. Exige --confirm; usa `build_approval_check` y
    `transition` (ET-8 completo bajo el bloqueo; la approval_binding la deriva y escribe `transition`)."""
    from .experiments import ExperimentRegistry
    from .independence import build_approval_check
    from .prereg_store import DEFAULT_ROOT, PreregistrationStore
    from .result_store import for_registry
    if not a.confirm:
        print("approve escribe una aprobación permanente: repetir con --confirm", file=sys.stderr)
        return 2
    try:
        reg = ExperimentRegistry(registry_path or REGISTRY_PATH, decisions_dir)
        store, pstore = for_registry(reg), PreregistrationStore(prereg_root or DEFAULT_ROOT)
        wins, frozen, sel = _approve_inputs(reg, store, pstore, a.experiment, a.selection_inputs,
                                            manifest_dir or MANIFEST_DIR)
        check = build_approval_check(reg, pstore, wins, decisions_dir=reg.decisions_dir, preregistration=frozen,
                                     selection_inputs=sel)
        reg.transition(a.experiment, "APPROVED", actor=OWNER_ACTOR, evidence={"decision_ref": a.decision_ref},
                       approval_check=check)
    except Exception as exc:                              # Fail-Closed: cualquier fallo → sin aprobación
        print(f"ERROR de aprobación: {exc}", file=sys.stderr)
        return 1
    print(f"OK {a.experiment}: APPROVED decision_ref {a.decision_ref}")
    return 0


def _run(a) -> int:
    if a.cmd == "build-snapshot":
        if not a.confirm:
            print("build-snapshot fija las particiones de forma permanente: repetir con --confirm", file=sys.stderr)
            return 2
        windows = reserved_windows_provider()                          # fuente autoritativa; antes de cualquier descarga
        res = build_snapshot(BinancePublicClient(), a.id, DATA_ROOT, MANIFEST_DIR, d_dev=a.d_dev,
                             reserved_windows=[], reserved_windows_source=lambda: windows)
        print(f"snapshot {a.id}: manifiesto {res.manifest_path}")
        for part, info in res.manifest["files"].items():
            print(f"  {part}: {info['rows']} filas, sha256 {info['sha256']}")
        return 0
    if a.cmd == "build-evaluation":
        if not a.confirm:
            print("build-evaluation sella la ventana de forma permanente: repetir con --confirm", file=sys.stderr)
            return 2
        from .evaluation_snapshot import build_evaluation_snapshot
        from .experiments import ExperimentRegistry
        from .prereg_store import DEFAULT_ROOT, PreregistrationStore
        res = build_evaluation_snapshot(BinancePublicClient(), a.id, DATA_ROOT, MANIFEST_DIR,
                                        registry=ExperimentRegistry(REGISTRY_PATH), store=PreregistrationStore(DEFAULT_ROOT),
                                        experiment_id=a.experiment, window_id=f"{a.experiment}/{a.window}", confirm=True)
        print(f"snapshot de evaluación {a.id}: manifiesto {res.manifest_path}")
        for part, info in res.manifest["files"].items():
            print(f"  {part}: {info['rows']} filas, sha256 {info['sha256']} (sellado 0o000)")
        return 0
    out = verify_snapshot(MANIFEST_DIR / f"{a.id}.json", DATA_ROOT)
    print(f"OK {out}" if out else "OK sellado verificado (snapshot de evaluación: sin lectura ni hash)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
