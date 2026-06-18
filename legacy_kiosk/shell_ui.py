# -*- coding: utf-8 -*-

import os
import time

try:
    import Tkinter as tkinter
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
except ImportError:
    import tkinter
    from tkinter import filedialog, messagebox


DESIGN_WIDTH = 1440
DESIGN_HEIGHT = 900
WATCHDOG_INTERVAL_MS = 1000
THEME = {
    "background": "#050505",
    "panel": "#111418",
    "panel2": "#171b20",
    "muted": "#9ca3af",
    "text": "#f4f6f8",
    "accent": "#38bdf8",
    "blue": "#0ea5e9",
    "ok": "#22c55e",
    "danger": "#ef4444",
    "line": "#2b3138",
}


def _round_rect(name, x, y, width, height, radius, fill, outline=None, tags=()):
    return {
        "kind": "round_rect",
        "name": name,
        "rect": (x, y, width, height, radius),
        "fill": fill,
        "outline": outline,
        "tags": tuple(tags),
    }


def _text(name, text, x, y, width, height, font, fill, anchor="nw", tags=()):
    return {
        "kind": "text",
        "name": name,
        "text": text,
        "rect": (x, y, width, height),
        "font": font,
        "fill": fill,
        "anchor": anchor,
        "tags": tuple(tags),
    }


def build_shell_layout(
    app_path,
    app_status="running",
    admin_session_active=False,
    watchdog_enabled=True,
):
    minimized = app_status == "minimized"
    status_text = u"Свёрнуто" if minimized else u"Работает"
    status_color = THEME["danger"] if minimized else THEME["ok"]
    status_fill = "#3a1616" if minimized else "#0f2f1f"
    watchdog_text = u"Надзор: включён" if watchdog_enabled else u"Надзор: остановлен"
    watchdog_button_text = (
        u"Остановить надзор" if watchdog_enabled else u"Запустить надзор"
    )
    items = [
        {
            "kind": "background",
            "name": "background",
            "rect": (0, 0, DESIGN_WIDTH, DESIGN_HEIGHT),
            "fill": THEME["background"],
        },
        _round_rect("header_mark", 48, 34, 38, 38, 8, "#0f8bd7"),
        _text(
            "header_mark_text",
            u"РК",
            67,
            53,
            1,
            1,
            ("Segoe UI", 11, "bold"),
            "#ffffff",
            anchor="center",
        ),
        _text(
            "header_title",
            u"Режим киоска",
            100,
            40,
            168,
            32,
            ("Segoe UI", 16, "bold"),
            THEME["text"],
        ),
        _round_rect(
            "header_year_badge", 276, 29, 62, 48, 12, "#102126", "#397080"
        ),
        _text(
            "header_year_text",
            u"2026",
            307,
            53,
            1,
            1,
            ("Segoe UI", 10, "normal"),
            "#67e8f9",
            anchor="center",
        ),
        _text(
            "header_subtitle",
            u"Режим оператора: Explorer не запущен.",
            50,
            88,
            760,
            30,
            ("Segoe UI", 15, "normal"),
            THEME["muted"],
        ),
        _round_rect("left_panel", 50, 150, 820, 560, 8, THEME["panel"], THEME["line"]),
        _text(
            "allowed_title",
            u"Разрешённое приложение",
            92,
            190,
            480,
            44,
            ("Segoe UI", 26, "bold"),
            THEME["text"],
        ),
        _text(
            "allowed_subtitle",
            u"Запущено только настроенное приложение.",
            94,
            238,
            650,
            30,
            ("Segoe UI", 15, "normal"),
            THEME["muted"],
        ),
        _round_rect("app_card", 95, 300, 690, 250, 8, "#0b1220", "#1d4ed8"),
        _text(
            "app_name",
            os.path.basename(app_path) or app_path,
            135,
            344,
            560,
            58,
            ("Segoe UI", 34, "bold"),
            THEME["text"],
        ),
        _text(
            "app_path",
            app_path,
            138,
            410,
            600,
            55,
            ("Courier New", 13, "normal"),
            THEME["muted"],
        ),
        _round_rect("running_pill", 135, 478, 190, 44, 8, status_fill),
        _text(
            "running_status",
            status_text,
            166,
            486,
            130,
            28,
            ("Segoe UI", 15, "normal"),
            status_color,
        ),
        _round_rect(
            "watchdog_pill",
            345,
            478,
            270,
            44,
            8,
            "#122033" if watchdog_enabled else "#242a31",
        ),
        _text(
            "watchdog_status",
            watchdog_text,
            372,
            486,
            210,
            28,
            ("Segoe UI", 15, "normal"),
            THEME["accent"] if watchdog_enabled else THEME["muted"],
        ),
        _text(
            "restart_message",
            u"Если приложение свёрнуто, разверните его кнопкой.",
            94,
            586,
            720,
            34,
            ("Segoe UI", 15, "normal"),
            THEME["muted"],
        ),
        _round_rect("right_panel", 920, 150, 470, 560, 8, THEME["panel"], THEME["line"]),
        _text(
            "admin_title",
            u"Разблокировка",
            955,
            190,
            300,
            44,
            ("Segoe UI", 26, "bold"),
            THEME["text"],
        ),
        _round_rect(
            "unlock_button",
            958,
            284,
            250,
            54,
            8,
            THEME["blue"],
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_text",
            u"Разблокировать",
            985,
            297,
            200,
            28,
            ("Segoe UI", 15, "bold"),
            "#00111f",
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_hint",
            u"Нажмите кнопку для входа администратора.",
            958,
            360,
            360,
            48,
            ("Segoe UI", 13, "normal"),
            THEME["muted"],
        ),
        _round_rect("safety_strip", 50, 760, 1340, 86, 8, "#101010", "#27272a"),
        _text(
            "safety_message",
            u"Win+L доступна. Службы, драйверы, процессы и автозагрузка не изменяются.",
            82,
            792,
            1050,
            28,
            ("Segoe UI", 15, "normal"),
            THEME["muted"],
        ),
        _text(
            "developer_credit",
            u"разработал: Абдрахманов Амаль Даулетович",
            1390,
            858,
            520,
            28,
            ("Segoe UI", 12, "normal"),
            "#6b7280",
            anchor="ne",
        ),
    ]
    if minimized:
        items.extend(
            [
                _round_rect(
                    "minimized_alert", 135, 558, 520, 42, 8, "#3a1616", "#7f1d1d"
                ),
                _text(
                    "minimized_alert_text",
                    u"Приложение свёрнуто",
                    158,
                    567,
                    440,
                    24,
                    ("Segoe UI", 14, "bold"),
                    THEME["danger"],
                ),
                _round_rect(
                    "restore_app_button",
                    135,
                    615,
                    255,
                    44,
                    8,
                    THEME["blue"],
                    tags=("restore_app_click",),
                ),
                _text(
                    "restore_app_button_text",
                    u"Развернуть приложение",
                    158,
                    625,
                    220,
                    24,
                    ("Segoe UI", 14, "bold"),
                    "#00111f",
                    tags=("restore_app_click",),
                ),
            ]
        )
    if admin_session_active:
        items.append(
            _text(
                "admin_session_title",
                u"Админ-сессия активна",
                958,
                430,
                330,
                28,
                ("Segoe UI", 15, "bold"),
                THEME["ok"],
            )
        )
        items.extend(
            _button_layout(
                "unlock_desktop", u"Открыть рабочий стол", 958, 470, THEME["blue"]
            )
        )
        items.extend(
            _button_layout(
                "watchdog",
                watchdog_button_text,
                958,
                526,
                "#242a31" if watchdog_enabled else THEME["blue"],
            )
        )
        items.extend(
            _button_layout(
                "return_kiosk", u"Вернуться в киоск", 958, 582, "#101820"
            )
        )
        items.extend(
            _button_layout(
                "change_app", u"Изменить приложение", 958, 638, "#242a31"
            )
        )
    return items


def _button_layout(prefix, text, x, y, fill):
    tag = "%s_click" % prefix
    return [
        _round_rect(
            "%s_button" % prefix, x, y, 250, 44, 8, fill, tags=(tag,)
        ),
        _text(
            "%s_button_text" % prefix,
            text,
            x + 25,
            y + 10,
            210,
            24,
            ("Segoe UI", 13, "bold"),
            THEME["text"] if fill != THEME["blue"] else "#00111f",
            tags=(tag,),
        ),
    ]


def build_login_entry_options(masked=False):
    options = {
        "fg": THEME["text"],
        "bg": "#090b0f",
        "insertbackground": THEME["text"],
        "insertwidth": 2,
        "relief": "flat",
        "font": ("Courier New", 13),
        "highlightthickness": 1,
        "highlightbackground": "#4b5563",
        "highlightcolor": THEME["accent"],
        "selectbackground": THEME["accent"],
        "selectforeground": "#00111f",
    }
    if masked:
        options["show"] = "*"
    return options


def login_dialog_geometry(screen_width, screen_height):
    width = min(380, max(300, int(screen_width) - 40))
    height = min(350, max(300, int(screen_height) - 40))
    preferred_x = int(round(float(screen_width) * 965.0 / DESIGN_WIDTH))
    preferred_y = int(round(float(screen_height) * 270.0 / DESIGN_HEIGHT))
    x = max(0, min(preferred_x, int(screen_width) - width))
    y = max(0, min(preferred_y, int(screen_height) - height))
    return "%sx%s+%s+%s" % (width, height, x, y)


def _flatten_layout(layout):
    result = []
    for item in layout:
        if isinstance(item, list):
            result.extend(_flatten_layout(item))
        else:
            result.append(item)
    return result


def _draw_round_rect(canvas, x, y, width, height, radius, fill, outline, tags):
    right = x + width
    bottom = y + height
    points = (
        x + radius, y, right - radius, y, right, y, right, y + radius,
        right, bottom - radius, right, bottom, right - radius, bottom,
        x + radius, bottom, x, bottom, x, bottom - radius, x, y + radius, x, y,
    )
    canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=16,
        fill=fill,
        outline=outline or fill,
        width=2,
        tags=tags,
    )


def render_layout(canvas, layout, width, height):
    scale_x = float(width) / DESIGN_WIDTH
    scale_y = float(height) / DESIGN_HEIGHT
    for item in _flatten_layout(layout):
        if item["kind"] == "background":
            canvas.create_rectangle(0, 0, width, height, fill=item["fill"], outline=item["fill"])
            continue
        rect = item["rect"]
        x = rect[0] * scale_x
        y = rect[1] * scale_y
        item_width = rect[2] * scale_x
        item_height = rect[3] * scale_y
        if item["kind"] == "round_rect":
            _draw_round_rect(
                canvas,
                x,
                y,
                item_width,
                item_height,
                min(rect[4] * scale_x, rect[4] * scale_y),
                item["fill"],
                item.get("outline"),
                item.get("tags", ()),
            )
            continue
        family, size, style = item["font"]
        canvas.create_text(
            x,
            y,
            anchor=item.get("anchor", "nw"),
            text=item["text"],
            fill=item["fill"],
            font=(family, max(8, int(round(size * scale_y))), style),
            width=item_width,
            tags=item.get("tags", ()),
        )


class LegacyShellWindow(object):
    def __init__(
        self,
        root,
        runtime,
        credential_provider=None,
        error_reporter=None,
        application_selector=None,
        clock=None,
        sleeper=None,
        watchdog_interval_ms=WATCHDOG_INTERVAL_MS,
    ):
        self.root = root
        self.runtime = runtime
        self.credential_provider = credential_provider or self._show_login_dialog
        self.error_reporter = error_reporter or self._show_error
        self.application_selector = application_selector or self._select_application
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep
        self.watchdog_interval_ms = int(watchdog_interval_ms)
        self.canvas = None
        self.app_status = "running"
        self.admin_session_active = False
        self.admin_session_expires_at = None
        self.admin_dialog_open = False
        self.failed_attempts = 0

    @property
    def app_path(self):
        return self.runtime.config["allowedApplication"]["path"]

    def configure_window(self):
        self.root.title(u"Режим киоска")
        self.root.configure(bg=THEME["background"])
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.attributes("-fullscreen", True)
        self.canvas = tkinter.Canvas(
            self.root,
            bg=THEME["background"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._bind_clicks()
        self._render()
        self.keep_shell_background()

    def _bind_clicks(self):
        bindings = {
            "unlock_click": self.handle_admin_unlock,
            "restore_app_click": self.handle_restore_app,
            "unlock_desktop_click": self.handle_unlock_desktop,
            "watchdog_click": self.handle_watchdog_toggle,
            "return_kiosk_click": self.handle_return_to_kiosk,
            "change_app_click": self.handle_change_application,
        }
        for tag, handler in bindings.items():
            self.canvas.tag_bind(tag, "<Button-1>", handler)
            self.canvas.tag_configure(tag, cursor="hand2")
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self._render(event.width, event.height)

    def _render(self, width=None, height=None):
        if self.canvas is None:
            return
        width = width or self.root.winfo_screenwidth()
        height = height or self.root.winfo_screenheight()
        self.canvas.delete("all")
        render_layout(
            self.canvas,
            build_shell_layout(
                self.app_path,
                app_status=self.app_status,
                admin_session_active=self.admin_session_active,
                watchdog_enabled=self.runtime.watchdog_enabled,
            ),
            width,
            height,
        )

    def keep_shell_background(self):
        for action in (
            lambda: self.root.attributes("-topmost", False),
            lambda: self.root.lower(),
        ):
            try:
                action()
            except Exception:
                pass

    def _keyboard_stop(self):
        keyboard_filter = getattr(self.runtime, "keyboard_filter", None)
        if keyboard_filter is not None:
            keyboard_filter.stop()

    def _keyboard_start(self):
        keyboard_filter = getattr(self.runtime, "keyboard_filter", None)
        if keyboard_filter is not None:
            keyboard_filter.start()

    def handle_admin_unlock(self, event=None):
        if self.admin_dialog_open or self.admin_session_active:
            return self.admin_session_active
        self.keep_shell_background()
        self._keyboard_stop()
        self.admin_dialog_open = True
        try:
            try:
                credentials = self.credential_provider()
            except Exception:
                self.error_reporter(
                    u"Не удалось открыть окно авторизации администратора Windows."
                )
                self._keyboard_start()
                return False
        finally:
            self.admin_dialog_open = False
        if not credentials:
            self._keyboard_start()
            return False
        username, password = credentials
        try:
            try:
                result = self.runtime.authenticate(username, password)
            except Exception:
                self.error_reporter(
                    u"Отказано в доступе. Ошибка проверки учётной записи Windows."
                )
                self._keyboard_start()
                return False
        finally:
            password = None
        if result.success:
            self.failed_attempts = 0
            self.admin_session_active = True
            timeout = int(
                self.runtime.config.get("kiosk", {}).get(
                    "adminSessionTimeoutSeconds", 300
                )
            )
            self.admin_session_expires_at = float(self.clock()) + timeout
            self.keep_shell_background()
            self._render()
            return True
        self.failed_attempts += 1
        self.error_reporter(result.message)
        delay = 0
        if self.failed_attempts >= 3:
            delay = min(30, 2 ** (self.failed_attempts - 2))
        if delay:
            self.sleeper(delay)
        self._keyboard_start()
        return False

    def handle_unlock_desktop(self, event=None):
        if not self.admin_session_active:
            return False
        self.runtime.open_desktop()
        self.keep_shell_background()
        return True

    def handle_watchdog_toggle(self, event=None):
        if not self.admin_session_active:
            return False
        if self.runtime.watchdog_enabled:
            self.runtime.stop_supervision()
        else:
            self.runtime.start_supervision()
        self._render()
        return True

    def handle_return_to_kiosk(self, event=None):
        if not self.admin_session_active:
            return False
        self.runtime.return_to_kiosk()
        self.admin_session_active = False
        self.admin_session_expires_at = None
        self._keyboard_start()
        self.keep_shell_background()
        self._render()
        return True

    def handle_change_application(self, event=None):
        if not self.admin_session_active:
            return False
        path = self.application_selector()
        if not path:
            return False
        self.runtime.change_allowed_application(path)
        self.app_status = "running"
        self._render()
        return True

    def handle_restore_app(self, event=None):
        if self.runtime.restore_allowed_application():
            self.app_status = "running"
            self.keep_shell_background()
            self._render()
            return True
        return False

    def watchdog_tick(self):
        if self.admin_session_active:
            if float(self.clock()) >= float(self.admin_session_expires_at):
                self.handle_return_to_kiosk()
            self._schedule_tick()
            return
        result = self.runtime.tick_watchdog()
        if result in ("started", "restarted", "adopted"):
            self.runtime.bring_allowed_application_to_front(wait=True)
        if self.runtime.is_allowed_application_minimized():
            next_status = "minimized"
        else:
            next_status = "running"
            if result == "running":
                self.runtime.bring_allowed_application_to_front(wait=False)
        if next_status != self.app_status:
            self.app_status = next_status
            self._render()
        self.keep_shell_background()
        self._schedule_tick()

    def _schedule_tick(self):
        self.root.after(self.watchdog_interval_ms, self.watchdog_tick)

    def start(self):
        self.configure_window()
        self._keyboard_start()
        self.watchdog_tick()
        try:
            self.root.mainloop()
        finally:
            self._keyboard_stop()

    def _show_login_dialog(self):
        return LegacyAdminLoginDialog(self.root).ask()

    def _show_error(self, message):
        messagebox.showerror(u"Режим киоска", message)

    def _select_application(self):
        return filedialog.askopenfilename(
            title=u"Выберите разрешённое приложение",
            filetypes=((u"Windows EXE", "*.exe"), (u"Все файлы", "*.*")),
        )


class LegacyAdminLoginDialog(object):
    def __init__(self, root):
        self.root = root
        self.result = None

    def ask(self):
        dialog = tkinter.Toplevel(self.root)
        dialog.title(u"Режим киоска")
        dialog.configure(bg=THEME["panel2"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry(
            login_dialog_geometry(
                dialog.winfo_screenwidth(), dialog.winfo_screenheight()
            )
        )
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        frame = tkinter.Frame(
            dialog,
            bg=THEME["panel2"],
            highlightbackground="#374151",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True)
        tkinter.Label(
            frame,
            text=u"Вход администратора Windows",
            fg=THEME["text"],
            bg=THEME["panel2"],
            font=("Segoe UI", 15),
            anchor="w",
        ).place(x=34, y=30, width=310, height=30)
        tkinter.Label(
            frame,
            text=u"Логин",
            fg=THEME["muted"],
            bg=THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        ).place(x=34, y=72, width=160, height=22)
        username = tkinter.Entry(frame, **build_login_entry_options(masked=False))
        username.place(x=34, y=98, width=300, height=42)
        tkinter.Label(
            frame,
            text=u"Пароль",
            fg=THEME["muted"],
            bg=THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        ).place(x=34, y=152, width=160, height=22)
        password = tkinter.Entry(frame, **build_login_entry_options(masked=True))
        password.place(x=34, y=178, width=300, height=42)

        def accept(event=None):
            self.result = (username.get().strip(), password.get())
            dialog.destroy()

        def cancel(event=None):
            self.result = None
            dialog.destroy()

        tkinter.Button(
            frame,
            text=u"ОК",
            command=accept,
            fg="#00111f",
            bg=THEME["blue"],
            relief="flat",
            font=("Segoe UI", 15),
        ).place(x=34, y=264, width=132, height=42)
        tkinter.Button(
            frame,
            text=u"Отмена",
            command=cancel,
            fg=THEME["text"],
            bg="#242a31",
            relief="flat",
            font=("Segoe UI", 15),
        ).place(x=184, y=264, width=118, height=42)
        dialog.bind("<Return>", accept)
        dialog.bind("<Escape>", cancel)
        username.focus_set()
        dialog.after(50, username.focus_force)
        self.root.wait_window(dialog)
        return self.result
