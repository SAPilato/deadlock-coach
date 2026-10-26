// Runs the backend venv's Python with the given args, from the repo root.
// Usage: node scripts/py.mjs -m pytest ...   (--app-dir <dir> sets cwd for module runs)
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const venv = join(root, "backend", ".venv");
const python =
  process.platform === "win32" ? join(venv, "Scripts", "python.exe") : join(venv, "bin", "python");

if (!existsSync(python)) {
  console.error("Backend venv not found. Run `npm run setup` first.");
  process.exit(1);
}

let args = process.argv.slice(2);
let cwd = root;
// `--app-dir backend` for non-uvicorn modules means: run from that folder.
const i = args.indexOf("--app-dir");
if (i !== -1 && !args.includes("uvicorn")) {
  cwd = join(root, args[i + 1]);
  args = [...args.slice(0, i), ...args.slice(i + 2)];
}

const result = spawnSync(python, args, { cwd, stdio: "inherit" });
process.exit(result.status ?? 1);
