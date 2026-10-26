"""Post-City Never Sleeps map: replay truth, current layers, measured movement."""
import math

import pytest
from fastapi.testclient import TestClient

from app.analysis.geometry import MapGeometry
from app.analysis.loader import geometry
from app.macro.truth import truth_from_rows
from app.main import create_app
from app.replay.jobs import latest_truth
from app.state import create_state


def test_truth_keeps_spawns_and_deliveries_not_drop_pickups():
    urn = [
        {"tick": 1, "event": "picked_up", "x": -6600, "y": 0},   # spawn west
        {"tick": 2, "event": "dropped", "x": 0, "y": 0},
        {"tick": 3, "event": "picked_up", "x": 10, "y": 5},       # re-pickup at mid: not a site
        {"tick": 4, "event": "returned", "x": 6300, "y": -100},   # delivered east
        {"tick": 5, "event": "picked_up", "x": 6290, "y": -90},   # next spawn east
        {"tick": 6, "event": "returned", "x": -6590, "y": 10},    # delivered west
    ]
    guard = [{"team_num": 2, "lane": 1, "x": -8192, "y": -1856, "max_health": 5500}]
    obj = [
        {"objective_type": "mid_boss", "team_num": 4, "lane": 16777215, "x": 0, "y": 0, "max_health": 13000},
        {"objective_type": "mid_boss", "team_num": 4, "lane": 16777215, "x": 0, "y": 0, "max_health": 20000},  # respawn
        {"objective_type": "shrine", "team_num": 3, "lane": 0, "x": 2816, "y": 7536, "max_health": 5000},
    ]
    t = truth_from_rows(obj, guard, urn, match_id=1, build=None)
    sites = sorted((round(s["x"], -2), round(s["y"], -2)) for s in t["urn_sites"])
    assert sites == [(-6600, 0), (6300, -100)]
    kinds = [o["kind"] for o in t["objectives"]]
    assert kinds.count("mid_boss") == 1 and "shrine" in kinds and "tier1" in kinds
    assert next(o for o in t["objectives"] if o["kind"] == "tier1")["team"] == 0


def test_replay_truth_replaces_icon_positions(seed_gd):
    truth = latest_truth()
    assert truth and len(truth["urn_sites"]) == 2
    plain = MapGeometry(seed_gd.map_data(), seed_gd.generic_data())
    fixed = geometry(seed_gd)
    guardian = next(o for o in truth["objectives"] if o["kind"] == "tier1" and o["team"] == 0)
    key = next(k for k, lane in fixed.objective_lane.items() if lane == guardian["lane"])
    assert fixed.objectives[f"team0_tier1_{key}"] == (guardian["x"], guardian["y"])
    assert math.dist(plain.objectives[f"team0_tier1_{key}"], fixed.objectives[f"team0_tier1_{key}"]) > 1000
    assert {o["kind"] for o in fixed.extra} >= {"barracks", "shrine", "mid_boss"}


@pytest.fixture(scope="module")
def api():
    app = create_app(lambda: create_state(":memory:", offline=True))
    with TestClient(app) as client:
        yield client


def test_layers_show_the_current_map(api, seed_gd):
    d = api.get("/api/macro/layers").json()
    layers = {layer["id"]: layer for layer in d["layers"]}
    urn = layers["urn"]["points"]
    assert len(urn) == 2  # not the 6 points the asset data lists
    legacy = [e["position"] for e in seed_gd.map_data()["entities"]["soul_urn_spawns"]]
    tf = d["transform"]
    for p in urn:
        x, y = (p["left"] - tf["bx"]) / tf["ax"], (p["top"] - tf["by"]) / tf["ay"]
        close = [lp for lp in legacy if math.dist((x, y), lp[:2]) < 400]
        assert len(close) == 1  # each site is one of the two live points
    kinds = {p["kind"] for p in layers["objectives"]["points"]}
    assert kinds >= {"guardian", "walker", "base_guardian", "shrine", "patron", "mid_boss"}
    assert {p["label"] for p in layers["special"]["points"]} == {"Bell Tower", "Sunken Plaza"}
    assert {"Theater", "Chinatown", "Haunted Lot", "Plaza"} <= {p["label"] for p in layers["districts"]["points"]}
    assert all("Haunt" in p["label"] for p in layers["camps"]["points"])
    assert layers["vents"]["points"] and not any(p["label"] == "Steam vent" for p in layers["movement"]["points"])
    assert "spirit resist" in layers["statues"]["points"][0]["facts"]
    assert d["verified"]["match_id"]


def test_measured_movement(api):
    m = api.get("/api/macro/movement").json()
    assert m["matches"] >= 2 and m["samples"]["zip_s"] > 1000
    assert m["zip_speed"] > m["fast_speed"] > m["foot_speed"] > 0
    assert 1 <= m["detour_best"] <= m["detour"]
    assert len(m["walkable"]) > 100
