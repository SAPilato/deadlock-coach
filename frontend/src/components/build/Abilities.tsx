import type { Sheet } from "../../lib/api";
import { num, statDelta } from "../../lib/format";
import { EstTag } from "../ui";

const SCALING: Record<string, string> = {
  EWeaponPower: "weapon damage",
  EBaseWeaponDamageIncrease: "weapon damage",
  ELightMeleeDamage: "light melee",
  EHeavyMeleeDamage: "heavy melee",
  ELevelUpBoons: "level",
};

export default function Abilities({
  sheet,
  tier,
  onTier,
  spiritResist,
  onSpiritResist,
}: {
  sheet: Sheet | undefined;
  tier: number;
  onTier: (t: number) => void;
  spiritResist: number;
  onSpiritResist: (v: number) => void;
}) {
  if (!sheet) return null;
  const spirit = sheet.rows.find((r) => r.key === "spirit_power")?.value ?? 0;
  const cdr = sheet.rows.find((r) => r.key === "cooldown_reduction")?.value ?? 0;
  const amp = sheet.dps.spirit_amp;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-6">
        <div>
          <span className="label block mb-1">Ability upgrades bought</span>
          <div className="flex gap-1" role="radiogroup" aria-label="Ability upgrades">
            {[0, 1, 2, 3].map((t) => (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={tier === t}
                onClick={() => onTier(t)}
                className={`h-10 w-10 rounded-lg border-2 font-bold ${tier === t ? "border-s1 bg-panel2" : "border-line text-dim"}`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <label className="min-w-[14rem]">
          <span className="flex justify-between">
            <span className="label">Dummy spirit resist</span>
            <b className="tnum">{num(spiritResist)}%</b>
          </span>
          <input
            type="range"
            min={-30}
            max={80}
            step={1}
            value={spiritResist}
            onChange={(e) => onSpiritResist(Number(e.target.value))}
            className="w-full accent-[#3987e5]"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-3 text-lg">
        <span className="chip">
          ✦ Spirit power <b className="ml-1 tnum">{num(spirit, 1)}</b>
        </span>
        <span className="chip">
          ⟳ Cooldown −<b className="tnum">{num(cdr, 1)}%</b>
        </span>
        {amp !== 1 && (
          <span className="chip">
            × Spirit damage <b className="ml-1 tnum">{num(amp, 2)}</b>
          </span>
        )}
        {sheet.dps.spirit_shred > 0 && <span className="chip">🛡 Shred −{num(sheet.dps.spirit_shred, 1)}%</span>}
      </div>

      <ul className="grid gap-3 md:grid-cols-2">
        {sheet.abilities.map((a) => (
          <li key={a.name} className="rounded-xl bg-panel2 border border-line p-4 space-y-2">
            <div className="flex items-center gap-3">
              {a.image && <img src={a.image} alt="" className="h-10 w-10 rounded-lg bg-bg" />}
              <span className="text-lg font-bold">{a.name}</span>
              {a.cooldown != null && (
                <span className="ml-auto text-dim tnum" title="Cooldown: no items → this build">
                  ⟳ {num(a.cooldown_base, 1)} → <b className="text-ink">{num(a.cooldown, 1)} s</b>
                </span>
              )}
            </div>
            {a.lines.length === 0 ? (
              <p className="text-dim">No direct damage.</p>
            ) : (
              <table className="w-full tnum">
                <thead>
                  <tr className="text-xs text-muted">
                    <th className="text-left font-normal">Damage</th>
                    <th className="text-right font-normal">No items</th>
                    <th className="text-right font-normal">Build</th>
                    <th className="text-right font-normal">Vs dummy</th>
                  </tr>
                </thead>
                <tbody>
                  {a.lines.map((l) => {
                    const delta = statDelta(l.base, l.value, "");
                    return (
                      <tr key={l.label} className="border-t border-line">
                        <td className="py-1 pr-2">
                          {l.label}
                          <div className="text-xs text-muted">
                            {l.factor > 0
                              ? `+${num(l.factor, 2)} per spirit`
                              : l.other_scaling
                                ? `scales with ${SCALING[l.other_scaling] ?? l.other_scaling} (not shown)`
                                : "no spirit scaling"}
                          </div>
                        </td>
                        <td className="py-1 text-right text-dim">{num(l.base, 1)}</td>
                        <td className="py-1 text-right font-bold">
                          {num(l.value, 1)}
                          {delta && <div className="text-xs text-good">▲ {delta}</div>}
                        </td>
                        <td className="py-1 text-right">
                          {num(l.vs_dummy, 1)}
                          <EstTag />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted">
        Damage = base + scaling × spirit power (game data). Upgrades apply to all four abilities.
      </p>
    </div>
  );
}
