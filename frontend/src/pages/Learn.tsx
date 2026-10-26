import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Lesson, type LessonTopic } from "../lib/api";
import { suggestLessons, type Suggestion } from "../lib/learn";
import { useLessons } from "../components/LessonLink";
import { ErrorBox, Loading } from "../components/ui";
import { STATUS } from "./Home";

export const TOPIC: Record<LessonTopic, string> = { Lane: "🌊", Map: "🗺", Fights: "⚔", Items: "🛒" };

export default function Learn() {
  const lessons = useLessons();
  const trends = useQuery({ queryKey: ["trends", 20], queryFn: () => api.trends(20) });
  if (lessons.isLoading) return <Loading label="Loading lessons…" />;
  if (lessons.error) return <ErrorBox error={lessons.error} />;
  const all = lessons.data!;
  const picks = suggestLessons(all, trends.data);
  const topics = [...new Set(all.map((l) => l.topic))];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">📚 Learn</h1>
        <span className="text-dim">Short lessons. Each one opens a map or Build Lab view.</span>
      </div>

      <section className="space-y-3" aria-labelledby="for-you">
        <h2 id="for-you" className="text-2xl font-bold">
          🎯 For you
        </h2>
        {trends.isLoading ? (
          <Loading label="Checking your last 20 games…" />
        ) : trends.error ? (
          <p className="card text-dim">Could not check your games. All lessons are below.</p>
        ) : picks.length === 0 ? (
          <p className="card border-good text-xl font-bold text-good">✓ No repeat problems. Pick any lesson below.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {picks.map((s) => (
              <SuggestCard key={s.lesson.id} s={s} />
            ))}
          </div>
        )}
      </section>

      {topics.map((t) => (
        <section key={t} className="space-y-3">
          <h2 className="text-2xl font-bold">
            <span aria-hidden>{TOPIC[t]}</span> {t}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {all
              .filter((l) => l.topic === t)
              .map((l) => (
                <LessonCard key={l.id} lesson={l} />
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function SuggestCard({ s }: { s: Suggestion }) {
  const st = STATUS[s.status];
  return (
    <Link
      to={`/learn/${s.lesson.id}`}
      className={`card block space-y-2 hover:border-s1 ${s.focus ? "border-2 border-s1" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-3xl" aria-hidden>
          {s.lesson.icon}
        </span>
        {s.focus && <span className="chip border-s1 font-bold text-s1">🎯 Your focus</span>}
        <span className={`chip ml-auto font-bold ${st.cls}`}>
          {st.icon} {st.label}
        </span>
      </div>
      <p className="text-dim">
        <b className="text-3xl text-ink tnum">
          {s.hits} of {s.games}
        </b>{" "}
        recent games
      </p>
      <h3 className="text-xl font-bold">{s.lesson.title}</h3>
      {s.lesson.habit && <p className="text-dim">Habit: {s.lesson.habit}</p>}
    </Link>
  );
}

function LessonCard({ lesson: l }: { lesson: Lesson }) {
  return (
    <Link to={`/learn/${l.id}`} className="card block space-y-2 hover:border-s1">
      <div className="flex items-center gap-3">
        <span className="text-3xl" aria-hidden>
          {l.icon}
        </span>
        <h3 className="text-xl font-bold">{l.title}</h3>
      </div>
      <p className="text-dim">{l.summary}</p>
      <p className="text-sm font-bold text-s1">▶ {l.try.label}</p>
    </Link>
  );
}
