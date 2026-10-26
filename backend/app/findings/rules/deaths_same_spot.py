"""Three or more deaths in the same area of the map."""
from __future__ import annotations

import math

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, register

CLUSTER_UNITS = 1800  # est. ~46 m radius
MIN_DEATHS = 3
MIN_SHARE = 0.3  # est. 3 deaths in one spot out of 16 is noise; out of 6 it is a habit


@register
class SameDeathSpot(Rule):
    id = "same_death_spot"
    habit = "Same death spot"
    lesson_id = "death-spots"
    TEXT = {
        "headline": "Died {n} times in one area: {place}.",
        "do_next": "Avoid that area unless two allies are with you.",
        "more_times": "Deaths at {times}.",
        "more_why": "Enemies expect you there. Take a different path.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        deaths = ctx.player.death_list
        best: list = []
        for d in deaths:
            group = [o for o in deaths if math.dist((d.x, d.y), (o.x, o.y)) <= CLUSTER_UNITS]
            if len(group) > len(best):
                best = group
        n = len(best)
        share = n / len(deaths) if deaths else 0
        if n < MIN_DEATHS or (share < MIN_SHARE and n < 5):
            return []
        cx = sum(d.x for d in best) / n
        cy = sum(d.y for d in best) / n
        place = ctx.geo.describe(ctx.player.team, cx, cy)
        return [
            self.finding(
                "high" if n >= 4 and share >= 0.35 else "med",
                score=n,
                headline=self.t("headline", n=n, place=place),
                more=[self.t("more_times", times=", ".join(clock(d.t) for d in best[:4])), self.t("more_why")],
                evidence=[
                    Evidence(label="Deaths in one area", value=n, better="lower"),
                    Evidence(label="Area radius", value=ctx.geo.meters(CLUSTER_UNITS), unit="m", est=True),
                ],
                moments=[Moment(t=d.t, x=d.x, y=d.y, label="Death here") for d in best],
            )
        ]
