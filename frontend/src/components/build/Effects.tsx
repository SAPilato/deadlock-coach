import type { EffectInfo } from "../../lib/api";

function valueText(e: EffectInfo): string {
  const unit = ["%", "m", "m/s", "s"].includes(e.postfix) ? e.postfix : "";
  return `${e.value > 0 ? "+" : ""}${e.value}${unit}`;
}

export default function Effects({
  effects,
  toggles,
  onToggle,
}: {
  effects: EffectInfo[];
  toggles: Set<string>;
  onToggle: (key: string) => void;
}) {
  const switchable = effects.filter((e) => e.kind !== "always" && e.target !== "ability");
  const abilityOnly = effects.filter((e) => e.target === "ability");
  const byItem = new Map<string, EffectInfo[]>();
  switchable.forEach((e) => byItem.set(e.item, [...(byItem.get(e.item) ?? []), e]));
  const info =
    abilityOnly.length > 0 ? (
      <div>
        <div className="label mb-1">Only for some abilities (not in stats)</div>
        <ul className="space-y-1 text-dim">
          {abilityOnly.map((e) => (
            <li key={e.key}>
              <b className="text-ink tnum">{valueText(e)}</b> {e.label} · {e.item}
            </li>
          ))}
        </ul>
      </div>
    ) : null;
  if (!switchable.length) {
    return (
      <div className="space-y-3">
        <p className="text-dim">No conditional effects in this build.</p>
        {info}
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-dim">Switch on the effects you expect in a fight.</p>
      <ul className="grid gap-3 md:grid-cols-2">
        {[...byItem.entries()].map(([item, list]) => (
          <li key={item} className="rounded-xl bg-panel2 border border-line p-3 space-y-2">
            <div className="font-bold">{item}</div>
            {list.map((e) => {
              const on = toggles.has(e.key);
              const when =
                e.kind === "active" ? "while active" : e.condition ? e.condition : "when it triggers";
              return (
                <label key={e.key} className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={() => onToggle(e.key)}
                    className="h-5 w-5 accent-[#3987e5]"
                  />
                  <span>
                    <b className="tnum">{valueText(e)}</b> {e.label}
                    <span className="text-dim"> · {when}</span>
                    {e.target === "enemy" && <span className="ml-2 chip py-0 text-sm text-low">on enemy</span>}
                  </span>
                </label>
              );
            })}
          </li>
        ))}
      </ul>
      {info}
    </div>
  );
}
