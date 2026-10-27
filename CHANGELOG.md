# Changelog

All notable changes. Newest first.

## [Unreleased]

### Added (cloud hosting)
- `Dockerfile`: builds the site and runs the app with login on, data on a `/data` volume.
- `COACH_PASSWORD_HASH`: set the login on a cloud host; make it with `npm run password-hash`.
  A new hash logs every device out.
- GitHub Actions: offline tests, frontend build and a container build on every push.
- The bundled sample data is now in the repo (only the top-level `data/` is ignored), so
  fresh clones and cloud builds have it.

### Added (open it on your phone)
- `npm run share`: builds the site, runs the app on this PC only with a login, and opens a
  free Cloudflare quick tunnel, printing the public https link.
- `npm run set-password`: set the app password on this PC (scrypt hash; never sent).
- Login screen before anything loads when shared; log out in Settings. Signed 30-day
  cookie (HttpOnly, SameSite=Lax, Secure over https); 10 wrong tries lock logins for 10
  min; API docs are off when shared.

### Changed (movement rechecked on real route times)
- Route planner times now come from real trips: optimal = straight-line progress of the
  fastest 15% of out-of-combat trips covering 5,000+ units in 30 s; normal = the median.
  The old model was ~15% too fast even for the best trips.
- New "Optimal (high rank)" option: the newest ranked Ascendant+ matches this patch
  (327 vs 305 u/s at your rank). Zipline rides cost ~5 s each to get on (calibrated).
- Your movement profile uses only matches you played.

### Added (exact zipline control, waves in review)
- Replays now yield exact zipline control from the replay's zipline nodes (Boon
  `zipline_changes`): per lane, each team's owned share second by second.
- Match review labels zipline control "Exact, from the replay" or estimated (~8% off).
- Estimates start from replay-measured opening shares per lane and team, and never drop
  below each team's uncapturable home stretch; the planner sliders respect it too.
- "Show trooper waves" on the review minimap when the match's replay is parsed.
- Tests use an empty replay folder, so replays parsed on your machine do not leak in.

### Added (team zipline ownership)
- Route planner: pick Hidden King or Archmother and each lane's zipline reach (starts
  at the measured start reach, ~43%). Only your team's part can be ridden; the rest is
  dashed, a team dot marks where yours ends, and each ride says "toward the enemy" or
  "toward your base".
- Match review: zipline control per lane at the scrubbed second (your share vs the
  enemy's), painted on the minimap lanes from each base.
- Evidence (60 matches): nobody rides past the enemy's front objective; parts never
  overlap (sum of reaches median 0.84); same speed both ways; reach grows with pushes.
- Match list rows include your team.

### Added (routes, live review, build helper)
- Route planner chains ziplines: a graph of every zipline (ridden either way) with
  walk-and-latch switches between them. Shows each step, numbers each ride, and colours
  "2+ ziplines faster" on the map. In 40 matches players switched ziplines 3,260 times,
  ~2 s apart; 96% of zipline time is on the 3 lane ziplines in the map data.
- Game review: hero portraits on the minimap, a zipline badge on anyone riding, a
  "Live at" list (zipline lane or respawn timer per hero), and your rides as bars.
  Rides come from the match's per-second movement types, tagged with the nearest lane.
- Build Lab helper: Start (most-bought items per phase at your rank, "add the usual
  start"), Spikes (gains per purchase at the level you will be, your souls pace vs rank
  timing, big spending tiers) and Counter-buy (per-enemy item win rates vs each item's
  other games, z >= 2, from deadlock-api item-stats with `enemy_hero_ids`).

### Changed (Brass Deco with tab tones)
- Brass Deco is the default look. Each tab has its own tone: Home brass, Matches
  amethyst, Trends verdigris, Build Lab sapphire, Map neon rose, Learn ivory,
  Settings silver. The nav shows every tab's tone; links wear their target tab's tone.
- Tones drive accents, card hairlines and the page glow; borders and ink stay brass.
- The theme is only saved when you pick one (v1 saved Slate on every first visit).

### Added (look and feel)
- Four themes in Settings → Look: Slate, Brass Deco, Case File (light) and Neon HUD.
  Colours, heading font and corners change per theme; body text stays Atkinson
  Hyperlegible. Text colours checked for 4.5:1 contrast in every theme. `?theme=` works on any page.
- Line icons (lucide-react) replace every emoji. A test fails if one comes back.
- Pages that hit an error now show a message instead of a blank screen.

### Changed
- Late game now starts at the first Base Guardian, not the first Walker. In 40 real
  matches the first Walker fell ~40% of the way in, which labelled 60% of every match
  "late". Affects the death map phases and the heatmap.

### Fixed
- Learn: opening a lesson crashed the page. The scroll-to-top effect returned
  `scrollTo`'s Promise (newer browsers), which React then called as a cleanup.

### Added (Phase 4: Learn)
- Learn page (`/learn`) with 11 short lessons in Lane, Map, Fights and Items.
  "For you" suggests the lessons for your flagged habits, focus habit first.
- Lesson page (`/learn/:id`): up to 3 steps, up to 3 game numbers with their
  source, your record for the matching habit, read-aloud, and a "Try it" button
  that opens the matching map layer or Build Lab view.
- Lesson numbers come from game data at request time: wave timer and squad size,
  trooper souls and orb split, Guardian HP and bounty, objective bounties,
  Rejuvenator duration, camp/crate/buff counts, item tier prices, weapon spending
  bonus. Zipline vs running is measured (`est.`); urn sites come from a replay.
- Findings, the Home focus card and Trends link to their lesson. Learn is in the nav.
- Deep links: `/map?mode=explore&layers=lanes,camps` opens those layers;
  `/build#shop` scrolls to the shop.
- Tests: lesson readability (title, sentence length, ≤3 steps and facts, no
  hardcoded numbers), every rule has a lesson, facts fill offline, map links exist,
  and the suggestion order.

### Fixed (map is now the post-City Never Sleeps map)
- Urn: only the 2 live urn sites show. The asset data's 4 older spawn points are
  dropped (checked in post-update replays: urns only spawn and are delivered at 2 sites).
- Objectives stand where the NPCs really are (asset positions were minimap icon
  spots ~1,500 units off). Added Base Guardians, Shrines and Mid Boss.
- Positions come from the newest parsed replay (`truth.json`); a post-update sample
  is bundled. The map says which replay it was checked against.
- Hidden King is amber/orange and Archmother is blue, as in the game data.
  Your-side colours (heatmap, "What would you do?") stay ally blue / enemy orange.

### Added
- City Never Sleeps features: Bell Tower and Sunken Plaza markers, Haunt camps
  with their district, district labels (Theater, Chinatown, Haunted Lot, Plaza),
  Buff containers with their permanent buffs from the loot table, Tough crates,
  Steam vents and Veils as their own layers.
- Routes mode: optimal movement vs zipline from A to B, and a "faster from where?"
  map for any destination. Speeds are measured from real matches (zipline ~882,
  optimal movement ~443, normal ~326 game units/s) with a measured detour factor.
- Build Lab: ability damage per ability, without items vs with the build, scaled by
  spirit power from game data, with ability upgrade tiers, spirit damage
  multipliers, cooldown reduction and a dummy with spirit resist and your shred.

### Added (Phase 3: Macro Map page)
- Macro Map page (`/map`) with four modes: Explore (layers, hover tips, rotation
  planner with walk/sprint times), Waves (replay playback, meeting point per lane
  each minute), Your heatmap (per phase), What would you do? (pick, then replay
  the next 40 s with what you actually did and the matching finding).
- Markers use shape for identity and team colour for side, with a legend.

### Added (Phase 3: Macro Map backend)
- Map layers from `/v1/assets/map`: lanes/ziplines, Guardians and Walkers (HP and
  soul bounty from game data), 51 jungle camps (NPC names and HP), urn spawns and
  drop-offs, shops, golden statues, crates, buffs, teleporters/pads/ropes/vents.
- Trooper waves from replays (Boon `troopers`): waves per lane every 3 s and where
  the two sides met each minute. Wave timings from game convars (first wave 16 s,
  then every 30/25/20 s). The sample replay's results are bundled.
- Replay parsing now also saves wave data (`waves.json.gz`, ~30 KB).
- Heatmap of your positions per game phase over your last N matches, with the
  objectives that fell.
- "What would you do?" moments: 20 s before flagged mistakes, deaths and lost
  objectives, with the next 40 s of positions and what you actually did.
- GZip responses.

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
