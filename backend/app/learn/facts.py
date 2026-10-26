"""Numbers for lesson cards, read from game data at request time.

Each fact says where it came from: "game data" (assets, generic data, game
settings), "measured" (our analysis of real matches) or "replay" (a parsed
post-update replay). A fact whose data is missing is simply left out.
"""
from __future__ import annotations

import logging
from collections import Counter

from app.gamedata.client import ApiError
from app.state import AppState

log = logging.getLogger(__name__)


def _clock(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def _weapon_spend_bonus(st: AppState) -> str | None:
    """The biggest step in the weapon spending table most heroes share."""
    tables = Counter(
        tuple((r["gold_threshold"], r["bonus"]) for r in (h.get("cost_bonuses") or {}).get("weapon", []))
        for h in st.gd.heroes() if h.get("player_selectable") and not h.get("disabled")
    )
    table = tables.most_common(1)[0][0] if tables else ()
    best, prev = None, 0.0
    for threshold, bonus in table:
        if best is None or bonus - prev > best[2]:
            best = (threshold, bonus, bonus - prev)
        prev = bonus
    if not best:
        return None
    return f"Spend {best[0]:,} souls on weapon items: +{best[1]:g}% weapon damage."


def lesson_facts(st: AppState) -> dict[str, dict]:
    gd = st.gd
    out: dict[str, dict] = {}

    def add(key: str, source: str, make) -> None:
        try:
            text = make()
        except (ApiError, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            log.info("Lesson fact %s unavailable: %s", key, e)
            return
        if text:
            out[key] = {"text": text, "source": source}

    c = gd.convar
    add("wave_timing", "game data", lambda: (
        f"First wave at {_clock(c('citadel_trooper_spawn_initial'))}. "
        f"Then every {c('citadel_trooper_spawn_interval_early'):g} s, "
        f"every {c('citadel_trooper_spawn_interval_late'):g} s after {c('citadel_trooper_spawn_interval_late_time'):g} min."
    ))
    add("wave_squad", "game data", lambda: f"Troopers come in squads of {c('citadel_trooper_squad_size')}.")
    add("orb_split", "game data", lambda: (
        f"In lane, {100 - 100 * c('citadel_trooper_instant_gold_ratio_laning'):.0f}% of trooper souls drop as an orb."
    ))
    add("trooper_souls", "game data", lambda: (
        f"A trooper is worth {c('citadel_trooper_gold_reward')} souls, plus "
        f"{c('citadel_trooper_gold_reward_bonus_per_minute'):g} per game minute."
    ))

    npc = {u.get("class_name"): u for u in gd.npc_units()}
    params = gd.generic_data().get("objective_params") or {}
    add("guardian_hp", "game data", lambda: f"A Guardian has {npc['npc_boss_tier1']['max_health']:,} HP.")
    add("guardian_bounty", "game data", lambda: f"A Guardian is worth {params['tier1_gold_kill']:,} souls.")
    add("objective_bounties", "game data", lambda: (
        f"Souls: Walker {params['tier2_gold_kill']:,} · Shrine {params['shrines_gold_kill']:,} · "
        f"Base Guardian {params['base_guardians_gold_kill']:,}."
    ))
    rejuv = gd.generic_data().get("rejuv_params") or {}
    add("rejuvenator", "game data", lambda: f"Mid Boss gives the Rejuvenator for {rejuv['rejuvinator_buff_duration']:g} s.")

    m = gd.map_data()
    add("camp_counts", "game data", lambda: (
        lambda k: f"{sum(k.values())} Haunt camps: {k['weak']} weak, {k['medium']} medium, "
                  f"{k['strong']} strong, {k['vault']} vaults."
    )(Counter(cp.get("kind") for cp in m["neutral_camps"])))
    add("crate_counts", "game data", lambda: (
        f"{len(m['entities']['crates'])} crates and {len(m['entities']['tough_crates'])} tough crates on the map."
    ))
    loot = (gd.generic_data().get("breakable_powerup_loot_params") or {}).get("pickups_by_match_time_mins") or {}
    add("buff_types", "game data", lambda: (
        f"Buff containers hold {len({k.split('_permanent')[0] for t in loot.values() for k in t})} kinds of permanent buff."
        if loot else None
    ))
    prices = gd.generic_data().get("item_price_per_tier") or []
    add("item_prices", "game data", lambda: "Item tiers cost " + ", ".join(f"{p:,}" for p in prices[1:5]) + " souls.")
    add("weapon_spend_bonus", "game data", lambda: _weapon_spend_bonus(st))

    from app.macro.movement import measure

    add("zip_vs_run", "measured", lambda: (
        lambda mv: f"Ziplines are {mv['zip_speed'] / mv['fast_speed']:.1f}× faster than optimal running."
    )(measure(st)))

    from app.replay.jobs import latest_truth

    add("urn_sites", "replay", lambda: (
        lambda t: f"{len(t['urn_sites'])} urn sites: it spawns at one, you deliver to the other."
        if t and len(t.get("urn_sites", [])) == 2 else None
    )(latest_truth()))
    return out


def lessons_with_facts(st: AppState) -> list[dict]:
    from app.learn.lessons import LESSONS

    facts = lesson_facts(st)
    return [{**lesson, "facts": [facts[k] for k in lesson["facts"] if k in facts]} for lesson in LESSONS]
