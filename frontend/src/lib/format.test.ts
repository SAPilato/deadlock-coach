import { describe, expect, it } from "vitest";
import { ago, clock, compact, evidenceValue, signed, verdict } from "./format";

describe("clock", () => {
  it("formats seconds as m:ss", () => {
    expect(clock(0)).toBe("0:00");
    expect(clock(65)).toBe("1:05");
    expect(clock(1641.6)).toBe("27:22");
    expect(clock(-90)).toBe("-1:30");
    expect(clock(null)).toBe("–");
  });
});

describe("numbers", () => {
  it("compacts large numbers", () => {
    expect(compact(950)).toBe("950");
    expect(compact(1234)).toBe("1.2k");
    expect(compact(34567)).toBe("35k");
  });
  it("signs deltas", () => {
    expect(signed(120, clock)).toBe("+2:00");
    expect(signed(-30, clock)).toBe("−0:30");
  });
  it("formats evidence by unit", () => {
    expect(evidenceValue(1229, "time")).toBe("20:29");
    expect(evidenceValue(17, "%")).toBe("17%");
    expect(evidenceValue(812.4, "/min")).toBe("812/min");
  });
  it("describes time ago", () => {
    expect(ago(1000, 1000 + 7200)).toBe("2 h ago");
    expect(ago(1000, 1000 + 86400)).toBe("yesterday");
  });
});

describe("verdict", () => {
  it("respects which direction is better", () => {
    expect(verdict(10, 5, "higher")).toBe("better");
    expect(verdict(10, 5, "lower")).toBe("worse");
    expect(verdict(100, 102, "higher")).toBe("even");
    expect(verdict(3, null, "lower")).toBe("even");
  });
});
