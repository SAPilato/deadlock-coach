// Which lessons to suggest, from the habits the findings engine flagged.
import type { Lesson, Trends, TrendStatus } from "./api";

type Habit = Trends["habits"][number];

export interface Suggestion {
  lesson: Lesson;
  focus: boolean;
  hits: number;
  games: number;
  status: TrendStatus;
}

const rate = (hits: number, games: number) => (games ? hits / games : 0);

/** Focus habit first, then other flagged habits by how often they showed up. Improving habits are left out. */
export function suggestLessons(lessons: Lesson[], trends: Trends | undefined, max = 3): Suggestion[] {
  if (!trends) return [];
  const byId = new Map(lessons.map((l) => [l.id, l]));
  const out: Suggestion[] = [];
  const add = (id: string | null, s: Omit<Suggestion, "lesson">) => {
    const lesson = id ? byId.get(id) : undefined;
    if (lesson && !out.some((o) => o.lesson.id === id)) out.push({ lesson, ...s });
  };
  const f = trends.focus;
  if (f) add(f.lesson_id, { focus: true, hits: f.hits, games: f.games, status: f.status });
  [...trends.habits]
    .filter((h) => h.recent_hits > 0 && h.status !== "improving")
    .sort((a, b) => rate(b.recent_hits, b.recent_games) - rate(a.recent_hits, a.recent_games))
    .forEach((h) => add(h.lesson_id, { focus: false, hits: h.recent_hits, games: h.recent_games, status: h.status }));
  return out.slice(0, max);
}

/** The habit a lesson fixes, as tracked in your recent games. */
export function habitFor(lessonId: string, trends: Trends | undefined): Habit | undefined {
  return trends?.habits.find((h) => h.lesson_id === lessonId);
}
