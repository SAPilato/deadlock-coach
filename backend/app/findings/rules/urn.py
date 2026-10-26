"""Urn contesting. Urn events are only in replays, so this rule needs a parsed .dem.

The replay parser provides `ctx.replay.urn_events`: one row per urn spawn with the
times it was picked up / delivered and the positions involved.
"""
from __future__ import annotations

import math

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, register

NEAR_UNITS = 3000  # est. close enough to contest
MIN_SHARE = 0.34  # est. contest at least a third of urns


@register
class UrnContest(Rule):
    id = "urn_contest"
    habit = "Urn fights"
    lesson_id = "urn"
    requires_replay = True
    TEXT = {
        "headline": "Contested {k} of {n} urns.",
        "do_next": "When the urn spawns, move toward it with your team.",
        "more_missed": "First missed urn: {time}.",
        "more_why": "Each urn is a big soul swing for one team.",
    }

    def skip_reason(self, ctx: MatchContext) -> str | None:
        reason = super().skip_reason(ctx)
        if reason:
            return reason
        if not getattr(ctx.replay, "urn_events", None):
            return "No urn data in this replay"
        return None

    @staticmethod
    def _points(ctx: MatchContext, ev: dict) -> list[tuple[float, float, float]]:
        """Urn events plus the carrier's position every 5 s while carrying."""
        pts = list(ev["checkpoints"])
        by_hero = {q.hero_id: q for q in ctx.players}
        for hero_id, t0, t1 in ev.get("carriers", []):
            carrier = by_hero.get(hero_id)
            if carrier is None or carrier.track is None or t1 is None:
                continue
            for t in range(int(t0), int(t1) + 1, 5):
                pts.append((t, *carrier.track.at(t)))
        return pts

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        p = ctx.player
        events = ctx.replay.urn_events
        contested, missed = 0, []
        for ev in events:
            near = False
            for t, x, y in self._points(ctx, ev):
                if p.track and p.alive_at(t) and math.dist(p.track.at(t), (x, y)) <= NEAR_UNITS:
                    near = True
                    break
            if near:
                contested += 1
            else:
                missed.append(ev)
        n = len(events)
        if n == 0 or contested / n >= MIN_SHARE:
            return []
        first = missed[0]["checkpoints"][0]
        return [
            self.finding(
                "med" if contested else "high",
                score=1 - contested / n,
                headline=self.t("headline", k=contested, n=n),
                more=[self.t("more_missed", time=clock(first[0])), self.t("more_why")],
                evidence=[Evidence(label="Urns contested", value=contested, benchmark=n, better="higher", est=True)],
                moments=[Moment(t=int(ev["checkpoints"][0][0]), x=ev["checkpoints"][0][1], y=ev["checkpoints"][0][2], label="Urn missed") for ev in missed[:5]],
            )
        ]
