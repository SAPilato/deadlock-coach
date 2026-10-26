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

Game phases come from objectives, not a clock:
- **Laning** ends when the Guardian in your lane falls.
- **Late game** starts when the first Base Guardian falls (either team).
- In 40 recent matches the first Walker fell ~40% of the way in, too early to call
  "late". The first Base Guardian fell ~65% of the way in (median 24:47).

## Look

The app is built around **Brass Deco**: Deadlock's 1920s occult city, brass on black.
Each tab has its own tone inside the same brass frame:

| Tab | Tone | Why |
|---|---|---|
| Home | Brass | the base metal |
| Matches | Amethyst | case review |
| Trends | Verdigris | patina forms over time |
| Build Lab | Sapphire | lab glass |
| Map | Neon rose | city signs at night |
| Learn | Ivory | old pages |
| Settings | Silver | neutral |

Links that open another tab wear that tab's tone. Each tone reads 7:1 or better on
the Deco surfaces and stays clear of the data colours on its own page.
Settings → Look still offers Slate, Case File (light) and Neon HUD.
Add `?theme=slate` (or `casefile`, `hud`, `deco`) to any page to try one.
Body text is Atkinson Hyperlegible in every theme. The UI uses line icons
(lucide-react), never emojis; a test fails if an emoji is added.

## Build Lab (Phase 2)

- Pick a hero and level. Add up to 12 items (the most players held at once in
  recent matches).
- See every stat change against "no items", or preview an item by hovering it.
- Switch conditional effects on or off. Test gun damage on a dummy.
- Save, compare, export and import builds. Open the build from any reviewed match.

Stats follow [Boon's documented rules](https://boon.readthedocs.io/en/latest/hero-stats.html)
where they exist. Base gun DPS matches the API's own numbers for every hero.

Build Lab limits:
- Game data gives vitality and spirit spending bonuses, but not the stat they
  boost. They are shown on their own rows and not added elsewhere.
- DPS counts the gun only, at close range. Reload timing is anchored to the
  API's numbers and tagged `est.`
- Ability damage and item procs are not simulated.

## Macro Map (Phase 3)

- **Explore:** the current (post-City Never Sleeps) map: all objectives incl. Mid
  Boss, Shrines and Base Guardians, the 2 urn sites, Bell Tower, Sunken Plaza, Haunt
  camps, districts, buff containers, crates, steam vents and more. Hover for facts.
- **Routes:** is optimal movement or the zipline faster? Pick A and B, or pick a
  destination and see which option wins from every spot. Speeds are measured from
  real matches.
- **Waves:** real trooper waves from a replay, with play/pause, and where each
  lane's waves met every minute. A sample replay is bundled.
- **Your heatmap:** where you spent time in laning, mid and late game over your
  last 10 matches, with the objectives that fell.
- **What would you do?:** real moments from your games. Pick an action, then see
  what you did and what happened next.

Macro Map notes:
- The asset map data is partly stale (old urn spawns, icon-offset objectives). The
  newest parsed replay corrects it; load a replay of a recent match to refresh it.
- Route times: straight line × a detour factor measured from real paths. Zipline
  boost, blocked lanes and walls are not modelled: `est.`
- Wave data needs a replay. Your own appear after you load a replay on a match.

Build Lab ability damage: damage = base + scaling × spirit power, from each
ability's game data, plus the upgrade tiers you pick. Values that scale with
weapon or melee damage are listed but not computed.

## Learn (Phase 4)

- **11 short lessons** in four topics: Lane (wave management, slow vs fast push,
  freezing), Map (when to rotate, camp and crate rotations, always have a target,
  urn), Fights (objectives, fighting with your team, death spots) and Items.
- **For you:** the lessons that match your flagged habits, focus habit first, with
  how many of your recent games had the problem.
- **Each lesson:** up to 3 steps, up to 3 numbers from the game, and a button that
  opens the map layer or Build Lab view that shows the idea. Read-aloud included.
- Every finding, the Home focus card and Trends link to their lesson.

Lesson numbers (wave timer, soul values, Guardian HP, item prices, camp counts…)
are read from game data at request time, so they follow patches. Each one says
where it came from: game data, measured from matches (`est.`), or a replay.

## Where the data comes from

All game data is fetched, never hardcoded, so a patch only needs a cache refresh.

| Data | Source |
|---|---|
| Match history, match details (incl. per-second positions), rank | [deadlock-api.com](https://api.deadlock-api.com/docs) |
| Benchmarks for your hero and rank range | deadlock-api.com analytics endpoints |
| Heroes, items, ranks, map, lanes, NPC names | deadlock-api.com `/v1/assets/*` |
| Objective, gold-source and combat enums | Valve protobufs via [SteamDatabase/Protobufs](https://github.com/SteamDatabase/Protobufs) |
| Urn events from replays | [Boon](https://boon.readthedocs.io) |
| Lesson numbers (wave timer, bounties, prices) | game settings (`/v1/assets/convars`), generic data, NPC units |

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
backend/app/learn      lesson cards (lessons.py) and their game-data facts (facts.py)
frontend/src           React pages and components
```

Add a rule: create `backend/app/findings/rules/<name>.py`, subclass `Rule`, put all
text in `TEXT`, register it in `rules/__init__.py`, and add a test. The readability
test fails if any sentence is over 15 words.

Add a lesson: add an entry to `backend/app/learn/lessons.py` (no numbers in the
text; put them in `facts.py` so they come from game data). `tests/test_learn.py`
checks length, that every rule's `lesson_id` exists, and that map links are real.
