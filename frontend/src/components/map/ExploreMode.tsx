import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MapPoint } from "../../lib/api";
import { ErrorBox, Loading } from "../ui";
import MapCanvas, { Glyph, Lanes, S, TEAM_COLORS, type Hover } from "./MapCanvas";

const INK = "#f4f5f7";
const DIM = "#c3c2b7";
const CAMP = "#199e70";

// Shape carries identity (colour is shared); the toggle list doubles as the legend.
function glyph(p: MapPoint): { ch: string; color: string; size: number } {
  const team = p.team != null ? TEAM_COLORS[p.team] : INK;
  switch (p.kind) {
    case "guardian":
      return { ch: "▲", color: team, size: 30 };
    case "walker":
      return { ch: "■", color: team, size: 30 };
    case "patron":
      return { ch: "★", color: team, size: 36 };
    case "base_guardian":
      return { ch: "◆", color: team, size: 24 };
    case "shrine":
      return { ch: "◈", color: team, size: 26 };
    case "mid_boss":
      return { ch: "✹", color: INK, size: 38 };
    case "urn_site":
      return { ch: "◎", color: INK, size: 34 };
    case "camp":
      return { ch: "●", color: CAMP, size: p.size === "strong" ? 26 : p.size === "weak" ? 14 : 19 };
    case "vault":
      return { ch: "◆", color: CAMP, size: 26 };
    case "bell_tower":
      return { ch: "♪", color: INK, size: 40 };
    case "sunken_plaza":
      return { ch: "▽", color: INK, size: 40 };
    case "shop":
      return { ch: "$", color: INK, size: 28 };
    case "statue":
      return { ch: "✦", color: DIM, size: 18 };
    case "crate":
      return { ch: "•", color: DIM, size: 18 };
    case "tough_crate":
      return { ch: "▪", color: INK, size: 18 };
    case "buff":
      return { ch: "✚", color: INK, size: 22 };
    case "healing":
      return { ch: "✚", color: CAMP, size: 18 };
    case "vent":
      return { ch: "≋", color: DIM, size: 22 };
    case "veil":
      return { ch: "◌", color: DIM, size: 20 };
    case "move":
      return { ch: p.label.startsWith("Teleporter") ? "⊕" : p.label.startsWith("Bounce") ? "↑" : "┃", color: DIM, size: 22 };
    default:
      return { ch: "◌", color: DIM, size: 18 };
  }
}

const LEGEND: Record<string, string> = {
  objectives: "▲ ■ ◆ ◈ ★ ✹",
  special: "♪ ▽",
  camps: "● ◆",
  urn: "◎",
  districts: "Aa",
  shops: "$",
  statues: "✦",
  crates: "• ▪",
  healing: "✚",
  vents: "≋",
  veils: "◌",
  movement: "⊕ ↑ ┃",
  other: "◌",
};

export default function ExploreMode() {
  const q = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const [on, setOn] = useState<Set<string> | null>(null);
  const [tunnels, setTunnels] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<Hover | null>(null);

  useEffect(() => {
    if (q.data && on == null) setOn(new Set(q.data.layers.filter((l) => l.on).map((l) => l.id)));
  }, [q.data, on]);


  if (q.isLoading || !on) return <Loading label="Loading the map…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  const lanes = d.layers.find((l) => l.id === "lanes")?.lines ?? [];
  const toggle = (id: string) =>
    setOn((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,680px)_1fr]">
      <MapCanvas
        image={d.image}
        overlays={d.overlays.filter((o) => tunnels.has(o.id) && o.image).map((o) => o.image!)}
        hover={hover}
        caption="Hover any marker for facts and a tip."
      >
        {on.has("lanes") && <Lanes lanes={lanes} />}
        {d.layers
          .filter((layer) => layer.id !== "lanes" && on.has(layer.id))
          .map((layer) =>
            layer.points.map((p, i) => {
              if (p.kind === "district") {
                return (
                  <text
                    key={`${layer.id}${i}`} x={p.left * S} y={p.top * S} textAnchor="middle" dominantBaseline="central"
                    fontSize={30} fontWeight={700} fill="#f4f5f7" opacity={0.85} stroke="#0e1014" strokeWidth={6} paintOrder="stroke"
                    style={{ pointerEvents: "none", textTransform: "uppercase", letterSpacing: 2 }}
                  >
                    {p.label}
                  </text>
                );
              }
              const g = glyph(p);
              return (
                <g key={`${layer.id}${i}`}>
                  {p.target && (
                    <line
                      x1={p.left * S} y1={p.top * S} x2={p.target[0] * S} y2={p.target[1] * S}
                      stroke={g.color} strokeWidth={2} strokeDasharray="6 6" opacity={0.6}
                    />
                  )}
                  <Glyph
                    left={p.left} top={p.top} ch={g.ch} color={g.color} size={g.size} label={p.label}
                    onHover={() => setHover({ left: p.left, top: p.top, title: p.label, lines: [p.facts, p.tip && `Tip: ${p.tip}`].filter((x): x is string => !!x) })}
                    onLeave={() => setHover(null)}
                  />
                </g>
              );
            }),
          )}
      </MapCanvas>

      <div className="space-y-5">
        <div>
          <h3 className="label mb-2">Layers</h3>
          <ul className="space-y-1">
            {d.layers.map((layer) => (
              <li key={layer.id}>
                <label className="flex cursor-pointer items-center gap-3">
                  <input type="checkbox" checked={on.has(layer.id)} onChange={() => toggle(layer.id)} className="h-5 w-5 accent-[#3987e5]" />
                  <span className="w-24 shrink-0 text-center text-dim" aria-hidden>
                    {layer.id === "lanes" ? "━" : LEGEND[layer.id]}
                  </span>
                  <span>{layer.label}</span>
                  <span className="text-sm text-muted tnum">{layer.id === "lanes" ? layer.lines?.length : layer.points.length}</span>
                </label>
              </li>
            ))}
            {d.overlays.map((o) => (
              <li key={o.id}>
                <label className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    checked={tunnels.has(o.id)}
                    onChange={() =>
                      setTunnels((s) => {
                        const n = new Set(s);
                        if (n.has(o.id)) n.delete(o.id);
                        else n.add(o.id);
                        return n;
                      })
                    }
                    className="h-5 w-5 accent-[#3987e5]"
                  />
                  <span className="w-24 shrink-0 text-center text-dim" aria-hidden>▒</span>
                  <span>{o.label}</span>
                </label>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-dim">
            <span style={{ color: TEAM_COLORS[0] }}>■</span> {d.teams["0"]} ·{" "}
            <span style={{ color: TEAM_COLORS[1] }}>■</span> {d.teams["1"]}
          </p>
          <p className="mt-1 text-sm text-muted">
            {d.verified
              ? `Objectives and urn sites checked in a replay from ${d.verified.start_time ? new Date(d.verified.start_time * 1000).toLocaleDateString() : `match ${d.verified.match_id}`}.`
              : "Objectives and urn not checked against a replay yet."}
          </p>
        </div>

      </div>
    </div>
  );
}
