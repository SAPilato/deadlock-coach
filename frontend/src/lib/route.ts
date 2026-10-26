// On foot vs zipline. All speeds are real game units per second measured from
// match data (/api/macro/movement). Distances use the fitted minimap transform,
// so no unit-to-meter guess enters the times.
import { worldUnits, type Pt, type Transform } from "./geo";

export interface Lane {
  id: number;
  name: string;
  color: string;
  pts: Pt[];
}

export interface Speeds {
  foot: number; // units/s on foot
  zip: number; // units/s on a zipline
  detour: number; // real path length / straight line
  attach: number; // seconds to latch on and drop off
}

interface Projection {
  s: number; // world units along the lane from pts[0]
  point: Pt;
  dist: number; // world units from p to the lane
}

export function project(pts: Pt[], p: Pt, tf: Transform): Projection {
  let best: Projection = { s: 0, point: pts[0], dist: Infinity };
  let along = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1];
    const b = pts[i];
    // Work in world units so x and y weigh the same.
    const ax = a[0] / tf.ax, ay = a[1] / tf.ay, bx = b[0] / tf.ax, by = b[1] / tf.ay;
    const px = p[0] / tf.ax, py = p[1] / tf.ay;
    const dx = bx - ax, dy = by - ay;
    const L2 = dx * dx + dy * dy;
    const t = L2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L2));
    const qx = ax + t * dx, qy = ay + t * dy;
    const d = Math.hypot(px - qx, py - qy);
    if (d < best.dist) best = { s: along + t * Math.sqrt(L2), point: [qx * tf.ax, qy * tf.ay], dist: d };
    along += Math.sqrt(L2);
  }
  return best;
}

/** The lane polyline between two distances along it (either order). */
export function subpath(pts: Pt[], s0: number, s1: number, tf: Transform): Pt[] {
  const [lo, hi] = s0 <= s1 ? [s0, s1] : [s1, s0];
  const out: Pt[] = [];
  let along = 0;
  for (let i = 1; i < pts.length; i++) {
    const seg = worldUnits(pts[i - 1], pts[i], tf);
    const at = (s: number): Pt => {
      const t = seg === 0 ? 0 : (s - along) / seg;
      return [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])];
    };
    if (along + seg >= lo && along <= hi) {
      if (!out.length) out.push(at(Math.max(lo, along)));
      out.push(at(Math.min(hi, along + seg)));
    }
    along += seg;
  }
  return s0 <= s1 ? out : out.reverse();
}

export function footSeconds(a: Pt, b: Pt, tf: Transform, sp: Speeds): number {
  return (worldUnits(a, b, tf) * sp.detour) / sp.foot;
}

export interface ZipRoute {
  lane: Lane;
  entry: Pt;
  exit: Pt;
  walkIn: number;
  ride: number;
  walkOut: number;
  total: number;
  ridePath: Pt[];
}

/** Best zipline option: walk to a lane, ride it either way, walk off. */
export function zipRoute(a: Pt, b: Pt, lanes: Lane[], tf: Transform, sp: Speeds): ZipRoute | null {
  let best: ZipRoute | null = null;
  for (const lane of lanes) {
    const pa = project(lane.pts, a, tf);
    const pb = project(lane.pts, b, tf);
    const walkIn = (pa.dist * sp.detour) / sp.foot;
    const walkOut = (pb.dist * sp.detour) / sp.foot;
    const ride = Math.abs(pa.s - pb.s) / sp.zip;
    const total = walkIn + ride + walkOut + sp.attach;
    if (!best || total < best.total) {
      best = { lane, entry: pa.point, exit: pb.point, walkIn, ride, walkOut, total, ridePath: subpath(lane.pts, pa.s, pb.s, tf) };
    }
  }
  return best;
}

export interface Verdict {
  foot: number;
  zip: ZipRoute | null;
  faster: "foot" | "zip";
  saving: number; // seconds saved by the faster option
}

export function compare(a: Pt, b: Pt, lanes: Lane[], tf: Transform, sp: Speeds): Verdict {
  const foot = footSeconds(a, b, tf, sp);
  const zip = zipRoute(a, b, lanes, tf, sp);
  const faster = zip && zip.total < foot ? "zip" : "foot";
  return { foot, zip, faster, saving: zip ? Math.abs(foot - zip.total) : 0 };
}
