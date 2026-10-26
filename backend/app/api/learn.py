"""Learn API: lesson cards with their game-data facts."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import coach
from app.api.routes import _api_errors
from app.findings.base import REGISTRY
from app.learn.facts import lessons_with_facts
from app.state import AppState

router = APIRouter()


@router.get("/learn")
def lessons(st: AppState = Depends(coach)):
    """Every lesson, its facts, and the findings rule that suggests it (if any)."""
    rules = {r.lesson_id: (rid, r) for rid, r in REGISTRY.items() if r.lesson_id}
    out = []
    for lesson in _api_errors(lambda: lessons_with_facts(st)):
        rid, rule = rules.get(lesson["id"], (None, None))
        out.append({**lesson, "rule_id": rid, "habit": rule.habit if rule else None})
    return out
