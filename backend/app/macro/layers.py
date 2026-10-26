"""Map layers built from /v1/assets/map, NPC data and objective params.

Every point's position comes from the map data. Tooltip facts (names, health,
soul bounties) come from game data; the "Tip" line is coaching advice.
"""
from __future__ import annotations

from app.analysis.geometry import MapGeometry
from app.gamedata.service import GameData

# Coaching lines. Short by design: every one is checked by the readability test.
TIPS = {
    "guardian": "Take it when your wave is there. Never fight under it alone.",
    "walker": "Group with your team for Walkers. They stop a lane's push.",
    "patron": "The final objective. Win fights first, then push.",
    "camp": "Clear camps between waves. Never leave a wave to die.",
    "vault": "A bigger camp. Clear it when your lane is pushed.",
    "crate": "Break crates you pass. Never walk far out of your way.",
    "statue": "Break statues on your way. Check them after each fight.",
    "buff": "Grab it when you pass. It is free value.",
    "urn_spawn": "When the urn spawns, move toward it with your team.",
    "urn_pad": "Deliver the urn here. Guard the carrier.",
    "shop": "Buy when you pass. Do not hold many souls.",
    "move": "Use it to rotate faster between lanes.",
    "other": "Know where it is before a fight starts.",
}

CAMP_NPC = {"weak": "neutral_trooper_weak", "medium": "neutral_trooper_normal", "strong": "neutral_trooper_strong"}
TEAM_NAMES = {0: "Hidden King", 1: "Archmother"}  # Boon team_names(): 2 -> Hidden King, 3 -> Archmother


def _pt(geo: MapGeometry, e: dict, label: str, kind: str, facts: str | None = None, **extra) -> dict:
    left, top = e.get("left_relative"), e.get("top_relative")
    if left is None and "position" in e:
        left, top = geo.to_rel(e["position"][0], e["position"][1])
    out = {"left": round(left, 4), "top": round(top, 4), "label": label, "kind": kind, "facts": facts, "tip": TIPS.get(kind)}
    if e.get("target"):
        tl, tt = geo.to_rel(e["target"][0], e["target"][1])
        out["target"] = [round(tl, 4), round(tt, 4)]
    out.update(extra)
    return out


def build_layers(gd: GameData, geo: MapGeometry) -> dict:
    m = gd.map_data()
    ent = m.get("entities") or {}
    npc = {u.get("class_name"): u for u in gd.npc_units()}
    params = gd.generic_data().get("objective_params") or {}

    def hp(cls: str) -> str | None:
        h = (npc.get(cls) or {}).get("max_health")
        return f"{h:,} HP" if h else None

    def facts(*parts) -> str:
        return " · ".join(p for p in parts if p)

    objectives = []
    for key, (x, y) in geo.objectives.items():
        team = int(key[4])
        team_name = TEAM_NAMES.get(team, f"Team {team}")
        left, top = geo.to_rel(x, y)
        if "_tier1_" in key:
            kind, name = "guardian", gd.objective_display("tier1")
            f = facts(team_name, hp("npc_boss_tier1"), f"{params['tier1_gold_kill']:,} souls" if params.get("tier1_gold_kill") else None)
        elif "_tier2_" in key:
            kind, name = "walker", gd.objective_display("tier2")
            f = facts(team_name, hp("npc_boss_tier2"), f"{params['tier2_gold_kill']:,} souls" if params.get("tier2_gold_kill") else None)
        else:
            kind, name = "patron", gd.objective_display("titan" if "titan" in key else "core")
            f = facts(team_name, hp("npc_boss_tier3") if "titan" in key else None)
        objectives.append({"left": round(left, 4), "top": round(top, 4), "label": name, "kind": kind, "facts": f,
                           "tip": TIPS[kind], "team": team})

    camps = []
    for c in m.get("neutral_camps") or []:
        k = c.get("kind")
        if k == "vault":
            camps.append(_pt(geo, c, "Vault camp", "vault", size=k))
            continue
        u = npc.get(CAMP_NPC.get(k, ""), {})
        camps.append(_pt(geo, c, f"{(k or 'camp').title()} camp", "camp", facts(u.get("name"), hp(CAMP_NPC.get(k, ""))), size=k))

    lanes = [
        {"id": L.id, "name": L.name, "color": L.color, "pts": [[round(a, 4), round(b, 4)] for a, b in (geo.to_rel(x, y) for x, y in L.points)]}
        for L in geo.lanes.values()
    ]

    def group(name: str, label: str, kind: str, f: str | None = None) -> list[dict]:
        return [_pt(geo, e, label, kind, f) for e in ent.get(name, [])]

    shops = [
        _pt(geo, s, f"{(s.get('kind') or '').title() or 'Item'} shop", "shop",
            TEAM_NAMES.get(s["team"]) if "team" in s else "Both teams")
        for s in ent.get("shops", [])
    ]

    layers = [
        {"id": "lanes", "label": "Lanes and ziplines", "on": True, "lines": lanes, "points": []},
        {"id": "objectives", "label": "Guardians and Walkers", "on": True, "points": objectives},
        {"id": "camps", "label": "Jungle camps", "on": True, "points": camps},
        {"id": "urn", "label": "Urn spawns and drop-offs", "on": True,
         "points": group("soul_urn_spawns", "Urn spawn", "urn_spawn") + group("soul_urn_pads", "Urn drop-off", "urn_pad")},
        {"id": "shops", "label": "Shops", "on": False, "points": shops},
        {"id": "statues", "label": "Golden statues", "on": False, "points": group("golden_statues", "Golden statue", "statue")},
        {"id": "crates", "label": "Crates", "on": False,
         "points": group("crates", "Crate", "crate") + group("tough_crates", "Tough crate", "crate")},
        {"id": "buffs", "label": "Buffs and healing", "on": False,
         "points": group("bridge_buffs", "Bridge buff", "buff") + group("healing_snacks", "Healing pickup", "buff")},
        {"id": "movement", "label": "Teleporters, pads, ropes", "on": False,
         "points": group("teleporters", "Teleporter", "move") + group("bounce_pads", "Bounce pad", "move")
         + group("climb_ropes", "Climb rope", "move") + group("steam_vents", "Steam vent", "move")},
        {"id": "other", "label": "Bells, veils, rifts", "on": False,
         "points": group("bells", "Bell", "other") + group("cosmic_veils", "Cosmic veil", "other")
         + group("unstable_rifts", "Unstable rift", "other") + group("base_sentries", "Base sentry", "other")},
    ]
    images = m.get("images") or {}
    return {
        "image": images.get("minimap") or images.get("plain"),
        "overlays": [
            {"id": "mid_tunnels", "label": "Mid tunnels", "image": images.get("mid_tunnels")},
            {"id": "rat_tunnels", "label": "Rat tunnels", "image": images.get("rat_tunnels")},
        ],
        "layers": layers,
        "transform": {"ax": geo.ax.a, "bx": geo.ax.b, "ay": geo.ay.a, "by": geo.ay.b},
        "meters_per_unit": 0.0254,
        "teams": TEAM_NAMES,
    }
