"""Hero list and item shop for the Build Lab, with win rates at your rank."""
from __future__ import annotations

import logging

from app.buildlab.effects import item_effects
from app.buildlab.engine import boon_count, max_level, souls_for_level
from app.gamedata.client import ApiError
from app.gamedata.service import GameData

log = logging.getLogger(__name__)


def playable_heroes(gd: GameData) -> list[dict]:
    out = []
    for h in gd.heroes():
        if not h.get("player_selectable") or h.get("disabled") or h.get("in_development"):
            continue
        imgs = h.get("images", {})
        out.append({"id": h["id"], "name": h["name"], "image": imgs.get("icon_image_small") or imgs.get("icon_hero_card")})
    return sorted(out, key=lambda h: h["name"])


def hero_and_weapon(gd: GameData, hero_id: int) -> tuple[dict, dict]:
    hero = gd.hero_map().get(hero_id)
    if not hero:
        raise ValueError(f"Unknown hero {hero_id}")
    weapon_class = (hero.get("items") or {}).get("weapon_primary")
    weapon = next((i for i in gd.items() if i.get("class_name") == weapon_class), None)
    if not weapon:
        raise ValueError(f"No weapon data for {hero.get('name')}")
    return hero, weapon


def shop_items(gd: GameData, hero_id: int) -> list[dict]:
    return [
        i for i in gd.items()
        if i.get("type") == "upgrade" and i.get("shopable") and (not i.get("heroes") or hero_id in i["heroes"])
    ]


def _line(e) -> str:
    sign = "+" if e.value > 0 else ""
    value = f"{e.value:g}"
    unit = e.postfix if e.postfix in ("%", "m", "m/s", "s") else ""
    return f"{sign}{value}{unit} {e.label}"


def shop(gd: GameData, hero_id: int, bracket: tuple[int, int]) -> dict:
    hero, _ = hero_and_weapon(gd, hero_id)
    stats: dict[int, dict] = {}
    hero_games = None
    try:
        stats = {r["item_id"]: r for r in gd.item_stats(hero_id, bracket)}
        hero_games = next((r["matches"] for r in gd.hero_stats(bracket) if r["hero_id"] == hero_id), None)
    except ApiError as e:
        log.info("No item stats for hero %s: %s", hero_id, e)
    items = []
    for it in shop_items(gd, hero_id):
        effects = item_effects(it)
        always = [e for e in effects if e.kind == "always" and e.target != "enemy"]
        s = stats.get(it["id"])
        items.append({
            "id": it["id"],
            "name": it["name"],
            "tier": it.get("item_tier"),
            "cost": it.get("cost"),
            "slot": it.get("item_slot_type"),
            "image": it.get("shop_image") or it.get("image"),
            "active": bool(it.get("is_active_item")),
            "lines": [_line(e) for e in always[:3]],
            "conditional": sum(1 for e in effects if e.kind != "always"),
            "win_rate": round(s["wins"] / s["matches"], 3) if s and s.get("matches") else None,
            "games": s.get("matches") if s else None,
            "pick_rate": round(s["matches"] / hero_games, 3) if s and hero_games else None,
            "avg_buy_s": round(s["avg_buy_time_s"]) if s and s.get("avg_buy_time_s") else None,
        })
    items.sort(key=lambda i: (i["slot"] or "", i["tier"] or 0, i["cost"] or 0, i["name"]))
    top = max_level(hero)
    return {
        "hero": {"id": hero["id"], "name": hero["name"]},
        "items": items,
        "levels": [
            {"level": lv, "souls": souls_for_level(hero, lv), "boons": boon_count(hero, lv)} for lv in range(1, top + 1)
        ],
        "bracket": list(bracket),
        "has_rank_stats": bool(stats),
    }
