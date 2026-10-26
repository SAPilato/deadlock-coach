"""Item slot limit, measured from real matches instead of assumed.

The hero data's `item_slot_info` is ambiguous, so we replay purchases and sales
in cached match metadata and find the most upgrades held at once. The limit is
the highest peak that several players reach, which ignores one-off glitches
(e.g. a sale and a purchase logged in the wrong order).
"""
from __future__ import annotations

import json
from collections import Counter

from app.state import AppState

FALLBACK = 12  # used only when too few matches are cached; shown as est.
MIN_PLAYERS = 30
MIN_REACHING = 3  # a peak counts as the cap only if this many players reach it
MAX_MATCHES = 15

_memo: dict | None = None


def peak_owned(player: dict, item_map: dict[int, dict]) -> int:
    events = []
    for it in player.get("items") or []:
        if item_map.get(it["item_id"], {}).get("type") != "upgrade":
            continue
        events.append((it["game_time_s"], 1))
        if it.get("sold_time_s"):
            events.append((it["sold_time_s"], -1))
    events.sort()  # at equal times sales (-1) come before buys (+1)
    held = peak = 0
    for _, d in events:
        held += d
        peak = max(peak, held)
    return peak


def slot_limit(st: AppState) -> dict:
    global _memo
    if _memo is not None:
        return _memo
    item_map = st.gd.item_map()
    rows = st.db.all(
        "SELECT payload FROM cache WHERE key LIKE '/v1/matches/%/metadata' LIMIT ?", (MAX_MATCHES,)
    )
    peaks = Counter()
    for r in rows:
        info = json.loads(r["payload"]).get("match_info", {})
        if info.get("game_mode") != 1:
            continue
        for p in info.get("players", []):
            peaks[peak_owned(p, item_map)] += 1
    players = sum(peaks.values())
    reached = [v for v, n in peaks.items() if n >= MIN_REACHING]
    if players < MIN_PLAYERS or not reached:
        result = {"limit": FALLBACK, "est": True, "players": players}
    else:
        result = {"limit": max(reached), "est": False, "players": players}
    _memo = result
    return result
