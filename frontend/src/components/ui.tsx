import { ReactNode, useEffect, useId, useState } from "react";
import type { HeroCard, RankInfo, Severity } from "../lib/api";
import { evidenceValue, verdict } from "../lib/format";
import { canSpeak, speak, stopSpeaking } from "../lib/speech";
import { Check, Square, TriangleAlert, Volume2, X, type LucideIcon } from "lucide-react";

/** A line icon sized to the text around it. Decorative: the text next to it says the same. */
export function Icon({ icon: Glyph, className = "" }: { icon: LucideIcon; className?: string }) {
  return (
    <Glyph aria-hidden strokeWidth={2.25} className={`inline-block h-[1.1em] w-[1.1em] shrink-0 align-[-0.2em] ${className}`} />
  );
}

export function ReadAloud({ text, label = "Read aloud" }: { text: string; label?: string }) {
  const [on, setOn] = useState(false);
  useEffect(() => () => stopSpeaking(), []);
  if (!canSpeak) return null;
  return (
    <button
      type="button"
      className="chip hover:border-accent"
      aria-pressed={on}
      title={label}
      onClick={() => {
        if (on) {
          stopSpeaking();
          setOn(false);
        } else {
          setOn(true);
          speak(text, () => setOn(false));
        }
      }}
    >
      <Icon icon={on ? Square : Volume2} />
      <span className="sr-only sm:not-sr-only">{on ? "Stop" : "Read"}</span>
    </button>
  );
}

export function EstTag({ title = "Estimate: a coaching rule of thumb, not game data." }: { title?: string }) {
  return (
    <span
      title={title}
      className="ml-1 inline-block rounded-md border border-low/70 px-1.5 text-xs font-bold uppercase text-low align-middle"
    >
      est.
    </span>
  );
}

export function More({ children, label = "More" }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div>
      <button
        type="button"
        className="text-accent font-bold hover:underline"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        {open ? "Less ▴" : `${label} ▾`}
      </button>
      {open && (
        <div id={id} className="mt-3 space-y-3">
          {children}
        </div>
      )}
    </div>
  );
}

const SEV: Record<Severity, { icon: string; label: string; cls: string; stripe: string }> = {
  high: { icon: "▲", label: "High", cls: "text-high border-high", stripe: "bg-high" },
  med: { icon: "■", label: "Medium", cls: "text-med border-med", stripe: "bg-med" },
  low: { icon: "●", label: "Low", cls: "text-low border-low", stripe: "bg-low" },
};

export function sevStripe(s: Severity) {
  return SEV[s].stripe;
}

export function SevBadge({ severity }: { severity: Severity }) {
  const s = SEV[severity];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 text-sm font-bold ${s.cls}`}>
      <span aria-hidden>{s.icon}</span>
      {s.label}
    </span>
  );
}

export function HeroIcon({ hero, size = 48 }: { hero: HeroCard; size?: number }) {
  return hero.image ? (
    <img
      src={hero.image}
      alt={hero.name}
      width={size}
      height={size}
      className="rounded-xl bg-panel2 object-cover"
      style={{ width: size, height: size }}
    />
  ) : (
    <div className="rounded-xl bg-panel2 grid place-items-center font-bold" style={{ width: size, height: size }}>
      {hero.name.slice(0, 2)}
    </div>
  );
}

export function RankBadge({ rank, size = 32 }: { rank: RankInfo | null; size?: number }) {
  if (!rank) return null;
  return (
    <span className="inline-flex items-center gap-1" title={rank.name}>
      {rank.image && <img src={rank.image} alt="" width={size} height={size} style={{ width: size, height: size }} />}
      <span className="text-dim">{rank.name}</span>
    </span>
  );
}

export function WinLoss({ won }: { won: boolean }) {
  return won ? (
    <span className="chip border-good text-good font-bold">
      <Icon icon={Check} /> Win
    </span>
  ) : (
    <span className="chip border-high text-high font-bold">
      <Icon icon={X} /> Loss
    </span>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="card flex items-center gap-3 text-dim" role="status">
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="card border-high" role="alert">
      <p className="font-bold text-high">
        <Icon icon={TriangleAlert} /> Something went wrong
      </p>
      <p className="text-dim">{msg}</p>
    </div>
  );
}

export function StatTile({
  label,
  value,
  benchmark,
  better,
  unit = "",
  est = false,
  benchmarkLabel = "Rank typical",
}: {
  label: string;
  value: number;
  benchmark?: number | null;
  better?: "higher" | "lower" | null;
  unit?: string;
  est?: boolean;
  benchmarkLabel?: string;
}) {
  const v = verdict(value, benchmark, better ?? null);
  const color = v === "better" ? "text-good" : v === "worse" ? "text-high" : "text-ink";
  const icon = v === "better" ? "▲" : v === "worse" ? "▼" : "";
  const word = v === "better" ? "Better" : v === "worse" ? "Worse" : "Even";
  return (
    <div className="rounded-xl bg-panel2 border border-line p-4">
      <div className="label">{label}</div>
      <div className={`text-3xl font-bold ${color}`}>
        {evidenceValue(value, unit)}
        {est && <EstTag />}
      </div>
      {benchmark != null && (
        <div className="text-dim">
          {benchmarkLabel}: <span className="text-ink">{evidenceValue(benchmark, unit)}</span>
          {v !== "even" && (
            <span className={`ml-2 font-bold ${color}`}>
              <span aria-hidden>{icon}</span> {word}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function Section({
  id,
  title,
  children,
  aside,
  icon,
}: {
  id?: string;
  title: string;
  children: ReactNode;
  aside?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <section id={id} className="card scroll-mt-24 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-2xl font-bold">
          {icon && <Icon icon={icon} className="text-accent" />}
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
