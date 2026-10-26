import { useSearchParams } from "react-router-dom";
import ExploreMode from "../components/map/ExploreMode";
import RouteMode from "../components/map/RouteMode";
import WavesMode from "../components/map/WavesMode";
import HeatmapMode from "../components/map/HeatmapMode";
import ScenarioMode from "../components/map/ScenarioMode";

const MODES = [
  { id: "explore", label: "🗺 Explore", blurb: "Every camp, objective and shortcut on the current map." },
  { id: "route", label: "🧭 Routes", blurb: "Optimal movement or zipline: which gets you there faster?" },
  { id: "waves", label: "🌊 Waves", blurb: "Real trooper waves from a replay. See where they meet." },
  { id: "heatmap", label: "🔥 Your heatmap", blurb: "Where you spend your time in each phase." },
  { id: "decide", label: "🤔 What would you do?", blurb: "Real moments from your games. Pick, then see what happened." },
] as const;

type Mode = (typeof MODES)[number]["id"];

export default function MacroMap() {
  const [params, setParams] = useSearchParams();
  const mode = (MODES.find((m) => m.id === params.get("mode"))?.id ?? "explore") as Mode;
  const current = MODES.find((m) => m.id === mode)!;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">🗺 Macro Map</h1>
        <span className="text-dim">{current.blurb}</span>
      </div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Map mode">
        {MODES.map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-selected={mode === m.id}
            type="button"
            onClick={() => setParams({ mode: m.id })}
            className={`rounded-xl border-2 px-4 py-2 font-bold ${mode === m.id ? "border-s1 bg-panel2" : "border-line text-dim hover:text-ink"}`}
          >
            {m.label}
          </button>
        ))}
      </div>
      <section className="card">
        {mode === "explore" && <ExploreMode />}
        {mode === "route" && <RouteMode />}
        {mode === "waves" && <WavesMode />}
        {mode === "heatmap" && <HeatmapMode />}
        {mode === "decide" && <ScenarioMode />}
      </section>
    </div>
  );
}
