# Changelog

All notable changes. Newest first.

## [Unreleased]

### Added (Phase 2: Build Lab page)
- Build Lab page (`/build`): hero picker, level slider (boons and souls), 12 item
  slots coloured by category, shop with tier/search/sort, cost, win rate, pick rate
  and typical buy time at your rank.
- Live stat table: "No items" vs "This build", or "Now" vs "+ item" while hovering
  a shop item. Changes in green/red with arrows; estimates tagged `est.`
- Conditional effects as switches with the condition from the item's own tooltip
  ("while you are above 65% health"); ability-only bonuses listed separately.
- DPS dummy: health, bullet resist and headshot sliders; time to kill.
- Save, open, compare side by side, export/import JSON. Match report links to
  "Open this build in Build Lab" (items held at the end of that match).

### Added (Phase 2: Build Lab backend)
- Stat engine (`backend/app/buildlab`): hero base stats + per-boon growth by level,
  item effects typed by the stat they change, conditional and active effects behind
  toggles, enemy debuffs (shred, slows) applied to the target dummy.
- Combining rules follow Boon's documented equations (resists, lifesteal, fire
  rate, clip, reload, spirit power, move speed, melee). Others are tagged `est.`
- Base gun DPS matches the API's own weapon numbers for every hero (tested).
- Item slot limit measured from real matches (12), not assumed.
- Shop with soul cost, win rate and pick rate per item for your hero and rank.
- Saved builds, JSON export/import, and "build used in a match" import.

### Changed
- Minimaps draw the three lanes (York, Broadway, Greenwich) from map data so
  positions are readable; bigger death markers; whole-number rank benchmarks;
  kill and death markers use different shapes, with a legend.

### Added
- README with setup, data sources, `est.` policy and known data limits.
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
