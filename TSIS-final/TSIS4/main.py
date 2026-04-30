"""
TSIS 4 — Snake (Extended)
=================================================================
Точка входа в игру. Связывает вместе:
    config.py — константы (размеры, цвета)
    db.py     — работа с PostgreSQL
    game.py   — игровая логика (змея, еда, уровни)

Файл настроек: settings.json (цвет змеи, сетка, звук).

Экраны: Главное меню, Игра, Game Over, Лидерборд, Настройки.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Callable

import pygame

# Импорты наших модулей
import db                    # работа с БД
import game as gamemod       # игровая логика (переименована в gamemod чтобы не конфликтовать)
from config import (
    SCREEN_W, SCREEN_H, CELL, GRID_W, GRID_H, HUD_H,
    COLOR, SETTINGS_FILE,
)

# Настройки по умолчанию (если settings.json ещё не создан)
DEFAULT_SETTINGS = {
    "snake_color": [94, 214, 159],     # зелёный (RGB)
    "grid":  True,                      # показывать сетку
    "sound": True,                      # звуки
}


# =========================================================================
# ЗАГРУЗКА И СОХРАНЕНИЕ НАСТРОЕК
# =========================================================================
def load_settings() -> dict:
    """Читает настройки из JSON-файла. Если файла нет — создаёт с дефолтами."""
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            # {**A, **B} — объединение словарей: дефолты + пользовательские
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except (json.JSONDecodeError, OSError):
        # Файл повреждён или нечитаем — возвращаем дефолты
        return dict(DEFAULT_SETTINGS)


def save_settings(s: dict):
    """Записывает настройки в JSON-файл."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# =========================================================================
# ИНИЦИАЛИЗАЦИЯ pygame
# =========================================================================
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("TSIS-4 Snake")
clock = pygame.time.Clock()

# Шрифты разных размеров
font_title = pygame.font.SysFont("dejavusansmono,arial", 38, bold=True)
font_med   = pygame.font.SysFont("dejavusans,arial", 22)
font_small = pygame.font.SysFont("dejavusansmono,arial", 16)

# =========================================================================
# СИНТЕЗ ЗВУКОВ (бипы при еде и смерти)
# Звуки генерируются на лету — не нужны wav-файлы
# =========================================================================
beep_food = beep_dead = None
try:
    pygame.mixer.init()
    import array, math

    def _tone(freq, ms, vol=0.3):
        """Генерирует синусоиду заданной частоты и длительности."""
        n = int(44100 * ms / 1000)             # количество сэмплов
        # array.array("h") — массив 16-битных целых (формат звука)
        # Для каждого сэмпла считаем sin(2π × freq × t)
        buf = array.array("h", (int(vol * 32767 * math.sin(2 * math.pi * freq * i / 44100))
                                for i in range(n)))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    beep_food = _tone(880, 90)                 # высокий "бип" при еде
    beep_dead = _tone(220, 350)                # низкий "бууу" при смерти
except Exception:
    # Если звук не работает (нет драйвера) — просто молчим
    pass


# =========================================================================
# КЛАСС КНОПКИ
# =========================================================================
class Button:
    """Прямоугольная кнопка с подсветкой при наведении."""
    def __init__(self, rect, label, on_click: Callable[[], None],
                 colour=COLOR["accent"], fg=(20, 20, 20)):
        self.rect    = pygame.Rect(rect)
        self.label   = label                    # строка ИЛИ функция (для динамического текста)
        self.on_click = on_click                # что делать при клике
        self.colour  = colour                   # цвет фона
        self.fg      = fg                        # цвет текста

    def text(self):
        """Возвращает текущий текст (вызывает функцию если label — функция)."""
        return self.label() if callable(self.label) else self.label

    def draw(self, surf, font):
        """Рисует кнопку с подсветкой при наведении."""
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        # При наведении делаем цвет ярче на 25
        c = tuple(min(255, x + (25 if hover else 0)) for x in self.colour)
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        t = font.render(self.text(), True, self.fg)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def handle(self, ev):
        """Обрабатывает клик мыши."""
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and \
                self.rect.collidepoint(ev.pos):
            self.on_click()


def centered(surf, font, text, y, color=COLOR["text"]):
    """Рисует текст по центру экрана на высоте y."""
    s = font.render(text, True, color)
    surf.blit(s, s.get_rect(center=(SCREEN_W // 2, y)))


# =========================================================================
# ВВОД ИМЕНИ ИГРОКА
# =========================================================================
def prompt_username(default="player") -> str:
    """
    Модальное окно для ввода имени.
    Enter — подтвердить, Esc — оставить дефолт, Backspace — удалить букву.
    """
    name = default
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                if ev.key == pygame.K_BACKSPACE:
                    name = name[:-1]                # удалить последнюю букву
                elif ev.key == pygame.K_ESCAPE:
                    return name.strip() or default
                elif ev.unicode.isprintable() and len(name) < 14:
                    # Любой печатный символ — добавить (макс 14 символов)
                    name += ev.unicode

        # Отрисовка
        screen.fill(COLOR["bg"])
        centered(screen, font_title, "Enter your name", 180, COLOR["accent"])
        # Рамка для текстового поля
        box = pygame.Rect(0, 0, 420, 60)
        box.center = (SCREEN_W // 2, 280)
        pygame.draw.rect(screen, COLOR["panel"], box, border_radius=10)
        pygame.draw.rect(screen, COLOR["accent"], box, 2, border_radius=10)
        # Имя с курсором ▌
        centered(screen, font_med, name + "▌", box.centery)
        centered(screen, font_med, "Enter to start", 380, COLOR["dim"])
        # Если БД недоступна — предупредить
        if not db.is_online():
            centered(screen, font_small,
                     "(offline mode — DB not reachable, scores not saved)",
                     SCREEN_H - 30, COLOR["danger"])
        pygame.display.flip()
        clock.tick(60)


# =========================================================================
# ОТРИСОВКА ИГРОВОГО ЭКРАНА (поле, змея, еда, HUD)
# =========================================================================
def draw_board(g: gamemod.Game, settings: dict, name: str, pb: int):
    """Рисует ВСЁ: HUD сверху, игровое поле, объекты, змею."""
    screen.fill(COLOR["bg"])

    # ----- ВЕРХНЯЯ ПАНЕЛЬ (HUD) -----
    pygame.draw.rect(screen, COLOR["panel"], (0, 0, SCREEN_W, HUD_H))
    screen.blit(font_med.render(f"Score {g.score}", True, COLOR["text"]), (12, 8))
    screen.blit(font_med.render(f"Level {g.level}", True, COLOR["text"]), (12, 38))
    screen.blit(font_small.render(f"player: {name}", True, COLOR["dim"]), (200, 12))
    screen.blit(font_small.render(f"best:   {pb}",    True, COLOR["dim"]), (200, 32))
    screen.blit(font_small.render(f"len: {len(g.snake)}", True, COLOR["dim"]), (200, 52))

    # Активный power-up + сколько секунд осталось
    if g.effect:
        remain = "" if g.effect == "shield" \
            else f"  {max(0, g.effect_until - pygame.time.get_ticks())//1000+1}s"
        screen.blit(font_small.render(f"power: {g.effect.upper()}{remain}",
                                      True, COLOR["accent"]), (380, 12))
    if g.shield_active:
        screen.blit(font_small.render("SHIELD ARMED", True, COLOR["accent"]), (380, 32))

    # Индикатор offline
    if not db.is_online():
        screen.blit(font_small.render("offline", True, COLOR["danger"]),
                    (SCREEN_W - 80, 12))

    # ----- ИГРОВОЕ ПОЛЕ -----
    play_rect = pygame.Rect(0, HUD_H, SCREEN_W, SCREEN_H - HUD_H)
    pygame.draw.rect(screen, COLOR["bg"], play_rect)

    # Сетка (если включена в настройках)
    if settings.get("grid", True):
        # Вертикальные линии
        for x in range(GRID_W + 1):
            pygame.draw.line(screen, COLOR["grid"],
                             (x * CELL, HUD_H),
                             (x * CELL, SCREEN_H), 1)
        # Горизонтальные линии
        for y in range(GRID_H + 1):
            pygame.draw.line(screen, COLOR["grid"],
                             (0,        HUD_H + y * CELL),
                             (SCREEN_W, HUD_H + y * CELL), 1)

    # Препятствия (серые квадраты)
    for ox, oy in g.obstacles:
        pygame.draw.rect(screen, COLOR["obstacle"],
                         (ox * CELL + 1, HUD_H + oy * CELL + 1, CELL - 2, CELL - 2),
                         border_radius=3)

    # Еда — разная в зависимости от типа
    for f in g.foods:
        # Считаем центр клетки в пикселях
        cx = f.pos[0] * CELL + CELL // 2
        cy = HUD_H + f.pos[1] * CELL + CELL // 2
        if f.kind == "poison":
            # Яд — фиолетовый кружок с белым крестиком
            color = COLOR["poison"]
            pygame.draw.circle(screen, color, (cx, cy), CELL // 2 - 3)
            pygame.draw.line(screen, (255, 255, 255),
                             (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (cx - 4, cy + 4), (cx + 4, cy - 4), 2)
        elif f.kind == "big":
            # Большая еда — больший кружок
            pygame.draw.circle(screen, COLOR["food_big"], (cx, cy), CELL // 2 - 2)
        else:
            # Обычная — маленький кружок
            pygame.draw.circle(screen, COLOR["food"],     (cx, cy), CELL // 2 - 4)

    # Power-up (квадрат с буквой внутри)
    if g.powerup:
        cx = g.powerup.pos[0] * CELL + CELL // 2
        cy = HUD_H + g.powerup.pos[1] * CELL + CELL // 2
        col = COLOR[f"powerup_{g.powerup.kind}"]
        pygame.draw.rect(screen, col,
                         (cx - CELL//2 + 2, cy - CELL//2 + 2, CELL - 4, CELL - 4),
                         border_radius=6)
        # Буква-обозначение типа
        letter = {"speed": "S", "slow": "L", "shield": "★"}[g.powerup.kind]
        s = font_small.render(letter, True, (20, 20, 20))
        screen.blit(s, s.get_rect(center=(cx, cy)))

    # Змея — голова чуть ярче чем тело
    snake_color = tuple(settings.get("snake_color", [94, 214, 159]))
    head_color  = tuple(min(255, c + 25) for c in snake_color)
    for i, (sx, sy) in enumerate(g.snake):
        c = head_color if i == 0 else snake_color   # i==0 — голова
        pygame.draw.rect(screen, c,
                         (sx * CELL + 1, HUD_H + sy * CELL + 1, CELL - 2, CELL - 2),
                         border_radius=4)

    # Аура щита вокруг головы (если активен shield)
    if g.shield_active:
        hx, hy = g.snake[0]
        pygame.draw.rect(screen, COLOR["shield_aura"],
                         (hx * CELL - 1, HUD_H + hy * CELL - 1, CELL + 2, CELL + 2),
                         2, border_radius=6)


# =========================================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================================
def main_menu():
    """Возвращает действие: 'play'/'board'/'settings'/'quit'."""
    state = {"a": None}      # словарь чтобы изменять из lambda
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
        # Предупреждение если БД оффлайн
        if not db.is_online():
            centered(screen, font_small,
                     "DB offline — playing in local mode",
                     SCREEN_H - 24, COLOR["danger"])
        pygame.display.flip()
        clock.tick(60)
    return state["a"]


# =========================================================================
# ЭКРАН НАСТРОЕК
# =========================================================================
def settings_screen(s: dict):
    """Меняет цвет змеи, включает/выключает сетку и звук."""
    # Палитра доступных цветов змеи
    palette = [
        ("Green",  [94, 214, 159]),
        ("Blue",   [80, 160, 230]),
        ("Red",    [220, 90, 90]),
        ("Yellow", [240, 220, 100]),
        ("Pink",   [255, 130, 200]),
    ]
    state = {"done": False}

    def cycle_color():
        """Переключает цвет змеи на следующий из палитры."""
        cur = s.get("snake_color", palette[0][1])
        # Находим индекс текущего цвета в палитре
        idx = next((i for i,(_,c) in enumerate(palette) if c == cur), -1)
        # Берём следующий по кругу (% — остаток от деления)
        s["snake_color"] = palette[(idx + 1) % len(palette)][1]

    def color_label():
        """Возвращает текст кнопки с названием текущего цвета."""
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
    save_settings(s)        # сохраняем при выходе


# =========================================================================
# ЭКРАН ЛИДЕРБОРДА (топ-10 из БД)
# =========================================================================
def leaderboard_screen():
    """Загружает топ-10 из PostgreSQL и показывает таблицу."""
    rows = db.top10()       # SQL-запрос с JOIN players + game_sessions
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
            # Если нет результатов — разные сообщения для онлайн/оффлайн
            centered(screen, font_med,
                     "(no scores yet)" if db.is_online() else "(DB offline)",
                     220, COLOR["dim"])
        else:
            # Заголовок таблицы (выравнивание: <=влево, >=вправо)
            header = f"{'#':<3} {'name':<14} {'score':>6} {'lvl':>4}  date"
            screen.blit(font_small.render(header, True, COLOR["dim"]), (40, 130))
            y = 160
            # enumerate(rows, 1) — нумерация с 1
            for i, r in enumerate(rows, 1):
                # Форматируем дату для отображения
                d = r["played_at"].strftime("%Y-%m-%d %H:%M")
                line = (f"{i:<3} {r['username']:<14} "
                        f"{r['score']:>6} {r['level_reached']:>4}  {d}")
                screen.blit(font_small.render(line, True, COLOR["text"]), (40, y))
                y += 26
        back.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)


# =========================================================================
# ОСНОВНОЙ ИГРОВОЙ ЦИКЛ
# =========================================================================
def play(name: str, settings: dict):
    """Один заезд. Возвращает 'retry' или 'menu'."""
    g  = gamemod.Game()                     # новая игра
    pb = db.personal_best(name)             # личный рекорд из БД

    while True:
        # Обработка нажатий клавиш
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP,    pygame.K_w): g.turn(gamemod.DIR_UP)
                if ev.key in (pygame.K_DOWN,  pygame.K_s): g.turn(gamemod.DIR_DOWN)
                if ev.key in (pygame.K_LEFT,  pygame.K_a): g.turn(gamemod.DIR_LEFT)
                if ev.key in (pygame.K_RIGHT, pygame.K_d): g.turn(gamemod.DIR_RIGHT)
                if ev.key == pygame.K_ESCAPE:
                    return "menu"

        prev_score = g.score    # запоминаем счёт до шага
        g.step()                # ОДИН шаг змеи (вся логика в game.py)

        # Звуковые эффекты
        if settings.get("sound", True):
            # Если съели еду — счёт вырос → бип
            if g.score > prev_score and beep_food: beep_food.play()
            # Если умерли — низкий тон
            if g.over and beep_dead:               beep_dead.play()

        # Отрисовка кадра
        draw_board(g, settings, name, pb)
        pygame.display.flip()
        clock.tick(g.fps)        # FPS зависит от уровня и power-ups (свойство в game.py)

        # Game over → переход на финальный экран
        if g.over:
            return game_over_screen(g, name, pb)


# =========================================================================
# ЭКРАН GAME OVER
# =========================================================================
def game_over_screen(g: gamemod.Game, name: str, pb: int):
    """Сохраняет результат в БД и показывает кнопки Retry/Menu."""
    # save_session возвращает True/False (успех записи в БД)
    saved = db.save_session(name, g.score, g.level)
    new_pb = max(pb, g.score)        # новый личный рекорд

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
        # Если БД оффлайн — предупредить что результат не сохранён
        if not saved:
            centered(screen, font_small, "(score not saved — DB offline)",
                     310, COLOR["danger"])
        for b in btns: b.draw(screen, font_med)
        pygame.display.flip()
        clock.tick(60)
    return state["a"]


# =========================================================================
# ВЕРХНИЙ УРОВЕНЬ — ГЛАВНЫЙ ЦИКЛ ПРОГРАММЫ
# =========================================================================
def run():
    """
    Входная точка программы.
    1. Инициализация БД (создание таблиц если их нет)
    2. Загрузка настроек
    3. Цикл: меню → выбранный экран → меню
    """
    db.init_schema()                # CREATE TABLE IF NOT EXISTS
    settings = load_settings()
    name = None                     # имя игрока (запросится при первой игре)

    while True:
        action = main_menu()
        if action == "play":
            if not name:
                name = prompt_username()
            # Цикл повторных попыток (если в Game Over жмут Retry)
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


# Запуск только если файл выполнен напрямую
if __name__ == "__main__":
    run()