import httpx
import pytest
import respx

from app.gamedata.client import ApiClient, ApiError, NotFound

BASE = "https://api.test"


def make_client(cache, sleeps):
    return ApiClient(cache, base_url=BASE, http=httpx.Client(), sleep=sleeps.append, max_retries=3)


@respx.mock
def test_retries_on_429_and_honours_retry_after(cache):
    sleeps: list[float] = []
    route = respx.get(f"{BASE}/v1/x").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    client = make_client(cache, sleeps)
    assert client.get_json("/v1/x", ttl=60) == {"ok": True}
    assert route.call_count == 2
    assert any(s >= 7 for s in sleeps)


@respx.mock
def test_gives_up_after_max_retries(cache):
    sleeps: list[float] = []
    respx.get(f"{BASE}/v1/x").mock(return_value=httpx.Response(503))
    client = make_client(cache, sleeps)
    with pytest.raises(ApiError):
        client.get_json("/v1/x", ttl=60)
    backoffs = [s for s in sleeps if s >= 1]
    assert len(backoffs) == 3
    assert backoffs == sorted(backoffs)  # exponential


@respx.mock
def test_404_is_not_retried(cache):
    sleeps: list[float] = []
    route = respx.get(f"{BASE}/v1/missing").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFound):
        make_client(cache, sleeps).get_json("/v1/missing", ttl=60)
    assert route.call_count == 1


@respx.mock
def test_serves_cache_until_ttl_expires(cache, clock):
    route = respx.get(f"{BASE}/v1/x").mock(
        side_effect=[httpx.Response(200, json=[1]), httpx.Response(200, json=[2])]
    )
    client = make_client(cache, [])
    assert client.get_json("/v1/x", ttl=100) == [1]
    clock.t += 50
    assert client.get_json("/v1/x", ttl=100) == [1]
    clock.t += 60
    assert client.get_json("/v1/x", ttl=100) == [2]
    assert route.call_count == 2


@respx.mock
def test_refetches_when_live_patch_is_newer(cache):
    respx.get(f"{BASE}/v1/assets/items").mock(
        side_effect=[httpx.Response(200, json=["old"]), httpx.Response(200, json=["new"])]
    )
    client = make_client(cache, [])
    assert client.get_json("/v1/assets/items", ttl=None, patch_version=6800, min_patch=6800) == ["old"]
    assert client.get_json("/v1/assets/items", ttl=None, patch_version=6800, min_patch=6800) == ["old"]
    assert client.get_json("/v1/assets/items", ttl=None, patch_version=6819, min_patch=6819) == ["new"]
    assert cache.get("/v1/assets/items").patch_version == 6819


@respx.mock
def test_stale_cache_served_when_network_fails(cache, clock):
    respx.get(f"{BASE}/v1/x").mock(
        side_effect=[httpx.Response(200, json={"v": 1}), httpx.ConnectError("down")] + [httpx.ConnectError("down")] * 5
    )
    client = make_client(cache, [])
    client.get_json("/v1/x", ttl=10)
    clock.t += 100
    assert client.get_json("/v1/x", ttl=10) == {"v": 1}


@respx.mock
def test_list_params_are_comma_joined(cache):
    route = respx.get(f"{BASE}/v1/y").mock(return_value=httpx.Response(200, json=[]))
    make_client(cache, []).get_json("/v1/y", {"ids": [1, 2], "skip": None, "flag": True}, ttl=1)
    q = dict(route.calls.last.request.url.params)
    assert q == {"ids": "1,2", "flag": "true"}
