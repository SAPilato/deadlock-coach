import { Check, Target } from "lucide-react";
import { applyTheme, THEMES, TONES, useTheme } from "../lib/theme";
import { Icon } from "./ui";

/** Each option is drawn in its own theme (data-theme on the button scopes the colours and fonts). */
export default function ThemePicker() {
  const current = useTheme();
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {THEMES.map((t) => {
        const on = t.id === current;
        return (
          <button
            key={t.id}
            type="button"
            data-theme={t.id}
            aria-pressed={on}
            onClick={() => applyTheme(t.id)}
            className={`flex flex-col rounded-2xl border-2 bg-bg p-3 text-left text-ink ${on ? "border-accent" : "border-line hover:border-accent"}`}
          >
            <div className="card flex-1 space-y-3 p-4">
              <div className="flex items-center gap-2">
                <h3 className="font-display text-2xl font-bold">{t.name}</h3>
                {on && (
                  <span className="chip ml-auto border-accent font-bold text-accent">
                    <Icon icon={Check} /> In use
                  </span>
                )}
              </div>
              <p className="text-dim">{t.blurb}</p>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-xl bg-accent px-3 py-1 font-bold text-onaccent">
                  <Icon icon={Target} /> Next game
                </span>
                <span className="chip font-bold text-high">▲ High</span>
                <span className="chip font-bold text-good">
                  <Icon icon={Check} /> Good
                </span>
              </div>
              <p className="text-dim">
                <b className="text-3xl text-ink tnum">3 of 10</b> recent games
              </p>
              {t.id === "deco" && (
                <ul className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-dim" aria-label="Tab tones">
                  {TONES.map((tone) => (
                    <li key={tone.id} data-tone={tone.id} className="inline-flex items-center gap-1">
                      <span className="inline-block h-3 w-3 rounded-full bg-accent" aria-hidden /> {tone.name}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
