import { useState } from "react";
import type { Sheet, StatRow } from "../../lib/api";
import { statDelta, statValue } from "../../lib/format";
import { EstTag } from "../ui";

// Shown by default; the rest sit behind "All stats".
const KEY_STATS = new Set([
  "gun_dps", "bullet_damage", "fire_rate", "clip_size", "reload_time",
  "max_health", "bullet_resist", "spirit_resist", "move_speed",
  "spirit_power", "cooldown_reduction",
]);
const GROUPS: StatRow["group"][] = ["Weapon", "Vitality", "Spirit", "Spending"];

export default function StatTable({
  before,
  after,
  beforeLabel,
  afterLabel,
}: {
  before: Sheet | undefined;
  after: Sheet | undefined;
  beforeLabel: string;
  afterLabel: string;
}) {
  const [all, setAll] = useState(false);
  if (!after) return null;
  const prev = new Map((before?.rows ?? []).map((r) => [r.key, r]));
  const rows = after.rows.filter((r) => all || KEY_STATS.has(r.key) || changed(prev.get(r.key), r));

  return (
    <div className="space-y-3">
      <table className="w-full text-left tnum">
        <thead>
          <tr className="text-sm text-muted">
            <th className="py-1 font-normal">Stat</th>
            <th className="py-1 font-normal text-right">{beforeLabel}</th>
            <th className="py-1 font-normal text-right">{afterLabel}</th>
            <th className="py-1 font-normal text-right">Change</th>
          </tr>
        </thead>
        {GROUPS.map((g) => {
          const group = rows.filter((r) => r.group === g);
          if (!group.length) return null;
          return (
            <tbody key={g}>
              <tr>
                <th colSpan={4} className="label pt-3 pb-1">
                  {g}
                </th>
              </tr>
              {group.map((r) => {
                const b = prev.get(r.key);
                const delta = statDelta(b?.value ?? null, r.value, r.unit);
                const up = (r.value ?? 0) > (b?.value ?? 0);
                const good = (r.better === "higher") === up;
                return (
                  <tr key={r.key} className={`border-t border-line ${delta ? "bg-panel2" : ""}`}>
                    <td className="py-1.5 pr-2" title={r.note ?? undefined}>
                      {r.label}
                      {(r.status === "est" || b?.status === "est") && <EstTag />}
                    </td>
                    <td className="py-1.5 text-right text-dim">{b ? statValue(b.value, b.unit) : "–"}</td>
                    <td className="py-1.5 text-right font-bold">{statValue(r.value, r.unit)}</td>
                    <td className={`py-1.5 pl-2 text-right font-bold ${delta ? (good ? "text-good" : "text-high") : "text-muted"}`}>
                      {delta ? (
                        <>
                          <span aria-hidden>{good ? "▲" : "▼"}</span> {delta}
                          <span className="sr-only">{good ? " better" : " worse"}</span>
                        </>
                      ) : (
                        "·"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          );
        })}
      </table>
      <button type="button" className="text-accent font-bold hover:underline" onClick={() => setAll(!all)}>
        {all ? "Key stats only ▴" : "All stats ▾"}
      </button>
    </div>
  );
}

function changed(b: StatRow | undefined, a: StatRow): boolean {
  return b?.value != null && a.value != null && Math.abs(a.value - b.value) > 1e-6;
}
