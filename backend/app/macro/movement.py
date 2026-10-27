"""How fast players really travel: on foot vs on a zipline, measured from match data.

Two profiles, same method: yours (your cached matches) and high rank (the newest ranked
matches this patch with lobbies averaging HIGH_RANK_BADGE or more: Ascendant 1+).

Route times: `progress_fast` / `progress_normal` are straight-line progress (units/s) on
real out-of-combat foot trips of PROGRESS_S seconds covering PROGRESS_MIN_UNITS or more:
the fastest 15% and the median. Bends, jumps and dashes are all inside that number, so
the planner uses it with no separate detour factor. Checked by running the planner on
those trips: the fastest 15% of foot trips match it within ~3%. RIDE_OVERHEAD_S per
zipline ride (getting to it, mounting, the reach being an estimate) was calibrated the
same way on zipline trips.

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
HIGH_RANK_BADGE = 101  # Ascendant 1 (ranks: tier * 10 + subrank; Ascendant = tier 10)
MAX_STEP_UNITS = 2500  # bigger 1 s jumps are teleports or respawns
ATTACH_S = 1.0  # est. time to latch on and drop off a zipline (the old model; see RIDE_OVERHEAD_S)
PROGRESS_S = 30  # route-time trips: this long, out of combat, alive
PROGRESS_MIN_UNITS = 5000  # ...and covering at least this far (a real trip across the map)
# est. Calibrated on 1,159 of your zipline trips: with this per ride, the fastest 15% match
# the planner (1.01x). High-rank zipline trips still ran ~12% slower than predicted.
RIDE_OVERHEAD_S = 5.0
TRANSFER_GAP_S = 8  # off one zipline and on another within this counts as a switch
START_S = 120  # the opening: no lane has been pushed yet

_memo: dict[int, dict] = {}


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def measure(st: AppState) -> dict:
    """Your movement: matches you played (any cached match when none are, e.g. the sample)."""
    from app.settings import Settings

    acc = Settings(st.db).active_account
    infos, others = [], []
    for r in st.db.all("SELECT payload FROM cache WHERE key LIKE '/v1/matches/%/metadata'"):
        info = json.loads(r["payload"]).get("match_info", {})
        if info.get("game_mode") != 1:
            continue
        (infos if any(p.get("account_id") == acc for p in info.get("players", [])) else others).append(info)
    infos = sorted(infos or others, key=lambda i: -(i.get("start_time") or 0))[:MAX_MATCHES]
    return _measure(st, infos)


def measure_high(st: AppState) -> dict | None:
    """High-rank movement: the newest ranked matches this patch in Ascendant+ lobbies."""
    from datetime import datetime

    from app.gamedata.client import ApiError

    patch = st.gd.latest_patch()
    since = int(datetime.fromisoformat(patch["date"].replace("Z", "+00:00")).timestamp()) if patch and patch.get("date") else None
    try:
        rows = st.gd.high_rank_matches(HIGH_RANK_BADGE, since, MAX_MATCHES)
    except ApiError:
        return None
    infos = []
    for m in rows:
        try:
            meta = st.gd.match_metadata(m["match_id"])
        except ApiError:
            continue
        info = meta.get("match_info", meta)
        info["_average_badge"] = m.get("average_badge")
        infos.append(info)
    if not infos:
        return None
    out = _measure(st, infos)
    badges = [i["_average_badge"] for i in infos if i.get("_average_badge")]
    out["badges"] = [min(badges), max(badges)] if badges else None
    return out


def _measure(st: AppState, infos: list[dict]) -> dict:
    key = tuple(sorted(i.get("match_id") or 0 for i in infos))
    if key in _memo:
        return _memo[key]
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
    progress: list[float] = []
    matches = 0
    for info in infos:
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
            for a in range(120, n - PROGRESS_S, 15):
                if clean(a, a + PROGRESS_S):
                    straight = math.dist((tr.x[a], tr.y[a]), (tr.x[a + PROGRESS_S], tr.y[a + PROGRESS_S]))
                    if straight >= PROGRESS_MIN_UNITS:
                        progress.append(straight / PROGRESS_S)
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
        "samples": {"zip_s": len(zip_speeds), "foot_windows": len(moving), "trips": len(detours), "route_trips": len(progress)},
        "attach_s": ATTACH_S,
        # Route-time model the planner uses (see module docstring).
        "progress_fast": _pct(progress, OPTIMAL_PCT),
        "progress_normal": statistics.median(progress) if progress else None,
        "ride_overhead_s": RIDE_OVERHEAD_S,
        "switches": {"count": len(switch_gaps), "gap_s": statistics.median(switch_gaps) if switch_gaps else None},
        # How far each team's zipline reaches at the start, from its own base (share of the lane).
        "start_reach": _pct(start_us, 0.99),
        "avg_hero_move": sum(heroes) / len(heroes) if heroes else None,
        "grid": GRID,
        "walkable": sorted([i, j] for i, j in walkable),
    }
    _memo[key] = result
    return result
