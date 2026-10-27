// `npm run share`: open the app on your phone (or anywhere) through a free Cloudflare tunnel.
//
// 1. Builds the site.
// 2. Starts the app on this PC only (127.0.0.1:PORT) with the password login turned on.
// 3. Starts a Cloudflare quick tunnel to it and prints the public https link.
// The link changes every time and works only while this runs. Ctrl+C stops everything.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const PORT = 8787;
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const win = process.platform === "win32";
const python = join(root, "backend", ".venv", win ? "Scripts/python.exe" : "bin/python");
const vite = join(root, "frontend", "node_modules", "vite", "bin", "vite.js");

for (const [what, path] of [["Backend venv", python], ["Frontend packages", vite]]) {
  if (!existsSync(path)) {
    console.error(`${what} not found. Run \`npm run setup\` first.`);
    process.exit(1);
  }
}

// The app refuses to start shared without a password; check first for a clearer message.
const check = spawnSync(
  python,
  ["-c", "import sys; from app.auth import Auth; from app.db import Database; from app.config import DB_PATH; sys.exit(0 if Auth(Database(DB_PATH)).has_password else 3)"],
  { cwd: join(root, "backend"), encoding: "utf8" },
);
if (check.status === 3) {
  console.error("No app password yet. Run `npm run set-password` first.");
  process.exit(1);
}
if (check.status !== 0) {
  console.error(check.stderr || "Could not check the app password.");
  process.exit(1);
}

function findCloudflared() {
  const found = spawnSync(win ? "where" : "which", ["cloudflared"], { encoding: "utf8" });
  if (found.status === 0) return found.stdout.split(/\r?\n/)[0].trim();
  const local = process.env.LOCALAPPDATA ?? "";
  return [
    join(local, "Microsoft", "WinGet", "Links", "cloudflared.exe"),
    "C:\\Program Files (x86)\\cloudflared\\cloudflared.exe",
    "C:\\Program Files\\cloudflared\\cloudflared.exe",
  ].find((p) => existsSync(p));
}

const COLORS = { app: "\x1b[34m", tunnel: "\x1b[35m" };
const procs = [];
let stopping = false;

function say(name, line) {
  process.stdout.write(`${COLORS[name]}[${name}]\x1b[0m ${line}\n`);
}

function kill(child) {
  if (!child || child.exitCode !== null) return;
  if (win) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else child.kill("SIGTERM");
}

function stop(code = 0) {
  stopping = true;
  procs.forEach(kill);
  process.exit(code);
}

function start(name, cmd, args, opts = {}, onLine = () => {}) {
  const child = spawn(cmd, args, { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true, ...opts });
  for (const stream of [child.stdout, child.stderr]) {
    let buf = "";
    stream.on("data", (chunk) => {
      buf += chunk.toString();
      const lines = buf.split(/\r?\n/);
      buf = lines.pop();
      for (const line of lines) {
        say(name, line);
        onLine(line);
      }
    });
  }
  child.on("exit", (code) => {
    if (stopping) return;
    say(name, `exited with code ${code}`);
    stop(code ?? 1);
  });
  procs.push(child);
}

process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));

console.log("Building the site…");
if (spawnSync(process.execPath, [vite, "build"], { cwd: join(root, "frontend"), stdio: "inherit" }).status !== 0) {
  console.error("The site did not build.");
  process.exit(1);
}

// Only this PC can reach the app directly; the tunnel is the one way in from outside.
start("app", python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(PORT), "--app-dir", "backend"], {
  env: { ...process.env, COACH_REQUIRE_LOGIN: "1" },
});

const cloudflared = findCloudflared();
if (!cloudflared) {
  console.log(`
The app is running on this PC at http://127.0.0.1:${PORT} (login on).
To get a public link, install Cloudflare's tunnel tool once, then run \`npm run share\` again:
    winget install --id Cloudflare.cloudflared
`);
} else {
  let shown = false;
  // HTTP/2 over TCP 443, not the default QUIC over UDP 7844: many school and work networks
  // block that UDP port, and cloudflared then keeps retrying QUIC instead of falling back.
  const args = ["tunnel", "--no-autoupdate", "--protocol", "http2", "--url", `http://127.0.0.1:${PORT}`];
  start("tunnel", cloudflared, args, {}, (line) => {
    const url = line.match(/https:\/\/[-a-z0-9]+\.trycloudflare\.com/)?.[0];
    if (url && !shown) {
      shown = true;
      console.log(`\n  Open this on your phone:  ${url}\n  Log in with your app password. Keep this window open; Ctrl+C stops sharing.\n`);
    }
  });
}
