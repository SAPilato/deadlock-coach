// Small formatters. Numbers lead every card, so these keep them short.

export function clock(seconds: number | null | undefined): string {
  if (seconds == null || !isFinite(seconds)) return "–";
  const sign = seconds < 0 ? "-" : "";
  const s = Math.round(Math.abs(seconds));
  return `${sign}${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function num(n: number | null | undefined, digits = 0): string {
  if (n == null || !isFinite(n)) return "–";
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

/** 12,345 -> "12.3k" for tight spaces. */
export function compact(n: number | null | undefined): string {
  if (n == null || !isFinite(n)) return "–";
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(Math.abs(n) >= 10000 ? 0 : 1)}k`;
  return String(Math.round(n));
}

export function signed(n: number, formatter: (v: number) => string = (v) => num(v)): string {
  return `${n > 0 ? "+" : n < 0 ? "−" : ""}${formatter(Math.abs(n))}`;
}

export function ago(unixSeconds: number, now = Date.now() / 1000): string {
  const d = now - unixSeconds;
  if (d < 3600) return `${Math.max(1, Math.round(d / 60))} min ago`;
  if (d < 86400) return `${Math.round(d / 3600)} h ago`;
  const days = Math.round(d / 86400);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/** Format an evidence value by its unit. */
export function evidenceValue(v: number | string | null, unit: string): string {
  if (v == null) return "–";
  if (typeof v === "string") return v;
  switch (unit) {
    case "time":
      return clock(v);
    case "%":
      return `${num(v)}%`;
    case "min":
      return `${num(v, 1)} min`;
    case "s":
      return `${num(v)} s`;
    case "m":
      return `${num(v)} m`;
    case "/min":
      return `${num(v)}/min`;
    default:
      return num(v, 1);
  }
}

/** Is `value` better than `benchmark`, given which direction is good? */
export function verdict(
  value: number,
  benchmark: number | null | undefined,
  better: "higher" | "lower" | null,
): "better" | "worse" | "even" {
  if (benchmark == null || better == null) return "even";
  const diff = (value - benchmark) / (Math.abs(benchmark) || 1);
  if (Math.abs(diff) < 0.05) return "even";
  const higher = value > benchmark;
  return (better === "higher") === higher ? "better" : "worse";
}
