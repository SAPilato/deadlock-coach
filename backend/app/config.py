"""App-wide paths and constants. User settings live in the database (see settings.py)."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("COACH_DATA_DIR", REPO_ROOT / "data"))
DB_PATH = DATA_DIR / "coach.db"
DEMO_DIR = DATA_DIR / "demos"

API_BASE = os.environ.get("COACH_API_BASE", "https://api.deadlock-api.com")
PROTO_URL = (
    "https://raw.githubusercontent.com/SteamDatabase/Protobufs/master/"
    "deadlock/citadel_gcmessages_common.proto"
)

# Badge = tier * 10 + subrank. Ritualist 1 (61) .. Emissary 6 (76). Editable in Settings.
DEFAULT_BRACKET = (61, 76)

# Bump when findings logic changes; cached analyses with an older version are recomputed.
ENGINE_VERSION = 1

# Offline mode: never hit the network, serve cache and seed data only.
OFFLINE = os.environ.get("COACH_OFFLINE") == "1"
