"""Habits across recent matches, and the one focus habit for next game."""
from __future__ import annotations

import json
import logging
import time

from app.analysis.loader import load_context
from app.config import ENGINE_VERSION
from app.findings.base import REGISTRY, SEVERITY_RANK
from app.findings.engine import Report, run_rules
from app.gamedata.client import ApiError
from app.state import AppState

log = logging.getLogger(__name__)

RECENT_N = 10
MIN_PER_WINDOW = 4
TREND_DELTA = 0.2  # est. change in "games with this habit" share that counts as a real change


def analyze(st: AppState, match_id: int, account_id: int, bracket: tuple[int, int], replay=None, force=False) -> Report:
    """Run the rules for one match, using the stored result when it is still valid."""
    row = st.db.one(
        "SELECT payload, engine_version FROM analyses WHERE match_id = ? AND account_id = ?", (match_id, account_id)
    )
    if row and not force and row["engine_version"] == ENGINE_VERSION:
        payload = json.loads(row["payload"])
        if payload.get("bracket") == list(bracket) and (replay is None or payload.get("with_replay")):
            return Report.model_validate(payload["report"])
    ctx = load_context(st.gd, match_id, account_id, bracket, replay=replay)
    report = run_rules(ctx)
    save_analysis(st, ctx.match_id, account_id, bracket, report, with_replay=replay is not None)
    return report


def save_analysis(st: AppState, match_id: int, account_id: int, bracket, report: Report, with_replay: bool) -> None:
    payload = {"bracket": list(bracket), "with_replay": with_replay, "report": report.model_dump()}
    st.db.execute(
        "INSERT OR REPLACE INTO analyses (match_id, account_id, engine_version, patch_version, payload, computed_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (match_id, account_id, ENGINE_VERSION, st.gd.live_build(), json.dumps(payload), time.time()),
    )


def compute_trends(st: AppState, account_id: int, bracket: tuple[int, int], n: int = 20, replays=None) -> dict:
    history = [m for m in st.gd.match_history(account_id) if m.get("game_mode") == 1][:n]
    rows = []
    for m in history:
        try:
            replay = replays(m["match_id"]) if replays else None
            report = analyze(st, m["match_id"], account_id, bracket, replay=replay)
        except (ApiError, ValueError) as e:
            log.info("Trends: skip match %s (%s)", m["match_id"], e)
            continue
        rows.append({
            "match_id": m["match_id"],
            "start_time": m.get("start_time"),
            "hero_id": m.get("hero_id"),
            "won": m.get("match_result") == m.get("player_team"),
            "found": {f.rule_id: f.severity for f in report.findings},
            "ran": {h.rule_id for h in report.passed} | {f.rule_id for f in report.findings},
        })

    half = min(RECENT_N, max(1, len(rows) // 2)) if len(rows) < 2 * RECENT_N else RECENT_N
    recent, previous = rows[:half], rows[half:]
    habits = []
    for rid, rule in REGISTRY.items():
        r_ran = [r for r in recent if rid in r["ran"]]
        p_ran = [r for r in previous if rid in r["ran"]]
        r_hits = sum(1 for r in r_ran if rid in r["found"])
        p_hits = sum(1 for r in p_ran if rid in r["found"])
        r_rate = r_hits / len(r_ran) if r_ran else None
        p_rate = p_hits / len(p_ran) if p_ran else None
        if len(r_ran) < MIN_PER_WINDOW or len(p_ran) < MIN_PER_WINDOW:
            status = "not_enough"
        elif r_rate - p_rate <= -TREND_DELTA:
            status = "improving"
        elif r_rate - p_rate >= TREND_DELTA:
            status = "worse"
        else:
            status = "same"
        habits.append({
            "rule_id": rid,
            "habit": rule.habit,
            "lesson_id": rule.lesson_id,
            "do_next": rule.TEXT["do_next"],
            "status": status,
            "recent_hits": r_hits,
            "recent_games": len(r_ran),
            "previous_hits": p_hits,
            "previous_games": len(p_ran),
            "recent_rate": r_rate,
            "previous_rate": p_rate,
            "per_match": [{"match_id": r["match_id"], "severity": r["found"].get(rid), "ran": rid in r["ran"]} for r in rows],
        })
    return {
        "matches": [{k: r[k] for k in ("match_id", "start_time", "hero_id", "won")} for r in rows],
        "recent_n": len(recent),
        "previous_n": len(previous),
        "habits": habits,
        "focus": pick_focus(habits, recent),
    }


def pick_focus(habits: list[dict], recent: list[dict]) -> dict | None:
    """The habit with the most weighted findings in recent games; ties go to the one getting worse."""
    order = {"worse": 3, "same": 2, "not_enough": 1, "improving": 0}
    best, best_key = None, None
    for h in habits:
        weight = sum(SEVERITY_RANK[r["found"][h["rule_id"]]] for r in recent if h["rule_id"] in r["found"])
        if weight == 0:
            continue
        key = (weight, order[h["status"]])
        if best_key is None or key > best_key:
            best, best_key = h, key
    if best is None:
        return None
    return {
        "rule_id": best["rule_id"],
        "habit": best["habit"],
        "do_next": best["do_next"],
        "lesson_id": best["lesson_id"],
        "status": best["status"],
        "hits": best["recent_hits"],
        "games": best["recent_games"],
    }
