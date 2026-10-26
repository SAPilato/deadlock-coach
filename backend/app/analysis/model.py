"""MatchContext: one player's view of one match, from metadata plus optional replay data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.analysis.geometry import MapGeometry
from app.analysis.paths import Track, decode_paths

# Fallback end of laning when no Guardian falls in your lane. Convention, not game data.
DEFAULT_LANING_END_S = 600


@dataclass
class Death:
    t: int
    x: float
    y: float
    killer_slot: int | None
    respawn_t: int


@dataclass
class ItemBuy:
    t: int
    item_id: int
    sold_t: int | None
    name: str
    tier: int | None
    slot_type: str | None
    cost: int | None
    image: str | None


@dataclass
class Snapshot:
    t: int
    net_worth: int
    kills: int
    deaths: int
    assists: int
    creep_kills: int
    neutral_kills: int
    denies: int
    level: int
    player_damage: int


@dataclass
class PlayerView:
    slot: int
    account_id: int
    team: int
    hero_id: int
    hero_name: str
    lane: int
    kills: int
    deaths: int
    assists: int
    net_worth: int
    last_hits: int
    denies: int
    level: int
    death_list: list[Death]
    items: list[ItemBuy]
    snapshots: list[Snapshot]
    track: Track | None
    custom: dict[str, float] = field(default_factory=dict)

    def alive_at(self, t: float) -> bool:
        return not any(d.t <= t < d.respawn_t for d in self.death_list)

    def net_worth_at(self, t: int) -> int | None:
        for s in self.snapshots:
            if s.t == t:
                return s.net_worth
        return None


@dataclass
class ObjectiveEvent:
    t: int
    owner_team: int
    objective_id: int
    kind: str
    lane_num: int | None
    lane_id: int | None
    name: str
    x: float | None
    y: float | None


@dataclass
class Benchmarks:
    bracket: tuple[int, int]
    metrics: dict[str, dict]
    curve: list[dict]
    items: dict[int, dict]

    def curve_at(self, t: int) -> dict | None:
        for row in self.curve:
            if row.get("game_time") == t:
                return row
        return None


@dataclass
class MatchContext:
    match_id: int
    start_time: int
    duration_s: int
    winning_team: int
    match_mode: str
    average_badge: int | None
    player: PlayerView
    players: list[PlayerView]
    objectives: list[ObjectiveEvent]
    geo: MapGeometry
    enums: dict[str, dict[str, str]]
    item_map: dict[int, dict]
    bench: Benchmarks | None = None
    replay: Any = None  # app.replay.parser.ReplayData when a .dem was parsed

    @property
    def won(self) -> bool:
        return self.player.team == self.winning_team

    @property
    def allies(self) -> list[PlayerView]:
        return [p for p in self.players if p.team == self.player.team and p.slot != self.player.slot]

    @property
    def enemies(self) -> list[PlayerView]:
        return [p for p in self.players if p.team != self.player.team]

    def by_slot(self, slot: int | None) -> PlayerView | None:
        return next((p for p in self.players if p.slot == slot), None)

    def enum_value(self, enum: str, name: str) -> int | None:
        for k, v in self.enums.get(enum, {}).items():
            if v == name:
                return int(k)
        return None

    def laning_end(self) -> tuple[int, bool]:
        """(seconds, is_estimate). First Guardian to fall in your lane, either team."""
        mine = [o.t for o in self.objectives if o.kind == "tier1" and o.lane_id == self.player.lane]
        if mine:
            return min(mine), False
        return DEFAULT_LANING_END_S, True


def build_context(
    meta: dict,
    account_id: int,
    *,
    hero_map: dict[int, dict],
    item_map: dict[int, dict],
    geo: MapGeometry,
    enums: dict[str, dict[str, str]],
    objective_label,
    bench: Benchmarks | None = None,
    replay: Any = None,
) -> MatchContext:
    info = meta.get("match_info", meta)
    tracks = decode_paths(info.get("match_paths"))
    custom_names = {c["id"]: c["name"] for c in info.get("custom_user_stats") or []}

    players = [_player(p, hero_map, item_map, tracks, custom_names) for p in info["players"]]
    me = next((p for p in players if p.account_id == account_id), None)
    if me is None:
        raise ValueError(f"Account {account_id} did not play match {info.get('match_id')}")

    objectives = []
    for o in info.get("objectives") or []:
        t = o.get("destroyed_time_s") or 0
        if t <= 0:
            continue
        label = objective_label(o["team_objective_id"])
        pos = geo.objective_pos(o["team"], label["kind"], label["lane"])
        objectives.append(
            ObjectiveEvent(
                t=t,
                owner_team=o["team"],
                objective_id=o["team_objective_id"],
                kind=label["kind"],
                lane_num=label["lane"],
                lane_id=geo.objective_lane.get(label["lane"]) if label["lane"] else None,
                name=label["name"],
                x=pos[0] if pos else None,
                y=pos[1] if pos else None,
            )
        )
    objectives.sort(key=lambda o: o.t)

    badge = info.get(f"average_badge_team{me.team}") or None
    mode = enums.get("ECitadelMatchMode", {}).get(str(info.get("match_mode")), str(info.get("match_mode")))
    return MatchContext(
        match_id=info["match_id"],
        start_time=info.get("start_time", 0),
        duration_s=info["duration_s"],
        winning_team=info["winning_team"],
        match_mode=mode,
        average_badge=badge,
        player=me,
        players=players,
        objectives=objectives,
        geo=geo,
        enums=enums,
        item_map=item_map,
        bench=bench,
        replay=replay,
    )


def _player(p: dict, hero_map, item_map, tracks, custom_names) -> PlayerView:
    deaths = [
        Death(
            t=d["game_time_s"],
            x=d["death_pos"]["x"],
            y=d["death_pos"]["y"],
            killer_slot=d.get("killer_player_slot"),
            respawn_t=d["game_time_s"] + int(d.get("death_duration_s") or 0),
        )
        for d in p.get("death_details") or []
    ]
    items = []
    for it in p.get("items") or []:
        a = item_map.get(it["item_id"], {})
        if a.get("type") != "upgrade":
            continue  # ability unlocks and weapons also appear in this list
        items.append(
            ItemBuy(
                t=it["game_time_s"],
                item_id=it["item_id"],
                sold_t=it.get("sold_time_s") or None,
                name=a.get("name", str(it["item_id"])),
                tier=a.get("item_tier"),
                slot_type=a.get("item_slot_type"),
                cost=a.get("cost"),
                image=a.get("shop_image") or a.get("image"),
            )
        )
    snaps = [
        Snapshot(
            t=s["time_stamp_s"],
            net_worth=s.get("net_worth", 0),
            kills=s.get("kills", 0),
            deaths=s.get("deaths", 0),
            assists=s.get("assists", 0),
            creep_kills=s.get("creep_kills", 0),
            neutral_kills=s.get("neutral_kills", 0),
            denies=s.get("denies", 0),
            level=s.get("level", 0),
            player_damage=s.get("player_damage", 0),
        )
        for s in p.get("stats") or []
    ]
    custom = {}
    if p.get("stats"):
        for c in p["stats"][-1].get("custom_user_stats") or []:
            if c["id"] in custom_names:
                custom[custom_names[c["id"]]] = c["value"]
    hero = hero_map.get(p["hero_id"], {})
    return PlayerView(
        slot=p["player_slot"],
        account_id=p["account_id"],
        team=p["team"],
        hero_id=p["hero_id"],
        hero_name=hero.get("name", f"Hero {p['hero_id']}"),
        lane=p.get("assigned_lane", 0),
        kills=p.get("kills", 0),
        deaths=p.get("deaths", 0),
        assists=p.get("assists", 0),
        net_worth=p.get("net_worth", 0),
        last_hits=p.get("last_hits", 0),
        denies=p.get("denies", 0),
        level=p.get("level", 0),
        death_list=sorted(deaths, key=lambda d: d.t),
        items=sorted(items, key=lambda i: i.t),
        snapshots=sorted(snaps, key=lambda s: s.t),
        track=tracks.get(p["player_slot"]),
        custom=custom,
    )
