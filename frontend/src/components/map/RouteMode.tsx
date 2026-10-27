import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { num } from "../../lib/format";
import type { Pt } from "../../lib/geo";
import { buildGraph, compare, laneLength, ownedSection, quickVerdict, subpath, towards, type Lane, type Leg, type Speeds, type Team } from "../../lib/route";
import { ErrorBox, EstTag, Loading } from "../ui";
import MapCanvas, { Lanes, S, SURFACE, TEAM_COLORS } from "./MapCanvas";

// Three outcomes, validated category slots (not team colours; blue failed CVD next to violet).
const ZIP = "#199e70";
const MULTI = "#c98500"; // two or more ziplines
const FOOT = "#9085e9";
const INK = "#f4f5f7";
const MAX_SAVING_S = 20; // full colour at 20+ seconds saved
const TIE_S = 2; // est. closer than this is a tie: estimates are not that precise

type Mode = "pair" | "grid";
type Style = "optimal" | "high" | "normal";

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
  const [team, setTeam] = useState<Team | null>(null);
  const [reach, setReach] = useState<Record<number, number>>({});

  useEffect(() => {
    if (heroId == null && layers.data && !matches.isLoading) {
      setHeroId(matches.data?.matches.find((m) => !m.street_brawl)?.hero.id ?? layers.data.heroes[0]?.id ?? null);
    }
  }, [heroId, layers.data, matches.isLoading, matches.data]);
  // Start on the side you played last; switch any time.
  useEffect(() => {
    if (team == null && !matches.isLoading) {
      const last = matches.data?.matches.find((m) => !m.street_brawl)?.team;
      setTeam(last === 1 ? 1 : 0);
    }
  }, [team, matches.isLoading, matches.data]);

  const d = layers.data;
  const m = mv.data;
  const lanes: Lane[] = (d?.layers.find((l) => l.id === "lanes")?.lines ?? []) as Lane[];
  const hero = d?.heroes.find((h) => h.id === heroId) ?? d?.heroes[0];
  // Route times from real trips: straight-line progress, so no separate detour factor.
  const profile = style === "high" && m?.high ? m.high : m;
  const progress = style === "normal" ? profile?.progress_normal : profile?.progress_fast;
  const speeds: Speeds | null =
    m && hero && progress
      ? {
          // Scaled by this hero's base move speed vs the average hero.
          foot: progress * (hero.move / m.avg_hero_move),
          zip: profile!.zip_speed,
          detour: 1,
          attach: m.ride_overhead_s,
        }
      : null;

  // Your team's part of each zipline: from your base out to its reach (start reach measured).
  const side: Team = team ?? 0;
  // Opening share and home stretch per lane, from the newest parsed replay (else one measured share).
  const startFor = (laneId: number) => m?.zipline_map?.start[String(laneId)]?.[side] ?? m?.start_reach ?? 0.5;
  const homeFor = (laneId: number) => m?.zipline_map?.home[String(laneId)]?.[side] ?? 0;
  const owned = useMemo(
    () =>
      new Map(
        lanes.map((l) => [l.id, ownedSection(side, Math.max(homeFor(l.id), reach[l.id] ?? startFor(l.id)))] as [number, [number, number]]),
      ),
    [lanes, side, reach, m],
  );
  // Every zipline stretch you can ride and where you can switch; rebuilt when ownership changes.
  const graph = useMemo(() => (d ? buildGraph(lanes, d.transform, owned, side) : null), [d, lanes, owned, side]);
  const verdict = useMemo(
    () => (d && graph && speeds && a && b ? compare(a, b, graph, d.transform, speeds) : null),
    [a, b, d, graph, speeds],
  );
  const grid = useMemo(() => {
    if (!d || !m || !graph || !speeds || !dest) return [];
    const field = towards(dest, graph, d.transform, speeds);
    const n = m.grid;
    return m.walkable.map(([i, j]) => ({ i, j, ...quickVerdict([(i + 0.5) / n, (j + 0.5) / n], graph, field, d.transform, speeds) }));
  }, [d, m, graph, speeds, dest]);

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
  const multiShare = grid.length ? grid.filter((c) => c.faster === "zip" && c.rides > 1).length / grid.length : 0;
  const color = (c: { faster: string; rides: number }) => (c.faster === "foot" ? FOOT : c.rides > 1 ? MULTI : ZIP);
  const rideLegs = verdict?.zip?.legs.filter((l): l is Extract<Leg, { kind: "ride" }> => l.kind === "ride") ?? [];
  const zipColor = rideLegs.length > 1 ? MULTI : ZIP;

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
            fill={color(c)}
            opacity={0.15 + 0.6 * Math.min(1, c.saving / MAX_SAVING_S)}
          />
        ))}
        <Lanes lanes={lanes} width={6} />
        {/* Grey out what you cannot ride (enemy or neutral); a team dot marks where yours ends. */}
        {lanes.map((l) => {
          const [f0, f1] = owned.get(l.id) ?? [0, 0];
          const L = laneLength(l, d.transform);
          const [g0, g1] = side === 0 ? [f1, 1] : [0, f0];
          const end = subpath(l.pts, (side === 0 ? f1 : f0) * L, (side === 0 ? f1 : f0) * L, d.transform)[0];
          return (
            <g key={`own${l.id}`}>
              {g1 > g0 && (
                <polyline
                  points={line(subpath(l.pts, g0 * L, g1 * L, d.transform))}
                  fill="none"
                  stroke={SURFACE}
                  strokeWidth={8}
                  strokeOpacity={0.85}
                  strokeDasharray="10 8"
                />
              )}
              {end && f1 > f0 && <circle cx={end[0] * S} cy={end[1] * S} r={10} fill={TEAM_COLORS[side]} stroke={INK} strokeWidth={3} />}
            </g>
          );
        })}
        {mode === "pair" && verdict && a && b && (
          <g>
            <line x1={a[0] * S} y1={a[1] * S} x2={b[0] * S} y2={b[1] * S} stroke={FOOT} strokeWidth={6} strokeDasharray="14 10" />
            {verdict.zip && (
              <g>
                {verdict.zip.legs.map((leg, k) =>
                  leg.kind === "walk" ? (
                    <polyline key={k} points={line([leg.from, leg.to])} fill="none" stroke={zipColor} strokeWidth={4} strokeDasharray="4 8" />
                  ) : (
                    <polyline key={k} points={line(leg.path)} fill="none" stroke={zipColor} strokeWidth={10} strokeLinecap="round" />
                  ),
                )}
                {/* Number each ride where you latch on. */}
                {rideLegs.map((leg, k) => (
                  <g key={`n${k}`}>
                    <circle cx={leg.path[0][0] * S} cy={leg.path[0][1] * S} r={15} fill={INK} stroke={SURFACE} strokeWidth={3} />
                    <text x={leg.path[0][0] * S} y={leg.path[0][1] * S} textAnchor="middle" dominantBaseline="central" fontSize={18} fontWeight={700} fill={SURFACE}>
                      {k + 1}
                    </text>
                  </g>
                ))}
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
              className={`rounded-xl border-2 px-4 py-2 font-bold ${mode === id ? "border-accent bg-panel2" : "border-line text-dim"}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          <div className="label">Your team</div>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Your team">
            {([0, 1] as Team[]).map((t) => (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={side === t}
                onClick={() => setTeam(t)}
                className={`rounded-xl border-2 px-4 py-2 font-bold ${side === t ? "bg-panel2" : "border-line text-dim"}`}
                style={side === t ? { borderColor: TEAM_COLORS[t] } : undefined}
              >
                <span style={{ color: TEAM_COLORS[t] }}>■</span> {d.teams[String(t)] ?? `Team ${t}`}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="label">Your zipline reaches</span>
            <span className="text-sm text-dim">share of each lane, from your base. Dashed: not yours.</span>
            <button type="button" className="chip ml-auto hover:border-accent" onClick={() => setReach({})}>
              Start of game
            </button>
          </div>
          {lanes.map((l) => {
            const home = homeFor(l.id);
            const r = Math.max(home, reach[l.id] ?? startFor(l.id));
            return (
              <label key={l.id} className="grid grid-cols-[6rem_1fr_3.5rem] items-center gap-3">
                <span className="font-bold">
                  <span style={{ color: l.color }}>━</span> {l.name}
                </span>
                <input
                  type="range"
                  min={Math.ceil(home * 100)}
                  max={Math.floor((1 - (m?.zipline_map?.home[String(l.id)]?.[1 - side] ?? 0)) * 100)}
                  value={Math.round(r * 100)}
                  onChange={(e) => setReach((x) => ({ ...x, [l.id]: Number(e.target.value) / 100 }))}
                  className="w-full accent-accent"
                  aria-label={`${l.name} zipline reach`}
                />
                <span className="tnum text-right">{Math.round(r * 100)}%</span>
              </label>
            );
          })}
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
              <option value="optimal">Optimal (your rank)</option>
              {m.high && <option value="high">Optimal (high rank)</option>}
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
                <div className="rounded-xl border-2 p-4" style={{ borderColor: verdict.faster === "foot" ? FOOT : zipColor }}>
                  <div className="label">Faster</div>
                  <div className="text-3xl font-bold">
                    {verdict.faster === "zip" ? rideLegs.map((l) => l.lane.name).join(" → ") : "On foot"}
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
                    <div className="label" style={{ color: zipColor }}>
                      ━ {rideLegs.length > 1 ? `${rideLegs.length} ziplines` : "Zipline"}
                    </div>
                    <div className="text-3xl font-bold tnum">{num(verdict.zip.total)} s</div>
                  </div>
                )}
              </div>
              {verdict.zip && (
                <div>
                  <div className="label">Zipline route, step by step</div>
                  <ol className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 tnum">
                    {verdict.zip.legs
                      .filter((leg) => leg.kind === "ride" || leg.seconds >= 0.5) // hide sub-second steps
                      .map((leg, k) => (
                      <li key={k} className="flex items-center gap-2">
                        {k > 0 && <span className="text-muted" aria-hidden>→</span>}
                        <span className={`chip ${leg.kind === "ride" ? "font-bold" : ""}`}>
                          {leg.kind === "ride"
                            ? `${rideLegs.indexOf(leg) + 1}. Ride ${leg.lane.name} ${leg.toward === "enemy" ? "toward the enemy" : leg.toward === "home" ? "toward your base" : ""} ${num(leg.seconds)} s`
                            : `Walk ${num(leg.seconds)} s`}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          ) : (
            <p className="text-dim">Click two spots on the map.</p>
          ))}

        {mode === "grid" &&
          (dest ? (
            <div className="space-y-2">
              <div className="flex gap-4 text-lg">
                <span>
                  <span style={{ color: ZIP }}>■</span> 1 zipline faster
                </span>
                <span>
                  <span style={{ color: MULTI }}>■</span> 2+ ziplines faster
                </span>
                <span>
                  <span style={{ color: FOOT }}>■</span> On foot faster
                </span>
              </div>
              <p className="text-dim">Brighter = more seconds saved.</p>
              <p className="text-xl">
                Ziplines win from <b className="tnum">{Math.round(zipShare * 100)}%</b> of the map.
                {multiShare > 0 && (
                  <>
                    {" "}
                    Switching ziplines wins from <b className="tnum">{Math.round(multiShare * 100)}%</b>.
                  </>
                )}
              </p>
            </div>
          ) : (
            <p className="text-dim">Click a destination on the map.</p>
          ))}

        <ul className="space-y-1 text-sm text-muted">
          <li>
            Times come from real trips across the map. Optimal = the fastest 15%: {num(m.progress_fast ?? 0)} u/s at your rank (
            {num(m.samples.route_trips)} trips)
            {m.high?.progress_fast && m.progress_fast
              ? `, ${num(m.high.progress_fast)} u/s at high rank (${num(m.high.samples.route_trips)} trips, badges ${m.high.badges?.[0]}–${m.high.badges?.[1]}): ${Math.round((m.high.progress_fast / m.progress_fast - 1) * 100)}% faster`
              : ""}
            . Normal = the median.
          </li>
          <li>
            Zipline {num(m.zip_speed)} u/s, plus ~{num(m.ride_overhead_s)} s per ride to get on (calibrated on real trips).
          </li>
          <li>
            You ride only your team's part of each zipline, both ways at the same speed. Each team keeps a home stretch nobody
            can capture{m.zipline_map ? ` (measured from replay ${m.zipline_map.match_id})` : ""}. Push a lane to extend yours.
          </li>
          <li>Zipline boost and blocked lanes are not modelled.</li>
          {m.switches.count > 0 && (
            <li>
              Players switch ziplines often: {num(m.switches.count)} switches seen, about {num(m.switches.gap_s ?? 0)} s apart.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
