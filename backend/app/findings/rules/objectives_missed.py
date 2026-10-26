"""Objective fights where 3+ teammates showed up and you were dead or far away."""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, min_distance, register

NEAR_UNITS = 3000  # est. ~76 m from the objective counts as "there"
MIN_ALLIES = 3
WINDOW_S = 20  # look at the 20 s before the objective fell
KINDS = ("tier1", "tier2", "titan")


@register
class MissedObjectives(Rule):
    id = "missed_objectives"
    habit = "Objective fights"
    lesson_id = "group-for-objectives"
    TEXT = {
        "headline": "Missed {n} objective fights your team joined.",
        "do_next": "When three allies group at an objective, join them fast.",
        "more_dead": "You were dead for {dead} of them.",
        "more_far": "You were far away for {far} of them.",
        "more_example": "Example: {name} in {lane} at {time}.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        p = ctx.player
        if p.track is None:
            return []
        missed = []
        laning_end, _ = ctx.laning_end()
        for o in ctx.objectives:
            if o.kind not in KINDS or o.x is None or o.t >= ctx.duration_s - 5:
                continue
            if o.t < laning_end:
                continue  # you are expected to hold your own lane until then
            t0 = o.t - WINDOW_S
            allies = sum(
                1 for a in ctx.allies
                if a.track and a.alive_at(o.t) and min_distance(a.track, t0, o.t, o.x, o.y) <= NEAR_UNITS
            )
            if allies < MIN_ALLIES:
                continue
            if not p.alive_at(o.t):
                missed.append((o, "dead"))
            elif min_distance(p.track, t0, o.t, o.x, o.y) > NEAR_UNITS:
                missed.append((o, "far"))
        n = len(missed)
        if n < 2:
            return []
        severity = "high" if n >= 5 else "med" if n >= 3 else "low"
        dead = sum(1 for _, why in missed if why == "dead")
        far = n - dead
        more = []
        if far:
            more.append(self.t("more_far", far=far))
        if dead:
            more.append(self.t("more_dead", dead=dead))
        o0 = missed[0][0]
        lane = ctx.geo.lanes.get(o0.lane_id)
        more.append(self.t("more_example", name=o0.name, lane=lane.name if lane else "base", time=clock(o0.t)))
        return [
            self.finding(
                severity,
                score=n,
                headline=self.t("headline", n=n),
                more=more,
                evidence=[
                    Evidence(label="Objective fights missed", value=n, better="lower"),
                    Evidence(label="Counted as there within", value=ctx.geo.meters(NEAR_UNITS), unit="m", est=True),
                ],
                moments=[
                    Moment(
                        t=o.t, x=o.x, y=o.y,
                        label=f"{o.name} {'lost' if o.owner_team == p.team else 'taken'} ({why})",
                    )
                    for o, why in missed
                ],
            )
        ]
