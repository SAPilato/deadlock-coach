"""Build Lab API against the bundled seed, fully offline."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.state import create_state

PARADOX = 10


@pytest.fixture(scope="module")
def api():
    app = create_app(lambda: create_state(":memory:", offline=True))
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def shop(api):
    return api.get(f"/api/buildlab/shop?hero_id={PARADOX}").json()


def item(shop, name):
    return next(i for i in shop["items"] if i["name"] == name)


def compute(api, **build):
    return api.post("/api/buildlab/compute", json={"hero_id": PARADOX, **build}).json()


def row(sheet, key):
    return next(r for r in sheet["rows"] if r["key"] == key)["value"]


def test_heroes_list(api):
    heroes = api.get("/api/buildlab/heroes").json()
    assert len(heroes) > 30 and any(h["name"] == "Paradox" for h in heroes)


def test_shop_has_costs_win_rates_and_measured_slots(shop):
    assert len(shop["items"]) > 100
    assert all(i["cost"] and i["slot"] in ("weapon", "vitality", "spirit") for i in shop["items"])
    assert shop["has_rank_stats"] and any(i["win_rate"] is not None for i in shop["items"])
    assert shop["slots"]["limit"] == 12 and shop["slots"]["est"] is False
    assert shop["levels"][0] == {"level": 1, "souls": 0, "boons": 0}


def test_compute_adds_items_and_reports_warnings(api, shop):
    base = compute(api)
    eh = item(shop, "Extra Health")["id"]
    with_eh = compute(api, items=[eh, eh, 999999])
    assert row(with_eh, "max_health") > row(base, "max_health")
    assert with_eh["items"] == [eh]
    assert len(with_eh["warnings"]) == 2
    assert with_eh["cost"] == item(shop, "Extra Health")["cost"]


def test_compute_enforces_slot_limit(api, shop):
    ids = [i["id"] for i in shop["items"][:15]]
    sheet = compute(api, items=ids)
    assert len(sheet["items"]) == shop["slots"]["limit"]
    assert any("slots" in w for w in sheet["warnings"])


def test_saved_build_round_trip(api, shop):
    eh = item(shop, "Extra Health")["id"]
    saved = api.post("/api/builds", json={"name": "Tank test", "hero_id": PARADOX, "level": 12, "items": [eh]}).json()
    assert saved["id"] and saved["level"] == 12
    assert any(b["id"] == saved["id"] for b in api.get("/api/builds").json())

    exp = api.get(f"/api/builds/{saved['id']}/export")
    assert "attachment" in exp.headers["content-disposition"]
    data = exp.json()
    assert data["format"] == "deadlock-coach-build/1" and data["items"][0]["name"] == "Extra Health"

    copy = api.post("/api/builds/import", json=data).json()
    assert copy["id"] != saved["id"] and copy["items"] == [eh]
    assert api.post("/api/builds/import", json={"format": "nope"}).status_code == 400

    assert api.delete(f"/api/builds/{saved['id']}").status_code == 200
    assert api.delete(f"/api/builds/{saved['id']}").status_code == 404


def test_import_build_from_match(api, seed_info):
    mid = 123203951  # a seed match played on Paradox
    end = api.get(f"/api/matches/{mid}/build").json()
    early = api.get(f"/api/matches/{mid}/build?t=600").json()
    assert end["hero_id"] == PARADOX
    assert 0 < len(early["items"]) < len(end["items"]) <= 12
    assert early["level"] < end["level"]
