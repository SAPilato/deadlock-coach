"""Lessons: readable, linked to findings, numbers from data."""
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.findings.base import REGISTRY
from app.learn.lessons import BY_ID, LESSONS, TOPICS
from app.main import create_app
from app.state import create_state

MAX_WORDS = 15
MAP_MODES = {"explore", "route", "waves", "heatmap", "decide"}  # frontend MacroMap MODES
BRIEF_TOPICS = {"wave-management", "slow-vs-fast-push", "freezing", "rotate-after-laning",
                "waves-and-camps", "item-timing", "group-for-objectives"}


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def test_every_finding_has_a_lesson():
    for rid, rule in REGISTRY.items():
        assert rule.lesson_id in BY_ID, f"{rid} points to missing lesson {rule.lesson_id}"


def test_brief_topics_are_covered():
    assert BRIEF_TOPICS <= set(BY_ID)


@pytest.mark.parametrize("lesson", LESSONS, ids=[x["id"] for x in LESSONS])
def test_lesson_cards_are_short(lesson):
    assert 1 <= len(lesson["title"].split()) <= 5
    assert 1 <= len(lesson["points"]) <= 3
    assert len(lesson["facts"]) <= 3
    assert lesson["topic"] in TOPICS
    for text in [lesson["summary"], *lesson["points"], lesson["try"]["label"]]:
        for s in sentences(text):
            assert len(s.split()) <= MAX_WORDS, s
    # Coaching text carries no game numbers; those come from facts.py.
    assert not re.search(r"\d", " ".join([lesson["summary"], *lesson["points"]])), lesson["id"]
    assert lesson["try"]["href"].startswith(("/map", "/build"))
    assert re.fullmatch(r"[a-z]+(-[a-z]+)*", lesson["icon"]), "icons are names, not emojis"


@pytest.fixture(scope="module")
def api():
    app = create_app(lambda: create_state(":memory:", offline=True))
    with TestClient(app) as client:
        yield client


def test_learn_api_fills_facts_from_data(api):
    lessons = {x["id"]: x for x in api.get("/api/learn").json()}
    assert len(lessons) == len(LESSONS)
    for lesson in LESSONS:  # the seed data is enough to fill every fact
        assert len(lessons[lesson["id"]]["facts"]) == len(lesson["facts"]), lesson["id"]
    for lesson in lessons.values():
        for fact in lesson["facts"]:
            assert fact["source"] in ("game data", "measured", "replay")
            for s in sentences(fact["text"]):
                assert len(s.split()) <= MAX_WORDS, s
    assert lessons["item-timing"]["rule_id"] == "late_core_item"
    assert lessons["freezing"]["rule_id"] is None


def test_try_links_open_real_map_views(api):
    layer_ids = {x["id"] for x in api.get("/api/macro/layers").json()["layers"]}
    for lesson in LESSONS:
        url = urlparse(lesson["try"]["href"])
        q = parse_qs(url.query)
        if url.path == "/map":
            assert q["mode"][0] in MAP_MODES, lesson["id"]
            assert set(q.get("layers", [""])[0].split(",")) - {""} <= layer_ids, lesson["id"]


def test_lesson_icons_exist_in_the_frontend():
    src = (Path(__file__).parents[2] / "frontend/src/components/LessonIcon.tsx").read_text(encoding="utf-8")
    block = src.split("const ICONS", 1)[1].split("};", 1)[0]
    names = set(re.findall(r'^\s*"?([a-z-]+)"?:', block, re.M))
    assert {x["icon"] for x in LESSONS} <= names
