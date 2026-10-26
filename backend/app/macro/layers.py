"""Map layers for the current (post-City Never Sleeps) map.

Positions come from /v1/assets/map, corrected by replay truth where the asset
data is stale (objectives, urn; see app/macro/truth.py). Names come from game
data (NPC units, generic-data districts, loot tables). Mechanics in "facts" are
quoted from the official City Never Sleeps page. The "Tip" line is coaching.
"""
from __future__ import annotations

from app.analysis.geometry import MapGeometry
from app.gamedata.service import GameData

# Coaching lines. Short by design: every one is checked by the readability test.
TIPS = {
    "guardian": "Take it when your wave is there. Never fight under it alone.",
    "walker": "Group with your team for Walkers. They stop a lane's push.",
    "patron": "The final objective. Win fights first, then push.",
    "base_guardian": "Losing these opens your base. Defend them as a team.",
    "shrine": "Shrines protect the Patron. Take them before pushing it.",
    "mid_boss": "Take it after winning a fight. Watch for steals.",
    "camp": "Clear Haunts between waves. Never leave a wave to die.",
    "vault": "A bigger Haunt camp. Clear it when your lane is pushed.",
    "bell_tower": "Big souls, but the whole map hears the bell. Go when enemies are busy.",
    "sunken_plaza": "Big farm with high risk. Go down only when your lanes are safe.",
    "urn_site": "When the urn spawns, move toward it with your team.",
    "shop": "Buy when you pass. Do not hold many souls.",
    "statue": "Break them on your way. The buffs last all game.",
    "crate": "Break crates you pass. Never walk far out of your way.",
    "tough_crate": "Worth a Heavy Melee when you pass by.",
    "buff": "Grab it when you pass. It is free value.",
    "healing": "Heal here instead of walking back to base.",
    "vent": "Use it to hide, flank or reset a fight.",
    "veil": "Know where it is before a fight starts.",
    "move": "Use it to rotate faster between lanes.",
    "other": "Know where it is before a fight starts.",
}

CAMP_NPC = {"weak": "neutral_trooper_weak", "medium": "neutral_trooper_normal", "strong": "neutral_trooper_strong"}
TEAM_NAMES = {0: "Hidden King", 1: "Archmother"}  # Boon team_names(): 2 -> Hidden King, 3 -> Archmother
BUFF_NAMES = {  # loot-table keys -> readable names
    "spirit": "spirit power", "firerate": "fire rate", "ammo": "ammo", "hp": "health", "cd": "cooldown",
    "wp": "weapon damage", "bulletresist": "bullet resist", "spiritresist": "spirit resist",
    "range": "ability range", "movespeed": "move speed",
}


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


def _facts(*parts) -> str:
    return " · ".join(str(p) for p in parts if p)


class Districts:
    """Name a camp's district from its own name, using generic-data map_districts.

    Camp names carry their area ("theater_lobby_camp", "slums_roof_camp",
    "chinatown_bell_1"); district and building keys carry the same words.
    Plaza camps below ground (z < 0) are the Sunken Plaza.
    """

    def __init__(self, generic: dict):
        self.words: dict[str, tuple[str, str | None]] = {}
        self.sunken = self.bell = None
        for d in generic.get("map_districts") or []:
            name, building = d["district_name"], d.get("building_name")
            key = d["district"].removeprefix("map_district_")
            if key == "sunkenplaza":
                self.sunken = name
                continue
            if (d.get("building") or "").endswith("belltower"):
                self.bell = building
            for w in key.split("_") + [name.lower()]:
                self.words.setdefault(w, (name, None))
            if d.get("building"):
                bkey = d["building"].removeprefix("map_district_building_")
                for w in bkey.split("_"):
                    self.words.setdefault(w, (name, building))

    GENERIC = {"camp", "vault", "neutrals", "down", "upstairs", "downstairs", "roof", "alley", "street", "corner"}

    def of(self, camp: dict) -> str | None:
        tokens = [t for t in camp["name"].lower().split("_") if t not in self.GENERIC and not t.isdigit()]
        if "plaza" in tokens and camp["position"][2] < 0 and self.sunken:
            return self.sunken
        for t in tokens:
            for w, (name, _) in self.words.items():
                # exact word, or a short form of it ("dock" -> "docks", "bell" -> "belltower")
                if len(t) >= 4 and (t == w or w.startswith(t)):
                    return name
        return None


def build_layers(gd: GameData, geo: MapGeometry) -> dict:
    m = gd.map_data()
    ent = m.get("entities") or {}
    generic = gd.generic_data()
    npc = {u.get("class_name"): u for u in gd.npc_units()}
    params = generic.get("objective_params") or {}
    rejuv = generic.get("rejuv_params") or {}
    districts = Districts(generic)

    def hp(cls: str) -> str | None:
        h = (npc.get(cls) or {}).get("max_health")
        return f"{h:,} HP" if h else None

    # ---- objectives (positions from replay truth when available) ------------------
    objectives = []
    for key, (x, y) in geo.objectives.items():
        team = int(key[4])
        left, top = geo.to_rel(x, y)
        if "_tier1_" in key:
            kind, name = "guardian", gd.objective_display("tier1")
            f = _facts(TEAM_NAMES[team], hp("npc_boss_tier1"), f"{params['tier1_gold_kill']:,} souls" if params.get("tier1_gold_kill") else None)
        elif "_tier2_" in key:
            kind, name = "walker", gd.objective_display("tier2")
            f = _facts(TEAM_NAMES[team], hp("npc_boss_tier2"), f"{params['tier2_gold_kill']:,} souls" if params.get("tier2_gold_kill") else None)
        elif "titan" in key:
            kind, name = "patron", gd.objective_display("titan")
            f = _facts(TEAM_NAMES[team], hp("npc_boss_tier3"))
        else:
            continue  # "core" is an icon spot at the Patron; the Patron marker covers it
        objectives.append({"left": round(left, 4), "top": round(top, 4), "label": name, "kind": kind, "facts": f,
                           "tip": TIPS[kind], "team": team})
    extra_names = {"barracks": ("base_guardian", "Base Guardian", "base_guardians_gold_kill"),
                   "shrine": ("shrine", "Shrine", "shrines_gold_kill"), "mid_boss": ("mid_boss", "Mid Boss", None)}
    for o in geo.extra:
        if o["kind"] not in extra_names:
            continue
        kind, name, bounty = extra_names[o["kind"]]
        left, top = geo.to_rel(o["x"], o["y"])
        team = o.get("team")
        extra = f"Rejuvenator lasts {rejuv['rejuvinator_buff_duration']:.0f} s" if kind == "mid_boss" and rejuv.get("rejuvinator_buff_duration") else None
        f = _facts(TEAM_NAMES.get(team) if team is not None else None, f"{o['hp']:,} HP" if o.get("hp") else None,
                   f"{params[bounty]:,} souls" if bounty and params.get(bounty) else None, extra)
        objectives.append({"left": round(left, 4), "top": round(top, 4), "label": name, "kind": kind, "facts": f,
                           "tip": TIPS[kind], "team": team})

    # ---- Haunt camps, Bell Tower, Sunken Plaza, district labels ---------------------
    camps, special, by_district = [], [], {}
    sunken = []
    for c in m.get("neutral_camps") or []:
        size = c.get("kind") or "camp"
        district = districts.of(c)
        cls = CAMP_NPC.get(size)
        label = "Vault Haunt camp" if size == "vault" else f"{size.title()} Haunt camp"
        camps.append(_pt(geo, c, label, "vault" if size == "vault" else "camp",
                         _facts(district, f"base {hp(cls)}" if cls and hp(cls) else None), size=size))
        if district:
            by_district.setdefault(district, []).append(c["position"])
        if district and district == districts.sunken:
            sunken.append(c["position"])
        if districts.bell and "bell" in c["name"] and size == "vault":
            special.append(_pt(geo, c, districts.bell, "bell_tower",
                               "Soul hotspot at the top. The bell rings across the map."))
    if sunken:
        x = sum(p[0] for p in sunken) / len(sunken)
        y = sum(p[1] for p in sunken) / len(sunken)
        special.append(_pt(geo, {"position": [x, y]}, districts.sunken, "sunken_plaza",
                           f"{len(sunken)} Haunt camps underground. Stamina fades down there."))
    labels = []
    lane_names = {L.name for L in geo.lanes.values()}
    for name, pts in by_district.items():
        if name == districts.sunken or name in lane_names:
            continue  # lanes are drawn and named already; label the districts between them
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        labels.append(_pt(geo, {"position": [x, y]}, name, "district", f"{len(pts)} Haunt camps"))

    lanes = [
        {"id": L.id, "name": L.name, "color": L.color, "pts": [[round(a, 4), round(b, 4)] for a, b in (geo.to_rel(x, y) for x, y in L.points)]}
        for L in geo.lanes.values()
    ]

    def group(name: str, label: str, kind: str, f: str | None = None) -> list[dict]:
        return [_pt(geo, e, label, kind, f) for e in ent.get(name, [])]

    shops = [
        _pt(geo, s, {"secret": "Secret shop", "base": "Base shop"}.get(s.get("kind"), "Lane shop"), "shop",
            TEAM_NAMES.get(s["team"]) if "team" in s else "Both teams")
        for s in ent.get("shops", [])
    ]
    loot = (generic.get("breakable_powerup_loot_params") or {}).get("pickups_by_match_time_mins") or {}
    kinds = sorted({k.split("_permanent")[0] for tier in loot.values() for k in tier})
    statue_facts = "Permanent buff: " + ", ".join(BUFF_NAMES.get(k, k) for k in kinds) if kinds else None

    # Since City Never Sleeps the urn uses 2 sites (spawn on one, deliver to the other).
    # The asset data still lists 4 older spawn points; they are left out.
    urn = (
        [_pt(geo, {"position": [x, y]}, "Urn site", "urn_site", "Spawns or is delivered here (checked in a replay).")
         for x, y in geo.urn_sites]
        if geo.urn_sites else group("soul_urn_pads", "Urn site", "urn_site", "From map data, not checked.")
    )

    layers = [
        {"id": "lanes", "label": "Lanes and ziplines", "on": True, "lines": lanes, "points": []},
        {"id": "objectives", "label": "Objectives", "on": True, "points": objectives},
        {"id": "special", "label": "Bell Tower and Sunken Plaza", "on": True, "points": special},
        {"id": "camps", "label": "Haunt camps", "on": True, "points": camps},
        {"id": "urn", "label": "Urn sites", "on": True, "points": urn},
        {"id": "districts", "label": "District names", "on": True, "points": labels},
        {"id": "shops", "label": "Shops", "on": False, "points": shops},
        {"id": "statues", "label": "Buff containers", "on": False,
         "points": group("golden_statues", "Buff container", "statue", statue_facts)},
        {"id": "crates", "label": "Crates", "on": False,
         "points": group("crates", "Crate", "crate")
         + group("tough_crates", "Tough crate", "tough_crate", "Needs a Heavy Melee. Extra souls.")},
        {"id": "healing", "label": "Healing and bridge buffs", "on": False,
         "points": group("healing_snacks", "Healing snack", "healing") + group("bridge_buffs", "Bridge buff", "buff")},
        {"id": "vents", "label": "Steam vents", "on": False,
         "points": group("steam_vents", "Steam vent", "vent", "Stand on it: invisible, small regen.")},
        {"id": "veils", "label": "Veils", "on": False, "points": group("cosmic_veils", "Veil", "veil")},
        {"id": "movement", "label": "Teleporters, pads, ropes", "on": False,
         "points": group("teleporters", "Teleporter", "move") + group("bounce_pads", "Bounce pad", "move")
         + group("climb_ropes", "Climb rope", "move")},
        {"id": "other", "label": "Rifts and base sentries", "on": False,
         "points": group("unstable_rifts", "Rift", "other") + group("base_sentries", "Base sentry", "other")},
    ]
    images = m.get("images") or {}
    truth = geo.truth or {}
    return {
        "image": images.get("minimap") or images.get("plain"),
        "overlays": [
            {"id": "mid_tunnels", "label": "Mid tunnels", "image": images.get("mid_tunnels")},
            {"id": "rat_tunnels", "label": "Rat tunnels", "image": images.get("rat_tunnels")},
        ],
        "layers": layers,
        "verified": {"match_id": truth.get("match_id"), "start_time": truth.get("start_time")} if truth else None,
        "transform": {"ax": geo.ax.a, "bx": geo.ax.b, "ay": geo.ay.a, "by": geo.ay.b},
        "meters_per_unit": 0.0254,
        "teams": TEAM_NAMES,
    }
