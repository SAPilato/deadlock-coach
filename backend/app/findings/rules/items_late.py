"""Core items bought much later than the bracket's average for this hero.

"Core" has no official definition: we take this hero's most-bought tier 3+
items in your bracket.
"""
from __future__ import annotations

from app.analysis.model import MatchContext
from app.findings.base import Evidence, Finding, Moment, Rule, clock, register

CORE_TOP_N = 6  # est.
CORE_MIN_TIER = 3
LATE_MIN_S = 180  # est.
LATE_FRAC = 0.25  # est. late = over max(3 min, 25% of the average time)


def core_items(ctx: MatchContext) -> list[int]:
    rows = [
        r for iid, r in ctx.bench.items.items()
        if (ctx.item_map.get(iid, {}).get("item_tier") or 0) >= CORE_MIN_TIER
        and ctx.item_map.get(iid, {}).get("type") == "upgrade"
    ]
    rows.sort(key=lambda r: r.get("matches", 0), reverse=True)
    return [r["item_id"] for r in rows[:CORE_TOP_N]]


@register
class LateCoreItem(Rule):
    id = "late_core_item"
    habit = "Item timing"
    lesson_id = "item-timing"
    needs_bench = True
    TEXT = {
        "headline": "{item} came {late} min later than average.",
        "do_next": "Buy your next core item the moment you can afford it.",
        "more_times": "You: {you}. Average at your rank: {avg}.",
        "more_unspent": "You held about {unspent} unspent souls on average.",
        "more_others": "Also late: {others}.",
    }

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        first_buy: dict[int, int] = {}
        for it in ctx.player.items:
            first_buy.setdefault(it.item_id, it.t)
        late = []
        for iid in core_items(ctx):
            if iid not in first_buy:
                continue
            avg = ctx.bench.items[iid].get("avg_buy_time_s")
            if not avg:
                continue
            delay = first_buy[iid] - avg
            if delay > max(LATE_MIN_S, LATE_FRAC * avg):
                late.append((delay, iid, first_buy[iid], avg))
        if not late:
            return []
        late.sort(reverse=True)
        delay, iid, you, avg = late[0]
        name = ctx.item_map.get(iid, {}).get("name", str(iid))
        more = [self.t("more_times", you=clock(you), avg=clock(avg))]
        unspent = ctx.player.custom.get("Unspent Gold Minutes")
        if unspent and ctx.duration_s:
            more.append(self.t("more_unspent", unspent=f"{unspent / (ctx.duration_s / 60):,.0f}"))
        if len(late) > 1:
            others = ", ".join(ctx.item_map.get(i, {}).get("name", str(i)) for _, i, _, _ in late[1:3])
            more.append(self.t("more_others", others=others))
        x, y = ctx.player.track.at(you) if ctx.player.track else (None, None)
        return [
            self.finding(
                "high" if delay >= 360 else "med",
                score=delay / 60,
                headline=self.t("headline", item=name, late=round(delay / 60)),
                more=more,
                evidence=[
                    Evidence(label=f"{name} bought", value=you, benchmark=round(avg), unit="time", better="lower"),
                    Evidence(label="Late threshold", value=max(LATE_MIN_S, round(LATE_FRAC * avg)), unit="s", est=True),
                ],
                moments=[Moment(t=you, x=x, y=y, label=f"Bought {name}")],
            )
        ]
