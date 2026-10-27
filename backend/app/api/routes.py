"""HTTP API under /api. Routes are sync: FastAPI runs them in a thread pool."""
from __future__ import annotations

import shutil

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.analysis.loader import load_context
from app.api.deps import coach, settings
from app.findings.engine import run_rules
from app.gamedata.client import ApiError, NotFound
from app.gamedata.steamid import parse_account_id
from app.replay.jobs import match_dir, replay_for, replay_status, run_job, set_status
from app.report import build_paths, build_report, hero_card, rank_info
from app.settings import Settings
from app.state import AppState
from app.trends import compute_trends, save_analysis

router = APIRouter()


def _account(s: Settings, account_id: int | None) -> int:
    acc = account_id or s.active_account
    if not acc:
        raise HTTPException(400, "Set your Steam ID in Settings first.")
    return acc


def _api_errors(fn):
    try:
        return fn()
    except NotFound as e:
        raise HTTPException(404, str(e))
    except ApiError as e:
        raise HTTPException(502, f"deadlock-api.com: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- meta / settings ---------------------------------------------------------------


@router.get("/meta")
def meta(st: AppState = Depends(coach), s: Settings = Depends(settings)):
    lo, hi = s.bracket
    return {
        "patch": st.gd.patch_status(),
        "offline": st.client.offline,
        "account_id": s.active_account,
        "using_sample": s.using_sample,
        "bracket": [lo, hi],
        "bracket_names": [rank_info(st.gd, lo), rank_info(st.gd, hi)],
    }


@router.get("/settings")
def get_settings(st: AppState = Depends(coach), s: Settings = Depends(settings)):
    profile = None
    if s.active_account:
        try:
            rows = st.gd.steam_profiles([s.active_account])
            if rows:
                profile = {"name": rows[0].get("personaname"), "avatar": rows[0].get("avatarmedium")}
        except ApiError:
            pass
    ranks = [
        {"tier": r["tier"], "name": r["name"], "image": (r.get("images") or {}).get("small_subrank1")}
        for r in st.gd.ranks() if r.get("tier")
    ]
    return {
        "account_id": s.account_id,
        "sample_account": s.sample_account,
        "using_sample": s.using_sample,
        "profile": profile,
        "bracket": list(s.bracket),
        "ranks": ranks,
    }


class SettingsIn(BaseModel):
    steam_id: str | None = None
    clear_account: bool = False
    bracket: tuple[int, int] | None = None


@router.put("/settings")
def put_settings(body: SettingsIn, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    if body.clear_account:
        s.account_id = None
    elif body.steam_id is not None:
        acc = parse_account_id(body.steam_id)
        if acc is None:
            raise HTTPException(400, "That does not look like a Steam ID.")
        s.account_id = acc
    if body.bracket:
        s.bracket = body.bracket
    return get_settings(st, s)


@router.get("/steam/search")
def steam_search(q: str = Query(min_length=2), st: AppState = Depends(coach)):
    rows = _api_errors(lambda: st.gd.steam_search(q))
    return [
        {"account_id": r["account_id"], "name": r.get("personaname"), "avatar": r.get("avatarmedium"),
         "badge": r.get("last_team_avg_badge"), "matches_30d": r.get("matches_played_last_30d")}
        for r in rows
    ]


@router.post("/gamedata/refresh")
def refresh_gamedata(st: AppState = Depends(coach)):
    dropped = st.gd.refresh_assets()
    for loader in (st.gd.heroes, st.gd.items, st.gd.ranks, st.gd.generic_data, st.gd.map_data, st.gd.npc_units, st.gd.enums):
        _api_errors(loader)
    return {"dropped": dropped, "patch": st.gd.patch_status()}


# ---- matches -----------------------------------------------------------------------


@router.get("/matches")
def matches(
    refresh: bool = False,
    limit: int = 50,
    account_id: int | None = None,
    st: AppState = Depends(coach),
    s: Settings = Depends(settings),
):
    acc = _account(s, account_id)
    history = _api_errors(lambda: st.gd.match_history(acc, force=refresh))
    modes = st.gd.enums().get("ECitadelMatchMode", {})
    out = []
    for m in history[:limit]:
        minutes = (m.get("match_duration_s") or 1) / 60
        out.append({
            "match_id": m["match_id"],
            "start_time": m.get("start_time"),
            "duration_s": m.get("match_duration_s"),
            "hero": hero_card(st.gd, m["hero_id"]),
            "won": m.get("match_result") == m.get("player_team"),
            "team": m.get("player_team"),
            "kills": m.get("player_kills"),
            "deaths": m.get("player_deaths"),
            "assists": m.get("player_assists"),
            "net_worth": m.get("net_worth"),
            "souls_per_min": round((m.get("net_worth") or 0) / minutes),
            "rank": rank_info(st.gd, m.get("ranked_display_badge")),
            "mode": modes.get(str(m.get("match_mode")), str(m.get("match_mode"))),
            "street_brawl": m.get("game_mode") != 1,
        })
    return {"account_id": acc, "using_sample": s.using_sample and not account_id, "matches": out}


@router.get("/matches/{match_id}/report")
def report(match_id: int, account_id: int | None = None, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    acc = _account(s, account_id)
    replay = replay_for(st, match_id)
    ctx = _api_errors(lambda: load_context(st.gd, match_id, acc, s.bracket, replay=replay))
    rules = run_rules(ctx)
    save_analysis(st, match_id, acc, s.bracket, rules, with_replay=replay is not None)
    return build_report(st.gd, ctx, rules, replay_status(st, match_id))


@router.get("/matches/{match_id}/paths")
def paths(
    match_id: int,
    step: int = Query(5, ge=1, le=30),
    account_id: int | None = None,
    st: AppState = Depends(coach),
    s: Settings = Depends(settings),
):
    acc = _account(s, account_id)
    ctx = _api_errors(lambda: load_context(st.gd, match_id, acc, s.bracket))
    from app.macro.movement import measure
    from app.replay.jobs import waves_for, zipline_for, zipline_map

    return build_paths(
        st.gd, ctx, step, start_reach=measure(st).get("start_reach"),
        exact=zipline_for(match_id), zip_map=zipline_map(), has_waves=waves_for(match_id) is not None,
    )


# ---- replays ------------------------------------------------------------------------

BUSY = ("downloading", "parsing")


@router.get("/matches/{match_id}/replay")
def get_replay(match_id: int, st: AppState = Depends(coach)):
    return replay_status(st, match_id)


@router.post("/matches/{match_id}/replay/fetch")
def fetch_replay(match_id: int, tasks: BackgroundTasks, st: AppState = Depends(coach)):
    if replay_status(st, match_id)["status"] in BUSY:
        return replay_status(st, match_id)
    set_status(st, match_id, "downloading")
    tasks.add_task(run_job, st, match_id)
    return replay_status(st, match_id)


@router.post("/matches/{match_id}/replay")
def upload_replay(match_id: int, tasks: BackgroundTasks, file: UploadFile = File(...), st: AppState = Depends(coach)):
    name = (file.filename or "").lower()
    if not (name.endswith(".dem") or name.endswith(".dem.bz2") or name.endswith(".bz2")):
        raise HTTPException(400, "Pick a .dem or .dem.bz2 replay file.")
    folder = match_dir(match_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / ("match.download" if name.endswith(".bz2") else "match.dem")
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out, 1 << 20)
    set_status(st, match_id, "parsing", path=str(dest))
    tasks.add_task(run_job, st, match_id, dest)
    return replay_status(st, match_id)


# ---- trends -------------------------------------------------------------------------


@router.get("/trends")
def trends(n: int = Query(20, ge=4, le=40), st: AppState = Depends(coach), s: Settings = Depends(settings)):
    acc = _account(s, None)
    data = _api_errors(lambda: compute_trends(st, acc, s.bracket, n, replays=lambda mid: replay_for(st, mid)))
    heroes = {m["hero_id"] for m in data["matches"]}
    data["heroes"] = {h: hero_card(st.gd, h) for h in heroes}
    data["using_sample"] = s.using_sample
    return data
