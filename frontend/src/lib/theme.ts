// Look of the whole app. Colours, fonts and corners live in index.css per theme;
// this file switches between them and hands resolved colours to charts.
import { useEffect, useState } from "react";

export const THEMES = [
  { id: "slate", name: "Slate", blurb: "Calm dark dashboard. Clean and plain." },
  { id: "deco", name: "Brass Deco", blurb: "Deadlock's 1920s occult city. Brass on black." },
  { id: "casefile", name: "Case File", blurb: "Light paper and dark ink. A detective's ledger." },
  { id: "hud", name: "Neon HUD", blurb: "Esports overlay. Sharp edges and cyan glow." },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];

const KEY = "coach.theme";
const EVENT = "coach:themechange";
const isTheme = (id: unknown): id is ThemeId => THEMES.some((t) => t.id === id);

export function currentTheme(): ThemeId {
  const id = document.documentElement.dataset.theme;
  return isTheme(id) ? id : "slate";
}

export function applyTheme(id: ThemeId): void {
  document.documentElement.dataset.theme = id;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* private mode: the choice lasts until reload */
  }
  window.dispatchEvent(new Event(EVENT));
}

/** ?theme=<id> wins (handy for comparing), then the saved choice, then Slate. */
export function initTheme(): void {
  const fromUrl = new URLSearchParams(window.location.search).get("theme");
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(KEY);
  } catch {
    /* ignore */
  }
  applyTheme(isTheme(fromUrl) ? fromUrl : isTheme(saved) ? saved : "slate");
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
