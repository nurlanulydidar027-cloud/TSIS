"""
TSIS 3 — Racer | persistence layer for settings & leaderboard.

Both files are plain JSON.  Missing files are auto-created with sane
defaults so a first run "just works".
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

SETTINGS_FILE   = "settings.json"
LEADERBOARD_FILE = "leaderboard.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "sound":      True,
    "car_color":  "red",          # red / blue / green / yellow / black
    "difficulty": "normal",       # easy / normal / hard
}


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------
def load_settings() -> dict[str, Any]:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)
    # backfill missing keys
    return {**DEFAULT_SETTINGS, **data}


def save_settings(s: dict[str, Any]) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# ---------------------------------------------------------------------------
# leaderboard
# ---------------------------------------------------------------------------
def load_leaderboard() -> list[dict[str, Any]]:
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def add_score(name: str, score: int, distance: int, coins: int) -> list[dict]:
    board = load_leaderboard()
    board.append({
        "name":     (name or "anon")[:14],
        "score":    int(score),
        "distance": int(distance),
        "coins":    int(coins),
        "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    board.sort(key=lambda r: r["score"], reverse=True)
    board = board[:10]
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)
    return board
