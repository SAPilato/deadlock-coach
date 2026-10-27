import math
import statistics

from app.analysis.loader import geometry
from app.analysis.model import ObjectiveEvent
from app.analysis.paths import Track, zipline_rides
from app.analysis.zipline import reach_from_samples
from app.report import phase_bounds, phase_of
from tests import factories as f


def test_seed_is_available(seed_info):
    assert seed_info and len(seed_info["match_ids"]) >= 2


def test_path_decoding_matches_death_positions(seed_contexts):
    """Decoded per-second positions should sit where the API says each death happened."""
    errors = []
    for ctx in seed_contexts:
        for p in ctx.players:
            for d in p.death_list:
                if p.track:
                    errors.append(math.dist(p.track.at(d.t), (d.x, d.y)))
    assert len(errors) > 50
    assert statistics.median(errors) < 400  # world units; players move ~300+ units/s


def test_minimap_transform_fits_entities(seed_gd):
    geo = geometry(seed_gd)
    assert geo.fit_error < 0.005
    x, y = geo.to_world(*geo.to_rel(1234.0, -4321.0))
    assert abs(x - 1234.0) < 1e-6 and abs(y + 4321.0) < 1e-6


def test_lanes_come_from_zipline_colors(seed_gd):
    geo = geometry(seed_gd)
    names = {lane.name for lane in geo.lanes.values()}
    assert len(geo.lanes) == 3
    assert "Unused" not in names
    # Every objective lane number maps to a distinct lane.
    assert len(set(geo.objective_lane.values())) == len(geo.objective_lane) == 3


def test_teams_start_in_their_own_base(seed_contexts):
    for ctx in seed_contexts:
        for p in ctx.players:
            if p.track:
                assert ctx.geo.enemy_progress(p.team, *p.track.at(0)) < 0.2


def test_objective_lane_mapping_matches_players(seed_contexts):
    """Players assigned to a lane are near that lane's Guardians early on."""
    hits = total = 0
    for ctx in seed_contexts:
        for p in ctx.players:
            if not p.track:
                continue
            x, y = p.track.at(150)  # laning, before most rotations
            lane = ctx.geo.nearest_lane(x, y)
            total += 1
            hits += lane is not None and lane.id == p.lane
    assert hits / total > 0.75


def test_objectives_have_positions_and_owner(seed_contexts):
    for ctx in seed_contexts:
        guardians = [o for o in ctx.objectives if o.kind == "tier1"]
        assert guardians, "every full match loses some Guardians"
        assert all(o.x is not None and o.lane_id in ctx.geo.lanes for o in guardians)
        cores = [o for o in ctx.objectives if o.kind == "core"]
        if cores:
            # The core that falls belongs to the losing team.
            assert cores[-1].owner_team != ctx.winning_team


def test_upgrades_only_in_item_list(seed_contexts):
    for ctx in seed_contexts:
        assert ctx.player.items
        assert all(i.tier for i in ctx.player.items)


def _fell(kind: str, t: int, lane_id=None) -> ObjectiveEvent:
    return ObjectiveEvent(t=t, owner_team=1, objective_id=0, kind=kind, lane_num=None, lane_id=lane_id,
                          name=kind, x=None, y=None)


def test_late_game_starts_at_first_base_guardian_not_walker(seed_gd):
    me = f.player(0, 0, duration=2400)
    objectives = [_fell("tier1", 500, me.lane), _fell("tier2", 900), _fell("barracks", 1600), _fell("barracks", 1500)]
    bounds = phase_bounds(f.context(seed_gd, [me], duration=2400, objectives=objectives))
    assert bounds == (500, 1500, False)
    assert [phase_of(t, bounds) for t in (400, 1000, 1499, 1500)] == ["early", "mid", "mid", "late"]


def test_no_base_guardian_down_means_no_late_game(seed_gd):
    me = f.player(0, 0, duration=1700)
    objectives = [_fell("tier1", 500, me.lane), _fell("tier2", 900)]
    bounds = phase_bounds(f.context(seed_gd, [me], duration=1700, objectives=objectives))
    assert bounds[1] == 1700
    assert phase_of(1699, bounds) == "mid"


class _Lane:
    def __init__(self, id, y):
        self.id, self.y = id, y

    def dist(self, x, y):
        return abs(y - self.y)


def test_zipline_rides_split_by_lane():
    zip_id = 6
    move = [0, 6, 6, 6, 0, 0, 6, 6, 0, 6]  # three rides; the last runs to the end
    ys = [0, 0, 0, 0, 0, 0, 900, 900, 900, 0]
    tr = Track(slot=0, x=[0.0] * 10, y=[float(v) for v in ys], health=[1] * 10, combat=[0] * 10, move=move)
    rides = zipline_rides(tr, zip_id, [_Lane(1, 0), _Lane(4, 1000)])
    assert [(r.start, r.end, r.lane_id) for r in rides] == [(1, 4, 1), (6, 8, 4), (9, 10, 1)]
    assert zipline_rides(tr, None, [_Lane(1, 0)]) == []


def test_zipline_reach_grows_with_riders_and_never_overlaps():
    samples = {
        30: [(1, 0, 0.40)],  # inside the start reach: no change
        60: [(1, 0, 0.55)],  # team 0 rides past the middle: it owns 55%, team 1 at most 45%
        90: [(1, 1, 0.70)],  # team 1 pushes back: it owns 70%, team 0 at most 30%
        95: [(1, 1, 0.705)],  # under 1% more: not recorded
    }
    out = reach_from_samples(samples, [1, 4], start=0.43)
    assert out[1] == [[0, 0.43, 0.43], [60, 0.55, 0.43], [90, 0.3, 0.7]]
    assert out[4] == [[0, 0.43, 0.43]]
    assert all(r0 + r1 <= 1.0 for _, r0, r1 in out[1])


class _StraightLane:
    """A lane along x from 0 (team 0's base) to 1000 (team 1's base)."""
    id = 1
    length = 1000.0

    def project(self, x, y):
        return x, abs(y)


def test_exact_zipline_control_from_replay_nodes():
    from app.analysis.zipline import control_from_nodes

    # 11 nodes at x = 0, 100, ..., 1000; the two at each end cannot be captured.
    nodes = [{"handle": i, "lane": 1, "x": i * 100.0, "y": 0.0, "capturable": 2 <= i <= 8} for i in range(11)]
    start = [(0, i, 0) for i in range(5)] + [(0, i, 1) for i in range(6, 11)]  # node 5 neutral at first
    changes = start + [(300, 5, 1), (300, 4, 1), (900, 4, 0), (900, 5, 0), (900, 6, 0)]
    out = control_from_nodes(nodes, changes, {1: _StraightLane()})
    assert out["home"]["1"] == [0.1, 0.1]  # nodes 0-1 and 9-10 are fixed
    assert out["start"]["1"] == [0.4, 0.4]
    assert out["timeline"]["1"] == [[0, 0.4, 0.4], [300, 0.3, 0.6], [900, 0.6, 0.3]]


def test_estimate_starts_per_lane_and_keeps_home_stretches():
    samples = {60: [(1, 0, 0.95)]}  # a rider deep in the enemy's home stretch
    out = reach_from_samples(samples, [1], start={1: [0.46, 0.41]}, home={1: [0.2, 0.2]})
    assert out[1][0] == [0, 0.46, 0.41]
    assert out[1][-1] == [60, 0.8, 0.2]  # capped at the enemy's home stretch, which they keep
