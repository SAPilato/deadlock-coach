import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { num } from "../../lib/format";
import type { Pt } from "../../lib/geo";
import { compare, type Lane, type Speeds } from "../../lib/route";
import { ErrorBox, EstTag, Loading } from "../ui";
import MapCanvas, { Lanes, S, SURFACE } from "./MapCanvas";

// Two outcomes, validated category slots (not team colours).
const ZIP = "#199e70";
const FOOT = "#9085e9";
const INK = "#f4f5f7";
const MAX_SAVING_S = 20; // full colour at 20+ seconds saved
const TIE_S = 2; // est. closer than this is a tie: estimates are not that precise

type Mode = "pair" | "grid";
type Style = "optimal" | "normal";

function Marker({ p, label }: { p: Pt; label: string }) {
  return (
    <g>
      <circle cx={p[0] * S} cy={p[1] * S} r={20} fill={INK} stroke={SURFACE} strokeWidth={4} />
      <text x={p[0] * S} y={p[1] * S} textAnchor="middle" dominantBaseline="central" fontSize={22} fontWeight={700} fill={SURFACE}>
        {label}
      </text>
    </g>
  );
}

const line = (pts: Pt[]) => pts.map(([a, b]) => `${a * S},${b * S}`).join(" ");

export default function RouteMode() {
  const layers = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const mv = useQuery({ queryKey: ["macro-movement"], queryFn: api.macroMovement, staleTime: Infinity });
  const matches = useQuery({ queryKey: ["matches"], queryFn: () => api.matches() });
  const [mode, setMode] = useState<Mode>("pair");
  const [style, setStyle] = useState<Style>("optimal");
  const [a, setA] = useState<Pt | null>(null);
  const [b, setB] = useState<Pt | null>(null);
  const [dest, setDest] = useState<Pt | null>(null);
  const [heroId, setHeroId] = useState<number | null>(null);

  useEffect(() => {
    if (heroId == null && layers.data && !matches.isLoading) {
      setHeroId(matches.data?.matches.find((m) => !m.street_brawl)?.hero.id ?? layers.data.heroes[0]?.id ?? null);
    }
  }, [heroId, layers.data, matches.isLoading, matches.data]);

  const d = layers.data;
  const m = mv.data;
  const lanes: Lane[] = (d?.layers.find((l) => l.id === "lanes")?.lines ?? []) as Lane[];
  const hero = d?.heroes.find((h) => h.id === heroId) ?? d?.heroes[0];
  const speeds: Speeds | null =
    m && hero
      ? {
          // Measured speeds scaled by this hero's base move speed vs the average hero.
          foot: (style === "optimal" ? m.fast_speed : m.foot_speed) * (hero.move / m.avg_hero_move),
          zip: m.zip_speed,
          detour: style === "optimal" ? m.detour_best : m.detour,
          attach: m.attach_s,
        }
      : null;

  const verdict = useMemo(
    () => (d && speeds && a && b ? compare(a, b, lanes, d.transform, speeds) : null),
    [a, b, d, speeds, lanes],
  );
  const grid = useMemo(() => {
    if (!d || !m || !speeds || !dest) return [];
    const g = m.grid;
    return m.walkable.map(([i, j]) => {
      const v = compare([(i + 0.5) / g, (j + 0.5) / g], dest, lanes, d.transform, speeds);
      return { i, j, faster: v.faster, saving: v.saving };
    });
  }, [d, m, speeds, dest, lanes]);

  if (layers.isLoading || mv.isLoading) return <Loading label="Measuring how fast players really move…" />;
  if (layers.error || mv.error) return <ErrorBox error={layers.error || mv.error} />;
  if (!d || !m || !speeds) return null;

  const onClick = (left: number, top: number) => {
    const p: Pt = [left, top];
    if (mode === "grid") setDest(p);
    else if (!a || b) {
      setA(p);
      setB(null);
    } else setB(p);
  };
  const cell = S / m.grid;
  const zipShare = grid.length ? grid.filter((c) => c.faster === "zip").length / grid.length : 0;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,680px)_1fr]">
      <MapCanvas
        image={d.image}
        crosshair
        onClick={onClick}
        caption={mode === "pair" ? "Click a start (A), then a destination (B)." : "Click a destination. Colours show the faster way there."}
      >
        {mode === "grid" && grid.map((c) => (
          <rect
            key={`${c.i}-${c.j}`}
            x={c.i * cell}
            y={c.j * cell}
            width={cell}
            height={cell}
            fill={c.faster === "zip" ? ZIP : FOOT}
            opacity={0.15 + 0.6 * Math.min(1, c.saving / MAX_SAVING_S)}
          />
        ))}
        <Lanes lanes={lanes} width={6} />
        {mode === "pair" && verdict && a && b && (
          <g>
            <line x1={a[0] * S} y1={a[1] * S} x2={b[0] * S} y2={b[1] * S} stroke={FOOT} strokeWidth={6} strokeDasharray="14 10" />
            {verdict.zip && (
              <g>
                <polyline points={line([a, verdict.zip.entry])} fill="none" stroke={ZIP} strokeWidth={4} strokeDasharray="4 8" />
                <polyline points={line(verdict.zip.ridePath)} fill="none" stroke={ZIP} strokeWidth={10} strokeLinecap="round" />
                <polyline points={line([verdict.zip.exit, b])} fill="none" stroke={ZIP} strokeWidth={4} strokeDasharray="4 8" />
              </g>
            )}
          </g>
        )}
        {mode === "pair" && a && <Marker p={a} label="A" />}
        {mode === "pair" && b && <Marker p={b} label="B" />}
        {mode === "grid" && dest && <Marker p={dest} label="★" />}
      </MapCanvas>

      <div className="space-y-5">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Planner view">
          {(
            [
              ["pair", "A → B"],
              ["grid", "Faster from where?"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={mode === id}
              type="button"
              onClick={() => setMode(id)}
              className={`rounded-xl border-2 px-4 py-2 font-bold ${mode === id ? "border-s1 bg-panel2" : "border-line text-dim"}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">Hero</span>
            <select value={hero?.id} onChange={(e) => setHeroId(Number(e.target.value))} className="mt-1 w-full rounded-lg bg-panel2 border border-line px-3 py-2">
              {d.heroes.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name} · {h.move} m/s base
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="label">On foot</span>
            <select value={style} onChange={(e) => setStyle(e.target.value as Style)} className="mt-1 w-full rounded-lg bg-panel2 border border-line px-3 py-2">
              <option value="optimal">Optimal movement</option>
              <option value="normal">Normal movement</option>
            </select>
          </label>
        </div>

        {mode === "pair" &&
          (verdict ? (
            <div className="space-y-3">
              {verdict.saving < TIE_S ? (
                <div className="rounded-xl border-2 border-line p-4">
                  <div className="label">Faster</div>
                  <div className="text-3xl font-bold">
                    About the same
                    <EstTag />
                  </div>
                  <div className="text-xl">Pick the safer path.</div>
                </div>
              ) : (
                <div className={`rounded-xl border-2 p-4 ${verdict.faster === "zip" ? "border-[#199e70]" : "border-[#9085e9]"}`}>
                  <div className="label">Faster</div>
                  <div className="text-3xl font-bold">
                    {verdict.faster === "zip" ? `Zipline on ${verdict.zip?.lane.name}` : "On foot"}
                    <EstTag />
                  </div>
                  <div className="text-xl">
                    Saves <b className="tnum">{num(verdict.saving)} s</b>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-panel2 border border-line p-4">
                  <div className="label" style={{ color: FOOT }}>
                    ┅ On foot
                  </div>
                  <div className="text-3xl font-bold tnum">{num(verdict.foot)} s</div>
                </div>
                {verdict.zip && (
                  <div className="rounded-xl bg-panel2 border border-line p-4">
                    <div className="label" style={{ color: ZIP }}>
                      ━ Zipline
                    </div>
                    <div className="text-3xl font-bold tnum">{num(verdict.zip.total)} s</div>
                    <div className="text-sm text-dim tnum">
                      walk {num(verdict.zip.walkIn)} + ride {num(verdict.zip.ride)} + walk {num(verdict.zip.walkOut)} s
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="text-dim">Click two spots on the map.</p>
          ))}

        {mode === "grid" &&
          (dest ? (
            <div className="space-y-2">
              <div className="flex gap-4 text-lg">
                <span>
                  <span style={{ color: ZIP }}>■</span> Zipline faster
                </span>
                <span>
                  <span style={{ color: FOOT }}>■</span> On foot faster
                </span>
              </div>
              <p className="text-dim">Brighter = more seconds saved.</p>
              <p className="text-xl">
                Zipline wins from <b className="tnum">{Math.round(zipShare * 100)}%</b> of the map.
              </p>
            </div>
          ) : (
            <p className="text-dim">Click a destination on the map.</p>
          ))}

        <ul className="space-y-1 text-sm text-muted">
          <li>
            Speeds measured from {m.matches} real matches: zipline {num(m.zip_speed)} u/s, optimal movement {num(m.fast_speed)} u/s,
            normal {num(m.foot_speed)} u/s.
          </li>
          <li>Real paths bend: walking counts ×{num(speeds.detour, 2)} the straight line.</li>
          <li>Ziplines ride both ways (game setting). Zipline boost and blocked lanes are not modelled.</li>
        </ul>
      </div>
    </div>
  );
}
