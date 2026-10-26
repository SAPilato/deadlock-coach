import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Lesson, type Trends } from "../lib/api";
import { habitFor } from "../lib/learn";
import { useLessons } from "../components/LessonLink";
import { ErrorBox, EstTag, Loading, ReadAloud } from "../components/ui";
import { STATUS } from "./Home";
import { TOPIC } from "./Learn";

const SOURCE: Record<Lesson["facts"][number]["source"], string> = {
  "game data": "Read from the game's own data files.",
  measured: "Measured from real match paths.",
  replay: "Seen in a parsed replay from the current map.",
};

export default function LessonPage() {
  const { id } = useParams();
  const lessons = useLessons();
  const trends = useQuery({ queryKey: ["trends", 20], queryFn: () => api.trends(20) });
  useEffect(() => window.scrollTo(0, 0), [id]);

  if (lessons.isLoading) return <Loading label="Loading lesson…" />;
  if (lessons.error) return <ErrorBox error={lessons.error} />;
  const all = lessons.data!;
  const i = all.findIndex((l) => l.id === id);
  if (i < 0) {
    return (
      <div className="card space-y-3">
        <p className="text-xl font-bold">Lesson not found.</p>
        <Link to="/learn" className="btn">
          ← All lessons
        </Link>
      </div>
    );
  }
  const l = all[i];
  const next = all[(i + 1) % all.length];
  const habit = habitFor(l.id, trends.data);

  return (
    <div className="space-y-6">
      <Link to="/learn" className="font-bold text-s1 hover:underline">
        ← All lessons
      </Link>
      <header className="flex flex-wrap items-center gap-4">
        <span className="text-6xl" aria-hidden>
          {l.icon}
        </span>
        <div>
          <div className="label">
            {TOPIC[l.topic]} {l.topic}
          </div>
          <h1 className="text-4xl font-bold">{l.title}</h1>
        </div>
        <span className="ml-auto">
          <ReadAloud text={`${l.title}. ${l.summary} ${l.points.join(" ")}`} />
        </span>
      </header>
      <p className="text-2xl">{l.summary}</p>

      {habit && <YourGames habit={habit} />}

      <div className="grid gap-6 md:grid-cols-2">
        <section className="card space-y-4">
          <h2 className="label">How to do it</h2>
          <ol className="space-y-4">
            {l.points.map((p, n) => (
              <li key={p} className="flex gap-3 text-xl">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-s1 font-bold text-white" aria-hidden>
                  {n + 1}
                </span>
                <span className="pt-1">{p}</span>
              </li>
            ))}
          </ol>
        </section>
        {l.facts.length > 0 && (
          <section className="card space-y-4">
            <h2 className="label">📊 From the game</h2>
            <ul className="space-y-4">
              {l.facts.map((f) => (
                <li key={f.text} className="text-xl">
                  {f.text}
                  <span
                    title={SOURCE[f.source]}
                    className="ml-2 inline-block rounded-md border border-line px-1.5 align-middle text-xs text-muted"
                  >
                    {f.source}
                  </span>
                  {f.source === "measured" && <EstTag title="Measured from real matches. An average, not a game rule." />}
                </li>
              ))}
            </ul>
            <p className="text-sm text-muted">Numbers update with each patch.</p>
          </section>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Link to={l.try.href} className="btn-primary px-6 py-3 text-xl">
          ▶ {l.try.label}
        </Link>
        <Link to={`/learn/${next.id}`} className="btn ml-auto">
          Next: <span aria-hidden>{next.icon}</span> {next.title} →
        </Link>
      </div>
    </div>
  );
}

function YourGames({ habit }: { habit: Trends["habits"][number] }) {
  const s = STATUS[habit.status];
  const clean = habit.recent_hits === 0;
  return (
    <section className={`card space-y-3 border-2 ${clean ? "border-good" : "border-s1"}`}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="label">Your games · {habit.habit}</h2>
        <span className={`chip font-bold ${s.cls}`}>
          {s.icon} {s.label}
        </span>
      </div>
      <p className="text-dim">
        <b className={`text-3xl tnum ${clean ? "text-good" : "text-ink"}`}>
          {habit.recent_hits} of {habit.recent_games}
        </b>{" "}
        recent games had this problem.
      </p>
      {clean ? (
        <p className="font-bold text-good">✓ Clean lately. Keep it up.</p>
      ) : (
        <p className="rounded-xl border-l-4 border-s1 bg-panel2 px-4 py-2">
          <b className="text-s1">🎯 Next game: </b>
          {habit.do_next}
        </p>
      )}
      <Link to="/trends" className="font-bold text-s1 hover:underline">
        See it per game →
      </Link>
    </section>
  );
}
