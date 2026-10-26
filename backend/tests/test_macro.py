"""Macro Map: layers, wave math, endpoints (offline seed, incl. the bundled sample replay)."""
import pytest
from fastapi.testclient import TestClient

from app.analysis.loader import geometry
from app.macro.waves import frames_from_rows, meets_per_minute
from app.main import create_app
from app.state import create_state


@pytest.fixture(scope="module")
def api():
    app = create_app(lambda: create_state(":memory:", offline=True))
    with TestClient(app) as client:
        yield client


def test_layers_come_from_map_data(api):
    data = api.get("/api/macro/layers").json()
    layers = {layer["id"]: layer for layer in data["layers"]}
    for lid in ("objectives", "camps", "urn", "shops", "crates", "statues", "movement"):
        assert layers[lid]["points"], lid
    assert len(layers["lanes"]["lines"]) == 3
    pts = [p for layer in data["layers"] for p in layer["points"]]
    assert all(-0.05 <= p["left"] <= 1.05 and -0.05 <= p["top"] <= 1.05 for p in pts)
    guardian = next(p for p in layers["objectives"]["points"] if p["kind"] == "guardian")
    assert "HP" in guardian["facts"] and "souls" in guardian["facts"]
    assert any(p.get("target") for p in layers["movement"]["points"])  # teleporters / pads point somewhere
    assert data["heroes"] and data["heroes"][0]["move"] > 0


def test_lanes_run_from_team0_to_team1(seed_gd):
    geo = geometry(seed_gd)
    for lane in geo.lanes.values():
        start, end = lane.points[0], lane.points[-1]
        assert geo.enemy_progress(0, *start) < geo.enemy_progress(0, *end)
        s, d = lane.project(*lane.point_at(lane.length / 3))
        assert s == pytest.approx(lane.length / 3, rel=1e-3) and d < 1e-6


def test_wave_fronts_meet_when_close(seed_gd):
    geo = geometry(seed_gd)
    lane_id = next(iter(geo.lanes))
    lane = geo.lanes[lane_id]
    near = lambda f: {"team_num": 2, "lane": lane_id, "x": lane.point_at(lane.length * f)[0], "y": lane.point_at(lane.length * f)[1]}  # noqa: E731
    far = lambda f: {"team_num": 3, "lane": lane_id, "x": lane.point_at(lane.length * f)[0], "y": lane.point_at(lane.length * f)[1]}  # noqa: E731
    frames = frames_from_rows({
        30: [near(0.30), near(0.31), far(0.70)],          # apart: no contact
        60: [near(0.49), near(0.50), far(0.51), far(0.52)],  # touching
    }, geo)
    lanes = [f["lanes"][str(lane_id)] for f in frames]
    assert lanes[0]["c"] is None
    assert lanes[1]["c"] == pytest.approx(0.505, abs=0.01)
    assert {w[0] for w in lanes[1]["w"]} == {0, 1}
    assert meets_per_minute(frames) == [{"minute": 1, "lanes": {str(lane_id): lanes[1]["c"]}}]


def test_waves_endpoint_serves_bundled_sample(api):
    w = api.get("/api/macro/waves").json()
    assert w["available"] and w["available"][0]["sample"]
    assert len(w["frames"]) > 500 and len(w["lanes"]) == 3
    assert w["schedule"]["first"] == 16 and w["schedule"]["squad"] == 4
    assert any(m["lanes"] for m in w["meets"])


def test_heatmap_and_scenarios_from_seed(api):
    h = api.get("/api/macro/heatmap?n=5").json()
    assert h["matches"] >= 1 and h["phases"]["early"]["cells"] and h["objectives"]
    rows = api.get("/api/macro/scenarios").json()
    assert rows, "seed matches have flagged moments"
    s = api.get(f"/api/macro/scenario?match_id={rows[0]['match_id']}&t={rows[0]['t']}").json()
    assert len(s["players"]) == 12 and len(s["frames"]) >= 10
    assert s["did"]["label"] and len(s["options"]) == 4
    assert {o["kind"] for o in s["objectives"]} >= {"tier1", "tier2"}
