"""SQLite storage: API cache, settings, analysis results, replay jobs."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    patch_version INTEGER,
    fetched_at REAL NOT NULL,
    expires_at REAL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    match_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    engine_version INTEGER NOT NULL,
    patch_version INTEGER,
    payload TEXT NOT NULL,
    computed_at REAL NOT NULL,
    PRIMARY KEY (match_id, account_id)
);
CREATE TABLE IF NOT EXISTS replays (
    match_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,
    path TEXT,
    error TEXT,
    updated_at REAL NOT NULL
);
"""


class Database:
    """One shared connection guarded by a lock. Plenty for a single local user."""

    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            if str(path) != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple | dict = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def one(self, sql: str, params: tuple | dict = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def all(self, sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def scalar(self, sql: str, params: tuple | dict = ()) -> Any:
        row = self.one(sql, params)
        return row[0] if row else None
