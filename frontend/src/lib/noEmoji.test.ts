import { expect, it } from "vitest";

// The UI uses line icons (lucide-react), never emojis.
const files = import.meta.glob("../**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

// Colour-emoji characters, the emoji variation selector, and symbols some systems draw as emoji.
const EMOJI = /\p{Emoji_Presentation}|️|[▶⚙⚠⏱↗⬆⬇⚔☠▪✖✔]/u;

it("UI source has no emojis", () => {
  const hits = Object.entries(files)
    .filter(([path]) => !path.endsWith("noEmoji.test.ts"))
    .flatMap(([path, src]) =>
      src
        .split("\n")
        .map((line, i) => ({ where: `${path}:${i + 1}`, line }))
        .filter(({ line }) => EMOJI.test(line)),
    );
  expect(hits.map((h) => h.where)).toEqual([]);
  expect(Object.keys(files).length).toBeGreaterThan(20);
});
