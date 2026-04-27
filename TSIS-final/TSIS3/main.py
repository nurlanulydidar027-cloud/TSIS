"""
TSIS 3 — Racer (Extended)
=================================================================

Entry point.  Wires together:
    persistence.py — settings.json / leaderboard.json
    racer.py       — gameplay state machine
    ui.py          — buttons, prompt_username, palette

Screens implemented (3.5):
    Main Menu, Settings, Leaderboard, Game Over.
"""
from __future__ import annotations

import sys

import pygame

import persistence
import racer
from ui import (
    Button, draw_centered, prompt_username,
    BG, PANEL, ACCENT, TEXT, DIM, DANGER,
)

pygame.init()
SCREEN_W, SCREEN_H = racer.SCREEN_W, racer.SCREEN_H
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("TSIS-3 Racer")
clock = pygame.time.Clock()

font_big   = pygame.font.SysFont("dejavusansmono,arial", 36, bold=True)
font_med   = pygame.font.SysFont("dejavusans,arial", 22)
font_small = pygame.font.SysFont("dejavusans,arial", 16)


# ---------------------------------------------------------------------------
# road / HUD rendering
# ---------------------------------------------------------------------------
def draw_road(surf, dash_offset: int):
    surf.fill((58, 60, 64))
    # grass
    pygame.draw.rect(surf, (38, 78, 50), (0, 0, racer.ROAD_LEFT, SCREEN_H))
    pygame.draw.rect(surf, (38, 78, 50),
                     (racer.ROAD_RIGHT, 0, SCREEN_W - racer.ROAD_RIGHT, SCREEN_H))
    # road edges
    pygame.draw.rect(surf, (245, 245, 245), (racer.ROAD_LEFT - 3, 0, 3, SCREEN_H))
    pygame.draw.rect(surf, (245, 245, 245), (racer.ROAD_RIGHT,    0, 3, SCREEN_H))
    # lane dashes
    for i in range(1, racer.LANES):
        x = racer.ROAD_LEFT + racer.LANE_W * i
        for y in range(-40 + dash_offset, SCREEN_H, 40):
            pygame.draw.rect(surf, (235, 235, 235), (x - 2, y, 4, 22))


def draw_car(surf, rect: pygame.Rect, color):
    pygame.draw.rect(surf, color, rect, border_radius=8)
    # windshield
    ws = rect.inflate(-12, -50).move(0, -10)
    ws.height = 24
    ws.centerx = rect.centerx
    ws.centery = rect.centery - 12
    pygame.draw.rect(surf, (180, 220, 255), ws, border_radius=4)
    # wheels
    for dx in (-2, rect.width - 6):
        for dy in (8, rect.height - 22):
            pygame.draw.rect(surf, (20, 20, 20),
                             (rect.x + dx, rect.y + dy, 6, 14), border_radius=2)


def draw_obstacle(surf, e):
    r = e.rect
    if e.kind == "oil":
        pygame.draw.ellipse(surf, (20, 20, 20), r)
    elif e.kind == "pothole":
        pygame.draw.ellipse(surf, (15, 15, 15), r)
        pygame.draw.ellipse(surf, (60, 60, 60), r.inflate(-12, -30))
    elif e.kind == "barrier":
        pygame.draw.rect(surf, (240, 200, 50), r, border_radius=6)
        pygame.draw.rect(surf, (40, 40, 40), r, 3, border_radius=6)
    elif e.kind == "bump":
        pygame.draw.rect(surf, (220, 220, 220), r, border_radius=4)
        for i in range(3):
            pygame.draw.rect(surf, (40, 40, 40),
                             (r.x + 4, r.y + 8 + i * 22, r.w - 8, 6))


def draw_coin(surf, r):
    pygame.draw.circle(surf, (255, 215, 0), r.center, 14)
    pygame.draw.circle(surf, (200, 160, 0), r.center, 14, 2)


def draw_powerup(surf, e):
    r = e.rect
    pygame.draw.rect(surf, e.color, r, border_radius=10)
    label = {"nitro": "N", "shield": "S", "repair": "R"}[e.kind]
    s = font_med.render(label, True, (20, 20, 20))
    surf.blit(s, s.get_rect(center=r.center))


def draw_hud(surf, game: racer.Racer):
    pygame.draw.rect(surf, (0, 0, 0, 120), (0, 0, SCREEN_W, 60))
    surf.blit(font_small.render(f"score {game.score}",        True, TEXT),  (10, 8))
    surf.blit(font_small.render(f"coins {game.coins_count}",  True, TEXT),  (10, 28))
    surf.blit(font_small.render(f"speed {game.speed}",        True, TEXT),  (140, 8))

    # progress bar
    pct = min(1.0, game.distance / racer.FINISH_DISTANCE)
    pygame.draw.rect(surf, (50, 50, 50),  (260, 14, 200, 14), border_radius=4)
    pygame.draw.rect(surf, ACCENT,        (260, 14, int(200 * pct), 14), border_radius=4)
    surf.blit(font_small.render(f"{int(pct*100)}%", True, TEXT), (470, 10))

    if game.active_power:
        remain = max(0, game.power_until - pygame.time.get_ticks()) // 1000
        label = f"{game.active_power.upper()}"
        if game.active_power == "nitro":
            label += f"  {remain}s"
        elif game.active_power == "shield":
            label += "  (until hit)"
        surf.blit(font_small.render(label, True, ACCENT), (140, 28))

    if game.last_event and pygame.time.get_ticks() < game.last_event_until:
        s = font_med.render(game.last_event, True, ACCENT)
        surf.blit(s, s.get_rect(center=(SCREEN_W // 2, 100)))


# ---------------------------------------------------------------------------
# screens
# ---------------------------------------------------------------------------
def main_menu():
    state = {"action": None}

    def go(action): state["action"] = action

    buttons = [
        Button((SCREEN_W//2-110, 280, 220, 50), "Play",        lambda: go("play")),
        Button((SCREEN_W//2-110, 345, 220, 50), "Leaderboard", lambda: go("board"), colour=(120,150,255)),
        Button((SCREEN_W//2-110, 410, 220, 50), "Settings",    lambda: go("settings"), colour=(180,180,180)),
        Button((SCREEN_W//2-110, 475, 220, 50), "Quit",        lambda: go("quit"),     colour=DANGER, fg=(255,255,255)),
    ]

    while state["action"] is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["action"] = "quit"
            for b in buttons:
                b.handle(ev)

        screen.fill(BG)
        draw_centered(screen, font_big, "RACER", 130, ACCENT)
        draw_centered(screen, font_med, "Arcade Road Course", 180, DIM)
        for b in buttons:
            b.draw(screen, font_med)
        draw_centered(screen, font_small, "← / → drive   Esc menu", SCREEN_H - 24, DIM)
        pygame.display.flip()
        clock.tick(60)
    return state["action"]


def settings_screen(settings):
    color_keys = list(racer.CAR_COLORS.keys())
    diff_keys  = ["easy", "normal", "hard"]
    state = {"done": False}

    def cycle_color():
        i = color_keys.index(settings["car_color"])
        settings["car_color"] = color_keys[(i + 1) % len(color_keys)]

    def cycle_diff():
        i = diff_keys.index(settings["difficulty"])
        settings["difficulty"] = diff_keys[(i + 1) % len(diff_keys)]

    def toggle_sound():
        settings["sound"] = not settings["sound"]

    def save_back():
        persistence.save_settings(settings)
        state["done"] = True

    btns = [
        Button((SCREEN_W//2-130, 200, 260, 50),
               lambda: f"Sound: {'ON' if settings['sound'] else 'OFF'}",
               toggle_sound),
        Button((SCREEN_W//2-130, 270, 260, 50),
               lambda: f"Car colour: {settings['car_color']}", cycle_color,
               colour=(180,180,255)),
        Button((SCREEN_W//2-130, 340, 260, 50),
               lambda: f"Difficulty: {settings['difficulty']}", cycle_diff,
               colour=(255,200,120)),
        Button((SCREEN_W//2-130, 460, 260, 50),
               "Save & Back", save_back, colour=ACCENT),
    ]

    while not state["done"]:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                save_back()
            for b in btns: b.handle(ev)

        screen.fill(BG)
        draw_centered(screen, font_big, "Settings", 110, ACCENT)
        for b in btns:
            # update label dynamically
            if callable(b.label):
                b.label_text = b.label()
            else:
                b.label_text = b.label
            # draw with current text
            mx, my = pygame.mouse.get_pos()
            hover = b.rect.collidepoint(mx, my)
            pygame.draw.rect(screen,
                             tuple(min(255, c + (25 if hover else 0)) for c in b.colour),
                             b.rect, border_radius=10)
            t = font_med.render(b.label_text, True, b.fg)
            screen.blit(t, t.get_rect(center=b.rect.center))
        pygame.display.flip()
        clock.tick(60)


def leaderboard_screen():
    board = persistence.load_leaderboard()
    state = {"done": False}
    back = Button((SCREEN_W//2-80, SCREEN_H-80, 160, 46),
                  "Back", lambda: state.update(done=True),
                  colour=(180, 180, 180))

    while not state["done"]:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                state["done"] = True
            back.handle(ev)

        screen.fill(BG)
        draw_centered(screen, font_big, "Leaderboard", 70, ACCENT)
        if not board:
            draw_centered(screen, font_med, "(no scores yet)", 200, DIM)
        else:
            y = 130
            screen.blit(font_small.render(
                f"{'#':<3} {'name':<14} {'score':>6} {'dist':>6} {'coins':>6} date",
                True, DIM), (40, y))
            y += 26
            for i, r in enumerate(board, 1):
                line = (
                    f"{i:<3} {r['name']:<14} "
                    f"{r['score']:>6} {r['distance']:>6} {r['coins']:>6} "
                    f"{r.get('date','')}"
                )
                screen.blit(font_small.render(line, True, TEXT), (40, y))
                y += 24
        back.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)


def game_over_screen(game: racer.Racer, name: str):
    persistence.add_score(name, game.score, game.distance, game.coins_count)
    state = {"action": None}

    btns = [
        Button((SCREEN_W//2-140, 480, 130, 48), "Retry",
               lambda: state.update(action="retry")),
        Button((SCREEN_W//2+10, 480, 130, 48), "Main Menu",
               lambda: state.update(action="menu"), colour=(180, 180, 180)),
    ]

    title  = "FINISHED!" if game.finished else "GAME OVER"
    color  = ACCENT if game.finished else DANGER

    while state["action"] is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            for b in btns: b.handle(ev)

        screen.fill(BG)
        draw_centered(screen, font_big, title, 140, color)
        draw_centered(screen, font_med, f"score: {game.score}",        230, TEXT)
        draw_centered(screen, font_med, f"distance: {game.distance}",   270, TEXT)
        draw_centered(screen, font_med, f"coins: {game.coins_count}",   310, TEXT)
        draw_centered(screen, font_small, f"name: {name}",              340, DIM)
        for b in btns: b.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)
    return state["action"]


# ---------------------------------------------------------------------------
# play loop
# ---------------------------------------------------------------------------
def play(name: str, settings: dict):
    game = racer.Racer(settings)

    while True:
        dt = clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_LEFT,  pygame.K_a): game.move_left()
                if ev.key in (pygame.K_RIGHT, pygame.K_d): game.move_right()
                if ev.key == pygame.K_ESCAPE:
                    return "menu"

        game.update(dt)

        # render
        draw_road(screen, game.lane_dash_offset)
        for o in game.obstacles: draw_obstacle(screen, o)
        for c in game.coins:     draw_coin(screen, c.rect)
        for p in game.powerups:  draw_powerup(screen, p)
        for t in game.traffic:   draw_car(screen, t.rect, t.color)

        # player car
        pr = pygame.Rect(racer.LANE_X[game.player_lane] - racer.CAR_W/2,
                         game.player_y, racer.CAR_W, racer.CAR_H)
        draw_car(screen, pr, game.player_color)
        # shield aura
        if game.shield:
            pygame.draw.rect(screen, ACCENT, pr.inflate(10, 10), 3, border_radius=10)

        draw_hud(screen, game)
        pygame.display.flip()

        if game.over or game.finished:
            return game_over_screen(game, name)


# ---------------------------------------------------------------------------
# top-level state machine
# ---------------------------------------------------------------------------
def run():
    settings = persistence.load_settings()
    name     = None

    while True:
        action = main_menu()
        if action == "play":
            if not name:
                name = prompt_username(screen, font_big, font_med)
            result = play(name, settings)
            if result == "retry":
                # loop back into play
                while play(name, settings) == "retry":
                    pass
        elif action == "board":
            leaderboard_screen()
        elif action == "settings":
            settings_screen(settings)
        else:  # quit
            pygame.quit()
            return


if __name__ == "__main__":
    run()
