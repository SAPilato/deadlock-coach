"""Rebuild the seed bundle from the live API. Run with: npm run seed

Picks the newest matches of SAMPLE_ACCOUNT (a public Ritualist-rank player at
seeding time), then records every API response the app needs to show them:
game data, enums, match metadata and hero/rank benchmarks.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

from app.config import DEFAULT_BRACKET
from app.gamedata.client import ApiError
from app.state import create_state

SAMPLE_ACCOUNT = 254935688
N_MATCHES = 3
OUT = Path(__file__).parent / "data"


def build(account_id: int = SAMPLE_ACCOUNT, n_matches: int = N_MATCHES) -> None:
    st = create_state(":memory:", offline=False)
    gd = st.gd
    build_no = gd.live_build()
    gd.latest_patch()
    for loader in (gd.heroes, gd.items, gd.ranks, gd.generic_data, gd.map_data, gd.npc_units, gd.enums):
        loader()

    history = gd.match_history(account_id)
    gd.player_rank(account_id)
    gd.hero_stats(DEFAULT_BRACKET)

    picked: list[int] = []
    for m in history:
        if len(picked) == n_matches:
            break
        if m.get("game_mode") != 1:  # 1 = normal mode (not Street Brawl)
            continue
        try:
            gd.match_metadata(m["match_id"])
        except ApiError as e:
            print(f"skip {m['match_id']}: {e}", file=sys.stderr)
            continue
        picked.append(m["match_id"])
        for fetch in (gd.hero_metrics, gd.perf_curve, gd.item_stats):
            fetch(m["hero_id"], DEFAULT_BRACKET)

    rows = st.db.all("SELECT key, payload, patch_version FROM cache")
    bundle = {r["key"]: {"payload": json.loads(r["payload"]), "patch_version": r["patch_version"]} for r in rows}
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "cache.json.gz", "wt", encoding="utf-8") as f:
        json.dump(bundle, f, separators=(",", ":"))
    meta = {"account_id": account_id, "match_ids": picked, "build": build_no, "built_at": int(time.time())}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    size = (OUT / "cache.json.gz").stat().st_size / 1e6
    print(f"Seeded {len(bundle)} responses, matches {picked}, build {build_no}, {size:.1f} MB")


if __name__ == "__main__":
    build()
