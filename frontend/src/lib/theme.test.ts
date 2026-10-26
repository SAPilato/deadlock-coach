import { describe, expect, it } from "vitest";
import { THEMES, TONES, toneFor } from "./theme";

describe("toneFor", () => {
  it("gives every tab its own tone", () => {
    expect(new Set(TONES.map((t) => t.id)).size).toBe(TONES.length);
    for (const t of TONES) expect(toneFor(t.path)).toBe(t.id);
  });

  it("follows sub-pages, and ignores query and hash", () => {
    expect(toneFor("/matches/123966074")).toBe("matches");
    expect(toneFor("/learn/item-timing")).toBe("learn");
    expect(toneFor("/map?mode=explore&layers=lanes,camps")).toBe("map");
    expect(toneFor("/build#shop")).toBe("build");
  });

  it("falls back to home", () => {
    expect(toneFor("/")).toBe("home");
    expect(toneFor("/nowhere")).toBe("home");
    expect(toneFor("/matchesque")).toBe("home");
  });
});

it("Brass Deco is listed first, as the default", () => {
  expect(THEMES[0].id).toBe("deco");
});
