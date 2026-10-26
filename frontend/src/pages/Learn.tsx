import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Lesson, type LessonTopic } from "../lib/api";
import { suggestLessons, type Suggestion } from "../lib/learn";
import { useLessons } from "../components/LessonLink";
import { ErrorBox, Icon, Loading } from "../components/ui";
import { STATUS } from "./Home";
import { BookOpen, Check, type LucideIcon, Map as MapIcon, Play, ShoppingCart, Swords, Target, Waves } from "lucide-react";
import LessonIcon from "../components/LessonIcon";

export const TOPIC: Record<LessonTopic, LucideIcon> = { Lane: Waves, Map: MapIcon, Fights: Swords, Items: ShoppingCart };

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
        <h1 className="text-3xl font-bold">
          <Icon icon={BookOpen} className="text-accent" /> Learn
        </h1>
        <span className="text-dim">Short lessons. Each one opens a map or Build Lab view.</span>
      </div>

      <section className="space-y-3" aria-labelledby="for-you">
        <h2 id="for-you" className="text-2xl font-bold">
          <Icon icon={Target} className="text-accent" /> For you
        </h2>
        {trends.isLoading ? (
          <Loading label="Checking your last 20 games…" />
        ) : trends.error ? (
          <p className="card text-dim">Could not check your games. All lessons are below.</p>
        ) : picks.length === 0 ? (
          <p className="card border-good text-xl font-bold text-good"><Icon icon={Check} /> No repeat problems. Pick any lesson below.</p>
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
            <Icon icon={TOPIC[t]} className="text-accent" /> {t}
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
      className={`card block space-y-2 hover:border-accent ${s.focus ? "border-2 border-accent" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <LessonIcon name={s.lesson.icon} className="text-3xl text-accent" />
        {s.focus && <span className="chip border-accent font-bold text-accent"><Icon icon={Target} /> Your focus</span>}
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
    <Link to={`/learn/${l.id}`} className="card block space-y-2 hover:border-accent">
      <div className="flex items-center gap-3">
        <LessonIcon name={l.icon} className="text-3xl text-accent" />
        <h3 className="text-xl font-bold">{l.title}</h3>
      </div>
      <p className="text-dim">{l.summary}</p>
      <p className="text-sm font-bold text-accent"><Icon icon={Play} /> {l.try.label}</p>
    </Link>
  );
}
