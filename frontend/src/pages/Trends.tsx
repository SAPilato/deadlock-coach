import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Severity } from "../lib/api";
import { ErrorBox, EstTag, Loading, More } from "../components/ui";
import { STATUS } from "./Home";

const DOT: Record<Severity, { color: string; icon: string }> = {
  high: { color: "#d03b3b", icon: "▲" },
  med: { color: "#ec835a", icon: "■" },
  low: { color: "#fab219", icon: "●" },
};

export default function Trends() {
  const q = useQuery({ queryKey: ["trends", 20], queryFn: () => api.trends(20) });
  if (q.isLoading) return <Loading label="Checking your last 20 games… (first time takes a minute)" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const t = q.data!;
  const order = { worse: 0, same: 1, not_enough: 2, improving: 3 };
  const habits = [...t.habits].sort((a, b) => order[a.status] - order[b.status] || b.recent_hits - a.recent_hits);
  const oldestFirst = [...t.matches].reverse();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">↗ Habit trends</h1>
        <span className="chip">{t.matches.length} games</span>
        <span className="text-dim">
          Last {t.recent_n} vs the {t.previous_n} before
          <EstTag title="Improving/worse means a change of 20+ points in how often the habit shows up." />
        </span>
      </div>
      {t.matches.length < 8 && (
        <p className="card text-dim">⏳ Trends need 8+ reviewed games. Play more, or check your Steam ID.</p>
      )}

      <div className="flex flex-wrap gap-4 text-sm text-dim">
        <span>Dots: oldest → newest game</span>
        {(Object.keys(DOT) as Severity[]).map((s) => (
          <span key={s}>
            <span style={{ color: DOT[s].color }}>{DOT[s].icon}</span> {s === "med" ? "Medium" : s === "high" ? "High" : "Low"}
          </span>
        ))}
        <span>○ Fine</span>
      </div>

      <ul className="space-y-3">
        {habits.map((h) => {
          const s = STATUS[h.status];
          const byMatch = new Map(h.per_match.map((p) => [p.match_id, p]));
          return (
            <li key={h.rule_id} className="card space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-bold">{h.habit}</h2>
                <span className={`chip font-bold ${s.cls}`}>
                  {s.icon} {s.label}
                </span>
                <span className="ml-auto text-dim">
                  <b className="text-ink text-lg">
                    {h.recent_hits} of {h.recent_games}
                  </b>{" "}
                  recent games
                </span>
              </div>
              <div className="flex flex-wrap gap-1" aria-label={`${h.habit} per game, oldest first`}>
                {oldestFirst.map((m) => {
                  const p = byMatch.get(m.match_id);
                  const sev = p?.severity;
                  return (
                    <Link
                      key={m.match_id}
                      to={`/matches/${m.match_id}`}
                      title={sev ? `${sev} in this game` : p?.ran ? "Fine in this game" : "Not checked"}
                      className="grid h-8 w-8 place-items-center rounded-lg bg-panel2 border border-line hover:border-s1"
                      style={{ color: sev ? DOT[sev].color : "#9a9890" }}
                    >
                      {sev ? DOT[sev].icon : p?.ran ? "○" : "·"}
                    </Link>
                  );
                })}
              </div>
              <More label="How to fix">
                <p className="rounded-xl bg-panel2 border-l-4 border-s1 px-4 py-2">
                  <b className="text-s1">🎯 Next game: </b>
                  {h.do_next}
                </p>
              </More>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
