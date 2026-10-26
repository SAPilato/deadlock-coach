"""'What would you do?': real moments from your matches, just before a mistake.

Candidates are the moments your findings flagged (a death alone, a missed
objective fight, an idle stretch). The snapshot is LEAD_S seconds earlier, built
from the match's per-second positions. After you pick an action we show what
you actually did and what happened next. There is no single right answer.
"""
from __future__ import annotations

import math

from app.analysis.loader import load_context
from app.analysis.model import MatchContext
from app.gamedata.client import ApiError
from app.state import AppState
from app.trends import analyze

LEAD_S = 20  # est. how long before the flagged moment the decision was made
FUTURE_S = 40
FRAME_S = 2
NEAR_UNITS = 2500  # est. "with your team"
RULES = {"died_alone", "missed_objectives", "idle_time", "same_death_spot"}

OPTIONS = [
    {"id": "team", "label": "Join your team"},
    {"id": "camp", "label": "Farm a camp"},
    {"id": "lane", "label": "Push a lane"},
    {"id": "back", "label": "Back off and heal"},
]
DID = {**{o["id"]: o["label"] for o in OPTIONS}, "alone": "Moved around alone"}


def list_scenarios(st: AppState, account_id: int, bracket, n_matches: int = 8, limit: int = 12) -> list[dict]:
    """Flagged moments first; then the time before your deaths and lost objectives."""
    flagged, other = [], []
    history = [m for m in st.gd.match_history(account_id) if m.get("game_mode") == 1][:n_matches]
    for m in history:
        try:
            report = analyze(st, m["match_id"], account_id, bracket)
            ctx = load_context(st.gd, m["match_id"], account_id, bracket, with_bench=False)
        except (ApiError, ValueError):
            continue
        base = {"match_id": m["match_id"], "hero_id": m["hero_id"], "start_time": m.get("start_time")}
        seen: set[int] = set()
        for f in report.findings:
            if f.rule_id not in RULES:
                continue
            for mo in f.moments[:3]:
                seen.add(mo.t)
                flagged.append({**base, "t": max(0, mo.t - LEAD_S), "habit": f.habit, "label": mo.label})
        for d in ctx.player.death_list:
            if d.t not in seen and d.t > LEAD_S:
                other.append({**base, "t": d.t - LEAD_S, "habit": None, "label": "Before you died"})
        for o in ctx.objectives:
            if o.owner_team == ctx.player.team and o.t > LEAD_S and o.kind != "core":
                other.append({**base, "t": o.t - LEAD_S, "habit": None, "label": f"Before your {o.name} fell"})
        if len(flagged) >= limit:
            break
    return (flagged + other)[:limit]


def _pos(ctx: MatchContext, p, t: int) -> dict:
    left, top = ctx.geo.to_rel(*p.track.at(t))
    hp = p.track.health[p.track.index(t)] if p.track.health else None
    return {"slot": p.slot, "left": round(left, 4), "top": round(top, 4), "alive": p.alive_at(t), "hp": hp}


def classify(ctx: MatchContext, t0: int, t1: int) -> str:
    """What you did between t0 and t1, in the same words as the options."""
    p, tr = ctx.player, ctx.player.track
    neutral = ctx.enum_value("ECombatType", "Neutral")
    npc = ctx.enum_value("ECombatType", "EnemyNPC")
    secs = range(t0, min(t1, len(tr)))
    with_team = camp = lane = 0
    for t in secs:
        x, y = tr.at(t)
        near = sum(1 for a in ctx.allies if a.track and a.alive_at(t) and math.dist(a.track.at(t), (x, y)) <= NEAR_UNITS)
        with_team += near >= 2
        i = tr.index(t)
        camp += tr.combat[i] == neutral if tr.combat else 0
        lane += tr.combat[i] == npc if tr.combat else 0
    n = max(1, len(secs))
    if with_team >= n / 2:
        return "team"
    if camp >= 4:
        return "camp"
    if lane >= 4:
        return "lane"
    progress = ctx.geo.enemy_progress(p.team, *tr.at(t1)) - ctx.geo.enemy_progress(p.team, *tr.at(t0))
    return "back" if progress < -0.05 else "alone"


def scenario(st: AppState, account_id: int, match_id: int, t: int, bracket) -> dict:
    ctx = load_context(st.gd, match_id, account_id, bracket, with_bench=False)
    p = ctx.player
    if p.track is None:
        raise ValueError("No position data for this match.")
    t = max(0, min(t, ctx.duration_s - 1))
    end = min(ctx.duration_s, t + FUTURE_S)

    players = [
        {"slot": q.slot, "hero": q.hero_name, "hero_id": q.hero_id, "side": "me" if q.slot == p.slot else "ally" if q.team == p.team else "enemy"}
        for q in ctx.players if q.track
    ]
    frames = [
        {"t": ft, "pos": [_pos(ctx, q, ft) for q in ctx.players if q.track]}
        for ft in range(t, end + 1, FRAME_S)
    ]

    # Objectives still standing at the snapshot.
    fallen = {(o.owner_team, o.kind, o.lane_num) for o in ctx.objectives if o.t <= t}
    standing = []
    for key, (x, y) in ctx.geo.objectives.items():
        team = int(key[4])
        kind = "tier1" if "_tier1_" in key else "tier2" if "_tier2_" in key else "titan" if "titan" in key else "core"
        lane = int(key.rsplit("_", 1)[1]) if kind in ("tier1", "tier2") else None
        left, top = ctx.geo.to_rel(x, y)
        standing.append({"left": round(left, 4), "top": round(top, 4), "kind": kind,
                         "ally": team == p.team, "alive": (team, kind, lane) not in fallen})

    def souls(team: int) -> int:
        snaps = [max((s for s in q.snapshots if s.t <= t), key=lambda s: s.t, default=None) for q in ctx.players if q.team == team]
        return sum(s.net_worth for s in snaps if s)

    events = []
    for q in ctx.players:
        for d in q.death_list:
            if t < d.t <= end:
                who = "You" if q.slot == p.slot else q.hero_name
                side = "me" if q.slot == p.slot else "ally" if q.team == p.team else "enemy"
                events.append({"t": d.t, "text": f"{who} died", "side": side})
    for o in ctx.objectives:
        if t < o.t <= end:
            mine = o.owner_team == p.team
            events.append({"t": o.t, "text": f"{'Your' if mine else 'Enemy'} {o.name} fell", "side": "ally" if mine else "enemy"})
    events.sort(key=lambda e: e["t"])

    did = classify(ctx, t, min(end, t + LEAD_S))
    report = analyze(st, match_id, account_id, bracket)
    finding = next(
        (f for f in report.findings if any(abs((m.t - LEAD_S) - t) <= 3 or abs(m.t - t) <= 3 for m in f.moments)),
        None,
    )
    return {
        "match_id": match_id,
        "t": t,
        "hero": p.hero_name,
        "team": p.team,
        "players": players,
        "frames": frames,
        "objectives": standing,
        "souls": {"you": souls(p.team), "them": souls(1 - p.team)},
        "options": OPTIONS,
        "did": {"id": did, "label": DID[did]},
        "events": events,
        "finding": {"habit": finding.habit, "headline": finding.headline, "do_next": finding.do_next} if finding else None,
    }
