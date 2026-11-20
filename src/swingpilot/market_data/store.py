"""Almacén local de velas cerradas (REQ-G-097: «las velas recuperadas se persisten con la
misma fuente y timestamp»; REQ-G-070: separación entre tiempo de mercado y de procesamiento).

SQLite fuera de Git (var/). Una vela cerrada es inmutable: triggers impiden UPDATE y DELETE.
Si llega otra vez la misma vela con el mismo contenido, se ignora; con contenido distinto se
registra un conflicto y no se sobrescribe (Fail-Closed lo decide quien llama).
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .candles import Candle, interval_ms

SOURCES = ("binance_ws", "binance_rest")

_DDL = """
CREATE TABLE IF NOT EXISTS candles (
    interval TEXT NOT NULL, open_time INTEGER NOT NULL, close_time INTEGER NOT NULL,
    open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
    volume REAL NOT NULL, source TEXT NOT NULL, received_at_utc TEXT NOT NULL,
    PRIMARY KEY (interval, open_time));
CREATE TABLE IF NOT EXISTS candle_conflicts (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, interval TEXT NOT NULL, open_time INTEGER NOT NULL,
    stored_json TEXT NOT NULL, received_json TEXT NOT NULL, source TEXT NOT NULL,
    detected_at_utc TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS candles_no_update BEFORE UPDATE ON candles
BEGIN SELECT RAISE(ABORT, 'candles es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS candles_no_delete BEFORE DELETE ON candles
BEGIN SELECT RAISE(ABORT, 'candles es inmutable'); END;
"""

INSERTED, DUPLICATE, CONFLICT = "INSERTED", "DUPLICATE", "CONFLICT"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class CandleStore:
    def __init__(self, path: str | Path, now: Callable[[], str] = _utcnow):
        # check_same_thread=False porque stream.py ejecuta resync() con asyncio.to_thread. Todo
        # acceso a la conexión pasa por self._lock (QA3-08): la conexión SQLite no es segura entre
        # hilos sin serializar.
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(_DDL)
        self._now = now

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def add(self, candle: Candle, source: str) -> str:
        if source not in SOURCES:
            raise ValueError(f"fuente no válida: {source!r}")
        with self._lock:
            return self._add(candle, source)

    def _add(self, candle: Candle, source: str) -> str:
        row = self._db.execute(
            "SELECT close_time, open, high, low, close, volume FROM candles WHERE interval=? AND open_time=?",
            (candle.interval, candle.open_time)).fetchone()
        if row is not None:
            stored = Candle(candle.interval, candle.open_time, *row)
            if stored == candle:
                return DUPLICATE
            with self._db:
                self._db.execute(
                    "INSERT INTO candle_conflicts(interval, open_time, stored_json, received_json, source, detected_at_utc)"
                    " VALUES (?,?,?,?,?,?)",
                    (candle.interval, candle.open_time, json.dumps(stored.to_dict()),
                     json.dumps(candle.to_dict()), source, self._now()))
            return CONFLICT
        with self._db:
            self._db.execute(
                "INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)",
                (candle.interval, candle.open_time, candle.close_time, candle.open, candle.high,
                 candle.low, candle.close, candle.volume, source, self._now()))
        return INSERTED

    def last_open_time(self, interval: str) -> int | None:
        interval_ms(interval)
        with self._lock:
            (v,) = self._db.execute("SELECT MAX(open_time) FROM candles WHERE interval=?", (interval,)).fetchone()
        return v

    def candles(self, interval: str, since_open_time: int | None = None) -> list[Candle]:
        q = "SELECT open_time, close_time, open, high, low, close, volume FROM candles WHERE interval=?"
        args: list = [interval]
        if since_open_time is not None:
            q += " AND open_time >= ?"
            args.append(since_open_time)
        with self._lock:
            rows = self._db.execute(q + " ORDER BY open_time", args).fetchall()
        return [Candle(interval, *r) for r in rows]

    def provenance(self, interval: str, open_time: int) -> tuple[str, str] | None:
        """(fuente, hora de recepción) de una vela persistida."""
        with self._lock:
            return self._db.execute("SELECT source, received_at_utc FROM candles WHERE interval=? AND open_time=?",
                                    (interval, open_time)).fetchone()

    def conflicts(self) -> list[tuple]:
        with self._lock:
            return self._db.execute("SELECT interval, open_time, source FROM candle_conflicts ORDER BY seq").fetchall()
