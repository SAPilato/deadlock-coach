"""Staying in your starting lane long after the laning phase ended."""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, register

LANE_UNITS = 2200  # est. distance from the lane's zipline that counts as "in lane"
WINDOW_S = 15 * 60  # est. the mid-game window checked after laning ends
OVERSTAY_SHARE = 0.65  # est.
MIN_ALIVE_S = 300
BASE_PROGRESS = 0.15  # est. time in your own base is not lane time


@register
class LaneOverstay(Rule):
    id = "lane_overstay"
    habit = "Rotating after lane"
    lesson_id = "rotate-after-laning"
    TEXT = {
        "headline": "{share} of mid-game spent in your starting lane.",
        "do_next": "After your Guardian falls, take camps and join the nearest fight.",
        "more_end": "Laning ended at {time}.",
        "more_team": "Group with your team for Walkers and the Urn.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        p, tr = ctx.player, ctx.player.track
        lane = ctx.geo.lanes.get(p.lane)
        if tr is None or lane is None:
            return []
        start, start_est = ctx.laning_end()
        end = min(ctx.duration_s, start + WINDOW_S, len(tr))
        alive = in_lane = 0
        for t in range(start, end, 2):  # every 2 s is plenty
            if not p.alive_at(t):
                continue
            x, y = tr.at(t)
            if ctx.geo.enemy_progress(p.team, x, y) < BASE_PROGRESS:
                continue
            alive += 1
            in_lane += lane.dist(x, y) <= LANE_UNITS
        if alive * 2 < MIN_ALIVE_S:
            return []
        share = in_lane / alive
        if share < OVERSTAY_SHARE:
            return []
        x, y = tr.at(start)
        return [
            self.finding(
                "high" if share >= 0.85 else "med",
                score=share,
                headline=self.t("headline", share=f"{share:.0%}"),
                more=[self.t("more_end", time=clock(start) + (" (est.)" if start_est else "")), self.t("more_team")],
                evidence=[
                    Evidence(label=f"Time in {lane.name} after laning", value=round(share * 100), unit="%", better="lower", est=True),
                ],
                moments=[Moment(t=start, x=x, y=y, label="Laning ends")],
            )
        ]
