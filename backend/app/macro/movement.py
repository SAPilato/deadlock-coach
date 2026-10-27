"""How fast players really travel: on foot vs on a zipline, measured from match data.

Match metadata has every player's position each second plus a movement type
(Valve's EMoveType: Normal, GroundDash, Slide, Ziplining, InAir, AirDash...).
From cached matches we measure, in game units per second:
- zipline: median speed over seconds spent ziplining;
- on foot: speed over 6 s windows out of combat and off ziplines. The median is
  ordinary movement; the 85th percentile is "optimal movement" (sprint, dash-jumps);
- detour: path length / straight-line distance over 20 s trips (streets bend);
  the median is ordinary travel, the lower quartile is the most direct routes;
- walkable cells: grid cells players actually stood in;
- zipline switches: one lane's zipline to another's within TRANSFER_GAP_S;
- start reach: how far along a lane, from your own base, anyone rides in the
  first START_S seconds, when each team owns its starting part (analysis/zipline.py).
Ziplines can be ridden both ways (convar citadel_zipline_allow_direction_choice).
"""
from __future__ import annotations

import json
import math
import statistics

from app.analysis.paths import decode_paths, zipline_rides
from app.analysis.zipline import MAX_LANE_DIST, lane_u
from app.state import AppState

GRID = 40
WINDOW_S = 6
TRIP_S = 20
OPTIMAL_PCT = 0.85  # est. "optimal movement" = the fastest 15% of real travel
MAX_MATCHES = 15
MAX_STEP_UNITS = 2500  # bigger 1 s jumps are teleports or respawns
ATTACH_S = 1.0  # est. time to latch on and drop off a zipline
TRANSFER_GAP_S = 8  # off one zipline and on another within this counts as a switch
START_S = 120  # the opening: no lane has been pushed yet

_memo: dict[int, dict] = {}


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def measure(st: AppState) -> dict:
    rows = st.db.all("SELECT payload FROM cache WHERE key LIKE '/v1/matches/%/metadata' LIMIT ?", (MAX_MATCHES,))
    if len(rows) in _memo:
        return _memo[len(rows)]
    enums = st.gd.enums()
    zip_id = next((int(k) for k, v in enums.get("EMoveType", {}).items() if v == "Ziplining"), None)
    out_id = next((int(k) for k, v in enums.get("ECombatType", {}).items() if v == "Out"), None)
    from app.analysis.loader import geometry

    geo = geometry(st.gd)
    zip_speeds: list[float] = []
    foot_speeds: list[float] = []
    detours: list[float] = []
    walkable: set[tuple[int, int]] = set()
    switch_gaps: list[int] = []
    start_us: list[float] = []
    matches = 0
    for r in rows:
        info = json.loads(r["payload"]).get("match_info", {})
        if info.get("game_mode") != 1:
            continue
        matches += 1
        team_of = {p["player_slot"]: p["team"] for p in info.get("players", [])}
        for tr in decode_paths(info.get("match_paths")).values():
            n = len(tr.x)
            if not tr.move or not tr.combat or not tr.health:
                continue
            step = [math.dist((tr.x[i], tr.y[i]), (tr.x[i + 1], tr.y[i + 1])) for i in range(n - 1)]
            for i in range(0, n, 5):
                left, top = geo.to_rel(tr.x[i], tr.y[i])
                if 0 <= left < 1 and 0 <= top < 1 and tr.health[i] > 0:
                    walkable.add((int(left * GRID), int(top * GRID)))
            for t in range(min(START_S, n)):
                if tr.move[t] == zip_id and tr.slot in team_of:
                    lane = min(geo.lanes.values(), key=lambda ln: ln.dist(tr.x[t], tr.y[t]))
                    if lane.dist(tr.x[t], tr.y[t]) <= MAX_LANE_DIST:
                        start_us.append(lane_u(lane, team_of[tr.slot], tr.x[t], tr.y[t]))
            rides = zipline_rides(tr, zip_id, geo.lanes.values())
            for r0, r1 in zip(rides, rides[1:]):
                if r0.lane_id != r1.lane_id and r1.start - r0.end <= TRANSFER_GAP_S:
                    switch_gaps.append(r1.start - r0.end)
            for i in range(n - 1):
                if tr.move[i] == zip_id and tr.move[i + 1] == zip_id and tr.health[i] > 0 and step[i] < MAX_STEP_UNITS:
                    zip_speeds.append(step[i])

            def clean(a: int, b: int) -> bool:
                return all(
                    tr.move[k] != zip_id and tr.combat[k] == out_id and tr.health[k] > 0 and step[k] < MAX_STEP_UNITS
                    for k in range(a, b)
                )

            for a in range(60, n - TRIP_S, WINDOW_S):
                if clean(a, a + WINDOW_S):
                    foot_speeds.append(sum(step[a:a + WINDOW_S]) / WINDOW_S)
            for a in range(60, n - TRIP_S, TRIP_S):
                if clean(a, a + TRIP_S):
                    path = sum(step[a:a + TRIP_S])
                    straight = math.dist((tr.x[a], tr.y[a]), (tr.x[a + TRIP_S], tr.y[a + TRIP_S]))
                    if straight > 2000:  # a real trip, not wandering on a spot
                        detours.append(path / straight)
    moving = [s for s in foot_speeds if s > 100]  # standing still is not travel
    heroes = [h["starting_stats"]["max_move_speed"]["value"] for h in st.gd.heroes() if h.get("player_selectable") and not h.get("disabled")]
    result = {
        "matches": matches,
        "zip_speed": statistics.median(zip_speeds) if zip_speeds else None,
        "foot_speed": statistics.median(moving) if moving else None,
        "fast_speed": _pct(moving, OPTIMAL_PCT),
        "detour": statistics.median(detours) if detours else None,
        "detour_best": _pct(detours, 0.25),  # the most direct quarter of real trips
        "samples": {"zip_s": len(zip_speeds), "foot_windows": len(moving), "trips": len(detours)},
        "attach_s": ATTACH_S,
        "switches": {"count": len(switch_gaps), "gap_s": statistics.median(switch_gaps) if switch_gaps else None},
        # How far each team's zipline reaches at the start, from its own base (share of the lane).
        "start_reach": _pct(start_us, 0.99),
        "avg_hero_move": sum(heroes) / len(heroes) if heroes else None,
        "grid": GRID,
        "walkable": sorted([i, j] for i, j in walkable),
    }
    _memo[len(rows)] = result
    return result
