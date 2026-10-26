import pytest

from app.db import Database
from app.gamedata.cache import Cache


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
