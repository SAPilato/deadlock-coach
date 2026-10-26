"""Key/value cache in SQLite. Every row carries the patch build it was fetched under."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.db import Database


@dataclass
class CacheEntry:
    payload: Any
    patch_version: int | None
    fetched_at: float
    expires_at: float | None

    def is_fresh(self, now: float, min_patch: int | None = None) -> bool:
        if self.expires_at is not None and now >= self.expires_at:
            return False
        if min_patch is not None and (self.patch_version is None or self.patch_version < min_patch):
            return False
        return True


class Cache:
    def __init__(self, db: Database, clock: Callable[[], float] = time.time):
        self.db = db
        self.clock = clock
        # Parsed payloads, so big assets (items, map) are decoded once per process.
        self._memo: dict[str, CacheEntry] = {}

    def get(self, key: str) -> CacheEntry | None:
        if key in self._memo:
            return self._memo[key]
        row = self.db.one(
            "SELECT payload, patch_version, fetched_at, expires_at FROM cache WHERE key = ?", (key,)
        )
        if row is None:
            return None
        entry = CacheEntry(json.loads(row["payload"]), row["patch_version"], row["fetched_at"], row["expires_at"])
        self._memo[key] = entry
        return entry

    def set(self, key: str, payload: Any, *, ttl: float | None, patch_version: int | None) -> CacheEntry:
        now = self.clock()
        entry = CacheEntry(payload, patch_version, now, None if ttl is None else now + ttl)
        self.db.execute(
            "INSERT OR REPLACE INTO cache (key, payload, patch_version, fetched_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (key, json.dumps(payload, separators=(",", ":")), patch_version, entry.fetched_at, entry.expires_at),
        )
        self._memo[key] = entry
        return entry

    def delete_prefix(self, prefix: str) -> int:
        n = self.db.scalar("SELECT COUNT(*) FROM cache WHERE key LIKE ?", (prefix + "%",))
        self.db.execute("DELETE FROM cache WHERE key LIKE ?", (prefix + "%",))
        for k in [k for k in self._memo if k.startswith(prefix)]:
            del self._memo[k]
        return n or 0

    def oldest_patch(self, prefix: str) -> int | None:
        return self.db.scalar(
            "SELECT MIN(patch_version) FROM cache WHERE key LIKE ? AND patch_version IS NOT NULL",
            (prefix + "%",),
        )
