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
    zip: [number, number, number][]; // [start s, end s, lane id] per zipline ride
  })[];
  lanes: { id: number; name: string; color: string }[];
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

// ---- Build Lab -----------------------------------------------------------------

export type SlotType = "weapon" | "vitality" | "spirit";

export interface ShopItem {
  id: number;
  name: string;
  tier: number;
  cost: number;
  slot: SlotType;
  image?: string;
  active: boolean;
  lines: string[];
  conditional: number;
  win_rate: number | null;
  games: number | null;
  pick_rate: number | null;
  avg_buy_s: number | null;
}

export interface ShopData {
  hero: { id: number; name: string };
  items: ShopItem[];
  levels: { level: number; souls: number; boons: number }[];
  bracket: [number, number];
  has_rank_stats: boolean;
  slots: { limit: number; est: boolean; players: number };
}

export interface Target {
  hp: number;
  bullet_resist: number;
  headshot_pct: number;
  spirit_resist: number;
}

export interface Build {
  hero_id: number;
  level: number;
  items: number[];
  toggles: string[];
  target: Target;
  ability_tier: number;
}

export interface AbilityInfo {
  name: string;
  image?: string;
  lines: { label: string; base: number; value: number; vs_dummy: number; factor: number; other_scaling: string | null }[];
  cooldown_base: number | null;
  cooldown: number | null;
}

export interface StatRow {
  key: string;
  label: string;
  group: "Weapon" | "Vitality" | "Spirit" | "Spending";
  value: number | null;
  unit: string;
  status: "data" | "rule" | "est";
  better: "higher" | "lower";
  note: string | null;
}

export interface EffectInfo {
  key: string;
  item_id: number;
  item: string;
  label: string;
  stat: string;
  value: number;
  postfix: string;
  kind: "always" | "conditional" | "active";
  condition: string | null;
  target: "self" | "enemy" | "ability";
  on: boolean;
}

export interface Sheet {
  hero: { id: number; name: string };
  level: number;
  boons: number;
  souls_for_level: number | null;
  cost: number;
  spend: Record<SlotType, number>;
  rows: StatRow[];
  dps: {
    gun_dps: number;
    dps_reload: number;
    effective: number;
    ttk: number | null;
    headshot_mult: number;
    target_resist: number;
    shred: number;
    spirit_amp: number;
    target_spirit_resist: number;
    spirit_shred: number;
  };
  effects: EffectInfo[];
  abilities: AbilityInfo[];
  notes: string[];
  items: number[];
  slots: { limit: number; est: boolean };
  warnings: string[];
}

export interface SavedBuild extends Build {
  id: number;
  name: string;
  updated_at: number;
}

// ---- Macro Map -------------------------------------------------------------------

export interface MapPoint {
  left: number;
  top: number;
  label: string;
  kind: string;
  facts: string | null;
  tip: string | null;
  target?: [number, number];
  team?: number;
  size?: string;
}

export interface MapLayerData {
  id: string;
  label: string;
  on: boolean;
  points: MapPoint[];
  lines?: { id: number; name: string; color: string; pts: [number, number][] }[];
}

export interface MacroLayers {
  image?: string;
  overlays: { id: string; label: string; image?: string }[];
  layers: MapLayerData[];
  verified: { match_id: number; start_time: number | null } | null;
  transform: { ax: number; bx: number; ay: number; by: number };
  meters_per_unit: number;
  teams: Record<string, string>;
  heroes: (HeroCard & { move: number; sprint: number })[];
}

export interface Movement {
  matches: number;
  zip_speed: number; // game units per second, measured
  foot_speed: number;
  fast_speed: number;
  detour: number;
  detour_best: number;
  samples: { zip_s: number; foot_windows: number; trips: number };
  attach_s: number;
  switches: { count: number; gap_s: number | null }; // one zipline to another, measured
  avg_hero_move: number;
  grid: number;
  walkable: [number, number][];
}

export interface WavesData {
  available: { match_id: number; sample: boolean; hero?: HeroCard; team?: number; start_time?: number }[];
  match_id: number;
  my_team: number | null;
  teams: Record<string, string>;
  lanes: { id: number; name: string; color: string; pts: [number, number][] }[];
  schedule: {
    first: number;
    every: number;
    late_every: number;
    late_after_min: number;
    very_late_every: number;
    very_late_after_min: number;
    squad: number;
  } | null;
  step: number;
  frames: { t: number; lanes: Record<string, { w: [number, number, number][]; c: number | null }> }[];
  meets: { minute: number; lanes: Record<string, number> }[];
}

export interface HeatmapData {
  grid: number;
  matches: number;
  phases: Record<"early" | "mid" | "late", { cells: [number, number, number][]; max: number; minutes: number }>;
  objectives: { left: number; top: number; phase: string; taken: boolean; name: string; match_id: number; t: number }[];
}

export interface ScenarioRow {
  match_id: number;
  t: number;
  hero: HeroCard;
  start_time: number;
  habit: string | null;
  label: string;
}

export interface Scenario {
  match_id: number;
  t: number;
  hero: string;
  team: number;
  players: { slot: number; hero: string; hero_id: number; side: "me" | "ally" | "enemy" }[];
  frames: { t: number; pos: { slot: number; left: number; top: number; alive: boolean; hp: number | null }[] }[];
  objectives: { left: number; top: number; kind: string; ally: boolean; alive: boolean }[];
  souls: { you: number; them: number };
  options: { id: string; label: string }[];
  did: { id: string; label: string };
  events: { t: number; text: string; side: string }[];
  finding: { habit: string; headline: string; do_next: string } | null;
}

export type LessonTopic = "Lane" | "Map" | "Fights" | "Items";

export interface Lesson {
  id: string;
  topic: LessonTopic;
  title: string;
  icon: string;
  summary: string;
  points: string[];
  facts: { text: string; source: "game data" | "measured" | "replay" }[];
  try: { label: string; href: string };
  /** Findings rule that suggests this lesson, if any. */
  rule_id: string | null;
  habit: string | null;
}

// ---- Build helper ---------------------------------------------------------------------

export interface HelperItem {
  id: number;
  name: string;
  tier: number | null;
  cost: number | null;
  slot: SlotType | null;
  image: string | null;
}

export interface PhasePicks {
  phases: { phase: string; games: number; items: (HelperItem & { pick_rate: number; win_rate: number; games: number })[] }[];
  games: number | null;
  win_rate: number | null;
  bracket: [number, number];
}

export interface SpikeStep extends HelperItem {
  souls: number; // total spent after this item
  level: number;
  at_s: number | null; // when your recent games reached these souls
  typical_s: number | null; // when players at your rank usually buy it
  gains: { dps: number | null; ehp: number | null; ability: number | null };
  bonus: { slot: SlotType; threshold: number; bonus: number; jump: number } | null;
  spike: boolean;
  spike_on: ("dps" | "ehp" | "ability")[];
}

export interface Spikes {
  steps: SpikeStep[];
  pace: { games: number; this_hero: boolean } | null;
}

export interface CounterRow extends HelperItem {
  delta: number; // win rate vs these enemies minus the item's other games
  z: number;
  games: number;
  strong_vs: string[];
  weak_vs: string[];
  lines: string[];
}

export interface Counters {
  buy: CounterRow[];
  skip: CounterRow[];
  enemies: number[];
  bracket: [number, number];
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

  blHeroes: () => request<HeroCard[]>("/buildlab/heroes"),
  blShop: (heroId: number) => request<ShopData>(`/buildlab/shop?hero_id=${heroId}`),
  blCompute: (b: Build) => request<Sheet>("/buildlab/compute", { method: "POST", body: JSON.stringify(b) }),
  builds: () => request<SavedBuild[]>("/builds"),
  saveBuild: (b: Build & { id?: number; name: string }) =>
    request<SavedBuild>("/builds", { method: "POST", body: JSON.stringify(b) }),
  deleteBuild: (id: number) => request<{ deleted: number }>(`/builds/${id}`, { method: "DELETE" }),
  importBuild: (data: unknown) =>
    request<SavedBuild>("/builds/import", { method: "POST", body: JSON.stringify(data) }),
  exportUrl: (id: number) => `/api/builds/${id}/export`,
  macroLayers: () => request<MacroLayers>("/macro/layers"),
  macroMovement: () => request<Movement>("/macro/movement"),
  macroWaves: (matchId?: number) => request<WavesData>(`/macro/waves${matchId ? `?match_id=${matchId}` : ""}`),
  macroHeatmap: (n = 10) => request<HeatmapData>(`/macro/heatmap?n=${n}`),
  macroScenarios: () => request<ScenarioRow[]>("/macro/scenarios"),
  macroScenario: (matchId: number, t: number) => request<Scenario>(`/macro/scenario?match_id=${matchId}&t=${t}`),
  learn: () => request<Lesson[]>("/learn"),
  helperPhases: (heroId: number) => request<PhasePicks>(`/buildlab/helper/phases?hero_id=${heroId}`),
  helperSpikes: (b: Build) => request<Spikes>("/buildlab/helper/spikes", { method: "POST", body: JSON.stringify(b) }),
  helperCounters: (heroId: number, enemies: number[]) =>
    request<Counters>(`/buildlab/helper/counters?hero_id=${heroId}&enemies=${enemies.join(",")}`),
  matchEnemies: (matchId: number) => request<{ match_id: number; hero_id: number; enemies: number[] }>(`/matches/${matchId}/enemies`),
  matchBuild: (matchId: number, t?: number) =>
    request<{ hero_id: number; level: number; items: number[]; at: number; name: string }>(
      `/matches/${matchId}/build${t != null ? `?t=${t}` : ""}`,
    ),
};
