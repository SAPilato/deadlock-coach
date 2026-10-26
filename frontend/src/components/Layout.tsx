import { ReactNode, useLayoutEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { applyTone, toneFor } from "../lib/theme";
import { BookOpen, Eye, FlaskConical, House, List, Map as MapIcon, Settings as SettingsIcon, TrendingUp, TriangleAlert } from "lucide-react";
import { Icon } from "./ui";
import ErrorBoundary from "./ErrorBoundary";

const NAV = [
  { to: "/", label: "Home", icon: House },
  { to: "/matches", label: "Matches", icon: List },
  { to: "/trends", label: "Trends", icon: TrendingUp },
  { to: "/build", label: "Build Lab", icon: FlaskConical },
  { to: "/map", label: "Map", icon: MapIcon },
  { to: "/learn", label: "Learn", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

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
          <Icon icon={TriangleAlert} /> New patch {patch.live_build}. Refresh data
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
        <Icon icon={Eye} /> Showing a sample player.{" "}
        <Link to="/settings" className="text-accent font-bold hover:underline">
          Add your Steam ID →
        </Link>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  // Brass Deco: each tab has its own tone. Layout effect so the new tone lands before paint.
  useLayoutEffect(() => {
    applyTone(pathname);
  }, [pathname]);
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 bg-bg/95 backdrop-blur border-b border-line">
        <div className="mx-auto max-w-6xl px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
          <Link to="/" className="font-display text-xl font-bold tracking-tight">
            <span className="text-accent">◆</span> Deadlock Coach
          </Link>
          <nav className="flex flex-wrap gap-1" aria-label="Main">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-tone={toneFor(n.to)}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-1.5 font-bold ${isActive ? "bg-panel2 text-ink shadow-[inset_0_-2px_0_rgb(var(--c-accent))]" : "text-dim hover:text-ink"}`
                }
              >
                <Icon icon={n.icon} className="mr-1.5 text-accent" />
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <PatchBanner />
          </div>
        </div>
      </header>
      <SampleBanner />
      <main className="mx-auto max-w-6xl px-4 py-6 space-y-6">
        <ErrorBoundary key={pathname}>{children}</ErrorBoundary>
      </main>
    </div>
  );
}
