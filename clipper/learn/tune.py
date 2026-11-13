"""Retrain the scoring weights from how our own posted clips did.

Input: data/performance.jsonl, one line per posted clip:
  {"clip_id": "...", "signals": {"loudness": .., "chat": ..}, "views": 1234,
   "avg_view_pct": 0.71, "shares": 12}

Clips whose signals predicted good results raise those signals' weights.
Small, safe steps: weights move at most 30% per run and stay in [0.1, 3].
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..score import DEFAULT_WEIGHTS


def outcome(row: dict) -> float:
    """One number for 'how good was this clip': reach x retention x shares.

    Optional fields: ``stayed_pct`` (YouTube "Stayed to watch", 0-1: the hook) and
    ``sends`` (Instagram shares by DM, its strongest signal for non-followers).
    """
    views = max(1, row.get("views", 0))
    hook = 0.5 * (row.get("stayed_pct", 0.6) - 0.6)
    shares = row.get("shares", 0) + row.get("sends", 0)
    return np.log10(views) * (0.5 + row.get("avg_view_pct", 0.5) + hook) + 0.3 * np.log1p(shares)


def fit(rows: list[dict], current: dict[str, float], max_step: float = 0.3) -> dict[str, float]:
    names = sorted(current)
    if len(rows) < 8:
        return dict(current)                 # not enough data yet
    X = np.array([[r["signals"].get(n, 0.0) for n in names] for r in rows], dtype=float)
    y = np.array([outcome(r) for r in rows])
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    y = (y - y.mean()) / (y.std() + 1e-9)
    corr = X.T @ y / len(y)                  # how much each signal tracks success
    new = {}
    for n, c in zip(names, corr):
        factor = float(np.clip(1 + c, 1 - max_step, 1 + max_step))
        new[n] = round(float(np.clip(current[n] * factor, 0.1, 3.0)), 3)
    return new


def main(perf: str = "data/performance.jsonl", weights: str = "data/weights.json") -> dict:
    rows = [json.loads(l) for l in Path(perf).read_text().splitlines() if l.strip()] if Path(perf).exists() else []
    cur = dict(DEFAULT_WEIGHTS)
    if Path(weights).exists():
        cur.update(json.loads(Path(weights).read_text()))
    new = fit(rows, cur)
    Path(weights).parent.mkdir(parents=True, exist_ok=True)
    Path(weights).write_text(json.dumps(new, indent=2))
    return new
