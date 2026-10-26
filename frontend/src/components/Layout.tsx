import { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

const NAV = [
  { to: "/", label: "Home", icon: "⌂" },
  { to: "/matches", label: "Matches", icon: "▤" },
  { to: "/trends", label: "Trends", icon: "↗" },
  { to: "/build", label: "Build Lab", icon: "🧪" },
  { to: "/map", label: "Map", icon: "🗺" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

const SOON = ["Learn"];

function PatchBanner() {
  const { data } = useQuery({ queryKey: ["meta"], queryFn: api.meta, staleTime: 5 * 60_000 });
  if (!data) return null;
  const { patch } = data;
  const date = patch.latest_patch?.date ? new Date(patch.latest_patch.date).toLocaleDateString() : null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="chip" title="Deadlock client build the game data comes from">
        Build {patch.cached_build ?? patch.live_build ?? "?"}
        {date && <span className="text-muted">· patch {date}</span>}
      </span>
      {patch.stale && (
        <Link to="/settings" className="chip border-low text-low font-bold">
          ⚠ New patch {patch.live_build}. Refresh data
        </Link>
      )}
      {data.offline && <span className="chip border-low text-low">Offline</span>}
    </div>
  );
}

function SampleBanner() {
  const { data } = useQuery({ queryKey: ["meta"], queryFn: api.meta, staleTime: 5 * 60_000 });
  if (!data?.using_sample) return null;
  return (
    <div className="bg-panel2 border-b border-line">
      <div className="mx-auto max-w-6xl px-4 py-2 text-dim">
        👀 Showing a sample player.{" "}
        <Link to="/settings" className="text-s1 font-bold hover:underline">
          Add your Steam ID →
        </Link>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 bg-bg/95 backdrop-blur border-b border-line">
        <div className="mx-auto max-w-6xl px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
          <Link to="/" className="text-xl font-bold tracking-tight">
            <span className="text-s1">◆</span> Deadlock Coach
          </Link>
          <nav className="flex flex-wrap gap-1" aria-label="Main">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-1.5 font-bold ${isActive ? "bg-panel2 text-ink" : "text-dim hover:text-ink"}`
                }
              >
                <span aria-hidden className="mr-1">
                  {n.icon}
                </span>
                {n.label}
              </NavLink>
            ))}
            {SOON.map((s) => (
              <span key={s} className="rounded-xl px-3 py-1.5 text-muted" title="Coming in a later phase">
                {s} <span className="text-xs">soon</span>
              </span>
            ))}
          </nav>
          <div className="ml-auto">
            <PatchBanner />
          </div>
        </div>
      </header>
      <SampleBanner />
      <main className="mx-auto max-w-6xl px-4 py-6 space-y-6">{children}</main>
    </div>
  );
}
