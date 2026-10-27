"""Build Lab API: heroes, shop, stat sheets, saved builds, import from a match."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.api.deps import coach, settings
from app.api.routes import _account, _api_errors
from app.buildlab import store
from app.buildlab.catalog import hero_abilities, hero_and_weapon, item_lines, playable_heroes, shop, shop_items
from app.buildlab.helper import counter_items, phase_picks, souls_curve, spike_steps
from app.buildlab.engine import Target, compute, max_level
from app.buildlab.slots import slot_limit
from app.gamedata.client import ApiError
from app.settings import Settings
from app.state import AppState

router = APIRouter()


@router.get("/buildlab/heroes")
def heroes(st: AppState = Depends(coach)):
    return _api_errors(lambda: playable_heroes(st.gd))


@router.get("/buildlab/shop")
def get_shop(hero_id: int, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    data = _api_errors(lambda: shop(st.gd, hero_id, s.bracket))
    data["slots"] = slot_limit(st)
    return data


def sheet_for(st: AppState, b: store.BuildIn) -> dict:
    hero, weapon = hero_and_weapon(st.gd, b.hero_id)
    valid = {i["id"]: i for i in shop_items(st.gd, b.hero_id)}
    slots = slot_limit(st)
    picked, warnings = [], []
    for iid in b.items:
        if iid not in valid:
            warnings.append(f"Item {iid} is not in this patch's shop.")
        elif iid in {p["id"] for p in picked}:
            warnings.append(f"{valid[iid]['name']} is already in the build.")
        elif len(picked) >= slots["limit"]:
            warnings.append(f"Only {slots['limit']} item slots. {valid[iid]['name']} left out.")
        else:
            picked.append(valid[iid])
    level = max(1, min(b.level, max_level(hero)))
    sheet = compute(
        hero, weapon, picked, level, set(b.toggles), Target(**b.target.model_dump()),
        abilities=hero_abilities(st.gd, hero), ability_tier=b.ability_tier,
    )
    return {
        **sheet.to_dict(),
        "hero": {"id": hero["id"], "name": hero["name"]},
        "items": [p["id"] for p in picked],
        "slots": slots,
        "warnings": warnings,
        "weapon_image": (hero.get("shop_stat_display") or {}).get("weapon_stats_display", {}).get("weapon_image"),
    }


@router.post("/buildlab/compute")
def compute_build(b: store.BuildIn, st: AppState = Depends(coach)):
    return _api_errors(lambda: sheet_for(st, b))


# ---- saved builds ----------------------------------------------------------------------


@router.get("/builds")
def list_builds(st: AppState = Depends(coach)):
    return store.list_builds(st.db)


@router.post("/builds")
def save_build(b: store.SavedBuildIn, st: AppState = Depends(coach)):
    _api_errors(lambda: hero_and_weapon(st.gd, b.hero_id))
    return store.get(st.db, store.save(st.db, b))


@router.delete("/builds/{build_id}")
def delete_build(build_id: int, st: AppState = Depends(coach)):
    if not store.delete(st.db, build_id):
        raise HTTPException(404, "No such build.")
    return {"deleted": build_id}


@router.get("/builds/{build_id}/export")
def export_build(build_id: int, st: AppState = Depends(coach)):
    b = store.get(st.db, build_id)
    if not b:
        raise HTTPException(404, "No such build.")
    hero = st.gd.hero_map().get(b["hero_id"], {})
    names = {i["id"]: i["name"] for i in st.gd.items()}
    data = store.export(b, hero.get("name", str(b["hero_id"])), names, st.gd.live_build())
    filename = "".join(c if c.isalnum() else "-" for c in b["name"]).strip("-") or "build"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{filename}.json"'})


@router.post("/builds/import")
def import_build(data: dict, st: AppState = Depends(coach)):
    try:
        b = store.parse_export(data)
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, f"Could not read that build file: {e}")
    return save_build(b, st)


# ---- build used in a real match ----------------------------------------------------------


# ---- build helper ----------------------------------------------------------------------


def _shop_map(st: AppState, hero_id: int) -> dict[int, dict]:
    return {i["id"]: i for i in shop_items(st.gd, hero_id)}


CURVE_GAMES = 8


def _your_souls(st: AppState, s: Settings, hero_id: int) -> dict | None:
    """Your average souls over time: this hero's recent games if 3+, else any recent games."""
    if not s.active_account:
        return None
    try:
        recent = [m for m in st.gd.match_history(s.active_account) if m.get("game_mode") == 1][:20]
    except ApiError:
        return None
    mine = [m for m in recent if m.get("hero_id") == hero_id]
    pool, hero_only = (mine, True) if len(mine) >= 3 else (recent, False)
    games = []
    for m in pool[:CURVE_GAMES]:
        try:
            info = st.gd.match_metadata(m["match_id"])
        except ApiError:
            continue
        info = info.get("match_info", info)
        me = next((p for p in info.get("players", []) if p["account_id"] == s.active_account), None)
        if me:
            games.append([(x["time_stamp_s"], x["net_worth"]) for x in me.get("stats") or []])
    curve = souls_curve(games)
    return {"curve": curve, "games": len(games), "this_hero": hero_only} if curve else None


@router.get("/buildlab/helper/phases")
def helper_phases(hero_id: int, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    """Most-bought items per phase for your hero and rank."""
    return _api_errors(lambda: {**phase_picks(st.gd.item_flow(hero_id, s.bracket), _shop_map(st, hero_id)), "bracket": list(s.bracket)})


@router.post("/buildlab/helper/spikes")
def helper_spikes(b: store.BuildIn, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    """Each item in build order: what it adds and when you would have it."""

    def run():
        hero, weapon = hero_and_weapon(st.gd, b.hero_id)
        valid = _shop_map(st, b.hero_id)
        try:
            typical = {r["item_id"]: round(r["avg_buy_time_s"]) for r in st.gd.item_stats(b.hero_id, s.bracket) if r.get("avg_buy_time_s")}
        except ApiError:
            typical = {}
        yours = _your_souls(st, s, b.hero_id)
        steps = spike_steps(
            hero, weapon, [valid[i] for i in b.items if i in valid], hero_abilities(st.gd, hero),
            Target(**b.target.model_dump()), yours["curve"] if yours else None, typical,
        )
        return {"steps": steps, "pace": {k: v for k, v in yours.items() if k != "curve"} if yours else None}

    return _api_errors(run)


@router.get("/buildlab/helper/counters")
def helper_counters(
    hero_id: int,
    enemies: str = Query(..., description="Comma-separated enemy hero ids (up to 6)"),
    st: AppState = Depends(coach),
    s: Settings = Depends(settings),
):
    """Items that win more than usual for your hero against these enemy heroes."""

    def run():
        ids = list(dict.fromkeys(int(x) for x in enemies.split(",") if x.strip()))[:6]
        if not ids:
            raise ValueError("Pick at least one enemy hero.")
        names = {h["id"]: h["name"] for h in st.gd.heroes()}
        shop_map = _shop_map(st, hero_id)
        out = counter_items(
            st.gd.item_stats(hero_id, s.bracket),
            {e: st.gd.item_stats(hero_id, s.bracket, enemy_id=e) for e in ids},
            shop_map,
            {e: names.get(e, str(e)) for e in ids},
        )
        for row in out["buy"] + out["skip"]:
            row["lines"] = item_lines(shop_map[row["id"]], 2)
        return {**out, "enemies": ids, "bracket": list(s.bracket)}

    return _api_errors(run)


@router.get("/matches/{match_id}/enemies")
def match_enemies(match_id: int, account_id: int | None = None, st: AppState = Depends(coach), s: Settings = Depends(settings)):
    """The enemy heroes you faced in a match."""
    acc = _account(s, account_id)
    info = _api_errors(lambda: st.gd.match_metadata(match_id))
    info = info.get("match_info", info)
    me = next((p for p in info["players"] if p["account_id"] == acc), None)
    if me is None:
        raise HTTPException(404, "You did not play in this match.")
    return {"match_id": match_id, "hero_id": me["hero_id"], "enemies": [p["hero_id"] for p in info["players"] if p["team"] != me["team"]]}


@router.get("/matches/{match_id}/build")
def match_build(
    match_id: int,
    t: int | None = Query(None, ge=0),
    account_id: int | None = None,
    st: AppState = Depends(coach),
    s: Settings = Depends(settings),
):
    acc = _account(s, account_id)
    meta = _api_errors(lambda: st.gd.match_metadata(match_id))
    info = meta.get("match_info", meta)
    me = next((p for p in info["players"] if p["account_id"] == acc), None)
    if me is None:
        raise HTTPException(404, "You did not play in this match.")
    at = info["duration_s"] if t is None else min(t, info["duration_s"])
    items = st.gd.item_map()
    owned = [
        it["item_id"] for it in sorted(me.get("items") or [], key=lambda i: i["game_time_s"])
        if items.get(it["item_id"], {}).get("type") == "upgrade"
        and it["game_time_s"] <= at
        and not (it.get("sold_time_s") and it["sold_time_s"] <= at)
    ]
    level = me.get("level") or 1
    if t is not None:
        snaps = [x for x in me.get("stats") or [] if x["time_stamp_s"] <= at]
        level = snaps[-1].get("level", level) if snaps else 1
    hero = st.gd.hero_map().get(me["hero_id"], {})
    return {
        "hero_id": me["hero_id"],
        "level": level,
        "items": list(dict.fromkeys(owned)),
        "at": at,
        "name": f"{hero.get('name', 'Hero')} · match {match_id}",
    }
