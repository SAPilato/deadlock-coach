"""GameData: the single entry point for patch info, assets, matches and benchmarks."""
from __future__ import annotations

from typing import Any

from app.config import PROTO_URL
from app.gamedata.client import ApiClient, ApiError
from app.gamedata.enums import objective_parts, parse_enums

HOUR = 3600.0
DAY = 24 * HOUR

TTL_VERSIONS = 1 * HOUR
TTL_PATCHES = 6 * HOUR
TTL_ASSETS = 7 * DAY  # also refetched when the live build moves past the cached one
TTL_HISTORY = 10 * 60.0
TTL_RANK = 1 * HOUR
TTL_BENCH = 1 * DAY
TTL_SALTS = 1 * DAY

ASSET_PREFIX = "/v1/assets/"


class GameData:
    def __init__(self, client: ApiClient):
        self.client = client
        self._memo: dict[str, Any] = {}

    # ---- patch --------------------------------------------------------------

    def live_build(self) -> int | None:
        try:
            versions = self.client.get_json("/v1/assets/client-versions", ttl=TTL_VERSIONS)
        except ApiError:
            return None
        return max(versions) if versions else None

    def latest_patch(self) -> dict | None:
        try:
            notes = self.client.get_json("/v2/patches", ttl=TTL_PATCHES)
        except ApiError:
            return None
        if not notes:
            return None
        n = max(notes, key=lambda x: x.get("pub_date") or "")
        return {"title": n.get("title"), "date": n.get("pub_date"), "link": n.get("link")}

    def patch_status(self) -> dict:
        live = self.live_build()
        cached = self.client.cache.oldest_patch(ASSET_PREFIX)
        return {
            "live_build": live,
            "cached_build": cached,
            "stale": bool(live and cached and cached < live),
            "latest_patch": self.latest_patch(),
        }

    def refresh_assets(self) -> int:
        """Drop cached game data so the next request refetches it for the live build."""
        self._memo.clear()
        n = self.client.cache.delete_prefix(ASSET_PREFIX)
        n += self.client.cache.delete_prefix("proto:")
        return n

    # ---- assets -------------------------------------------------------------

    def _asset(self, path: str, params: dict | None = None) -> Any:
        build = self.live_build()
        return self.client.get_json(path, params, ttl=TTL_ASSETS, patch_version=build, min_patch=build)

    def heroes(self) -> list[dict]:
        return self._asset("/v1/assets/heroes")

    def hero_map(self) -> dict[int, dict]:
        return self._indexed("heroes", self.heroes)

    def items(self) -> list[dict]:
        return self._asset("/v1/assets/items")

    def item_map(self) -> dict[int, dict]:
        return self._indexed("items", self.items)

    def ranks(self) -> list[dict]:
        return self._asset("/v1/assets/ranks")

    def generic_data(self) -> dict:
        return self._asset("/v1/assets/generic-data")

    def map_data(self) -> dict:
        return self._asset("/v1/assets/map")

    def npc_units(self) -> list[dict]:
        return self._asset("/v1/assets/npc-units")

    def _indexed(self, name: str, loader) -> dict[int, dict]:
        rows = loader()
        key = f"{name}:{id(rows)}"
        if key not in self._memo:
            self._memo = {k: v for k, v in self._memo.items() if not k.startswith(name + ":")}
            self._memo[key] = {r["id"]: r for r in rows}
        return self._memo[key]

    # ---- enums from Valve protobufs ----------------------------------------

    def enums(self) -> dict[str, dict[str, str]]:
        build = self.live_build()
        return self.client.cached(
            "proto:enums",
            lambda: parse_enums(self.client.get_text(PROTO_URL)),
            ttl=TTL_ASSETS,
            patch_version=build,
            min_patch=build,
        )

    def objective_label(self, objective_id: int) -> dict:
        """Name + kind + lane number for an ECitadelTeamObjective value."""
        short = self.enums().get("ECitadelTeamObjective", {}).get(str(objective_id), f"Objective{objective_id}")
        parts = objective_parts(short)
        return {"id": objective_id, "enum": short, **parts, "name": self._objective_display(parts["kind"])}

    def _objective_display(self, kind: str) -> str:
        # Names come from NPC unit data where it has them (Guardian, Walker, Base Guardian).
        npc_class = {"tier1": "npc_boss_tier1", "tier2": "npc_boss_tier2", "barracks": "npc_barrack_boss"}.get(kind)
        if npc_class:
            for u in self.npc_units():
                if u.get("class_name") == npc_class and u.get("name"):
                    return u["name"]
        # generic-data objective_params names these "shrines" and "patron".
        return {"shrine": "Shrine", "titan": "Patron", "core": "Patron core"}.get(kind, kind.title())

    # ---- players and matches -------------------------------------------------

    def match_history(self, account_id: int, force: bool = False) -> list[dict]:
        return self.client.get_json(
            f"/v1/players/{account_id}/match-history", ttl=TTL_HISTORY, force=force
        )

    def match_metadata(self, match_id: int) -> dict:
        # Finished matches never change: cache forever.
        return self.client.get_json(f"/v1/matches/{match_id}/metadata", ttl=None)

    def salts(self, match_id: int) -> dict:
        return self.client.get_json(f"/v1/matches/{match_id}/salts", ttl=TTL_SALTS)

    def player_rank(self, account_id: int) -> dict:
        return self.client.get_json(f"/v1/players/{account_id}/rank", ttl=TTL_RANK)

    def steam_search(self, query: str) -> list[dict]:
        return self.client.get_json(
            "/v1/players/steam-search", {"search_query": query, "limit": 10}, ttl=DAY
        )

    def steam_profiles(self, account_ids: list[int]) -> list[dict]:
        return self.client.get_json("/v1/players/steam", {"account_ids": account_ids}, ttl=DAY)

    # ---- benchmarks (hero + rank bracket) -----------------------------------

    def _bench(self, path: str, params: dict) -> Any:
        return self.client.get_json(path, params, ttl=TTL_BENCH, patch_version=self.live_build())

    @staticmethod
    def _bracket(bracket: tuple[int, int]) -> dict:
        return {"min_average_badge": bracket[0], "max_average_badge": bracket[1]}

    def hero_metrics(self, hero_id: int, bracket: tuple[int, int]) -> dict:
        return self._bench("/v1/analytics/player-stats/metrics", {"hero_ids": hero_id, **self._bracket(bracket)})

    def perf_curve(self, hero_id: int, bracket: tuple[int, int]) -> list[dict]:
        return self._bench(
            "/v1/analytics/player-performance-curve",
            {"hero_ids": hero_id, "resolution": 0, **self._bracket(bracket)},
        )

    def item_stats(self, hero_id: int, bracket: tuple[int, int]) -> list[dict]:
        return self._bench(
            "/v1/analytics/item-stats", {"hero_id": hero_id, "min_matches": 20, **self._bracket(bracket)}
        )

    def hero_stats(self, bracket: tuple[int, int]) -> list[dict]:
        return self._bench("/v1/analytics/hero-stats", self._bracket(bracket))
