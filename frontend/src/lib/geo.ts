// Minimap geometry helpers. Positions are relative (0..1); the backend's fitted
// transform is linear: left = ax * x + bx, top = ay * y + by.

export type Pt = [number, number];

export interface Transform {
  ax: number;
  bx: number;
  ay: number;
  by: number;
}

function cumulative(pts: Pt[]): number[] {
  const out = [0];
  for (let i = 1; i < pts.length; i++) {
    out.push(out[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  }
  return out;
}

/** Point at fraction `s` (0..1) of a polyline's length. */
export function pointAt(pts: Pt[], s: number): Pt {
  const cum = cumulative(pts);
  const target = Math.max(0, Math.min(1, s)) * cum[cum.length - 1];
  for (let i = 1; i < cum.length; i++) {
    if (cum[i] >= target) {
      const seg = cum[i] - cum[i - 1];
      const t = seg === 0 ? 0 : (target - cum[i - 1]) / seg;
      return [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])];
    }
  }
  return pts[pts.length - 1];
}

/** World distance in game units between two relative points. */
export function worldUnits(a: Pt, b: Pt, tf: Transform): number {
  return Math.hypot((b[0] - a[0]) / tf.ax, (b[1] - a[1]) / tf.ay);
}

/** Total route length in meters (est.: 1 unit = 0.0254 m, the Source convention). */
export function routeMeters(route: Pt[], tf: Transform, metersPerUnit: number): number {
  let total = 0;
  for (let i = 1; i < route.length; i++) total += worldUnits(route[i - 1], route[i], tf);
  return total * metersPerUnit;
}
