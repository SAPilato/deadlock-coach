// One-time setup: Python venv + backend deps, then frontend deps.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const venv = join(root, "backend", ".venv");
const win = process.platform === "win32";
const python = win ? join(venv, "Scripts", "python.exe") : join(venv, "bin", "python");

function run(cmd, args, opts = {}) {
  console.log(`> ${cmd} ${args.join(" ")}`);
  const r = spawnSync(cmd, args, { stdio: "inherit", cwd: root, shell: win, ...opts });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

if (!existsSync(python)) {
  run(win ? "python" : "python3", ["-m", "venv", venv]);
}
run(python, ["-m", "pip", "install", "--upgrade", "pip"], { shell: false });
run(python, ["-m", "pip", "install", "-e", "backend[dev]"], { shell: false });
run("npm", ["--prefix", "frontend", "install"]);
console.log("\nSetup done. Start the app with: npm run dev");
