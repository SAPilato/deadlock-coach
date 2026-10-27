"""App password for sharing through a tunnel: hashing, sessions, lockout, the API gate."""
import pytest
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app.auth import COOKIE, MAX_FAILS, Auth, Locked, hash_password, verify_password
from app.db import Database
from app.main import create_app
from app.state import create_state

PASSWORD = "correct horse battery"


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_password_hash_round_trip_and_rules():
    stored = hash_password(PASSWORD)
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert verify_password(PASSWORD, stored) and not verify_password("nope", stored)
    assert not verify_password(PASSWORD, "garbage")
    with pytest.raises(ValueError):
        Auth(Database(":memory:")).set_password("short")


def test_sessions_expire_resist_tampering_and_end_on_new_password():
    clock = Clock()
    a = Auth(Database(":memory:"), clock=clock)
    assert a.login(PASSWORD) is None  # no password set yet
    a.set_password(PASSWORD)
    token = a.login(PASSWORD)
    assert a.valid(token)
    assert not a.valid(token[:-1] + ("0" if token[-1] != "0" else "1"))
    assert not a.valid(None) and not a.valid("1.2") and not a.valid("")
    clock.t += auth_mod.SESSION_DAYS * 86400 + 1
    assert not a.valid(token)
    fresh = a.login(PASSWORD)
    a.set_password("another good password")
    assert not a.valid(fresh)  # every device logs in again


def test_too_many_wrong_passwords_lock_logins():
    clock = Clock()
    a = Auth(Database(":memory:"), clock=clock)
    a.set_password(PASSWORD)
    for _ in range(MAX_FAILS):
        assert a.login("wrong") is None
    with pytest.raises(Locked):
        a.login(PASSWORD)  # even the right one, while locked
    clock.t += auth_mod.LOCK_S + 1
    assert a.valid(a.login(PASSWORD))


def _app(require_login: bool, password: str | None = PASSWORD):
    def factory():
        st = create_state(":memory:", offline=True)
        if password:
            Auth(st.db).set_password(password)
        return st

    return create_app(factory, require_login=require_login)


def test_shared_app_needs_login_for_the_api():
    with TestClient(_app(require_login=True)) as c:
        assert c.get("/api/auth/status").json() == {"required": True, "logged_in": False}
        assert c.get("/api/meta").status_code == 401
        # No API description: no docs page, no schema (a 404 or the built site may answer instead).
        assert "swagger" not in c.get("/docs").text.lower()
        assert '"openapi"' not in c.get("/openapi.json").text
        assert c.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
        r = c.post("/api/auth/login", json={"password": PASSWORD})
        assert r.status_code == 200 and COOKIE in r.cookies
        assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
        assert c.get("/api/auth/status").json()["logged_in"] is True
        assert c.get("/api/meta").status_code == 200
        c.post("/api/auth/logout")
        assert c.get("/api/meta").status_code == 401


def test_cookie_is_secure_behind_an_https_tunnel():
    with TestClient(_app(require_login=True)) as c:
        r = c.post("/api/auth/login", json={"password": PASSWORD}, headers={"x-forwarded-proto": "https"})
        assert "secure" in r.headers["set-cookie"].lower()


def test_local_app_stays_open_and_shared_app_needs_a_password():
    with TestClient(_app(require_login=False, password=None)) as c:
        assert c.get("/api/meta").status_code == 200
        assert c.get("/api/auth/status").json()["required"] is False
    with pytest.raises(RuntimeError, match="set-password"):
        with TestClient(_app(require_login=True, password=None)):
            pass


def test_cloud_password_hash_from_environment(monkeypatch):
    a = Auth(Database(":memory:"))
    assert not a.has_password
    monkeypatch.setenv(auth_mod.ENV_HASH, hash_password(PASSWORD))
    assert a.has_password
    token = a.login(PASSWORD)
    assert a.valid(token) and a.login("wrong") is None
    monkeypatch.setenv(auth_mod.ENV_HASH, hash_password("a brand new password"))
    assert not a.valid(token)  # a new hash logs every device out
