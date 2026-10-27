"""API tests against the bundled seed, fully offline."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.state import create_state


@pytest.fixture(scope="module")
def api():
    app = create_app(lambda: create_state(":memory:", offline=True))
    with TestClient(app) as client:
        yield client


def test_meta_reports_patch_and_sample_mode(api):
    m = api.get("/api/meta").json()
    assert m["using_sample"] is True
    assert m["patch"]["live_build"] >= m["patch"]["cached_build"] > 6000
    assert m["bracket_names"][0]["name"].startswith("Ritualist")
    assert m["bracket_names"][1]["name"].startswith("Emissary")


def test_match_list_from_seed(api, seed_info):
    data = api.get("/api/matches").json()
    ids = [m["match_id"] for m in data["matches"]]
    assert set(seed_info["match_ids"]) <= set(ids)
    first = data["matches"][0]
    assert first["hero"]["name"] and isinstance(first["won"], bool)


def test_report_has_every_section(api, seed_info):
    r = api.get(f"/api/matches/{seed_info['match_ids'][0]}/report").json()
    for key in ("match", "findings", "passed", "skipped", "benchmarks", "timeline", "deaths", "items", "lane", "map"):
        assert key in r
    assert r["benchmarks"]["available"] and r["benchmarks"]["tiles"]
    assert r["timeline"]["series"][0] == {"t": 0, "you": 0, "avg": 0}
    assert all(0 <= d["left"] <= 1 and 0 <= d["top"] <= 1 for d in r["deaths"])
    assert {d["phase"] for d in r["deaths"]} <= {"early", "mid", "late"}
    assert [c["t"] for c in r["lane"]["checkpoints"]] == [360, 540, 720]
    assert any(s["rule_id"] == "urn_contest" for s in r["skipped"])
    assert len(r["map"]["lanes"]) == 3 and all(len(lane["pts"]) > 10 for lane in r["map"]["lanes"])


def test_paths_for_scrubber(api, seed_info):
    p = api.get(f"/api/matches/{seed_info['match_ids'][0]}/paths?step=10").json()
    assert len(p["players"]) == 12
    assert sum(1 for q in p["players"] if q["is_me"]) == 1
    assert len(p["players"][0]["pts"]) == p["duration_s"] // 10 + 1
    # Zipline rides come from the per-second movement types: every player rides at some point.
    lane_ids = {ln["id"] for ln in p["lanes"]}
    assert len(lane_ids) == 3
    rides = [r for q in p["players"] for r in q["zip"]]
    assert all(q["zip"] for q in p["players"])
    assert all(0 <= start < end <= p["duration_s"] + 1 and lane in lane_ids for start, end, lane in rides)


def test_trends_and_focus(api):
    t = api.get("/api/trends?n=6").json()
    assert t["matches"] and t["habits"]
    assert {h["status"] for h in t["habits"]} <= {"improving", "same", "worse", "not_enough"}
    if t["focus"]:
        assert t["focus"]["do_next"]


def test_settings_accepts_steam64_and_bracket(api):
    r = api.put("/api/settings", json={"steam_id": "76561198000000000", "bracket": [76, 61]}).json()
    assert r["account_id"] == 39734272 and r["bracket"] == [61, 76]
    assert api.put("/api/settings", json={"steam_id": "nope"}).status_code == 400
    r = api.put("/api/settings", json={"clear_account": True}).json()
    assert r["using_sample"] is True
