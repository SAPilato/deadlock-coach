"""Copy the seed bundle into the cache, without overwriting anything fetched live.

Seeded rows are stored already expired (except finished-match metadata, which
never changes), so when the network is up the app fetches fresh data, and when
it is down the stale-cache fallback serves the seed.
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

from app.gamedata.cache import Cache

DATA = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def seed_meta() -> dict | None:
    p = DATA / "meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@lru_cache(maxsize=1)
def seed_bundle() -> dict:
    path = DATA / "cache.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def load_seed(cache: Cache) -> int:
    added = 0
    for key, row in seed_bundle().items():
        if cache.get(key) is not None:
            continue
        immutable = key.startswith("/v1/matches/") and key.endswith("/metadata")
        cache.set(key, row["payload"], ttl=None if immutable else 0, patch_version=row["patch_version"])
        added += 1
    return added
