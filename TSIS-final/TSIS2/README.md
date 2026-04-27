# TSIS 2 — Paint (Extended)

Pygame-only drawing app combining all Practice 10/11 shapes with the new TSIS-2 tools.

## Features

| Group | Tools / actions |
|---|---|
| Freehand | **Pencil** (P), **Eraser** (X) |
| Lines / shapes (with live preview) | **Line** (L), **Rect** (R), **Square** (S), **Circle** (C), **R-Triangle** (T), **E-Triangle** (E), **Rhombus** (H) |
| Fill | **Flood fill** (F) — iterative 4-way using `get_at` / `set_at` |
| Text | **Text tool** (Y) — click to set caret, type, **Enter** = commit, **Esc** = cancel |
| Brush size | `1` = 2 px, `2` = 5 px, `3` = 10 px (applies to every tool) |
| Save | **Ctrl+S** — file `paint_YYYYMMDD_HHMMSS.png`, never overwrites |
| Clear | **Ctrl+N** |

## Run

```bash
pip install pygame
python paint.py
```

## File layout

```
TSIS2/
├── paint.py    main loop, UI, toolbar, event dispatch
└── tools.py    Tool classes (Pencil, Line, Rect, …, Fill, Text)
```

The `Tool` base class defines `on_mouse_down / on_mouse_drag / on_mouse_up / preview`
so adding a new tool is just one new class — `paint.py` doesn't need to change.
