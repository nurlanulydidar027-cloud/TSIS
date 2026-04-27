# TSIS 3 — Racer (Extended)

Top-down arcade racer in Pygame.  Implements every TSIS-3 requirement:

| Section | Implementation |
|---|---|
| 3.1 Track | 4-lane road with animated dashes, lane hazards, dynamic events ("NITRO STRIP!", oil messages) |
| 3.2 Traffic | Cars, barriers, oil, potholes, speed bumps; safe-spawn logic; difficulty ramp every 1500 px |
| 3.3 Power-ups | **Nitro** (4 s speed), **Shield** (one free hit), **Repair** (instant +5 coins).  Only one active at a time, displayed in HUD with countdown |
| 3.4 Score / distance / leaderboard | Score = coins × 10 + distance / 10 + bonuses.  Distance bar with finish line at 12 000 px.  Top-10 saved in `leaderboard.json` with name, score, distance, coins, date |
| 3.5 Screens | Main Menu, Settings (sound / car colour / difficulty), Leaderboard, Game Over (Retry / Menu).  Settings persist in `settings.json` |

## Files

```
TSIS3/
├── main.py          entry point + screens
├── racer.py         gameplay state machine
├── ui.py            buttons, palette, username prompt
├── persistence.py   JSON load/save for settings & scores
├── settings.json    auto-created if missing
└── leaderboard.json auto-created if missing
```

## Run

```bash
pip install pygame
python main.py
```

## Controls

- **← / →** or **A / D** — change lane
- **Esc** — back to main menu
- Mouse on the menu buttons
