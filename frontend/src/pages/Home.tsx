import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type TrendStatus } from "../lib/api";
import { ago, num } from "../lib/format";
import { ErrorBox, HeroIcon, Loading, ReadAloud, WinLoss } from "../components/ui";
import LessonLink from "../components/LessonLink";

export const STATUS: Record<TrendStatus, { icon: string; label: string; cls: string }> = {
  improving: { icon: "▲", label: "Improving", cls: "text-good border-good" },
  same: { icon: "→", label: "Same", cls: "text-dim border-line" },
  worse: { icon: "▼", label: "Worse", cls: "text-high border-high" },
  not_enough: { icon: "…", label: "Need more games", cls: "text-muted border-line" },
};

export default function Home() {
  const trends = useQuery({ queryKey: ["trends", 20], queryFn: () => api.trends(20) });
  const matches = useQuery({ queryKey: ["matches"], queryFn: () => api.matches() });
  const last = matches.data?.matches.find((m) => !m.street_brawl);

  return (
    <div className="space-y-6">
      {trends.isLoading ? (
        <Loading label="Checking your last 20 games… (first time takes a minute)" />
      ) : trends.error ? (
        <ErrorBox error={trends.error} />
      ) : (
        <FocusCard focus={trends.data!.focus} />
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="card space-y-4">
          <h2 className="label">Last match</h2>
          {matches.isLoading && <p className="text-dim">Loading…</p>}
          {matches.error && <ErrorBox error={matches.error} />}
          {last && (
            <>
              <div className="flex items-center gap-4">
                <HeroIcon hero={last.hero} size={64} />
                <div>
                  <div className="text-2xl font-bold">{last.hero.name}</div>
                  <div className="text-dim">{ago(last.start_time)}</div>
                </div>
                <div className="ml-auto">
                  <WinLoss won={last.won} />
                </div>
              </div>
              <div className="flex gap-6">
                <div>
                  <div className="label">K / D / A</div>
                  <div className="text-2xl font-bold tnum">
                    {last.kills} / {last.deaths} / {last.assists}
                  </div>
                </div>
                <div>
                  <div className="label">Souls / min</div>
                  <div className="text-2xl font-bold tnum">{num(last.souls_per_min)}</div>
                </div>
              </div>
              <Link to={`/matches/${last.match_id}`} className="btn-primary">
                🔎 Review this match
              </Link>
            </>
          )}
        </div>

        <div className="card space-y-3">
          <h2 className="label">Go to</h2>
          <Link to="/matches" className="btn w-full justify-start">
            ▤ All matches
          </Link>
          <Link to="/trends" className="btn w-full justify-start">
            ↗ Habit trends
          </Link>
          <Link to="/learn" className="btn w-full justify-start">
            📚 Lessons
          </Link>
          <Link to="/settings" className="btn w-full justify-start">
            ⚙ Settings
          </Link>
        </div>
      </div>
    </div>
  );
}

function FocusCard({ focus }: { focus: NonNullable<Awaited<ReturnType<typeof api.trends>>["focus"]> | null }) {
  if (!focus) {
    return (
      <div className="card border-good">
        <div className="label">Next game focus</div>
        <p className="text-3xl font-bold text-good mt-2">✓ No repeat problems found.</p>
        <p className="text-dim mt-1">Keep playing. We check again after each game.</p>
      </div>
    );
  }
  const s = STATUS[focus.status];
  return (
    <div className="card border-2 border-s1 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="label text-s1">🎯 Next game focus</span>
        <span className={`chip font-bold ${s.cls}`}>
          {s.icon} {s.label}
        </span>
        <span className="ml-auto">
          <ReadAloud text={`Next game focus: ${focus.habit}. ${focus.do_next}`} />
        </span>
      </div>
      <h1 className="text-5xl font-bold leading-tight">{focus.habit}</h1>
      <p className="text-2xl">{focus.do_next}</p>
      <p className="text-dim">
        <b className="text-ink text-xl">
          {focus.hits} of {focus.games}
        </b>{" "}
        recent games had this problem.
      </p>
      <LessonLink id={focus.lesson_id} big />
    </div>
  );
}
