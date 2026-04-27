"""
TSIS 3 — Racer | core gameplay (track, traffic, obstacles, power-ups).

Decoupled from the menu / screen layer in main.py so the game itself
can be tested in isolation.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import pygame

# ---------------------------------------------------------------------------
# track geometry
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 540, 720
ROAD_LEFT  = 70
ROAD_RIGHT = SCREEN_W - 70
ROAD_W     = ROAD_RIGHT - ROAD_LEFT
LANES      = 4
LANE_W     = ROAD_W / LANES
LANE_X     = [ROAD_LEFT + LANE_W * (i + 0.5) for i in range(LANES)]

CAR_W, CAR_H = 50, 90

CAR_COLORS = {
    "red":    (220, 60, 60),
    "blue":   (70, 130, 220),
    "green":  (80, 180, 100),
    "yellow": (240, 200, 70),
    "black":  (35, 35, 40),
}

DIFFICULTY = {
    "easy":   {"base_speed": 4, "spawn": 90,  "obstacle_chance": 0.20},
    "normal": {"base_speed": 6, "spawn": 65,  "obstacle_chance": 0.30},
    "hard":   {"base_speed": 8, "spawn": 45,  "obstacle_chance": 0.45},
}

FINISH_DISTANCE = 12_000   # pixels of travel = 1 race


# ---------------------------------------------------------------------------
# entities
# ---------------------------------------------------------------------------
@dataclass
class Entity:
    lane: int
    y:    float
    kind: str
    color: tuple = (200, 200, 200)
    extra: dict = field(default_factory=dict)

    @property
    def rect(self) -> pygame.Rect:
        x = LANE_X[self.lane] - CAR_W / 2
        return pygame.Rect(x, self.y, CAR_W, CAR_H)


# ---------------------------------------------------------------------------
# main game
# ---------------------------------------------------------------------------
class Racer:
    """One race.  Holds player, traffic, obstacles, power-ups, score."""

    def __init__(self, settings: dict):
        cfg = DIFFICULTY[settings.get("difficulty", "normal")]
        self.base_speed       = cfg["base_speed"]
        self.spawn_interval   = cfg["spawn"]
        self.obstacle_chance  = cfg["obstacle_chance"]

        self.player_color = CAR_COLORS.get(settings.get("car_color", "red"),
                                           CAR_COLORS["red"])

        self.player_lane  = LANES // 2
        self.player_y     = SCREEN_H - CAR_H - 30
        self.speed        = self.base_speed

        self.traffic:    list[Entity] = []
        self.obstacles:  list[Entity] = []
        self.coins:      list[Entity] = []
        self.powerups:   list[Entity] = []

        self.score        = 0
        self.coins_count  = 0
        self.distance     = 0  # pixels
        self.spawn_timer  = 0
        self.frame        = 0

        # active power-up
        self.active_power: Optional[str] = None
        self.power_until: int = 0
        self.shield: bool = False

        # game flags
        self.over     = False
        self.finished = False
        self.last_event: str = ""
        self.last_event_until = 0

        # road animation
        self.lane_dash_offset = 0

    # -------------------------------------------------------------- input
    def move_left(self):
        if self.player_lane > 0:
            self.player_lane -= 1

    def move_right(self):
        if self.player_lane < LANES - 1:
            self.player_lane += 1

    # -------------------------------------------------------------- core loop
    def update(self, dt_ms: int):
        if self.over or self.finished:
            return
        self.frame += 1

        # difficulty ramp -- every 1500 px add a tiny speed bump
        ramp = self.distance // 1500
        cur_speed = self.base_speed + ramp + (4 if self.active_power == "nitro" else 0)
        self.speed = cur_speed
        self.distance += int(cur_speed)
        self.lane_dash_offset = (self.lane_dash_offset + cur_speed) % 40

        # spawn
        self.spawn_timer += 1
        if self.spawn_timer >= max(20, self.spawn_interval - ramp * 2):
            self.spawn_timer = 0
            self._spawn()

        # move all entities downward; cull off-screen
        for col in (self.traffic, self.obstacles, self.coins, self.powerups):
            for e in col:
                e.y += cur_speed
            col[:] = [e for e in col if e.y < SCREEN_H + 100]

        # collisions
        self._handle_collisions()

        # passive scoring
        self.score = self.coins_count * 10 + self.distance // 10

        # power-up timer
        if self.active_power and pygame.time.get_ticks() > self.power_until:
            if self.active_power != "shield":  # shield ends on hit
                self.active_power = None

        # finish line
        if self.distance >= FINISH_DISTANCE:
            self.finished = True
            self.score += 500

    # -------------------------------------------------------------- spawning
    def _safe_lane(self) -> int:
        """Pick a lane that does not overlap with the player or recent spawns."""
        candidate_lanes = list(range(LANES))
        random.shuffle(candidate_lanes)
        for ln in candidate_lanes:
            # never spawn directly on top of the player's lane near the bottom
            if ln == self.player_lane and self._has_anything_in(ln, top=SCREEN_H * 0.55):
                continue
            if not self._has_anything_in(ln, top=-CAR_H, bottom=120):
                return ln
        return random.randint(0, LANES - 1)

    def _has_anything_in(self, lane: int, top=-200, bottom=200) -> bool:
        for col in (self.traffic, self.obstacles, self.coins, self.powerups):
            for e in col:
                if e.lane == lane and top <= e.y <= bottom:
                    return True
        return False

    def _spawn(self):
        kind_roll = random.random()
        lane = self._safe_lane()
        y    = -CAR_H - 20

        if kind_roll < 0.45:                                # traffic
            color = random.choice([(180,80,80),(80,80,180),(80,180,80),(40,40,40)])
            self.traffic.append(Entity(lane, y, "car", color))
        elif kind_roll < 0.45 + self.obstacle_chance * 0.6:  # static obstacle
            otype = random.choice(["barrier", "oil", "pothole", "bump"])
            self.obstacles.append(Entity(lane, y, otype, (200,160,40)))
        elif kind_roll < 0.85:                              # coin (sometimes 2x)
            big = random.random() < 0.2
            self.coins.append(Entity(lane, y, "coin",
                                     (255,215,0),
                                     extra={"value": 5 if big else 1}))
        else:                                               # power-up
            ptype = random.choice(["nitro", "shield", "repair"])
            self.powerups.append(Entity(lane, y, ptype,
                                        {"nitro":(0,200,255),
                                         "shield":(120,255,160),
                                         "repair":(255,140,200)}[ptype]))

        # occasional nitro strip event (advertised to user via banner)
        if random.random() < 0.02:
            self.last_event = "NITRO STRIP!"
            self.last_event_until = pygame.time.get_ticks() + 1500

    # -------------------------------------------------------------- collisions
    def _player_rect(self) -> pygame.Rect:
        x = LANE_X[self.player_lane] - CAR_W / 2
        return pygame.Rect(x, self.player_y, CAR_W, CAR_H)

    def _handle_collisions(self):
        pr = self._player_rect()

        # coins
        new_coins = []
        for c in self.coins:
            if pr.colliderect(c.rect):
                self.coins_count += c.extra.get("value", 1)
            else:
                new_coins.append(c)
        self.coins = new_coins

        # power-ups
        new_pu = []
        for p in self.powerups:
            if pr.colliderect(p.rect):
                self._apply_powerup(p.kind)
            else:
                new_pu.append(p)
        self.powerups = new_pu

        # traffic
        for t in list(self.traffic):
            if pr.colliderect(t.rect):
                if self.shield:
                    self.shield = False
                    self.active_power = None
                    self.last_event = "SHIELD ABSORBED HIT"
                    self.last_event_until = pygame.time.get_ticks() + 1200
                    self.traffic.remove(t)
                else:
                    self.over = True
                    return

        # obstacles
        for o in list(self.obstacles):
            if pr.colliderect(o.rect):
                if o.kind == "oil":          # spin-out: lose a coin and slow
                    self.coins_count = max(0, self.coins_count - 2)
                    self.last_event = "OIL!  -2 COINS"
                    self.last_event_until = pygame.time.get_ticks() + 1500
                    self.obstacles.remove(o)
                elif self.shield:
                    self.shield = False
                    self.active_power = None
                    self.obstacles.remove(o)
                else:
                    self.over = True
                    return

    def _apply_powerup(self, kind: str):
        self.active_power = kind
        now = pygame.time.get_ticks()
        if kind == "nitro":
            self.power_until = now + 4000
        elif kind == "shield":
            self.shield = True
            self.power_until = now + 60_000  # effectively until hit
        elif kind == "repair":
            self.coins_count += 5
            self.last_event = "REPAIR! +5 COINS"
            self.last_event_until = now + 1500
            self.active_power = None  # instant
        self.last_event = self.last_event or kind.upper()
