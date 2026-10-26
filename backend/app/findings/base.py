"""Finding model, Rule base class, registry and shared helpers."""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Callable, ClassVar, Literal

from pydantic import BaseModel, Field

from app.analysis.model import MatchContext

Severity = Literal["high", "med", "low"]
SEVERITY_RANK = {"high": 3, "med": 2, "low": 1}


class Evidence(BaseModel):
    label: str
    value: float | str
    benchmark: float | str | None = None
    unit: Literal["", "time", "min", "s", "m", "%", "souls", "/min"] = ""
    better: Literal["higher", "lower"] | None = None
    est: bool = False  # True when the number (or its threshold) is an estimate


class Moment(BaseModel):
    t: int
    x: float | None = None
    y: float | None = None
    label: str


class Finding(BaseModel):
    rule_id: str
    habit: str
    severity: Severity
    score: float = 0.0  # ranks findings of equal severity
    headline: str
    do_next: str
    more: list[str] = Field(default_factory=list, max_length=3)
    evidence: list[Evidence] = Field(default_factory=list)
    moments: list[Moment] = Field(default_factory=list)
    est: bool = False
    lesson_id: str | None = None


class Rule:
    id: ClassVar[str]
    habit: ClassVar[str]  # 1-3 words, shown on the Trends page
    lesson_id: ClassVar[str | None] = None
    requires_replay: ClassVar[bool] = False
    needs_bench: ClassVar[bool] = False
    TEXT: ClassVar[dict[str, str]] = {}  # every user-facing string, as a format template

    def skip_reason(self, ctx: MatchContext) -> str | None:
        if self.requires_replay and ctx.replay is None:
            return "Needs a replay file"
        if self.needs_bench and ctx.bench is None:
            return "No rank data yet"
        return None

    def evaluate(self, ctx: MatchContext) -> list[Finding]:
        raise NotImplementedError

    def t(self, key: str, **values) -> str:
        return self.TEXT[key].format(**values)

    def finding(
        self,
        severity: Severity,
        score: float,
        headline: str,
        more: list[str],
        evidence: list[Evidence],
        moments: list[Moment],
        est: bool = False,
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            habit=self.habit,
            severity=severity,
            score=round(score, 3),
            headline=headline,
            do_next=self.TEXT["do_next"],
            more=more[:3],
            evidence=evidence,
            moments=moments,
            est=est or any(e.est for e in evidence),
            lesson_id=self.lesson_id,
        )


REGISTRY: dict[str, Rule] = {}


def register(cls: type[Rule]) -> type[Rule]:
    if cls.id in REGISTRY:
        raise ValueError(f"Duplicate rule id {cls.id}")
    REGISTRY[cls.id] = cls()
    return cls


# ---- helpers shared by rules -------------------------------------------------


def clock(t: float) -> str:
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def nearest_ally_units(ctx: MatchContext, t: int, x: float, y: float) -> float | None:
    """Distance to the closest living teammate at second t, or None if none is alive."""
    best = None
    for a in ctx.allies:
        if a.track is None or not a.alive_at(t):
            continue
        d = math.dist(a.track.at(t), (x, y))
        best = d if best is None else min(best, d)
    return best


def min_distance(track, t0: int, t1: int, x: float, y: float) -> float:
    return min(math.dist(track.at(t), (x, y)) for t in range(max(0, t0), t1 + 1))


def lobby_average(ctx: MatchContext, measure: Callable[[MatchContext], float | None]) -> float | None:
    """Average of `measure` over the other 11 players in the same match.

    Used as the benchmark for habits the API has no rank stats for: same match,
    same lobby rank, real numbers.
    """
    vals = [measure(replace(ctx, player=p)) for p in ctx.players if p.slot != ctx.player.slot]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None
