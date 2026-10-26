"""Get a match's .dem file: from Valve's replay servers (via the API's salts) or an upload.

Valve's replay URLs end in .dem.bz2, but the files are often zstd-compressed,
so the format is detected from the first bytes, not the file name.
"""
from __future__ import annotations

import bz2
import shutil
from pathlib import Path

import httpx

from app.gamedata.service import GameData

CHUNK = 1 << 20
BZ2_MAGIC = b"BZh"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


class ReplayUnavailable(Exception):
    pass


def download_demo(gd: GameData, match_id: int, dest_dir: Path) -> Path:
    salts = gd.salts(match_id)
    url = salts.get("demo_url")
    if not url:
        raise ReplayUnavailable("No replay link for this match. Upload the .dem file instead.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    packed = dest_dir / "match.download"
    with httpx.stream("GET", url, timeout=httpx.Timeout(120.0, connect=15.0), follow_redirects=True) as r:
        if r.status_code == 404:
            raise ReplayUnavailable("Valve no longer has this replay. Old replays expire.")
        r.raise_for_status()
        with packed.open("wb") as f:
            for chunk in r.iter_bytes(CHUNK):
                f.write(chunk)
    return unpack(packed)


def _zstd_open(path: Path):
    try:
        from compression import zstd  # Python 3.14+

        return zstd.open(path, "rb")
    except ImportError:
        import zstandard  # older Pythons: pip install zstandard

        return zstandard.ZstdDecompressor().stream_reader(path.open("rb"))


def unpack(path: Path) -> Path:
    """Decompress a bz2 or zstd file to match.dem next to it; plain demos pass through."""
    with path.open("rb") as f:
        head = f.read(4)
    if head.startswith(BZ2_MAGIC):
        opener = lambda: bz2.open(path, "rb")  # noqa: E731
    elif head == ZSTD_MAGIC:
        opener = lambda: _zstd_open(path)  # noqa: E731
    else:
        if path.name == "match.dem":
            return path
        out = path.with_name("match.dem")
        path.replace(out)
        return out
    out = path.with_name("match.dem")
    with opener() as src, out.open("wb") as dst:
        shutil.copyfileobj(src, dst, CHUNK)
    path.unlink()
    return out
