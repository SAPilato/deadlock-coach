import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CableCar, Check, Skull, Waves } from "lucide-react";
import { api, type Paths, type Report, type TimelineEvent } from "../lib/api";
import { clock } from "../lib/format";
import Minimap, { type LaneSection, type Marker, type WaveDot } from "./Minimap";
import SoulsChart from "./SoulsChart";
import { useThemeColors } from "../lib/theme";
import { EstTag, Icon } from "./ui";

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
  const live = paths.data ? liveStatus(paths.data, t) : [];
  if (paths.data) {
    const idx = Math.min(Math.round(t / paths.data.step), paths.data.players[0]?.pts.length - 1);
    for (const { p, dead, lane } of live) {
      const pt = p.pts[Math.max(0, idx)];
      if (!pt) continue;
      markers.push({
        key: `p${p.slot}`,
        left: pt[0],
        top: pt[1],
        color: p.ally ? ALLY : ENEMY,
        label: `${p.is_me ? "You" : p.name}${dead ? " (dead)" : lane ? ` (on the ${lane.name} zipline)` : ""}`,
        shape: dead ? "x" : "dot",
        emphasis: p.is_me,
        size: p.is_me ? 24 : 26,
        image: p.image,
        zipline: lane?.color ?? null,
      });
    }
  }
  const me = paths.data?.players.find((p) => p.is_me);
  const laneOf = new Map((paths.data?.lanes ?? []).map((l) => [l.id, l]));
  const myZipSeconds = me ? me.zip.reduce((sum, [a, b]) => sum + (b - a), 0) : 0;
  const control = paths.data && me ? zipControl(paths.data, me.team, t) : [];
  // Trooper waves from the parsed replay, on demand.
  const [showWaves, setShowWaves] = useState(false);
  const waves = useQuery({
    queryKey: ["waves", report.match.id],
    queryFn: () => api.macroWaves(report.match.id),
    enabled: showWaves && !!paths.data?.has_waves,
    staleTime: Infinity,
  });
  const waveDots: WaveDot[] = [];
  if (showWaves && waves.data?.frames.length && me) {
    const w = waves.data;
    const frame = w.frames[Math.min(w.frames.length - 1, Math.max(0, Math.round(t / w.step)))];
    for (const [laneId, lane] of Object.entries(frame.lanes)) {
      for (const [team, at, n] of lane.w) {
        waveDots.push({ laneId: Number(laneId), at, troopers: n, color: team === me.team ? ALLY : ENEMY });
      }
    }
  }
  // Each side's part of every zipline, painted from its own base (lanes run from team 0's base).
  const sections: LaneSection[] = control.flatMap((c) => {
    const [r0, r1] = me!.team === 0 ? [c.mine, c.theirs] : [c.theirs, c.mine];
    const [c0, c1] = me!.team === 0 ? [ALLY, ENEMY] : [ENEMY, ALLY];
    return [
      { laneId: c.lane.id, from: 0, to: r0, color: c0 },
      { laneId: c.lane.id, from: 1 - r1, to: 1, color: c1 },
    ];
  });

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
          {me && (
            <div className="grid grid-cols-[6.5rem_1fr] items-center gap-2">
              <span className="text-sm text-muted">Your ziplines</span>
              <div className="relative h-8 overflow-hidden rounded-lg bg-panel2 border border-line">
                {me.zip.map(([a, b, laneId], i) => {
                  const lane = laneOf.get(laneId);
                  const label = `${clock(a)} ${lane?.name ?? ""} zipline, ${b - a} s`;
                  return (
                    <button
                      key={`z${i}`}
                      type="button"
                      title={label}
                      aria-label={label}
                      onClick={() => setTime(a)}
                      className="absolute top-1.5 bottom-1.5 rounded-sm hover:brightness-125"
                      style={{ left: `${(a / duration) * 100}%`, width: `${Math.max(0.4, ((b - a) / duration) * 100)}%`, background: lane?.color }}
                    />
                  );
                })}
                <span className="absolute top-0 h-full w-0.5 bg-ink" style={{ left: `${(t / duration) * 100}%` }} aria-hidden />
              </div>
            </div>
          )}
        </div>
        {me && (
          <p className="text-sm text-dim">
            <Icon icon={CableCar} /> You rode ziplines <b className="text-ink tnum">{me.zip.length}</b> times,{" "}
            <b className="text-ink tnum">{Math.round(myZipSeconds / 60)} min</b> in total. Bar colour = lane.
          </p>
        )}

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
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-dim mb-2">
          <span><span style={{ color: ALLY }}>◯</span> Your team</span>
          <span><span style={{ color: ENEMY }}>◯</span> Enemies</span>
          <span>White ring: you</span>
          <span><Icon icon={CableCar} /> On a zipline</span>
          <span>Faded ✕: dead</span>
        </div>
        <label className={`mb-2 inline-flex items-center gap-2 ${paths.data?.has_waves ? "" : "text-muted"}`}>
          <input
            type="checkbox"
            className="h-5 w-5 accent-accent"
            checked={showWaves}
            disabled={!paths.data?.has_waves}
            onChange={(e) => setShowWaves(e.target.checked)}
          />
          <Icon icon={Waves} /> Show trooper waves
          {!paths.data?.has_waves && (
            <a href="#replay" className="text-sm text-accent hover:underline">
              needs the replay file
            </a>
          )}
          {showWaves && waves.isLoading && <span className="text-sm text-dim">loading…</span>}
        </label>
        <Minimap
          map={report.map}
          markers={markers}
          sections={sections}
          waves={waveDots}
          caption={`Positions at ${clock(t)}. Hover a hero for their name.${waveDots.length ? " Dots on lanes: waves (bigger = more troopers)." : ""}`}
        />
        {control.length > 0 && <ZipControl control={control} t={t} exact={paths.data?.reach_source === "replay"} />}
        {paths.data && <LiveList live={live} t={t} />}
      </div>
    </div>
  );
}

type PathPlayer = Paths["players"][number];
interface Live {
  p: PathPlayer;
  dead: [number, number] | undefined;
  lane: Paths["lanes"][number] | undefined;
}

/** Who is dead or riding a zipline at second t. Rides are exact to the second. */
function liveStatus(paths: Paths, t: number): Live[] {
  const laneOf = new Map(paths.lanes.map((l) => [l.id, l]));
  return paths.players.map((p) => {
    const dead = p.dead.find(([a, b]) => a <= t && t < b);
    const ride = dead ? undefined : p.zip.find(([a, b]) => a <= t && t < b);
    return { p, dead, lane: ride ? laneOf.get(ride[2]) : undefined };
  });
}

function LiveList({ live, t }: { live: Live[]; t: number }) {
  const riding = live.filter((l) => l.lane).length;
  const dead = live.filter((l) => l.dead).length;
  return (
    <div className="mt-4 space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h4 className="label">Live at {clock(t)}</h4>
        <span className="text-sm text-dim">
          <b className="text-ink tnum">{riding}</b> on ziplines · <b className="text-ink tnum">{dead}</b> dead
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {[true, false].map((ally) => (
          <ul key={String(ally)} className="space-y-1" aria-label={ally ? "Your team" : "Enemies"}>
            {live
              .filter((l) => l.p.ally === ally)
              .map(({ p, dead, lane }) => (
                <li key={p.slot} className="flex min-w-0 items-center gap-2">
                  {p.image && (
                    <img
                      src={p.image}
                      alt=""
                      className={`h-7 w-7 shrink-0 rounded-full border-2 object-cover ${dead ? "opacity-40" : ""}`}
                      style={{ borderColor: ally ? ALLY : ENEMY }}
                    />
                  )}
                  <span className={`truncate ${p.is_me ? "font-bold" : ""}`}>{p.is_me ? "You" : p.name}</span>
                  {lane && (
                    <span className="chip shrink-0 py-0 text-xs" style={{ borderColor: lane.color }}>
                      <Icon icon={CableCar} /> {lane.name}
                    </span>
                  )}
                  {dead && (
                    <span className="chip shrink-0 py-0 text-xs text-high">
                      <Icon icon={Skull} /> {Math.max(0, dead[1] - t)} s
                    </span>
                  )}
                </li>
              ))}
          </ul>
        ))}
      </div>
    </div>
  );
}

interface Control {
  lane: Paths["lanes"][number];
  mine: number; // share of the lane's zipline your team owns, from your base
  theirs: number;
}

/** Each lane's zipline split at second t, from the reach timeline. */
function zipControl(paths: Paths, myTeam: number, t: number): Control[] {
  return paths.lanes.flatMap((lane) => {
    const rows = paths.reach[String(lane.id)];
    if (!rows?.length) return [];
    let cur = rows[0];
    for (const r of rows) {
      if (r[0] > t) break;
      cur = r;
    }
    const [r0, r1] = [cur[1], cur[2]];
    return [{ lane, mine: myTeam === 0 ? r0 : r1, theirs: myTeam === 0 ? r1 : r0 }];
  });
}

function ZipControl({ control, t, exact }: { control: Control[]; t: number; exact: boolean }) {
  return (
    <div className="mt-4 space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h4 className="label">
          <Icon icon={CableCar} /> Zipline control at {clock(t)}
        </h4>
        {exact ? (
          <span className="chip border-good py-0 text-sm text-good">
            <Icon icon={Check} /> Exact, from the replay
          </span>
        ) : (
          <span className="text-sm text-dim">
            From riders, about ±8% of the lane.
            <EstTag title="A team owns at least as far as one of its players rode. Checked against 2 replays." />{" "}
            <a href="#replay" className="text-accent hover:underline">
              Load the replay for exact
            </a>
          </span>
        )}
      </div>
      <ul className="space-y-1">
        {control.map(({ lane, mine, theirs }) => (
          <li key={lane.id} className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
            <span className="text-sm font-bold">
              <span style={{ color: lane.color }}>━</span> {lane.name}
            </span>
            <div
              className="flex h-6 overflow-hidden rounded-md border border-line bg-panel2 text-xs font-bold tnum"
              role="img"
              aria-label={`${lane.name}: your team ${Math.round(mine * 100)}%, enemy ${Math.round(theirs * 100)}%`}
            >
              <span className="grid place-items-center text-[#0e1014]" style={{ width: `${mine * 100}%`, background: ALLY }}>
                {Math.round(mine * 100)}%
              </span>
              <span className="flex-1" />
              <span className="grid place-items-center text-[#0e1014]" style={{ width: `${theirs * 100}%`, background: ENEMY }}>
                {Math.round(theirs * 100)}%
              </span>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">Your base on the left. The gap: {exact ? "neutral, nobody owns it yet." : "no rider seen there yet."}</p>
    </div>
  );
}
