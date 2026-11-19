"""Almacén de eventos inmutable y reconstrucción por correlation_id
(REQ-G-062, REQ-G-076, REQ-G-141; TC-MSG-003, TC-SEC-004, TC-AC-04).

Decisión de implementación: SQLite (tecnología ya fijada para trades.db,
architecture.md §5), tabla `audit_events` append-only. Los triggers prohíben
UPDATE y DELETE. NO resuelve el pendiente «almacenamiento durable del estado»
de FASE 2: esto es el registro de auditoría de mensajes, no el estado operativo.
"""
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from swingpilot.contracts import validate_message

_DDL = """
CREATE TABLE IF NOT EXISTS audit_events (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id     TEXT NOT NULL UNIQUE,
    correlation_id TEXT NOT NULL,
    causation_id   TEXT,
    message_type   TEXT NOT NULL,
    timestamp_utc  TEXT NOT NULL,
    message_json   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id);
CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events es inmutable: UPDATE prohibido'); END;
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events es inmutable: DELETE prohibido'); END;
"""


class EventStoreError(RuntimeError):
    pass


@dataclass
class ChainReport:
    correlation_id: str
    messages: list[dict]
    roots: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)  # causation_id inexistente en la cadena

    @property
    def complete(self) -> bool:
        """Cadena con al menos un mensaje, sin huérfanos y con un único origen."""
        return bool(self.messages) and not self.orphans and len(self.roots) == 1


def _canonical(msg: dict) -> str:
    return json.dumps(msg, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventStore:
    def __init__(self, path: str | Path):
        self._db = sqlite3.connect(str(path))
        self._db.executescript(_DDL)

    def close(self) -> None:
        self._db.close()

    def append(self, message: dict) -> bool:
        """Valida y agrega. Idempotente: reenviar el mismo mensaje idéntico devuelve
        False sin duplicar; un message_id repetido con contenido distinto es error
        (los registros históricos no se sobrescriben). Mensaje inválido: se lanza
        la excepción de validación y no se guarda nada."""
        validate_message(message)
        body = _canonical(message)
        row = self._db.execute(
            "SELECT message_json FROM audit_events WHERE message_id=?",
            (message["message_id"],)).fetchone()
        if row:
            if row[0] == body:
                return False
            raise EventStoreError(f"message_id {message['message_id']} ya existe con contenido distinto")
        with self._db:
            self._db.execute(
                "INSERT INTO audit_events(message_id,correlation_id,causation_id,"
                "message_type,timestamp_utc,message_json) VALUES (?,?,?,?,?,?)",
                (message["message_id"], message["correlation_id"], message["causation_id"],
                 message["message_type"], message["timestamp_utc"], body))
        return True

    def get_chain(self, correlation_id: str) -> ChainReport:
        rows = self._db.execute(
            "SELECT message_json FROM audit_events WHERE correlation_id=? ORDER BY seq",
            (correlation_id,)).fetchall()
        msgs = [json.loads(r[0]) for r in rows]
        ids = {m["message_id"] for m in msgs}
        roots = [m["message_id"] for m in msgs if m["causation_id"] is None]
        orphans = [m["message_id"] for m in msgs
                   if m["causation_id"] is not None and m["causation_id"] not in ids]
        return ChainReport(correlation_id, msgs, roots, orphans)

    def count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
