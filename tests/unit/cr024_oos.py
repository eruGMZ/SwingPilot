"""CR-024 B.7 (ayuda de pruebas heredadas): persiste un OOS favorable GENUINO para un consumo OOS ya registrado.
Usa el único camino de escritura (`persist_window_result`: ligaduras bajo bloqueo, bytes reales del manifiesto,
evidencia durable, marcador y relectura). Solo sintetiza el `WindowOutcome` favorable; nada se escribe a mano."""
import json
from pathlib import Path

from swingpilot.research import preregistration as PR
from swingpilot.research import result_serialization as RS
from swingpilot.research import result_store as RST
from swingpilot.research import window_evaluation as W


def persist_favorable_oos(reg, manifest_dir, eid, partition="oos"):
    lines, records = reg._load()
    rec = [r for r in records if r.get("kind") == "PARTITION_CONSUMED" and r.get("experiment_id") == eid
           and r.get("partition") == partition][-1]
    raw = (Path(manifest_dir) / f"{rec['snapshot_id']}.json").read_bytes()
    manifest = json.loads(raw)
    oc = W.WindowOutcome(partition, W.FAVORABLE, None, "ELIGIBLE", [], {"trials_count": 1}, trades=30)
    doc, data = RS.build_document(oc, experiment_id=eid, prereg_sha256=PR._preregistered_sha(reg, eid),
                                  snapshot_id=rec["snapshot_id"], window_id=str(manifest["window_id"]),
                                  manifest_sha256=RS.evaluation_hash(raw), decision_ref=rec["decision_ref"],
                                  consumed_line_sha256=RS.evaluation_hash(lines[records.index(rec)]))
    issued = RS.issue(RS._ISSUE_KEY, oc, doc, data, (eid, partition, rec["snapshot_id"], rec["decision_ref"]))
    return reg.persist_window_result(RST.for_registry(reg), issued, manifest_dir=manifest_dir, actor="propietario")
