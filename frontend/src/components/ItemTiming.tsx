import type { Report } from "../lib/api";
import { clock, signed } from "../lib/format";

const EARLY = "#3987e5";
const LATE = "#e66767";

/** Diverging bars: each item's buy time minus the rank average, centred on zero. */
export default function ItemTiming({ items, onPick }: { items: Report["items"]; onPick: (t: number) => void }) {
  const rows = items.filter((i) => i.delta != null);
  const others = items.filter((i) => i.delta == null);
  const maxAbs = Math.max(240, ...rows.map((r) => Math.abs(r.delta!)));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4 text-sm text-dim">
        <span><span style={{ color: EARLY }}>■</span> Earlier than average</span>
        <span><span style={{ color: LATE }}>■</span> Later than average</span>
        <span>★ Core item for this hero</span>
      </div>
      {rows.length === 0 && <p className="text-dim">No rank timing data for these items yet.</p>}
      <ul className="space-y-2">
        {rows.map((r, i) => {
          const d = r.delta!;
          const width = (Math.abs(d) / maxAbs) * 50;
          return (
            <li key={`${r.item_id}-${i}`}>
              <button
                type="button"
                onClick={() => onPick(r.t)}
                className="grid w-full grid-cols-[minmax(9rem,14rem)_1fr_6.5rem] items-center gap-3 rounded-lg px-2 py-1 text-left hover:bg-panel2"
                title={`You ${clock(r.t)} · average ${clock(r.avg_t)}`}
              >
                <span className="flex items-center gap-2 min-w-0">
                  {r.image && <img src={r.image} alt="" className="h-8 w-8 rounded-md bg-panel2" />}
                  <span className="truncate">
                    {r.core && <span className="text-low" aria-label="core item">★ </span>}
                    {r.name}
                  </span>
                </span>
                <span className="relative h-6" aria-hidden>
                  <span className="absolute left-1/2 top-0 h-full w-px bg-line" />
                  <span
                    className="absolute top-1 h-4 rounded-sm"
                    style={{
                      background: d > 0 ? LATE : EARLY,
                      width: `${width}%`,
                      left: d > 0 ? "50%" : `${50 - width}%`,
                    }}
                  />
                </span>
                <span className={`tnum font-bold ${d > 60 ? "text-neg" : d < -60 ? "text-s1" : "text-dim"}`}>
                  {signed(d, clock)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {others.length > 0 && (
        <p className="text-sm text-muted">
          Also bought: {others.map((o) => `${o.name} (${clock(o.t)})`).join(", ")}.
        </p>
      )}
    </div>
  );
}
