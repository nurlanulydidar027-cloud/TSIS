"""
TSIS 2 — Paint  (Extended)
=================================================================

Pygame-only paint application that combines Practice 10 / 11 shapes
with the new TSIS-2 tools:

    Pencil         — freehand
    Line           — click-drag, live preview
    Rect/Square    — bounding-box, live preview
    Circle         — radius from click, live preview
    R-Triangle     — right triangle from click-drag
    E-Triangle     — equilateral, centred between click points
    Rhombus        — diamond inscribed in click-drag rectangle
    Eraser         — pencil with background colour
    Flood-fill     — get_at / set_at iterative 4-way fill
    Text           — click, type, Enter/Esc

Brush size : 1=small(2px) 2=medium(5px) 3=large(10px)
Save       : Ctrl+S        — file name has timestamp, can't be overwritten
Clear      : Ctrl+N
Quit       : Esc on empty canvas, or window close
"""
from __future__ import annotations

import datetime as dt
import sys

import pygame

from tools import make_tool_set, TextTool

# ---------------------------------------------------------------------------
# layout / palette
# ---------------------------------------------------------------------------
WIN_W, WIN_H = 1100, 700
TOOLBAR_W    = 180
CANVAS_RECT  = pygame.Rect(TOOLBAR_W, 0, WIN_W - TOOLBAR_W, WIN_H)
BG_COLOR     = (255, 255, 255)
TOOLBAR_BG   = (38, 41, 48)
TEXT_COLOR   = (230, 230, 230)
ACCENT       = (94, 214, 159)

PALETTE = [
    (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 200, 0),
    (0, 120, 255), (255, 200, 0), (200, 0, 200), (0, 200, 200),
    (255, 128, 0), (128, 64, 0), (180, 180, 180), (60, 60, 60),
]

SIZES = {pygame.K_1: 2, pygame.K_2: 5, pygame.K_3: 10}
DEFAULT_SIZE = 5

TOOL_KEYS = [
    ("P", "Pencil"), ("L", "Line"),
    ("R", "Rect"),   ("S", "Square"),
    ("C", "Circle"), ("T", "R-Tri"),
    ("E", "E-Tri"),  ("H", "Rhomb"),
    ("F", "Fill"),   ("X", "Eraser"),
    ("Y", "Text"),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def in_canvas(pos):
    return CANVAS_RECT.collidepoint(pos)


def to_canvas_coords(pos):
    """Translate a window position to canvas-local coords."""
    return pos[0] - CANVAS_RECT.x, pos[1] - CANVAS_RECT.y


def save_canvas(canvas):
    fname = f"paint_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
    pygame.image.save(canvas, fname)
    print(f"saved → {fname}")
    return fname


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("TSIS-2 Paint")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock  = pygame.time.Clock()

    ui_font   = pygame.font.SysFont("dejavusansmono,arial", 14)
    text_font = pygame.font.SysFont("dejavusans,arial", 22)

    canvas = pygame.Surface(CANVAS_RECT.size)
    canvas.fill(BG_COLOR)

    tools  = make_tool_set(text_font)
    active_key = "P"
    color = (0, 0, 0)
    size  = DEFAULT_SIZE

    drawing = False  # mouse held down
    save_flash = 0

    # text-tool typing state
    typing       = False
    typing_pos   = (0, 0)
    typing_text  = ""

    while True:
        # ------------------------------------------------------------- events
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ------------------------ keyboard ------------------------
            if ev.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()

                # text-input mode hijacks the keyboard
                if typing:
                    if ev.key == pygame.K_RETURN:
                        tools["Y"].render(canvas, typing_pos, color, typing_text)
                        typing, typing_text = False, ""
                    elif ev.key == pygame.K_ESCAPE:
                        typing, typing_text = False, ""
                    elif ev.key == pygame.K_BACKSPACE:
                        typing_text = typing_text[:-1]
                    elif ev.unicode and ev.unicode.isprintable():
                        typing_text += ev.unicode
                    continue

                # save / clear shortcuts
                if (mods & pygame.KMOD_CTRL) and ev.key == pygame.K_s:
                    save_canvas(canvas); save_flash = pygame.time.get_ticks()
                    continue
                if (mods & pygame.KMOD_CTRL) and ev.key == pygame.K_n:
                    canvas.fill(BG_COLOR); continue

                # brush sizes 1/2/3
                if ev.key in SIZES:
                    size = SIZES[ev.key]; continue

                # tool keys
                key_letter = pygame.key.name(ev.key).upper()
                if key_letter in tools:
                    active_key = key_letter
                    drawing = False  # cancel any in-progress shape
                    continue

                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

            # ------------------------ mouse ---------------------------
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                # toolbar click?
                if ev.pos[0] < TOOLBAR_W:
                    handle_toolbar_click(ev.pos, locals_dict := locals())
                    # re-extract values that toolbar may have changed
                    active_key = locals_dict["active_key"]
                    color      = locals_dict["color"]
                    size       = locals_dict["size"]
                    continue

                # canvas click
                if in_canvas(ev.pos):
                    cpos = to_canvas_coords(ev.pos)

                    # Text tool: click positions caret, no drag
                    if active_key == "Y":
                        typing = True
                        typing_pos = cpos
                        typing_text = ""
                        continue

                    drawing = True
                    erase_color = BG_COLOR if active_key == "X" else color
                    tools[active_key].on_mouse_down(canvas, cpos, erase_color, size)

            elif ev.type == pygame.MOUSEMOTION and drawing:
                if in_canvas(ev.pos):
                    cpos = to_canvas_coords(ev.pos)
                    erase_color = BG_COLOR if active_key == "X" else color
                    tools[active_key].on_mouse_drag(canvas, cpos, erase_color, size)

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and drawing:
                cpos = to_canvas_coords(ev.pos)
                erase_color = BG_COLOR if active_key == "X" else color
                tools[active_key].on_mouse_up(canvas, cpos, erase_color, size)
                drawing = False

        # ------------------------------------------------------------- render
        screen.fill(TOOLBAR_BG)
        draw_toolbar(screen, ui_font, active_key, color, size)
        screen.blit(canvas, CANVAS_RECT.topleft)

        # live preview (line / shape tools paint to a transparent overlay)
        overlay = pygame.Surface(CANVAS_RECT.size, pygame.SRCALPHA)
        if drawing and not isinstance(tools[active_key], TextTool):
            tools[active_key].preview(overlay, color, size)
        screen.blit(overlay, CANVAS_RECT.topleft)

        # text-tool live caret
        if typing:
            caret = text_font.render(typing_text + "▌", True, color)
            screen.blit(caret, (CANVAS_RECT.x + typing_pos[0],
                                CANVAS_RECT.y + typing_pos[1]))

        # save toast
        if save_flash and pygame.time.get_ticks() - save_flash < 1500:
            toast = ui_font.render("✓ saved", True, ACCENT)
            screen.blit(toast, (WIN_W - 80, 10))

        pygame.display.flip()
        clock.tick(120)


# ---------------------------------------------------------------------------
# toolbar drawing & click handling
# ---------------------------------------------------------------------------
def draw_toolbar(screen, font, active_key, color, size):
    pygame.draw.rect(screen, TOOLBAR_BG, (0, 0, TOOLBAR_W, WIN_H))
    y = 10

    label(screen, font, "TOOLS", 10, y); y += 22
    for i, (k, name) in enumerate(TOOL_KEYS):
        rect = pygame.Rect(10, y, TOOLBAR_W - 20, 26)
        active = (k == active_key)
        pygame.draw.rect(screen, ACCENT if active else (60, 64, 72), rect, border_radius=6)
        screen.blit(font.render(f"[{k}] {name}", True,
                                (20, 20, 20) if active else TEXT_COLOR),
                    (rect.x + 8, rect.y + 6))
        y += 30

    y += 6
    label(screen, font, "SIZE  (1/2/3)", 10, y); y += 22
    for k, px in [(pygame.K_1, 2), (pygame.K_2, 5), (pygame.K_3, 10)]:
        active = (px == size)
        rect = pygame.Rect(10, y, TOOLBAR_W - 20, 22)
        pygame.draw.rect(screen, ACCENT if active else (60, 64, 72), rect, border_radius=6)
        screen.blit(font.render(f"{px}px", True,
                                (20, 20, 20) if active else TEXT_COLOR),
                    (rect.x + 8, rect.y + 4))
        y += 26

    y += 8
    label(screen, font, "COLOUR", 10, y); y += 22
    sw = 28
    for i, c in enumerate(PALETTE):
        col = i % 4
        row = i // 4
        rect = pygame.Rect(10 + col * (sw + 6), y + row * (sw + 6), sw, sw)
        pygame.draw.rect(screen, c, rect, border_radius=4)
        if c == color:
            pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=4)
    y += ((len(PALETTE) + 3) // 4) * (sw + 6) + 6

    label(screen, font, "Ctrl+S  save", 10, WIN_H - 60)
    label(screen, font, "Ctrl+N  clear", 10, WIN_H - 40)
    label(screen, font, "Esc     quit",  10, WIN_H - 20)


def label(screen, font, text, x, y):
    screen.blit(font.render(text, True, TEXT_COLOR), (x, y))


def handle_toolbar_click(pos, frame):
    """Translate a toolbar click into a state mutation in the caller frame."""
    x, y = pos

    # --- tool buttons ---
    yy = 10 + 22
    for k, _ in TOOL_KEYS:
        if pygame.Rect(10, yy, TOOLBAR_W - 20, 26).collidepoint(pos):
            frame["active_key"] = k
            return
        yy += 30

    # --- size buttons ---
    yy += 6 + 22
    for px in (2, 5, 10):
        if pygame.Rect(10, yy, TOOLBAR_W - 20, 22).collidepoint(pos):
            frame["size"] = px
            return
        yy += 26

    # --- palette ---
    yy += 8 + 22
    sw = 28
    for i, c in enumerate(PALETTE):
        col = i % 4
        row = i // 4
        r = pygame.Rect(10 + col * (sw + 6), yy + row * (sw + 6), sw, sw)
        if r.collidepoint(pos):
            frame["color"] = c
            return


if __name__ == "__main__":
    main()
