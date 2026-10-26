from app.findings.base import REGISTRY
from app.replay.jobs import ReplayData
from app.replay.parser import urn_episodes
from tests import factories as f


def ev(tick, event, hero=0, x=0.0, y=0.0):
    return {"tick": tick, "event": event, "hero_id": hero, "team_num": 0, "x": x, "y": y, "z": 0.0}


def test_urn_events_group_into_episodes():
    rows = [
        ev(5, "delivery_active", x=9, y=9),  # before any pickup: ignored
        ev(10, "picked_up", hero=7, x=1, y=1),
        ev(20, "dropped", hero=7, x=2, y=2),
        ev(25, "picked_up", hero=3, x=2, y=2),
        ev(40, "returned", hero=3, x=5, y=5),
        ev(100, "picked_up", hero=1, x=6, y=6),
    ]
    eps = urn_episodes(rows, to_seconds=lambda tick: float(tick))
    assert len(eps) == 2
    assert eps[0]["carriers"] == [[7, 10.0, 20.0], [3, 25.0, 40.0]]
    assert [c[0] for c in eps[0]["checkpoints"]] == [10.0, 20.0, 25.0, 40.0]
    assert eps[1]["carriers"] == [[1, 100.0, None]]  # match ended while carried


def test_replay_data_round_trip(tmp_path):
    data = ReplayData(match_id=5, urn_events=[{"checkpoints": [(1.0, 2.0, 3.0)], "carriers": [[7, 1.0, 9.0]]}])
    data.save(tmp_path / "r.json")
    back = ReplayData.load(tmp_path / "r.json")
    assert back.urn_events[0]["checkpoints"] == [(1.0, 2.0, 3.0)]


def test_urn_rule_follows_the_carrier(seed_gd):
    """You never touch urn event points, but you escort the carrier: that counts."""
    from app.analysis.loader import geometry

    geo = geometry(seed_gd)
    pts = geo.lanes[next(iter(geo.lanes))].points
    carrier_path = lambda t: pts[min(len(pts) - 1, t // 30)]  # noqa: E731
    me = f.player(0, 0, where=carrier_path)
    me_ally = f.player(1, 0, where=carrier_path)
    me_ally.hero_id = 99
    enemies = [f.player(s, 1, where=(0.0, 0.0)) for s in range(6, 12)]
    allies = [f.player(s, 0, where=(0.0, 0.0)) for s in range(2, 6)]
    far = (99999.0, 99999.0)
    urns = [{"checkpoints": [(t, *far), (t + 300, *far)], "carriers": [[99, t, t + 300]]} for t in (600, 1000)]

    class R:
        urn_events = urns

    ctx = f.context(seed_gd, [me, me_ally, *allies, *enemies], replay=R())
    assert REGISTRY["urn_contest"].evaluate(ctx) == []
