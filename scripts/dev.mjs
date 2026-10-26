// `npm run dev`: API (uvicorn) + web (Vite) with prefixed output.
//
// The API restarts when a .py file in backend/app changes. We do the restart
// here instead of `uvicorn --reload`: on Windows that reloader stops the worker
// with a console-wide Ctrl+C, which also kills Vite (or hangs when detached).
import { spawn, spawnSync } from "node:child_process";
import { existsSync, watch } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const win = process.platform === "win32";
const python = join(root, "backend", ".venv", win ? "Scripts/python.exe" : "bin/python");
const vite = join(root, "frontend", "node_modules", "vite", "bin", "vite.js");
const appDir = join(root, "backend", "app");

for (const [what, path] of [["Backend venv", python], ["Frontend packages", vite]]) {
  if (!existsSync(path)) {
    console.error(`${what} not found. Run \`npm run setup\` first.`);
    process.exit(1);
  }
}

const COLORS = { api: "\x1b[34m", web: "\x1b[35m" };
const procs = {};
let stopping = false;

function say(name, line) {
  process.stdout.write(`${COLORS[name]}[${name}]\x1b[0m ${line}\n`);
}

function pipe(name, stream) {
  let buf = "";
  stream.on("data", (chunk) => {
    buf += chunk.toString();
    const lines = buf.split(/\r?\n/);
    buf = lines.pop();
    for (const line of lines) say(name, line);
  });
}

function kill(child) {
  if (!child || child.exitCode !== null) return;
  if (win) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else child.kill("SIGTERM");
}

function start(name, cmd, args, opts = {}) {
  const child = spawn(cmd, args, { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true, ...opts });
  pipe(name, child.stdout);
  pipe(name, child.stderr);
  child.on("exit", (code) => {
    if (stopping || child.restarting) return;
    say(name, `exited with code ${code}`);
    if (name === "web") stop(code ?? 1); // the API stays down until the next file change
  });
  procs[name] = child;
}

const startApi = () =>
  start("api", python, ["-m", "uvicorn", "app.main:app", "--port", "8000", "--app-dir", "backend"]);

function stop(code = 0) {
  stopping = true;
  Object.values(procs).forEach(kill);
  process.exit(code);
}

process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));

let timer = null;
watch(appDir, { recursive: true }, (_event, file) => {
  if (!file || !file.endsWith(".py")) return;
  clearTimeout(timer);
  timer = setTimeout(() => {
    say("api", `change in ${file}, restarting…`);
    if (procs.api) procs.api.restarting = true;
    kill(procs.api);
    startApi();
  }, 300);
});

startApi();
start("web", process.execPath, [vite], { cwd: join(root, "frontend") });
