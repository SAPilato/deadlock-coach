"""Souls per minute below the bracket's typical value for this hero."""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, register


@register
class LowSoulsPerMin(Rule):
    id = "low_souls_per_min"
    habit = "Souls per minute"
    lesson_id = "waves-and-camps"
    needs_bench = True
    TEXT = {
        "headline": "{value} souls/min. Typical {hero} at your rank: {typical}.",
        "do_next": "Last-hit every wave, then clear a camp before the next wave.",
        "more_gap": "You fell furthest behind between {start} and {end}.",
        "more_bottom": "That is in the bottom {part} of {hero} games at your rank.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        m = ctx.bench.metrics.get("net_worth_per_min") or {}
        p10, p25, p50 = m.get("percentile10"), m.get("percentile25"), m.get("percentile50") or m.get("avg")
        if not p25 or not p50 or ctx.duration_s <= 0:
            return []
        value = ctx.player.net_worth / (ctx.duration_s / 60)
        if value >= p25:
            return []
        severe = p10 is not None and value < p10
        hero = ctx.player.hero_name
        more = [self.t("more_bottom", part="10%" if severe else "25%", hero=hero)]
        moments = []
        gap = self._worst_window(ctx)
        if gap:
            start, end = gap
            more.insert(0, self.t("more_gap", start=clock(start), end=clock(end)))
            x, y = ctx.player.track.at(start) if ctx.player.track else (None, None)
            moments.append(Moment(t=start, x=x, y=y, label="Souls fell behind"))
        return [
            self.finding(
                "high" if severe else "med",
                score=(p50 - value) / p50,
                headline=self.t("headline", value=f"{value:,.0f}", hero=hero, typical=f"{p50:,.0f}"),
                more=more,
                evidence=[Evidence(label="Souls per minute", value=round(value), benchmark=round(p50), unit="/min", better="higher")],
                moments=moments,
            )
        ]

    @staticmethod
    def _worst_window(ctx: MatchContext) -> tuple[int, int] | None:
        """The snapshot window where you lost the most ground vs the rank average."""
        prev_t, prev_gap, worst = 0, 0.0, None
        for s in ctx.player.snapshots:
            row = ctx.bench.curve_at(s.t)
            if not row or "net_worth_avg" not in row:
                continue
            gap = s.net_worth - row["net_worth_avg"]
            drop = prev_gap - gap
            if worst is None or drop > worst[0]:
                worst = (drop, prev_t, s.t)
            prev_t, prev_gap = s.t, gap
        return (worst[1], worst[2]) if worst and worst[0] > 0 else None
