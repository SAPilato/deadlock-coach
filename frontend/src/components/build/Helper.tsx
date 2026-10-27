import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Crosshair, ListChecks, ShieldHalf, Swords, X, Zap } from "lucide-react";
import { api, type Build, type CounterRow, type HelperItem, type HeroCard, type SpikeStep } from "../../lib/api";
import { clock } from "../../lib/format";
import { ErrorBox, EstTag, Icon, Loading } from "../ui";
import { CATEGORY, souls } from "./common";

type Tab = "start" | "spikes" | "counters";

const TABS: { id: Tab; label: string; icon: typeof Zap }[] = [
  { id: "start", label: "Start", icon: ListChecks },
  { id: "spikes", label: "Spikes", icon: Zap },
  { id: "counters", label: "Counter-buy", icon: ShieldHalf },
];

const METRIC = { dps: "gun DPS", ehp: "durability", ability: "ability damage" } as const;
const pct = (x: number) => `${x > 0 ? "+" : ""}${Math.round(x * 100)}%`;
const START_ITEMS = 4;

interface Props {
  build: Build;
  heroes: HeroCard[];
  full: boolean;
  lastMatchId: number | null;
  onAdd: (ids: number[]) => void;
}

/** Build helper: the usual start, where this build spikes, and what counters the enemy. */
export default function Helper(props: Props) {
  const [tab, setTab] = useState<Tab>("start");
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Build helper">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-xl border-2 px-4 py-2 font-bold ${tab === t.id ? "border-accent bg-panel2" : "border-line text-dim hover:text-ink"}`}
          >
            <Icon icon={t.icon} /> {t.label}
          </button>
        ))}
      </div>
      {tab === "start" && <Start {...props} />}
      {tab === "spikes" && <SpikesView build={props.build} />}
      {tab === "counters" && <CountersView {...props} />}
    </div>
  );
}

function ItemRow({ it, owned, full, onAdd, children }: { it: HelperItem; owned: boolean; full: boolean; onAdd: () => void; children?: React.ReactNode }) {
  const c = it.slot ? CATEGORY[it.slot] : null;
  return (
    <div className={`flex items-center gap-3 rounded-xl border bg-panel2 p-2 ${c ? c.border : "border-line"}`}>
      {it.image && <img src={it.image} alt="" className="h-10 w-10 shrink-0 rounded-md" />}
      <div className="min-w-0 flex-1">
        <div className="font-bold leading-tight">{it.name}</div>
        {children}
      </div>
      <button
        type="button"
        disabled={owned || full}
        onClick={onAdd}
        className="chip shrink-0 font-bold text-accent hover:border-accent disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={owned ? `${it.name} is in your build` : `Add ${it.name}`}
      >
        {owned ? <Icon icon={Check} /> : "+ Add"}
      </button>
    </div>
  );
}

// ---- Start: what players at your rank buy in each phase --------------------------------

function Start({ build, full, onAdd }: Props) {
  const q = useQuery({ queryKey: ["bl-phases", build.hero_id], queryFn: () => api.helperPhases(build.hero_id), staleTime: 30 * 60_000 });
  if (q.isLoading) return <Loading label="Reading what players at your rank buy…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  const owned = new Set(build.items);
  const start = d.phases[0]?.items.filter((i) => !owned.has(i.id)).slice(0, START_ITEMS) ?? [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-dim">
          Most-bought items per phase. <b className="text-ink tnum">{d.games?.toLocaleString() ?? "?"}</b> games, badges {d.bracket[0]}–
          {d.bracket[1]}.
        </p>
        {start.length > 0 && (
          <button type="button" className="btn-primary ml-auto" disabled={full} onClick={() => onAdd(start.map((i) => i.id))}>
            <Icon icon={ListChecks} /> Add the usual start ({start.length})
          </button>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {d.phases.map((ph) => (
          <div key={ph.phase} className="space-y-2">
            <div className="label">{ph.phase}</div>
            {ph.items.length === 0 && <p className="text-sm text-muted">Not enough games.</p>}
            {ph.items.map((it) => (
              <ItemRow key={it.id} it={it} owned={owned.has(it.id)} full={full} onAdd={() => onAdd([it.id])}>
                <div className="text-sm text-dim tnum">
                  {Math.round(it.pick_rate * 100)}% buy it · {Math.round(it.win_rate * 100)}% win
                </div>
              </ItemRow>
            ))}
          </div>
        ))}
      </div>
      <p className="text-sm text-muted">Phases are fixed by the data source. Win rate is raw: players ahead buy more.</p>
    </div>
  );
}

// ---- Spikes: what each purchase adds, and when ---------------------------------------

function SpikesView({ build }: { build: Build }) {
  const q = useQuery({
    queryKey: ["bl-spikes", build],
    queryFn: () => api.helperSpikes(build),
    enabled: build.items.length > 0,
  });
  if (build.items.length === 0) return <p className="text-dim">Add items in buying order. Then see where the build spikes.</p>;
  if (q.isLoading) return <Loading label="Running the build step by step…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const { steps, pace } = q.data!;
  const spikes = steps.filter((s) => s.spike);
  return (
    <div className="space-y-4">
      <p className="text-xl">
        <b className="tnum">{spikes.length}</b> {spikes.length === 1 ? "spike" : "spikes"} in this build
        {spikes.length > 0 && (
          <span className="text-dim">
            : {spikes.map((s) => `${s.name}${s.at_s != null ? ` (~${clock(s.at_s)})` : ""}`).join(", ")}
          </span>
        )}
      </p>
      <ol className="space-y-2">
        {steps.map((s, k) => (
          <SpikeRow key={`${s.id}-${k}`} s={s} n={k + 1} />
        ))}
      </ol>
      <ul className="space-y-1 text-sm text-muted">
        <li>
          Spike: +15% gun DPS, durability or ability damage, or a big spending bonus. <EstTag />
        </li>
        <li>
          {pace
            ? `"You": when your last ${pace.games} ${pace.this_hero ? "games on this hero" : "games"} had these souls.`
            : `"You" needs your Steam ID in Settings.`}{" "}
          "Rank": when players at your rank usually buy it.
        </li>
        <li>Order matters. Items are bought in the order of your build slots.</li>
      </ul>
    </div>
  );
}

function SpikeRow({ s, n }: { s: SpikeStep; n: number }) {
  const gains = (Object.keys(METRIC) as (keyof typeof METRIC)[])
    .map((m) => [m, s.gains[m]] as const)
    .filter(([, g]) => g != null && Math.abs(g) >= 0.01);
  return (
    <li className={`flex flex-wrap items-center gap-3 rounded-xl border bg-panel2 p-2 ${s.spike ? "border-accent" : "border-line"}`}>
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-panel font-bold tnum">{n}</span>
      {s.image && <img src={s.image} alt="" className="h-10 w-10 shrink-0 rounded-md" />}
      <div className="min-w-[10rem] flex-1">
        <div className="flex flex-wrap items-center gap-2 font-bold">
          {s.name}
          {s.spike && (
            <span className="chip border-accent py-0 text-xs font-bold text-accent">
              <Icon icon={Zap} /> Spike
            </span>
          )}
        </div>
        <div className="text-sm text-dim tnum">
          ◆ {souls(s.souls)} · level {s.level}
          {s.at_s != null && ` · you ~${clock(s.at_s)}`}
          {s.typical_s != null && ` · rank ~${clock(s.typical_s)}`}
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {gains.map(([m, g]) => (
          <span key={m} className={`chip py-0 text-sm tnum ${s.spike_on.includes(m) ? "border-accent font-bold" : ""}`}>
            {pct(g!)} {METRIC[m]}
          </span>
        ))}
        {s.bonus && (
          <span className={`chip py-0 text-sm tnum ${s.bonus.jump >= 15 ? "border-accent font-bold" : ""}`}>
            {CATEGORY[s.bonus.slot].label} {souls(s.bonus.threshold)}: +{s.bonus.bonus}%
          </span>
        )}
      </div>
    </li>
  );
}

// ---- Counter-buy: what wins more than usual against these enemies ---------------------

function CountersView({ build, heroes, full, lastMatchId, onAdd }: Props) {
  const [enemies, setEnemies] = useState<number[]>([]);
  const [filled, setFilled] = useState(false);
  const last = useQuery({
    queryKey: ["match-enemies", lastMatchId],
    queryFn: () => api.matchEnemies(lastMatchId!),
    enabled: lastMatchId != null,
    staleTime: Infinity,
  });
  // Start from the team you last played against.
  useEffect(() => {
    if (!filled && last.data) {
      setEnemies(last.data.enemies);
      setFilled(true);
    }
  }, [filled, last.data]);
  const q = useQuery({
    queryKey: ["bl-counters", build.hero_id, [...enemies].sort()],
    queryFn: () => api.helperCounters(build.hero_id, enemies),
    enabled: enemies.length > 0,
    staleTime: 30 * 60_000,
  });
  const byId = new Map(heroes.map((h) => [h.id, h]));
  const owned = new Set(build.items);
  const choices = heroes.filter((h) => h.id !== build.hero_id && !enemies.includes(h.id));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="label">Enemy team</span>
        {enemies.map((id) => {
          const h = byId.get(id);
          return (
            <span key={id} className="chip gap-2">
              {h?.image && <img src={h.image} alt="" className="h-6 w-6 rounded-full object-cover" />}
              {h?.name ?? id}
              <button type="button" onClick={() => setEnemies((e) => e.filter((x) => x !== id))} aria-label={`Remove ${h?.name ?? id}`}>
                <Icon icon={X} />
              </button>
            </span>
          );
        })}
        {enemies.length < 6 && (
          <select
            value=""
            onChange={(e) => e.target.value && setEnemies((x) => [...x, Number(e.target.value)])}
            className="rounded-lg bg-panel2 border border-line px-3 py-1"
            aria-label="Add an enemy hero"
          >
            <option value="">+ Add enemy</option>
            {choices.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        )}
        {last.data && (
          <button type="button" className="chip hover:border-accent" onClick={() => setEnemies(last.data!.enemies)}>
            <Icon icon={Swords} /> My last match
          </button>
        )}
      </div>

      {enemies.length === 0 ? (
        <p className="text-dim">Pick the heroes you are up against.</p>
      ) : q.isLoading ? (
        <Loading label="Comparing items against these heroes…" />
      ) : q.error ? (
        <ErrorBox error={q.error} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
          <div className="space-y-2">
            <h3 className="font-bold">
              <Icon icon={Crosshair} className="text-good" /> Buy: wins more vs this team <EstTag />
            </h3>
            {q.data!.buy.length === 0 && <p className="text-dim">No item clearly beats this team. Build as usual.</p>}
            {q.data!.buy.map((r) => (
              <CounterItem key={r.id} r={r} owned={owned.has(r.id)} full={full} onAdd={() => onAdd([r.id])} />
            ))}
          </div>
          <div className="space-y-2">
            <h3 className="font-bold">
              <Icon icon={X} className="text-high" /> Skip: wins less vs this team
            </h3>
            {q.data!.skip.length === 0 && <p className="text-dim">Nothing clearly worse.</p>}
            {q.data!.skip.map((r) => (
              <CounterItem key={r.id} r={r} owned={owned.has(r.id)} full={full} onAdd={() => onAdd([r.id])} />
            ))}
          </div>
        </div>
      )}
      <p className="text-sm text-muted">
        Each item is compared with its own other games, for your hero and rank. Only clear differences (95% sure) show.
      </p>
    </div>
  );
}

function CounterItem({ r, owned, full, onAdd }: { r: CounterRow; owned: boolean; full: boolean; onAdd: () => void }) {
  const vs = r.delta > 0 ? r.strong_vs : r.weak_vs;
  return (
    <ItemRow it={r} owned={owned} full={full} onAdd={onAdd}>
      <div className="text-sm tnum">
        <b className={r.delta > 0 ? "text-good" : "text-high"}>{pct(r.delta)} win</b>
        <span className="text-dim"> · {r.games.toLocaleString()} games</span>
        {vs.length > 0 && <span className="text-dim"> · vs {vs.join(", ")}</span>}
      </div>
      {r.lines.length > 0 && <div className="truncate text-sm text-dim">{r.lines.join(" · ")}</div>}
    </ItemRow>
  );
}
