"""Turn an item's raw properties into typed effects.

Each item property names the hero stat it changes (`provided_property_type`),
and conditional ones are flagged (`ConditionallyApplied`, a `conditional` text,
or listed in a passive/active tooltip section). Some effects land on the enemy
(resist shred, slows, healing cuts); those feed the target dummy, not your stats.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)")

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
    target: str  # self | enemy

    def to_dict(self) -> dict:
        return asdict(self)


def _sections(item: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in item.get("tooltip_sections") or []:
        kind = s.get("section_type") or "passive"
        for attr in s.get("section_attributes") or []:
            for field in ("properties", "elevated_properties", "important_properties"):
                for p in attr.get(field) or []:
                    out.setdefault(p, kind)
    return out


def item_effects(item: dict) -> list[Effect]:
    sections = _sections(item)
    out = []
    for prop, v in (item.get("properties") or {}).items():
        stat = v.get("provided_property_type")
        value = parse_number(v.get("value"))
        if not stat or stat == "MODIFIER_VALUE_INVALID" or not value:
            continue
        flags = v.get("usage_flags") or []
        condition = v.get("conditional")
        section = sections.get(prop)
        if section == "active":
            kind = "active"
        elif "ConditionallyApplied" in flags or "ConditionallyEnemyApplied" in flags or condition or section == "passive":
            kind = "conditional"
        else:
            kind = "always"
        enemy = (
            "ConditionallyEnemyApplied" in flags
            or stat in ENEMY_STATS
            or (stat in ENEMY_IF_NEGATIVE and value < 0 and kind != "always")
        )
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
                target="enemy" if enemy else "self",
            )
        )
    return out
