import { useRef } from "react";
import type { HeroCard, SavedBuild } from "../../lib/api";
import { api } from "../../lib/api";
import { ago } from "../../lib/format";
import { HeroIcon } from "../ui";

export default function SavedBuilds({
  builds,
  heroes,
  currentId,
  compareId,
  onLoad,
  onCompare,
  onDelete,
  onImport,
}: {
  builds: SavedBuild[];
  heroes: Map<number, HeroCard>;
  currentId: number | null;
  compareId: number | null;
  onLoad: (b: SavedBuild) => void;
  onCompare: (id: number | null) => void;
  onDelete: (b: SavedBuild) => void;
  onImport: (data: unknown) => void;
}) {
  const file = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          ref={file}
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            try {
              onImport(JSON.parse(await f.text()));
            } finally {
              e.target.value = "";
            }
          }}
        />
        <button type="button" className="btn" onClick={() => file.current?.click()}>
          ⬆ Import build file
        </button>
      </div>
      {builds.length === 0 ? (
        <p className="text-dim">No saved builds yet.</p>
      ) : (
        <ul className="space-y-2">
          {builds.map((b) => {
            const hero = heroes.get(b.hero_id);
            return (
              <li
                key={b.id}
                className={`flex flex-wrap items-center gap-3 rounded-xl border bg-panel2 p-3 ${
                  b.id === currentId ? "border-s1" : "border-line"
                }`}
              >
                {hero && <HeroIcon hero={hero} size={36} />}
                <div className="min-w-0">
                  <div className="font-bold truncate">{b.name}</div>
                  <div className="text-sm text-dim">
                    {hero?.name} · level {b.level} · {b.items.length} items · {ago(b.updated_at)}
                  </div>
                </div>
                <div className="ml-auto flex flex-wrap gap-2">
                  <button type="button" className="chip hover:border-s1" onClick={() => onLoad(b)}>
                    Open
                  </button>
                  <button
                    type="button"
                    className={`chip hover:border-s1 ${compareId === b.id ? "border-s1 text-s1" : ""}`}
                    onClick={() => onCompare(compareId === b.id ? null : b.id)}
                    aria-pressed={compareId === b.id}
                  >
                    ⇄ Compare
                  </button>
                  <a className="chip hover:border-s1" href={api.exportUrl(b.id)} download>
                    ⬇ Export
                  </a>
                  <button type="button" className="chip hover:border-high" onClick={() => onDelete(b)}>
                    🗑 Delete
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
