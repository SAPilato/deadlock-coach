"""Turn any common Steam ID format into the 32-bit account id (SteamID3) the API uses."""
from __future__ import annotations

import re

STEAM64_BASE = 76561197960265728


def parse_account_id(raw: str | int) -> int | None:
    s = str(raw).strip()
    if not s:
        return None
    m = re.search(r"/profiles/(\d{17})", s)
    if m:
        s = m.group(1)
    m = re.fullmatch(r"\[?U:1:(\d+)\]?", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"STEAM_[0-5]:([01]):(\d+)", s)
    if m:
        return int(m.group(2)) * 2 + int(m.group(1))
    if s.isdigit():
        n = int(s)
        if n >= STEAM64_BASE:
            return n - STEAM64_BASE
        if 0 < n < 2**32:
            return n
    return None
