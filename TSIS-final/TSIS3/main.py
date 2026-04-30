"""
TSIS 3 — Racer (Extended)
=================================================================
Точка входа в игру. Связывает вместе:
    persistence.py — settings.json / leaderboard.json (сохранения)
    racer.py       — игровая логика (машина, объекты, столкновения)
    ui.py          — кнопки, ввод имени, цвета

Экраны (требование 3.5):
    Главное меню, Настройки, Лидерборд, Game Over.
"""
from __future__ import annotations

import sys
import pygame

# Импорты наших модулей
import persistence
import racer
from ui import (
    Button, draw_centered, prompt_username,
    BG, PANEL, ACCENT, TEXT, DIM, DANGER,
)

# === ИНИЦИАЛИЗАЦИЯ pygame ================================================
pygame.init()
SCREEN_W, SCREEN_H = racer.SCREEN_W, racer.SCREEN_H   # 540×720
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("TSIS-3 Racer")
clock = pygame.time.Clock()                            # для контроля FPS

# Шрифты для разных размеров текста
font_big   = pygame.font.SysFont("dejavusansmono,arial", 36, bold=True)
font_med   = pygame.font.SysFont("dejavusans,arial", 22)
font_small = pygame.font.SysFont("dejavusans,arial", 16)


# =========================================================================
# ОТРИСОВКА ДОРОГИ И HUD (интерфейс игры)
# =========================================================================
def draw_road(surf, dash_offset: int):
    """Рисует асфальт, обочины и пунктир между полосами."""
    surf.fill((58, 60, 64))                           # серый асфальт
    # Зелёная трава по бокам
    pygame.draw.rect(surf, (38, 78, 50), (0, 0, racer.ROAD_LEFT, SCREEN_H))
    pygame.draw.rect(surf, (38, 78, 50),
                     (racer.ROAD_RIGHT, 0, SCREEN_W - racer.ROAD_RIGHT, SCREEN_H))
    # Белые полосы по краям дороги
    pygame.draw.rect(surf, (245, 245, 245), (racer.ROAD_LEFT - 3, 0, 3, SCREEN_H))
    pygame.draw.rect(surf, (245, 245, 245), (racer.ROAD_RIGHT,    0, 3, SCREEN_H))
    # Пунктир между полосами — dash_offset двигает его вниз для иллюзии движения
    for i in range(1, racer.LANES):
        x = racer.ROAD_LEFT + racer.LANE_W * i
        for y in range(-40 + dash_offset, SCREEN_H, 40):
            pygame.draw.rect(surf, (235, 235, 235), (x - 2, y, 4, 22))


def draw_car(surf, rect: pygame.Rect, color):
    """Рисует машину: корпус, лобовое стекло, 4 колеса."""
    pygame.draw.rect(surf, color, rect, border_radius=8)        # корпус
    # Лобовое стекло — голубой прямоугольник сверху
    ws = rect.inflate(-12, -50).move(0, -10)
    ws.height = 24
    ws.centerx = rect.centerx
    ws.centery = rect.centery - 12
    pygame.draw.rect(surf, (180, 220, 255), ws, border_radius=4)
    # 4 колеса — чёрные прямоугольники по углам
    for dx in (-2, rect.width - 6):
        for dy in (8, rect.height - 22):
            pygame.draw.rect(surf, (20, 20, 20),
                             (rect.x + dx, rect.y + dy, 6, 14), border_radius=2)


def draw_obstacle(surf, e):
    """Рисует препятствие в зависимости от типа."""
    r = e.rect
    if e.kind == "oil":
        # Масло — чёрный овал
        pygame.draw.ellipse(surf, (20, 20, 20), r)
    elif e.kind == "pothole":
        # Яма — двойной овал (тёмный + светлый внутри)
        pygame.draw.ellipse(surf, (15, 15, 15), r)
        pygame.draw.ellipse(surf, (60, 60, 60), r.inflate(-12, -30))
    elif e.kind == "barrier":
        # Барьер — жёлтый прямоугольник с чёрной обводкой
        pygame.draw.rect(surf, (240, 200, 50), r, border_radius=6)
        pygame.draw.rect(surf, (40, 40, 40), r, 3, border_radius=6)
    elif e.kind == "bump":
        # Лежачий полицейский — белый с чёрными полосами
        pygame.draw.rect(surf, (220, 220, 220), r, border_radius=4)
        for i in range(3):
            pygame.draw.rect(surf, (40, 40, 40),
                             (r.x + 4, r.y + 8 + i * 22, r.w - 8, 6))


def draw_coin(surf, r):
    """Рисует монету — золотой кружок с обводкой."""
    pygame.draw.circle(surf, (255, 215, 0), r.center, 14)
    pygame.draw.circle(surf, (200, 160, 0), r.center, 14, 2)


def draw_powerup(surf, e):
    """Рисует бонус с буквой внутри (N=nitro, S=shield, R=repair)."""
    r = e.rect
    pygame.draw.rect(surf, e.color, r, border_radius=10)
    label = {"nitro": "N", "shield": "S", "repair": "R"}[e.kind]
    s = font_med.render(label, True, (20, 20, 20))
    surf.blit(s, s.get_rect(center=r.center))


def draw_hud(surf, game: racer.Racer):
    """Рисует верхний интерфейс: счёт, монеты, скорость, прогресс-бар."""
    pygame.draw.rect(surf, (0, 0, 0, 120), (0, 0, SCREEN_W, 60))
    surf.blit(font_small.render(f"score {game.score}",        True, TEXT),  (10, 8))
    surf.blit(font_small.render(f"coins {game.coins_count}",  True, TEXT),  (10, 28))
    surf.blit(font_small.render(f"speed {game.speed}",        True, TEXT),  (140, 8))

    # Прогресс-бар до финиша
    pct = min(1.0, game.distance / racer.FINISH_DISTANCE)
    pygame.draw.rect(surf, (50, 50, 50),  (260, 14, 200, 14), border_radius=4)
    pygame.draw.rect(surf, ACCENT,        (260, 14, int(200 * pct), 14), border_radius=4)
    surf.blit(font_small.render(f"{int(pct*100)}%", True, TEXT), (470, 10))

    # Активный бонус и сколько осталось
    if game.active_power:
        remain = max(0, game.power_until - pygame.time.get_ticks()) // 1000
        label = f"{game.active_power.upper()}"
        if game.active_power == "nitro":
            label += f"  {remain}s"
        elif game.active_power == "shield":
            label += "  (until hit)"
        surf.blit(font_small.render(label, True, ACCENT), (140, 28))

    # Сообщение о событии (например "SHIELD ABSORBED HIT")
    if game.last_event and pygame.time.get_ticks() < game.last_event_until:
        s = font_med.render(game.last_event, True, ACCENT)
        surf.blit(s, s.get_rect(center=(SCREEN_W // 2, 100)))


# =========================================================================
# ЭКРАНЫ (МЕНЮ, НАСТРОЙКИ, ЛИДЕРБОРД, GAME OVER)
# =========================================================================
def main_menu():
    """Главное меню. Возвращает действие: 'play'/'board'/'settings'/'quit'."""
    state = {"action": None}     # словарь — чтобы изменять из вложенных функций

    def go(action): state["action"] = action

    # Создаём 4 кнопки. lambda: go(...) — функция-обработчик клика
    buttons = [
        Button((SCREEN_W//2-110, 280, 220, 50), "Play",        lambda: go("play")),
        Button((SCREEN_W//2-110, 345, 220, 50), "Leaderboard", lambda: go("board"), colour=(120,150,255)),
        Button((SCREEN_W//2-110, 410, 220, 50), "Settings",    lambda: go("settings"), colour=(180,180,180)),
        Button((SCREEN_W//2-110, 475, 220, 50), "Quit",        lambda: go("quit"),     colour=DANGER, fg=(255,255,255)),
    ]

    # Цикл меню — крутится пока не выбрали действие
    while state["action"] is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                state["action"] = "quit"
            for b in buttons:
                b.handle(ev)        # каждая кнопка проверяет своё нажатие

        # Отрисовка
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
    """Экран настроек: звук, цвет машины, сложность."""
    color_keys = list(racer.CAR_COLORS.keys())          # red, blue, green...
    diff_keys  = ["easy", "normal", "hard"]
    state = {"done": False}

    # Функции, которые меняют настройки по кругу
    def cycle_color():
        i = color_keys.index(settings["car_color"])
        settings["car_color"] = color_keys[(i + 1) % len(color_keys)]

    def cycle_diff():
        i = diff_keys.index(settings["difficulty"])
        settings["difficulty"] = diff_keys[(i + 1) % len(diff_keys)]

    def toggle_sound():
        settings["sound"] = not settings["sound"]

    def save_back():
        persistence.save_settings(settings)             # сохраняем в JSON
        state["done"] = True

    # label — функция (lambda), потому что текст меняется при кликах
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
            # Обновляем динамический текст кнопки
            if callable(b.label):
                b.label_text = b.label()
            else:
                b.label_text = b.label
            # Рисуем с подсветкой при наведении
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
    """Экран таблицы рекордов. Загружает из JSON-файла."""
    board = persistence.load_leaderboard()      # топ-10 из leaderboard.json
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
            # Заголовок таблицы
            y = 130
            screen.blit(font_small.render(
                f"{'#':<3} {'name':<14} {'score':>6} {'dist':>6} {'coins':>6} date",
                True, DIM), (40, y))
            y += 26
            # enumerate(board, 1) — нумерация с 1, а не с 0
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
    """
    Экран после гибели или финиша.
    Сохраняет результат в лидерборд и показывает кнопки Retry/Menu.
    """
    persistence.add_score(name, game.score, game.distance, game.coins_count)
    state = {"action": None}

    btns = [
        Button((SCREEN_W//2-140, 480, 130, 48), "Retry",
               lambda: state.update(action="retry")),
        Button((SCREEN_W//2+10, 480, 130, 48), "Main Menu",
               lambda: state.update(action="menu"), colour=(180, 180, 180)),
    ]

    # Заголовок зависит от исхода
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


# =========================================================================
# ОСНОВНОЙ ИГРОВОЙ ЦИКЛ
# =========================================================================
def play(name: str, settings: dict):
    """Один заезд. Возвращает 'retry' или 'menu' после game over."""
    game = racer.Racer(settings)        # создаём новую игру

    while True:
        dt = clock.tick(60)              # 60 FPS, dt = миллисекунды от прошлого кадра

        # Обработка событий (управление)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_LEFT,  pygame.K_a): game.move_left()
                if ev.key in (pygame.K_RIGHT, pygame.K_d): game.move_right()
                if ev.key == pygame.K_ESCAPE:
                    return "menu"

        game.update(dt)                  # игровая логика — вся в racer.py

        # Отрисовка всех объектов
        draw_road(screen, game.lane_dash_offset)
        for o in game.obstacles: draw_obstacle(screen, o)
        for c in game.coins:     draw_coin(screen, c.rect)
        for p in game.powerups:  draw_powerup(screen, p)
        for t in game.traffic:   draw_car(screen, t.rect, t.color)

        # Машина игрока
        pr = pygame.Rect(racer.LANE_X[game.player_lane] - racer.CAR_W/2,
                         game.player_y, racer.CAR_W, racer.CAR_H)
        draw_car(screen, pr, game.player_color)
        # Зелёная аура щита если активен
        if game.shield:
            pygame.draw.rect(screen, ACCENT, pr.inflate(10, 10), 3, border_radius=10)

        draw_hud(screen, game)
        pygame.display.flip()

        # Конец игры — game over или финиш
        if game.over or game.finished:
            return game_over_screen(game, name)


# =========================================================================
# ВЕРХНИЙ УРОВЕНЬ — ГЛАВНЫЙ ЦИКЛ ПРОГРАММЫ
# =========================================================================
def run():
    """
    Главный цикл: меню → выбор → игра/настройки/лидерборд → меню.
    """
    settings = persistence.load_settings()    # читаем настройки из JSON
    name     = None                            # имя игрока (запросится при первой игре)

    while True:
        action = main_menu()
        if action == "play":
            # Если имя ещё не введено — спросить через модальное окно
            if not name:
                name = prompt_username(screen, font_big, font_med)
            result = play(name, settings)
            if result == "retry":
                # Цикл повторных попыток
                while play(name, settings) == "retry":
                    pass
        elif action == "board":
            leaderboard_screen()
        elif action == "settings":
            settings_screen(settings)
        else:  # quit
            pygame.quit()
            return


# Запуск только если файл выполнен напрямую
if __name__ == "__main__":
    run()