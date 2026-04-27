"""
TSIS 4 — Snake | shared constants & DB credentials.
"""
import os

# ---- screen / grid -----------------------------------------------------
CELL          = 24                 # px per cell
GRID_W        = 25
GRID_H        = 22
HUD_H         = 80                 # top HUD strip height
SCREEN_W      = CELL * GRID_W
SCREEN_H      = CELL * GRID_H + HUD_H

# ---- gameplay ----------------------------------------------------------
BASE_FPS          = 8              # snake speed at level 1
LEVEL_FOOD_STEP   = 5              # foods to clear → next level
SPEED_PER_LEVEL   = 1
OBSTACLE_LEVEL    = 3              # obstacles begin appearing here
OBSTACLES_PER_LV  = 6

POISON_PROBABILITY = 0.18          # chance a new "regular" food spawn is poison

# ---- power-ups ---------------------------------------------------------
POWERUP_LIFETIME_MS = 8000         # disappears if not collected
POWERUP_DURATION_MS = 5000         # speed/slow effect length
POWERUP_SPAWN_CHANCE_PER_FOOD = 0.35

# ---- DB ----------------------------------------------------------------
DB_CONFIG = {
    "host":     os.getenv("PGHOST",     "localhost"),
    "port":     os.getenv("PGPORT",     "5432"),
    "dbname":   os.getenv("PGDATABASE", "snakegame"),
    "user":     os.getenv("PGUSER",     "postgres"),
    "password": os.getenv("PGPASSWORD", "postgres"),
}

# ---- palette -----------------------------------------------------------
COLOR = {
    "bg":         (24, 28, 36),
    "panel":      (38, 42, 54),
    "grid":       (40, 46, 58),
    "text":       (235, 235, 235),
    "dim":        (150, 158, 170),
    "accent":     (94, 214, 159),
    "danger":     (235, 95, 95),
    "snake":      (94, 214, 159),
    "snake_head": (74, 184, 130),
    "food":       (240, 200, 70),
    "food_big":   (255, 140, 70),
    "poison":     (180, 50, 50),
    "obstacle":   (90, 90, 110),
    "shield_aura":(120, 200, 255),
    "powerup_speed":(120, 200, 255),
    "powerup_slow": (200, 130, 255),
    "powerup_shield":(255, 215, 100),
}

# ---- save file ---------------------------------------------------------
SETTINGS_FILE = "settings.json"
