"""Parse enum values from Valve's protobuf definitions (SteamDatabase/Protobufs).

Objective ids, gold sources, combat and movement types in match metadata are
protobuf enums. We read them from the .proto file instead of hardcoding them.
"""
from __future__ import annotations

import re

ENUM_RE = re.compile(r"enum\s+(\w+)\s*\{([^}]*)\}")
VALUE_RE = re.compile(r"(\w+)\s*=\s*(-?\d+)\s*;")
PREFIX_RE = re.compile(r"^k_[eE](?:[A-Z][A-Za-z0-9]*_)?(.+)$")

WANTED = ("ECitadelTeamObjective", "ECombatType", "EMoveType", "EGoldSource", "ECitadelMatchMode")


def short_name(full: str) -> str:
    m = PREFIX_RE.match(full)
    return m.group(1) if m else full


def parse_enums(text: str, wanted: tuple[str, ...] = WANTED) -> dict[str, dict[str, str]]:
    """Return {enum_name: {value_as_str: short_name}}. First definition wins."""
    out: dict[str, dict[str, str]] = {}
    for name, body in ENUM_RE.findall(text):
        if wanted and name not in wanted or name in out:
            continue
        out[name] = {str(int(v)): short_name(k) for k, v in VALUE_RE.findall(body)}
    return out


def objective_parts(short: str) -> dict:
    """'Tier1_Lane3' -> {'kind': 'tier1', 'lane': 3}. Works on names from ECitadelTeamObjective."""
    lane = re.search(r"Lane(\d+)", short)
    index = re.search(r"_(\d+)$", short)
    s = short.lower()
    if s.startswith("tier1"):
        kind = "tier1"
    elif s.startswith("tier2"):
        kind = "tier2"
    elif s.startswith("barrackboss"):
        kind = "barracks"
    elif s.startswith("titanshieldgenerator"):
        kind = "shrine"
    elif s.startswith("titan"):
        kind = "titan"
    elif s.startswith("core"):
        kind = "core"
    else:
        kind = s
    return {
        "kind": kind,
        "lane": int(lane.group(1)) if lane else None,
        "index": int(index.group(1)) if index and not lane else None,
    }
