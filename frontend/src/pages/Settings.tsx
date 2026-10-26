import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type SteamHit } from "../lib/api";
import { ErrorBox, Loading, Section } from "../components/ui";

const SUBRANKS = [1, 2, 3, 4, 5, 6];

export default function Settings() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const [steam, setSteam] = useState("");
  const [search, setSearch] = useState("");
  const [hits, setHits] = useState<SteamHit[] | null>(null);
  const [lo, setLo] = useState(61);
  const [hi, setHi] = useState(76);

  useEffect(() => {
    if (q.data) {
      setLo(q.data.bracket[0]);
      setHi(q.data.bracket[1]);
    }
  }, [q.data]);

  const afterSave = () => {
    qc.invalidateQueries();
  };
  const save = useMutation({ mutationFn: api.saveSettings, onSuccess: afterSave });
  const refresh = useMutation({ mutationFn: api.refreshGameData, onSuccess: afterSave });
  const find = useMutation({ mutationFn: api.steamSearch, onSuccess: setHits });

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const s = q.data!;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">⚙ Settings</h1>

      <Section title="1. Your Steam account">
        {s.using_sample ? (
          <p className="text-dim">👀 Now showing a sample player. Add your own ID below.</p>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            {s.profile?.avatar && <img src={s.profile.avatar} alt="" className="h-12 w-12 rounded-xl" />}
            <div>
              <div className="text-xl font-bold">{s.profile?.name ?? "Your account"}</div>
              <div className="text-dim tnum">ID {s.account_id}</div>
            </div>
            <button type="button" className="btn ml-auto" onClick={() => save.mutate({ clear_account: true })}>
              Use sample player
            </button>
          </div>
        )}
        <form
          className="flex flex-wrap gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (steam.trim()) save.mutate({ steam_id: steam.trim() });
          }}
        >
          <label className="flex-1 min-w-[16rem]">
            <span className="label block mb-1">Steam ID or profile link</span>
            <input
              value={steam}
              onChange={(e) => setSteam(e.target.value)}
              placeholder="7656119… or steamcommunity.com/profiles/…"
              className="w-full rounded-xl bg-panel2 border border-line px-4 py-2 text-ink"
            />
          </label>
          <button type="submit" className="btn-primary self-end">
            Save
          </button>
        </form>
        <form
          className="flex flex-wrap gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (search.trim().length >= 2) find.mutate(search.trim());
          }}
        >
          <label className="flex-1 min-w-[16rem]">
            <span className="label block mb-1">Or search by Steam name</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl bg-panel2 border border-line px-4 py-2 text-ink"
            />
          </label>
          <button type="submit" className="btn self-end">
            🔍 Search
          </button>
        </form>
        {find.error && <ErrorBox error={find.error} />}
        {hits && (
          <ul className="space-y-2">
            {hits.length === 0 && <li className="text-dim">No players found.</li>}
            {hits.map((h) => (
              <li key={h.account_id}>
                <button
                  type="button"
                  className="btn w-full justify-start"
                  onClick={() => {
                    save.mutate({ steam_id: String(h.account_id) });
                    setHits(null);
                  }}
                >
                  {h.avatar && <img src={h.avatar} alt="" className="h-8 w-8 rounded-lg" />}
                  {h.name}
                  <span className="ml-auto text-dim text-sm">{h.matches_30d ?? 0} games in 30 days</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {save.error && <ErrorBox error={save.error} />}
      </Section>

      <Section title="2. Compare me with">
        <p className="text-dim">Benchmarks use players in this rank range.</p>
        <div className="flex flex-wrap items-end gap-4">
          <RankPicker label="From" value={lo} onChange={setLo} ranks={s.ranks} />
          <RankPicker label="To" value={hi} onChange={setHi} ranks={s.ranks} />
          <button type="button" className="btn-primary" onClick={() => save.mutate({ bracket: [lo, hi] })}>
            Save range
          </button>
        </div>
      </Section>

      <Section title="3. Game data">
        {meta.data && (
          <ul className="space-y-1 text-lg">
            <li>
              Live build: <b>{meta.data.patch.live_build ?? "unknown"}</b>
            </li>
            <li>
              Cached build: <b>{meta.data.patch.cached_build ?? "none"}</b>{" "}
              {meta.data.patch.stale ? <span className="text-low font-bold">⚠ out of date</span> : <span className="text-good">✓ current</span>}
            </li>
            {meta.data.patch.latest_patch && (
              <li>
                Latest patch:{" "}
                <a className="text-s1 hover:underline" href={meta.data.patch.latest_patch.link} target="_blank" rel="noreferrer">
                  {meta.data.patch.latest_patch.title}
                </a>
              </li>
            )}
          </ul>
        )}
        <button type="button" className="btn" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          ↻ {refresh.isPending ? "Refreshing…" : "Refresh game data"}
        </button>
        {refresh.error && <ErrorBox error={refresh.error} />}
      </Section>
    </div>
  );
}

function RankPicker({
  label,
  value,
  onChange,
  ranks,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  ranks: { tier: number; name: string }[];
}) {
  const tier = Math.floor(value / 10);
  const sub = value % 10 || 1;
  return (
    <fieldset className="flex items-end gap-2">
      <legend className="label mb-1">{label}</legend>
      <select
        aria-label={`${label} rank`}
        value={tier}
        onChange={(e) => onChange(Number(e.target.value) * 10 + sub)}
        className="rounded-xl bg-panel2 border border-line px-3 py-2 text-ink"
      >
        {ranks.map((r) => (
          <option key={r.tier} value={r.tier}>
            {r.name}
          </option>
        ))}
      </select>
      <select
        aria-label={`${label} sub-rank`}
        value={sub}
        onChange={(e) => onChange(tier * 10 + Number(e.target.value))}
        className="rounded-xl bg-panel2 border border-line px-3 py-2 text-ink"
      >
        {SUBRANKS.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </fieldset>
  );
}
