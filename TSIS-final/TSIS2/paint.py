"""
TSIS 2 — Paint (Extended)
=================================================================
Графический редактор на pygame.

Инструменты:
    Pencil         — свободное рисование
    Line           — линия с предпросмотром
    Rect/Square    — прямоугольник/квадрат
    Circle         — круг от центра
    R-Triangle     — прямоугольный треугольник
    E-Triangle     — равносторонний треугольник
    Rhombus        — ромб
    Eraser         — ластик (карандаш цветом фона)
    Flood-fill     — заливка (как ведёрко)
    Text           — печатаешь текст с клавиатуры

Размер кисти : 1=малый(2px) 2=средний(5px) 3=большой(10px)
Сохранение   : Ctrl+S   — имя файла с временем, не перезапишется
Очистить     : Ctrl+N
Выход        : Esc или закрыть окно
"""
from __future__ import annotations

# === ИМПОРТЫ =============================================================
import datetime as dt        # для имени файла с timestamp
import sys                   # для выхода из программы
import pygame                # игровая библиотека (тут используем для графики)

# Импортируем инструменты из tools.py
from tools import make_tool_set, TextTool


# =========================================================================
# РАЗМЕРЫ И ЦВЕТА
# =========================================================================
WIN_W, WIN_H = 1100, 700                 # размер окна
TOOLBAR_W    = 180                       # ширина левой панели с кнопками
# Прямоугольник, в котором происходит рисование (правее тулбара)
CANVAS_RECT  = pygame.Rect(TOOLBAR_W, 0, WIN_W - TOOLBAR_W, WIN_H)
BG_COLOR     = (255, 255, 255)           # белый — цвет холста и ластика
TOOLBAR_BG   = (38, 41, 48)              # тёмный фон тулбара
TEXT_COLOR   = (230, 230, 230)           # цвет надписей
ACCENT       = (94, 214, 159)            # зелёный для подсветки активной кнопки

# Палитра — 12 цветов в формате (R, G, B)
PALETTE = [
    (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 200, 0),
    (0, 120, 255), (255, 200, 0), (200, 0, 200), (0, 200, 200),
    (255, 128, 0), (128, 64, 0), (180, 180, 180), (60, 60, 60),
]

# Соответствие "клавиша → размер кисти в пикселях"
SIZES = {pygame.K_1: 2, pygame.K_2: 5, pygame.K_3: 10}
DEFAULT_SIZE = 5

# Список инструментов: (буква-горячая клавиша, название для тулбара)
TOOL_KEYS = [
    ("P", "Pencil"), ("L", "Line"),
    ("R", "Rect"),   ("S", "Square"),
    ("C", "Circle"), ("T", "R-Tri"),
    ("E", "E-Tri"),  ("H", "Rhomb"),
    ("F", "Fill"),   ("X", "Eraser"),
    ("Y", "Text"),
]


# =========================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================================
def in_canvas(pos):
    """Проверяет, попала ли мышь в область холста (а не в тулбар)."""
    return CANVAS_RECT.collidepoint(pos)


def to_canvas_coords(pos):
    """
    Преобразует координаты окна в координаты холста.
    В окне (0,0) — верхний левый угол окна, а холст начинается с x=180.
    Поэтому вычитаем смещение тулбара.
    """
    return pos[0] - CANVAS_RECT.x, pos[1] - CANVAS_RECT.y


def save_canvas(canvas):
    """
    Сохраняет холст в PNG-файл с именем paint_ГГГГММДД_ЧЧММСС.png
    Каждое сохранение даёт уникальное имя — ничего не перезаписывается.
    """
    fname = f"paint_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
    pygame.image.save(canvas, fname)     # встроенная функция pygame
    print(f"saved → {fname}")
    return fname


# =========================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =========================================================================
def main():
    pygame.init()                         # инициализация pygame
    pygame.display.set_caption("TSIS-2 Paint")
    screen = pygame.display.set_mode((WIN_W, WIN_H))   # создаём окно
    clock  = pygame.time.Clock()          # для контроля FPS

    # Шрифты для тулбара и текстового инструмента
    ui_font   = pygame.font.SysFont("dejavusansmono,arial", 14)
    text_font = pygame.font.SysFont("dejavusans,arial", 22)

    # Создаём холст — отдельную поверхность только для рисования
    # На неё рисуем; на screen её только копируем
    canvas = pygame.Surface(CANVAS_RECT.size)
    canvas.fill(BG_COLOR)                 # заливаем белым

    # Создаём словарь инструментов (буква → объект инструмента)
    tools  = make_tool_set(text_font)
    active_key = "P"                      # стартовый инструмент — карандаш
    color = (0, 0, 0)                     # стартовый цвет — чёрный
    size  = DEFAULT_SIZE                  # стартовый размер — 5px

    drawing = False                       # True пока зажата мышь
    save_flash = 0                        # время последнего сохранения (для тоста)

    # Состояние текстового инструмента
    typing       = False                  # True если сейчас печатаем
    typing_pos   = (0, 0)                 # где будет текст
    typing_text  = ""                     # что напечатали

    # ===== ГЛАВНЫЙ ЦИКЛ — выполняется каждый кадр (бесконечно) =====
    while True:
        # ----- ОБРАБОТКА СОБЫТИЙ (клавиатура, мышь) -----
        for ev in pygame.event.get():
            # Закрытие окна
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ============== КЛАВИАТУРА ==============
            if ev.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()    # зажаты ли Ctrl/Shift/Alt

                # Если печатаем текст — клавиши идут в текст
                if typing:
                    if ev.key == pygame.K_RETURN:
                        # Enter — закончили печатать, рисуем текст на холсте
                        tools["Y"].render(canvas, typing_pos, color, typing_text)
                        typing, typing_text = False, ""
                    elif ev.key == pygame.K_ESCAPE:
                        # Esc — отмена ввода
                        typing, typing_text = False, ""
                    elif ev.key == pygame.K_BACKSPACE:
                        # Backspace — удалить последний символ
                        typing_text = typing_text[:-1]
                    elif ev.unicode and ev.unicode.isprintable():
                        # Любой печатный символ — добавить к строке
                        typing_text += ev.unicode
                    continue   # не обрабатываем как горячую клавишу

                # Ctrl+S — сохранить
                if (mods & pygame.KMOD_CTRL) and ev.key == pygame.K_s:
                    save_canvas(canvas)
                    save_flash = pygame.time.get_ticks()
                    continue
                # Ctrl+N — очистить холст
                if (mods & pygame.KMOD_CTRL) and ev.key == pygame.K_n:
                    canvas.fill(BG_COLOR); continue

                # 1/2/3 — размеры кисти
                if ev.key in SIZES:
                    size = SIZES[ev.key]; continue

                # Буквы P/L/R/S/C/T/E/H/F/X/Y — выбор инструмента
                key_letter = pygame.key.name(ev.key).upper()
                if key_letter in tools:
                    active_key = key_letter
                    drawing = False         # отменить незаконченную фигуру
                    continue

                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

            # ============== МЫШКА ==============
            # Нажали левую кнопку мыши
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                # Клик по тулбару?
                if ev.pos[0] < TOOLBAR_W:
                    handle_toolbar_click(ev.pos, locals_dict := locals())
                    # Обновляем переменные после клика по тулбару
                    active_key = locals_dict["active_key"]
                    color      = locals_dict["color"]
                    size       = locals_dict["size"]
                    continue

                # Клик по холсту
                if in_canvas(ev.pos):
                    cpos = to_canvas_coords(ev.pos)

                    # Текстовый инструмент — клик ставит курсор
                    if active_key == "Y":
                        typing = True
                        typing_pos = cpos
                        typing_text = ""
                        continue

                    drawing = True
                    # Для ластика используем цвет фона, для остальных — выбранный цвет
                    erase_color = BG_COLOR if active_key == "X" else color
                    tools[active_key].on_mouse_down(canvas, cpos, erase_color, size)

            # Двигаем мышь с зажатой кнопкой
            elif ev.type == pygame.MOUSEMOTION and drawing:
                if in_canvas(ev.pos):
                    cpos = to_canvas_coords(ev.pos)
                    erase_color = BG_COLOR if active_key == "X" else color
                    tools[active_key].on_mouse_drag(canvas, cpos, erase_color, size)

            # Отпустили кнопку
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and drawing:
                cpos = to_canvas_coords(ev.pos)
                erase_color = BG_COLOR if active_key == "X" else color
                tools[active_key].on_mouse_up(canvas, cpos, erase_color, size)
                drawing = False

        # ----- ОТРИСОВКА -----
        screen.fill(TOOLBAR_BG)                      # фон окна — тёмный
        draw_toolbar(screen, ui_font, active_key, color, size)   # тулбар
        screen.blit(canvas, CANVAS_RECT.topleft)     # копируем холст на экран

        # Предпросмотр фигур (линия, прямоугольник и т.д.)
        # Рисуется на отдельной прозрачной поверхности — не на холсте!
        # Иначе на холсте остался бы хвост из всех промежуточных фигур
        overlay = pygame.Surface(CANVAS_RECT.size, pygame.SRCALPHA)
        if drawing and not isinstance(tools[active_key], TextTool):
            tools[active_key].preview(overlay, color, size)
        screen.blit(overlay, CANVAS_RECT.topleft)

        # Курсор для текстового инструмента (мигающий ▌)
        if typing:
            caret = text_font.render(typing_text + "▌", True, color)
            screen.blit(caret, (CANVAS_RECT.x + typing_pos[0],
                                CANVAS_RECT.y + typing_pos[1]))

        # Уведомление "✓ saved" — показывается 1.5 секунды
        if save_flash and pygame.time.get_ticks() - save_flash < 1500:
            toast = ui_font.render("✓ saved", True, ACCENT)
            screen.blit(toast, (WIN_W - 80, 10))

        pygame.display.flip()    # показать кадр на экране
        clock.tick(120)          # ограничение FPS — 120 кадров в секунду


# =========================================================================
# ОТРИСОВКА ТУЛБАРА И ОБРАБОТКА КЛИКОВ ПО НЕМУ
# =========================================================================
def draw_toolbar(screen, font, active_key, color, size):
    """Рисует левую панель: список инструментов, размеры, палитра."""
    pygame.draw.rect(screen, TOOLBAR_BG, (0, 0, TOOLBAR_W, WIN_H))
    y = 10

    # --- секция инструментов ---
    label(screen, font, "TOOLS", 10, y); y += 22
    for i, (k, name) in enumerate(TOOL_KEYS):
        rect = pygame.Rect(10, y, TOOLBAR_W - 20, 26)
        active = (k == active_key)        # активный инструмент подсвечен
        # Зелёная подсветка для активного, серая для остальных
        pygame.draw.rect(screen, ACCENT if active else (60, 64, 72), rect, border_radius=6)
        screen.blit(font.render(f"[{k}] {name}", True,
                                (20, 20, 20) if active else TEXT_COLOR),
                    (rect.x + 8, rect.y + 6))
        y += 30

    # --- секция размеров ---
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

    # --- секция палитры ---
    y += 8
    label(screen, font, "COLOUR", 10, y); y += 22
    sw = 28                                # размер квадратика цвета
    for i, c in enumerate(PALETTE):
        col = i % 4                        # 4 цвета в ряд
        row = i // 4
        rect = pygame.Rect(10 + col * (sw + 6), y + row * (sw + 6), sw, sw)
        pygame.draw.rect(screen, c, rect, border_radius=4)
        if c == color:                     # активный цвет — обведён
            pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=4)
    y += ((len(PALETTE) + 3) // 4) * (sw + 6) + 6

    # --- подсказки внизу ---
    label(screen, font, "Ctrl+S  save", 10, WIN_H - 60)
    label(screen, font, "Ctrl+N  clear", 10, WIN_H - 40)
    label(screen, font, "Esc     quit",  10, WIN_H - 20)


def label(screen, font, text, x, y):
    """Просто рисует текст на экране."""
    screen.blit(font.render(text, True, TEXT_COLOR), (x, y))


def handle_toolbar_click(pos, frame):
    """
    Обрабатывает клик по тулбару.
    Изменяет переменные active_key / color / size в главной функции.
    """
    x, y = pos

    # --- кнопки инструментов ---
    yy = 10 + 22
    for k, _ in TOOL_KEYS:
        if pygame.Rect(10, yy, TOOLBAR_W - 20, 26).collidepoint(pos):
            frame["active_key"] = k
            return
        yy += 30

    # --- кнопки размеров ---
    yy += 6 + 22
    for px in (2, 5, 10):
        if pygame.Rect(10, yy, TOOLBAR_W - 20, 22).collidepoint(pos):
            frame["size"] = px
            return
        yy += 26

    # --- палитра цветов ---
    yy += 8 + 22
    sw = 28
    for i, c in enumerate(PALETTE):
        col = i % 4
        row = i // 4
        r = pygame.Rect(10 + col * (sw + 6), yy + row * (sw + 6), sw, sw)
        if r.collidepoint(pos):
            frame["color"] = c
            return


# Этот блок выполняется только если запустить файл напрямую
if __name__ == "__main__":
    main()