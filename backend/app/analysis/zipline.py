"""Which part of each lane's zipline each team owns, second by second.

Each lane's zipline is a chain of nodes (replay entity CCitadelZipLineNode). Checked on
replays of real matches (Boon `zipline_nodes` / `zipline_changes`):
- each team has a home stretch from its base that cannot be captured (16-25% of a lane);
- the middle is captured node by node by troopers: a team's reach sits at its own
  trooper front (median gap -0.4% of the lane) and stays after they fall back;
- the two teams' parts do not overlap; a neutral gap can sit between them;
- you ride only your team's part, both ways, at the same speed.

With a replay, ownership is exact (`control_from_nodes`). Without one, reach is tracked
from riders (`zipline_reach`): a rider at u proves their team owns up to u, and that the
enemy owns no more than 1 - u. Scored against 2 replays this is off by ~8% of the lane on
average (est.): troopers, which really move it, are not in match data.
u = 0 at your base, 1 at the enemy's.
"""
from __future__ import annotations

from collections import defaultdict

from app.analysis.model import MatchContext

MAX_LANE_DIST = 600  # units: further from every zipline than this is not riding a lane zipline
MIN_STEP = 0.01  # record a change of 1% of the lane or more
START_AT_S = 60  # the opening state: no wave has pushed yet


def lane_u(lane, team: int, x: float, y: float) -> float:
    """Fraction of the lane from `team`'s base (lanes run from team 0's end to team 1's)."""
    s, _ = lane.project(x, y)
    u = s / lane.length if lane.length else 0.0
    return u if team == 0 else 1 - u


# ---- exact, from a replay ------------------------------------------------------------


def _reach(strip: list[tuple[float, int | None]]) -> tuple[float, float]:
    """Contiguous ownership from each base along a lane's nodes sorted by u (team 0's view)."""
    r0 = 0.0
    for u, owner in strip:
        if owner != 0:
            break
        r0 = u
    r1 = 0.0
    for u, owner in reversed(strip):
        if owner != 1:
            break
        r1 = 1 - u
    return round(r0, 3), round(r1, 3)


def control_from_nodes(nodes: list[dict], changes: list[tuple[float, int, int | None]], lanes: dict) -> dict:
    """Exact zipline control from replay nodes.

    nodes: [{"handle", "lane", "x", "y", "capturable"}]; changes: [(seconds, handle, team or
    None)] in time order (team 0 / 1 as in match data, None = neutral).
    Returns {"timeline": {lane: [[t, r0, r1], ...]}, "home": {lane: [h0, h1]},
    "start": {lane: [s0, s1]}}; shares are of the lane from each team's own base.
    """
    u_of = {n["handle"]: lane_u(lanes[n["lane"]], 0, n["x"], n["y"]) for n in nodes if n["lane"] in lanes}
    lane_of = {n["handle"]: n["lane"] for n in nodes if n["handle"] in u_of}
    by_lane: dict[int, list[int]] = defaultdict(list)
    for h in u_of:
        by_lane[lane_of[h]].append(h)
    for hs in by_lane.values():
        hs.sort(key=lambda h: u_of[h])
    capturable = {n["handle"]: bool(n.get("capturable")) for n in nodes}
    home = {}
    for lane, hs in by_lane.items():
        fixed = [(u_of[h], None if capturable[h] else 0) for h in hs]
        h0, _ = _reach(fixed)
        _, h1 = _reach([(u, None if o is None else 1) for u, o in fixed])
        home[lane] = [h0, h1]
    owner: dict[int, int | None] = {}
    timeline = {lane: [[0, 0.0, 0.0]] for lane in by_lane}
    start = {}
    for t, handle, team in changes:
        lane = lane_of.get(handle)
        if lane is None:
            continue
        owner[handle] = team
        r0, r1 = _reach([(u_of[h], owner.get(h)) for h in by_lane[lane]])
        last = timeline[lane][-1]
        sec = max(0, round(t))
        if abs(r0 - last[1]) >= MIN_STEP or abs(r1 - last[2]) >= MIN_STEP:
            if last[0] == sec:
                last[1:] = [r0, r1]  # same second: keep the settled state
            else:
                timeline[lane].append([sec, r0, r1])
        if sec <= START_AT_S:
            start[lane] = [r0, r1]
    return {"timeline": {str(k): v for k, v in timeline.items()}, "home": {str(k): v for k, v in home.items()},
            "start": {str(k): v for k, v in start.items()}}


# ---- estimated, from riders -------------------------------------------------------------


def reach_from_samples(samples: dict[int, list[tuple[int, int, float]]], lane_ids: list[int], start,
                       min_step: float = MIN_STEP, home: dict | None = None) -> dict[int, list[list[float]]]:
    """Per lane: [[t, team 0 reach, team 1 reach], ...] at each change.

    `samples` maps a second to the riders then: (lane id, team, u from that team's base).
    `start` is one share for every lane, or {lane: [team 0, team 1]}. With `home`
    ({lane: [team 0, team 1]}), neither team's reach drops below its home stretch.
    """
    def begin(lane):
        return list(start[lane]) if isinstance(start, dict) and lane in start else [float(start)] * 2

    floor = {ln: (home or {}).get(ln, [0.0, 0.0]) for ln in lane_ids}
    reach = {ln: begin(ln) for ln in lane_ids}
    out = {ln: [[0, round(reach[ln][0], 3), round(reach[ln][1], 3)]] for ln in lane_ids}
    for t in sorted(samples):
        for lane, team, u in samples[t]:
            r = reach[lane]
            r[team] = max(r[team], min(u, 1 - floor[lane][1 - team]))
            r[1 - team] = max(floor[lane][1 - team], min(r[1 - team], 1 - u))  # parts never overlap
        for lane, r in reach.items():
            last = out[lane][-1]
            if abs(r[0] - last[1]) >= min_step or abs(r[1] - last[2]) >= min_step:
                out[lane].append([t, round(r[0], 3), round(r[1], 3)])
    return out


def zipline_reach(ctx: MatchContext, start, home: dict | None = None) -> dict[int, list[list[float]]]:
    """Estimated team zipline reach per lane through the match, from every player's riding."""
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
    return reach_from_samples(samples, [ln.id for ln in lanes], start, home=home)
