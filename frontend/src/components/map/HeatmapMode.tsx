import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { clock } from "../../lib/format";
import { ErrorBox, Loading } from "../ui";
import MapCanvas, { ALLY, ENEMY, Glyph, Lanes, S, type Hover } from "./MapCanvas";

const PHASES = [
  { id: "early", label: "Laning" },
  { id: "mid", label: "Mid game" },
  { id: "late", label: "Late game" },
] as const;
const HEAT = "#86b6ef"; // one hue; more time = more opaque

export default function HeatmapMode() {
  const q = useQuery({ queryKey: ["macro-heatmap"], queryFn: () => api.macroHeatmap(10) });
  const layers = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const [phase, setPhase] = useState<"early" | "mid" | "late">("early");
  const [hover, setHover] = useState<Hover | null>(null);

  if (q.isLoading) return <Loading label="Reading your last 10 games…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  const ph = d.phases[phase];
  const cell = S / d.grid;
  const objectives = d.objectives.filter((o) => o.phase === phase);
  const lanes = layers.data?.layers.find((l) => l.id === "lanes")?.lines ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,680px)_1fr]">
      <MapCanvas image={layers.data?.image} hover={hover} caption="Brighter = more of your time there.">
        <Lanes lanes={lanes} width={4} />
        {ph.cells.map(([i, j, c]) => (
          <rect
            key={`${i}-${j}`}
            x={i * cell}
            y={j * cell}
            width={cell}
            height={cell}
            fill={HEAT}
            opacity={0.15 + 0.7 * Math.sqrt(c / (ph.max || 1))}
          />
        ))}
        {objectives.map((o, k) => (
          <Glyph
            key={k}
            left={o.left}
            top={o.top}
            ch={o.taken ? "▲" : "▼"}
            color={o.taken ? ALLY : ENEMY}
            size={26}
            label={o.name}
            onHover={() => setHover({ left: o.left, top: o.top, title: `${o.taken ? "Taken" : "Lost"}: ${o.name}`, lines: [`At ${clock(o.t)} in match ${o.match_id}`] })}
            onLeave={() => setHover(null)}
          />
        ))}
      </MapCanvas>
      <div className="space-y-5">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Game phase">
          {PHASES.map((p) => (
            <button
              key={p.id}
              role="tab"
              aria-selected={phase === p.id}
              type="button"
              onClick={() => setPhase(p.id)}
              className={`rounded-xl border-2 px-4 py-2 font-bold ${phase === p.id ? "border-s1 bg-panel2" : "border-line text-dim"}`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-panel2 border border-line p-4">
            <div className="label">Games</div>
            <div className="text-3xl font-bold tnum">{d.matches}</div>
          </div>
          <div className="rounded-xl bg-panel2 border border-line p-4">
            <div className="label">Minutes alive</div>
            <div className="text-3xl font-bold tnum">{ph.minutes}</div>
          </div>
        </div>
        <ul className="space-y-1 text-dim">
          <li>
            <span style={{ color: ALLY }}>▲</span> Objective your team took
          </li>
          <li>
            <span style={{ color: ENEMY }}>▼</span> Objective your team lost
          </li>
        </ul>
        <p className="text-dim">Are you near the objectives that fell? If not, rotate sooner.</p>
        <p className="text-sm text-muted">Phases end when your lane's Guardian falls, then the first Walker.</p>
      </div>
    </div>
  );
}
