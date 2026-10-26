import { describe, expect, it } from "vitest";
import { ago, clock, compact, evidenceValue, signed, statDelta, statValue, verdict } from "./format";

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

describe("stat values", () => {
  it("picks decimals by size and unit", () => {
    expect(statValue(1234.6, "")).toBe("1,235");
    expect(statValue(51.39, "")).toBe("51.4");
    expect(statValue(6.84, "")).toBe("6.84");
    expect(statValue(2.585, "s")).toBe("2.59 s");
    expect(statValue(36.04, "%")).toBe("36%");
  });
  it("signs deltas and hides no-change", () => {
    expect(statDelta(730, 940, "")).toBe("+210");
    expect(statDelta(2.585, 2.3265, "s")).toBe("−0.26 s");
    expect(statDelta(5, 5, "")).toBeNull();
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
