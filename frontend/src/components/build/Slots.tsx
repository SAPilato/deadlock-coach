import type { ShopItem } from "../../lib/api";
import { CATEGORY, souls } from "./common";
import { X } from "lucide-react";
import { Icon } from "../ui";

export default function Slots({
  items,
  limit,
  limitEst,
  cost,
  onRemove,
}: {
  items: ShopItem[];
  limit: number;
  limitEst: boolean;
  cost: number;
  onRemove: (id: number) => void;
}) {
  const empty = Math.max(0, limit - items.length);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <span className="text-2xl font-bold tnum">
          {items.length} / {limit}
          <span className="text-base font-normal text-dim"> slots</span>
        </span>
        <span className="text-2xl font-bold tnum">
          {souls(cost)}
          <span className="text-base font-normal text-dim"> souls</span>
        </span>
        <span className="text-sm text-muted" title="Most items players held at once in recent matches.">
          {limitEst ? "Slot count est." : "Slot count from real matches"}
        </span>
      </div>
      <ul className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2" aria-label="Build slots">
        {items.map((it) => {
          const c = CATEGORY[it.slot];
          return (
            <li key={it.id}>
              <button
                type="button"
                onClick={() => onRemove(it.id)}
                title={`Remove ${it.name}`}
                aria-label={`Remove ${it.name}`}
                className={`group relative flex h-full w-full flex-col items-center gap-1 rounded-xl border-2 ${c.border} bg-panel2 p-2 hover:bg-bg`}
              >
                {it.image && <img src={it.image} alt="" className="h-10 w-10 rounded-md" />}
                <span className="text-xs text-center leading-tight">{it.name}</span>
                <span className="absolute right-1 top-0.5 text-sm text-muted group-hover:text-high" aria-hidden>
                  <Icon icon={X} />
                </span>
              </button>
            </li>
          );
        })}
        {Array.from({ length: empty }).map((_, i) => (
          <li key={`e${i}`} className="grid min-h-[5.5rem] place-items-center rounded-xl border-2 border-dashed border-line text-muted text-sm">
            empty
          </li>
        ))}
      </ul>
    </div>
  );
}
