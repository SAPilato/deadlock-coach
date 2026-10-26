"""Map geometry built only from /v1/assets/map and /v1/assets/generic-data.

- World -> minimap transform is fitted from map entities, which carry both
  world positions and relative minimap positions.
- Lanes: zipline splines matched to lane_info by their exact color.
- Objective lane numbers (Lane1..4 in Valve's enum, `tier1_N` in map keys) are
  linked to lanes by the nearest zipline to that lane's Guardian.
- "Enemy progress" measures how far a point is from your core toward theirs (0..1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Source engine convention, 1 unit = 1 inch. Not confirmed for Deadlock: shown as "est.".
METERS_PER_UNIT = 0.0254


@dataclass
class Axis:
    a: float
    b: float

    def fwd(self, v: float) -> float:
        return self.a * v + self.b

    def inv(self, r: float) -> float:
        return (r - self.b) / self.a


def _fit(ws: list[float], rs: list[float]) -> Axis:
    n = len(ws)
    mw, mr = sum(ws) / n, sum(rs) / n
    var = sum((w - mw) ** 2 for w in ws)
    a = sum((w - mw) * (r - mr) for w, r in zip(ws, rs)) / var
    return Axis(a, mr - a * mw)


def _hex(color: str) -> str:
    return color.lstrip("#").lower()


def _rgb_hex(c: dict | None) -> str | None:
    if not c:
        return None
    return f"{c['red']:02x}{c['green']:02x}{c['blue']:02x}"


def _seg_dist(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


@dataclass
class Lane:
    id: int  # the `assigned_lane` value used in match data
    name: str
    color: str  # hex, from lane_info
    points: list[tuple[float, float]]

    def dist(self, x: float, y: float) -> float:
        pts = self.points
        return min(_seg_dist((x, y), pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    @property
    def cumulative(self) -> list[float]:
        if not hasattr(self, "_cum"):
            cum = [0.0]
            for a, b in zip(self.points, self.points[1:]):
                cum.append(cum[-1] + math.dist(a, b))
            self._cum = cum
        return self._cum

    @property
    def length(self) -> float:
        return self.cumulative[-1]

    def project(self, x: float, y: float) -> tuple[float, float]:
        """(distance along the lane from points[0], distance from the lane)."""
        best = (0.0, float("inf"))
        cum = self.cumulative
        for i, (a, b) in enumerate(zip(self.points, self.points[1:])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L))
            px, py = a[0] + t * dx, a[1] + t * dy
            d = math.hypot(x - px, y - py)
            if d < best[1]:
                best = (cum[i] + t * math.sqrt(L), d)
        return best

    def point_at(self, s: float) -> tuple[float, float]:
        cum = self.cumulative
        s = max(0.0, min(s, cum[-1]))
        for i in range(len(cum) - 1):
            if cum[i + 1] >= s:
                seg = cum[i + 1] - cum[i]
                t = 0.0 if seg == 0 else (s - cum[i]) / seg
                (ax, ay), (bx, by) = self.points[i], self.points[i + 1]
                return ax + t * (bx - ax), ay + t * (by - ay)
        return self.points[-1]


class MapGeometry:
    def __init__(self, map_data: dict, generic_data: dict):
        self.radius = map_data.get("radius")
        self.images = map_data.get("images", {})
        samples = []
        for group in (map_data.get("entities") or {}).values():
            samples += [e for e in group if "position" in e and "left_relative" in e]
        samples += [c for c in map_data.get("neutral_camps", []) if "left_relative" in c]
        self.ax = _fit([s["position"][0] for s in samples], [s["left_relative"] for s in samples])
        self.ay = _fit([s["position"][1] for s in samples], [s["top_relative"] for s in samples])
        self.fit_error = max(
            max(abs(self.ax.fwd(s["position"][0]) - s["left_relative"]),
                abs(self.ay.fwd(s["position"][1]) - s["top_relative"]))
            for s in samples
        )

        self.objectives = {
            k: self.to_world(v["left_relative"], v["top_relative"])
            for k, v in map_data.get("objective_positions", {}).items()
        }

        lane_info = generic_data.get("lane_info", [])
        by_color = {_rgb_hex(l.get("color")): (i, l) for i, l in enumerate(lane_info) if l.get("color")}
        self.lanes: dict[int, Lane] = {}
        for z in map_data.get("zipline_paths", []):
            match = by_color.get(_hex(z["color"]))
            if not match:
                continue
            idx, info = match
            ox, oy = z["origin"][0], z["origin"][1]
            pts = [(ox + p[0], oy + p[1]) for p in z["P0_points"]]
            self.lanes[idx] = Lane(idx, info["lane_name"], "#" + _hex(z["color"]), pts)

        self.cores = {t: self.objectives.get(f"team{t}_core") for t in (0, 1)}
        # Orient every lane from team 0's end to team 1's end, so "progress" means the same everywhere.
        for lane in self.lanes.values():
            c0 = self.cores.get(0)
            if c0 and math.dist(lane.points[-1], c0) < math.dist(lane.points[0], c0):
                lane.points = lane.points[::-1]

        # Objective lane number N -> lane id, via the zipline closest to team0's Guardian N.
        self.objective_lane: dict[int, int] = {}
        for key, (x, y) in self.objectives.items():
            if key.startswith("team0_tier1_") and self.lanes:
                n = int(key.rsplit("_", 1)[1])
                self.objective_lane[n] = min(self.lanes.values(), key=lambda L: L.dist(x, y)).id

    # ---- transforms ----------------------------------------------------------

    def to_rel(self, x: float, y: float) -> tuple[float, float]:
        return self.ax.fwd(x), self.ay.fwd(y)

    def to_world(self, left: float, top: float) -> tuple[float, float]:
        return self.ax.inv(left), self.ay.inv(top)

    # ---- queries -------------------------------------------------------------

    def enemy_progress(self, team: int, x: float, y: float) -> float:
        """0 at your core, 1 at the enemy core, projected on the line between them."""
        own, enemy = self.cores.get(team), self.cores.get(1 - team)
        if not own or not enemy:
            return 0.5
        dx, dy = enemy[0] - own[0], enemy[1] - own[1]
        return ((x - own[0]) * dx + (y - own[1]) * dy) / (dx * dx + dy * dy)

    def nearest_lane(self, x: float, y: float) -> Lane | None:
        if not self.lanes:
            return None
        return min(self.lanes.values(), key=lambda L: L.dist(x, y))

    def objective_pos(self, owner_team: int, kind: str, lane_num: int | None) -> tuple[float, float] | None:
        if kind in ("tier1", "tier2") and lane_num is not None:
            return self.objectives.get(f"team{owner_team}_{kind}_{lane_num}")
        if kind in ("titan", "core"):
            return self.objectives.get(f"team{owner_team}_{kind}")
        return None

    def describe(self, team: int, x: float, y: float) -> str:
        lane = self.nearest_lane(x, y)
        p = self.enemy_progress(team, x, y)
        side = "enemy base" if p > 0.85 else "enemy side" if p > 0.55 else "mid" if p > 0.45 else "your side" if p > 0.15 else "your base"
        return f"{lane.name}, {side}" if lane else side

    @staticmethod
    def meters(units: float) -> int:
        return int(round(units * METERS_PER_UNIT))
