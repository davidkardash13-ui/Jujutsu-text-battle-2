# -*- coding: utf-8 -*-
"""
Jujutsu Text Battle 2 — графическая версия (Tkinter).

Возможности:
  * Открытие кейсов (гача) с анимацией прокрутки, вспышкой редкости и пульсацией.
  * Коллекция персонажей, выбор активного бойца, продажа дубликатов.
  * Пошаговые сражения с анимированными полосами HP, вспышками урона
    и всплывающими цифрами урона.
  * Промокоды (кнопка в меню) — монеты, кейсы и редкие персонажи.
  * Большой список разнообразных врагов из вселенной JJK.
  * Валюта (проклятые монеты), сохранение/загрузка прогресса.
  * Анимированный фон с «частицами проклятой энергии» и градиентами.

Запуск:  python game_gui.py
(Tkinter входит в стандартную поставку Python — ставить ничего не нужно.)
"""

import os
import json
import random
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import characters as db


SAVE_FILE = "savegame.json"
CASE_PRICE = 100

# ----------------------- Палитра тёмной темы -----------------------
BG = "#0d0b16"
BG2 = "#15111f"
PANEL = "#1b1730"
PANEL_LIGHT = "#2a2444"
ACCENT = "#b06bff"
ACCENT_DARK = "#6c2bd9"
ACCENT2 = "#3bd6ff"
TEXT = "#f0edf8"
MUTED = "#9b93bd"
GOLD = "#ffcf5c"
GREEN = "#42d67f"
RED = "#ff5d72"


# --------------------------------------------------------------------------
#                         ЛОГИКА (без интерфейса)
# --------------------------------------------------------------------------

def new_player(name):
    return {
        "name": name,
        "coins": 300,
        "collection": {},
        "battles_won": 0,
        "cases_opened": 0,
        "active": None,
        "redeemed_codes": [],
    }


def normalize_player(player):
    """Дополняет старые сохранения недостающими полями."""
    defaults = new_player(player.get("name", "Маг"))
    for key, value in defaults.items():
        player.setdefault(key, value)
    return player


def add_character(player, char_name):
    is_new = char_name not in player["collection"]
    player["collection"][char_name] = player["collection"].get(char_name, 0) + 1
    if player["active"] is None:
        player["active"] = char_name
    return is_new


def save_game(player):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(player, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def load_game():
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return normalize_player(json.load(f))
    except (OSError, json.JSONDecodeError):
        return None


def roll_rank():
    ranks = list(db.RANK_DROP_RATES.keys())
    weights = list(db.RANK_DROP_RATES.values())
    return random.choices(ranks, weights=weights, k=1)[0]


def roll_character():
    return random.choice(db.characters_by_rank(roll_rank()))


# ----------------------------- ПРОМОКОДЫ -----------------------------
# Каждый код можно активировать один раз. Награды: coins / cases / char.
PROMO_CODES = {
    "JJK2":       {"coins": 500, "msg": "Бонус за запуск Jujutsu Text Battle 2!"},
    "GOJO":       {"coins": 300, "cases": 1, "msg": "Сильнейший маг с тобой!"},
    "DOMAIN":     {"coins": 1000, "msg": "Расширение Территории активировано!"},
    "BLACKFLASH": {"coins": 250, "cases": 1, "msg": "Чёрная Вспышка 2.5%!"},
    "REVERSE":    {"coins": 400, "msg": "Обратная проклятая техника!"},
    "SHIBUYA":    {"coins": 750, "cases": 2, "msg": "Инцидент в Сибуя!"},
    "SUKUNA":     {"char": "Рёмен Сукуна", "msg": "Король проклятий присоединился!"},
    "ITADORI":    {"char": "Юдзи Итадори", "msg": "Юдзи в команде!"},
    "MEGUMI":     {"coins": 200, "cases": 1, "msg": "Десять теней!"},
    "NOBARA":     {"coins": 200, "msg": "Соломенная кукла!"},
    "CURSE":      {"cases": 3, "msg": "Три бесплатных кейса!"},
}


def redeem_code(player, raw_code):
    """Активирует промокод. Возвращает (ok, message, opened_results|None)."""
    code = raw_code.strip().upper()
    if not code:
        return False, "Введите промокод.", None
    if code not in PROMO_CODES:
        return False, "Неверный промокод.", None
    if code in player["redeemed_codes"]:
        return False, "Этот код уже активирован.", None

    reward = PROMO_CODES[code]
    player["redeemed_codes"].append(code)
    parts = []

    if "coins" in reward:
        player["coins"] += reward["coins"]
        parts.append(f"+{reward['coins']} монет")

    if "char" in reward:
        is_new = add_character(player, reward["char"])
        parts.append(f"персонаж «{reward['char']}»" + (" (новый!)" if is_new else " (дубликат)"))

    opened = None
    if "cases" in reward:
        opened = []
        for _ in range(reward["cases"]):
            player["cases_opened"] += 1
            ch = roll_character()
            is_new = add_character(player, ch["name"])
            opened.append((ch, is_new))
        parts.append(f"{reward['cases']} кейс(ов)")

    save_game(player)
    msg = reward.get("msg", "Промокод активирован!")
    full = f"{msg}\n\nНаграда: " + ", ".join(parts) + "."
    return True, full, opened


# ------------------------------- ВРАГИ -------------------------------
# Больше видов врагов разных тиров. emoji — иконка для интерфейса.
ENEMIES = [
    {"name": "Проклятие 4-го уровня", "emoji": "👻", "hp": 80, "attack": 14, "defense": 6, "speed": 7, "reward": 50, "tier": "Слабые"},
    {"name": "Мутировавшее проклятие", "emoji": "🦠", "hp": 110, "attack": 18, "defense": 9, "speed": 9, "reward": 80, "tier": "Слабые"},
    {"name": "Проклятие 3-го уровня", "emoji": "💀", "hp": 140, "attack": 22, "defense": 12, "speed": 10, "reward": 120, "tier": "Слабые"},
    {"name": "Носитель пальца Сукуны", "emoji": "🖐", "hp": 175, "attack": 27, "defense": 14, "speed": 11, "reward": 170, "tier": "Средние"},
    {"name": "Проклятие 2-го уровня", "emoji": "👹", "hp": 200, "attack": 30, "defense": 16, "speed": 14, "reward": 220, "tier": "Средние"},
    {"name": "Тёмная утроба", "emoji": "🥚", "hp": 235, "attack": 33, "defense": 20, "speed": 9, "reward": 270, "tier": "Средние"},
    {"name": "Тёсо", "emoji": "🩸", "hp": 260, "attack": 36, "defense": 18, "speed": 16, "reward": 320, "tier": "Средние"},
    {"name": "Ханами", "emoji": "🌸", "hp": 285, "attack": 38, "defense": 24, "speed": 13, "reward": 360, "tier": "Сильные"},
    {"name": "Дагон", "emoji": "🌊", "hp": 300, "attack": 40, "defense": 22, "speed": 15, "reward": 400, "tier": "Сильные"},
    {"name": "Дзёго", "emoji": "🌋", "hp": 320, "attack": 44, "defense": 21, "speed": 17, "reward": 460, "tier": "Сильные"},
    {"name": "Проклятие 1-го уровня", "emoji": "👺", "hp": 350, "attack": 46, "defense": 25, "speed": 18, "reward": 500, "tier": "Сильные"},
    {"name": "Курурусу (особый)", "emoji": "🕷", "hp": 400, "attack": 50, "defense": 28, "speed": 20, "reward": 620, "tier": "Особые"},
    {"name": "Махито (раскрытый)", "emoji": "🧬", "hp": 440, "attack": 54, "defense": 27, "speed": 22, "reward": 720, "tier": "Особые"},
    {"name": "Проклятие особого ранга", "emoji": "☠", "hp": 480, "attack": 58, "defense": 32, "speed": 24, "reward": 820, "tier": "Особые"},
    {"name": "Король проклятий (эхо)", "emoji": "🔥", "hp": 560, "attack": 66, "defense": 36, "speed": 27, "reward": 1100, "tier": "Особые"},
]


def make_combatant(char):
    return {
        "name": char["name"], "max_hp": char["hp"], "hp": char["hp"],
        "attack": char["attack"], "defense": char["defense"], "speed": char["speed"],
        "technique": char["technique"], "technique_power": char["technique_power"],
        "energy": 0,
    }


def make_enemy(enemy):
    return {
        "name": f"{enemy['emoji']} {enemy['name']}", "max_hp": enemy["hp"], "hp": enemy["hp"],
        "attack": enemy["attack"], "defense": enemy["defense"], "speed": enemy["speed"],
        "technique": "Проклятый всплеск", "technique_power": int(enemy["attack"] * 1.8),
        "energy": 0,
    }


def calc_damage(attacker, defender, power):
    base = max(1, power - defender["defense"] * 0.5)
    variance = random.uniform(0.85, 1.15)
    crit = random.random() < 0.15
    dmg = int(base * variance * (1.6 if crit else 1.0))
    return dmg, crit


# --------------------------------------------------------------------------
#                              ВИДЖЕТЫ-ПОМОЩНИКИ
# --------------------------------------------------------------------------

def lighten(hex_color, factor=0.25):
    """Делает цвет светлее на factor (0..1)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def blend(c1, c2, t):
    """Линейная интерполяция между двумя hex-цветами (t: 0..1)."""
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r1, g1, b1 = (int(c1[i:i+2], 16) for i in (0, 2, 4))
    r2, g2, b2 = (int(c2[i:i+2], 16) for i in (0, 2, 4))
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class HoverButton(tk.Button):
    """Кнопка с плавной подсветкой при наведении."""
    def __init__(self, master, base_bg, hover_bg, **kw):
        super().__init__(master, bg=base_bg, activebackground=hover_bg,
                         relief="flat", bd=0, cursor="hand2",
                         highlightthickness=0, **kw)
        self.base_bg = base_bg
        self.hover_bg = hover_bg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _e):
        if str(self["state"]) != "disabled":
            self.config(bg=self.hover_bg)

    def _on_leave(self, _e):
        self.config(bg=self.base_bg)


class ParticleField:
    """Анимированный фон с «частицами проклятой энергии» на Canvas."""
    def __init__(self, canvas, count=46):
        self.canvas = canvas
        self.particles = []
        self.count = count
        self.running = True
        canvas.bind("<Configure>", self._on_resize)
        self._spawn()
        self._animate()

    def _dims(self):
        w = self.canvas.winfo_width() or 900
        h = self.canvas.winfo_height() or 640
        return w, h

    def _spawn(self):
        w, h = self._dims()
        colors = [ACCENT, ACCENT2, "#7a4fd6", "#4a3f73", GOLD]
        self.particles = []
        for _ in range(self.count):
            r = random.uniform(1.0, 3.2)
            self.particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "r": r,
                "vy": -random.uniform(0.2, 1.1),
                "vx": random.uniform(-0.3, 0.3),
                "color": random.choice(colors),
            })

    def _on_resize(self, _e):
        self._spawn()

    def _gradient(self, w, h):
        self.canvas.delete("grad")
        steps = 40
        for i in range(steps):
            t = i / (steps - 1)
            color = blend(BG, "#1a1330", t)
            y0 = int(h * i / steps)
            y1 = int(h * (i + 1) / steps) + 1
            self.canvas.create_rectangle(0, y0, w, y1, fill=color,
                                         outline=color, tags="grad")

    def _animate(self):
        if not self.running or not self.canvas.winfo_exists():
            return
        w, h = self._dims()
        self.canvas.delete("grad")
        self._gradient(w, h)
        self.canvas.delete("particle")
        for p in self.particles:
            p["y"] += p["vy"]
            p["x"] += p["vx"]
            if p["y"] < -5:
                p["y"] = h + 5
                p["x"] = random.uniform(0, w)
            if p["x"] < -5:
                p["x"] = w + 5
            elif p["x"] > w + 5:
                p["x"] = -5
            x, y, r = p["x"], p["y"], p["r"]
            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=p["color"], outline="", tags="particle")
        try:
            self.canvas.after(50, self._animate)
        except tk.TclError:
            self.running = False


# --------------------------------------------------------------------------
#                          ГЛАВНОЕ ПРИЛОЖЕНИЕ
# --------------------------------------------------------------------------

class JujutsuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jujutsu Text Battle 2")
        self.geometry("960x680")
        self.minsize(880, 640)
        self.configure(bg=BG)

        self.player = None
        self._anim_jobs = []
        self._setup_style()

        # Верхняя панель статуса (с градиентом через Canvas)
        self.topbar = tk.Canvas(self, height=66, bg=PANEL, highlightthickness=0)
        self.topbar.pack(side="top", fill="x")
        self.topbar.bind("<Configure>", self._draw_topbar)
        self._title_glow = 0.0
        self._title_dir = 1

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(side="top", fill="both", expand=True)

        self._animate_title()
        self.start_screen()

    # ---------------- стиль ----------------
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Vertical.TScrollbar", background=PANEL_LIGHT,
                        troughcolor=BG, bordercolor=BG, arrowcolor=TEXT)

    def _draw_topbar(self, _e=None):
        c = self.topbar
        c.delete("all")
        w = c.winfo_width() or 960
        h = 66
        for i in range(h):
            t = i / h
            color = blend(PANEL, BG, t)
            c.create_line(0, i, w, i, fill=color)
        # светящийся заголовок
        glow = blend(ACCENT, "#ffffff", self._title_glow * 0.5)
        c.create_text(22, h / 2, anchor="w", text="呪 JUJUTSU TEXT BATTLE 2",
                      fill=glow, font=("Segoe UI", 17, "bold"))
        if self.player:
            active = self.player["active"] or "не выбран"
            txt = f"{self.player['name']}    💰 {self.player['coins']}    ⚔ {active}"
            c.create_text(w - 18, h / 2, anchor="e", text=txt,
                          fill=TEXT, font=("Segoe UI", 11))

    def _animate_title(self):
        self._title_glow += 0.06 * self._title_dir
        if self._title_glow >= 1:
            self._title_glow = 1; self._title_dir = -1
        elif self._title_glow <= 0:
            self._title_glow = 0; self._title_dir = 1
        self._draw_topbar()
        self.after(60, self._animate_title)

    def update_status(self):
        self._draw_topbar()

    # ---------------- утилиты ----------------
    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def card(self, parent, **kw):
        opts = dict(bg=PANEL, bd=0, highlightthickness=1,
                    highlightbackground=PANEL_LIGHT)
        opts.update(kw)
        return tk.Frame(parent, **opts)

    def make_button(self, parent, text, command, big=False, color=ACCENT_DARK):
        btn = HoverButton(parent, base_bg=color, hover_bg=lighten(color, 0.22),
                          text=text, command=command, fg=TEXT,
                          font=("Segoe UI", 13 if big else 11,
                                "bold" if big else "normal"),
                          padx=16, pady=12 if big else 8)
        return btn

    def heading(self, parent, text):
        return tk.Label(parent, text=text, bg=BG, fg=TEXT,
                        font=("Segoe UI", 22, "bold"))

    def back_button(self, parent, command):
        return self.make_button(parent, "← Назад", command, color=PANEL_LIGHT)

    # ============================================================
    #                       СТАРТОВЫЙ ЭКРАН
    # ============================================================
    def start_screen(self):
        self.clear()
        self.update_status()

        canvas = tk.Canvas(self.container, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        ParticleField(canvas)

        panel = tk.Frame(canvas, bg=BG)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(panel, text="呪術廻戦", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 46, "bold")).pack()
        tk.Label(panel, text="JUJUTSU TEXT BATTLE 2", bg=BG, fg=TEXT,
                 font=("Segoe UI", 28, "bold")).pack(pady=(2, 6))
        tk.Label(panel, text="Открывай кейсы • Собирай магов • Сражайся с проклятиями",
                 bg=BG, fg=MUTED, font=("Segoe UI", 12)).pack(pady=(0, 28))

        saved = load_game()
        if saved:
            info = f"Сохранение: {saved['name']} • 💰 {saved['coins']} • героев {len(saved['collection'])}"
            tk.Label(panel, text=info, bg=BG, fg=GOLD,
                     font=("Segoe UI", 11)).pack(pady=(0, 10))
            self.make_button(panel, "▶  Продолжить", lambda: self._continue(saved),
                             big=True, color=ACCENT_DARK).pack(fill="x", pady=4)

        self.make_button(panel, "✦  Новая игра", self._new_game_dialog,
                         big=True, color=ACCENT).pack(fill="x", pady=4)
        self.make_button(panel, "✕  Выход", self.destroy,
                         big=True, color=PANEL_LIGHT).pack(fill="x", pady=4)

    def _continue(self, saved):
        self.player = saved
        self.main_menu()

    def _new_game_dialog(self):
        name = simpledialog.askstring("Новая игра", "Введите имя мага:", parent=self)
        if name is None:
            return
        name = name.strip() or "Безымянный маг"
        self.player = new_player(name)
        char = roll_character()
        add_character(self.player, char["name"])
        save_game(self.player)
        self.update_status()
        messagebox.showinfo(
            "Добро пожаловать!",
            f"Удачи, {name}!\n\nВам начислено 300 проклятых монет.\n"
            f"Стартовый персонаж: [{char['rank']}] {char['name']}.\n\n"
            f"Подсказка: загляни в «Промокоды» в меню!")
        self.main_menu()

    # ============================================================
    #                        ГЛАВНОЕ МЕНЮ
    # ============================================================
    def main_menu(self):
        self.clear()
        self.update_status()

        canvas = tk.Canvas(self.container, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        ParticleField(canvas, count=34)

        wrap = tk.Frame(canvas, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        self.heading(wrap, "Главное меню").pack(pady=(0, 22))

        buttons = [
            ("📦  Открыть кейсы", self.shop_screen, ACCENT),
            ("🎴  Коллекция", self.collection_screen, ACCENT_DARK),
            ("⚔  В бой!", self.battle_select_screen, ACCENT_DARK),
            ("🎁  Промокоды", self.promo_screen, "#d98a3a"),
            ("👤  Профиль", self.profile_screen, ACCENT_DARK),
            ("💾  Сохранить игру", self._save_and_notify, ACCENT_DARK),
            ("⏏  Выйти в меню", self.start_screen, PANEL_LIGHT),
        ]
        for text, cmd, col in buttons:
            self.make_button(wrap, text, cmd, big=True, color=col).pack(
                fill="x", pady=4, ipadx=50)

    def _save_and_notify(self):
        if save_game(self.player):
            messagebox.showinfo("Сохранение", "Игра успешно сохранена!")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить игру.")

    # ============================================================
    #                          ПРОМОКОДЫ
    # ============================================================
    def promo_screen(self):
        self.clear()
        self.update_status()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)

        top = tk.Frame(root, bg=BG)
        top.pack(fill="x")
        self.heading(top, "🎁 Промокоды").pack(side="left")
        self.back_button(top, self.main_menu).pack(side="right")

        tk.Label(root, text="Введите промокод и получите награду. Каждый код — один раз.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 12)).pack(anchor="w", pady=(12, 16))

        entry_card = self.card(root)
        entry_card.pack(fill="x", pady=4)
        inner = tk.Frame(entry_card, bg=PANEL)
        inner.pack(padx=16, pady=16, fill="x")

        self.promo_var = tk.StringVar()
        entry = tk.Entry(inner, textvariable=self.promo_var, font=("Consolas", 15),
                         bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                         relief="flat", justify="center")
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._do_redeem())
        self.make_button(inner, "Активировать", self._do_redeem,
                         big=True, color=ACCENT).pack(side="right")

        self.promo_result = tk.Label(root, text="", bg=BG, fg=GREEN,
                                     font=("Segoe UI", 12, "bold"),
                                     wraplength=820, justify="left")
        self.promo_result.pack(anchor="w", pady=16)

        hint = ("Подсказки: попробуй названия техник и героев из аниме —\n"
                "например, имя сильнейшего мага, короля проклятий или\n"
                "знаменитую «вспышку». Коды вводятся без учёта регистра.")
        tk.Label(root, text=hint, bg=BG, fg=MUTED, font=("Segoe UI", 10),
                 justify="left").pack(anchor="w", side="bottom")

        used = len(self.player["redeemed_codes"])
        tk.Label(root, text=f"Активировано кодов: {used} / {len(PROMO_CODES)}",
                 bg=BG, fg=GOLD, font=("Segoe UI", 11)).pack(anchor="w", side="bottom", pady=(0, 6))

    def _do_redeem(self):
        ok, message, opened = redeem_code(self.player, self.promo_var.get())
        self.update_status()
        self.promo_result.config(text=message, fg=GREEN if ok else RED)
        if ok:
            self.promo_var.set("")
            if opened:
                self.after(700, lambda: self.case_reveal_screen(opened, return_to="promo"))

    # ============================================================
    #                          МАГАЗИН
    # ============================================================
    def shop_screen(self):
        self.clear()
        self.update_status()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)

        top = tk.Frame(root, bg=BG)
        top.pack(fill="x")
        self.heading(top, "📦 Магазин кейсов").pack(side="left")
        self.back_button(top, self.main_menu).pack(side="right")

        tk.Label(root, text=f"Цена кейса: {CASE_PRICE} монет",
                 bg=BG, fg=MUTED, font=("Segoe UI", 12)).pack(anchor="w", pady=(10, 4))

        rates = self.card(root)
        rates.pack(fill="x", pady=8)
        tk.Label(rates, text="Шансы выпадения рангов", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(10, 6))
        for rank in db.RANKS:
            rate = db.RANK_DROP_RATES[rank]
            row = tk.Frame(rates, bg=PANEL)
            row.pack(fill="x", padx=14, pady=2)
            tk.Label(row, text=rank, bg=PANEL, fg=db.RANK_HEX[rank], width=12,
                     anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left")
            bar_bg = tk.Frame(row, bg=PANEL_LIGHT, height=16, width=420)
            bar_bg.pack(side="left", padx=8)
            bar_bg.pack_propagate(False)
            fill = tk.Frame(bar_bg, bg=db.RANK_HEX[rank], height=16,
                            width=max(4, int(rate / 100 * 420)))
            fill.pack(side="left")
            tk.Label(row, text=f"{rate:.0f}%", bg=PANEL, fg=MUTED).pack(side="left", padx=6)
        tk.Frame(rates, bg=PANEL, height=8).pack()

        btns = tk.Frame(root, bg=BG)
        btns.pack(pady=18)
        self.make_button(btns, "Открыть 1 кейс  (100)",
                         lambda: self.open_cases(1), big=True, color=ACCENT).pack(side="left", padx=8)
        self.make_button(btns, "Открыть 5 кейсов  (500)",
                         lambda: self.open_cases(5), big=True).pack(side="left", padx=8)

    def open_cases(self, count):
        cost = CASE_PRICE * count
        if self.player["coins"] < cost:
            messagebox.showwarning("Недостаточно монет",
                                   f"Нужно {cost} монет, у вас {self.player['coins']}.")
            return
        self.player["coins"] -= cost
        results = []
        for _ in range(count):
            self.player["cases_opened"] += 1
            char = roll_character()
            is_new = add_character(self.player, char["name"])
            results.append((char, is_new))
        save_game(self.player)
        self.update_status()
        self.case_reveal_screen(results)

    # ----------------- АНИМАЦИЯ ОТКРЫТИЯ КЕЙСА -----------------
    def case_reveal_screen(self, results, return_to="shop"):
        self.clear()
        self.update_status()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)
        self.heading(root, "✦ Открытие кейса ✦").pack(pady=(0, 6))

        # большая «коробка» по центру для эффекта вспышки
        self.reveal_canvas = tk.Canvas(root, bg=BG, height=140, highlightthickness=0)
        self.reveal_canvas.pack(fill="x", pady=6)

        spin_lbl = tk.Label(root, text="", bg=BG, fg=ACCENT,
                            font=("Segoe UI", 26, "bold"))
        spin_lbl.pack()

        result_holder = tk.Frame(root, bg=BG)
        result_holder.pack(fill="both", expand=True, pady=10)

        best_rank_idx = max(db.RANKS.index(c["rank"]) for c, _ in results)
        best_rank = db.RANKS[best_rank_idx]

        self._spin_left = 22
        self._spin_speed = 45

        def animate():
            if self._spin_left > 0:
                ch = random.choice(db.CHARACTERS)
                spin_lbl.config(text=ch["name"], fg=db.RANK_HEX[ch["rank"]])
                self._flash_box(db.RANK_HEX[ch["rank"]], 0.3)
                self._spin_left -= 1
                # замедление к концу
                if self._spin_left < 8:
                    self._spin_speed += 18
                self.after(self._spin_speed, animate)
            else:
                spin_lbl.config(text="", fg=ACCENT)
                self._rarity_burst(best_rank, lambda: self._show_results(
                    result_holder, results, return_to))
        animate()

    def _flash_box(self, color, alpha=0.5):
        c = self.reveal_canvas
        c.delete("all")
        w = c.winfo_width() or 880
        h = 140
        cx = w / 2
        bg = blend(BG, color, alpha)
        c.create_rectangle(cx - 90, 20, cx + 90, 120, fill=bg, outline=color, width=3)
        c.create_text(cx, 70, text="📦", font=("Segoe UI", 44))

    def _rarity_burst(self, rank, on_done):
        """Вспышка цвета редкости, расходящаяся от центра."""
        c = self.reveal_canvas
        color = db.RANK_HEX[rank]
        w = c.winfo_width() or 880
        h = 140
        cx, cy = w / 2, h / 2
        self._burst_r = 0

        def step():
            if not c.winfo_exists():
                return
            c.delete("all")
            self._burst_r += 18
            r = self._burst_r
            shade = blend(color, BG, min(1, r / 240))
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=shade, width=4)
            c.create_oval(cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6,
                          outline=color, width=2)
            c.create_text(cx, cy, text=rank, fill=color,
                          font=("Segoe UI", 18, "bold"))
            if r < 260:
                self.after(22, step)
            else:
                c.delete("all")
                c.create_text(cx, cy, text=f"✦ {rank} ✦", fill=color,
                              font=("Segoe UI", 20, "bold"))
                on_done()
        step()

    def _show_results(self, holder, results, return_to):
        grid = tk.Frame(holder, bg=BG)
        grid.pack()
        for i, (char, is_new) in enumerate(results):
            col = i % 5
            row = i // 5
            rcolor = db.RANK_HEX[char["rank"]]
            c = tk.Frame(grid, bg=PANEL, highlightthickness=2,
                         highlightbackground=rcolor)
            c.grid(row=row, column=col, padx=6, pady=6, sticky="n")
            tk.Label(c, text=char["rank"], bg=PANEL, fg=rcolor,
                     font=("Segoe UI", 10, "bold")).pack(padx=10, pady=(8, 0))
            tk.Label(c, text=char["name"], bg=PANEL, fg=TEXT, wraplength=150,
                     justify="center", font=("Segoe UI", 11, "bold")).pack(padx=10)
            tk.Label(c, text=f"HP {char['hp']} • АТК {char['attack']}",
                     bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(padx=10)
            tag = "★ НОВЫЙ" if is_new else f"дубль +{db.RANK_SELL_VALUE[char['rank']]}"
            tk.Label(c, text=tag, bg=PANEL, fg=(GOLD if is_new else MUTED),
                     font=("Segoe UI", 9, "bold")).pack(padx=10, pady=(0, 8))
            # пульсация рамки для высоких рангов
            if db.RANKS.index(char["rank"]) >= 4:
                self._pulse_border(c, rcolor)

        btns = tk.Frame(holder, bg=BG)
        btns.pack(pady=18)
        if return_to == "shop":
            self.make_button(btns, "Открыть ещё", self.shop_screen,
                             big=True, color=ACCENT).pack(side="left", padx=8)
        self.make_button(btns, "В меню", self.main_menu, big=True).pack(side="left", padx=8)

    def _pulse_border(self, widget, color):
        state = {"t": 0.0, "dir": 1}

        def step():
            if not widget.winfo_exists():
                return
            state["t"] += 0.08 * state["dir"]
            if state["t"] >= 1:
                state["t"] = 1; state["dir"] = -1
            elif state["t"] <= 0:
                state["t"] = 0; state["dir"] = 1
            widget.config(highlightbackground=blend(color, "#ffffff", state["t"] * 0.6))
            self.after(60, step)
        step()

    # ============================================================
    #                         КОЛЛЕКЦИЯ
    # ============================================================
    def collection_screen(self):
        self.clear()
        self.update_status()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)

        top = tk.Frame(root, bg=BG)
        top.pack(fill="x")
        self.heading(top, "🎴 Коллекция").pack(side="left")
        self.back_button(top, self.main_menu).pack(side="right")

        if not self.player["collection"]:
            tk.Label(root, text="Коллекция пуста. Откройте кейсы в магазине!",
                     bg=BG, fg=MUTED, font=("Segoe UI", 13)).pack(pady=40)
            return

        tk.Label(root, text=f"Уникальных героев: {len(self.player['collection'])} / {len(db.CHARACTERS)}",
                 bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w", pady=(8, 6))

        canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        owned = [db.get_character(n) for n in self.player["collection"]]
        owned.sort(key=lambda c: (-db.RANKS.index(c["rank"]), c["name"]))
        for char in owned:
            self._collection_row(scroll_frame, char)

    def _collection_row(self, parent, char):
        count = self.player["collection"][char["name"]]
        is_active = char["name"] == self.player["active"]
        rcolor = db.RANK_HEX[char["rank"]]
        row = tk.Frame(parent, bg=PANEL, highlightthickness=2,
                       highlightbackground=ACCENT if is_active else PANEL_LIGHT)
        row.pack(fill="x", pady=4, padx=2)

        # цветная полоска ранга слева
        strip = tk.Frame(row, bg=rcolor, width=6)
        strip.pack(side="left", fill="y")

        tk.Label(row, text=char["rank"], bg=PANEL, fg=rcolor,
                 width=11, anchor="w", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(12, 6), pady=10)

        info = tk.Frame(row, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)
        name_txt = char["name"] + (f"  x{count}" if count > 1 else "")
        if is_active:
            name_txt += "   • активный"
        tk.Label(info, text=name_txt, bg=PANEL, fg=TEXT,
                 anchor="w", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(info, text=f"{char['technique']} • HP {char['hp']} • АТК {char['attack']} • ЗАЩ {char['defense']} • СКР {char['speed']}",
                 bg=PANEL, fg=MUTED, anchor="w", font=("Segoe UI", 9)).pack(anchor="w")

        actions = tk.Frame(row, bg=PANEL)
        actions.pack(side="right", padx=10)
        if not is_active:
            self.make_button(actions, "Сделать активным",
                             lambda c=char: self._set_active(c), color=ACCENT_DARK).pack(side="left", padx=4)
        if count > 1:
            self.make_button(actions, f"Продать ({db.RANK_SELL_VALUE[char['rank']]})",
                             lambda c=char: self._sell(c), color=PANEL_LIGHT).pack(side="left", padx=4)

    def _set_active(self, char):
        self.player["active"] = char["name"]
        save_game(self.player)
        self.collection_screen()

    def _sell(self, char):
        if self.player["collection"][char["name"]] <= 1:
            return
        self.player["collection"][char["name"]] -= 1
        self.player["coins"] += db.RANK_SELL_VALUE[char["rank"]]
        save_game(self.player)
        self.collection_screen()

    # ============================================================
    #                     ВЫБОР ПРОТИВНИКА
    # ============================================================
    def battle_select_screen(self):
        self.clear()
        self.update_status()
        if self.player["active"] is None:
            messagebox.showwarning("Нет бойца", "Сначала откройте кейс и выберите бойца!")
            self.main_menu()
            return

        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x")
        self.heading(top, "⚔ Выбор противника").pack(side="left")
        self.back_button(top, self.main_menu).pack(side="right")

        hero = db.get_character(self.player["active"])
        tk.Label(root, text=f"Ваш боец: [{hero['rank']}] {hero['name']}  "
                            f"(HP {hero['hp']} • АТК {hero['attack']})",
                 bg=BG, fg=GREEN, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 12))

        canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        current_tier = None
        tier_colors = {"Слабые": GREEN, "Средние": ACCENT2, "Сильные": ACCENT, "Особые": GOLD}
        for enemy in ENEMIES:
            if enemy["tier"] != current_tier:
                current_tier = enemy["tier"]
                tk.Label(scroll_frame, text=f"— {current_tier} —", bg=BG,
                         fg=tier_colors.get(current_tier, MUTED),
                         font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 2))
            self._enemy_row(scroll_frame, enemy)

    def _enemy_row(self, parent, enemy):
        row = self.card(parent)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=enemy["emoji"], bg=PANEL,
                 font=("Segoe UI", 22)).pack(side="left", padx=(14, 6), pady=10)
        info = tk.Frame(row, bg=PANEL)
        info.pack(side="left", padx=4, pady=12)
        tk.Label(info, text=enemy["name"], bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(info, text=f"HP {enemy['hp']} • АТК {enemy['attack']} • ЗАЩ {enemy['defense']} • награда 💰 {enemy['reward']}",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.make_button(row, "Сразиться", lambda e=enemy: self.start_battle(e),
                         color=ACCENT).pack(side="right", padx=14)

    # ============================================================
    #                            БОЙ
    # ============================================================
    def start_battle(self, enemy_data):
        hero_char = db.get_character(self.player["active"])
        self.hero = make_combatant(hero_char)
        self.enemy = make_enemy(enemy_data)
        self.reward = enemy_data["reward"]
        self.turn = 1
        self.battle_over = False
        self.defending = False
        self.battle_screen()

    def battle_screen(self):
        self.clear()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=14)
        self.battle_root = root
        self.heading(root, "⚔ Сражение").pack(anchor="w")

        bars = tk.Frame(root, bg=BG)
        bars.pack(fill="x", pady=10)
        self.hero_panel = self._combatant_panel(bars, self.hero, GREEN, "left")
        self.enemy_panel = self._combatant_panel(bars, self.enemy, RED, "right")

        log_card = self.card(root)
        log_card.pack(fill="both", expand=True, pady=8)
        self.log = tk.Text(log_card, bg=PANEL, fg=TEXT, bd=0, height=8,
                           font=("Consolas", 10), wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=10)
        self.log.tag_config("hero", foreground=GREEN)
        self.log.tag_config("enemy", foreground=RED)
        self.log.tag_config("crit", foreground=GOLD)
        self.log.tag_config("tech", foreground=ACCENT)

        self.actions_frame = tk.Frame(root, bg=BG)
        self.actions_frame.pack(fill="x", pady=8)
        self._render_actions()

        self._log(f"Бой начался: {self.hero['name']} против {self.enemy['name']}!")
        self._init_bars()

    def _combatant_panel(self, parent, comb, color, side):
        p = self.card(parent, width=400)
        p.pack(side=side, fill="x", expand=True, padx=6)
        tk.Label(p, text=comb["name"], bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        hp_bg = tk.Frame(p, bg=PANEL_LIGHT, height=24)
        hp_bg.pack(fill="x", padx=12)
        hp_bg.pack_propagate(False)
        hp_fill = tk.Frame(hp_bg, bg=color, height=24)
        hp_fill.place(x=0, y=0, relheight=1.0, relwidth=1.0)
        hp_text = tk.Label(hp_bg, text="", bg=color, fg="#0d0d0d",
                           font=("Segoe UI", 9, "bold"))
        hp_text.place(relx=0.5, rely=0.5, anchor="center")
        en_bg = tk.Frame(p, bg=PANEL_LIGHT, height=8)
        en_bg.pack(fill="x", padx=12, pady=(6, 2))
        en_bg.pack_propagate(False)
        en_fill = tk.Frame(en_bg, bg=ACCENT2, height=8)
        en_fill.place(x=0, y=0, relheight=1.0, relwidth=0.0)
        en_text = tk.Label(p, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        en_text.pack(anchor="w", padx=12, pady=(2, 10))
        return {"frame": p, "color": color, "hp_bg": hp_bg, "hp_fill": hp_fill,
                "hp_text": hp_text, "en_fill": en_fill, "en_text": en_text,
                "cur_ratio": 1.0}

    def _init_bars(self):
        for comb, panel in ((self.hero, self.hero_panel), (self.enemy, self.enemy_panel)):
            panel["cur_ratio"] = comb["hp"] / comb["max_hp"]
            panel["hp_fill"].place_configure(relwidth=panel["cur_ratio"])
            panel["hp_text"].config(text=f"{comb['hp']} / {comb['max_hp']}")
        self._refresh_energy()

    def _refresh_energy(self):
        self.hero_panel["en_fill"].place_configure(relwidth=self.hero["energy"] / 100)
        self.enemy_panel["en_fill"].place_configure(relwidth=self.enemy["energy"] / 100)
        self.hero_panel["en_text"].config(text=f"Энергия: {self.hero['energy']}/100")
        self.enemy_panel["en_text"].config(text=f"Энергия: {self.enemy['energy']}/100   ход {self.turn}")

    def _animate_hp(self, comb, panel):
        """Плавно анимирует полосу HP к текущему значению."""
        target = max(0, comb["hp"]) / comb["max_hp"]
        panel["hp_text"].config(text=f"{max(0, comb['hp'])} / {comb['max_hp']}")

        def step():
            if not panel["hp_fill"].winfo_exists():
                return
            cur = panel["cur_ratio"]
            diff = target - cur
            if abs(diff) < 0.01:
                panel["cur_ratio"] = target
                panel["hp_fill"].place_configure(relwidth=max(0, target))
                return
            panel["cur_ratio"] = cur + diff * 0.25
            panel["hp_fill"].place_configure(relwidth=max(0, panel["cur_ratio"]))
            self.after(20, step)
        step()

    def _flash_panel(self, panel):
        """Кратковременная вспышка панели при получении урона."""
        frame = panel["frame"]
        if not frame.winfo_exists():
            return
        frame.config(highlightthickness=2, highlightbackground=RED)
        self.after(140, lambda: frame.winfo_exists() and
                   frame.config(highlightthickness=1, highlightbackground=PANEL_LIGHT))

    def _float_damage(self, panel, amount, crit=False, heal=False):
        """Всплывающая цифра урона над панелью."""
        frame = panel["frame"]
        if not frame.winfo_exists():
            return
        color = GOLD if crit else (GREEN if heal else "#ffffff")
        prefix = "+" if heal else "-"
        lbl = tk.Label(frame, text=f"{prefix}{amount}", bg=PANEL, fg=color,
                       font=("Segoe UI", 16 if not crit else 20, "bold"))
        x = random.uniform(0.3, 0.7)
        state = {"y": 0.55}
        lbl.place(relx=x, rely=state["y"], anchor="center")

        def step():
            if not lbl.winfo_exists():
                return
            state["y"] -= 0.04
            if state["y"] < 0.12:
                lbl.destroy()
                return
            lbl.place_configure(rely=state["y"])
            self.after(40, step)
        step()

    def _render_actions(self):
        for w in self.actions_frame.winfo_children():
            w.destroy()
        tech_ready = self.hero["energy"] >= 100
        self.make_button(self.actions_frame, "Атака (+30 энергии)",
                         lambda: self.hero_action("attack"), color=ACCENT_DARK).pack(side="left", padx=5)
        tech_btn = self.make_button(self.actions_frame, f"Техника: {self.hero['technique']}",
                                    lambda: self.hero_action("technique"),
                                    color=ACCENT if tech_ready else PANEL_LIGHT)
        tech_btn.pack(side="left", padx=5)
        if not tech_ready:
            tech_btn.config(state="disabled")
        self.make_button(self.actions_frame, "Защита (+20)",
                         lambda: self.hero_action("defend"), color=ACCENT_DARK).pack(side="left", padx=5)
        self.make_button(self.actions_frame, "Сбежать",
                         self.try_flee, color=PANEL_LIGHT).pack(side="left", padx=5)

    def _log(self, text, tag=None):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag or "")
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_actions_enabled(self, enabled):
        for w in self.actions_frame.winfo_children():
            try:
                w.config(state="normal" if enabled else "disabled")
            except tk.TclError:
                pass

    def hero_action(self, kind):
        if self.battle_over:
            return
        self.defending = False
        if kind == "attack":
            dmg, crit = calc_damage(self.hero, self.enemy, self.hero["attack"])
            self.enemy["hp"] -= dmg
            self.hero["energy"] = min(100, self.hero["energy"] + 30)
            self._log(f"{self.hero['name']} атакует на {dmg} урона." +
                      ("  КРИТ!" if crit else ""), "crit" if crit else "hero")
            self._animate_hp(self.enemy, self.enemy_panel)
            self._flash_panel(self.enemy_panel)
            self._float_damage(self.enemy_panel, dmg, crit)
        elif kind == "technique":
            if self.hero["energy"] < 100:
                return
            self.hero["energy"] = 0
            dmg, crit = calc_damage(self.hero, self.enemy, self.hero["technique_power"])
            self.enemy["hp"] -= dmg
            self._log(f"✦ {self.hero['name']} применяет «{self.hero['technique']}» — "
                      f"{dmg} урона!" + ("  КРИТ!" if crit else ""), "tech")
            self._screen_shake()
            self._animate_hp(self.enemy, self.enemy_panel)
            self._flash_panel(self.enemy_panel)
            self._float_damage(self.enemy_panel, dmg, True)
        elif kind == "defend":
            self.defending = True
            self.hero["energy"] = min(100, self.hero["energy"] + 20)
            self._log(f"{self.hero['name']} занимает оборону.", "hero")

        self._refresh_energy()
        if self.enemy["hp"] <= 0:
            self._end_battle(victory=True)
            return
        self._set_actions_enabled(False)
        self.after(700, self.enemy_action)

    def enemy_action(self):
        if self.battle_over:
            return
        self.enemy["energy"] = min(100, self.enemy["energy"] + 30)
        crit = False
        if self.enemy["energy"] >= 100 and random.random() < 0.6:
            self.enemy["energy"] = 0
            dmg, crit = calc_damage(self.enemy, self.hero, self.enemy["technique_power"])
            if self.defending:
                dmg = int(dmg * 0.5)
            self.hero["hp"] -= dmg
            self._log(f"✦ {self.enemy['name']} применяет «{self.enemy['technique']}» — "
                      f"{dmg} урона!", "enemy")
            self._screen_shake()
        else:
            dmg, crit = calc_damage(self.enemy, self.hero, self.enemy["attack"])
            if self.defending:
                dmg = int(dmg * 0.5)
            self.hero["hp"] -= dmg
            self._log(f"{self.enemy['name']} атакует на {dmg} урона." +
                      ("  КРИТ!" if crit else ""), "crit" if crit else "enemy")

        self._animate_hp(self.hero, self.hero_panel)
        self._flash_panel(self.hero_panel)
        self._float_damage(self.hero_panel, dmg, crit)
        self._refresh_energy()
        if self.hero["hp"] <= 0:
            self._end_battle(victory=False)
            return
        self.turn += 1
        self._refresh_energy()
        self._render_actions()

    def _screen_shake(self, count=6):
        """Лёгкая тряска окна для эффектности техник."""
        try:
            geo = self.geometry()
            base = geo.split("+")
            if len(base) < 3:
                return
            size, x0, y0 = base[0], int(base[1]), int(base[2])
        except (ValueError, tk.TclError):
            return
        offsets = [(-6, 0), (6, 0), (-4, 2), (4, -2), (-2, 0), (0, 0)][:count]

        def do(i):
            if i >= len(offsets) or not self.winfo_exists():
                self.geometry(f"{size}+{x0}+{y0}")
                return
            dx, dy = offsets[i]
            self.geometry(f"{size}+{x0 + dx}+{y0 + dy}")
            self.after(28, lambda: do(i + 1))
        do(0)

    def try_flee(self):
        if self.battle_over:
            return
        if random.random() < 0.5:
            self._log("Вы успешно сбежали из боя.")
            self.battle_over = True
            self.after(800, self.main_menu)
        else:
            self._log("Сбежать не удалось!", "enemy")
            self._set_actions_enabled(False)
            self.after(700, self.enemy_action)

    def _end_battle(self, victory):
        self.battle_over = True
        self._set_actions_enabled(False)
        if victory:
            self.player["coins"] += self.reward
            self.player["battles_won"] += 1
            save_game(self.player)
            self.update_status()
            self._log(f"ПОБЕДА! {self.enemy['name']} повержен. Награда: {self.reward} монет.", "crit")
            self.after(450, lambda: self._battle_result_dialog(True))
        else:
            self._log(f"ПОРАЖЕНИЕ. {self.hero['name']} пал в бою.", "enemy")
            self.after(450, lambda: self._battle_result_dialog(False))

    def _battle_result_dialog(self, victory):
        if victory:
            messagebox.showinfo("Победа!",
                                f"{self.enemy['name']} повержен!\nНаграда: {self.reward} монет.")
        else:
            messagebox.showinfo("Поражение",
                                "Ваш боец пал. Прокачайте коллекцию и возвращайтесь!")
        self.battle_select_screen()

    # ============================================================
    #                          ПРОФИЛЬ
    # ============================================================
    def profile_screen(self):
        self.clear()
        self.update_status()
        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True, padx=24, pady=20)
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x")
        self.heading(top, "👤 Профиль").pack(side="left")
        self.back_button(top, self.main_menu).pack(side="right")

        card = self.card(root)
        card.pack(fill="x", pady=16)
        rows = [
            ("Имя мага", self.player["name"]),
            ("Проклятые монеты", f"💰 {self.player['coins']}"),
            ("Активный боец", self.player["active"] or "—"),
            ("Побед в боях", self.player["battles_won"]),
            ("Кейсов открыто", self.player["cases_opened"]),
            ("Уникальных героев", f"{len(self.player['collection'])} / {len(db.CHARACTERS)}"),
            ("Активировано промокодов", f"{len(self.player['redeemed_codes'])} / {len(PROMO_CODES)}"),
        ]
        for label, value in rows:
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", padx=18, pady=6)
            tk.Label(r, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 12)).pack(side="left")
            tk.Label(r, text=str(value), bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 12, "bold")).pack(side="right")


def main():
    app = JujutsuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
