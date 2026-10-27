"""Which part of each lane's zipline each team owns, second by second.

Game settings describe ziplines made of nodes that teams capture ("captured zipline
nodes"), enemy ziplines with their own minimap colour, and troopers that drop off
before an enemy-captured zipline. Measured in 60 real matches:
- you ride only your team's part, both ways, at the same speed;
- each team starts owning the same share of every lane from its own base
  (`start_reach`, measured in macro/movement.py);
- nobody rides past the enemy's frontmost standing objective;
- the two teams' parts do not overlap.

So reach is tracked from riders: a rider at u proves their team owns the zipline up to
u, and that the enemy owns no more than 1 - u. u = 0 at your base, 1 at the enemy's.
It is a lower bound on what a team owns (est.): ground taken with no rider is not seen.
"""
from __future__ import annotations

from collections import defaultdict

from app.analysis.model import MatchContext

MAX_LANE_DIST = 600  # units: further from every zipline than this is not riding a lane zipline
MIN_STEP = 0.01  # record a change of 1% of the lane or more


def lane_u(lane, team: int, x: float, y: float) -> float:
    """Fraction of the lane from `team`'s base (lanes run from team 0's end to team 1's)."""
    s, _ = lane.project(x, y)
    u = s / lane.length if lane.length else 0.0
    return u if team == 0 else 1 - u


def reach_from_samples(samples: dict[int, list[tuple[int, int, float]]], lane_ids: list[int], start: float,
                       min_step: float = MIN_STEP) -> dict[int, list[list[float]]]:
    """Per lane: [[t, team 0 reach, team 1 reach], ...] at each change.

    `samples` maps a second to the riders then: (lane id, team, u from that team's base).
    """
    reach = {ln: [start, start] for ln in lane_ids}
    out = {ln: [[0, round(start, 3), round(start, 3)]] for ln in lane_ids}
    for t in sorted(samples):
        for lane, team, u in samples[t]:
            r = reach[lane]
            r[team] = max(r[team], u)
            r[1 - team] = min(r[1 - team], max(0.0, 1 - u))  # parts never overlap
        for lane, r in reach.items():
            last = out[lane][-1]
            if abs(r[0] - last[1]) >= min_step or abs(r[1] - last[2]) >= min_step:
                out[lane].append([t, round(r[0], 3), round(r[1], 3)])
    return out


def zipline_reach(ctx: MatchContext, start: float) -> dict[int, list[list[float]]]:
    """Team zipline reach per lane through the match, from every player's riding."""
    zip_id = ctx.enum_value("EMoveType", "Ziplining")
    lanes = list(ctx.geo.lanes.values())
    samples: dict[int, list[tuple[int, int, float]]] = defaultdict(list)
    for q in ctx.players:
        tr = q.track
        if tr is None or not tr.move or zip_id is None:
            continue
        for t in range(min(len(tr.move), ctx.duration_s)):
            if tr.move[t] != zip_id or (tr.health and tr.health[t] <= 0):
                continue
            x, y = tr.x[t], tr.y[t]
            lane = min(lanes, key=lambda ln: ln.dist(x, y))
            if lane.dist(x, y) <= MAX_LANE_DIST:
                samples[t].append((lane.id, q.team, lane_u(lane, q.team, x, y)))
    return reach_from_samples(samples, [ln.id for ln in lanes], start)
