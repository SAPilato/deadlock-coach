import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type WavesData } from "../../lib/api";
import { ago, clock } from "../../lib/format";
import { pointAt } from "../../lib/geo";
import { ErrorBox, HeroIcon, Icon, Loading } from "../ui";
import MapCanvas, { Lanes, S, SURFACE, TEAM_COLORS } from "./MapCanvas";
import { Pause, Play } from "lucide-react";

const MID = 0.05; // within 5% of the lane's middle counts as "middle"

function nextWave(t: number, s: WavesData["schedule"]): number | null {
  if (!s) return null;
  let spawn = s.first;
  while (spawn <= t) {
    const minute = spawn / 60;
    spawn += minute >= s.very_late_after_min ? s.very_late_every : minute >= s.late_after_min ? s.late_every : s.every;
  }
  return spawn - t;
}

/** Whose side of the lane the meeting point is on (s is 0 at team 0's base). */
function side(s: number): 0 | 1 | null {
  return s < 0.5 - MID ? 0 : s > 0.5 + MID ? 1 : null;
}

export default function WavesMode() {
  const [matchId, setMatchId] = useState<number | undefined>(undefined);
  const q = useQuery({ queryKey: ["macro-waves", matchId], queryFn: () => api.macroWaves(matchId) });
  const layers = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const [t, setT] = useState(180);
  const [playing, setPlaying] = useState(false);

  const d = q.data;
  const end = d?.frames.length ? d.frames[d.frames.length - 1].t : 0;
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setT((x) => (x + (d?.step ?? 3) > end ? end : x + (d?.step ?? 3))), 150);
    return () => window.clearInterval(id);
  }, [playing, d?.step, end]);
  useEffect(() => {
    if (t >= end && playing) setPlaying(false);
  }, [t, end, playing]);

  const frame = useMemo(() => {
    if (!d?.frames.length) return null;
    const i = Math.min(d.frames.length - 1, Math.max(0, Math.round(t / d.step)));
    return d.frames[i];
  }, [d, t]);

  if (q.isLoading) return <Loading label="Loading wave data…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  if (!d || !d.frames.length) {
    return <p className="card text-dim">No wave data yet. Load a replay on any match report.</p>;
  }
  const teamName = (team: number) => d.teams[String(team)] ?? `Team ${team}`;
  const describe = (s: number | undefined) => {
    if (s == null) return "No contact";
    const sd = side(s);
    if (sd == null) return "Middle";
    const pct = Math.round((sd === 0 ? 1 - s : s) * 100);
    if (d.my_team != null) return sd === d.my_team ? `Your side (${pct}%)` : `Their side (${pct}%)`;
    return `${teamName(sd)} side (${pct}%)`;
  };
  const minute = Math.round(t / 60);
  const meetNow = d.meets.find((m) => m.minute === minute);
  const chosen = d.available.find((a) => a.match_id === d.match_id);
  const next = nextWave(t, d.schedule);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,680px)_1fr]">
      <div className="space-y-3">
        <MapCanvas image={layers.data?.image} caption="Each dot is a wave. Bigger = more troopers. ✕ = waves meeting.">
          <Lanes lanes={d.lanes} width={10} />
          {frame &&
            d.lanes.map((lane) => {
              const fl = frame.lanes[String(lane.id)];
              if (!fl) return null;
              return (
                <g key={lane.id}>
                  {fl.w.map(([team, s, n], i) => {
                    const [x, y] = pointAt(lane.pts, s);
                    return (
                      <circle key={i} cx={x * S} cy={y * S} r={9 + 5 * Math.sqrt(n)} fill={TEAM_COLORS[team]} stroke={SURFACE} strokeWidth={3}>
                        <title>{`${teamName(team)}: ${n} troopers`}</title>
                      </circle>
                    );
                  })}
                  {fl.c != null &&
                    (() => {
                      const [x, y] = pointAt(lane.pts, fl.c);
                      return (
                        <text x={x * S} y={y * S} textAnchor="middle" dominantBaseline="central" fontSize={34} fontWeight={700} fill="#ffffff" stroke={SURFACE} strokeWidth={6} paintOrder="stroke">
                          ✕
                        </text>
                      );
                    })()}
                </g>
              );
            })}
        </MapCanvas>
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn-primary" onClick={() => setPlaying(!playing)} aria-pressed={playing}>
            {playing ? (
            <>
              <Icon icon={Pause} /> Pause
            </>
          ) : (
            <>
              <Icon icon={Play} /> Play
            </>
          )}
          </button>
          <span className="text-3xl font-bold tnum">{clock(t)}</span>
          {next != null && <span className="chip">Next wave in {Math.round(next)} s</span>}
        </div>
        <input
          type="range"
          min={0}
          max={end}
          step={d.step}
          value={t}
          onChange={(e) => setT(Number(e.target.value))}
          className="w-full accent-accent"
          aria-label="Match time"
        />
      </div>

      <div className="space-y-5">
        <label className="block">
          <span className="label">Replay</span>
          <select
            value={d.match_id}
            onChange={(e) => setMatchId(Number(e.target.value))}
            className="mt-1 w-full rounded-lg bg-panel2 border border-line px-3 py-2"
          >
            {d.available.map((a) => (
              <option key={a.match_id} value={a.match_id}>
                {a.sample ? "Sample · " : ""}
                {a.hero?.name ?? "Match"} · {a.start_time ? ago(a.start_time) : a.match_id}
              </option>
            ))}
          </select>
        </label>
        {chosen?.hero && (
          <p className="flex items-center gap-2 text-dim">
            <HeroIcon hero={chosen.hero} size={32} /> {chosen.sample ? "A sample player's match." : "Your match."}
            {chosen.team != null && <> Team: {teamName(chosen.team)}.</>}
          </p>
        )}

        <div>
          <h3 className="label mb-2">Where waves meet at {minute}:00</h3>
          <ul className="space-y-1 text-lg">
            {d.lanes.map((l) => (
              <li key={l.id} className="flex justify-between gap-3">
                <span>
                  <span style={{ color: l.color }}>●</span> {l.name}
                </span>
                <b>{describe(meetNow?.lanes[String(l.id)])}</b>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="label mb-2">Every minute</h3>
          <div className="overflow-x-auto">
            <table className="text-xs">
              <tbody>
                {d.lanes.map((l) => (
                  <tr key={l.id}>
                    <th className="pr-2 text-left font-normal text-dim">{l.name}</th>
                    {d.meets.map((m) => {
                      const s = m.lanes[String(l.id)];
                      const sd = s == null ? undefined : side(s);
                      const bg = sd == null ? (s == null ? "transparent" : "#5a5a55") : TEAM_COLORS[sd];
                      return (
                        <td key={m.minute} className="p-0">
                          <button
                            type="button"
                            title={`${m.minute}:00 · ${describe(s)}`}
                            onClick={() => setT(m.minute * 60)}
                            className={`block h-5 w-3 border ${m.minute === minute ? "border-ink" : "border-bg"}`}
                            style={{ background: bg }}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-sm text-dim">
            <span style={{ color: TEAM_COLORS[0] }}>■</span> on {teamName(0)} side · <span style={{ color: TEAM_COLORS[1] }}>■</span> on{" "}
            {teamName(1)} side · <span style={{ color: "#5a5a55" }}>■</span> middle
          </p>
        </div>
        {d.schedule && (
          <p className="text-sm text-muted">
            Game data: first wave at {d.schedule.first} s, then every {d.schedule.every} s. Every {d.schedule.late_every} s after{" "}
            {d.schedule.late_after_min} min.
          </p>
        )}
      </div>
    </div>
  );
}
