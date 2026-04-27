"""
TSIS 3 — Racer | UI helpers: menus, buttons, text-input, screens.

Keeps drawing concerns out of the gameplay file.  Uses only Pygame.
"""
from __future__ import annotations

import pygame
from typing import Callable

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------
BG          = (24, 28, 36)
PANEL       = (38, 42, 54)
ACCENT      = (94, 214, 159)
TEXT        = (235, 235, 235)
DIM         = (150, 158, 170)
DANGER      = (235, 95, 95)


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, on_click: Callable[[], None],
                 colour=ACCENT, fg=(20, 20, 20)):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.on_click = on_click
        self.colour  = colour
        self.fg      = fg

    def draw(self, screen, font):
        mx, my  = pygame.mouse.get_pos()
        hover   = self.rect.collidepoint(mx, my)
        pygame.draw.rect(
            screen,
            tuple(min(255, c + (25 if hover else 0)) for c in self.colour),
            self.rect, border_radius=10,
        )
        text = font.render(self.label, True, self.fg)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.on_click()


# ---------------------------------------------------------------------------
# centred draw helpers
# ---------------------------------------------------------------------------
def draw_centered(screen, font, text, y, color=TEXT):
    s = font.render(text, True, color)
    screen.blit(s, s.get_rect(center=(screen.get_width() // 2, y)))


# ---------------------------------------------------------------------------
# Username entry — modal-style screen
# ---------------------------------------------------------------------------
def prompt_username(screen, font_big, font_med, default="player") -> str:
    name  = default
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                if ev.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif ev.key == pygame.K_ESCAPE:
                    return name.strip() or default
                elif ev.unicode.isprintable() and len(name) < 14:
                    name += ev.unicode

        screen.fill(BG)
        draw_centered(screen, font_big, "Enter your name", 220, ACCENT)
        # input box
        box = pygame.Rect(0, 0, 420, 60)
        box.center = (screen.get_width() // 2, 320)
        pygame.draw.rect(screen, PANEL, box, border_radius=10)
        pygame.draw.rect(screen, ACCENT, box, 2, border_radius=10)
        draw_centered(screen, font_med, name + "▌", box.centery)
        draw_centered(screen, font_med, "Enter to start", 420, DIM)
        pygame.display.flip()
        clock.tick(60)
