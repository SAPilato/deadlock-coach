"""Build helper: phase picks, spikes along a build order, counters vs enemy heroes."""
from app.buildlab.catalog import hero_abilities, hero_and_weapon, shop_items
from app.buildlab.engine import Target
from app.buildlab.helper import (
    MIN_GAMES, counter_items, level_for_souls, phase_picks, souls_curve, spike_steps, time_for_souls,
)


def _shop(n=4):
    return {i: {"id": i, "name": f"Item {i}", "item_tier": 1, "cost": 800, "item_slot_type": "weapon"} for i in range(1, n + 1)}


def test_phase_picks_rank_by_pick_rate_and_drop_rare_items():
    flow = {
        "reached_per_column": [1000, 900, 0, 0],
        "baseline": {"wins": 520, "matches": 1000},
        "nodes": [
            {"column": 0, "item_id": 1, "wins": 300, "matches": 600},
            {"column": 0, "item_id": 2, "wins": 500, "matches": 800},
            {"column": 0, "item_id": 3, "wins": 10, "matches": 20},  # 2%: too rare
            {"column": 0, "item_id": 99, "wins": 500, "matches": 900},  # not a shop item
            {"column": 1, "item_id": 1, "wins": 200, "matches": 450},
        ],
    }
    out = phase_picks(flow, _shop())
    assert [i["id"] for i in out["phases"][0]["items"]] == [2, 1]
    assert out["phases"][0]["items"][0]["pick_rate"] == 0.8
    assert out["phases"][1]["items"][0]["pick_rate"] == 0.5
    assert out["phases"][2]["items"] == [] and out["win_rate"] == 0.52


def test_souls_curve_and_time_for_souls():
    games = [[(180, 1800), (360, 3600)], [(180, 1200), (360, 2400), (540, 4000)]]
    curve = souls_curve(games, step=60)
    assert curve[0] == (0, 0.0)
    assert curve[3] == (180, 1500.0)  # average of both games at 3:00
    assert curve[-1][0] == 360  # stops once fewer than 2 games are still running
    assert time_for_souls(curve, 1500) == 180
    assert time_for_souls(curve, 10**6) is None


def test_counters_compare_each_item_with_its_own_other_games():
    shop = _shop()
    n = 400
    base = [
        {"item_id": 1, "wins": 1000, "matches": 2000},  # 50% overall
        {"item_id": 2, "wins": 1000, "matches": 2000},
        {"item_id": 3, "wins": 1000, "matches": 2000},
    ]
    vs = {7: [
        {"item_id": 1, "wins": int(0.62 * n), "matches": n},  # clearly better vs hero 7
        {"item_id": 2, "wins": int(0.51 * n), "matches": n},  # noise
        {"item_id": 3, "wins": int(0.38 * n), "matches": n},  # clearly worse
        {"item_id": 4, "wins": 5, "matches": MIN_GAMES - 1},  # too few games
    ]}
    out = counter_items(base, vs, shop, {7: "Haze"})
    assert [r["id"] for r in out["buy"]] == [1]
    assert out["buy"][0]["strong_vs"] == ["Haze"] and out["buy"][0]["delta"] > 0.1
    assert [r["id"] for r in out["skip"]] == [3]


def test_spikes_flag_the_big_weapon_spending_threshold(seed_gd):
    hero = next(h for h in seed_gd.heroes() if h.get("player_selectable") and not h.get("disabled") and h.get("cost_bonuses"))
    hero, weapon = hero_and_weapon(seed_gd, hero["id"])
    weapon_items = sorted(
        (i for i in shop_items(seed_gd, hero["id"]) if i.get("item_slot_type") == "weapon" and i.get("cost") == 800),
        key=lambda i: i["id"],
    )[:6]
    table = hero["cost_bonuses"]["weapon"]
    big = next(r for r, prev in zip(table[1:], table) if r["bonus"] - prev["bonus"] >= 15)
    steps = spike_steps(hero, weapon, weapon_items, hero_abilities(seed_gd, hero), Target(),
                        curve=[(0, 0.0), (600, 6000.0)], typical_buy_s={weapon_items[0]["id"]: 300})
    assert [s["souls"] for s in steps] == [800 * k for k in range(1, 7)]
    assert steps[0]["at_s"] == 80 and steps[0]["typical_s"] == 300
    assert steps[1]["level"] == level_for_souls(hero, 1600)
    crossing = next(s for s in steps if s["bonus"] and s["bonus"]["threshold"] == big["gold_threshold"])
    assert crossing["spike"] and crossing["bonus"]["jump"] >= 15
    assert not steps[0]["spike"]  # the first small threshold is not a spike
