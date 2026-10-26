"""Trooper waves from a replay: compact waves per lane, and where the two sides meet.

Boon's `troopers` table has every trooper's position on every tick. We sample it
every STEP_S seconds, project troopers onto their lane (oriented from team 0's
base to team 1's), group them into waves and find the contact point between the
two teams' fronts. Mappings checked on a real replay: Boon team 2 = match team 0,
team 3 = match team 1, and Boon lane numbers equal `assigned_lane` (1, 4, 6).
"""
from __future__ import annotations

import bisect
import gzip
import json
from pathlib import Path

from app.analysis.geometry import MapGeometry

STEP_S = 3
WAVE_GAP_UNITS = 600  # troopers closer than this along the lane are drawn as one wave
CONTACT_UNITS = 1500  # est. fronts closer than this count as "meeting"
TEAM_FROM_BOON = {2: 0, 3: 1}


def _group(values: list[float], gap: float) -> list[tuple[float, int]]:
    """Sorted positions -> (center, count) for runs closer than `gap`."""
    out: list[list[float]] = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return [(sum(g) / len(g), len(g)) for g in out]


def frames_from_rows(rows_by_time: dict[int, list[dict]], geo: MapGeometry) -> list[dict]:
    """rows: {t: [{"team_num", "lane", "x", "y"}]} -> per-frame waves and contact points."""
    frames = []
    for t in sorted(rows_by_time):
        lanes: dict[str, dict] = {}
        for lane_id, lane in geo.lanes.items():
            L = lane.length or 1
            s_by_team: dict[int, list[float]] = {0: [], 1: []}
            for r in rows_by_time[t]:
                team = TEAM_FROM_BOON.get(r["team_num"])
                if r["lane"] != lane_id or team is None:
                    continue
                s, _ = lane.project(r["x"], r["y"])
                s_by_team[team].append(s / L)
            if not s_by_team[0] and not s_by_team[1]:
                continue
            waves = [
                [team, round(center, 4), n]
                for team in (0, 1)
                for center, n in _group(s_by_team[team], WAVE_GAP_UNITS / L)
            ]
            f0 = max(s_by_team[0]) if s_by_team[0] else None
            f1 = min(s_by_team[1]) if s_by_team[1] else None
            contact = round((f0 + f1) / 2, 4) if f0 is not None and f1 is not None and f1 - f0 < CONTACT_UNITS / L else None
            lanes[str(lane_id)] = {"w": waves, "c": contact}
        frames.append({"t": t, "lanes": lanes})
    return frames


def meets_per_minute(frames: list[dict]) -> list[dict]:
    """Median contact point per lane for each minute (null when the waves never met)."""
    by_minute: dict[int, dict[str, list[float]]] = {}
    for f in frames:
        m = int(round(f["t"] / 60))
        for lane, d in f["lanes"].items():
            if d.get("c") is not None:
                by_minute.setdefault(m, {}).setdefault(lane, []).append(d["c"])
    out = []
    for m in sorted(by_minute):
        lanes = {lane: sorted(v)[len(v) // 2] for lane, v in by_minute[m].items()}
        out.append({"minute": m, "lanes": lanes})
    return out


def extract_waves(demo, geo: MapGeometry, step: int = STEP_S) -> dict:
    import polars as pl

    demo.load("troopers")
    tr = demo.troopers.filter((pl.col("trooper_type") == "trooper") & (pl.col("health") > 0))
    if tr.height == 0:
        return {"step": step, "frames": [], "meets": []}
    ticks = tr["tick"].unique().sort().to_list()

    def seconds(tick: int) -> float:
        s = demo.tick_to_match_seconds(int(tick))
        return float(s) if s is not None else float(demo.tick_to_seconds(int(tick)))

    end = int(seconds(ticks[-1]))
    wanted: dict[int, int] = {}
    for t in range(0, end + 1, step):
        i = bisect.bisect_left(ticks, t, key=seconds)
        if i < len(ticks):
            wanted[ticks[i]] = t
    sel = tr.filter(pl.col("tick").is_in(list(wanted))).select(["tick", "team_num", "lane", "x", "y"])
    rows: dict[int, list[dict]] = {}
    for r in sel.iter_rows(named=True):
        rows.setdefault(wanted[r["tick"]], []).append(r)
    frames = frames_from_rows(rows, geo)
    return {"step": step, "frames": frames, "meets": meets_per_minute(frames)}


def save_waves(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))


def load_waves(path: Path) -> dict | None:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
