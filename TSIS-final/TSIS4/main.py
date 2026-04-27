"""
TSIS 4 — Snake (Extended)
=================================================================

Entry point.  Wires together:
    config.py — constants
    db.py     — PostgreSQL persistence
    game.py   — gameplay state machine

Settings file: settings.json (snake colour, grid, sound).

Screens:  Main Menu, Game, Game Over, Leaderboard, Settings.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Callable

import pygame

import db
import game as gamemod
from config import (
    SCREEN_W, SCREEN_H, CELL, GRID_W, GRID_H, HUD_H,
    COLOR, SETTINGS_FILE,
)

DEFAULT_SETTINGS = {
    "snake_color": [94, 214, 159],
    "grid":  True,
    "sound": True,
}

# ---------------------------------------------------------------------------
# settings load / save
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(s: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# ---------------------------------------------------------------------------
# pygame init
# ---------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("TSIS-4 Snake")
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("dejavusansmono,arial", 38, bold=True)
font_med   = pygame.font.SysFont("dejavusans,arial", 22)
font_small = pygame.font.SysFont("dejavusansmono,arial", 16)

# optional beep (pygame.mixer)
beep_food = beep_dead = None
try:
    pygame.mixer.init()
    # synth tiny beeps so we don't ship binary assets
    import array, math
    def _tone(freq, ms, vol=0.3):
        n = int(44100 * ms / 1000)
        buf = array.array("h", (int(vol * 32767 * math.sin(2 * math.pi * freq * i / 44100))
                                for i in range(n)))
        return pygame.mixer.Sound(buffer=buf.tobytes())
    beep_food = _tone(880, 90)
    beep_dead = _tone(220, 350)
except Exception:
    pass


# ---------------------------------------------------------------------------
# button helper (minimal, kept local since only main.py uses it)
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, on_click: Callable[[], None],
                 colour=COLOR["accent"], fg=(20, 20, 20)):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.on_click = on_click
        self.colour  = colour
        self.fg      = fg

    def text(self):
        return self.label() if callable(self.label) else self.label

    def draw(self, surf, font):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        c = tuple(min(255, x + (25 if hover else 0)) for x in self.colour)
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        t = font.render(self.text(), True, self.fg)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and \
                self.rect.collidepoint(ev.pos):
            self.on_click()


def centered(surf, font, text, y, color=COLOR["text"]):
    s = font.render(text, True, color)
    surf.blit(s, s.get_rect(center=(SCREEN_W // 2, y)))


# ---------------------------------------------------------------------------
# username prompt
# ---------------------------------------------------------------------------
def prompt_username(default="player") -> str:
    name = default
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                if ev.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif ev.key == pygame.K_ESCAPE:
                    return name.strip() or default
                elif ev.unicode.isprintable() and len(name) < 14:
                    name += ev.unicode

        screen.fill(COLOR["bg"])
        centered(screen, font_title, "Enter your name", 180, COLOR["accent"])
        box = pygame.Rect(0, 0, 420, 60)
        box.center = (SCREEN_W // 2, 280)
        pygame.draw.rect(screen, COLOR["panel"], box, border_radius=10)
        pygame.draw.rect(screen, COLOR["accent"], box, 2, border_radius=10)
        centered(screen, font_med, name + "▌", box.centery)
        centered(screen, font_med, "Enter to start", 380, COLOR["dim"])
        if not db.is_online():
            centered(screen, font_small,
                     "(offline mode — DB not reachable, scores not saved)",
                     SCREEN_H - 30, COLOR["danger"])
        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# rendering — board, snake, foods, hud
# ---------------------------------------------------------------------------
def draw_board(g: gamemod.Game, settings: dict, name: str, pb: int):
    screen.fill(COLOR["bg"])

    # ----- HUD -----
    pygame.draw.rect(screen, COLOR["panel"], (0, 0, SCREEN_W, HUD_H))
    screen.blit(font_med.render(f"Score {g.score}", True, COLOR["text"]), (12, 8))
    screen.blit(font_med.render(f"Level {g.level}", True, COLOR["text"]), (12, 38))
    screen.blit(font_small.render(f"player: {name}", True, COLOR["dim"]), (200, 12))
    screen.blit(font_small.render(f"best:   {pb}",    True, COLOR["dim"]), (200, 32))
    screen.blit(font_small.render(f"len: {len(g.snake)}", True, COLOR["dim"]), (200, 52))

    if g.effect:
        remain = "" if g.effect == "shield" \
            else f"  {max(0, g.effect_until - pygame.time.get_ticks())//1000+1}s"
        screen.blit(font_small.render(f"power: {g.effect.upper()}{remain}",
                                      True, COLOR["accent"]), (380, 12))
    if g.shield_active:
        screen.blit(font_small.render("SHIELD ARMED", True, COLOR["accent"]), (380, 32))

    if not db.is_online():
        screen.blit(font_small.render("offline", True, COLOR["danger"]),
                    (SCREEN_W - 80, 12))

    # ----- play area background -----
    play_rect = pygame.Rect(0, HUD_H, SCREEN_W, SCREEN_H - HUD_H)
    pygame.draw.rect(screen, COLOR["bg"], play_rect)

    # grid overlay
    if settings.get("grid", True):
        for x in range(GRID_W + 1):
            pygame.draw.line(screen, COLOR["grid"],
                             (x * CELL, HUD_H),
                             (x * CELL, SCREEN_H), 1)
        for y in range(GRID_H + 1):
            pygame.draw.line(screen, COLOR["grid"],
                             (0,        HUD_H + y * CELL),
                             (SCREEN_W, HUD_H + y * CELL), 1)

    # obstacles
    for ox, oy in g.obstacles:
        pygame.draw.rect(screen, COLOR["obstacle"],
                         (ox * CELL + 1, HUD_H + oy * CELL + 1, CELL - 2, CELL - 2),
                         border_radius=3)

    # foods
    for f in g.foods:
        cx = f.pos[0] * CELL + CELL // 2
        cy = HUD_H + f.pos[1] * CELL + CELL // 2
        if f.kind == "poison":
            color = COLOR["poison"]
            pygame.draw.circle(screen, color, (cx, cy), CELL // 2 - 3)
            pygame.draw.line(screen, (255, 255, 255),
                             (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (cx - 4, cy + 4), (cx + 4, cy - 4), 2)
        elif f.kind == "big":
            pygame.draw.circle(screen, COLOR["food_big"], (cx, cy), CELL // 2 - 2)
        else:
            pygame.draw.circle(screen, COLOR["food"],     (cx, cy), CELL // 2 - 4)

    # power-up
    if g.powerup:
        cx = g.powerup.pos[0] * CELL + CELL // 2
        cy = HUD_H + g.powerup.pos[1] * CELL + CELL // 2
        col = COLOR[f"powerup_{g.powerup.kind}"]
        pygame.draw.rect(screen, col,
                         (cx - CELL//2 + 2, cy - CELL//2 + 2, CELL - 4, CELL - 4),
                         border_radius=6)
        letter = {"speed": "S", "slow": "L", "shield": "★"}[g.powerup.kind]
        s = font_small.render(letter, True, (20, 20, 20))
        screen.blit(s, s.get_rect(center=(cx, cy)))

    # snake
    snake_color = tuple(settings.get("snake_color", [94, 214, 159]))
    head_color  = tuple(min(255, c + 25) for c in snake_color)
    for i, (sx, sy) in enumerate(g.snake):
        c = head_color if i == 0 else snake_color
        pygame.draw.rect(screen, c,
                         (sx * CELL + 1, HUD_H + sy * CELL + 1, CELL - 2, CELL - 2),
                         border_radius=4)

    # shield aura
    if g.shield_active:
        hx, hy = g.snake[0]
        pygame.draw.rect(screen, COLOR["shield_aura"],
                         (hx * CELL - 1, HUD_H + hy * CELL - 1, CELL + 2, CELL + 2),
                         2, border_radius=6)


# ---------------------------------------------------------------------------
# main menu
# ---------------------------------------------------------------------------
def main_menu():
    state = {"a": None}
    btns = [
        Button((SCREEN_W//2-110, 220, 220, 50), "Play",
               lambda: state.update(a="play")),
        Button((SCREEN_W//2-110, 285, 220, 50), "Leaderboard",
               lambda: state.update(a="board"), colour=(120, 150, 255)),
        Button((SCREEN_W//2-110, 350, 220, 50), "Settings",
               lambda: state.update(a="settings"), colour=(180, 180, 180)),
        Button((SCREEN_W//2-110, 415, 220, 50), "Quit",
               lambda: state.update(a="quit"), colour=COLOR["danger"], fg=(255,255,255)),
    ]
    while state["a"] is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["a"] = "quit"
            for b in btns: b.handle(ev)
        screen.fill(COLOR["bg"])
        centered(screen, font_title, "SNAKE",  100, COLOR["accent"])
        centered(screen, font_med,   "Database edition", 150, COLOR["dim"])
        for b in btns: b.draw(screen, font_med)
        if not db.is_online():
            centered(screen, font_small,
                     "DB offline — playing in local mode",
                     SCREEN_H - 24, COLOR["danger"])
        pygame.display.flip()
        clock.tick(60)
    return state["a"]


# ---------------------------------------------------------------------------
# settings screen
# ---------------------------------------------------------------------------
def settings_screen(s: dict):
    palette = [
        ("Green",  [94, 214, 159]),
        ("Blue",   [80, 160, 230]),
        ("Red",    [220, 90, 90]),
        ("Yellow", [240, 220, 100]),
        ("Pink",   [255, 130, 200]),
    ]
    state = {"done": False}

    def cycle_color():
        cur = s.get("snake_color", palette[0][1])
        idx = next((i for i,(_,c) in enumerate(palette) if c == cur), -1)
        s["snake_color"] = palette[(idx + 1) % len(palette)][1]

    def color_label():
        for n, c in palette:
            if c == s["snake_color"]:
                return f"Snake colour: {n}"
        return "Snake colour: custom"

    btns = [
        Button((SCREEN_W//2-150, 180, 300, 50),
               lambda: f"Grid: {'ON' if s['grid'] else 'OFF'}",
               lambda: s.update(grid=not s["grid"])),
        Button((SCREEN_W//2-150, 250, 300, 50),
               lambda: f"Sound: {'ON' if s['sound'] else 'OFF'}",
               lambda: s.update(sound=not s["sound"])),
        Button((SCREEN_W//2-150, 320, 300, 50), color_label, cycle_color,
               colour=(180, 180, 255)),
        Button((SCREEN_W//2-150, 430, 300, 50), "Save & Back",
               lambda: state.update(done=True), colour=COLOR["accent"]),
    ]
    while not state["done"]:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                state["done"] = True
            for b in btns: b.handle(ev)
        screen.fill(COLOR["bg"])
        centered(screen, font_title, "Settings", 110, COLOR["accent"])
        for b in btns: b.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)
    save_settings(s)


# ---------------------------------------------------------------------------
# leaderboard screen
# ---------------------------------------------------------------------------
def leaderboard_screen():
    rows = db.top10()
    state = {"done": False}
    back  = Button((SCREEN_W//2-80, SCREEN_H-70, 160, 46), "Back",
                   lambda: state.update(done=True), colour=(180,180,180))
    while not state["done"]:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                state["done"] = True
            back.handle(ev)
        screen.fill(COLOR["bg"])
        centered(screen, font_title, "Top 10", 60, COLOR["accent"])

        if not rows:
            centered(screen, font_med,
                     "(no scores yet)" if db.is_online() else "(DB offline)",
                     220, COLOR["dim"])
        else:
            header = f"{'#':<3} {'name':<14} {'score':>6} {'lvl':>4}  date"
            screen.blit(font_small.render(header, True, COLOR["dim"]), (40, 130))
            y = 160
            for i, r in enumerate(rows, 1):
                d = r["played_at"].strftime("%Y-%m-%d %H:%M")
                line = (f"{i:<3} {r['username']:<14} "
                        f"{r['score']:>6} {r['level_reached']:>4}  {d}")
                screen.blit(font_small.render(line, True, COLOR["text"]), (40, y))
                y += 26
        back.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# game loop
# ---------------------------------------------------------------------------
def play(name: str, settings: dict):
    g  = gamemod.Game()
    pb = db.personal_best(name)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP,    pygame.K_w): g.turn(gamemod.DIR_UP)
                if ev.key in (pygame.K_DOWN,  pygame.K_s): g.turn(gamemod.DIR_DOWN)
                if ev.key in (pygame.K_LEFT,  pygame.K_a): g.turn(gamemod.DIR_LEFT)
                if ev.key in (pygame.K_RIGHT, pygame.K_d): g.turn(gamemod.DIR_RIGHT)
                if ev.key == pygame.K_ESCAPE:
                    return "menu"

        prev_score = g.score
        g.step()

        # sound
        if settings.get("sound", True):
            if g.score > prev_score and beep_food: beep_food.play()
            if g.over and beep_dead:               beep_dead.play()

        draw_board(g, settings, name, pb)
        pygame.display.flip()
        clock.tick(g.fps)

        if g.over:
            return game_over_screen(g, name, pb)


def game_over_screen(g: gamemod.Game, name: str, pb: int):
    saved = db.save_session(name, g.score, g.level)
    new_pb = max(pb, g.score)

    state = {"a": None}
    btns = [
        Button((SCREEN_W//2-150, SCREEN_H-130, 130, 48), "Retry",
               lambda: state.update(a="retry")),
        Button((SCREEN_W//2+20,  SCREEN_H-130, 130, 48), "Main Menu",
               lambda: state.update(a="menu"), colour=(180,180,180)),
    ]
    while state["a"] is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            for b in btns: b.handle(ev)
        screen.fill(COLOR["bg"])
        centered(screen, font_title, "GAME OVER", 110, COLOR["danger"])
        centered(screen, font_med, f"score: {g.score}",         200, COLOR["text"])
        centered(screen, font_med, f"level: {g.level}",          235, COLOR["text"])
        centered(screen, font_med, f"personal best: {new_pb}",   270, COLOR["accent"])
        if not saved:
            centered(screen, font_small, "(score not saved — DB offline)",
                     310, COLOR["danger"])
        for b in btns: b.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)
    return state["a"]


# ---------------------------------------------------------------------------
# top-level
# ---------------------------------------------------------------------------
def run():
    db.init_schema()
    settings = load_settings()
    name = None

    while True:
        action = main_menu()
        if action == "play":
            if not name:
                name = prompt_username()
            while True:
                result = play(name, settings)
                if result != "retry":
                    break
        elif action == "board":
            leaderboard_screen()
        elif action == "settings":
            settings_screen(settings)
        else:
            pygame.quit()
            return


if __name__ == "__main__":
    run()
