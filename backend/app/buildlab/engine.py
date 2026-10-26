"""Build Lab stat engine.

Inputs are game data only: the hero record (base stats, per-boon growth,
spending bonuses, spirit scaling), its primary weapon record and item
properties. How numbers combine follows Boon's documented stat rules
(boon.readthedocs.io/en/latest/hero-stats.html) where one exists.

Every row carries a status:
  data  - read or summed straight from game data
  rule  - a Boon-documented equation
  est   - our assumption; the UI shows an "est." tag
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from app.buildlab.effects import Effect, item_effects

SLOT_TYPES = ("weapon", "vitality", "spirit")

M = "MODIFIER_VALUE_"


@dataclass
class Target:
    """The DPS dummy. Resist is the dummy's own, before your shred."""

    hp: float = 2500.0
    bullet_resist: float = 0.0
    headshot_pct: float = 0.0


@dataclass
class Row:
    key: str
    label: str
    group: str
    value: float | None
    unit: str = ""
    status: str = "data"
    better: str = "higher"
    note: str | None = None


@dataclass
class Sheet:
    level: int
    boons: int
    souls_for_level: int | None
    cost: int
    spend: dict[str, int]
    rows: list[Row]
    dps: dict
    effects: list[dict]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rows"] = [asdict(r) for r in self.rows]
        return d


# ---- helpers ---------------------------------------------------------------------


def boon_count(hero: dict, level: int) -> int:
    """Levels up to `level` that grant the standard per-boon stat growth."""
    info = hero.get("level_info") or {}
    return sum(1 for k, v in info.items() if int(k) <= level and v.get("use_standard_upgrade"))


def souls_for_level(hero: dict, level: int) -> int | None:
    row = (hero.get("level_info") or {}).get(str(level))
    return row.get("required_gold") if row else None


def max_level(hero: dict) -> int:
    return max((int(k) for k in (hero.get("level_info") or {"1": {}})), default=1)


def spend_bonus(table: list[dict], spent: float) -> float:
    """Highest spending threshold reached (hero `cost_bonuses`)."""
    reached = [r["bonus"] for r in table or [] if spent >= r["gold_threshold"]]
    return max(reached) if reached else 0.0


def stack(percents: list[float]) -> float:
    """100 * (1 - prod(1 - p/100)): Boon's rule for resist, lifesteal, debuff resist."""
    keep = 1.0
    for p in percents:
        keep *= 1 - p / 100
    return 100 * (1 - keep)


def fire_rate_modifier(values: list[float]) -> float:
    """Boon fire_rate.v1: positives add, negatives are slows that multiply, floor -50."""
    remaining = 1.0
    bonus = 0.0
    for v in values:
        if v >= 0:
            bonus += v
        else:
            remaining *= 1 - abs(v) / 100
    return max(-50.0, bonus - 100 * (1 - remaining))


def rate_multiplier(modifier: float) -> float:
    return 1 + modifier / 100 if modifier >= 0 else 1 / (1 + abs(modifier) / 100)


def resistance(innate: float, sources: list[float], reductions: list[float]) -> float:
    """Boon damage-resistance rule: stack sources on innate, subtract stacked reductions."""
    resist = 100 * (1 - (1 - innate / 100) * (1 - stack(sources) / 100))
    return resist - stack([abs(r) for r in reductions])


# ---- main ---------------------------------------------------------------------------


def compute(
    hero: dict,
    weapon: dict,
    items: list[dict],
    level: int,
    toggles: set[str] | frozenset[str] = frozenset(),
    target: Target | None = None,
) -> Sheet:
    target = target or Target()
    w = weapon.get("weapon_info") or {}
    base = {k: v.get("value") for k, v in (hero.get("starting_stats") or {}).items()}
    growth = hero.get("standard_level_up_upgrades") or {}
    scaling = hero.get("scaling_stats") or {}
    boons = boon_count(hero, level)

    effects: list[Effect] = [e for it in items for e in item_effects(it)]
    on = [e for e in effects if e.kind == "always" or e.key in toggles]
    mine = [e for e in on if e.target == "self"]
    theirs = [e for e in on if e.target == "enemy"]

    def each(stat: str) -> list[float]:
        return [e.value for e in mine if e.stat == M + stat]

    def total(stat: str) -> float:
        return sum(each(stat))

    spend = {s: sum(int(it.get("cost") or 0) for it in items if it.get("item_slot_type") == s) for s in SLOT_TYPES}
    bonus = {s: spend_bonus((hero.get("cost_bonuses") or {}).get(s, []), spend[s]) for s in SLOT_TYPES}
    rows: list[Row] = []
    notes: list[str] = []

    # Spirit power: (base + flat) * prod(1 + pct) — Boon's global spirit rule.
    spirit_pct = each("TECH_POWER_PERCENT")
    spirit = (boons * growth.get(M + "TECH_POWER", 0) + total("TECH_POWER"))
    for p in spirit_pct:
        spirit *= 1 + p / 100

    def scaled(stat_type: str) -> tuple[float, bool]:
        s = scaling.get(stat_type)
        return (spirit * s["scale"], True) if s and s.get("scaling_stat") == "ETechPower" else (0.0, False)

    # ---- weapon -------------------------------------------------------------------
    wd_sources = each("WEAPON_DAMAGE_INCREASE") + each("CLOSE_RANGE_WEAPON_DAMAGE_INCREASE") + each("LONG_RANGE_BULLET_DAMAGE_INCREASE")
    weapon_damage = sum(wd_sources) + bonus["weapon"]
    bd_scale, bd_scaled = scaled("EBulletDamage")
    bullet_base = (w.get("bullet_damage") or 0) + boons * growth.get(M + "BASE_BULLET_DAMAGE_FROM_LEVEL", 0) + bd_scale
    bullet = bullet_base * (1 + weapon_damage / 100)

    fr_scale, fr_scaled = scaled("EFireRate")
    fire_mod = fire_rate_modifier(each("FIRE_RATE") + ([fr_scale] if fr_scaled else []))
    rps_scale, rps_scaled = scaled("ERoundsPerSecond")
    shots = (w.get("shots_per_second") or 0) * rate_multiplier(fire_mod) + rps_scale

    clip_scale, clip_scaled = scaled("EClipSize")
    clip_flat = (w.get("clip_size") or 0) + total("AMMO_CLIP_SIZE") + clip_scale
    clip = math.ceil(clip_flat * (1 + total("AMMO_CLIP_SIZE_PERCENT") / 100)) if clip_flat else 0

    reload_adj = each("RELOAD_SPEED")
    reload = (w.get("reload_duration") or 0) * (1 + sum(reload_adj) / 100)

    all_dmg = 1.0
    for p in each("ALL_DAMAGE_MULTIPLIER"):
        all_dmg *= 1 + p / 100
    bullets = w.get("bullets") or 1
    gun_dps = bullet * bullets * shots * all_dmg

    # Reload-inclusive DPS: anchored to the API's own base number, scaled by our model.
    def uptime(c: float, s: float, r: float) -> float:
        fire_time = c / s if s else 0
        return fire_time / (fire_time + r) if fire_time + r else 1.0

    base_dps, base_dps_r = w.get("damage_per_second"), w.get("damage_per_second_with_reload")
    api_reload_factor = (base_dps_r / base_dps) if base_dps and base_dps_r else 1.0
    f0 = uptime(w.get("clip_size") or 0, w.get("shots_per_second") or 1, w.get("reload_duration") or 0)
    f = uptime(clip, shots, reload)
    dps_reload = gun_dps * api_reload_factor * (f / f0 if f0 else 1)

    # Melee: Boon light/heavy melee rule (documented as following player observations: est.)
    light0 = base.get("light_melee_damage") or 0
    melee_growth = boons * growth.get(M + "BASE_MELEE_DAMAGE_FROM_LEVEL", 0)

    def melee(base_damage: float, stat_type: str) -> float:
        with_growth = base_damage + melee_growth * (base_damage / light0 if light0 else 1)
        bonus_spirit, _ = scaled(stat_type)
        return (with_growth + bonus_spirit) * (1 + (weapon_damage / 2 + total("MELEE_DAMAGE_INCREASE")) / 100)

    rows += [
        Row("bullet_damage", "Bullet damage", "Weapon", bullet, "", "est" if (weapon_damage or bd_scaled) else "data",
            note="Base + boon growth, times weapon damage %."),
        Row("weapon_damage", "Weapon damage", "Weapon", weapon_damage, "%", "rule", note="Item bonuses + weapon spending bonus (Boon rule)."),
        Row("fire_rate", "Fire rate", "Weapon", fire_mod, "%", "est" if fr_scaled else "rule"),
        Row("shots_per_second", "Shots / second", "Weapon", shots, "", "est" if rps_scaled else "rule"),
        Row("clip_size", "Clip size", "Weapon", clip, "", "est" if clip_scaled else "rule"),
        Row("reload_time", "Reload time", "Weapon", reload, "s", "rule" if len(reload_adj) <= 1 else "est", better="lower"),
        Row("gun_dps", "Gun DPS (no reload)", "Weapon", gun_dps, "", "est" if (bd_scaled or all_dmg != 1 or weapon_damage) else "data"),
        Row("light_melee", "Light melee", "Weapon", melee(light0, "ELightMeleeDamage"), "", "est"),
        Row("heavy_melee", "Heavy melee", "Weapon", melee(base.get("heavy_melee_damage") or 0, "EHeavyMeleeDamage"), "", "est"),
        Row("bullet_lifesteal", "Bullet lifesteal", "Weapon", stack(each("BULLET_LIFESTEAL")), "%", "rule"),
    ]

    # ---- vitality -----------------------------------------------------------------
    hp_pct, base_hp_pct = each("HEALTH_MAX_PERCENT"), each("BASE_HEALTH_PERCENT")
    hp_base = ((base.get("max_health") or 0) + boons * growth.get(M + "BASE_HEALTH_FROM_LEVEL", 0)) * (1 + sum(base_hp_pct) / 100)
    health = (hp_base + total("HEALTH_MAX")) * (1 + sum(hp_pct) / 100)
    ms_scale, ms_scaled = scaled("EMaxMoveSpeed")
    sprint_scale, sprint_scaled = scaled("ESprintSpeed")
    move = ((base.get("max_move_speed") or 0) + total("MOVEMENT_SPEED_MAX") + ms_scale) * (1 + total("MOVEMENT_SPEED_MAX_PERCENT") / 100)
    rows += [
        Row("max_health", "Max health", "Vitality", health, "", "est" if hp_pct or base_hp_pct else "data"),
        Row("health_regen", "Health regen / s", "Vitality", (base.get("base_health_regen") or 0) + total("HEALTH_REGEN_PER_SECOND"), "", "data"),
        Row("ooc_regen", "Out of combat regen", "Vitality", (base.get("ooc_health_regen") or 0) + total("OUT_OF_COMBAT_HEALTH_REGEN"), "", "data"),
        Row("bullet_resist", "Bullet resist", "Vitality",
            resistance(boons * growth.get(M + "BULLET_ARMOR_DAMAGE_RESIST", 0), each("BULLET_ARMOR_DAMAGE_RESIST"), []), "%", "rule"),
        Row("spirit_resist", "Spirit resist", "Vitality",
            resistance(boons * growth.get(M + "TECH_RESIST", 0), each("TECH_RESIST"), []), "%", "rule"),
        Row("melee_resist", "Melee resist", "Vitality", resistance(0, each("MELEE_RESIST"), []), "%", "rule"),
        Row("move_speed", "Move speed", "Vitality", move, "m/s", "est" if ms_scaled else "rule"),
        Row("sprint_speed", "Sprint bonus", "Vitality",
            (base.get("sprint_speed") or 0) + total("SPRINT_SPEED_BONUS") + sprint_scale, "m/s", "est" if sprint_scaled else "rule"),
        Row("stamina", "Stamina", "Vitality", (base.get("stamina") or 0) + total("STAMINA"), "", "rule"),
    ]

    # ---- spirit -------------------------------------------------------------------
    rows += [
        Row("spirit_power", "Spirit power", "Spirit", spirit, "", "rule"),
        Row("cooldown_reduction", "Cooldown reduction", "Spirit", stack(each("COOLDOWN_REDUCTION_PERCENTAGE")), "%", "est"),
        Row("ability_range", "Ability range", "Spirit", total("TECH_RANGE_PERCENT"), "%", "est"),
        Row("ability_duration", "Ability duration", "Spirit", total("BONUS_ABILITY_DURATION_PERCENTAGE"), "%", "est"),
        Row("spirit_lifesteal", "Spirit lifesteal", "Spirit", stack(each("TECH_LIFESTEAL")), "%", "rule"),
    ]

    # ---- spending bonuses (the game data gives the %, not always which stat) -------------
    rows += [
        Row("bonus_weapon", "Weapon spending bonus", "Spending", bonus["weapon"], "%", "data", note="Counted in weapon damage."),
        Row("bonus_vitality", "Vitality spending bonus", "Spending", bonus["vitality"], "%", "data",
            note="Game data gives the %, not the stat it boosts. Not added to other rows."),
        Row("bonus_spirit", "Spirit spending bonus", "Spending", bonus["spirit"], "%", "data",
            note="Game data gives the %, not the stat it boosts. Not added to other rows."),
    ]

    # ---- DPS dummy (all estimates) ----------------------------------------------------
    crit = w.get("crit_bonus_start") or 1.0
    shred = [e.value for e in theirs if e.stat == M + "BULLET_AND_MELEE_RESIST_REDUCTION"]
    target_resist = resistance(0, [target.bullet_resist], shred)
    hs = max(0.0, min(100.0, target.headshot_pct)) / 100
    effective = dps_reload * (1 + hs * (crit - 1)) * (1 - target_resist / 100)
    dps = {
        "gun_dps": gun_dps,
        "dps_reload": dps_reload,
        "effective": effective,
        "ttk": (target.hp / effective) if effective > 0 else None,
        "headshot_mult": crit,
        "target_resist": target_resist,
        "shred": stack([abs(s) for s in shred]),
        "api_base_dps": base_dps,
        "api_base_dps_reload": base_dps_r,
    }
    if any(s for s in (bd_scaled, clip_scaled, fr_scaled, rps_scaled, ms_scaled, sprint_scaled)):
        notes.append("This hero scales some stats with spirit power. Those rows are estimates.")

    return Sheet(
        level=level,
        boons=boons,
        souls_for_level=souls_for_level(hero, level),
        cost=sum(spend.values()),
        spend=spend,
        rows=rows,
        dps=dps,
        effects=[{**e.to_dict(), "on": e.kind == "always" or e.key in toggles} for e in effects],
        notes=notes,
    )
