"""Macro Map API: layers, waves, heatmap, decision scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analysis.loader import geometry
from app.api.deps import coach, settings
from app.api.routes import _account, _api_errors
from app.buildlab.catalog import playable_heroes
from app.gamedata.client import ApiError
from app.macro.heatmap import heatmap
from app.macro.layers import TEAM_NAMES, build_layers
from app.macro.movement import measure
from app.macro.scenarios import list_scenarios, scenario
from app.replay.jobs import SEED_REPLAYS, matches_with_waves, waves_for
from app.report import hero_card
from app.settings import Settings
from app.state import AppState

router = APIRouter(prefix="/macro")


@router.get("/layers")
def layers(st: AppState = Depends(coach)):
    data = _api_errors(lambda: build_layers(st.gd, geometry(st.gd)))
    heroes = {h["id"]: h for h in st.gd.heroes()}
    data["heroes"] = [
        {**h, "move": heroes[h["id"]]["starting_stats"]["max_move_speed"]["value"],
         "sprint": heroes[h["id"]]["starting_stats"]["sprint_speed"]["value"]}
        for h in playable_heroes(st.gd)
    ]
    return data


def _wave_schedule(st: AppState) -> dict | None:
    c = st.gd.convar
    try:
        c("citadel_trooper_spawn_initial")
    except ApiError:
        return None
    return {
        "first": c("citadel_trooper_spawn_initial"),
        "every": c("citadel_trooper_spawn_interval_early"),
        "late_every": c("citadel_trooper_spawn_interval_late"),
        "late_after_min": c("citadel_trooper_spawn_interval_late_time"),
        "very_late_every": c("citadel_trooper_spawn_interval_very_late"),
        "very_late_after_min": c("citadel_trooper_spawn_interval_very_late_time"),
        "squad": c("citadel_trooper_squad_size"),
    }


def _match_side(st: AppState, match_id: int, accounts: list[int | None]) -> dict:
    """Hero and team of the first listed account found in the match."""
    try:
        info = st.gd.match_metadata(match_id)["match_info"]
    except (ApiError, KeyError):
        return {}
    for acc in accounts:
        me = next((p for p in info["players"] if p["account_id"] == acc), None)
        if me:
            return {"hero": hero_card(st.gd, me["hero_id"]), "team": me["team"], "start_time": info.get("start_time")}
    return {"start_time": info.get("start_time")}


@router.get("/waves")
def waves(match_id: int | None = None, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    accounts = [s.account_id, s.sample_account]
    available = []
    for mid in matches_with_waves():
        side = _match_side(st, mid, accounts)
        available.append({"match_id": mid, "sample": (SEED_REPLAYS / str(mid)).exists(), **side})
    if not available:
        return {"available": [], "frames": [], "meets": []}
    chosen = match_id or available[0]["match_id"]
    data = waves_for(chosen)
    if data is None:
        raise HTTPException(404, "No wave data for that match. Load its replay first.")
    geo = geometry(st.gd)
    lanes = [
        {"id": L.id, "name": L.name, "color": L.color,
         "pts": [[round(a, 4), round(b, 4)] for a, b in (geo.to_rel(x, y) for x, y in L.points)]}
        for L in geo.lanes.values()
    ]
    me = next((a for a in available if a["match_id"] == chosen), {})
    return {
        "available": available,
        "match_id": chosen,
        "my_team": me.get("team"),
        "teams": TEAM_NAMES,
        "lanes": lanes,
        "schedule": _wave_schedule(st),
        **data,
    }


@router.get("/movement")
def movement(st: AppState = Depends(coach)):
    return _api_errors(lambda: measure(st))


@router.get("/heatmap")
def get_heatmap(n: int = Query(10, ge=1, le=20), st: AppState = Depends(coach), s: Settings = Depends(settings)):
    acc = _account(s, None)
    return _api_errors(lambda: heatmap(st, acc, s.bracket, n))


@router.get("/scenarios")
def scenarios(st: AppState = Depends(coach), s: Settings = Depends(settings)):
    acc = _account(s, None)
    rows = _api_errors(lambda: list_scenarios(st, acc, s.bracket))
    for r in rows:
        r["hero"] = hero_card(st.gd, r.pop("hero_id"))
    return rows


@router.get("/scenario")
def get_scenario(match_id: int, t: int = Query(ge=0), st: AppState = Depends(coach), s: Settings = Depends(settings)):
    acc = _account(s, None)
    return _api_errors(lambda: scenario(st, acc, match_id, t, s.bracket))
