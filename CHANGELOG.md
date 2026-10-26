# Changelog

All notable changes. Newest first.

## [Unreleased]

### Added
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
