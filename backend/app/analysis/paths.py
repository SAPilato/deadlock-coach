"""Decode `match_paths` from match metadata: one sample per second for every player.

Positions are quantized to 0..x_resolution inside each player's own bounding box:
    world_x = x_min + x_pos / x_resolution * (x_max - x_min)
Sample index i is game second i (checked against death positions in tests).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass
class Track:
    slot: int
    x: list[float]
    y: list[float]
    health: list[int]
    combat: list[int]
    move: list[int]
    interval: float = 1.0

    def __len__(self) -> int:
        return len(self.x)

    def index(self, t: float) -> int:
        return max(0, min(len(self.x) - 1, int(round(t / self.interval))))

    def at(self, t: float) -> tuple[float, float]:
        i = self.index(t)
        return self.x[i], self.y[i]

    def speed(self, t: float, window: int = 2) -> float:
        """Average ground speed (units/s) around second t."""
        i0, i1 = self.index(t - window), self.index(t + window)
        if i1 <= i0:
            return 0.0
        return math.dist((self.x[i0], self.y[i0]), (self.x[i1], self.y[i1])) / ((i1 - i0) * self.interval)


class _Lane(Protocol):
    id: int

    def dist(self, x: float, y: float) -> float: ...


@dataclass
class Ride:
    start: int  # first second on the zipline
    end: int  # first second off it
    lane_id: int  # the lane whose zipline it was (nearest at mid-ride)


def zipline_rides(track: Track, zip_id: int | None, lanes: Iterable[_Lane]) -> list[Ride]:
    """Each stretch of seconds the player spent ziplining, tagged with the nearest lane zipline."""
    lanes = list(lanes)
    if zip_id is None or not track.move or not lanes:
        return []
    rides: list[Ride] = []
    start = None
    for t, m in enumerate([*track.move, -1]):  # sentinel closes a ride at the end
        if m == zip_id and start is None:
            start = t
        elif m != zip_id and start is not None:
            mid = (start + t - 1) // 2
            x, y = track.x[mid], track.y[mid]
            rides.append(Ride(start, t, min(lanes, key=lambda ln: ln.dist(x, y)).id))
            start = None
    return rides


def decode_paths(match_paths: dict | None) -> dict[int, Track]:
    if not match_paths:
        return {}
    xr = match_paths.get("x_resolution") or 16383
    yr = match_paths.get("y_resolution") or 16383
    interval = match_paths.get("interval_s") or 1.0
    tracks: dict[int, Track] = {}
    for p in match_paths.get("paths", []):
        sx = (p["x_max"] - p["x_min"]) / xr
        sy = (p["y_max"] - p["y_min"]) / yr
        tracks[p["player_slot"]] = Track(
            slot=p["player_slot"],
            x=[p["x_min"] + v * sx for v in p["x_pos"]],
            y=[p["y_min"] + v * sy for v in p["y_pos"]],
            health=list(p.get("health") or []),
            combat=list(p.get("combat_type") or []),
            move=list(p.get("move_type") or []),
            interval=interval,
        )
    return tracks
