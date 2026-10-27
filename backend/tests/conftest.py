import pytest

import app.replay.jobs as jobs


@pytest.fixture(autouse=True, scope="session")
def _no_local_replays(tmp_path_factory):
    """Tests see only the bundled sample replay, never the replays parsed on this machine."""
    saved = jobs.DEMO_DIR
    jobs.DEMO_DIR = tmp_path_factory.mktemp("replays")
    yield
    jobs.DEMO_DIR = saved

from app.config import DEFAULT_BRACKET
from app.db import Database
from app.gamedata.cache import Cache
from app.gamedata.client import ApiClient
from app.gamedata.service import GameData
from app.seed.load import load_seed, seed_meta


class FakeClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def cache(clock):
    return Cache(Database(":memory:"), clock=clock)


@pytest.fixture(scope="session")
def seed_gd() -> GameData:
    """GameData over the bundled seed: real API responses, no network."""
    cache = Cache(Database(":memory:"))
    load_seed(cache)
    return GameData(ApiClient(cache, offline=True))


@pytest.fixture(scope="session")
def seed_info():
    return seed_meta()


@pytest.fixture(scope="session")
def seed_contexts(seed_gd, seed_info):
    from app.analysis.loader import load_context

    return [
        load_context(seed_gd, mid, seed_info["account_id"], DEFAULT_BRACKET) for mid in seed_info["match_ids"]
    ]
