"""B9.3 (CR-023 §C.9/§D.8, CR-025 B.7): resolutor autoritativo de ET-10 para varias referencias de experimento.

Una sola instantánea por ciclo: se adquiere `ExperimentRegistry._locked_et10()` UNA vez (plazo único de 2 s) y,
DENTRO de ese bloqueo, se resuelven y verifican todas las entradas y se ejecuta `eligibility(..., "ET-10")` (que
incluye V9) por ventana final. Sin bloqueos anidados, sin lecturas de evidencia tras liberar, sin caché entre ciclos y
sin veredictos aportados por el llamador: el proveedor solo configura DÓNDE leer (rutas), nunca QUÉ concluir.
Todo fallo técnico (plazo, ausente, ambiguo, corrupto, no verificable) → `UNDETERMINABLE`; los resultados
metodológicos se conservan, y la precedencia técnica prevalece (§D.8). No cablea el Strategy Engine (B9.4)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .independence import ELIGIBLE, NOT_ELIGIBLE, UNDETERMINABLE, eligibility


@dataclass(frozen=True)
class EvidenceProvider:
    """Configuración de rutas de evidencia (no contiene veredictos). `selection_inputs` asigna a cada experimento la
    ruta EXPLÍCITA de su archivo de selección (su SHA-256 se verifica contra el citado por OOS_EVALUATION); no se
    exige un directorio canónico."""
    registry: object                      # ExperimentRegistry
    prereg_store: object                  # PreregistrationStore
    manifest_dir: Path
    selection_inputs: Mapping[str, Path]

    def __post_init__(self):
        """Configuración de producción: rutas absolutas (B9.4); una ruta relativa dependería del cwd del proceso."""
        if not Path(self.manifest_dir).is_absolute():
            raise ValueError("manifest_dir debe ser una ruta absoluta")
        if not isinstance(self.selection_inputs, Mapping):
            raise ValueError("selection_inputs debe ser un mapa experimento → ruta")
        for eid, p in self.selection_inputs.items():
            if not isinstance(eid, str) or not isinstance(p, (str, Path)) or not Path(p).is_absolute():
                raise ValueError(f"{eid!r}: la ruta de selection_inputs debe ser absoluta")
        for attr in ("registry", "prereg_store"):
            if getattr(self, attr, None) is None:
                raise ValueError(f"{attr} es obligatorio")


def _tech(why: str) -> dict:
    return {"result": UNDETERMINABLE, "nature": "TECHNICAL", "causes": {"ET-10": why}, "checks": {}}


def _combine(per_window: list[dict]) -> dict:
    """Precedencia §D.8: cualquier UNDETERMINABLE ⇒ UNDETERMINABLE; si no, cualquier NOT_ELIGIBLE ⇒ NOT_ELIGIBLE."""
    tech = [r for r in per_window if r["result"] == UNDETERMINABLE]
    meth = [r for r in per_window if r["result"] == NOT_ELIGIBLE]
    if not per_window or any(r["result"] not in (ELIGIBLE, NOT_ELIGIBLE, UNDETERMINABLE) for r in per_window):
        return _tech("resultado de elegibilidad no reconocido")
    for group, res, nature in ((tech, UNDETERMINABLE, "TECHNICAL"), (meth, NOT_ELIGIBLE, "METHODOLOGICAL")):
        if group:
            causes: dict = {}
            for r in group:
                causes.update(r["causes"])
            return {"result": res, "nature": nature, "causes": causes, "checks": {}}
    return {"result": ELIGIBLE, "nature": None, "causes": {}, "checks": {}}


def _one(provider: EvidenceProvider, eid: str) -> dict:
    # DEUDA TÉCNICA (B9.3/B9.4, documentada, sin refactor autorizado): la resolución verificada de entradas vive en
    # `cli._approve_inputs` (B8.4a) y el motor depende de ella en tiempo de llamada. Debe moverse a un módulo
    # compartido en un cambio aparte; hasta entonces se reutiliza sin modificar para no alterar B8.
    from .cli import _approve_inputs
    from .result_store import for_registry
    reg, pstore = provider.registry, provider.prereg_store
    path = provider.selection_inputs.get(eid)
    if path is None:
        return _tech(f"{eid}: sin ruta de selection_inputs configurada")
    store = for_registry(reg)
    wins, frozen, sel = _approve_inputs(reg, store, pstore, eid, path, provider.manifest_dir)
    out = []
    for w in sorted(wins, key=lambda x: x["window_id"]):
        grant = w["grant"]
        out.append(eligibility(reg, pstore, eid, "ET-10", preregistration=frozen, selection_inputs=sel,
                               decisions_dir=reg.decisions_dir, manifest=w["manifest"],
                               decision_ref=grant.decision_ref, grant=grant, manifest_dir=w["manifest_dir"],
                               window_id=w["window_id"]))
    return _combine(out)


def resolve_et10(provider: EvidenceProvider, experiment_ids: list[str]) -> dict[str, dict]:
    """Elegibilidad ET-10 por experimento, con una única instantánea bajo `_locked_et10` (una vez por ciclo)."""
    ids = list(experiment_ids)
    out: dict[str, dict] = {}
    try:
        with provider.registry._locked_et10():
            for eid in ids:
                if not isinstance(eid, str) or ids.count(eid) != 1:
                    out[eid if isinstance(eid, str) else repr(eid)] = _tech(f"{eid!r}: referencia no válida o duplicada")
                    continue
                try:
                    out[eid] = _one(provider, eid)
                except Exception as exc:                   # noqa: BLE001  Fail-Closed: nunca METHOD ni excepción
                    out[eid] = _tech(f"{eid}: {type(exc).__name__}: {exc}")
    except Exception as exc:                               # plazo (RegistryLockTimeout), ruta ausente, etc.
        return {(e if isinstance(e, str) else repr(e)): _tech(f"{type(exc).__name__}: {exc}") for e in ids}
    return out
