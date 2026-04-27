"""
TSIS 2 — Paint | Tool implementations.

All drawing tools share a common interface so paint.py can dispatch
mouse / keyboard events generically:

    on_mouse_down(canvas, pos, color, size)   -> None | Surface
    on_mouse_drag(canvas, pos, color, size)   -> None | Surface
    on_mouse_up  (canvas, pos, color, size)   -> None | Surface
    preview      (overlay, color, size)       -> draws live preview

The "preview" call lets the main loop paint a non-destructive
overlay on top of the canvas while the user is dragging.
"""
from __future__ import annotations

import math
from collections import deque

import pygame


# ---------------------------------------------------------------------------
# base
# ---------------------------------------------------------------------------
class Tool:
    """Abstract tool — override the methods you care about."""
    name = "tool"

    def on_mouse_down(self, canvas, pos, color, size): pass
    def on_mouse_drag(self, canvas, pos, color, size): pass
    def on_mouse_up  (self, canvas, pos, color, size): pass
    def preview      (self, overlay, color, size):     pass


# ---------------------------------------------------------------------------
# 3.1.1   Pencil — freehand
# ---------------------------------------------------------------------------
class PencilTool(Tool):
    name = "pencil"

    def __init__(self):
        self._last = None

    def on_mouse_down(self, canvas, pos, color, size):
        self._last = pos
        pygame.draw.circle(canvas, color, pos, max(1, size // 2))

    def on_mouse_drag(self, canvas, pos, color, size):
        if self._last is not None:
            pygame.draw.line(canvas, color, self._last, pos, size)
        self._last = pos

    def on_mouse_up(self, canvas, pos, color, size):
        self._last = None


# ---------------------------------------------------------------------------
# 3.1.2   Straight line tool with live preview
# ---------------------------------------------------------------------------
class LineTool(Tool):
    name = "line"

    def __init__(self):
        self.start = None
        self.current = None

    def on_mouse_down(self, canvas, pos, color, size):
        self.start = pos
        self.current = pos

    def on_mouse_drag(self, canvas, pos, color, size):
        self.current = pos  # preview only

    def on_mouse_up(self, canvas, pos, color, size):
        if self.start is not None:
            pygame.draw.line(canvas, color, self.start, pos, size)
        self.start = self.current = None

    def preview(self, overlay, color, size):
        if self.start and self.current:
            pygame.draw.line(overlay, color, self.start, self.current, size)


# ---------------------------------------------------------------------------
# Rectangle / Square / Circle / Triangles / Rhombus  (Practice 10-11)
# All respect the active brush size = stroke thickness.
# ---------------------------------------------------------------------------
class _ShapeBaseTool(Tool):
    """Click-drag rectangle bounding box, filled or outlined."""
    name = "shape"

    def __init__(self):
        self.start = None
        self.current = None

    def on_mouse_down(self, canvas, pos, color, size):
        self.start = pos
        self.current = pos

    def on_mouse_drag(self, canvas, pos, color, size):
        self.current = pos

    def on_mouse_up(self, canvas, pos, color, size):
        if self.start is not None:
            self._draw(canvas, self.start, pos, color, size)
        self.start = self.current = None

    def preview(self, overlay, color, size):
        if self.start and self.current:
            self._draw(overlay, self.start, self.current, color, size)

    # subclasses override this:
    def _draw(self, surf, p1, p2, color, size): ...


class RectTool(_ShapeBaseTool):
    name = "rect"
    def _draw(self, surf, p1, p2, color, size):
        rect = pygame.Rect(min(p1[0], p2[0]), min(p1[1], p2[1]),
                           abs(p2[0]-p1[0]), abs(p2[1]-p1[1]))
        pygame.draw.rect(surf, color, rect, size)


class SquareTool(_ShapeBaseTool):
    name = "square"
    def _draw(self, surf, p1, p2, color, size):
        side = max(abs(p2[0]-p1[0]), abs(p2[1]-p1[1]))
        x = p1[0] if p2[0] >= p1[0] else p1[0] - side
        y = p1[1] if p2[1] >= p1[1] else p1[1] - side
        pygame.draw.rect(surf, color, (x, y, side, side), size)


class CircleTool(_ShapeBaseTool):
    name = "circle"
    def _draw(self, surf, p1, p2, color, size):
        r = int(math.hypot(p2[0]-p1[0], p2[1]-p1[1]))
        if r > 0:
            pygame.draw.circle(surf, color, p1, r, size)


class RightTriangleTool(_ShapeBaseTool):
    name = "rtri"
    def _draw(self, surf, p1, p2, color, size):
        pts = [p1, (p2[0], p1[1]), p2]
        pygame.draw.polygon(surf, color, pts, size)


class EquilateralTriangleTool(_ShapeBaseTool):
    name = "etri"
    def _draw(self, surf, p1, p2, color, size):
        side = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
        h = side * math.sqrt(3) / 2
        cx, cy = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        pts = [
            (cx, cy - h/2),
            (cx - side/2, cy + h/2),
            (cx + side/2, cy + h/2),
        ]
        pygame.draw.polygon(surf, color, pts, size)


class RhombusTool(_ShapeBaseTool):
    name = "rhombus"
    def _draw(self, surf, p1, p2, color, size):
        cx, cy = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        w, h   = abs(p2[0]-p1[0])/2, abs(p2[1]-p1[1])/2
        pts = [(cx, cy-h), (cx+w, cy), (cx, cy+h), (cx-w, cy)]
        pygame.draw.polygon(surf, color, pts, size)


# ---------------------------------------------------------------------------
# Eraser — same as pencil but in canvas background colour
# ---------------------------------------------------------------------------
class EraserTool(PencilTool):
    name = "eraser"


# ---------------------------------------------------------------------------
# 3.3   Flood-fill
# ---------------------------------------------------------------------------
class FillTool(Tool):
    """
    Iterative 4-way flood fill using get_at / set_at.
    Stops at any pixel whose colour differs from the seed pixel.
    Surface is locked once for the whole operation for speed.
    """
    name = "fill"

    def on_mouse_down(self, canvas, pos, color, size):
        target = canvas.get_at(pos)
        replacement = pygame.Color(*color)
        if target == replacement:
            return

        w, h = canvas.get_size()
        canvas.lock()
        try:
            stack = deque([pos])
            while stack:
                x, y = stack.pop()
                if not (0 <= x < w and 0 <= y < h):
                    continue
                if canvas.get_at((x, y)) != target:
                    continue
                canvas.set_at((x, y), replacement)
                stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        finally:
            canvas.unlock()


# ---------------------------------------------------------------------------
# 3.5   Text tool  (paint.py drives the typing loop; this just paints)
# ---------------------------------------------------------------------------
class TextTool(Tool):
    name = "text"

    def __init__(self, font: pygame.font.Font):
        self.font = font

    def render(self, canvas, pos, color, text):
        surf = self.font.render(text, True, color)
        canvas.blit(surf, pos)


# ---------------------------------------------------------------------------
# Convenience: ordered map for the toolbar / keyboard shortcuts.
# ---------------------------------------------------------------------------
def make_tool_set(font):
    return {
        "P": PencilTool(),
        "L": LineTool(),
        "R": RectTool(),
        "S": SquareTool(),
        "C": CircleTool(),
        "T": RightTriangleTool(),
        "E": EquilateralTriangleTool(),
        "H": RhombusTool(),
        "F": FillTool(),
        "X": EraserTool(),
        "Y": TextTool(font),
    }
