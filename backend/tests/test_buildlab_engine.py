import math

import pytest

from app.buildlab.effects import item_effects
from app.buildlab.engine import (
    Target,
    boon_count,
    compute,
    fire_rate_modifier,
    resistance,
    stack,
)


@pytest.fixture(scope="module")
def data(seed_gd):
    items = seed_gd.items()
    return {
        "heroes": [h for h in seed_gd.heroes() if h.get("player_selectable") and not h.get("disabled")],
        "by_class": {i["class_name"]: i for i in items},
        "by_name": {i["name"]: i for i in items if i.get("type") == "upgrade" and i.get("shopable")},
    }


def hero_named(data, name):
    return next(h for h in data["heroes"] if h["name"] == name)


def weapon_of(data, hero):
    return data["by_class"][hero["items"]["weapon_primary"]]


def row(sheet, key):
    return next(r for r in sheet.rows if r.key == key).value


# ---- Boon's documented examples --------------------------------------------------------


def test_boon_rule_examples():
    assert stack([40, 20]) == pytest.approx(52)
    assert stack([22, 30]) == pytest.approx(45.4)
    assert resistance(0, [40, 20], [-25, -20]) == pytest.approx(12)
    assert fire_rate_modifier([18, 20, -20, -30]) == pytest.approx(-6)
    assert fire_rate_modifier([-90]) == -50  # floor


def test_clip_rule_example():
    hero = {"starting_stats": {}, "level_info": {"1": {}}}
    weapon = {"weapon_info": {"clip_size": 20, "shots_per_second": 1, "bullet_damage": 1}}
    items = [
        {"id": 1, "name": "A", "cost": 0, "item_slot_type": "weapon",
         "properties": {"C": {"value": "10", "provided_property_type": "MODIFIER_VALUE_AMMO_CLIP_SIZE"}}},
        {"id": 2, "name": "B", "cost": 0, "item_slot_type": "weapon",
         "properties": {"P": {"value": "15", "provided_property_type": "MODIFIER_VALUE_AMMO_CLIP_SIZE_PERCENT"}}},
        {"id": 3, "name": "C", "cost": 0, "item_slot_type": "weapon",
         "properties": {"P": {"value": "4", "provided_property_type": "MODIFIER_VALUE_AMMO_CLIP_SIZE_PERCENT"}}},
    ]
    assert row(compute(hero, weapon, items, 1), "clip_size") == 36


# ---- anchored to the API's own numbers -----------------------------------------------------


def test_base_dps_matches_api_for_every_hero(data):
    checked = 0
    for hero in data["heroes"]:
        weapon = weapon_of(data, hero)
        w = weapon.get("weapon_info")
        if not w or not w.get("damage_per_second"):
            continue
        sheet = compute(hero, weapon, [], level=1)
        assert sheet.dps["gun_dps"] == pytest.approx(w["damage_per_second"], rel=1e-6), hero["name"]
        assert sheet.dps["dps_reload"] == pytest.approx(w["damage_per_second_with_reload"], rel=1e-6), hero["name"]
        checked += 1
    assert checked > 30


def test_level_growth_comes_from_hero_data(data):
    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    top = max(int(k) for k in hero["level_info"])
    boons = boon_count(hero, top)
    assert boon_count(hero, 1) == 0 and boons > 10
    growth = hero["standard_level_up_upgrades"]["MODIFIER_VALUE_BASE_HEALTH_FROM_LEVEL"]
    base = hero["starting_stats"]["max_health"]["value"]
    assert row(compute(hero, weapon, [], top), "max_health") == pytest.approx(base + boons * growth)


# ---- items -------------------------------------------------------------------------------


def test_flat_item_adds_exactly_its_value(data):
    hero = hero_named(data, "Paradox")
    extra = data["by_name"]["Extra Health"]
    bonus = float(extra["properties"]["BonusHealth"]["value"])
    before = row(compute(hero, weapon_of(data, hero), [], 1), "max_health")
    after = row(compute(hero, weapon_of(data, hero), [extra], 1), "max_health")
    assert after - before == pytest.approx(bonus)


def test_conditional_effect_needs_toggle(data):
    hero = hero_named(data, "Paradox")
    cq = data["by_name"]["Close Quarters"]
    effects = item_effects(cq)
    eff = next(e for e in effects if e.stat == "MODIFIER_VALUE_CLOSE_RANGE_WEAPON_DAMAGE_INCREASE")
    assert eff.kind == "conditional" and eff.condition == "within 15m"  # range folded into the condition
    assert not any(e.stat.endswith("_MAX_RANGE") for e in effects)
    off = compute(hero, weapon_of(data, hero), [cq], 1)
    on = compute(hero, weapon_of(data, hero), [cq], 1, toggles={eff.key})
    assert row(on, "weapon_damage") - row(off, "weapon_damage") == pytest.approx(eff.value)
    assert on.dps["gun_dps"] > off.dps["gun_dps"]


def test_passive_text_decides_what_is_conditional(data):
    def effect(item, stat):
        return next(e for e in item_effects(data["by_name"][item]) if e.stat == stat)

    cdr = effect("Superior Cooldown", "MODIFIER_VALUE_COOLDOWN_REDUCTION_PERCENTAGE")
    assert cdr.kind == "always"  # "Reduces the Cooldown of your abilities."
    emblem = effect("Enchanter's Emblem", "MODIFIER_VALUE_TECH_POWER")
    assert emblem.kind == "conditional" and "65% health" in emblem.condition
    opening = next(
        e for e in item_effects(data["by_name"]["Opening Rounds"]) if e.prop == "BaseAttackDamagePercentBonus"
    )
    assert opening.kind == "conditional" and "50% health" in opening.condition


def test_enemy_debuffs_hit_the_dummy_not_you(data):
    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    rusted = data["by_name"]["Rusted Barrel"]
    effects = item_effects(rusted)
    assert all(e.target == "enemy" for e in effects if e.stat == "MODIFIER_VALUE_FIRE_RATE_SLOW")
    shred = next(e for e in effects if e.stat == "MODIFIER_VALUE_BULLET_AND_MELEE_RESIST_REDUCTION")
    target = Target(bullet_resist=30)
    off = compute(hero, weapon, [rusted], 1, target=target)
    on = compute(hero, weapon, [rusted], 1, toggles={shred.key}, target=target)
    assert row(off, "fire_rate") == row(compute(hero, weapon, [], 1), "fire_rate")
    assert on.dps["target_resist"] == pytest.approx(30 - abs(shred.value))
    assert on.dps["effective"] > off.dps["effective"]


def test_ability_only_and_enemy_spirit_effects_stay_out_of_your_spirit(data):
    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    base = row(compute(hero, weapon, [], 1), "spirit_power")
    for name in ("Extra Charge", "Spirit Sap"):
        item = data["by_name"][name]
        kinds = {e.target for e in item_effects(item) if e.stat == "MODIFIER_VALUE_TECH_POWER"}
        assert kinds <= {"ability", "enemy"}, (name, kinds)
        assert row(compute(hero, weapon, [item], 1), "spirit_power") == base
    extra = data["by_name"]["Extra Spirit"]
    assert row(compute(hero, weapon, [extra], 1), "spirit_power") > base


def test_weapon_spending_bonus_uses_highest_threshold(data):
    hero = hero_named(data, "Paradox")
    t3 = next(i for i in data["by_name"].values() if i["item_slot_type"] == "weapon" and i["item_tier"] == 3)
    sheet = compute(hero, weapon_of(data, hero), [t3], 1)
    table = hero["cost_bonuses"]["weapon"]
    expected = max(r["bonus"] for r in table if r["gold_threshold"] <= t3["cost"])
    assert row(sheet, "bonus_weapon") == expected
    assert sheet.spend["weapon"] == t3["cost"]


def test_resist_items_stack_multiplicatively(data):
    hero = hero_named(data, "Paradox")
    resil = data["by_name"]["Bullet Resilience"]
    value = next(e.value for e in item_effects(resil) if e.stat == "MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST")
    sheet = compute(hero, weapon_of(data, hero), [resil], 1)
    assert row(sheet, "bullet_resist") == pytest.approx(value)


def test_ability_damage_scales_with_spirit_and_upgrades(data, seed_gd):
    from app.buildlab.catalog import hero_abilities

    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    kit = hero_abilities(seed_gd, hero)
    grenade = next(a for a in kit if a["name"] == "Pulse Grenade")
    prop = grenade["properties"]["PulseDamage"]
    base, factor = float(prop["value"]), prop["scale_function"]["stat_scale"]
    spirit_items = [data["by_name"]["Extra Spirit"], data["by_name"]["Improved Spirit"]]

    no_items = compute(hero, weapon, [], 1, abilities=kit)
    built = compute(hero, weapon, spirit_items, 1, abilities=kit)
    spirit = row(built, "spirit_power")
    line = next(a for a in built.abilities if a["name"] == "Pulse Grenade")["lines"][0]
    assert line["base"] == pytest.approx(base)  # level 1: no boons, no spirit
    assert line["value"] == pytest.approx(base + factor * spirit)

    # Upgrades add flat damage and extra spirit scaling, from the ability's own data.
    upgraded = compute(hero, weapon, spirit_items, 1, abilities=kit, ability_tier=2)
    up = next(a for a in upgraded.abilities if a["name"] == "Pulse Grenade")["lines"][0]
    assert up["factor"] > factor and up["value"] > line["value"]
    assert next(a for a in no_items.abilities if a["name"] == "Pulse Grenade")["lines"][0]["factor"] == factor


def test_only_damage_values_are_listed(data, seed_gd):
    from app.buildlab.catalog import hero_abilities

    for hero in data["heroes"]:
        sheet = compute(hero, weapon_of(data, hero), [], 1, abilities=hero_abilities(seed_gd, hero))
        for a in sheet.abilities:
            for line in a["lines"]:
                assert not any(w in line["label"].lower() for w in ("interval", "tick", "duration", "radius")), line


def test_cooldown_reduction_and_spirit_resist_apply_to_abilities(data, seed_gd):
    from app.buildlab.catalog import hero_abilities

    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    kit = hero_abilities(seed_gd, hero)
    cdr = data["by_name"]["Superior Cooldown"]
    pct = float(cdr["properties"]["CooldownReduction"]["value"])
    sheet = compute(hero, weapon, [cdr], 1, abilities=kit, target=Target(spirit_resist=25))
    grenade = next(a for a in sheet.abilities if a["name"] == "Pulse Grenade")
    assert grenade["cooldown"] == pytest.approx(grenade["cooldown_base"] * (1 - pct / 100))
    assert grenade["lines"][0]["vs_dummy"] == pytest.approx(grenade["lines"][0]["value"] * 0.75)


def test_headshots_and_resist_change_time_to_kill(data):
    hero = hero_named(data, "Paradox")
    weapon = weapon_of(data, hero)
    plain = compute(hero, weapon, [], 1, target=Target(hp=1000))
    tanky = compute(hero, weapon, [], 1, target=Target(hp=1000, bullet_resist=50))
    aimed = compute(hero, weapon, [], 1, target=Target(hp=1000, headshot_pct=100))
    assert tanky.dps["ttk"] == pytest.approx(plain.dps["ttk"] * 2)
    assert aimed.dps["ttk"] < plain.dps["ttk"]
    assert math.isclose(plain.dps["ttk"], 1000 / plain.dps["effective"])
