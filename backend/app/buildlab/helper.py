"""Build helper: what to buy first, where a build spikes, and what counters the enemy.

Everything is read from live data, never from memory:
- Phase picks: deadlock-api item-flow-stats for your hero and rank. The API's phases
  are fixed: 0-9, 9-20, 20-30 and 30+ minutes. "Standard early items" = phase 1.
- Spikes: the Build Lab engine run on each step of your build order. A step is a
  spike when it lifts gun damage, durability or ability damage a lot, or crosses a
  category spending threshold that adds a big bonus (the hero's own `cost_bonuses`).
  "When" comes from your own souls over time in recent games.
- Counters: item-stats for your hero against each enemy hero, compared with the same
  item's win rate in your other games (so each item is measured against itself).
  Only clear differences are kept (z >= Z_MIN). Win rates are not causes: est.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.buildlab.engine import SLOT_TYPES, Target, compute

PHASES = ["0-9 min", "9-20 min", "20-30 min", "30+ min"]
PER_PHASE = 6
MIN_PICK = 0.05  # est. an item must appear in 5%+ of games that reach the phase
SPIKE_GAIN = 0.15  # est. +15% gun DPS, durability or ability damage in one purchase
SPEND_JUMP = 15  # est. a tier adding 15+ points over the tier below it is a spike (e.g. weapon at 4,800)
MIN_GAMES = 60  # est. fewer games against a hero than this is too noisy to use
Z_MIN = 2.0  # about 95% confidence that the difference is real
MAX_COUNTERS = 6


def _item_card(it: dict) -> dict:
    return {
        "id": it["id"],
        "name": it["name"],
        "tier": it.get("item_tier"),
        "cost": it.get("cost"),
        "slot": it.get("item_slot_type"),
        "image": it.get("shop_image") or it.get("image"),
    }


# ---- phase picks ----------------------------------------------------------------------


def phase_picks(flow: dict, shop: dict[int, dict]) -> dict:
    """Most-bought shop items in each phase, with pick and win rates."""
    reached = flow.get("reached_per_column") or []
    base = flow.get("baseline") or {}
    phases = []
    for col, name in enumerate(PHASES):
        games = reached[col] if col < len(reached) else 0
        rows = []
        for n in flow.get("nodes") or []:
            it = shop.get(n["item_id"])
            if n.get("column") != col or not it or not games or not n.get("matches"):
                continue
            pick = n["matches"] / games
            if pick < MIN_PICK:
                continue
            rows.append({**_item_card(it), "pick_rate": round(pick, 3), "win_rate": round(n["wins"] / n["matches"], 3), "games": n["matches"]})
        rows.sort(key=lambda r: -r["pick_rate"])
        phases.append({"phase": name, "games": games, "items": rows[:PER_PHASE]})
    return {
        "phases": phases,
        "games": base.get("matches"),
        "win_rate": round(base["wins"] / base["matches"], 3) if base.get("matches") else None,
    }


# ---- spikes -----------------------------------------------------------------------------


def _interp(series: list[tuple[int, float]], t: float) -> float:
    for (t0, v0), (t1, v1) in zip(series, series[1:]):
        if t0 <= t <= t1:
            return v1 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return series[-1][1]


def souls_curve(games: list[list[tuple[int, float]]], step: int = 60) -> list[tuple[int, float]]:
    """Average souls over time across games, each a list of (seconds, net worth) snapshots.

    Each minute averages the games still running then; it stops when fewer than 2 are.
    """
    series = [[(0, 0.0)] + sorted(g) for g in games if g]
    out: list[tuple[int, float]] = []
    t = 0
    while True:
        running = [s for s in series if s[-1][0] >= t]
        if len(running) < 2:
            return out
        out.append((t, sum(_interp(s, t) for s in running) / len(running)))
        t += step


def time_for_souls(curve: list[tuple[int, float]], souls: float) -> int | None:
    """When the curve first reaches `souls`; None if it never does."""
    for (t0, v0), (t1, v1) in zip(curve, curve[1:]):
        if v0 <= souls <= v1:
            return round(t1 if v1 == v0 else t0 + (t1 - t0) * (souls - v0) / (v1 - v0))
    return None


def level_for_souls(hero: dict, souls: float) -> int:
    """Highest level whose soul requirement is met (hero `level_info`)."""
    info = hero.get("level_info") or {}
    reached = [int(k) for k, v in info.items() if (v.get("required_gold") or 0) <= souls]
    return max(reached, default=1)


def _metrics(sheet) -> dict:
    rows = {r.key: r.value or 0 for r in sheet.rows}
    hp = rows.get("max_health", 0)
    # Durability: health against bullets and against spirit, averaged.
    ehp = sum(hp / max(0.05, 1 - rows.get(k, 0) / 100) for k in ("bullet_resist", "spirit_resist")) / 2
    ability = sum(line["value"] for ab in sheet.abilities for line in ab["lines"])
    return {"dps": sheet.dps.get("effective") or 0, "ehp": ehp, "ability": ability}


def _gain(new: float, old: float) -> float | None:
    return (new - old) / old if old > 0 else None


def spike_steps(hero: dict, weapon: dict, items: list[dict], abilities: list[dict], target: Target,
                curve: list[tuple[int, float]] | None = None, typical_buy_s: dict[int, int] | None = None) -> list[dict]:
    """Each purchase in build order: what it adds, at the level you will be by then."""
    steps = []
    spent = 0
    spend = {s: 0 for s in SLOT_TYPES}
    tables = hero.get("cost_bonuses") or {}
    for k, it in enumerate(items):
        cost = int(it.get("cost") or 0)
        spent += cost
        level = level_for_souls(hero, spent)
        # Same level on both sides, so the gain is the item's, not the level-up's.
        before = _metrics(compute(hero, weapon, items[:k], level, target=target, abilities=abilities))
        after = _metrics(compute(hero, weapon, items[:k + 1], level, target=target, abilities=abilities))
        gains = {m: _gain(after[m], before[m]) for m in after}
        slot = it.get("item_slot_type")
        crossed = None
        if slot in spend:
            old = spend[slot]
            spend[slot] += cost
            table = sorted(tables.get(slot, []), key=lambda r: r["gold_threshold"])
            # Each tier's own step over the tier below, so one big first purchase that
            # crosses several small tiers is not mistaken for a big one.
            tiers = [(r, r["bonus"] - (table[i - 1]["bonus"] if i else 0.0)) for i, r in enumerate(table)]
            hits = [(r, step) for r, step in tiers if old < r["gold_threshold"] <= spend[slot]]
            if hits:
                top = hits[-1][0]
                crossed = {"slot": slot, "threshold": top["gold_threshold"], "bonus": top["bonus"], "jump": max(step for _, step in hits)}
        big = {m: g for m, g in gains.items() if g is not None and g >= SPIKE_GAIN}
        steps.append({
            **_item_card(it),
            "souls": spent,
            "level": level,
            "at_s": time_for_souls(curve, spent) if curve else None,
            "typical_s": (typical_buy_s or {}).get(it["id"]),
            "gains": {m: (round(g, 3) if g is not None else None) for m, g in gains.items()},
            "values": {m: round(v, 1) for m, v in after.items()},
            "bonus": crossed,
            "spike": bool(big) or bool(crossed and crossed["jump"] >= SPEND_JUMP),
            "spike_on": sorted(big, key=lambda m: -big[m]),
        })
    return steps


# ---- counters ---------------------------------------------------------------------------


@dataclass
class _Rate:
    wins: int
    games: int

    @property
    def p(self) -> float:
        return self.wins / self.games


def _z(a: _Rate, b: _Rate) -> float:
    se = math.sqrt(a.p * (1 - a.p) / a.games + b.p * (1 - b.p) / b.games)
    return (a.p - b.p) / se if se > 0 else 0.0


def counter_items(base_rows: list[dict], vs_rows: dict[int, list[dict]], shop: dict[int, dict],
                  enemy_names: dict[int, str]) -> dict:
    """Items that win clearly more (or less) than usual against these enemy heroes.

    For each enemy, an item's games against that hero are compared with the item's
    other games for your hero and rank. Evidence is combined across enemies (Stouffer z).
    """
    base = {r["item_id"]: r for r in base_rows}
    per_item: dict[int, list[tuple[int, float, float, int]]] = {}
    for enemy, rows in vs_rows.items():
        for r in rows:
            b = base.get(r["item_id"])
            if not b or r["item_id"] not in shop or r["matches"] < MIN_GAMES:
                continue
            rest = _Rate(b["wins"] - r["wins"], b["matches"] - r["matches"])
            if rest.games < MIN_GAMES:
                continue
            vs = _Rate(r["wins"], r["matches"])
            per_item.setdefault(r["item_id"], []).append((enemy, vs.p - rest.p, _z(vs, rest), vs.games))
    picks, skips = [], []
    for iid, parts in per_item.items():
        z = sum(p[2] for p in parts) / math.sqrt(len(enemy_names) or len(parts))
        row = {
            **_item_card(shop[iid]),
            "delta": round(sum(p[1] for p in parts) / len(parts), 3),
            "z": round(z, 2),
            "games": sum(p[3] for p in parts),
            "strong_vs": [enemy_names.get(e, str(e)) for e, d, zz, _ in sorted(parts, key=lambda p: -p[2]) if zz >= Z_MIN],
            "weak_vs": [enemy_names.get(e, str(e)) for e, d, zz, _ in sorted(parts, key=lambda p: p[2]) if zz <= -Z_MIN],
        }
        if z >= Z_MIN:
            picks.append(row)
        elif z <= -Z_MIN:
            skips.append(row)
    picks.sort(key=lambda r: -r["delta"])
    skips.sort(key=lambda r: r["delta"])
    return {"buy": picks[:MAX_COUNTERS], "skip": skips[:3]}
