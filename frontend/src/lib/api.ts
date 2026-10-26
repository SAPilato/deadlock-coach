// Typed client for the FastAPI backend (/api, proxied by Vite in dev).

export type Severity = "high" | "med" | "low";

export interface HeroCard {
  id: number;
  name: string;
  image?: string;
  card?: string;
}

export interface RankInfo {
  badge: number;
  tier: number;
  subrank: number;
  name: string;
  image?: string;
}

export interface Meta {
  patch: {
    live_build: number | null;
    cached_build: number | null;
    stale: boolean;
    latest_patch: { title: string; date: string; link: string } | null;
  };
  offline: boolean;
  account_id: number | null;
  using_sample: boolean;
  bracket: [number, number];
  bracket_names: [RankInfo | null, RankInfo | null];
}

export interface MatchRow {
  match_id: number;
  start_time: number;
  duration_s: number;
  hero: HeroCard;
  won: boolean;
  kills: number;
  deaths: number;
  assists: number;
  net_worth: number;
  souls_per_min: number;
  rank: RankInfo | null;
  mode: string;
  street_brawl: boolean;
}

export interface Evidence {
  label: string;
  value: number | string;
  benchmark: number | string | null;
  unit: "" | "time" | "min" | "s" | "m" | "%" | "souls" | "/min";
  better: "higher" | "lower" | null;
  est: boolean;
}

export interface Moment {
  t: number;
  x: number | null;
  y: number | null;
  label: string;
}

export interface Finding {
  rule_id: string;
  habit: string;
  severity: Severity;
  score: number;
  headline: string;
  do_next: string;
  more: string[];
  evidence: Evidence[];
  moments: Moment[];
  est: boolean;
  lesson_id: string | null;
}

export interface HabitStatus {
  rule_id: string;
  habit: string;
  reason: string | null;
}

export interface TimelineEvent {
  t: number;
  type: "death" | "kill" | "objective" | "midboss" | "item";
  label: string;
  side?: "ally" | "enemy";
  x?: number | null;
  y?: number | null;
  image?: string;
  tier?: number;
}

export interface MapLayer {
  image?: string;
  lanes: { id: number; name: string; color: string; pts: [number, number][] }[];
}

export interface Report {
  match: {
    id: number;
    start_time: number;
    duration_s: number;
    won: boolean;
    mode: string;
    hero: HeroCard;
    kills: number;
    deaths: number;
    assists: number;
    net_worth: number;
    souls_per_min: number;
    rank: RankInfo | null;
    lane: { id: number; name: string; color: string } | null;
    team: number;
  };
  findings: Finding[];
  passed: HabitStatus[];
  skipped: HabitStatus[];
  benchmarks: {
    available: boolean;
    bracket?: [number, number];
    tiles: {
      key: string;
      label: string;
      value: number;
      benchmark: number;
      p25: number | null;
      p75: number | null;
      better: "higher" | "lower";
    }[];
  };
  timeline: {
    duration_s: number;
    series: { t: number; you: number; avg: number | null }[];
    events: TimelineEvent[];
  };
  phases: { laning_end: number; mid_end: number; est: boolean };
  deaths: {
    t: number;
    left: number;
    top: number;
    phase: "early" | "mid" | "late";
    killer: string | null;
    place: string;
  }[];
  items: {
    t: number;
    item_id: number;
    name: string;
    image?: string;
    tier: number;
    slot_type: string;
    cost: number | null;
    sold_t: number | null;
    avg_t: number | null;
    delta: number | null;
    core: boolean;
    win_rate: number | null;
  }[];
  lane: {
    lane: { id: number; name: string; color: string } | null;
    partner: HeroCard[];
    opponents: HeroCard[];
    checkpoints: { t: number; you: number; avg: number | null; lead: number | null }[];
    deaths_before_10: number;
    laning_end: number;
    laning_end_est: boolean;
  };
  map: MapLayer;
  players: (HeroCard & { slot: number; team: number; is_me: boolean })[];
  replay: { status: string; error?: string | null };
}

export interface Paths {
  step: number;
  duration_s: number;
  players: (HeroCard & {
    slot: number;
    team: number;
    is_me: boolean;
    ally: boolean;
    pts: [number, number][];
    dead: [number, number][];
  })[];
}

export type TrendStatus = "improving" | "same" | "worse" | "not_enough";

export interface Trends {
  matches: { match_id: number; start_time: number; hero_id: number; won: boolean }[];
  recent_n: number;
  previous_n: number;
  heroes: Record<string, HeroCard>;
  using_sample: boolean;
  habits: {
    rule_id: string;
    habit: string;
    lesson_id: string | null;
    do_next: string;
    status: TrendStatus;
    recent_hits: number;
    recent_games: number;
    previous_hits: number;
    previous_games: number;
    per_match: { match_id: number; severity: Severity | null; ran: boolean }[];
  }[];
  focus: {
    rule_id: string;
    habit: string;
    do_next: string;
    lesson_id: string | null;
    status: TrendStatus;
    hits: number;
    games: number;
  } | null;
}

export interface SettingsData {
  account_id: number | null;
  sample_account: number | null;
  using_sample: boolean;
  profile: { name: string; avatar: string } | null;
  bracket: [number, number];
  ranks: { tier: number; name: string; image?: string }[];
}

export interface SteamHit {
  account_id: number;
  name: string;
  avatar?: string;
  badge: number | null;
  matches_30d: number | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = body.detail || msg;
    } catch {
      /* not JSON */
    }
    throw new ApiError(msg, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => request<Meta>("/meta"),
  matches: (refresh = false) =>
    request<{ account_id: number; using_sample: boolean; matches: MatchRow[] }>(
      `/matches${refresh ? "?refresh=true" : ""}`,
    ),
  report: (id: number) => request<Report>(`/matches/${id}/report`),
  paths: (id: number, step = 5) => request<Paths>(`/matches/${id}/paths?step=${step}`),
  trends: (n = 20) => request<Trends>(`/trends?n=${n}`),
  settings: () => request<SettingsData>("/settings"),
  saveSettings: (body: { steam_id?: string; clear_account?: boolean; bracket?: [number, number] }) =>
    request<SettingsData>("/settings", { method: "PUT", body: JSON.stringify(body) }),
  steamSearch: (q: string) => request<SteamHit[]>(`/steam/search?q=${encodeURIComponent(q)}`),
  refreshGameData: () => request<{ dropped: number }>("/gamedata/refresh", { method: "POST" }),
  replayFetch: (id: number) => request<{ status: string }>(`/matches/${id}/replay/fetch`, { method: "POST" }),
  replayUpload: async (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`/api/matches/${id}/replay`, { method: "POST", body: fd });
    if (!res.ok) throw new ApiError((await res.json()).detail || res.statusText, res.status);
    return res.json() as Promise<{ status: string }>;
  },
  replayStatus: (id: number) => request<{ status: string; error?: string }>(`/matches/${id}/replay`),
};
