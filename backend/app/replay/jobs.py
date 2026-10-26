"""Replay job state in SQLite, and loading of parsed replay results."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.config import DEMO_DIR
from app.state import AppState

log = logging.getLogger(__name__)

RESULT_NAME = "replay.json"
WAVES_NAME = "waves.json.gz"
# Parsed results of the seed's sample replay, so the urn check and wave view work out of the box.
SEED_REPLAYS = Path(__file__).resolve().parents[1] / "seed" / "data" / "replays"


@dataclass
class ReplayData:
    """What rules can use from a parsed replay. All times are match-clock seconds."""

    match_id: int
    # One per urn: {"checkpoints": [(t, x, y)], "carriers": [(hero_id, t_from, t_to)]}
    urn_events: list[dict] = field(default_factory=list)
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


def result_file(match_id: int, name: str) -> Path | None:
    """Your parsed file if it exists, else the bundled sample's, else None."""
    for base in (DEMO_DIR, SEED_REPLAYS):
        p = base / str(match_id) / name
        if p.exists():
            return p
    return None


def matches_with_waves() -> list[int]:
    ids = set()
    for base in (DEMO_DIR, SEED_REPLAYS):
        if base.exists():
            ids |= {int(p.parent.name) for p in base.glob(f"*/{WAVES_NAME}") if p.parent.name.isdigit()}
    return sorted(ids, reverse=True)


def waves_for(match_id: int) -> dict | None:
    from app.macro.waves import load_waves

    p = result_file(match_id, WAVES_NAME)
    return load_waves(p) if p else None


def set_status(st: AppState, match_id: int, status: str, path: str | None = None, error: str | None = None) -> None:
    st.db.execute(
        "INSERT OR REPLACE INTO replays (match_id, status, path, error, updated_at) VALUES (?, ?, ?, ?, ?)",
        (match_id, status, path, error, time.time()),
    )


def run_job(st: AppState, match_id: int, uploaded: Path | None = None) -> None:
    """Download (unless uploaded), parse and store. Runs in a background thread."""
    from app.analysis.loader import geometry
    from app.macro.waves import save_waves
    from app.replay.download import ReplayUnavailable, download_demo, unpack
    from app.replay.parser import parse_demo

    folder = match_dir(match_id)
    try:
        if uploaded is None:
            set_status(st, match_id, "downloading")
            dem = download_demo(st.gd, match_id, folder)
        else:
            set_status(st, match_id, "parsing")
            dem = unpack(uploaded)
        set_status(st, match_id, "parsing", path=str(dem))
        data, waves = parse_demo(dem, match_id, geometry(st.gd))
        data.save(folder / RESULT_NAME)
        if waves:
            save_waves(waves, folder / WAVES_NAME)
        dem.unlink(missing_ok=True)  # demos are 300-500 MB; the parsed result is all we keep
        set_status(st, match_id, "done")
    except ReplayUnavailable as e:
        set_status(st, match_id, "failed", error=str(e))
    except Exception as e:  # parser errors: keep the message short for the UI
        log.exception("Replay job failed for %s", match_id)
        set_status(st, match_id, "failed", error=f"Could not read this replay: {str(e)[:160]}")


_loaded: dict[int, tuple[float, ReplayData]] = {}


def replay_for(st: AppState, match_id: int) -> ReplayData | None:
    row = st.db.one("SELECT status, updated_at FROM replays WHERE match_id = ?", (match_id,))
    if row and row["status"] == "done":
        stamp, path = row["updated_at"], match_dir(match_id) / RESULT_NAME
    else:
        stamp, path = 0.0, SEED_REPLAYS / str(match_id) / RESULT_NAME
    hit = _loaded.get(match_id)
    if hit and hit[0] == stamp:
        return hit[1]
    if not path.exists():
        return None
    data = ReplayData.load(path)
    _loaded[match_id] = (stamp, data)
    return data


def replay_status(st: AppState, match_id: int) -> dict:
    row = st.db.one("SELECT status, error, updated_at FROM replays WHERE match_id = ?", (match_id,))
    if row:
        return {"status": row["status"], "error": row["error"], "updated_at": row["updated_at"]}
    if (SEED_REPLAYS / str(match_id) / RESULT_NAME).exists():
        return {"status": "done", "error": None, "sample": True}
    return {"status": "none"}
