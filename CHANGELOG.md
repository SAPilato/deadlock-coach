# Changelog

All notable changes. Newest first.

## [Unreleased]

### Added
- Replays: auto-download from Valve (when the API has the replay link) or upload a
  `.dem`. Parsed with Boon in the background; urn pickups/drops/returns become
  "urn episodes" for the urn rule. Valve serves zstd files named `.bz2`, so the
  format is detected from magic bytes. The demo is deleted after parsing.
- Frontend (React + Vite + Tailwind): Home with the focus habit, Matches list,
  Match report (findings, souls timeline with event strip and live minimap
  scrubber, vs-rank tiles, death map by phase, item timing diverging bars, lane
  phase, replay box), Trends with per-game dots, Settings (Steam ID or name
  search, rank range, game-data refresh). 18px Atkinson Hyperlegible, read-aloud
  buttons, `est.` tags, colour palette checked for colour-blind safety.
- `npm run dev` runner that restarts the API on .py changes without killing Vite
  (uvicorn's own reloader breaks Vite on Windows).
- HTTP API (`/api`): meta + patch status, settings (Steam ID in any format, rank
  bracket), Steam name search, match list, full match report, minimap paths for
  the timeline scrubber, trends across recent matches with one focus habit.
- Match phases (early/mid/late) come from objectives: Guardian in your lane falls,
  then the first Walker falls.
- Per-match analysis cached in SQLite, invalidated by engine version or bracket change.
- Findings engine (`backend/app/findings`) with 8 rules: low souls/min, dying alone,
  same death spot, idle time, late core item, missed objective fights, urn contest
  (replay only), lane overstay. Each finding has a headline, one "next game" fix,
  up to 3 detail lines, evidence vs a benchmark and map/timeline moments.
- Habits without API rank stats are compared to the lobby average in the same match.
- Readability test: fails if any rule text has a sentence over 15 words.
- Match analysis (`backend/app/analysis`): per-second path decoding, minimap transform
  fitted from map entities, lanes matched to ziplines by color, objective positions,
  `MatchContext` with deaths, upgrades, snapshots and benchmarks for one player.
- Offline seed: 3 real matches of a public Ritualist player plus game data and
  benchmarks (`npm run seed` rebuilds it).
- Game-data layer (`backend/app/gamedata`): the only code that calls deadlock-api.com.
  SQLite cache stamped with `patch_version`, 3 req/s throttle for analytics,
  exponential backoff on 429/5xx with Retry-After, stale-cache fallback when offline.
- Enum values (objectives, gold sources, combat/move types) parsed from Valve's protobufs.
- Steam ID parser: SteamID64, SteamID3, legacy STEAM_0, profile URLs.
- Project scaffold: FastAPI backend, React + Vite frontend, one-command dev (`npm run dev`).
