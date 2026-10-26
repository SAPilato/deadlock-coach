"""Bundle a parsed replay with the seed: python -m app.seed.replay <match_id> <path/to/match.dem>

Stores only the small parsed results (urn episodes, trooper waves, live-map
truth), never the demo.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.analysis.geometry import MapGeometry
from app.config import DB_PATH
from app.macro.truth import save_truth
from app.macro.waves import save_waves
from app.replay.jobs import RESULT_NAME, SEED_REPLAYS, TRUTH_NAME, WAVES_NAME
from app.replay.parser import parse_demo
from app.state import create_state


def build(match_id: int, dem: Path) -> None:
    st = create_state(DB_PATH)
    geo = MapGeometry(st.gd.map_data(), st.gd.generic_data())  # waves only need lanes, not truth
    start = st.gd.match_metadata(match_id)["match_info"].get("start_time")
    data, waves, truth = parse_demo(dem, match_id, geo, start)
    out = SEED_REPLAYS / str(match_id)
    data.save(out / RESULT_NAME)
    save_waves(waves or {"frames": []}, out / WAVES_NAME)
    save_truth(truth, out / TRUTH_NAME)
    print(
        f"Seeded replay {match_id}: {len(data.urn_events)} urns, {len((waves or {}).get('frames', []))} wave frames, "
        f"{len(truth['objectives'])} objectives, {len(truth['urn_sites'])} urn sites"
    )


if __name__ == "__main__":
    build(int(sys.argv[1]), Path(sys.argv[2]))
