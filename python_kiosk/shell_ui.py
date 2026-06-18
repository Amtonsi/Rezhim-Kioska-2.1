# -*- coding: utf-8 -*-

import subprocess
import os
import threading
import time

from python_kiosk.admin_session import AdminSession
from python_kiosk.logging_service import KioskLogger
from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_SUCCESS,
    AuthResult,
    MESSAGE_BAD_CREDENTIALS,
)
from python_kiosk.session_lockdown import WindowsSessionLockdown
from python_kiosk.security import FailedAttemptLimiter
from python_kiosk.window_control import AppWindowController


WATCHDOG_INTERVAL_MS = 2000
FOCUS_GUARD_INTERVAL_MS = 500
DESIGN_WIDTH = 1440
DESIGN_HEIGHT = 900
SHELL_THEME = {
    "background": "#050505",
    "panel": "#111418",
    "panel2": "#171b20",
    "muted": "#9ca3af",
    "text": "#f4f6f8",
    "accent": "#38bdf8",
    "ok": "#22c55e",
    "danger": "#ef4444",
    "line": "#2b3138",
    "blue": "#0ea5e9",
}


def _app_name(app_path):
    name = os.path.basename(app_path)
    return name or app_path


def combine_windows_account_name(username, domain):
    username = (username or "").strip()
    domain = (domain or "").strip()
    if "\\" in username or not domain:
        return username
    return "{0}\\{1}".format(domain, username)


def _round_rect(name, x, y, width, height, radius, fill, outline=None, tags=None):
    return {
        "kind": "round_rect",
        "name": name,
        "rect": (x, y, width, height, radius),
        "fill": fill,
        "outline": outline,
        "tags": tuple(tags or ()),
    }


def _text(name, text, x, y, width, height, font, fill, anchor="nw", tags=None):
    return {
        "kind": "text",
        "name": name,
        "text": text,
        "rect": (x, y, width, height),
        "font": font,
        "fill": fill,
        "anchor": anchor,
        "tags": tuple(tags or ()),
    }


def build_shell_layout(
    app_path,
    app_status="running",
    admin_session_active=False,
    watchdog_enabled=True,
):
    theme = SHELL_THEME
    is_minimized = app_status == "minimized"
    watchdog_enabled = bool(watchdog_enabled)
    status_text = "Свернуто" if is_minimized else "Работает"
    status_color = theme["danger"] if is_minimized else theme["ok"]
    status_fill = "#3a1616" if is_minimized else "#0f2f1f"
    watchdog_status_text = (
        "Надзор: включен" if watchdog_enabled else "Надзор: остановлен"
    )
    watchdog_status_fill = theme["accent"] if watchdog_enabled else theme["muted"]
    watchdog_pill_fill = "#122033" if watchdog_enabled else "#242a31"
    watchdog_button_text = (
        "Остановить надзор" if watchdog_enabled else "Запустить надзор"
    )
    watchdog_button_fill = "#242a31" if watchdog_enabled else theme["blue"]
    watchdog_button_text_fill = theme["text"] if watchdog_enabled else "#00111f"
    layout = [
        {
            "kind": "background",
            "name": "background",
            "rect": (0, 0, DESIGN_WIDTH, DESIGN_HEIGHT),
            "fill": theme["background"],
        },
        _text(
            "header_title",
            "Режим киоска",
            48,
            42,
            420,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _text(
            "header_subtitle",
            "Режим оператора: Explorer не запущен.",
            50,
            88,
            760,
            30,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("left_panel", 50, 150, 820, 560, 14, theme["panel"], theme["line"]),
        _text(
            "allowed_title",
            "Разрешенное приложение",
            92,
            190,
            420,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _text(
            "allowed_subtitle",
            "Запущено только настроенное приложение.",
            94,
            238,
            650,
            30,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("app_card", 95, 300, 690, 250, 12, "#0b1220", "#1d4ed8"),
        _text(
            "app_name",
            _app_name(app_path),
            135,
            344,
            430,
            58,
            ("Segoe UI", 36, "bold"),
            theme["text"],
        ),
        _text(
            "app_path",
            app_path,
            138,
            410,
            520,
            28,
            ("Consolas", 13, "normal"),
            theme["muted"],
        ),
        _round_rect("running_pill", 135, 478, 190, 44, 22, status_fill, None),
        _text(
            "running_status",
            status_text,
            166,
            486,
            110,
            28,
            ("Segoe UI", 15, "normal"),
            status_color,
        ),
        _round_rect("watchdog_pill", 345, 478, 270, 44, 22, watchdog_pill_fill, None),
        _text(
            "watchdog_status",
            watchdog_status_text,
            372,
            486,
            190,
            28,
            ("Segoe UI", 15, "normal"),
            watchdog_status_fill,
        ),
        _text(
            "restart_message",
            "Приложение должно быть поверх оболочки. Если оно свернуто, разверните его кнопкой.",
            94,
            586,
            720,
            34,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("right_panel", 920, 150, 470, 560, 14, theme["panel"], theme["line"]),
        _text(
            "admin_title",
            "Разблокировка",
            955,
            190,
            260,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _round_rect(
            "unlock_button",
            958,
            284,
            250,
            54,
            8,
            theme["blue"],
            None,
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_text",
            "Разблокировать",
            985,
            297,
            190,
            28,
            ("Segoe UI", 15, "bold"),
            "#00111f",
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_hint",
            "Нажмите кнопку для входа администратора.",
            958,
            360,
            360,
            28,
            ("Segoe UI", 13, "normal"),
            theme["muted"],
        ),
        _text(
            "unlock_success_message",
            "После успеха откроется ограниченная админ-сессия.",
            958,
            718,
            360,
            42,
            ("Segoe UI", 12, "normal"),
            theme["muted"],
        ),
        _round_rect("safety_strip", 50, 760, 1340, 86, 12, "#101010", "#27272a"),
        _text(
            "safety_title",
            "Модель безопасности",
            82,
            782,
            160,
            28,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
        _text(
            "safety_message",
            "Win+L остается доступен. Службы, драйверы, процессы и автозагрузка не трогаются.",
            82,
            815,
            1120,
            28,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _text(
            "policy_note",
            "Политики реестра: только отдельной админ-командой.",
            735,
            782,
            580,
            28,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _text(
            "developer_credit",
            "разработал: Абдрахманов Амаль Даулетович",
            1390,
            858,
            520,
            28,
            ("Segoe UI", 12, "normal"),
            "#6b7280",
            anchor="ne",
        ),
    ]
    if admin_session_active:
        layout.extend(
            [
                _text(
                    "admin_session_title",
                    "Админ-сессия активна",
                    958,
                    455,
                    330,
                    28,
                    ("Segoe UI", 15, "bold"),
                    theme["ok"],
                ),
                _round_rect(
                    "unlock_desktop_button",
                    958,
                    492,
                    250,
                    44,
                    8,
                    theme["blue"],
                    None,
                    tags=("unlock_desktop_click",),
                ),
                _text(
                    "unlock_desktop_button_text",
                    "Открыть рабочий стол",
                    980,
                    502,
                    210,
                    24,
                    ("Segoe UI", 13, "bold"),
                    "#00111f",
                    tags=("unlock_desktop_click",),
                ),
                _round_rect(
                    "stop_watchdog_button",
                    958,
                    548,
                    250,
                    44,
                    8,
                    watchdog_button_fill,
                    None,
                    tags=("stop_watchdog_click",),
                ),
                _text(
                    "stop_watchdog_button_text",
                    watchdog_button_text,
                    984,
                    558,
                    205,
                    24,
                    ("Segoe UI", 13, "bold"),
                    watchdog_button_text_fill,
                    tags=("stop_watchdog_click",),
                ),
                _round_rect(
                    "return_kiosk_button",
                    958,
                    604,
                    250,
                    44,
                    8,
                    "#101820",
                    "#374151",
                    tags=("return_kiosk_click",),
                ),
                _text(
                    "return_kiosk_button_text",
                    "Вернуться в киоск",
                    995,
                    614,
                    180,
                    24,
                    ("Segoe UI", 13, "bold"),
                    theme["accent"],
                    tags=("return_kiosk_click",),
                ),
                _round_rect(
                    "change_app_button",
                    958,
                    660,
                    250,
                    44,
                    8,
                    "#242a31",
                    None,
                    tags=("change_app_click",),
                ),
                _text(
                    "change_app_button_text",
                    "Изменить приложение",
                    1000,
                    670,
                    180,
                    24,
                    ("Segoe UI", 13, "bold"),
                    theme["text"],
                    tags=("change_app_click",),
                ),
            ]
        )
    if is_minimized:
        layout.extend(
            [
                _round_rect(
                    "minimized_alert",
                    135,
                    558,
                    520,
                    42,
                    8,
                    "#3a1616",
                    "#7f1d1d",
                ),
                _text(
                    "minimized_alert_text",
                    "Приложение свернуто",
                    158,
                    567,
                    440,
                    24,
                    ("Segoe UI", 14, "bold"),
                    theme["danger"],
                ),
                _round_rect(
                    "restore_app_button",
                    135,
                    615,
                    255,
                    44,
                    8,
                    theme["blue"],
                    None,
                    tags=("restore_app_click",),
                ),
                _text(
                    "restore_app_button_text",
                    "Развернуть приложение",
                    158,
                    625,
                    210,
                    24,
                    ("Segoe UI", 14, "bold"),
                    "#00111f",
                    tags=("restore_app_click",),
                ),
            ]
        )
    return layout


def build_unlock_dialog_layout():
    theme = SHELL_THEME
    return [
        _round_rect("unlock_dialog", 965, 270, 380, 350, 12, theme["panel2"], "#374151"),
        _text(
            "unlock_title",
            "Вход администратора Windows",
            1000,
            320,
            310,
            30,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
        _text(
            "username_label",
            "Логин",
            1000,
            365,
            120,
            22,
            ("Segoe UI", 11, "normal"),
            theme["muted"],
        ),
        _round_rect("username_input", 1000, 391, 300, 42, 8, "#090b0f", "#4b5563"),
        _text(
            "username_example",
            "Администратор",
            1018,
            401,
            220,
            22,
            ("Consolas", 12, "normal"),
            theme["muted"],
        ),
        _text(
            "password_label",
            "Пароль",
            1000,
            432,
            120,
            22,
            ("Segoe UI", 11, "normal"),
            theme["muted"],
        ),
        _round_rect("password_input", 1000, 458, 300, 42, 8, "#090b0f", "#4b5563"),
        _text(
            "password_bullets",
            "************",
            1018,
            468,
            220,
            24,
            ("Consolas", 13, "normal"),
            theme["muted"],
        ),
        _round_rect("unlock_button", 1000, 540, 132, 42, 8, theme["blue"], None),
        _text(
            "unlock_button_text",
            "Открыть",
            1035,
            548,
            78,
            26,
            ("Segoe UI", 15, "normal"),
            "#00111f",
        ),
        _round_rect("cancel_button", 1150, 540, 118, 42, 8, "#242a31", None),
        _text(
            "cancel_button_text",
            "Отмена",
            1183,
            548,
            70,
            26,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
    ]


def scaled_unlock_dialog_geometry(screen_width, screen_height):
    dialog = dict((item["name"], item) for item in build_unlock_dialog_layout())[
        "unlock_dialog"
    ]
    x, y, width, height, _ = dialog["rect"]
    scale_x = float(screen_width) / DESIGN_WIDTH
    scale_y = float(screen_height) / DESIGN_HEIGHT
    return "{0}x{1}+{2}+{3}".format(
        int(round(width * scale_x)),
        int(round(height * scale_y)),
        int(round(x * scale_x)),
        int(round(y * scale_y)),
    )


def build_login_entry_options(masked=False):
    options = {
        "fg": SHELL_THEME["text"],
        "bg": "#090b0f",
        "insertbackground": SHELL_THEME["text"],
        "insertwidth": 2,
        "relief": "flat",
        "font": ("Consolas", 13),
        "highlightthickness": 1,
        "highlightbackground": "#4b5563",
        "highlightcolor": SHELL_THEME["accent"],
        "selectbackground": SHELL_THEME["accent"],
        "selectforeground": "#00111f",
    }
    if masked:
        options["show"] = "*"
    return options


def _scale_rect(rect, scale_x, scale_y):
    if len(rect) == 5:
        x, y, width, height, radius = rect
        return (
            x * scale_x,
            y * scale_y,
            width * scale_x,
            height * scale_y,
            min(radius * scale_x, radius * scale_y),
        )
    x, y, width, height = rect
    return x * scale_x, y * scale_y, width * scale_x, height * scale_y


def _scale_font(font, scale_y):
    family, size, style = font
    scaled_size = max(8, int(round(size * scale_y)))
    return family, scaled_size, style


def _draw_round_rect(canvas, x, y, width, height, radius, fill, outline=None, tags=()):
    x2 = x + width
    y2 = y + height
    points = [
        x + radius,
        y,
        x2 - radius,
        y,
        x2,
        y,
        x2,
        y + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x + radius,
        y2,
        x,
        y2,
        x,
        y2 - radius,
        x,
        y + radius,
        x,
        y,
    ]
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
    for item in layout:
        kind = item["kind"]
        if kind == "background":
            canvas.create_rectangle(0, 0, width, height, fill=item["fill"], outline=item["fill"])
        elif kind == "round_rect":
            x, y, w, h, r = _scale_rect(item["rect"], scale_x, scale_y)
            _draw_round_rect(
                canvas,
                x,
                y,
                w,
                h,
                r,
                item["fill"],
                item.get("outline"),
                item.get("tags", ()),
            )
        elif kind == "text":
            x, y, w, h = _scale_rect(item["rect"], scale_x, scale_y)
            canvas.create_text(
                x,
                y,
                anchor=item.get("anchor", "nw"),
                text=item["text"],
                fill=item["fill"],
                font=_scale_font(item["font"], scale_y),
                width=w,
                tags=item.get("tags", ()),
            )


class ShellWindow(object):
    def __init__(
        self,
        root,
        launcher,
        credential_provider=None,
        password_provider=None,
        unlock_action=None,
        hotkey_service=None,
        keyboard_filter_service=None,
        app_window_controller=None,
        canvas_factory=None,
        credential_dialog_factory=None,
        password_dialog_factory=None,
        failed_attempt_limiter=None,
        sleep_func=None,
        logger=None,
        admin_session=None,
        session_lockdown=None,
        error_reporter=None,
        allowed_app_selector=None,
        watchdog_interval_ms=WATCHDOG_INTERVAL_MS,
        focus_guard_interval_ms=FOCUS_GUARD_INTERVAL_MS,
    ):
        self.root = root
        self.launcher = launcher
        self.credential_provider = (
            credential_provider
            or self._wrap_password_provider(password_provider)
            or self._default_credential_provider
        )
        self.unlock_action = unlock_action or unlock_desktop
        self.hotkey_service = hotkey_service
        self.keyboard_filter_service = keyboard_filter_service
        self.app_window_controller = app_window_controller or AppWindowController()
        self.canvas_factory = canvas_factory
        self.credential_dialog_factory = (
            credential_dialog_factory
            or password_dialog_factory
            or StyledAdminLoginDialog
        )
        self.failed_attempt_limiter = failed_attempt_limiter or FailedAttemptLimiter()
        self.sleep_func = sleep_func or time.sleep
        self.logger = logger or KioskLogger()
        self.admin_session = admin_session or AdminSession(logger=self.logger)
        self.error_reporter = error_reporter or (
            show_admin_error if hasattr(self.root, "tk") else (lambda message: False)
        )
        self.allowed_app_selector = allowed_app_selector or select_allowed_application
        kiosk_options = getattr(self.launcher.config, "kiosk", {})
        self.session_lockdown = session_lockdown or WindowsSessionLockdown(
            logger=self.logger,
            enabled=bool(kiosk_options.get("blockDesktop", True)),
        )
        self.watchdog_interval_ms = int(watchdog_interval_ms)
        self.focus_guard_interval_ms = int(focus_guard_interval_ms)
        self.watchdog = None
        self.canvas = None
        self.app_status = "running"
        self.watchdog_disabled = False
        self.keyboard_filter_suspended_for_admin = False
        self.admin_dialog_open = False

    def configure_window(self):
        self.root.title("Режим киоска")
        self.root.configure(bg=SHELL_THEME["background"])
        self.root.protocol("WM_DELETE_WINDOW", self.ignore_close)
        self.root.bind("<FocusOut>", self.keep_shell_background)
        self.root.bind("<Unmap>", self._handle_shell_unmap)
        self.activate_restrictions()
        self._configure_canvas()
        self.enforce_shell_focus()
        self.keep_shell_background()
        self.root.after(self.focus_guard_interval_ms, self._focus_guard_tick)

    def ignore_close(self):
        return None

    def _wrap_password_provider(self, password_provider):
        if password_provider is None:
            return None

        def provider():
            return "", password_provider()

        return provider

    def _default_credential_provider(self):
        return self.credential_dialog_factory(self.root).ask()

    def _configure_canvas(self):
        factory = self.canvas_factory
        if factory is None and hasattr(self.root, "tk"):
            factory = create_shell_canvas
        if factory is None:
            return

        self.canvas = factory(self.root)
        self.canvas.pack(fill="both", expand=True)
        self._configure_canvas_clicks()
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self._render_canvas(width, height)
        self.canvas.bind("<Configure>", self._handle_canvas_resize)

    def _configure_canvas_clicks(self):
        if hasattr(self.canvas, "tag_bind"):
            self.canvas.tag_bind("unlock_click", "<Button-1>", self.handle_admin_unlock)
            self.canvas.tag_bind("restore_app_click", "<Button-1>", self.handle_restore_app)
            self.canvas.tag_bind("unlock_desktop_click", "<Button-1>", self.handle_unlock_desktop)
            self.canvas.tag_bind("stop_watchdog_click", "<Button-1>", self.handle_stop_watchdog)
            self.canvas.tag_bind("return_kiosk_click", "<Button-1>", self.handle_return_to_kiosk)
            self.canvas.tag_bind("change_app_click", "<Button-1>", self.handle_change_allowed_app)
        if hasattr(self.canvas, "tag_configure"):
            self.canvas.tag_configure("unlock_click", cursor="hand2")
            self.canvas.tag_configure("restore_app_click", cursor="hand2")
            self.canvas.tag_configure("unlock_desktop_click", cursor="hand2")
            self.canvas.tag_configure("stop_watchdog_click", cursor="hand2")
            self.canvas.tag_configure("return_kiosk_click", cursor="hand2")
            self.canvas.tag_configure("change_app_click", cursor="hand2")

    def _handle_canvas_resize(self, event):
        self._render_canvas(event.width, event.height)

    def _render_canvas(self, width, height):
        self.canvas.delete("all")
        layout = build_shell_layout(
            self.launcher.config.app_path,
            self.app_status,
            admin_session_active=self.admin_session.is_active(),
            watchdog_enabled=not self.watchdog_disabled,
        )
        render_layout(self.canvas, layout, width, height)

    def enforce_shell_focus(self, event=None):
        for call in (
            lambda: self.root.state("normal"),
            self.root.deiconify,
            lambda: self.root.attributes("-fullscreen", True),
        ):
            try:
                call()
            except Exception:
                pass

    def keep_shell_background(self, event=None):
        for call in (
            lambda: self.root.attributes("-topmost", False),
            self.root.lower,
        ):
            try:
                call()
            except Exception:
                pass

    def _handle_shell_unmap(self, event=None):
        if not self.admin_session.is_active():
            self.enforce_shell_focus()
        self.keep_shell_background()

    def _focus_guard_tick(self):
        self.keep_shell_background()
        self.root.after(self.focus_guard_interval_ms, self._focus_guard_tick)

    def handle_admin_unlock(self, event=None):
        if self.admin_dialog_open or self.admin_session.is_active():
            return bool(self.admin_session.is_active())
        self.logger.info("admin.dialog_open")
        self.keep_shell_background()
        self._reset_keyboard_filter_state()
        self._stop_keyboard_filter()
        self.admin_dialog_open = True
        try:
            credentials = self.credential_provider()
        finally:
            self.admin_dialog_open = False
        if not credentials:
            self._resume_keyboard_filter_after_dialog()
            return False
        username, password = credentials
        result = self._verify_admin_credentials(username, password)
        if result.success:
            self.failed_attempt_limiter.record_success()
            self.logger.info("admin.unlock_granted", **result.to_log_data())
            self.admin_session.start(result.username or username)
            self._suspend_keyboard_filter_for_admin_session()
            self.keep_shell_background()
            self._rerender_canvas()
            return True
        delay = self.failed_attempt_limiter.record_failure()
        data = result.to_log_data()
        data["message"] = result.message
        data["delay_seconds"] = delay
        self.logger.warning("admin.unlock_denied", **data)
        self.error_reporter(result.message)
        if delay > 0:
            self.sleep_func(delay)
        self._resume_keyboard_filter_after_dialog()
        return False

    def _verify_admin_credentials(self, username, password):
        if hasattr(self.launcher, "verify_admin_credentials_result"):
            return self.launcher.verify_admin_credentials_result(username, password)
        if self.launcher.verify_admin_credentials(username, password):
            return AuthResult(
                AUTH_SUCCESS,
                username=username,
                domain="",
                message="Доступ разрешён.",
            )
        return AuthResult(
            AUTH_BAD_CREDENTIALS,
            username=username,
            domain="",
            message=MESSAGE_BAD_CREDENTIALS,
        )

    def handle_unlock_desktop(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="unlock_desktop")
            return False
        self.release_restrictions()
        self.unlock_action()
        self.admin_session.mark_desktop_unlocked()
        self.logger.info("explorer.launched", username=self.admin_session.username)
        return True

    def handle_stop_watchdog(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="stop_watchdog")
            return False
        if self.watchdog_disabled:
            try:
                self._start_watchdog_now()
            except Exception as error:
                self.logger.warning("watchdog.start_by_admin_failed", error=str(error))
                self.error_reporter(str(error))
                return False
            self.logger.info("watchdog.started_by_admin", username=self.admin_session.username)
            self._rerender_canvas()
            return True
        self.watchdog_disabled = True
        if self.watchdog is not None and hasattr(self.watchdog, "stop"):
            self.watchdog.stop()
        self.watchdog = None
        self.logger.warning("watchdog.stopped_by_admin", username=self.admin_session.username)
        self._rerender_canvas()
        return True

    def handle_return_to_kiosk(self, event=None):
        if self.watchdog is not None and getattr(self.watchdog, "stopped", False):
            self.watchdog = None
        self.watchdog_disabled = False
        self.admin_session.close(reason="return_to_kiosk")
        self.logger.info("admin.return_to_kiosk")
        self.activate_restrictions()
        self.enforce_shell_focus()
        self.keep_shell_background()
        self._rerender_canvas()
        return True

    def handle_change_allowed_app(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="change_allowed_app")
            return False
        app_path = self.allowed_app_selector()
        if not app_path:
            return False
        try:
            self.launcher.set_allowed_application_path(app_path)
        except Exception as error:
            self.logger.warning("admin.change_app_failed", error=str(error))
            self.error_reporter(str(error))
            return False
        if self.watchdog is not None and hasattr(self.watchdog, "stop"):
            self.watchdog.stop()
        self.app_status = "running"
        try:
            self._start_watchdog_now()
        except Exception as error:
            self.logger.warning("admin.change_app_start_failed", error=str(error))
            self.error_reporter(str(error))
            self._rerender_canvas()
            return False
        self._rerender_canvas()
        self.logger.info("admin.change_app_path", path=app_path)
        return True

    def _start_watchdog_now(self):
        self.watchdog_disabled = False
        self.watchdog = self.launcher.create_watchdog()
        watchdog_result = self.watchdog.tick()
        if watchdog_result in ("started", "restarted", "running"):
            self.app_status = "running"
        return watchdog_result

    def release_restrictions(self):
        if self.hotkey_service is not None and hasattr(self.hotkey_service, "stop"):
            self.hotkey_service.stop()
        self._stop_keyboard_filter()
        if self.session_lockdown is not None and hasattr(
            self.session_lockdown,
            "release_operator_mode",
        ):
            self.session_lockdown.release_operator_mode()
        if self.app_window_controller is not None and hasattr(
            self.app_window_controller,
            "release_topmost",
        ):
            self.app_window_controller.release_topmost(self.launcher.config.app_path)

    def activate_restrictions(self):
        if self.keyboard_filter_service is not None:
            self.keyboard_filter_service.start()
            self.keyboard_filter_suspended_for_admin = False
        if self.session_lockdown is not None:
            self.session_lockdown.activate_operator_mode()

    def _reset_keyboard_filter_state(self):
        if self.keyboard_filter_service is not None and hasattr(
            self.keyboard_filter_service,
            "reset_state",
        ):
            self.keyboard_filter_service.reset_state()

    def _suspend_keyboard_filter_for_admin_session(self):
        self._stop_keyboard_filter()

    def _stop_keyboard_filter(self):
        if self.keyboard_filter_suspended_for_admin:
            return
        if self.keyboard_filter_service is not None and hasattr(
            self.keyboard_filter_service,
            "stop",
        ):
            self.keyboard_filter_service.stop()
        self.keyboard_filter_suspended_for_admin = True

    def _resume_keyboard_filter_after_dialog(self):
        if self.admin_session.is_active():
            return
        if not self.keyboard_filter_suspended_for_admin:
            return
        if self.keyboard_filter_service is not None and hasattr(
            self.keyboard_filter_service,
            "start",
        ):
            self.keyboard_filter_service.start()
        self.keyboard_filter_suspended_for_admin = False

    def handle_restore_app(self, event=None):
        if self.app_window_controller.restore(self.launcher.config.app_path):
            self.keep_shell_background()
            self.app_status = "running"
            self._rerender_canvas()
        return True

    def _rerender_canvas(self):
        if self.canvas is None:
            return
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self._render_canvas(width, height)

    def _watchdog_tick(self):
        if self.watchdog_disabled:
            self.root.after(self.watchdog_interval_ms, self._watchdog_tick)
            return
        if self.watchdog is None:
            self.watchdog = self.launcher.create_watchdog()
        admin_active = self.admin_session.is_active()
        if self.admin_dialog_open:
            self.root.after(self.watchdog_interval_ms, self._watchdog_tick)
            return
        if not admin_active and self._pause_watchdog_for_minimized_app():
            self.root.after(self.watchdog_interval_ms, self._watchdog_tick)
            return
        watchdog_result = self.watchdog.tick()
        if watchdog_result in ("started", "restarted"):
            self.app_status = "running"
        if not admin_active and self.keyboard_filter_suspended_for_admin:
            self.activate_restrictions()
            self._rerender_canvas()
        if not admin_active and not self.admin_dialog_open:
            self._update_allowed_app_window()
        self.root.after(self.watchdog_interval_ms, self._watchdog_tick)

    def _pause_watchdog_for_minimized_app(self):
        allowed_options = getattr(self.launcher.config, "allowed_application", None)
        restore_if_minimized = getattr(allowed_options, "restore_if_minimized", False)
        if restore_if_minimized:
            return False
        app_path = self.launcher.config.app_path
        if not self.app_window_controller.is_minimized(app_path):
            return False
        if self.app_status != "minimized":
            previous_status = self.app_status
            self.app_status = "minimized"
            self.logger.info(
                "shell.app_status_changed",
                previous=previous_status,
                current="minimized",
                app_path=app_path,
            )
            self._rerender_canvas()
        return True

    def _update_allowed_app_window(self):
        app_path = self.launcher.config.app_path
        allowed_options = getattr(self.launcher.config, "allowed_application", None)
        restore_if_minimized = getattr(allowed_options, "restore_if_minimized", False)
        if self.app_status == "minimized" and not restore_if_minimized:
            return

        if self.app_window_controller.is_minimized(app_path):
            if restore_if_minimized:
                if self.app_window_controller.restore(app_path):
                    self.keep_shell_background()
                    next_status = "running"
                else:
                    next_status = "minimized"
            else:
                next_status = "minimized"
        else:
            if hasattr(self.app_window_controller, "ensure_foreground"):
                self.app_window_controller.ensure_foreground(
                    app_path,
                    wait=True,
                    timeout_seconds=5,
                    start_maximized=getattr(
                        getattr(self.launcher.config, "allowed_application", None),
                        "start_maximized",
                        False,
                    ),
                )
            else:
                self.app_window_controller.bring_to_front(app_path)
            self.keep_shell_background()
            next_status = "running"

        if next_status != self.app_status:
            previous_status = self.app_status
            self.app_status = next_status
            self.logger.info(
                "shell.app_status_changed",
                previous=previous_status,
                current=next_status,
                app_path=app_path,
            )
            self._rerender_canvas()

    def start(self):
        self.logger.info("shell.starting")
        self.configure_window()
        try:
            self._watchdog_tick()
            self.root.mainloop()
        finally:
            self.release_restrictions()
            self.logger.info("shell.stopped")


def unlock_desktop(process_factory=None):
    factory = process_factory or subprocess.Popen
    return factory(["explorer.exe"])


def show_admin_error(message):
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror("Режим киоска", message)
    except Exception:
        return False
    return True


def select_allowed_application():
    try:
        import tkinter.filedialog as filedialog

        return filedialog.askopenfilename(
            title="Выберите разрешённое приложение",
            filetypes=(("Windows EXE", "*.exe"), ("Все файлы", "*.*")),
        )
    except Exception:
        return ""


def create_shell_canvas(root):
    import tkinter

    return tkinter.Canvas(
        root,
        bg=SHELL_THEME["background"],
        highlightthickness=0,
        bd=0,
    )


class StyledAdminLoginDialog(object):
    def __init__(self, root):
        self.root = root
        self.result = None

    def ask(self):
        import tkinter

        dialog = tkinter.Toplevel(self.root)
        dialog.title("Режим киоска")
        dialog.configure(bg=SHELL_THEME["panel2"])
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        dialog.geometry(
            scaled_unlock_dialog_geometry(
                dialog.winfo_screenwidth(),
                dialog.winfo_screenheight(),
            )
        )

        frame = tkinter.Frame(
            dialog,
            bg=SHELL_THEME["panel2"],
            highlightbackground="#374151",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True)

        title = tkinter.Label(
            frame,
            text="Вход администратора Windows",
            fg=SHELL_THEME["text"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 15),
            anchor="w",
        )
        title.place(x=34, y=30, width=310, height=30)

        username_label = tkinter.Label(
            frame,
            text="Логин",
            fg=SHELL_THEME["muted"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        )
        username_label.place(x=34, y=72, width=160, height=22)

        username = tkinter.Entry(
            frame,
            **build_login_entry_options(masked=False)
        )
        username.place(x=34, y=98, width=300, height=42)

        password_label = tkinter.Label(
            frame,
            text="Пароль",
            fg=SHELL_THEME["muted"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        )
        password_label.place(x=34, y=152, width=160, height=22)

        password = tkinter.Entry(
            frame,
            **build_login_entry_options(masked=True)
        )
        password.place(x=34, y=178, width=300, height=42)
        username.focus_set()
        try:
            dialog.after(50, username.focus_force)
        except Exception:
            pass

        def accept(event=None):
            self.result = (
                username.get().strip(),
                password.get(),
            )
            dialog.destroy()

        def cancel(event=None):
            self.result = None
            dialog.destroy()

        unlock_button = tkinter.Button(
            frame,
            text="Открыть",
            command=accept,
            fg="#00111f",
            bg=SHELL_THEME["blue"],
            activebackground=SHELL_THEME["blue"],
            activeforeground="#00111f",
            relief="flat",
            font=("Segoe UI", 15),
        )
        unlock_button.place(x=34, y=264, width=132, height=42)

        cancel_button = tkinter.Button(
            frame,
            text="Отмена",
            command=cancel,
            fg=SHELL_THEME["text"],
            bg="#242a31",
            activebackground="#242a31",
            activeforeground=SHELL_THEME["text"],
            relief="flat",
            font=("Segoe UI", 15),
        )
        cancel_button.place(x=184, y=264, width=118, height=42)

        dialog.bind("<Return>", accept)
        dialog.bind("<Escape>", cancel)
        self.root.wait_window(dialog)
        return self.result


StyledPasswordDialog = StyledAdminLoginDialog


class WindowsKeyFilter(object):
    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    WM_QUIT = 0x0012
    VK_L = ord("L")
    VK_TAB = 0x09
    VK_BACK = 0x08
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    VK_ESCAPE = 0x1B
    VK_DELETE = 0x2E
    VK_MENU = 0x12
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_F4 = 0x73
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LMENU = 0xA4
    VK_RMENU = 0xA5

    def __init__(self, lock_workstation=None, logger=None, key_state_checker=None):
        self.lock_workstation = lock_workstation
        self.logger = logger or KioskLogger()
        self.key_state_checker = key_state_checker
        self.thread = None
        self.thread_id = None
        self.hook = None
        self.callback = None
        self.reset_state()

    def reset_state(self):
        self.win_down = False
        self.alt_down = False
        self.ctrl_down = False
        self.shift_down = False

    def should_block_key(self, vk_code, message):
        is_down = message in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN)
        is_up = message in (self.WM_KEYUP, self.WM_SYSKEYUP)
        is_win_key = vk_code in (self.VK_LWIN, self.VK_RWIN)

        if is_win_key:
            if is_down:
                self.win_down = True
                return self._block_shortcut("Win", is_down)
            if is_up:
                self.win_down = False
            return False

        if vk_code in (self.VK_MENU, self.VK_LMENU, self.VK_RMENU):
            self.alt_down = is_down or (self.alt_down and not is_up)
            return False

        if vk_code in (self.VK_CONTROL, self.VK_LCONTROL, self.VK_RCONTROL):
            self.ctrl_down = is_down or (self.ctrl_down and not is_up)
            return False

        if vk_code in (self.VK_SHIFT, self.VK_LSHIFT, self.VK_RSHIFT):
            self.shift_down = is_down or (self.shift_down and not is_up)
            return False

        if not is_down:
            return False

        if self.win_down and not self._is_any_win_key_pressed():
            self.win_down = False
        self._recover_stale_modifier_state()

        alt_pressed = self.alt_down or self._is_any_alt_key_pressed()
        ctrl_pressed = self.ctrl_down or self._is_any_ctrl_key_pressed()

        if self.win_down:
            if is_down and vk_code == self.VK_L:
                self._lock_workstation()
                return self._block_shortcut("Win+L", is_down)
            return self._block_shortcut("Win+{0}".format(self._vk_name(vk_code)), is_down)

        if alt_pressed and vk_code == self.VK_TAB:
            if ctrl_pressed:
                return self._block_shortcut("Ctrl+Alt+Tab", is_down)
            return self._block_shortcut("Alt+Tab", is_down)

        if is_down and alt_pressed and vk_code in (self.VK_ESCAPE, self.VK_F4):
            return self._block_shortcut("Alt+{0}".format(self._vk_name(vk_code)), is_down)

        if is_down and ctrl_pressed and vk_code == self.VK_ESCAPE:
            return self._block_shortcut("Ctrl+Esc", is_down)

        return False

    def _block_shortcut(self, shortcut, is_down=True):
        if is_down:
            try:
                self.logger.warning("keyboard_filter.blocked_shortcut", shortcut=shortcut)
            except Exception:
                pass
        return True

    def _vk_name(self, vk_code):
        names = {
            self.VK_TAB: "Tab",
            self.VK_ESCAPE: "Esc",
            self.VK_F4: "F4",
            self.VK_L: "L",
        }
        if ord("A") <= int(vk_code) <= ord("Z") or ord("0") <= int(vk_code) <= ord("9"):
            return chr(int(vk_code))
        return "VK_{0}".format(vk_code)

    def _is_any_win_key_pressed(self):
        return self._is_key_pressed(self.VK_LWIN) or self._is_key_pressed(self.VK_RWIN)

    def _is_any_alt_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_MENU)
            or self._is_key_pressed(self.VK_LMENU)
            or self._is_key_pressed(self.VK_RMENU)
        )

    def _is_any_ctrl_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_CONTROL)
            or self._is_key_pressed(self.VK_LCONTROL)
            or self._is_key_pressed(self.VK_RCONTROL)
        )

    def _is_any_shift_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_SHIFT)
            or self._is_key_pressed(self.VK_LSHIFT)
            or self._is_key_pressed(self.VK_RSHIFT)
        )

    def _recover_stale_modifier_state(self):
        if not self._has_physical_key_state_source():
            return
        if self.alt_down and not self._is_any_alt_key_pressed():
            self.alt_down = False
        if self.ctrl_down and not self._is_any_ctrl_key_pressed():
            self.ctrl_down = False
        if self.shift_down and not self._is_any_shift_key_pressed():
            self.shift_down = False

    def _has_physical_key_state_source(self):
        return self.key_state_checker is not None or os.name == "nt"

    def _is_key_pressed(self, vk_code):
        if self.key_state_checker is not None:
            try:
                return bool(self.key_state_checker(vk_code))
            except Exception:
                return False
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
        except Exception:
            return False

    def _lock_workstation(self):
        if self.lock_workstation is not None:
            self.lock_workstation()
            return
        if os.name == "nt":
            import ctypes

            ctypes.windll.user32.LockWorkStation()

    def start(self):
        if os.name != "nt":
            return
        if self.thread is not None and self.thread.is_alive():
            return
        self.thread = None
        self.thread_id = None
        self.thread = threading.Thread(
            target=self._message_loop,
            name="PythonKioskWinKeyFilter",
        )
        self.thread.daemon = True
        self.thread.start()
        try:
            self.logger.info("keyboard_filter.started")
        except Exception:
            pass

    def _message_loop(self):
        import ctypes
        from ctypes import wintypes

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", wintypes.POINT),
            ]

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        HOOKPROC = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._configure_hook_api(user32, kernel32, HOOKPROC, MSG)
        self.thread_id = kernel32.GetCurrentThreadId()

        def callback(n_code, w_param, l_param):
            if n_code == self.HC_ACTION:
                try:
                    event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if self.should_block_key(event.vkCode, int(w_param)):
                        return 1
                except Exception as error:
                    self.reset_state()
                    try:
                        self.logger.warning(
                            "keyboard_filter.callback_failed",
                            error=str(error),
                        )
                    except Exception:
                        pass
            return user32.CallNextHookEx(self.hook, n_code, w_param, l_param)

        self.callback = HOOKPROC(callback)
        self.hook = user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            self.callback,
            None,
            0,
        )
        if not self.hook:
            try:
                self.logger.warning(
                    "keyboard_filter.install_failed",
                    error_code=kernel32.GetLastError(),
                )
            except Exception:
                pass
            return

        message = MSG()
        try:
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result <= 0:
                    break
        finally:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None

    def _configure_hook_api(self, user32, kernel32, hook_proc_type, message_type):
        import ctypes
        from ctypes import wintypes

        hook_handle = getattr(wintypes, "HHOOK", wintypes.HANDLE)
        module_handle = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
        result_type = getattr(wintypes, "LRESULT", wintypes.LPARAM)
        try:
            message_pointer = ctypes.POINTER(message_type)
        except TypeError:
            message_pointer = ctypes.c_void_p

        user32.SetWindowsHookExW.restype = hook_handle
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            hook_proc_type,
            module_handle,
            wintypes.DWORD,
        ]
        user32.CallNextHookEx.restype = result_type
        user32.CallNextHookEx.argtypes = [
            hook_handle,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.UnhookWindowsHookEx.argtypes = [hook_handle]
        user32.GetMessageW.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [
            message_pointer,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PostThreadMessageW.restype = wintypes.BOOL
        user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        kernel32.GetLastError.restype = wintypes.DWORD

    def stop(self):
        if os.name != "nt" or self.thread_id is None:
            return
        import ctypes

        ctypes.windll.user32.PostThreadMessageW(
            self.thread_id,
            self.WM_QUIT,
            0,
            0,
        )
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(1.0)
        self.thread = None
        self.thread_id = None
        try:
            self.logger.info("keyboard_filter.stopped")
        except Exception:
            pass


def run_shell(
    launcher,
    tkinter_module=None,
    shell_window_class=ShellWindow,
    keyboard_filter_class=WindowsKeyFilter,
):
    if tkinter_module is None:
        import tkinter as tkinter_module

    root = tkinter_module.Tk()
    kiosk_options = getattr(launcher.config, "kiosk", {})
    keyboard_filter_service = (
        keyboard_filter_class(logger=launcher.logger)
        if os.name == "nt" and bool(kiosk_options.get("blockWinKey", True))
        else None
    )
    shell_window_class(
        root,
        launcher,
        hotkey_service=None,
        keyboard_filter_service=keyboard_filter_service,
        canvas_factory=create_shell_canvas,
        logger=launcher.logger,
    ).start()
