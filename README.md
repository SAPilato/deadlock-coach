# Deadlock Coach

A personal web app to get better at Valve's Deadlock. It reviews your real
matches and finds specific habits to fix, one at a time.

## Run it

Needs Python 3.11+ and Node 18+.

```bash
npm run setup
```

```bash
npm run dev
```

Open http://localhost:5173. Without a Steam ID the app shows a sample player.
Add yours in **Settings** (SteamID64, profile link, `[U:1:…]`, or search by name).

Other commands: `npm test` (pytest + vitest), `npm run seed` (rebuild the offline sample).

## What it does (Phase 1)

- **Home**: one focus habit for your next game.
- **Matches**: your history with result, K/D/A, souls/min, rank.
- **Match report**: ranked findings, souls timeline with a live minimap scrubber,
  you vs your rank, death map by game phase, item timing, lane phase.
- **Replays (optional)**: auto-download or upload a `.dem` to add the urn check.
- **Trends**: each habit over your last 20 games: improving, same or worse.

Build Lab, Macro Map and Learn come in later phases.

## Where the data comes from

All game data is fetched, never hardcoded, so a patch only needs a cache refresh.

| Data | Source |
|---|---|
| Match history, match details (incl. per-second positions), rank | [deadlock-api.com](https://api.deadlock-api.com/docs) |
| Benchmarks for your hero and rank range | deadlock-api.com analytics endpoints |
| Heroes, items, ranks, map, lanes, NPC names | deadlock-api.com `/v1/assets/*` |
| Objective, gold-source and combat enums | Valve protobufs via [SteamDatabase/Protobufs](https://github.com/SteamDatabase/Protobufs) |
| Urn events from replays | [Boon](https://boon.readthedocs.io) |

Every cached row stores the game build (`patch_version`) it came from. The header
shows the build and warns when a newer one is live.

## Numbers marked `est.`

Some checks need a threshold that no data source defines, such as "how far is
alone". Those numbers carry an `est.` tag. Habits without rank stats are compared
with the other 11 players in the same match instead.

## Known data limits

- Souls are recorded every 3 minutes, so lane checks use 6, 9 and 12 minutes.
- Match data has no fog of war, so "dying alone" uses distance to teammates.
- Urn data exists only in replays. Valve deletes old replays.
- Valve names replay files `.dem.bz2` but often serves zstd; the app detects it.
- If your account is not friends with the API's bot, very recent games may be missing.

## Project layout

```
backend/app/gamedata   the only code that calls external data sources
backend/app/analysis   match data -> MatchContext (paths, map geometry, phases)
backend/app/findings   rules engine; one file per rule in rules/
backend/app/replay     replay download, Boon parsing, background jobs
frontend/src           React pages and components
```

Add a rule: create `backend/app/findings/rules/<name>.py`, subclass `Rule`, put all
text in `TEXT`, register it in `rules/__init__.py`, and add a test. The readability
test fails if any sentence is over 15 words.
