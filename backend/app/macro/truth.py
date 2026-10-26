"""Live-map truth from replays: where objectives really stand and where the urn really goes.

Why: the map asset data (/v1/assets/map) mixes current and legacy entries.
Checked on post-City Never Sleeps replays (build 6712+):
- it lists 6 urn spawns, but urns only spawn and get delivered at 2 sites;
- its objective positions are minimap icon spots, ~1,500 units from the real NPCs;
- Mid Boss, Shrines and Base Guardians are missing.
A parsed replay is ground truth for the build it was recorded on, so positions
from the newest replay win over the asset data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

TEAM_FROM_BOON = {2: 0, 3: 1}
SITE_MERGE_UNITS = 500  # urn events closer than this are the same site
MIN_SITE_HITS = 2


def _cluster(points: list[tuple[float, float]], gap: float) -> list[tuple[float, float, int]]:
    sites: list[list[tuple[float, float]]] = []
    for p in points:
        for s in sites:
            cx = sum(q[0] for q in s) / len(s)
            cy = sum(q[1] for q in s) / len(s)
            if math.dist(p, (cx, cy)) <= gap:
                s.append(p)
                break
        else:
            sites.append([p])
    return [(sum(q[0] for q in s) / len(s), sum(q[1] for q in s) / len(s), len(s)) for s in sites]


def truth_from_rows(
    objective_rows: list[dict],
    guardian_rows: list[dict],
    urn_rows: list[dict],
    *,
    match_id: int,
    build: int | None,
    start_time: int | None = None,
) -> dict:
    """Pure part, testable without a demo.

    objective_rows: Boon `objectives`, first row per entity (objective_type, team_num, lane, x, y, max_health).
    guardian_rows: Boon `troopers` trooper_boss, first row per (team_num, lane).
    urn_rows: Boon `urn` events (tick, event, x, y).
    """
    objectives: list[dict] = []
    seen: set[tuple] = set()

    def add(kind: str, r: dict, lane) -> None:
        team = TEAM_FROM_BOON.get(r["team_num"])
        key = (kind, team, lane, round(r["x"] / 100), round(r["y"] / 100))  # respawns share a spot
        if key not in seen:
            seen.add(key)
            objectives.append({"kind": kind, "team": team, "lane": lane, "x": r["x"], "y": r["y"], "hp": r.get("max_health")})

    for r in guardian_rows:
        add("tier1", r, r["lane"])
    kinds = {"walker": "tier2", "barracks": "barracks", "shrine": "shrine", "patron": "titan", "mid_boss": "mid_boss"}
    for r in objective_rows:
        kind = kinds.get(r["objective_type"])
        if kind:
            add(kind, r, r["lane"] if r["lane"] in (1, 4, 6) else None)

    # Urn sites: the first pickup of each urn (its spawn) and every delivery.
    # Re-pickups after a drop happen anywhere, so they are left out.
    pts = []
    fresh = True
    for r in sorted(urn_rows, key=lambda r: r.get("tick", 0)):
        if r["event"] == "picked_up":
            if fresh:
                pts.append((r["x"], r["y"]))
            fresh = False
        elif r["event"] == "returned":
            pts.append((r["x"], r["y"]))
            fresh = True
    sites = [
        {"x": round(x, 1), "y": round(y, 1), "seen": n}
        for x, y, n in _cluster(pts, SITE_MERGE_UNITS) if n >= MIN_SITE_HITS
    ]
    return {"match_id": match_id, "demo_build": build, "start_time": start_time, "objectives": objectives, "urn_sites": sites}


def extract_truth(demo, match_id: int, start_time: int | None = None) -> dict:
    import polars as pl

    demo.load("objectives", "troopers", "urn")
    obj = demo.objectives.group_by("entity_id").agg(
        pl.col("objective_type").first(), pl.col("team_num").first(), pl.col("lane").first(),
        pl.col("x").first(), pl.col("y").first(), pl.col("max_health").max(),
    )
    guard = demo.troopers.filter(pl.col("trooper_type") == "trooper_boss").group_by(["team_num", "lane"]).agg(
        pl.col("x").first(), pl.col("y").first(), pl.col("max_health").max(),
    )
    urn = demo.urn
    return truth_from_rows(
        obj.to_dicts(), guard.to_dicts(), urn.select(["tick", "event", "x", "y"]).to_dicts() if urn is not None else [],
        match_id=match_id, build=getattr(demo, "build", None), start_time=start_time,
    )


def save_truth(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def load_truth(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
