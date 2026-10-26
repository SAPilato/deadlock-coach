"""User settings stored in SQLite: Steam account and rank bracket."""
from __future__ import annotations

import json

from app.config import DEFAULT_BRACKET
from app.db import Database
from app.seed.load import seed_meta


class Settings:
    def __init__(self, db: Database):
        self.db = db

    def _get(self, key: str, default=None):
        v = self.db.scalar("SELECT value FROM settings WHERE key = ?", (key,))
        return json.loads(v) if v is not None else default

    def _set(self, key: str, value) -> None:
        self.db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))

    @property
    def account_id(self) -> int | None:
        return self._get("account_id")

    @account_id.setter
    def account_id(self, value: int | None) -> None:
        self._set("account_id", value)

    @property
    def bracket(self) -> tuple[int, int]:
        b = self._get("bracket")
        return (int(b[0]), int(b[1])) if b else DEFAULT_BRACKET

    @bracket.setter
    def bracket(self, value: tuple[int, int]) -> None:
        lo, hi = sorted((int(value[0]), int(value[1])))
        self._set("bracket", [lo, hi])

    @property
    def sample_account(self) -> int | None:
        meta = seed_meta()
        return meta["account_id"] if meta else None

    @property
    def active_account(self) -> int | None:
        """The user's account, or the seed's sample player when none is set."""
        return self.account_id or self.sample_account

    @property
    def using_sample(self) -> bool:
        return self.account_id is None
