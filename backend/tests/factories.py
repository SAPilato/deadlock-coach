"""Small builders for synthetic MatchContexts, on top of real map geometry and enums."""
from __future__ import annotations

from typing import Callable

from app.analysis.model import Benchmarks, Death, ItemBuy, MatchContext, ObjectiveEvent, PlayerView, Snapshot
from app.analysis.paths import Track

Pos = tuple[float, float]


def track(slot: int, duration: int, where: Callable[[int], Pos] | Pos, combat: Callable[[int], int] | int = 1) -> Track:
    pos = where if callable(where) else (lambda t: where)
    fight = combat if callable(combat) else (lambda t: combat)
    pts = [pos(t) for t in range(duration + 1)]
    return Track(
        slot=slot,
        x=[p[0] for p in pts],
        y=[p[1] for p in pts],
        health=[100] * (duration + 1),
        combat=[fight(t) for t in range(duration + 1)],
        move=[0] * (duration + 1),
    )


def player(
    slot: int,
    team: int,
    *,
    duration: int = 1800,
    where: Callable[[int], Pos] | Pos = (0.0, 0.0),
    combat: Callable[[int], int] | int = 1,
    lane: int = 1,
    deaths: list[tuple[int, Pos]] | None = None,
    items: list[ItemBuy] | None = None,
    snapshots: list[Snapshot] | None = None,
    net_worth: int = 30000,
    hero_name: str = "Tester",
) -> PlayerView:
    death_list = [Death(t=t, x=p[0], y=p[1], killer_slot=None, respawn_t=t + 20) for t, p in deaths or []]
    return PlayerView(
        slot=slot, account_id=1000 + slot, team=team, hero_id=1, hero_name=hero_name, lane=lane,
        kills=0, deaths=len(death_list), assists=0, net_worth=net_worth, last_hits=0, denies=0, level=20,
        death_list=death_list, items=items or [], snapshots=snapshots or [],
        track=track(slot, duration, where, combat),
    )


def context(
    gd,
    players: list[PlayerView],
    *,
    me: int = 0,
    duration: int = 1800,
    objectives: list[ObjectiveEvent] | None = None,
    bench: Benchmarks | None = None,
    replay=None,
) -> MatchContext:
    from app.analysis.loader import geometry

    return MatchContext(
        match_id=1, start_time=0, duration_s=duration, winning_team=0, match_mode="Ranked", average_badge=65,
        player=next(p for p in players if p.slot == me), players=players, objectives=objectives or [],
        geo=geometry(gd), enums=gd.enums(), item_map=gd.item_map(), bench=bench, replay=replay,
    )


def lobby(gd, me: PlayerView, *, duration: int = 1800, ally_where=(0.0, 0.0), enemy_where=(0.0, 0.0), **kw) -> MatchContext:
    """`me` plus 5 allies and 6 enemies who fight all game (combat=1) at fixed spots."""
    allies = [player(s, me.team, duration=duration, where=ally_where) for s in range(1, 6)]
    enemies = [player(s, 1 - me.team, duration=duration, where=enemy_where) for s in range(6, 12)]
    return context(gd, [me, *allies, *enemies], me=me.slot, duration=duration, **kw)
