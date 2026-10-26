import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useLessons() {
  return useQuery({ queryKey: ["learn"], queryFn: api.learn, staleTime: 10 * 60_000 });
}

/** "📚 Lesson: Wave management →" for a finding or habit that has a lesson. */
export default function LessonLink({ id, big = false }: { id: string | null; big?: boolean }) {
  const q = useLessons();
  if (!id) return null;
  const lesson = q.data?.find((l) => l.id === id);
  return (
    <Link to={`/learn/${id}`} className={big ? "btn" : "chip font-bold text-s1 hover:border-s1"}>
      <span aria-hidden>📚</span> {lesson ? `Lesson: ${lesson.title}` : "Lesson"} →
    </Link>
  );
}
