import { describe, expect, it } from "vitest";
import type { Lesson, Trends } from "./api";
import { habitFor, suggestLessons } from "./learn";

const lesson = (id: string): Lesson => ({
  id,
  topic: "Map",
  title: id,
  icon: "",
  summary: "",
  points: [],
  facts: [],
  try: { label: "", href: "/map" },
  rule_id: null,
  habit: null,
});

const habit = (lesson_id: string | null, recent_hits: number, recent_games = 10, status: Trends["habits"][number]["status"] = "same") => ({
  rule_id: `r-${lesson_id}`,
  habit: `h-${lesson_id}`,
  lesson_id,
  do_next: "",
  status,
  recent_hits,
  recent_games,
  previous_hits: 0,
  previous_games: 10,
  per_match: [],
});

const trends = (habits: Trends["habits"], focus: Trends["focus"] = null): Trends => ({
  matches: [],
  recent_n: 10,
  previous_n: 10,
  heroes: {},
  using_sample: false,
  habits,
  focus,
});

const lessons = ["a", "b", "c", "d"].map(lesson);

describe("suggestLessons", () => {
  it("returns nothing before trends load", () => {
    expect(suggestLessons(lessons, undefined)).toEqual([]);
  });

  it("puts the focus first, then habits by how often they showed up", () => {
    const t = trends([habit("b", 2), habit("c", 7), habit("a", 4)], {
      rule_id: "r-a", habit: "h-a", do_next: "", lesson_id: "a", status: "worse", hits: 4, games: 10,
    });
    const got = suggestLessons(lessons, t);
    expect(got.map((s) => s.lesson.id)).toEqual(["a", "c", "b"]);
    expect(got[0].focus).toBe(true);
    expect(got[1]).toMatchObject({ focus: false, hits: 7, games: 10 });
  });

  it("skips improving habits, clean habits and missing lessons", () => {
    const t = trends([habit("a", 5, 10, "improving"), habit("b", 0), habit("zzz", 9), habit(null, 9), habit("d", 1)]);
    expect(suggestLessons(lessons, t).map((s) => s.lesson.id)).toEqual(["d"]);
  });

  it("caps the list", () => {
    const t = trends([habit("a", 1), habit("b", 2), habit("c", 3), habit("d", 4)]);
    expect(suggestLessons(lessons, t, 2).map((s) => s.lesson.id)).toEqual(["d", "c"]);
  });
});

describe("habitFor", () => {
  it("finds the tracked habit for a lesson", () => {
    expect(habitFor("b", trends([habit("a", 1), habit("b", 3)]))?.recent_hits).toBe(3);
    expect(habitFor("x", trends([habit("a", 1)]))).toBeUndefined();
  });
});
