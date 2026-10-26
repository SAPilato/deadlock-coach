// Look of the whole app. Colours, fonts and corners live in index.css per theme;
// this file switches between them and hands resolved colours to charts.
import { useEffect, useState } from "react";

export const THEMES = [
  { id: "deco", name: "Brass Deco", blurb: "Deadlock's 1920s occult city. Each tab has its own tone." },
  { id: "slate", name: "Slate", blurb: "Calm dark dashboard. Clean and plain." },
  { id: "casefile", name: "Case File", blurb: "Light paper and dark ink. A detective's ledger." },
  { id: "hud", name: "Neon HUD", blurb: "Esports overlay. Sharp edges and cyan glow." },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];
export const DEFAULT_THEME: ThemeId = "deco";

/** Brass Deco tones, one per tab (colours in index.css). Other themes ignore them. */
export const TONES = [
  { id: "home", name: "Brass", path: "/" },
  { id: "matches", name: "Amethyst", path: "/matches" },
  { id: "trends", name: "Verdigris", path: "/trends" },
  { id: "build", name: "Sapphire", path: "/build" },
  { id: "map", name: "Neon rose", path: "/map" },
  { id: "learn", name: "Ivory", path: "/learn" },
  { id: "settings", name: "Silver", path: "/settings" },
] as const;

export type ToneId = (typeof TONES)[number]["id"];

/** The tab a path belongs to: /matches/123 -> matches, / -> home. */
export function toneFor(path: string): ToneId {
  const p = path.split(/[?#]/)[0];
  return TONES.find((t) => t.path !== "/" && (p === t.path || p.startsWith(`${t.path}/`)))?.id ?? "home";
}

export function applyTone(path: string): void {
  document.documentElement.dataset.tone = toneFor(path);
}

// v2: v1 saved "slate" on every first visit, before anyone picked a theme.
const KEY = "coach.theme.v2";
const EVENT = "coach:themechange";
const isTheme = (id: unknown): id is ThemeId => THEMES.some((t) => t.id === id);

export function currentTheme(): ThemeId {
  const id = document.documentElement.dataset.theme;
  return isTheme(id) ? id : DEFAULT_THEME;
}

/** Switch theme; `save` remembers it as the viewer's pick. */
export function applyTheme(id: ThemeId, save = true): void {
  document.documentElement.dataset.theme = id;
  if (save) {
    try {
      localStorage.setItem(KEY, id);
    } catch {
      /* private mode: the choice lasts until reload */
    }
  }
  window.dispatchEvent(new Event(EVENT));
}

/** ?theme=<id> wins (handy for comparing), then the saved pick, then Brass Deco. Nothing is saved here. */
export function initTheme(): void {
  const fromUrl = new URLSearchParams(window.location.search).get("theme");
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(KEY);
  } catch {
    /* ignore */
  }
  applyTheme(isTheme(fromUrl) ? fromUrl : isTheme(saved) ? saved : DEFAULT_THEME, false);
  applyTone(window.location.pathname);
}

export function useTheme(): ThemeId {
  const [id, setId] = useState(currentTheme);
  useEffect(() => {
    const on = () => setId(currentTheme());
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  return id;
}

const COLOR_VARS = ["bg", "panel", "panel2", "line", "ink", "dim", "muted", "accent", "high", "good", "s1"] as const;
export type ThemeColors = Record<(typeof COLOR_VARS)[number], string>;

/** Resolved theme colours for SVG/canvas code that can't use Tailwind classes. */
export function useThemeColors(): ThemeColors {
  const theme = useTheme();
  const [colors, setColors] = useState<ThemeColors>(readColors);
  useEffect(() => {
    setColors(readColors());
  }, [theme]);
  return colors;
}

function readColors(): ThemeColors {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(
    COLOR_VARS.map((v) => [v, `rgb(${style.getPropertyValue(`--c-${v}`).trim().replace(/\s+/g, ", ")})`]),
  ) as ThemeColors;
}
