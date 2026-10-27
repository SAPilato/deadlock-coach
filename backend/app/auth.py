"""Password login, for sharing the app through a public tunnel (`npm run share`).

It is a personal app, so there is one password for the whole app. Only a scrypt hash of
it is stored (settings table); it is set on this PC with `npm run set-password`, never
over the network. Logging in sets a signed cookie that lasts SESSION_DAYS. Setting a
new password changes the signing secret, which logs every device out.

Too many wrong passwords lock logins for a while (MAX_FAILS in FAIL_WINDOW_S locks for
LOCK_S), counted for the whole app: behind a tunnel every request comes from this PC,
so a per-address count would not mean anything.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

from app.db import Database

COOKIE = "coach_session"
SESSION_DAYS = 30
MAX_FAILS = 10
FAIL_WINDOW_S = 600
LOCK_S = 600
MIN_LENGTH = 8

_HASH_KEY = "auth_password_hash"
_SECRET_KEY = "auth_secret"
_SCRYPT = {"n": 2**15, "r": 8, "p": 1, "maxmem": 64 * 1024 * 1024}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        kind, salt, digest = stored.split("$")
    except ValueError:
        return False
    if kind != "scrypt":
        return False
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(candidate.hex(), digest)


class Locked(Exception):
    def __init__(self, seconds: int):
        super().__init__(f"Too many wrong passwords. Try again in {seconds // 60 + 1} min.")
        self.seconds = seconds


class Auth:
    def __init__(self, db: Database, clock=time.time):
        self.db = db
        self.clock = clock
        self._fails: list[float] = []
        self._locked_until = 0.0
        self._lock = threading.Lock()

    def _get(self, key: str) -> str | None:
        return self.db.scalar("SELECT value FROM settings WHERE key = ?", (key,))

    def _set(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    @property
    def has_password(self) -> bool:
        return self._get(_HASH_KEY) is not None

    def set_password(self, password: str) -> None:
        if len(password) < MIN_LENGTH:
            raise ValueError(f"Use at least {MIN_LENGTH} characters.")
        self._set(_HASH_KEY, hash_password(password))
        self._set(_SECRET_KEY, secrets.token_hex(32))  # old cookies stop working

    def _sign(self, payload: str) -> str:
        secret = self._get(_SECRET_KEY) or ""
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def issue(self) -> str:
        expires = int(self.clock() + SESSION_DAYS * 86400)
        payload = f"{expires}.{secrets.token_hex(8)}"
        return f"{payload}.{self._sign(payload)}"

    def valid(self, token: str | None) -> bool:
        if not token or not self.has_password:
            return False
        payload, _, sig = token.rpartition(".")
        expires = payload.split(".", 1)[0]
        if not payload or not expires.isdigit() or int(expires) < self.clock():
            return False
        return hmac.compare_digest(sig, self._sign(payload))

    def login(self, password: str) -> str | None:
        """A session token, or None for a wrong password. Raises Locked after too many tries."""
        with self._lock:
            now = self.clock()
            if now < self._locked_until:
                raise Locked(int(self._locked_until - now))
            stored = self._get(_HASH_KEY)
            if stored and verify_password(password, stored):
                self._fails.clear()
                return self.issue()
            self._fails = [t for t in self._fails if now - t < FAIL_WINDOW_S] + [now]
            if len(self._fails) >= MAX_FAILS:
                self._locked_until = now + LOCK_S
                self._fails.clear()
            return None
