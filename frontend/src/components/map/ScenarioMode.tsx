import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type ScenarioRow } from "../../lib/api";
import { ago, clock, signed } from "../../lib/format";
import { ErrorBox, HeroIcon, Loading, ReadAloud } from "../ui";
import MapCanvas, { Glyph, Lanes, S, SURFACE, TEAM_COLORS } from "./MapCanvas";

const ME = "#ffffff";

export default function ScenarioMode() {
  const list = useQuery({ queryKey: ["macro-scenarios"], queryFn: api.macroScenarios });
  const [pick, setPick] = useState<ScenarioRow | null>(null);

  if (list.isLoading) return <Loading label="Finding moments from your games…" />;
  if (list.error) return <ErrorBox error={list.error} />;
  if (!list.data?.length) return <p className="card text-dim">No moments yet. Play a few games first.</p>;
  if (pick) return <Play row={pick} onBack={() => setPick(null)} />;

  return (
    <div className="space-y-3">
      <p className="text-lg">Real moments from your games, 20 seconds before a key event.</p>
      <ul className="grid gap-3 md:grid-cols-2">
        {list.data.map((r) => (
          <li key={`${r.match_id}-${r.t}`}>
            <button type="button" onClick={() => setPick(r)} className="card flex w-full items-center gap-4 text-left hover:border-s1">
              <HeroIcon hero={r.hero} size={48} />
              <div className="min-w-0">
                <div className="text-lg font-bold">{r.label}</div>
                <div className="text-dim">
                  {clock(r.t)} · {r.hero.name} · {ago(r.start_time)}
                </div>
                {r.habit && <span className="chip mt-1 text-sm">{r.habit}</span>}
              </div>
              <span className="ml-auto font-bold text-s1">Play ▶</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Play({ row, onBack }: { row: ScenarioRow; onBack: () => void }) {
  const q = useQuery({ queryKey: ["macro-scenario", row.match_id, row.t], queryFn: () => api.macroScenario(row.match_id, row.t) });
  const layers = useQuery({ queryKey: ["macro-layers"], queryFn: api.macroLayers, staleTime: Infinity });
  const [choice, setChoice] = useState<string | null>(null);
  const [frame, setFrame] = useState(0);
  const total = q.data?.frames.length ?? 0;

  useEffect(() => {
    if (!choice || frame >= total - 1) return;
    const id = window.setTimeout(() => setFrame((f) => f + 1), 300);
    return () => window.clearTimeout(id);
  }, [choice, frame, total]);

  if (q.isLoading) return <Loading label="Setting up the moment…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const s = q.data!;
  const f = s.frames[Math.min(frame, total - 1)];
  const sides = new Map(s.players.map((p) => [p.slot, p]));
  const diff = s.souls.you - s.souls.them;
  const lanes = layers.data?.layers.find((l) => l.id === "lanes")?.lines ?? [];
  const chosen = s.options.find((o) => o.id === choice);
  const events = s.events.filter((e) => e.t <= f.t);

  return (
    <div className="space-y-4">
      <button type="button" className="text-s1 font-bold hover:underline" onClick={onBack}>
        ← All moments
      </button>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,680px)_1fr]">
        <MapCanvas image={layers.data?.image} caption="You: white ring. Blue: your team. Orange: enemies.">
          <Lanes lanes={lanes} width={4} />
          {s.objectives.map((o, i) => (
            <Glyph
              key={i}
              left={o.left}
              top={o.top}
              ch={o.kind === "tier1" ? "▲" : o.kind === "tier2" ? "■" : "★"}
              color={o.alive ? (o.ally ? TEAM_COLORS[0] : TEAM_COLORS[1]) : "#55555a"}
              size={24}
            />
          ))}
          {f.pos.map((p) => {
            const who = sides.get(p.slot);
            const color = who?.side === "enemy" ? TEAM_COLORS[1] : TEAM_COLORS[0];
            const me = who?.side === "me";
            return p.alive ? (
              <circle key={p.slot} cx={p.left * S} cy={p.top * S} r={me ? 17 : 13} fill={color} stroke={me ? ME : SURFACE} strokeWidth={me ? 6 : 3}>
                <title>{me ? "You" : who?.hero}</title>
              </circle>
            ) : (
              <text key={p.slot} x={p.left * S} y={p.top * S} textAnchor="middle" dominantBaseline="central" fontSize={26} fill={color} stroke={SURFACE} strokeWidth={5} paintOrder="stroke">
                ✕
              </text>
            );
          })}
        </MapCanvas>

        <div className="space-y-4">
          <div className="flex flex-wrap gap-6">
            <div>
              <div className="label">Time</div>
              <div className="text-4xl font-bold tnum">{clock(f.t)}</div>
            </div>
            <div>
              <div className="label">Team souls</div>
              <div className={`text-4xl font-bold tnum ${diff >= 0 ? "text-good" : "text-high"}`}>{signed(diff)}</div>
            </div>
          </div>
          <p className="text-dim">You are playing {s.hero}.</p>

          {!chosen ? (
            <div className="space-y-2">
              <h3 className="text-2xl font-bold">What would you do?</h3>
              {s.options.map((o) => (
                <button key={o.id} type="button" className="btn w-full justify-start text-lg" onClick={() => setChoice(o.id)}>
                  {o.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-xl bg-panel2 border border-line p-4 space-y-1">
                <div>
                  You picked: <b>{chosen.label}</b>
                </div>
                <div>
                  In the game you: <b className={s.did.id === choice ? "text-good" : "text-low"}>{s.did.label}</b>
                </div>
              </div>
              <div>
                <h4 className="label mb-1">What happened next</h4>
                {events.length === 0 ? (
                  <p className="text-dim">{frame >= total - 1 ? "Nothing big in the next 40 s." : "Watching…"}</p>
                ) : (
                  <ul className="space-y-1">
                    {events.map((e, i) => (
                      <li key={i}>
                        <span className="tnum text-dim">{clock(e.t)}</span>{" "}
                        <b className={e.side === "enemy" ? "text-good" : "text-high"}>{e.text}</b>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {s.finding && (
                <div className="rounded-xl border-l-4 border-s1 bg-panel2 px-4 py-3">
                  <div className="label">{s.finding.habit}</div>
                  <div className="font-bold">{s.finding.headline}</div>
                  <div>
                    <b className="text-s1">🎯 Next game: </b>
                    {s.finding.do_next}
                  </div>
                  <div className="mt-2">
                    <ReadAloud text={`${s.finding.headline} Next game: ${s.finding.do_next}`} />
                  </div>
                </div>
              )}
              <div className="flex gap-2">
                <button type="button" className="btn" onClick={() => setFrame(0)}>
                  ↺ Replay
                </button>
                <button type="button" className="btn" onClick={() => { setChoice(null); setFrame(0); }}>
                  Try again
                </button>
              </div>
              <p className="text-sm text-muted">There is no single right answer. Compare your pick with what happened.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
