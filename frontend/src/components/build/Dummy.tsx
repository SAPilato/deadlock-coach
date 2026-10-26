import type { Sheet, Target } from "../../lib/api";
import { num } from "../../lib/format";
import { EstTag, Icon } from "../ui";
import { Crosshair, Shield, Target as TargetIcon } from "lucide-react";

function Slider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="flex justify-between">
        <span className="label">{label}</span>
        <span className="font-bold tnum">
          {num(value)}
          {unit}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-accent"
      />
    </label>
  );
}

function Big({ label, value, est = true }: { label: string; value: string; est?: boolean }) {
  return (
    <div className="rounded-xl bg-panel2 border border-line p-4">
      <div className="label">{label}</div>
      <div className="text-3xl font-bold tnum">
        {value}
        {est && <EstTag />}
      </div>
    </div>
  );
}

export default function Dummy({
  target,
  onChange,
  sheet,
}: {
  target: Target;
  onChange: (t: Target) => void;
  sheet: Sheet | undefined;
}) {
  const d = sheet?.dps;
  const gunEst = sheet?.rows.find((r) => r.key === "gun_dps")?.status === "est";
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_1fr]">
      <div className="space-y-4">
        <Slider label="Dummy health" value={target.hp} min={500} max={8000} step={100} unit="" onChange={(hp) => onChange({ ...target, hp })} />
        <Slider
          label="Dummy bullet resist"
          value={target.bullet_resist}
          min={-30}
          max={80}
          step={1}
          unit="%"
          onChange={(bullet_resist) => onChange({ ...target, bullet_resist })}
        />
        <Slider
          label="Your headshots"
          value={target.headshot_pct}
          min={0}
          max={100}
          step={5}
          unit="%"
          onChange={(headshot_pct) => onChange({ ...target, headshot_pct })}
        />
      </div>
      {d && (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Big label="Time to kill" value={d.ttk != null ? `${num(d.ttk, 1)} s` : "–"} />
            <Big label="DPS vs dummy" value={num(d.effective, 1)} />
            <Big label="Gun DPS" value={num(d.gun_dps, 1)} est={gunEst} />
            <Big label="Gun DPS with reloads" value={num(d.dps_reload, 1)} />
          </div>
          <ul className="space-y-1 text-sm text-dim">
            <li>
          <Icon icon={TargetIcon} /> Headshots deal ×{num(d.headshot_mult, 2)} (weapon data). Close range, no falloff.</li>
            <li>
              <Icon icon={Shield} /> Dummy resist after your shred: <b className="text-ink">{num(d.target_resist, 1)}%</b>
              {d.shred > 0 && <> (shred {num(d.shred, 1)}%)</>}
            </li>
            <li>
          <Icon icon={Crosshair} /> Gun only. Ability and item damage are not counted.</li>
          </ul>
        </div>
      )}
    </div>
  );
}
