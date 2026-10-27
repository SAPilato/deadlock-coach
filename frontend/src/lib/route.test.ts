import { describe, expect, it } from "vitest";
import { buildGraph, compare, ownedSection, project, quickVerdict, subpath, towards, zipRoute, type Lane, type Speeds } from "./route";
import type { Transform } from "./geo";

// 1 relative unit = 10,000 world units on both axes (y flipped like the real map).
const tf: Transform = { ax: 1e-4, bx: 0.5, ay: -1e-4, by: 0.5 };
// A straight lane along y = 0.5 from left to right: 10,000 world units long.
const lane: Lane = { id: 1, name: "Test", color: "#fff", pts: [[0, 0.5], [0.5, 0.5], [1, 0.5]] };
// Measured shapes: zipline about twice optimal movement.
const sp: Speeds = { foot: 450, zip: 900, detour: 1.2, attach: 1 };

describe("project", () => {
  it("finds distance along and away from the lane in world units", () => {
    const p = project(lane.pts, [0.25, 0.4], tf);
    expect(p.s).toBeCloseTo(2500, 6);
    expect(p.dist).toBeCloseTo(1000, 6);
    expect(p.point[0]).toBeCloseTo(0.25, 9);
    expect(p.point[1]).toBeCloseTo(0.5, 9);
  });
});

describe("subpath", () => {
  it("returns the ridden stretch in travel order", () => {
    const path = subpath(lane.pts, 7500, 2500, tf);
    expect(path[0][0]).toBeCloseTo(0.75, 9);
    expect(path[path.length - 1][0]).toBeCloseTo(0.25, 9);
  });
});

const one = buildGraph([lane], tf);
const legSum = (r: { legs: { seconds: number }[] }) => r.legs.reduce((t, l) => t + l.seconds, 0);

describe("compare", () => {
  it("prefers the zipline for long trips next to a lane", () => {
    const v = compare([0.05, 0.48], [0.95, 0.48], one, tf, sp);
    // On foot: 9000 * 1.2 / 450 = 24 s. Zipline straight on and off: 2 * 200*1.2/450 + 9000/900 + 1 = ~12.07 s.
    // Walking on at an angle (boarding further along) is a little faster still.
    expect(v.foot).toBeCloseTo(24, 6);
    expect(v.zip!.total).toBeLessThanOrEqual(12.07);
    expect(v.zip!.total).toBeGreaterThan(11.8);
    expect(v.faster).toBe("zip");
    expect(v.zip!.rides).toHaveLength(1);
  });
  it("prefers walking for short hops far from any lane", () => {
    const v = compare([0.4, 0.1], [0.45, 0.1], one, tf, sp);
    expect(v.faster).toBe("foot");
  });
  it("can ride the zipline in either direction", () => {
    const there = zipRoute([0.05, 0.5], [0.95, 0.5], one, tf, sp)!;
    const back = zipRoute([0.95, 0.5], [0.05, 0.5], one, tf, sp)!;
    expect(back.total).toBeCloseTo(there.total, 6);
  });
});

describe("several ziplines", () => {
  // Lane A runs along the top, lane B down the right side; they meet near the top-right corner.
  const a: Lane = { id: 1, name: "A", color: "#fff", pts: [[0.05, 0.1], [0.95, 0.1]] };
  const b: Lane = { id: 2, name: "B", color: "#fff", pts: [[0.93, 0.12], [0.93, 0.95]] };
  const g = buildGraph([a, b], tf);
  const from: [number, number] = [0.05, 0.1];
  const to: [number, number] = [0.93, 0.95];

  it("chains two ziplines when that is fastest", () => {
    const r = zipRoute(from, to, g, tf, sp)!;
    expect(r.rides.map((l) => l.name)).toEqual(["A", "B"]);
    // Better than either zipline alone.
    const onlyA = zipRoute(from, to, buildGraph([a], tf), tf, sp)!;
    const onlyB = zipRoute(from, to, buildGraph([b], tf), tf, sp)!;
    expect(r.total).toBeLessThan(Math.min(onlyA.total, onlyB.total));
  });
  it("legs add up to the total", () => {
    const r = zipRoute(from, to, g, tf, sp)!;
    expect(legSum(r)).toBeCloseTo(r.total, 6);
    expect(r.legs.map((l) => l.kind)).toEqual(["walk", "ride", "walk", "ride", "walk"]);
  });
  it("the quick map lookup agrees with the full route", () => {
    const f = towards(to, g, tf, sp);
    const q = quickVerdict(from, g, f, tf, sp);
    const v = compare(from, to, g, tf, sp);
    expect(q.faster).toBe(v.faster);
    expect(q.rides).toBe(2);
    expect(q.saving).toBeCloseTo(v.saving, 6);
  });
});

describe("team-owned ziplines", () => {
  // The test lane runs left (team 0's base) to right (team 1's base), 10,000 units long.
  const from: [number, number] = [0.05, 0.5];
  const to: [number, number] = [0.95, 0.5];

  it("each team owns its stretch from its own base", () => {
    expect(ownedSection(0, 0.43)).toEqual([0, 0.43]);
    expect(ownedSection(1, 0.43)[0]).toBeCloseTo(0.57, 9);
    expect(ownedSection(1, 2)).toEqual([0, 1]);
  });

  it("only rides your own stretch, and says which way", () => {
    const g0 = buildGraph([lane], tf, new Map([[1, ownedSection(0, 0.5)]]), 0);
    const r0 = zipRoute(from, to, g0, tf, sp)!;
    const ride0 = r0.legs.find((l) => l.kind === "ride")!;
    expect(ride0.kind === "ride" && ride0.toward).toBe("enemy");
    expect(ride0.seconds).toBeLessThanOrEqual(5000 / sp.zip + 1e-9); // at most half the lane
    const g1 = buildGraph([lane], tf, new Map([[1, ownedSection(1, 0.5)]]), 1);
    const ride1 = zipRoute(from, to, g1, tf, sp)!.legs.find((l) => l.kind === "ride")!;
    expect(ride1.kind === "ride" && ride1.toward).toBe("home");
  });

  it("a longer zipline is faster", () => {
    const short = zipRoute(from, to, buildGraph([lane], tf, new Map([[1, ownedSection(0, 0.3)]]), 0), tf, sp)!;
    const long = zipRoute(from, to, buildGraph([lane], tf, new Map([[1, ownedSection(0, 0.9)]]), 0), tf, sp)!;
    expect(long.total).toBeLessThan(short.total);
  });

  it("a lane you own none of cannot be ridden", () => {
    const g = buildGraph([lane], tf, new Map(), 0);
    expect(g.nodes).toHaveLength(0);
    expect(compare(from, to, g, tf, sp).faster).toBe("foot");
  });
});
