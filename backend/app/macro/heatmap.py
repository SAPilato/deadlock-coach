"""Where you spend your time, per game phase, against where objectives fell.

Uses the per-second positions in match metadata for your last N matches.
Phases come from objectives (see report.phase_bounds), not a fixed clock.
"""
from __future__ import annotations

import logging

from app.analysis.loader import load_context
from app.gamedata.client import ApiError
from app.report import phase_bounds, phase_of
from app.state import AppState

log = logging.getLogger(__name__)

GRID = 40
SAMPLE_S = 5


def heatmap(st: AppState, account_id: int, bracket: tuple[int, int], n: int = 10) -> dict:
    history = [m for m in st.gd.match_history(account_id) if m.get("game_mode") == 1][:n]
    counts = {p: {} for p in ("early", "mid", "late")}
    totals = {p: 0 for p in counts}
    objectives = []
    used = 0
    for m in history:
        try:
            ctx = load_context(st.gd, m["match_id"], account_id, bracket, with_bench=False)
        except (ApiError, ValueError) as e:
            log.info("Heatmap: skip %s (%s)", m["match_id"], e)
            continue
        p = ctx.player
        if p.track is None:
            continue
        used += 1
        bounds = phase_bounds(ctx)
        for t in range(0, min(len(p.track), ctx.duration_s), SAMPLE_S):
            if not p.alive_at(t):
                continue
            left, top = ctx.geo.to_rel(*p.track.at(t))
            if not (0 <= left < 1 and 0 <= top < 1):
                continue
            cell = (int(left * GRID), int(top * GRID))
            phase = phase_of(t, bounds)
            counts[phase][cell] = counts[phase].get(cell, 0) + 1
            totals[phase] += 1
        for o in ctx.objectives:
            if o.x is None or o.kind == "core":
                continue
            left, top = ctx.geo.to_rel(o.x, o.y)
            objectives.append({
                "left": round(left, 4), "top": round(top, 4), "phase": phase_of(o.t, bounds),
                "taken": o.owner_team != p.team, "name": o.name, "match_id": ctx.match_id, "t": o.t,
            })
    phases = {}
    for phase, cells in counts.items():
        peak = max(cells.values(), default=0)
        phases[phase] = {
            "cells": [[i, j, c] for (i, j), c in cells.items()],
            "max": peak,
            "minutes": round(totals[phase] * SAMPLE_S / 60),
        }
    return {"grid": GRID, "matches": used, "phases": phases, "objectives": objectives}
