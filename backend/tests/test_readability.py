"""Enforces the Readability rules on every user-facing string the rules can produce.

- Max ~15 words per sentence.
- Max 3 bullets ("more" lines) per card.
- A habit name is a short label (1-3 words).
"""
import re

import pytest

from app.config import DEFAULT_BRACKET
from app.findings.base import REGISTRY
from app.findings.engine import run_rules

MAX_WORDS = 15


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def words(sentence: str) -> int:
    return len(sentence.split())


@pytest.mark.parametrize("rule_id", list(REGISTRY))
def test_rule_templates_are_short(rule_id):
    rule = REGISTRY[rule_id]
    assert 1 <= len(rule.habit.split()) <= 3, rule.habit
    assert "do_next" in rule.TEXT and "headline" in rule.TEXT
    for key, template in rule.TEXT.items():
        for s in sentences(template):
            assert words(s) <= MAX_WORDS, f"{rule_id}.{key}: {s!r}"


def test_map_tips_and_scenario_options_are_short():
    from app.macro.layers import TIPS
    from app.macro.scenarios import OPTIONS

    for key, tip in TIPS.items():
        for s in sentences(tip):
            assert words(s) <= MAX_WORDS, f"tip {key}: {s!r}"
    assert all(len(o["label"].split()) <= 4 for o in OPTIONS)


def test_rendered_findings_on_seed_matches_are_short(seed_gd, seed_info):
    from app.analysis.loader import load_context

    checked = 0
    for mid in seed_info["match_ids"]:
        info = seed_gd.match_metadata(mid)["match_info"]
        for p in info["players"]:
            for fnd in run_rules(load_context(seed_gd, mid, p["account_id"], DEFAULT_BRACKET)).findings:
                assert len(fnd.more) <= 3
                for text in [fnd.headline, fnd.do_next, *fnd.more]:
                    for s in sentences(text):
                        assert words(s) <= MAX_WORDS, s
                checked += 1
    assert checked > 10
