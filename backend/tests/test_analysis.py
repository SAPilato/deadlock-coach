import math
import statistics

from app.analysis.loader import geometry


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
