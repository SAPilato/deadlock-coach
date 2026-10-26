import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Report } from "../lib/api";
import { ago, clock, num, signed } from "../lib/format";
import FindingCard from "../components/FindingCard";
import ItemTiming from "../components/ItemTiming";
import Minimap from "../components/Minimap";
import ReplayBox from "../components/ReplayBox";
import Timeline from "../components/Timeline";
import { ErrorBox, EstTag, HeroIcon, Loading, More, RankBadge, Section, StatTile, WinLoss } from "../components/ui";

const PHASE = {
  early: { color: "#3987e5", label: "Laning" },
  mid: { color: "#d95926", label: "Mid game" },
  late: { color: "#199e70", label: "Late game" },
} as const;

const SECTIONS = [
  ["findings", "Findings"],
  ["timeline", "Timeline"],
  ["benchmarks", "Vs rank"],
  ["deaths", "Deaths"],
  ["items", "Items"],
  ["lane", "Lane"],
  ["replay", "Replay"],
] as const;

export default function MatchReport() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["report", id], queryFn: () => api.report(id) });
  const [time, setTime] = useState<number | null>(null);

  if (q.isLoading) return <Loading label="Reviewing this match…" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const r = q.data!;

  const jump = (t: number) => {
    setTime(t);
    document.getElementById("timeline")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="space-y-6">
      <Header r={r} />

      <nav className="sticky top-[4.2rem] z-10 -mx-1 flex flex-wrap gap-2 bg-bg/95 py-2" aria-label="Report sections">
        {SECTIONS.map(([key, label]) => (
          <a key={key} href={`#${key}`} className="chip hover:border-s1">
            {label}
          </a>
        ))}
      </nav>

      <Findings r={r} onMoment={jump} />

      <Section id="timeline" title="⏱ Timeline">
        <Timeline report={r} time={time} setTime={setTime} />
      </Section>

      <Benchmarks r={r} />

      <Section id="deaths" title={`✖ Deaths: ${r.deaths.length}`}>
        <DeathMap r={r} onPick={jump} />
      </Section>

      <Section id="items" title="🛒 Item timing vs your rank">
        <ItemTiming items={r.items} onPick={jump} />
      </Section>

      <Lane r={r} />

      <Section id="replay" title="🎞 Replay file (optional)">
        <ReplayBox report={r} />
      </Section>
    </div>
  );
}

function Header({ r }: { r: Report }) {
  const m = r.match;
  return (
    <div className="card flex flex-wrap items-center gap-5">
      <HeroIcon hero={m.hero} size={72} />
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-3xl font-bold">{m.hero.name}</h1>
          <WinLoss won={m.won} />
          <span className="chip">{m.mode}</span>
        </div>
        <div className="text-dim">
          {ago(m.start_time)} · {clock(m.duration_s)} long
          {m.lane && (
            <>
              {" · "}
              <span style={{ color: m.lane.color }}>●</span> {m.lane.name} lane
            </>
          )}
        </div>
      </div>
      <div className="ml-auto flex flex-wrap gap-6">
        <Big label="K / D / A" value={`${m.kills} / ${m.deaths} / ${m.assists}`} />
        <Big label="Souls / min" value={num(m.souls_per_min)} />
        <Big label="Souls" value={num(m.net_worth)} />
        {m.rank && (
          <div>
            <div className="label">Lobby rank</div>
            <RankBadge rank={m.rank} />
          </div>
        )}
      </div>
      <Link to="/matches" className="w-full text-s1 hover:underline">
        ← All matches
      </Link>
    </div>
  );
}

function Big({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="text-2xl font-bold tnum">{value}</div>
    </div>
  );
}

function Findings({ r, onMoment }: { r: Report; onMoment: (t: number) => void }) {
  const top = r.findings.slice(0, 3);
  const rest = r.findings.slice(3);
  return (
    <section id="findings" className="space-y-4 scroll-mt-24">
      <h2 className="text-2xl font-bold">
        🔎 {r.findings.length === 0 ? "No problems found" : `${r.findings.length} thing${r.findings.length > 1 ? "s" : ""} to fix`}
      </h2>
      {top.map((f) => (
        <FindingCard key={f.rule_id} finding={f} onMoment={onMoment} />
      ))}
      {rest.length > 0 && (
        <More label={`${rest.length} more finding${rest.length > 1 ? "s" : ""}`}>
          {rest.map((f) => (
            <FindingCard key={f.rule_id} finding={f} onMoment={onMoment} />
          ))}
        </More>
      )}
      {r.passed.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="label">Good this game:</span>
          {r.passed.map((p) => (
            <span key={p.rule_id} className="chip border-good text-good">
              ✓ {p.habit}
            </span>
          ))}
        </div>
      )}
      {r.skipped.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="label">Not checked:</span>
          {r.skipped.map((p) => (
            <span key={p.rule_id} className="chip text-muted" title={p.reason ?? ""}>
              ? {p.habit} · {p.reason}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function Benchmarks({ r }: { r: Report }) {
  const b = r.benchmarks;
  return (
    <Section
      id="benchmarks"
      title="📊 You vs your rank"
      aside={b.bracket && <span className="text-dim">Same hero · badges {b.bracket[0]}–{b.bracket[1]} · last 30 days</span>}
    >
      {!b.available ? (
        <p className="text-dim">No rank data for this hero right now.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {b.tiles.map((t) => (
            <StatTile
              key={t.key}
              label={t.label}
              value={t.value}
              benchmark={t.benchmark}
              better={t.better}
              unit={t.key.endsWith("per_min") ? "/min" : ""}
            />
          ))}
        </div>
      )}
    </Section>
  );
}

function DeathMap({ r, onPick }: { r: Report; onPick: (t: number) => void }) {
  if (r.deaths.length === 0) return <p className="text-good font-bold">✓ You never died. Great job.</p>;
  const counts = { early: 0, mid: 0, late: 0 };
  r.deaths.forEach((d) => counts[d.phase]++);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,480px)_1fr]">
      <Minimap
        image={r.map.image}
        markers={r.deaths.map((d, i) => ({
          key: `d${i}`,
          left: d.left,
          top: d.top,
          color: PHASE[d.phase].color,
          label: `${clock(d.t)} · ${d.killer ? `killed by ${d.killer}` : "died"} · ${d.place}`,
          onClick: () => onPick(d.t),
        }))}
        caption="Click a death to see it on the timeline."
      />
      <div className="space-y-3">
        <ul className="space-y-2">
          {(Object.keys(PHASE) as (keyof typeof PHASE)[]).map((k) => (
            <li key={k} className="flex items-center gap-3 text-lg">
              <span className="inline-block h-4 w-4 rounded-full" style={{ background: PHASE[k].color }} />
              <span className="font-bold tnum w-6">{counts[k]}</span> {PHASE[k].label}
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted">
          Laning ends when the Guardian in your lane falls ({clock(r.phases.laning_end)}). Late game starts at the first
          Walker ({clock(r.phases.mid_end)}).
          {r.phases.est && <EstTag title="One of these objectives never fell, so a default time is used." />}
        </p>
      </div>
    </div>
  );
}

function Lane({ r }: { r: Report }) {
  const l = r.lane;
  return (
    <Section
      id="lane"
      title={`🛣 Lane phase${l.lane ? `: ${l.lane.name}` : ""}`}
      aside={
        <span className="text-dim">
          Ends {clock(l.laning_end)}
          {l.laning_end_est && <EstTag />}
        </span>
      }
    >
      <div className="flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="label">With</span>
          {l.partner.length ? l.partner.map((h) => <HeroIcon key={h.id} hero={h} size={40} />) : <span className="text-dim">solo</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="label">Against</span>
          {l.opponents.map((h) => (
            <span key={h.id} className="flex items-center gap-1">
              <HeroIcon hero={h} size={40} />
              <span className="text-dim">{h.name}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {l.checkpoints.map((c) => (
          <div key={c.t} className="rounded-xl bg-panel2 border border-line p-4">
            <div className="label">Souls at {clock(c.t)}</div>
            <div className="text-3xl font-bold tnum">{num(c.you)}</div>
            {c.avg != null && <div className="text-dim">Rank avg: {num(c.avg)}</div>}
            {c.lead != null && (
              <div className={`font-bold ${c.lead >= 0 ? "text-good" : "text-high"}`}>
                {c.lead >= 0 ? "▲" : "▼"} Lane {c.lead >= 0 ? "lead" : "behind"} {signed(c.lead).replace(/^[+−]/, "")}
              </div>
            )}
          </div>
        ))}
        <div className="rounded-xl bg-panel2 border border-line p-4">
          <div className="label">Deaths before 10:00</div>
          <div className={`text-3xl font-bold ${l.deaths_before_10 >= 3 ? "text-high" : "text-ink"}`}>{l.deaths_before_10}</div>
        </div>
      </div>
      <p className="text-sm text-muted">Snapshots exist every 3 minutes, so these are 6, 9 and 12 min marks.</p>
    </Section>
  );
}
