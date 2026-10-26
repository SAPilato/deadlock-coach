import pytest

from app.analysis.loader import geometry
from app.analysis.model import Benchmarks, ItemBuy, ObjectiveEvent, Snapshot
from app.findings.base import REGISTRY
from app.findings.engine import run_rules
from tests import factories as f

BRACKET = (61, 76)


@pytest.fixture(scope="module")
def geo(seed_gd):
    return geometry(seed_gd)


def along(geo, team: int, frac: float) -> tuple[float, float]:
    """Point `frac` of the way from `team`'s core to the enemy core."""
    (ax, ay), (bx, by) = geo.cores[team], geo.cores[1 - team]
    return ax + (bx - ax) * frac, ay + (by - ay) * frac


def lane_point(geo, lane_id: int, i: int = 10) -> tuple[float, float]:
    return geo.lanes[lane_id].points[i]


def evaluate(rule_id: str, ctx):
    rule = REGISTRY[rule_id]
    assert rule.skip_reason(ctx) is None
    return rule.evaluate(ctx)


# ---- souls per minute ---------------------------------------------------------


def souls_bench(curve=None) -> Benchmarks:
    m = {"net_worth_per_min": {"percentile10": 700.0, "percentile25": 850.0, "percentile50": 1000.0, "avg": 1010.0}}
    return Benchmarks(bracket=BRACKET, metrics=m, curve=curve or [], items={})


@pytest.mark.parametrize("net_worth,expected", [(30 * 650, "high"), (30 * 800, "med"), (30 * 900, None)])
def test_low_souls_per_min_severity(seed_gd, net_worth, expected):
    me = f.player(0, 0, net_worth=net_worth)
    found = evaluate("low_souls_per_min", f.lobby(seed_gd, me, bench=souls_bench()))
    assert (found[0].severity if found else None) == expected


def test_low_souls_points_at_worst_window(seed_gd):
    curve = [{"game_time": t, "net_worth_avg": t * 17.0} for t in (180, 360, 540)]
    snaps = [Snapshot(t, nw, 0, 0, 0, 0, 0, 0, 1, 0) for t, nw in ((180, 3000), (360, 6000), (540, 6500))]
    me = f.player(0, 0, net_worth=30 * 650, snapshots=snaps)
    found = evaluate("low_souls_per_min", f.lobby(seed_gd, me, bench=souls_bench(curve)))
    assert found[0].moments[0].t == 360  # lost the most ground between 6:00 and 9:00
    assert "6:00" in found[0].more[0]


def test_low_souls_skips_without_bench(seed_gd):
    ctx = f.lobby(seed_gd, f.player(0, 0))
    assert REGISTRY["low_souls_per_min"].skip_reason(ctx) == "No rank data yet"


# ---- dying alone ----------------------------------------------------------------


def test_died_alone_flags_deaths_far_from_allies(seed_gd, geo):
    deep = along(geo, 0, 0.8)
    me = f.player(0, 0, deaths=[(600, deep), (900, deep), (1200, deep)])
    ctx = f.lobby(seed_gd, me, ally_where=along(geo, 0, 0.2), enemy_where=along(geo, 1, 0.2))
    found = evaluate("died_alone", ctx)
    assert found and found[0].headline.startswith("3 of 3 deaths")
    assert any("deep" in m for m in found[0].more)
    assert found[0].evidence[0].benchmark == 0  # nobody else in this lobby died alone


def test_died_alone_ignores_deaths_next_to_allies(seed_gd, geo):
    spot = along(geo, 0, 0.6)
    me = f.player(0, 0, deaths=[(600, spot), (900, spot), (1200, spot)])
    assert evaluate("died_alone", f.lobby(seed_gd, me, ally_where=spot)) == []


# ---- same death spot --------------------------------------------------------------


def test_same_spot_needs_three_close_deaths(seed_gd, geo):
    spot = lane_point(geo, 1)
    x, y = spot
    close = [(300, spot), (700, (x + 300, y)), (1100, (x, y + 300))]
    found = evaluate("same_death_spot", f.lobby(seed_gd, f.player(0, 0, deaths=close)))
    assert found and "3 times" in found[0].headline
    assert geo.lanes[1].name in found[0].headline


def test_same_spot_ignores_spread_deaths(seed_gd, geo):
    spread = [(300, along(geo, 0, 0.3)), (700, along(geo, 0, 0.6)), (1100, along(geo, 0, 0.9))]
    assert evaluate("same_death_spot", f.lobby(seed_gd, f.player(0, 0, deaths=spread))) == []


# ---- idle time --------------------------------------------------------------------


def test_idle_flags_long_no_combat_stretches(seed_gd):
    # Out of combat (0) for 5 minutes at a time, then 1 minute of fighting.
    me = f.player(0, 0, combat=lambda t: 0 if (t // 60) % 6 else 1)
    found = evaluate("idle_time", f.lobby(seed_gd, me))
    assert found and found[0].severity == "high"
    assert found[0].evidence[0].benchmark == 0
    assert found[0].est


def test_idle_ignores_short_gaps(seed_gd):
    me = f.player(0, 0, combat=lambda t: 0 if t % 50 < 30 else 1)  # 30 s gaps only
    assert evaluate("idle_time", f.lobby(seed_gd, me)) == []


# ---- late core item -----------------------------------------------------------------


def core_item(seed_gd) -> dict:
    return next(
        i for i in seed_gd.items()
        if i.get("type") == "upgrade" and i.get("shopable") and (i.get("item_tier") or 0) >= 3
    )


def item_bench(item_id: int, avg: float) -> Benchmarks:
    return Benchmarks(BRACKET, {}, [], {item_id: {"item_id": item_id, "matches": 5000, "avg_buy_time_s": avg}})


def buy(item: dict, t: int) -> ItemBuy:
    return ItemBuy(t, item["id"], None, item["name"], item["item_tier"], item["item_slot_type"], item.get("cost"), None)


def test_late_core_item_flags_big_delay(seed_gd):
    item = core_item(seed_gd)
    me = f.player(0, 0, items=[buy(item, 1300)])
    found = evaluate("late_core_item", f.lobby(seed_gd, me, bench=item_bench(item["id"], 700)))
    assert found and found[0].severity == "high"
    assert found[0].headline == f"{item['name']} came 10 min later than average."


def test_late_core_item_ok_when_close_to_average(seed_gd):
    item = core_item(seed_gd)
    me = f.player(0, 0, items=[buy(item, 760)])
    assert evaluate("late_core_item", f.lobby(seed_gd, me, bench=item_bench(item["id"], 700))) == []


# ---- missed objectives ----------------------------------------------------------------


def walker_events(geo, times):
    lane_num = next(iter(geo.objective_lane))
    x, y = geo.objective_pos(1, "tier2", lane_num)
    return [
        ObjectiveEvent(t=t, owner_team=1, objective_id=5, kind="tier2", lane_num=lane_num,
                       lane_id=geo.objective_lane[lane_num], name="Walker", x=x, y=y)
        for t in times
    ], (x, y)


def test_missed_objectives_when_team_groups_without_you(seed_gd, geo):
    events, spot = walker_events(geo, [900, 1200, 1500])
    me = f.player(0, 0, where=along(geo, 0, 0.1))
    found = evaluate("missed_objectives", f.lobby(seed_gd, me, ally_where=spot, objectives=events))
    assert found and found[0].headline == "Missed 3 objective fights your team joined."
    assert all("taken" in m.label for m in found[0].moments)


def test_missed_objectives_ok_when_you_were_there(seed_gd, geo):
    events, spot = walker_events(geo, [900, 1200, 1500])
    me = f.player(0, 0, where=spot)
    assert evaluate("missed_objectives", f.lobby(seed_gd, me, ally_where=spot, objectives=events)) == []


# ---- lane overstay -----------------------------------------------------------------------


def test_lane_overstay_flags_staying_in_lane(seed_gd, geo):
    lane_id = next(iter(geo.lanes))
    me = f.player(0, 0, lane=lane_id, where=lane_point(geo, lane_id, len(geo.lanes[lane_id].points) // 2))
    found = evaluate("lane_overstay", f.lobby(seed_gd, me))
    assert found and found[0].headline.startswith("100%")
    assert "(est.)" in found[0].more[0]  # no Guardian fell: laning end is the 10:00 fallback


def test_lane_overstay_ok_when_roaming(seed_gd, geo):
    lane_ids = list(geo.lanes)
    other = lane_point(geo, lane_ids[1], len(geo.lanes[lane_ids[1]].points) // 2)
    me = f.player(0, 0, lane=lane_ids[0], where=other)
    assert evaluate("lane_overstay", f.lobby(seed_gd, me)) == []


# ---- urn (replay only) -------------------------------------------------------------------


class FakeReplay:
    def __init__(self, urn_events):
        self.urn_events = urn_events


def test_urn_needs_replay(seed_gd):
    ctx = f.lobby(seed_gd, f.player(0, 0))
    assert REGISTRY["urn_contest"].skip_reason(ctx) == "Needs a replay file"


def test_urn_flags_missed_urns(seed_gd, geo):
    far = along(geo, 1, 0.1)
    urns = [{"checkpoints": [(t, *far), (t + 30, *far)]} for t in (900, 1200, 1500)]
    me = f.player(0, 0, where=along(geo, 0, 0.1))
    found = evaluate("urn_contest", f.lobby(seed_gd, me, replay=FakeReplay(urns)))
    assert found and found[0].headline == "Contested 0 of 3 urns."


# ---- engine --------------------------------------------------------------------------------


def test_engine_ranks_by_severity_and_survives_broken_rule(seed_gd, geo, monkeypatch):
    deep = along(geo, 0, 0.8)
    me = f.player(0, 0, net_worth=30 * 650, deaths=[(600, deep), (900, deep), (1200, deep)])
    ctx = f.lobby(seed_gd, me, ally_where=along(geo, 0, 0.2), bench=souls_bench())

    def boom(_ctx):
        raise RuntimeError("bug")

    monkeypatch.setattr(REGISTRY["lane_overstay"], "evaluate", boom)
    report = run_rules(ctx)
    ranks = [{"high": 3, "med": 2, "low": 1}[x.severity] for x in report.findings]
    assert ranks == sorted(ranks, reverse=True)
    assert any(s.rule_id == "lane_overstay" and s.reason.startswith("Error") for s in report.skipped)
    assert any(s.rule_id == "urn_contest" for s in report.skipped)


def test_engine_runs_on_every_seed_player(seed_gd, seed_info):
    from app.analysis.loader import load_context

    for mid in seed_info["match_ids"]:
        info = seed_gd.match_metadata(mid)["match_info"]
        for p in info["players"]:
            report = run_rules(load_context(seed_gd, mid, p["account_id"], BRACKET))
            assert not [s for s in report.skipped if (s.reason or "").startswith("Error")]
