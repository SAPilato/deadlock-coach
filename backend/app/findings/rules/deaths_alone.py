"""Deaths with no living teammate nearby, especially deep on the enemy side."""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, lobby_average, nearest_ally_units, register

# Thresholds are coaching estimates, not game data.
ALONE_UNITS = 2500  # est. ~64 m
DEEP_PROGRESS = 0.6  # est. 60% of the way from your core to theirs


def alone_deaths(ctx: MatchContext) -> list[tuple]:
    p = ctx.player
    out = []
    for d in p.death_list:
        near = nearest_ally_units(ctx, d.t, d.x, d.y)
        if near is None or near > ALONE_UNITS:
            out.append((d, ctx.geo.enemy_progress(p.team, d.x, d.y) > DEEP_PROGRESS))
    return out


@register
class DyingAlone(Rule):
    id = "died_alone"
    habit = "Dying alone"
    lesson_id = "fight-with-team"
    TEXT = {
        "headline": "{n} of {total} deaths had no ally within {meters} m.",
        "do_next": "Before crossing mid, check the minimap. Go only with an ally near.",
        "more_deep": "{k} of these were deep on the enemy side.",
        "more_lobby": "Lobby average: {lobby} deaths alone per player.",
        "more_why": "Solo deaths hand the enemy free souls and map control.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        flagged = alone_deaths(ctx)
        n, total = len(flagged), len(ctx.player.death_list)
        deep_n = sum(1 for _, deep in flagged if deep)
        if n < 3 and not (n == 2 and deep_n):
            return []
        lobby = lobby_average(ctx, lambda c: len(alone_deaths(c)))
        if lobby is not None and n <= lobby:
            return []  # no worse than the rest of this lobby
        share = n / total
        severity = "high" if n >= 5 or (n >= 3 and share >= 0.5) else "med" if n >= 3 else "low"
        more = []
        if deep_n:
            more.append(self.t("more_deep", k=deep_n))
        if lobby is not None:
            more.append(self.t("more_lobby", lobby=f"{lobby:.1f}"))
        more.append(self.t("more_why"))
        meters = ctx.geo.meters(ALONE_UNITS)
        return [
            self.finding(
                severity,
                score=n + deep_n * 0.5,
                headline=self.t("headline", n=n, total=total, meters=meters),
                more=more,
                evidence=[
                    Evidence(
                        label=f"Deaths with no ally within {meters} m",
                        value=n,
                        benchmark=round(lobby, 1) if lobby is not None else None,
                        better="lower",
                        est=True,
                    ),
                ],
                moments=[
                    Moment(t=d.t, x=d.x, y=d.y, label="Died alone, deep" if deep else "Died alone")
                    for d, deep in flagged
                ],
            )
        ]
