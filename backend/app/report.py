"""Builds the match report payload the frontend renders: header, findings,
benchmarks, timeline, death map, item timing and lane summary."""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.analysis.paths import zipline_rides
from app.analysis.zipline import zipline_reach
from app.findings.engine import Report
from app.findings.rules.items_late import core_items
from app.gamedata.service import GameData

LANE_CHECKPOINTS = (360, 540, 720)  # the API records snapshots every 3 min; no 5/10 min samples exist
EARLY_DEATHS_BEFORE_S = 600


def hero_card(gd: GameData, hero_id: int) -> dict:
    h = gd.hero_map().get(hero_id, {})
    imgs = h.get("images", {})
    return {
        "id": hero_id,
        "name": h.get("name", f"Hero {hero_id}"),
        "image": imgs.get("icon_image_small") or imgs.get("icon_hero_card"),
        "card": imgs.get("icon_hero_card"),
    }


def rank_info(gd: GameData, badge: int | None) -> dict | None:
    if not badge:
        return None
    tier, sub = divmod(int(badge), 10)
    rank = next((r for r in gd.ranks() if r.get("tier") == tier), None)
    if not rank:
        return None
    imgs = rank.get("images", {})
    return {
        "badge": badge,
        "tier": tier,
        "subrank": sub,
        "name": f"{rank['name']} {sub}" if sub else rank["name"],
        "image": imgs.get(f"small_subrank{sub}") or imgs.get("large"),
    }


def map_layer(ctx: MatchContext) -> dict:
    """Minimap image plus lane lines (zipline splines from the map data) for orientation."""
    lanes = []
    for lane in ctx.geo.lanes.values():
        pts = [ctx.geo.to_rel(x, y) for x, y in lane.points]
        lanes.append({
            "id": lane.id, "name": lane.name, "color": lane.color,
            "pts": [[round(a, 4), round(b, 4)] for a, b in pts],
        })
    return {"image": ctx.geo.images.get("minimap") or ctx.geo.images.get("plain"), "lanes": lanes}


def phase_bounds(ctx: MatchContext) -> tuple[int, int, bool]:
    """(end of laning, start of late game, is_estimate). Phases come from objectives, not a clock.

    Laning ends when the Guardian in your lane falls. Late game starts when the first Base
    Guardian falls (either team): a base is open and fights move to Shrines and the Patron.
    Not the first Walker: in 40 real matches it fell ~40% of the way in, which made 60% of
    every match "late". The first Base Guardian fell ~65% of the way in. A match where no
    Base Guardian fell has no late game.
    """
    laning, est = ctx.laning_end()
    base = [o.t for o in ctx.objectives if o.kind == "barracks"]
    late = min(base) if base else max(ctx.duration_s, laning)
    return laning, max(late, laning), est


def phase_of(t: int, bounds: tuple[int, int, bool]) -> str:
    laning, mid_end, _ = bounds
    return "early" if t < laning else "mid" if t < mid_end else "late"


def build_report(gd: GameData, ctx: MatchContext, rules: Report, replay_status: dict | None = None) -> dict:
    p = ctx.player
    minutes = ctx.duration_s / 60 if ctx.duration_s else 1
    bounds = phase_bounds(ctx)
    lane = ctx.geo.lanes.get(p.lane)
    return {
        "match": {
            "id": ctx.match_id,
            "start_time": ctx.start_time,
            "duration_s": ctx.duration_s,
            "won": ctx.won,
            "mode": ctx.match_mode,
            "hero": hero_card(gd, p.hero_id),
            "kills": p.kills,
            "deaths": p.deaths,
            "assists": p.assists,
            "net_worth": p.net_worth,
            "souls_per_min": round(p.net_worth / minutes),
            "rank": rank_info(gd, ctx.average_badge),
            "lane": {"id": lane.id, "name": lane.name, "color": lane.color} if lane else None,
            "team": p.team,
        },
        "findings": [f.model_dump() for f in rules.findings],
        "passed": [h.model_dump() for h in rules.passed],
        "skipped": [h.model_dump() for h in rules.skipped],
        "benchmarks": _benchmarks(ctx),
        "timeline": _timeline(gd, ctx),
        "phases": {"laning_end": bounds[0], "mid_end": bounds[1], "est": bounds[2]},
        "deaths": _deaths(gd, ctx, bounds),
        "items": _items(ctx),
        "lane": _lane(gd, ctx),
        "map": map_layer(ctx),
        "players": [
            {**hero_card(gd, q.hero_id), "slot": q.slot, "team": q.team, "is_me": q.slot == p.slot}
            for q in ctx.players
        ],
        "replay": replay_status or {"status": "none"},
    }


def _benchmarks(ctx: MatchContext) -> dict:
    if ctx.bench is None:
        return {"available": False, "tiles": []}
    p, m = ctx.player, ctx.bench.metrics
    minutes = ctx.duration_s / 60 if ctx.duration_s else 1
    last = p.snapshots[-1] if p.snapshots else None
    mine = {
        "net_worth_per_min": (p.net_worth / minutes, "Souls / min", "higher"),
        "kills": (p.kills, "Kills", "higher"),
        "deaths": (p.deaths, "Deaths", "lower"),
        "assists": (p.assists, "Assists", "higher"),
        "last_hits": (p.last_hits, "Last hits", "higher"),
        "player_damage_per_min": ((last.player_damage / minutes) if last else None, "Hero damage / min", "higher"),
    }
    tiles = []
    for key, (value, label, better) in mine.items():
        stat = m.get(key) or {}
        typical = stat.get("percentile50", stat.get("avg"))
        if value is None or typical is None:
            continue
        tiles.append({
            "key": key, "label": label, "value": round(value), "benchmark": round(typical),
            "p25": stat.get("percentile25"), "p75": stat.get("percentile75"), "better": better,
        })
    return {"available": True, "bracket": list(ctx.bench.bracket), "tiles": tiles}


def _timeline(gd: GameData, ctx: MatchContext) -> dict:
    p = ctx.player
    series = [{"t": 0, "you": 0, "avg": 0}]
    for s in p.snapshots:
        row = ctx.bench.curve_at(s.t) if ctx.bench else None
        series.append({"t": s.t, "you": s.net_worth, "avg": round(row["net_worth_avg"]) if row else None})
    events = []
    for d in p.death_list:
        killer = ctx.by_slot(d.killer_slot)
        events.append({"t": d.t, "type": "death", "label": f"Died to {killer.hero_name}" if killer else "Died", "x": d.x, "y": d.y})
    for e in ctx.enemies:
        for d in e.death_list:
            if d.killer_slot == p.slot:
                events.append({"t": d.t, "type": "kill", "label": f"Killed {e.hero_name}", "x": d.x, "y": d.y})
    for o in ctx.objectives:
        ours = o.owner_team != p.team
        lane = ctx.geo.lanes.get(o.lane_id) if o.lane_id else None
        where = f" ({lane.name})" if lane else ""
        events.append({
            "t": o.t, "type": "objective", "side": "ally" if ours else "enemy",
            "label": f"{'Took' if ours else 'Lost'} {o.name}{where}", "x": o.x, "y": o.y,
        })
    for t, team in ctx.mid_boss:
        events.append({"t": t, "type": "midboss", "side": "ally" if team == p.team else "enemy",
                       "label": "Mid Boss: " + ("your team" if team == p.team else "enemy team")})
    for it in p.items:
        events.append({"t": it.t, "type": "item", "label": f"Bought {it.name}", "image": it.image, "tier": it.tier})
    events.sort(key=lambda e: e["t"])
    return {"duration_s": ctx.duration_s, "series": series, "events": events}


def _deaths(gd: GameData, ctx: MatchContext, bounds) -> list[dict]:
    out = []
    for d in ctx.player.death_list:
        left, top = ctx.geo.to_rel(d.x, d.y)
        killer = ctx.by_slot(d.killer_slot)
        out.append({
            "t": d.t, "x": d.x, "y": d.y, "left": left, "top": top, "phase": phase_of(d.t, bounds),
            "killer": killer.hero_name if killer else None,
            "place": ctx.geo.describe(ctx.player.team, d.x, d.y),
        })
    return out


def _items(ctx: MatchContext) -> list[dict]:
    core = set(core_items(ctx)) if ctx.bench else set()
    seen: set[int] = set()
    out = []
    for it in ctx.player.items:
        bench = ctx.bench.items.get(it.item_id) if ctx.bench else None
        avg = bench.get("avg_buy_time_s") if bench else None
        first = it.item_id not in seen
        seen.add(it.item_id)
        out.append({
            "t": it.t, "item_id": it.item_id, "name": it.name, "image": it.image, "tier": it.tier,
            "slot_type": it.slot_type, "cost": it.cost, "sold_t": it.sold_t,
            "avg_t": round(avg) if avg and first else None,
            "delta": round(it.t - avg) if avg and first else None,
            "core": it.item_id in core,
            "win_rate": round(bench["wins"] / bench["matches"], 3) if bench and bench.get("matches") else None,
        })
    return out


def _lane(gd: GameData, ctx: MatchContext) -> dict:
    p = ctx.player
    partner = [q for q in ctx.allies if q.lane == p.lane]
    opponents = [q for q in ctx.enemies if q.lane == p.lane]
    checkpoints = []
    for t in LANE_CHECKPOINTS:
        you = p.net_worth_at(t)
        if you is None:
            continue
        row = ctx.bench.curve_at(t) if ctx.bench else None
        ours = [q.net_worth_at(t) for q in [p, *partner]]
        theirs = [q.net_worth_at(t) for q in opponents]
        lead = sum(ours) - sum(theirs) if None not in ours + theirs and theirs else None
        checkpoints.append({"t": t, "you": you, "avg": round(row["net_worth_avg"]) if row else None, "lead": lead})
    lane = ctx.geo.lanes.get(p.lane)
    return {
        "lane": {"id": lane.id, "name": lane.name, "color": lane.color} if lane else None,
        "partner": [hero_card(gd, q.hero_id) for q in partner],
        "opponents": [hero_card(gd, q.hero_id) for q in opponents],
        "checkpoints": checkpoints,
        "deaths_before_10": sum(1 for d in p.death_list if d.t < EARLY_DEATHS_BEFORE_S),
        "laning_end": ctx.laning_end()[0],
        "laning_end_est": ctx.laning_end()[1],
    }


def build_paths(gd: GameData, ctx: MatchContext, step: int = 5, start_reach: float | None = None) -> dict:
    """Minimap positions for every player every `step` seconds, for the timeline scrubber.

    `zip` lists each zipline ride to the second ([start, end, lane id]) from the match's
    movement types, so the review can show who is riding at any moment.
    `reach` gives each team's share of every lane's zipline over time (analysis/zipline.py),
    as [t, team 0 reach, team 1 reach] at each change.
    """
    zip_id = ctx.enum_value("EMoveType", "Ziplining")
    players = []
    for q in ctx.players:
        if q.track is None:
            continue
        pts = []
        for t in range(0, ctx.duration_s + 1, step):
            left, top = ctx.geo.to_rel(*q.track.at(t))
            pts.append([round(left, 4), round(top, 4)])
        players.append({
            **hero_card(gd, q.hero_id), "slot": q.slot, "team": q.team, "is_me": q.slot == ctx.player.slot,
            "ally": q.team == ctx.player.team, "pts": pts,
            "dead": [[d.t, d.respawn_t] for d in q.death_list],
            # Paths run a few seconds past the end of the match; keep rides inside it.
            "zip": [
                [r.start, min(r.end, ctx.duration_s), r.lane_id]
                for r in zipline_rides(q.track, zip_id, ctx.geo.lanes.values())
                if r.start < ctx.duration_s
            ],
        })
    lanes = [{"id": ln.id, "name": ln.name, "color": ln.color} for ln in ctx.geo.lanes.values()]
    reach = zipline_reach(ctx, start_reach) if start_reach is not None else {}
    return {
        "step": step, "duration_s": ctx.duration_s, "players": players, "lanes": lanes,
        "reach": {str(k): v for k, v in reach.items()}, "start_reach": start_reach,
    }
