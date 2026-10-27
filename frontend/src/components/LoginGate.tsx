import { ReactNode, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole } from "lucide-react";
import { api, ApiError, LOGIN_REQUIRED } from "../lib/api";
import { Icon, Loading } from "./ui";

/** When the app is shared through a tunnel, nothing loads until you log in. Locally it is open. */
export default function LoginGate({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["auth"], queryFn: api.authStatus, staleTime: Infinity, retry: 0 });
  // Any API call that comes back "login required" (say the session ran out) shows the login again.
  useEffect(() => {
    const on = () => qc.invalidateQueries({ queryKey: ["auth"] });
    window.addEventListener(LOGIN_REQUIRED, on);
    return () => window.removeEventListener(LOGIN_REQUIRED, on);
  }, [qc]);

  if (status.isLoading) return <Loading label="Starting…" />;
  if (status.data?.required && !status.data.logged_in) return <Login onDone={() => qc.invalidateQueries()} />;
  return <>{children}</>;
}

function Login({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <main className="mx-auto mt-[15vh] max-w-md px-4">
      <form
        className="card space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await api.login(password);
            setPassword("");
            onDone();
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Could not reach the app. Is it still running on your PC?");
          } finally {
            setBusy(false);
          }
        }}
      >
        <h1 className="text-3xl font-bold">
          <Icon icon={LockKeyhole} className="text-accent" /> Deadlock Coach
        </h1>
        <p className="text-dim">Enter your app password.</p>
        <label className="block">
          <span className="label">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-xl border border-line bg-panel2 px-3 py-2 text-ink"
          />
        </label>
        {error && (
          <p className="font-bold text-high" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn-primary w-full justify-center" disabled={busy || !password}>
          {busy ? "Checking…" : "Log in"}
        </button>
      </form>
    </main>
  );
}
