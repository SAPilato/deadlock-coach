"""Saved builds in SQLite, plus a portable JSON export format."""
from __future__ import annotations

import json
import time

from pydantic import BaseModel, Field

from app.db import Database

EXPORT_FORMAT = "deadlock-coach-build/1"


class TargetIn(BaseModel):
    hp: float = 2500
    bullet_resist: float = 0
    headshot_pct: float = 0


class BuildIn(BaseModel):
    hero_id: int
    level: int = Field(1, ge=1, le=60)
    items: list[int] = Field(default_factory=list, max_length=40)
    toggles: list[str] = Field(default_factory=list)
    target: TargetIn = Field(default_factory=TargetIn)


class SavedBuildIn(BuildIn):
    id: int | None = None
    name: str = Field(min_length=1, max_length=60)


def save(db: Database, b: SavedBuildIn) -> int:
    payload = json.dumps(b.model_dump(exclude={"id", "name", "hero_id"}))
    now = time.time()
    if b.id is not None and db.one("SELECT id FROM builds WHERE id = ?", (b.id,)):
        db.execute(
            "UPDATE builds SET name = ?, hero_id = ?, payload = ?, updated_at = ? WHERE id = ?",
            (b.name, b.hero_id, payload, now, b.id),
        )
        return b.id
    return db.insert(
        "INSERT INTO builds (name, hero_id, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (b.name, b.hero_id, payload, now, now),
    )


def _row(r) -> dict:
    return {"id": r["id"], "name": r["name"], "hero_id": r["hero_id"], "updated_at": r["updated_at"], **json.loads(r["payload"])}


def list_builds(db: Database) -> list[dict]:
    return [_row(r) for r in db.all("SELECT * FROM builds ORDER BY updated_at DESC")]


def get(db: Database, build_id: int) -> dict | None:
    r = db.one("SELECT * FROM builds WHERE id = ?", (build_id,))
    return _row(r) if r else None


def delete(db: Database, build_id: int) -> bool:
    if not db.one("SELECT id FROM builds WHERE id = ?", (build_id,)):
        return False
    db.execute("DELETE FROM builds WHERE id = ?", (build_id,))
    return True


def export(build: dict, hero_name: str, item_names: dict[int, str], game_build: int | None) -> dict:
    """Readable and re-importable: ids for the app, names for humans."""
    return {
        "format": EXPORT_FORMAT,
        "game_build": game_build,
        "name": build["name"],
        "hero": {"id": build["hero_id"], "name": hero_name},
        "level": build["level"],
        "items": [{"id": i, "name": item_names.get(i, str(i))} for i in build["items"]],
        "toggles": build.get("toggles", []),
        "target": build.get("target", {}),
    }


def parse_export(data: dict) -> SavedBuildIn:
    if data.get("format") != EXPORT_FORMAT:
        raise ValueError("Not a Deadlock Coach build file.")
    return SavedBuildIn(
        name=str(data.get("name") or "Imported build")[:60],
        hero_id=int(data["hero"]["id"]),
        level=int(data.get("level") or 1),
        items=[int(i["id"]) for i in data.get("items", [])],
        toggles=[str(t) for t in data.get("toggles", [])],
        target=TargetIn(**(data.get("target") or {})),
    )
