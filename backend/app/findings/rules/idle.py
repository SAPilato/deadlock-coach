"""Long stretches alive with no combat at all: not farming, not fighting.

Uses the per-second combat state from match paths. Players are out of combat
about half the time just moving between waves, so only gaps of a full minute
count. Souls are only recorded every 3-5 minutes, so this is an estimate.
"""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, lobby_average, register

GAP_MIN_S = 60  # est. calibrated on seed lobbies: median player idles ~6% of alive time
RESPAWN_GRACE_S = 45  # est. walking back from base after a death is not "idle"
START_S = 60  # est. ignore the opening walk to lane
MIN_SHARE = 0.10  # est. roughly the top quarter of players in seed lobbies


def idle_gaps(ctx: MatchContext) -> tuple[list[tuple[int, int]], int] | None:
    """(gaps as (start, end) seconds, seconds alive) or None without path data."""
    p, tr = ctx.player, ctx.player.track
    out = ctx.enum_value("ECombatType", "Out")
    if tr is None or not tr.combat or out is None:
        return None
    grace = [(d.respawn_t, d.respawn_t + RESPAWN_GRACE_S) for d in p.death_list]
    end = min(len(tr.combat), ctx.duration_s)
    gaps: list[tuple[int, int]] = []
    run_start = None
    alive_s = 0
    for t in range(START_S, end):
        alive = p.alive_at(t)
        alive_s += alive
        idle = alive and tr.combat[t] == out and not any(a <= t < b for a, b in grace)
        if idle and run_start is None:
            run_start = t
        elif not idle and run_start is not None:
            if t - run_start >= GAP_MIN_S:
                gaps.append((run_start, t))
            run_start = None
    if run_start is not None and end - run_start >= GAP_MIN_S:
        gaps.append((run_start, end))
    return gaps, alive_s


def idle_share(ctx: MatchContext) -> float | None:
    r = idle_gaps(ctx)
    if not r or not r[1]:
        return None
    gaps, alive = r
    return sum(b - a for a, b in gaps) / alive


@register
class IdleTime(Rule):
    id = "idle_time"
    habit = "Idle time"
    lesson_id = "always-moving"
    TEXT = {
        "headline": "{total} alive with no fights or farming.",
        "do_next": "Always walk toward a wave, camp or fight. Never wait.",
        "more_longest": "Longest gap: {longest}, starting at {time}.",
        "more_lobby": "You: {share} of your time alive. Lobby average: {lobby}.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        r = idle_gaps(ctx)
        if not r or not r[1]:
            return []
        gaps, alive = r
        total = sum(b - a for a, b in gaps)
        share = total / alive
        if share < MIN_SHARE:
            return []
        lobby = lobby_average(ctx, idle_share)
        if lobby is not None and share <= lobby:
            return []  # no worse than the rest of this lobby
        severity = "high" if share >= 0.2 else "med" if share >= 0.13 else "low"
        tr = ctx.player.track
        longest = max(gaps, key=lambda g: g[1] - g[0])
        top = sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:3]
        return [
            self.finding(
                severity,
                score=share,
                headline=self.t("headline", total=clock(total)),
                more=[
                    self.t("more_longest", longest=clock(longest[1] - longest[0]), time=clock(longest[0])),
                    self.t("more_lobby", share=f"{share:.0%}", lobby=f"{lobby:.0%}" if lobby is not None else "n/a"),
                ],
                evidence=[
                    Evidence(
                        label="Time alive with no combat for 1+ min",
                        value=round(share * 100),
                        benchmark=round(lobby * 100) if lobby is not None else None,
                        unit="%",
                        better="lower",
                        est=True,
                    ),
                ],
                moments=[Moment(t=a, x=tr.at(a)[0], y=tr.at(a)[1], label=f"No combat for {b - a}s") for a, b in top],
            )
        ]
