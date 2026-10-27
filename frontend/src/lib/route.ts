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

// ---- Routes over several ziplines ------------------------------------------------
// Players switch ziplines all the time (mostly in the base areas, ~2 s between rides;
// measured in /api/macro/movement). So the planner searches a graph: nodes every
// NODE_STEP units along each zipline, ride edges between neighbours (either way),
// and transfer edges (walk + latch on) between nodes on different ziplines.

const NODE_STEP = 300; // world units between graph nodes along a zipline
const TRANSFER_MAX = 5000; // world units: the longest walk between ziplines considered

interface GraphNode {
  lane: number; // index into graph.lanes
  s: number; // world units along that lane
  p: Pt;
}

interface Edge {
  to: number;
  d: number; // world units
  ride: boolean; // false = walk to another zipline and latch on
}

export interface ZipGraph {
  lanes: Lane[];
  nodes: GraphNode[];
  adj: Edge[][];
}

function pointAt(pts: Pt[], s: number, tf: Transform): Pt {
  let along = 0;
  for (let i = 1; i < pts.length; i++) {
    const seg = worldUnits(pts[i - 1], pts[i], tf);
    if (along + seg >= s || i === pts.length - 1) {
      const t = seg === 0 ? 0 : Math.min(1, (s - along) / seg);
      return [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])];
    }
    along += seg;
  }
  return pts[0];
}

export function buildGraph(lanes: Lane[], tf: Transform): ZipGraph {
  const nodes: GraphNode[] = [];
  const adj: Edge[][] = [];
  lanes.forEach((lane, li) => {
    let total = 0;
    for (let i = 1; i < lane.pts.length; i++) total += worldUnits(lane.pts[i - 1], lane.pts[i], tf);
    const n = Math.max(1, Math.ceil(total / NODE_STEP));
    for (let k = 0; k <= n; k++) {
      const s = (total * k) / n;
      const idx = nodes.push({ lane: li, s, p: pointAt(lane.pts, s, tf) }) - 1;
      adj.push([]);
      if (k > 0) {
        adj[idx - 1].push({ to: idx, d: total / n, ride: true });
        adj[idx].push({ to: idx - 1, d: total / n, ride: true });
      }
    }
  });
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (nodes[i].lane === nodes[j].lane) continue;
      const d = worldUnits(nodes[i].p, nodes[j].p, tf);
      if (d <= TRANSFER_MAX) {
        adj[i].push({ to: j, d, ride: false });
        adj[j].push({ to: i, d, ride: false });
      }
    }
  }
  return { lanes, nodes, adj };
}

/** Seconds from every graph node (riding) to `b`, with the next hop. Edges run both ways. */
export interface Field {
  b: Pt;
  time: Float64Array;
  next: Int32Array; // -1 = drop off here and walk to b
  nextRide: Uint8Array; // 1 if the hop to `next` is a ride, 0 if it is a transfer
  rides: Int32Array; // ziplines used from here on (this one included)
}

const edgeSeconds = (e: Edge, sp: Speeds) => (e.ride ? e.d / sp.zip : (e.d * sp.detour) / sp.foot + sp.attach);

export function towards(b: Pt, g: ZipGraph, tf: Transform, sp: Speeds): Field {
  const n = g.nodes.length;
  const time = new Float64Array(n);
  const next = new Int32Array(n).fill(-1);
  const nextRide = new Uint8Array(n);
  const done = new Uint8Array(n);
  const order: number[] = [];
  g.nodes.forEach((node, i) => (time[i] = footSeconds(node.p, b, tf, sp)));
  // Dijkstra from the destination outwards; O(n^2) is fine for a few hundred nodes.
  for (let k = 0; k < n; k++) {
    let u = -1;
    for (let i = 0; i < n; i++) if (!done[i] && (u < 0 || time[i] < time[u])) u = i;
    done[u] = 1;
    order.push(u);
    for (const e of g.adj[u]) {
      const t = time[u] + edgeSeconds(e, sp);
      if (!done[e.to] && t < time[e.to]) {
        time[e.to] = t;
        next[e.to] = u;
        nextRide[e.to] = e.ride ? 1 : 0;
      }
    }
  }
  // A node's next hop is settled before it, so one pass in settle order fills `rides`.
  const rides = new Int32Array(n);
  for (const u of order) rides[u] = next[u] < 0 ? 1 : rides[next[u]] + (nextRide[u] ? 0 : 1);
  return { b, time, next, nextRide, rides };
}

export type Leg =
  | { kind: "walk"; from: Pt; to: Pt; seconds: number }
  | { kind: "ride"; lane: Lane; path: Pt[]; seconds: number };

export interface ZipRoute {
  legs: Leg[];
  total: number;
  rides: Lane[]; // ziplines in riding order
}

/** Where to latch on from `a`, and the total via ziplines. */
function bestBoarding(a: Pt, g: ZipGraph, f: Field, tf: Transform, sp: Speeds): { i: number; total: number } | null {
  let best: { i: number; total: number } | null = null;
  g.nodes.forEach((node, i) => {
    const total = footSeconds(a, node.p, tf, sp) + sp.attach + f.time[i];
    if (!best || total < best.total) best = { i, total };
  });
  return best;
}

/** The fastest way using one or more ziplines: walk on, ride, switch, ride, walk off. */
export function zipRoute(a: Pt, b: Pt, g: ZipGraph, tf: Transform, sp: Speeds, field?: Field): ZipRoute | null {
  const f = field ?? towards(b, g, tf, sp);
  const start = bestBoarding(a, g, f, tf, sp);
  if (!start) return null;
  const legs: Leg[] = [];
  const rides: Lane[] = [];
  let i = start.i;
  legs.push({ kind: "walk", from: a, to: g.nodes[i].p, seconds: footSeconds(a, g.nodes[i].p, tf, sp) + sp.attach });
  let rideFrom = i;
  for (;;) {
    const j = f.next[i];
    const endRide = j < 0 || !f.nextRide[i];
    if (endRide) {
      const n0 = g.nodes[rideFrom];
      const n1 = g.nodes[i];
      const lane = g.lanes[n0.lane];
      if (rideFrom !== i) {
        legs.push({ kind: "ride", lane, path: subpath(lane.pts, n0.s, n1.s, tf), seconds: Math.abs(n1.s - n0.s) / sp.zip });
        rides.push(lane);
      }
      if (j < 0) break;
      const d = worldUnits(n1.p, g.nodes[j].p, tf);
      legs.push({ kind: "walk", from: n1.p, to: g.nodes[j].p, seconds: (d * sp.detour) / sp.foot + sp.attach });
      rideFrom = j;
    }
    i = j;
  }
  const last = g.nodes[i].p;
  legs.push({ kind: "walk", from: last, to: b, seconds: footSeconds(last, b, tf, sp) });
  return { legs, total: start.total, rides };
}

export interface Verdict {
  foot: number;
  zip: ZipRoute | null;
  faster: "foot" | "zip";
  saving: number; // seconds saved by the faster option
}

export function compare(a: Pt, b: Pt, g: ZipGraph, tf: Transform, sp: Speeds): Verdict {
  const foot = footSeconds(a, b, tf, sp);
  const zip = zipRoute(a, b, g, tf, sp);
  const faster = zip && zip.total < foot ? "zip" : "foot";
  return { foot, zip, faster, saving: zip ? Math.abs(foot - zip.total) : 0 };
}

/** For the "faster from where?" map: one field per destination, then a cheap lookup per start. */
export function quickVerdict(a: Pt, g: ZipGraph, f: Field, tf: Transform, sp: Speeds) {
  const foot = footSeconds(a, f.b, tf, sp);
  const start = bestBoarding(a, g, f, tf, sp);
  const zip = start ? start.total : Infinity;
  return {
    faster: zip < foot ? ("zip" as const) : ("foot" as const),
    saving: Math.abs(foot - zip),
    rides: start ? f.rides[start.i] : 0,
  };
}
