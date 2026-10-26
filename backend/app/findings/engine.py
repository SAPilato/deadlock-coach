"""Run every registered rule on a match and rank the findings."""
from __future__ import annotations

import logging

from pydantic import BaseModel

import app.findings.rules  # noqa: F401  (registers rules)
from app.analysis.model import MatchContext
from app.findings.base import REGISTRY, SEVERITY_RANK, Finding

log = logging.getLogger(__name__)


class HabitStatus(BaseModel):
    rule_id: str
    habit: str
    reason: str | None = None


class Report(BaseModel):
    findings: list[Finding]
    passed: list[HabitStatus]  # rules that ran and found nothing wrong
    skipped: list[HabitStatus]  # rules that could not run (no replay, no rank data)


def run_rules(ctx: MatchContext, rule_ids: list[str] | None = None) -> Report:
    findings: list[Finding] = []
    passed: list[HabitStatus] = []
    skipped: list[HabitStatus] = []
    for rid, rule in REGISTRY.items():
        if rule_ids and rid not in rule_ids:
            continue
        reason = rule.skip_reason(ctx)
        if reason:
            skipped.append(HabitStatus(rule_id=rid, habit=rule.habit, reason=reason))
            continue
        try:
            found = rule.evaluate(ctx)
        except Exception as e:  # one broken rule must not hide the others
            log.exception("Rule %s failed on match %s", rid, ctx.match_id)
            skipped.append(HabitStatus(rule_id=rid, habit=rule.habit, reason=f"Error: {e}"))
            continue
        if found:
            findings.extend(found)
        else:
            passed.append(HabitStatus(rule_id=rid, habit=rule.habit))
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.score), reverse=True)
    return Report(findings=findings, passed=passed, skipped=skipped)
