# Changelog

All notable changes. Newest first.

## [Unreleased]

### Added
- Game-data layer (`backend/app/gamedata`): the only code that calls deadlock-api.com.
  SQLite cache stamped with `patch_version`, 3 req/s throttle for analytics,
  exponential backoff on 429/5xx with Retry-After, stale-cache fallback when offline.
- Enum values (objectives, gold sources, combat/move types) parsed from Valve's protobufs.
- Steam ID parser: SteamID64, SteamID3, legacy STEAM_0, profile URLs.
- Project scaffold: FastAPI backend, React + Vite frontend, one-command dev (`npm run dev`).
