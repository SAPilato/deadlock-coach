import { describe, expect, it } from "vitest";
import { pointAt, routeMeters, worldUnits, type Pt, type Transform } from "./geo";

// The real fitted transform is about 4.65e-5 rel per unit on both axes (y flipped).
const tf: Transform = { ax: 4.65e-5, bx: 0.5, ay: -4.65e-5, by: 0.5 };

describe("pointAt", () => {
  const line: Pt[] = [
    [0, 0],
    [1, 0],
    [1, 1],
  ];
  it("walks along segments by length", () => {
    expect(pointAt(line, 0)).toEqual([0, 0]);
    expect(pointAt(line, 0.25)).toEqual([0.5, 0]);
    expect(pointAt(line, 0.75)).toEqual([1, 0.5]);
    expect(pointAt(line, 2)).toEqual([1, 1]);
  });
});

describe("route distance", () => {
  it("converts relative steps to world units and meters", () => {
    const a: Pt = [0.5, 0.5];
    const b: Pt = [0.5 + 4.65e-5 * 1000, 0.5];
    expect(worldUnits(a, b, tf)).toBeCloseTo(1000, 6);
    expect(routeMeters([a, b, a], tf, 0.0254)).toBeCloseTo(50.8, 6);
  });
});
