"""Parse a .dem with Boon into the small ReplayData the rules use.

Boon (boon.readthedocs.io) returns Polars DataFrames. Demos recorded after the
Sept 29 2026 update need Boon >= 0.11. Times are converted to match-clock
seconds (pauses excluded), the same clock as match metadata.
"""
from __future__ import annotations

from pathlib import Path

from app.replay.jobs import ReplayData


def _match_seconds(demo, tick: int) -> float:
    t = demo.tick_to_match_seconds(tick)
    return float(t) if t is not None else float(demo.tick_to_seconds(tick))


def urn_episodes(rows: list[dict], to_seconds) -> list[dict]:
    """Group urn events (sorted by tick) into one episode per urn, ending at its return.

    Each episode has `checkpoints` [(t, x, y)] for every event, and `carriers`
    [(hero_id, t_pickup, t_drop_or_return)] so rules can follow the carrier.
    """
    episodes: list[dict] = []
    cur: dict | None = None
    for r in rows:
        t = to_seconds(r["tick"])
        ev = r["event"]
        point = (round(t, 1), float(r["x"]), float(r["y"]))
        if ev == "picked_up":
            if cur is None:
                cur = {"checkpoints": [], "carriers": []}
            cur["checkpoints"].append(point)
            cur["carriers"].append([int(r["hero_id"]), point[0], None])
        elif cur is None:
            continue  # delivery points toggling before anyone has the urn
        elif ev in ("dropped", "returned"):
            cur["checkpoints"].append(point)
            if cur["carriers"] and cur["carriers"][-1][2] is None:
                cur["carriers"][-1][2] = point[0]
            if ev == "returned":
                episodes.append(cur)
                cur = None
        elif ev in ("delivery_active", "delivery_inactive"):
            cur["checkpoints"].append(point)
    if cur is not None and cur["checkpoints"]:
        episodes.append(cur)
    return episodes


TEAM_FROM_BOON = {2: 0, 3: 1}  # Boon team numbers -> match teams; others (0 neutral, 4) -> None


def extract_zipline(demo, geo) -> dict | None:
    """Exact zipline control per lane from the replay's zipline nodes (analysis/zipline.py)."""
    from app.analysis.zipline import control_from_nodes

    nodes_df = demo.zipline_nodes
    changes_df = demo.zipline_changes
    if nodes_df is None or not nodes_df.height or changes_df is None or not changes_df.height:
        return None
    first = nodes_df.sort("tick").unique(subset=["node_handle"], keep="first")
    nodes = [
        {"handle": r["node_handle"], "lane": r["lane"], "x": r["x"], "y": r["y"], "capturable": r["capturable"]}
        for r in first.iter_rows(named=True)
    ]
    changes = [
        (_match_seconds(demo, r["tick"]), r["node_handle"], TEAM_FROM_BOON.get(r["team_num"]))
        for r in changes_df.sort("tick").iter_rows(named=True)
        if r["change"] in ("observed", "owner_changed")
    ]
    return control_from_nodes(nodes, changes, geo.lanes)


def parse_demo(
    path: Path, match_id: int, geo=None, start_time: int | None = None
) -> tuple[ReplayData, dict | None, dict | None, dict | None]:
    """Urn episodes for the rules; with `geo`, also trooper waves, live-map truth and zipline control."""
    from boon import Demo  # imported lazily: heavy native module

    from app.macro.truth import extract_truth
    from app.macro.waves import extract_waves

    demo = Demo(str(path), preload=False)
    notes: list[str] = []
    demo.load("urn")
    urn = demo.urn
    rows = urn.sort("tick").to_dicts() if urn is not None and urn.height else []
    episodes = urn_episodes(rows, lambda tick: _match_seconds(demo, tick))
    if not episodes:
        notes.append("No urn events found in this replay.")
    waves = extract_waves(demo, geo) if geo is not None else None
    truth = extract_truth(demo, match_id, start_time) if geo is not None else None
    zipline = extract_zipline(demo, geo) if geo is not None else None
    return ReplayData(match_id=match_id, urn_events=episodes, notes=notes), waves, truth, zipline
