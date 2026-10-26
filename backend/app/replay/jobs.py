"""Replay job state in SQLite, and loading of parsed replay results."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.config import DEMO_DIR
from app.state import AppState

RESULT_NAME = "replay.json"


@dataclass
class ReplayData:
    """What rules can use from a parsed replay. All times are match-clock seconds."""

    match_id: int
    urn_events: list[dict] = field(default_factory=list)  # {"checkpoints": [(t, x, y), ...], "team": int|None}
    notes: list[str] = field(default_factory=list)  # parser caveats shown in the UI

    @classmethod
    def load(cls, path: Path) -> "ReplayData":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            match_id=raw["match_id"],
            urn_events=[{**e, "checkpoints": [tuple(c) for c in e["checkpoints"]]} for e in raw.get("urn_events", [])],
            notes=raw.get("notes", []),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"match_id": self.match_id, "urn_events": self.urn_events, "notes": self.notes}),
            encoding="utf-8",
        )


def match_dir(match_id: int) -> Path:
    return DEMO_DIR / str(match_id)


def set_status(st: AppState, match_id: int, status: str, path: str | None = None, error: str | None = None) -> None:
    st.db.execute(
        "INSERT OR REPLACE INTO replays (match_id, status, path, error, updated_at) VALUES (?, ?, ?, ?, ?)",
        (match_id, status, path, error, time.time()),
    )


def replay_status(st: AppState, match_id: int) -> dict:
    row = st.db.one("SELECT status, error, updated_at FROM replays WHERE match_id = ?", (match_id,))
    if not row:
        return {"status": "none"}
    return {"status": row["status"], "error": row["error"], "updated_at": row["updated_at"]}


_loaded: dict[int, tuple[float, ReplayData]] = {}


def replay_for(st: AppState, match_id: int) -> ReplayData | None:
    row = st.db.one("SELECT status, updated_at FROM replays WHERE match_id = ?", (match_id,))
    if not row or row["status"] != "done":
        return None
    hit = _loaded.get(match_id)
    if hit and hit[0] == row["updated_at"]:
        return hit[1]
    path = match_dir(match_id) / RESULT_NAME
    if not path.exists():
        return None
    data = ReplayData.load(path)
    _loaded[match_id] = (row["updated_at"], data)
    return data
