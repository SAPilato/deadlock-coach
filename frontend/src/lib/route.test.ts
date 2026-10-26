import { describe, expect, it } from "vitest";
import { compare, project, subpath, zipRoute, type Lane, type Speeds } from "./route";
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

describe("compare", () => {
  it("prefers the zipline for long trips next to a lane", () => {
    const v = compare([0.05, 0.48], [0.95, 0.48], [lane], tf, sp);
    // On foot: 9000 * 1.2 / 450 = 24 s. Zipline: walks 2 * 200*1.2/450 + ride 9000/900 + 1 = ~12.07 s.
    expect(v.foot).toBeCloseTo(24, 6);
    expect(v.zip!.total).toBeCloseTo(12.07, 2);
    expect(v.faster).toBe("zip");
  });
  it("prefers walking for short hops far from any lane", () => {
    const v = compare([0.4, 0.1], [0.45, 0.1], [lane], tf, sp);
    expect(v.faster).toBe("foot");
  });
  it("can ride the zipline in either direction", () => {
    const there = zipRoute([0.05, 0.5], [0.95, 0.5], [lane], tf, sp)!;
    const back = zipRoute([0.95, 0.5], [0.05, 0.5], [lane], tf, sp)!;
    expect(back.total).toBeCloseTo(there.total, 9);
  });
});
