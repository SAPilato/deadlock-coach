"""HTTP client for deadlock-api.com: throttling, retry with backoff, SQLite cache.

Rate limits (from the API docs): analytics endpoints share 200 req/min per IP, so
that group is throttled to 3 req/s. On 429/5xx we back off exponentially with
jitter and honour Retry-After. If the network fails and an expired cache row
exists, the stale row is served instead of failing.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from typing import Any, Callable

import httpx

from app.config import API_BASE
from app.gamedata.cache import Cache

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class NotFound(ApiError):
    pass


class Offline(ApiError):
    pass


class RateLimiter:
    """Token bucket. `rate` tokens per second, bursts up to `capacity`."""

    def __init__(self, rate: float, capacity: float, clock=time.monotonic, sleep=time.sleep):
        self.rate, self.capacity = rate, capacity
        self.tokens = capacity
        self.clock, self.sleep = clock, sleep
        self.updated = clock()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = self.clock()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens < 1:
                wait = (1 - self.tokens) / self.rate
                self.sleep(wait)
                self.tokens = 1
                self.updated = self.clock()
            self.tokens -= 1


def cache_key(path_or_url: str, params: dict | None) -> str:
    if not params:
        return path_or_url
    parts = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return f"{path_or_url}?{parts}"


def clean_params(params: dict | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (params or {}).items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            v = ",".join(str(x) for x in v)
        elif isinstance(v, bool):
            v = "true" if v else "false"
        out[k] = str(v)
    return out


class ApiClient:
    def __init__(
        self,
        cache: Cache,
        base_url: str = API_BASE,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 5,
        offline: bool = False,
    ):
        self.cache = cache
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.Client(
            timeout=httpx.Timeout(45.0, connect=10.0),
            headers={"User-Agent": "deadlock-coach/0.1 (personal, local)"},
            follow_redirects=True,
        )
        self.sleep = sleep
        self.max_retries = max_retries
        self.offline = offline
        self.limiters = {
            "analytics": RateLimiter(rate=3.0, capacity=5, sleep=sleep),
            "default": RateLimiter(rate=20.0, capacity=20, sleep=sleep),
        }

    # ---- public -------------------------------------------------------------

    def get_json(
        self,
        path: str,
        params: dict | None = None,
        *,
        ttl: float | None,
        patch_version: int | None = None,
        min_patch: int | None = None,
        force: bool = False,
    ) -> Any:
        """GET a JSON endpoint through the cache. `ttl=None` caches forever."""
        p = clean_params(params)
        url = path if path.startswith("http") else self.base_url + path
        return self.cached(
            cache_key(path, p),
            lambda: self._request(url, p).json(),
            ttl=ttl,
            patch_version=patch_version,
            min_patch=min_patch,
            force=force,
        )

    def get_text(self, url: str) -> str:
        return self._request(url, {}).text

    def cached(
        self,
        key: str,
        producer: Callable[[], Any],
        *,
        ttl: float | None,
        patch_version: int | None = None,
        min_patch: int | None = None,
        force: bool = False,
    ) -> Any:
        entry = self.cache.get(key)
        if entry and not force and entry.is_fresh(self.cache.clock(), min_patch):
            return entry.payload
        try:
            payload = producer()
        except NotFound:
            raise
        except ApiError as e:
            if entry is not None:
                log.warning("Serving stale cache for %s (%s)", key, e)
                return entry.payload
            raise
        self.cache.set(key, payload, ttl=ttl, patch_version=patch_version)
        return payload

    # ---- internals ----------------------------------------------------------

    def _group(self, url: str) -> str:
        return "analytics" if "/v1/analytics/" in url else "default"

    def _request(self, url: str, params: dict[str, str]) -> httpx.Response:
        if self.offline:
            raise Offline("Offline mode: no network calls")
        limiter = self.limiters[self._group(url)]
        last_error: str = ""
        for attempt in range(self.max_retries + 1):
            limiter.acquire()
            try:
                resp = self.http.get(url, params=params)
            except httpx.TransportError as e:
                last_error = f"network error: {e}"
                retry_after = None
            else:
                if resp.status_code == 404:
                    raise NotFound(f"Not found: {url}", 404)
                if resp.status_code < 400:
                    return resp
                if resp.status_code not in RETRY_STATUSES:
                    raise ApiError(f"HTTP {resp.status_code} for {url}: {resp.text[:200]}", resp.status_code)
                last_error = f"HTTP {resp.status_code}"
                retry_after = _retry_after_seconds(resp)
            if attempt == self.max_retries:
                break
            delay = min(30.0, 2.0**attempt) + random.uniform(0, 0.5)
            if retry_after is not None:
                delay = min(60.0, max(delay, retry_after))
            log.info("Retry %s in %.1fs (%s)", url, delay, last_error)
            self.sleep(delay)
        raise ApiError(f"Gave up on {url} after {self.max_retries + 1} tries: {last_error}")


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
