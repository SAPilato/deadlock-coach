import { useMemo, useState } from "react";
import type { ShopData, ShopItem, SlotType } from "../../lib/api";
import { clock } from "../../lib/format";
import { CATEGORY, SLOT_TYPES, souls } from "./common";
import { Check } from "lucide-react";
import { Icon } from "../ui";

type Sort = "tier" | "win" | "pick";

export default function Shop({
  shop,
  inBuild,
  full,
  onAdd,
  onPreview,
}: {
  shop: ShopData;
  inBuild: Set<number>;
  full: boolean;
  onAdd: (id: number) => void;
  onPreview: (id: number | null) => void;
}) {
  const [cat, setCat] = useState<SlotType>("weapon");
  const [tier, setTier] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("tier");

  const tiers = useMemo(() => [...new Set(shop.items.map((i) => i.tier))].sort(), [shop]);
  const list = useMemo(() => {
    const rows = shop.items.filter(
      (i) => i.slot === cat && (tier == null || i.tier === tier) && i.name.toLowerCase().includes(q.toLowerCase()),
    );
    const key = (i: ShopItem) => (sort === "win" ? -(i.win_rate ?? -1) : sort === "pick" ? -(i.pick_rate ?? -1) : i.tier);
    return rows.sort((a, b) => key(a) - key(b) || a.cost - b.cost || a.name.localeCompare(b.name));
  }, [shop, cat, tier, q, sort]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Item category">
        {SLOT_TYPES.map((s) => {
          const c = CATEGORY[s];
          const on = s === cat;
          return (
            <button
              key={s}
              role="tab"
              aria-selected={on}
              type="button"
              onClick={() => setCat(s)}
              className={`rounded-xl border-2 px-4 py-2 font-bold ${on ? `${c.border} bg-panel2 ${c.text}` : "border-line text-dim"}`}
            >
              <Icon icon={c.icon} /> {c.label}
            </button>
          );
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={`chip ${tier == null ? "border-accent" : ""}`} onClick={() => setTier(null)}>
          All tiers
        </button>
        {tiers.map((t) => (
          <button key={t} type="button" className={`chip ${tier === t ? "border-accent" : ""}`} onClick={() => setTier(t)}>
            Tier {t}
          </button>
        ))}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search items"
          aria-label="Search items"
          className="ml-auto rounded-lg bg-panel2 border border-line px-3 py-1.5"
        />
        <label className="text-sm text-dim">
          Sort{" "}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="rounded-lg bg-panel2 border border-line px-2 py-1.5 text-ink"
          >
            <option value="tier">Tier</option>
            <option value="win">Win rate</option>
            <option value="pick">Most bought</option>
          </select>
        </label>
      </div>
      {!shop.has_rank_stats && <p className="text-sm text-muted">No win rates right now (offline or no rank data).</p>}
      <p className="text-sm text-dim">
        {list.length} items. Scroll the list. Click to add, hover to preview.
      </p>
      <ul
        className="grid max-h-[min(70vh,40rem)] gap-2 overflow-y-auto pr-1 sm:grid-cols-2"
        onMouseLeave={() => onPreview(null)}
        aria-label="Items"
      >
        {list.map((it) => {
          const owned = inBuild.has(it.id);
          return (
            <li key={it.id}>
              <button
                type="button"
                disabled={owned || full}
                onClick={() => onAdd(it.id)}
                onMouseEnter={() => onPreview(owned ? null : it.id)}
                onFocus={() => onPreview(owned ? null : it.id)}
                onBlur={() => onPreview(null)}
                className={`flex w-full gap-3 rounded-xl border bg-panel2 p-3 text-left ${
                  owned ? "border-good opacity-70" : "border-line hover:border-accent"
                } disabled:cursor-not-allowed`}
              >
                {it.image && <img src={it.image} alt="" className="h-12 w-12 shrink-0 rounded-md" />}
                <span className="min-w-0 flex-1 space-y-1">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-bold">{it.name}</span>
                    <span className="text-sm text-muted">T{it.tier}</span>
                    {it.active && <span className="text-xs chip py-0">Active</span>}
                  </span>
                  <span className="flex flex-wrap gap-x-3 text-sm">
                    <span className="text-low tnum">◆ {souls(it.cost)}</span>
                    {it.win_rate != null && (
                      <span className="tnum" title={`${it.games?.toLocaleString()} games at your rank`}>
                        {Math.round(it.win_rate * 100)}% win
                      </span>
                    )}
                    {it.pick_rate != null && (
                      <span className="tnum text-dim">
                        in {it.pick_rate < 0.01 ? "<1" : Math.round(it.pick_rate * 100)}% of games
                      </span>
                    )}
                    {it.avg_buy_s != null && <span className="tnum text-dim">~{clock(it.avg_buy_s)}</span>}
                  </span>
                  {it.lines.length > 0 && <span className="block text-sm text-dim truncate">{it.lines.join(" · ")}</span>}
                </span>
                <span className="self-center text-sm font-bold text-accent">{owned ? <Icon icon={Check} /> : "+ Add"}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="text-sm text-muted">Win rate is raw. Players who are ahead buy more items.</p>
    </div>
  );
}
