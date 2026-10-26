"""Turn an item's raw properties into typed effects.

Each item property names the hero stat it changes (`provided_property_type`),
and conditional ones are flagged (`ConditionallyApplied`, a `conditional` text,
or listed in a passive/active tooltip section). Some effects land on the enemy
(resist shred, slows, healing cuts); those feed the target dummy, not your stats.
"""
from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass

NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)")

# Bonuses that only apply to some abilities (imbued or charged). Boon's rules keep
# these out of the global totals, so they are listed but never added to your stats.
ABILITY_ONLY = re.compile(r"Imbued|ChargedAbilities")

# A passive section is conditional only if its own text states a condition.
# "Reduces the Cooldown of your abilities." is always on;
# "While you are above 65% health, gain ..." is not.
CONDITION_RE = re.compile(
    r"\b((?:while|when|whenever|after|if|against|below|above|for the next|on (?:hit|kill|cast)|your next)\b[^,.;]*)",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")

# Not effects: the distance a "within/beyond Range" condition refers to.
RANGE_PARAMS = {
    "MODIFIER_VALUE_BONUS_WEAPON_DAMAGE_CLOSE_RANGE_MAX_RANGE",
    "MODIFIER_VALUE_BONUS_BULLET_DAMAGE_LONG_RANGE_MIN_RANGE",
}

# Effects that change the enemy, not the item's owner.
ENEMY_STATS = {
    "MODIFIER_VALUE_TECH_RESIST_REDUCTION",
    "MODIFIER_VALUE_BULLET_AND_MELEE_RESIST_REDUCTION",
    "MODIFIER_VALUE_MELEE_RESIST_REDUCTION",
    "MODIFIER_VALUE_MOVEMENT_SPEED_SLOW_PERCENT",
    "MODIFIER_VALUE_FIRE_RATE_SLOW",
    "MODIFIER_VALUE_MOVE_SPEED_LIMIT",
    "MODIFIER_VALUE_MOVEMENT_GROUND_DASH_REDUCTION_PERCENT",
    "MODIFIER_VALUE_TECH_DAMAGE_TAKEN_HEALS_ATTACKER",
}
# Negative and conditional: a debuff your item puts on the enemy (e.g. healing cut).
ENEMY_IF_NEGATIVE = {
    "MODIFIER_VALUE_HEAL_AMP_RECEIVE_PERCENT",
    "MODIFIER_VALUE_HEAL_AMP_REGEN_PERCENT",
    "MODIFIER_VALUE_ALL_DAMAGE_MULTIPLIER",
}


def parse_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = NUM_RE.match(str(value))
    return float(m.group(1)) if m else None


@dataclass
class Effect:
    key: str  # "<item_id>:<property>", stable id for toggles
    item_id: int
    item: str
    prop: str
    label: str
    stat: str
    value: float
    postfix: str
    kind: str  # always | conditional | active
    condition: str | None
    target: str  # self | enemy | ability (only some of your abilities)

    def to_dict(self) -> dict:
        return asdict(self)


def tooltip_condition(loc: str | None) -> str | None:
    """The condition phrase in a tooltip line, e.g. 'While you are above 65% health'."""
    if not loc:
        return None
    text = " ".join(TAG_RE.sub(" ", html.unescape(loc)).split())
    m = CONDITION_RE.search(text)
    if not m:
        return None
    words = m.group(1).split()
    phrase = " ".join(words[:9]) + ("…" if len(words) > 9 else "")
    return phrase[0].lower() + phrase[1:]


def _sections(item: dict) -> dict[str, tuple[str, str | None]]:
    """property -> (section type, condition phrase from that section's text)."""
    out: dict[str, tuple[str, str | None]] = {}
    for s in item.get("tooltip_sections") or []:
        kind = s.get("section_type") or "passive"
        for attr in s.get("section_attributes") or []:
            cond = tooltip_condition(attr.get("loc_string"))
            for field in ("properties", "elevated_properties", "important_properties"):
                for p in attr.get(field) or []:
                    out.setdefault(p, (kind, cond))
    return out


def item_effects(item: dict) -> list[Effect]:
    sections = _sections(item)
    props = item.get("properties") or {}
    range_text = next(
        (f"{parse_number(v.get('value')):g}{(v.get('postfix') or '').strip()}"
         for v in props.values() if v.get("provided_property_type") in RANGE_PARAMS and parse_number(v.get("value"))),
        None,
    )
    out = []
    for prop, v in props.items():
        stat = v.get("provided_property_type")
        value = parse_number(v.get("value"))
        if not stat or stat == "MODIFIER_VALUE_INVALID" or stat in RANGE_PARAMS or not value:
            continue
        flags = v.get("usage_flags") or []
        section, section_cond = sections.get(prop, (None, None))
        condition = v.get("conditional")
        if condition and range_text:
            condition = condition.replace("Range", range_text)
        flagged = "ConditionallyApplied" in flags or "ConditionallyEnemyApplied" in flags
        if section == "active":
            kind = "active"
        elif flagged or condition or (section == "passive" and section_cond):
            kind = "conditional"
            condition = condition or section_cond
        else:
            kind = "always"
        enemy = (
            "ConditionallyEnemyApplied" in flags
            or stat in ENEMY_STATS
            or (stat in ENEMY_IF_NEGATIVE and value < 0 and kind != "always")
            or (value < 0 and "Reduction" in prop)  # e.g. Spirit Sap's TechPowerReduction
        )
        target = "enemy" if enemy else "ability" if ABILITY_ONLY.search(prop) else "self"
        out.append(
            Effect(
                key=f"{item['id']}:{prop}",
                item_id=item["id"],
                item=item.get("name", str(item["id"])),
                prop=prop,
                label=v.get("label") or prop,
                stat=stat,
                value=value,
                postfix=(v.get("postfix") or "").strip(),
                kind=kind,
                condition=condition,
                target=target,
            )
        )
    return out
