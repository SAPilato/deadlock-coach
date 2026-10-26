"""Fetch everything a MatchContext needs through GameData and build it."""
from __future__ import annotations

import logging

from app.analysis.geometry import MapGeometry
from app.analysis.model import Benchmarks, MatchContext, build_context
from app.gamedata.client import ApiError
from app.gamedata.service import GameData

log = logging.getLogger(__name__)

_geo_memo: dict[tuple[int, int, int], MapGeometry] = {}


def geometry(gd: GameData) -> MapGeometry:
    """Map geometry from asset data, corrected by the newest parsed replay when there is one."""
    from app.replay.jobs import latest_truth

    map_data, generic, truth = gd.map_data(), gd.generic_data(), latest_truth()
    key = (id(map_data), id(generic), id(truth))
    if key not in _geo_memo:
        _geo_memo.clear()
        _geo_memo[key] = MapGeometry(map_data, generic, truth)
    return _geo_memo[key]


def load_bench(gd: GameData, hero_id: int, bracket: tuple[int, int]) -> Benchmarks | None:
    try:
        metrics = gd.hero_metrics(hero_id, bracket)
        curve = gd.perf_curve(hero_id, bracket)
        items = gd.item_stats(hero_id, bracket)
    except ApiError as e:
        log.info("No benchmarks for hero %s: %s", hero_id, e)
        return None
    return Benchmarks(bracket=bracket, metrics=metrics or {}, curve=curve or [], items={r["item_id"]: r for r in items or []})


def load_context(
    gd: GameData, match_id: int, account_id: int, bracket: tuple[int, int], replay=None, with_bench: bool = True
) -> MatchContext:
    meta = gd.match_metadata(match_id)
    info = meta.get("match_info", meta)
    me = next((p for p in info["players"] if p["account_id"] == account_id), None)
    if me is None:
        raise ValueError(f"Account {account_id} is not in match {match_id}")
    return build_context(
        meta,
        account_id,
        hero_map=gd.hero_map(),
        item_map=gd.item_map(),
        geo=geometry(gd),
        enums=gd.enums(),
        objective_label=gd.objective_label,
        bench=load_bench(gd, me["hero_id"], bracket) if with_bench else None,
        replay=replay,
    )
