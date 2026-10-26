"""Wires up the shared objects (database, cache, API client, game data)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import DB_PATH, OFFLINE
from app.db import Database
from app.gamedata.cache import Cache
from app.gamedata.client import ApiClient
from app.gamedata.service import GameData


@dataclass
class AppState:
    db: Database
    cache: Cache
    client: ApiClient
    gd: GameData


def create_state(db_path: str | Path = DB_PATH, offline: bool = OFFLINE) -> AppState:
    db = Database(db_path)
    cache = Cache(db)
    client = ApiClient(cache, offline=offline)
    return AppState(db=db, cache=cache, client=client, gd=GameData(client))
