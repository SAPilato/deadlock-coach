import { useState } from "react";
import type { HeroCard } from "../../lib/api";
import { HeroIcon } from "../ui";

export default function HeroPicker({
  heroes,
  value,
  onChange,
}: {
  heroes: HeroCard[];
  value: number;
  onChange: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const current = heroes.find((h) => h.id === value);
  const shown = heroes.filter((h) => h.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="space-y-3">
      <button type="button" className="btn" onClick={() => setOpen(!open)} aria-expanded={open}>
        {current && <HeroIcon hero={current} size={40} />}
        <span className="text-xl">{current?.name ?? "Pick a hero"}</span>
        <span className="text-dim">{open ? "▴" : "▾ Change"}</span>
      </button>
      {open && (
        <div className="rounded-xl bg-panel2 border border-line p-3 space-y-3">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search heroes"
            aria-label="Search heroes"
            className="w-full rounded-lg bg-bg border border-line px-3 py-2"
          />
          <div className="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] gap-2">
            {shown.map((h) => (
              <button
                key={h.id}
                type="button"
                onClick={() => {
                  onChange(h.id);
                  setOpen(false);
                  setQ("");
                }}
                className={`flex flex-col items-center gap-1 rounded-lg p-2 border ${
                  h.id === value ? "border-accent bg-bg" : "border-transparent hover:border-line"
                }`}
              >
                <HeroIcon hero={h} size={48} />
                <span className="text-sm text-center leading-tight">{h.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
