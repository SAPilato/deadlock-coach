import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ago, clock, num } from "../lib/format";
import { ErrorBox, HeroIcon, Icon, Loading, RankBadge, WinLoss } from "../components/ui";
import { List, RotateCw, Timer } from "lucide-react";

export default function Matches() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["matches"], queryFn: () => api.matches() });

  const refresh = async () => {
    const data = await api.matches(true);
    qc.setQueryData(["matches"], data);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">
          <Icon icon={List} className="text-accent" /> Matches
        </h1>
        {q.data && <span className="chip">{q.data.matches.length} games</span>}
        <button type="button" className="btn ml-auto" onClick={refresh}>
          <Icon icon={RotateCw} /> Refresh
        </button>
      </div>
      {q.isLoading && <Loading />}
      {q.error && <ErrorBox error={q.error} />}
      <ul className="space-y-2">
        {q.data?.matches.map((m) => {
          const row = (
            <div className="grid grid-cols-[auto_1fr_auto] sm:grid-cols-[auto_12rem_8rem_8rem_7rem_1fr] items-center gap-x-5 gap-y-1">
              <HeroIcon hero={m.hero} size={52} />
              <div>
                <div className="text-lg font-bold">{m.hero.name}</div>
                <div className="text-sm text-dim">
                  {ago(m.start_time)} · {m.mode}
                </div>
              </div>
              <WinLoss won={m.won} />
              <div>
                <div className="label">K/D/A</div>
                <div className="font-bold tnum">
                  {m.kills}/{m.deaths}/{m.assists}
                </div>
              </div>
              <div>
                <div className="label">Souls/min</div>
                <div className="font-bold tnum">{num(m.souls_per_min)}</div>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-3">
                <span className="tnum text-dim"><Icon icon={Timer} /> {clock(m.duration_s)}</span>
                <RankBadge rank={m.rank} size={28} />
              </div>
            </div>
          );
          return (
            <li key={m.match_id}>
              {m.street_brawl ? (
                <div className="card opacity-60" title="Street Brawl games are not reviewed">
                  {row}
                  <div className="text-sm text-muted mt-1">Street Brawl: not reviewed.</div>
                </div>
              ) : (
                <Link to={`/matches/${m.match_id}`} className="card block hover:border-accent">
                  {row}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
