import { useQuery } from "@tanstack/react-query";
import { api, type Report, type TimelineEvent } from "../lib/api";
import { clock } from "../lib/format";
import Minimap, { type Marker } from "./Minimap";
import SoulsChart from "./SoulsChart";
import { useThemeColors } from "../lib/theme";

const ALLY = "#3987e5";
const ENEMY = "#d95926";

const ROWS: { key: string; label: string; types: TimelineEvent["type"][] }[] = [
  { key: "fights", label: "Fights", types: ["kill", "death"] },
  { key: "objectives", label: "Objectives", types: ["objective", "midboss"] },
  { key: "items", label: "Items", types: ["item"] },
];

function eventStyle(e: TimelineEvent, other: string): { icon: string; color: string } {
  switch (e.type) {
    case "kill":
      return { icon: "●", color: ALLY };
    case "death":
      return { icon: "✕", color: "#d03b3b" };
    case "objective":
      return { icon: "◆", color: e.side === "ally" ? ALLY : ENEMY };
    case "midboss":
      return { icon: "★", color: e.side === "ally" ? ALLY : ENEMY };
    default:
      return { icon: "•", color: other };
  }
}

export default function Timeline({
  report,
  time,
  setTime,
}: {
  report: Report;
  time: number | null;
  setTime: (t: number) => void;
}) {
  const c = useThemeColors();
  const duration = report.timeline.duration_s;
  const t = time ?? 0;
  const paths = useQuery({ queryKey: ["paths", report.match.id], queryFn: () => api.paths(report.match.id, 5) });

  const near = report.timeline.events.filter((e) => Math.abs(e.t - t) <= 30).slice(0, 5);

  const markers: Marker[] = [];
  if (paths.data) {
    const idx = Math.min(Math.round(t / paths.data.step), paths.data.players[0]?.pts.length - 1);
    for (const p of paths.data.players) {
      const pt = p.pts[Math.max(0, idx)];
      if (!pt) continue;
      const dead = p.dead.some(([a, b]) => a <= t && t < b);
      markers.push({
        key: `p${p.slot}`,
        left: pt[0],
        top: pt[1],
        color: p.ally ? ALLY : ENEMY,
        label: `${p.is_me ? "You" : p.name}${dead ? " (dead)" : ""}`,
        shape: dead ? "x" : "dot",
        emphasis: p.is_me,
        size: p.is_me ? 12 : 10,
      });
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_minmax(0,420px)]">
      <div className="space-y-4 min-w-0">
        <div>
          <h3 className="text-lg font-bold">Souls over time</h3>
          <p className="text-dim text-sm">Click the chart to jump to that minute.</p>
        </div>
        <SoulsChart series={report.timeline.series} time={time} onPick={setTime} />

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-dim" aria-hidden>
          <span><span style={{ color: ALLY }}>●</span> Your kill</span>
          <span><span style={{ color: "#d03b3b" }}>✕</span> Your death</span>
          <span><span style={{ color: ALLY }}>◆</span> Your team took it</span>
          <span><span style={{ color: ENEMY }}>◆</span> Enemy took it</span>
          <span>★ Mid Boss</span>
          <span>• Item</span>
        </div>
        <div className="space-y-2" aria-label="Match events">
          {ROWS.map((row) => (
            <div key={row.key} className="grid grid-cols-[6.5rem_1fr] items-center gap-2">
              <span className="text-sm text-muted">{row.label}</span>
              <div className="relative h-8 rounded-lg bg-panel2 border border-line">
                {report.timeline.events
                  .filter((e) => row.types.includes(e.type))
                  .map((e, i) => {
                    const s = eventStyle(e, c.dim);
                    return (
                      <button
                        key={`${row.key}${i}`}
                        type="button"
                        title={`${clock(e.t)} ${e.label}`}
                        aria-label={`${clock(e.t)} ${e.label}`}
                        onClick={() => setTime(e.t)}
                        className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 px-1 text-lg leading-none hover:scale-125"
                        style={{ left: `${(e.t / duration) * 100}%`, color: s.color }}
                      >
                        {s.icon}
                      </button>
                    );
                  })}
                <span
                  className="absolute top-0 h-full w-0.5 bg-ink"
                  style={{ left: `${(t / duration) * 100}%` }}
                  aria-hidden
                />
              </div>
            </div>
          ))}
        </div>

        <label className="block">
          <span className="label">Time: </span>
          <span className="text-2xl font-bold tnum">{clock(t)}</span>
          <input
            type="range"
            min={0}
            max={duration}
            step={5}
            value={t}
            onChange={(e) => setTime(Number(e.target.value))}
            className="mt-2 w-full accent-accent"
            aria-label="Match time"
          />
        </label>

        <div className="rounded-xl bg-panel2 border border-line p-3 min-h-[4rem]">
          <div className="label mb-1">Around {clock(t)}</div>
          {near.length === 0 ? (
            <p className="text-dim">Nothing big happened here.</p>
          ) : (
            <ul className="space-y-1">
              {near.map((e, i) => {
                const s = eventStyle(e, c.dim);
                return (
                  <li key={i}>
                    <span style={{ color: s.color }} aria-hidden>
                      {s.icon}
                    </span>{" "}
                    <span className="tnum text-dim">{clock(e.t)}</span> {e.label}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold mb-2">Where everyone was</h3>
        <div className="flex gap-4 text-sm text-dim mb-2">
          <span><span style={{ color: ALLY }}>●</span> Your team</span>
          <span><span style={{ color: ENEMY }}>●</span> Enemies</span>
          <span>◎ You (white ring)</span>
          <span>✕ Dead</span>
        </div>
        <Minimap map={report.map} markers={markers} caption={`Positions at ${clock(t)}. Hover a dot for the hero.`} />
      </div>
    </div>
  );
}
