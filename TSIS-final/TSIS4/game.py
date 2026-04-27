"""
TSIS 4 — Snake | game logic (snake, foods, power-ups, obstacles).
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import pygame

from config import (
    GRID_W, GRID_H,
    BASE_FPS, LEVEL_FOOD_STEP, SPEED_PER_LEVEL,
    OBSTACLE_LEVEL, OBSTACLES_PER_LV,
    POISON_PROBABILITY,
    POWERUP_LIFETIME_MS, POWERUP_DURATION_MS, POWERUP_SPAWN_CHANCE_PER_FOOD,
)

DIR_UP    = (0, -1)
DIR_DOWN  = (0,  1)
DIR_LEFT  = (-1, 0)
DIR_RIGHT = (1,  0)


@dataclass
class Food:
    pos:     tuple[int, int]
    kind:    str            # "small" | "big" | "poison"
    value:   int  = 1       # body growth (or shrinkage if poison)
    points:  int  = 10
    expires_at: int = 0     # 0 = never


@dataclass
class PowerUp:
    pos:        tuple[int, int]
    kind:       str         # "speed" | "slow" | "shield"
    spawned_at: int


# ---------------------------------------------------------------------------
class Game:
    """One round of snake."""

    def __init__(self):
        self.snake: deque[tuple[int, int]] = deque(
            [(GRID_W // 2, GRID_H // 2),
             (GRID_W // 2 - 1, GRID_H // 2),
             (GRID_W // 2 - 2, GRID_H // 2)]
        )
        self.dir       = DIR_RIGHT
        self.next_dir  = DIR_RIGHT

        self.score        = 0
        self.level        = 1
        self.foods_eaten  = 0
        self.over         = False

        self.foods:    list[Food] = []
        self.powerup:  Optional[PowerUp] = None
        self.obstacles: set[tuple[int, int]] = set()

        # active power-up effect
        self.effect:        Optional[str] = None
        self.effect_until:  int           = 0
        self.shield_active: bool          = False

        self._regenerate_obstacles()
        self._spawn_food()

    # ---------------------------------------------------------- direction
    def turn(self, d):
        # forbid 180° reverse
        if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
            self.next_dir = d

    # ---------------------------------------------------------- speed
    @property
    def fps(self) -> int:
        base = BASE_FPS + (self.level - 1) * SPEED_PER_LEVEL
        if self.effect == "speed":
            base += 5
        elif self.effect == "slow":
            base = max(3, base - 4)
        return base

    # ---------------------------------------------------------- main step
    def step(self):
        if self.over:
            return

        now = pygame.time.get_ticks()
        # power-up timing
        if self.effect and self.effect != "shield" and now > self.effect_until:
            self.effect = None
        # despawn power-up after lifetime
        if self.powerup and now - self.powerup.spawned_at > POWERUP_LIFETIME_MS:
            self.powerup = None
        # despawn timed foods
        self.foods = [f for f in self.foods
                      if f.expires_at == 0 or f.expires_at > now]

        self.dir = self.next_dir
        head = self.snake[0]
        new_head = (head[0] + self.dir[0], head[1] + self.dir[1])

        # ----- collisions
        # walls
        if (not 0 <= new_head[0] < GRID_W) or (not 0 <= new_head[1] < GRID_H):
            if self._consume_shield():
                # bounce-back: skip move
                return
            self.over = True
            return
        # obstacles
        if new_head in self.obstacles:
            if self._consume_shield():
                return
            self.over = True
            return
        # self-collision (excluding tail because it'll move)
        if new_head in list(self.snake)[:-1]:
            if self._consume_shield():
                return
            self.over = True
            return

        # ----- move snake
        self.snake.appendleft(new_head)
        ate = self._food_at(new_head)
        grew = False
        if ate:
            if ate.kind == "poison":
                # appendleft already added 1 to length; we want NET -2 from pre-step.
                # So pop 3 segments total.
                for _ in range(3):
                    if self.snake:
                        self.snake.pop()
                if len(self.snake) <= 1:
                    self.over = True
                    return
            else:
                # eating food = grow by `value`, but appendleft already added 1
                for _ in range(ate.value - 1):
                    # extend without moving by duplicating head until tail catches
                    self.snake.append(self.snake[-1])
                self.score += ate.points
                grew = True
                self.foods_eaten += 1
                self._maybe_level_up()
                if random.random() < POWERUP_SPAWN_CHANCE_PER_FOOD and not self.powerup:
                    self._spawn_powerup()
            self.foods.remove(ate)
            self._spawn_food()
        else:
            # didn't eat → move tail
            self.snake.pop()

        # collect power-up?
        if self.powerup and new_head == self.powerup.pos:
            self._activate_powerup(self.powerup.kind)
            self.powerup = None

    # ---------------------------------------------------------- helpers
    def _food_at(self, pos) -> Optional[Food]:
        for f in self.foods:
            if f.pos == pos:
                return f
        return None

    def _consume_shield(self) -> bool:
        if self.shield_active:
            self.shield_active = False
            self.effect = None
            return True
        return False

    def _maybe_level_up(self):
        new_level = 1 + self.foods_eaten // LEVEL_FOOD_STEP
        if new_level > self.level:
            self.level = new_level
            self._regenerate_obstacles()

    # ---------------------------------------------------------- spawns
    def _free_cells(self) -> set[tuple[int, int]]:
        used = set(self.snake) | self.obstacles | {f.pos for f in self.foods}
        if self.powerup:
            used.add(self.powerup.pos)
        all_cells = {(x, y) for x in range(GRID_W) for y in range(GRID_H)}
        return all_cells - used

    def _spawn_food(self):
        free = self._free_cells()
        if not free:
            return
        # Try to keep at least one regular food on the field
        has_regular = any(f.kind != "poison" for f in self.foods)

        # Decide kind
        kind_roll = random.random()
        now = pygame.time.get_ticks()

        if not has_regular or kind_roll < 0.55:
            kind, value, points, expires = "small", 1, 10, 0
        elif kind_roll < 0.75:
            kind, value, points, expires = "big", 2, 25, now + 6000   # disappears
        elif kind_roll < 0.75 + POISON_PROBABILITY:
            kind, value, points, expires = "poison", 0, 0, 0
        else:
            kind, value, points, expires = "small", 1, 10, 0

        self.foods.append(Food(random.choice(list(free)), kind, value, points, expires))

    def _spawn_powerup(self):
        free = self._free_cells()
        if not free:
            return
        kind = random.choice(["speed", "slow", "shield"])
        self.powerup = PowerUp(random.choice(list(free)), kind, pygame.time.get_ticks())

    def _activate_powerup(self, kind: str):
        self.effect = kind
        if kind == "shield":
            self.shield_active = True
            self.effect_until = 0  # effectively until used
        else:
            self.effect_until = pygame.time.get_ticks() + POWERUP_DURATION_MS

    def _regenerate_obstacles(self):
        """Rebuild obstacle layout for the current level."""
        self.obstacles.clear()
        if self.level < OBSTACLE_LEVEL:
            return

        count = OBSTACLES_PER_LV + (self.level - OBSTACLE_LEVEL) * 2

        # forbid cells too close to the snake's current head & body
        forbidden = set(self.snake)
        head = self.snake[0]
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                forbidden.add((head[0] + dx, head[1] + dy))

        all_cells = {(x, y) for x in range(GRID_W) for y in range(GRID_H)}
        candidates = list(all_cells - forbidden)
        random.shuffle(candidates)
        self.obstacles = set(candidates[:count])

        # remove any food that overlaps new obstacles
        self.foods = [f for f in self.foods if f.pos not in self.obstacles]
