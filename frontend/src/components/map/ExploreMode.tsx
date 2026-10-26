import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MapPoint } from "../../lib/api";
import { routeMeters, type Pt } from "../../lib/geo";
import { num } from "../../lib/format";
import { ErrorBox, EstTag, Loading } from "../ui";
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
    case "urn_spawn":
      return { ch: "◎", color: INK, size: 30 };
    case "urn_pad":
      return { ch: "▣", color: INK, size: 28 };
    case "shop":
      return { ch: "$", color: INK, size: 28 };
    case "statue":
      return { ch: "✦", color: DIM, size: 18 };
    case "crate":
      return { ch: "•", color: DIM, size: 18 };
    case "buff":
      return { ch: "✚", color: INK, size: 22 };
    case "move":
      return { ch: p.label.startsWith("Teleporter") ? "⊕" : p.label.startsWith("Bounce") ? "↑" : p.label.startsWith("Climb") ? "┃" : "≋", color: DIM, size: 22 };
    default:
      return { ch: "◌", color: DIM, size: 18 };
  }
}

const LEGEND: Record<string, string> = {
  objectives: "▲ ■ ★",
  camps: "● ◆",
  urn: "◎ ▣",
  shops: "$",
  statues: "✦",
  crates: "•",
  buffs: "✚",
  movement: "⊕ ↑ ┃ ≋",
  other: "◌",
};

export default function ExploreMode() {
  const q = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const matches = useQuery({ queryKey: ["matches"], queryFn: () => api.matches() });
  const [on, setOn] = useState<Set<string> | null>(null);
  const [tunnels, setTunnels] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<Hover | null>(null);
  const [planning, setPlanning] = useState(false);
  const [route, setRoute] = useState<Pt[]>([]);
  const [heroId, setHeroId] = useState<number | null>(null);

  useEffect(() => {
    if (q.data && on == null) setOn(new Set(q.data.layers.filter((l) => l.on).map((l) => l.id)));
  }, [q.data, on]);
  useEffect(() => {
    if (heroId == null && q.data && !matches.isLoading) {
      setHeroId(matches.data?.matches.find((m) => !m.street_brawl)?.hero.id ?? q.data.heroes[0]?.id ?? null);
    }
  }, [heroId, q.data, matches.isLoading, matches.data]);

  const meters = useMemo(
    () => (q.data ? routeMeters(route, q.data.transform, q.data.meters_per_unit) : 0),
    [route, q.data],
  );

  if (q.isLoading || !on) return <Loading label="Loading the map…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  const hero = d.heroes.find((h) => h.id === heroId) ?? d.heroes[0];
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
        crosshair={planning}
        onClick={(l, t) => planning && setRoute((r) => [...r, [l, t]])}
        caption={planning ? "Click the map to add route points." : "Hover any marker for a tip."}
      >
        {on.has("lanes") && <Lanes lanes={lanes} />}
        {d.layers
          .filter((layer) => layer.id !== "lanes" && on.has(layer.id))
          .map((layer) =>
            layer.points.map((p, i) => {
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
        {route.length > 0 && (
          <g>
            <polyline points={route.map(([a, b]) => `${a * S},${b * S}`).join(" ")} fill="none" stroke={INK} strokeWidth={5} strokeDasharray="12 8" />
            {route.map(([a, b], i) => (
              <circle key={i} cx={a * S} cy={b * S} r={10} fill={i === 0 ? "#3987e5" : INK} stroke="#171a21" strokeWidth={3} />
            ))}
          </g>
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
        </div>

        <div className="rounded-xl bg-panel2 border border-line p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-bold">🧭 Rotation planner</h3>
            <button type="button" className={planning ? "btn-primary" : "btn"} onClick={() => setPlanning(!planning)} aria-pressed={planning}>
              {planning ? "Planning: on" : "Plan a route"}
            </button>
          </div>
          <label className="block">
            <span className="label">Hero speed</span>
            <select
              value={hero?.id}
              onChange={(e) => setHeroId(Number(e.target.value))}
              className="mt-1 w-full rounded-lg bg-bg border border-line px-3 py-2"
            >
              {d.heroes.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name} · {h.move} m/s
                </option>
              ))}
            </select>
          </label>
          {route.length >= 2 && hero ? (
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="label">Distance</div>
                <div className="text-2xl font-bold tnum">{num(meters)} m<EstTag /></div>
              </div>
              <div>
                <div className="label">Walking</div>
                <div className="text-2xl font-bold tnum">{num(meters / hero.move)} s<EstTag /></div>
              </div>
              <div>
                <div className="label">Sprinting</div>
                <div className="text-2xl font-bold tnum">{num(meters / (hero.move + hero.sprint))} s<EstTag /></div>
              </div>
            </div>
          ) : (
            <p className="text-dim">Click two or more points on the map.</p>
          )}
          <div className="flex gap-2">
            <button type="button" className="btn" disabled={!route.length} onClick={() => setRoute((r) => r.slice(0, -1))}>
              ↶ Undo
            </button>
            <button type="button" className="btn" disabled={!route.length} onClick={() => setRoute([])}>
              Clear
            </button>
          </div>
          <p className="text-sm text-muted">Straight lines. Walls, ziplines and items are ignored.</p>
        </div>
      </div>
    </div>
  );
}
