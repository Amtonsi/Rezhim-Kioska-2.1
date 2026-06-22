# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ntpath


DESIGN_WIDTH = 1440
DESIGN_HEIGHT = 900

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


def _item(kind, name, rect, **values):
    result = {"kind": kind, "name": name, "rect": tuple(rect)}
    result.update(values)
    return result


def _rect(name, x, y, width, height, fill, outline=None, radius=8):
    return _item("rect", name, (x, y, width, height), fill=fill, outline=outline, radius=radius)


def _text(name, text, x, y, width, height, size, fill, bold=False, anchor="nw"):
    return _item(
        "text",
        name,
        (x, y, width, height),
        text=text,
        size=size,
        fill=fill,
        bold=bool(bold),
        anchor=anchor,
    )


def _button(name, text, action, x, y, width, height, fill, text_fill, outline=None):
    return _item(
        "button",
        name,
        (x, y, width, height),
        text=text,
        action=action,
        fill=fill,
        textFill=text_fill,
        outline=outline,
        size=14,
        bold=True,
        radius=8,
    )


def _application_name(path):
    return ntpath.basename(path) or path


def build_operator_scene(
    application_path,
    app_status="running",
    application_configured=True,
    admin_session_active=False,
    supervision_enabled=True,
    isolation_degraded=False,
):
    application_configured = bool(application_configured)
    minimized = application_configured and app_status == "minimized"
    if application_configured:
        application_name = _application_name(application_path)
        application_path_text = application_path
        status_text = "Свернуто" if minimized else "Работает"
        status_fill = "#3a1616" if minimized else "#0f2f1f"
        status_color = THEME["danger"] if minimized else THEME["ok"]
        supervision_text = "Надзор: включен" if supervision_enabled else "Надзор: остановлен"
        hint_text = "Приложение работает поверх оболочки. При сворачивании появится кнопка возврата."
    else:
        application_name = "Не выбрано"
        application_path_text = "Разрешенное приложение не настроено."
        status_text = "Не настроено"
        status_fill = "#3a1616"
        status_color = THEME["danger"]
        supervision_text = "Надзор: ожидает настройки"
        hint_text = "Разблокируйте режим и выберите разрешенное приложение."
    scene = [
        _item("background", "background", (0, 0, DESIGN_WIDTH, DESIGN_HEIGHT), fill=THEME["background"]),
        _rect("header_mark", 48, 34, 38, 38, "#0f8bd7"),
        _text("header_mark_text", "РК", 48, 34, 38, 38, 11, "#ffffff", True, "center"),
        _text("header_title", "Режим киоска", 100, 39, 168, 34, 16, THEME["text"], True),
        _rect("header_year_badge", 276, 29, 62, 48, "#102126", "#397080"),
        _text("header_year_text", "2026", 276, 29, 62, 48, 10, "#67e8f9", False, "center"),
        _text("header_subtitle", "Режим оператора: Explorer не запущен.", 50, 88, 760, 30, 15, THEME["muted"]),
        _rect("left_panel", 50, 150, 820, 560, THEME["panel"], THEME["line"]),
        _text("allowed_title", "Разрешенное приложение", 92, 190, 650, 44, 26, THEME["text"], True),
        _text("allowed_subtitle", "Запущено только настроенное приложение.", 94, 238, 650, 30, 15, THEME["muted"]),
        _rect("application_card", 95, 300, 690, 250, "#0b1220", "#1d4ed8"),
        _text("application_name", application_name, 135, 344, 600, 58, 34, THEME["text"], True),
        _text("application_path", application_path_text, 138, 410, 600, 32, 13, THEME["muted"]),
        _rect("application_status_pill", 135, 478, 190, 44, status_fill, None, 8),
        _text("application_status", status_text, 154, 486, 150, 28, 15, status_color),
        _rect("supervision_status_pill", 345, 478, 270, 44, "#122033", None, 8),
        _text("supervision_status", supervision_text, 372, 486, 220, 28, 15, THEME["accent"]),
        _rect("right_panel", 920, 150, 470, 560, THEME["panel"], THEME["line"]),
        _text("admin_title", "Разблокировка", 955, 190, 360, 44, 26, THEME["text"], True),
        _rect("safety_strip", 50, 760, 1340, 86, "#101010", "#27272a"),
        _text("safety_title", "Модель безопасности", 82, 782, 260, 28, 15, THEME["text"]),
        _text(
            "safety_message",
            "Защита ограничена: Explorer обнаружен. Вернитесь в киоск после устранения причины."
            if isolation_degraded
            else "Win+L остается доступен. Службы, драйверы, процессы и автозагрузка не трогаются.",
            82,
            815,
            1160,
            28,
            14,
            THEME["danger"] if isolation_degraded else THEME["muted"],
            isolation_degraded,
        ),
        _text("policy_note", "Политики применяются только к отдельной операторской УЗ.", 760, 782, 560, 28, 14, THEME["muted"]),
        _text(
            "developer_credit",
            "разработал: Абдрахманов Амаль Даулетович",
            870,
            858,
            520,
            28,
            12,
            "#6b7280",
            False,
            "ne",
        ),
    ]
    if minimized:
        scene.extend(
            [
                _text("minimized_alert", "Приложение свернуто", 135, 570, 400, 30, 15, THEME["danger"], True),
                _button("restore_application_button", "Развернуть приложение", "restoreApplication", 135, 615, 255, 46, THEME["blue"], "#00111f"),
            ]
        )
    else:
        scene.append(
            _text(
                "application_hint",
                hint_text,
                94,
                586,
                720,
                54,
                15,
                THEME["muted"],
            )
        )
    if admin_session_active:
        scene.extend(_admin_session_items(supervision_enabled, application_configured))
    else:
        scene.extend(
            [
                _button("unlock_button", "Разблокировать", "unlock", 958, 284, 250, 54, THEME["blue"], "#00111f"),
                _text("unlock_hint", "Нажмите кнопку для входа администратора.", 958, 360, 360, 58, 13, THEME["muted"]),
                _text("unlock_result_hint", "После успешной проверки откроется ограниченная админ-сессия.", 958, 620, 360, 58, 12, THEME["muted"]),
            ]
        )
    return scene


def _admin_session_items(supervision_enabled, application_configured=True):
    items = [
        _text("admin_session_title", "Админ-сессия активна", 958, 248, 350, 30, 15, THEME["ok"], True),
        _button("unlock_desktop_button", "Открыть рабочий стол", "unlockDesktop", 958, 292, 250, 46, THEME["blue"], "#00111f"),
    ]
    if application_configured:
        items.append(_button(
            "toggle_supervision_button",
            "Остановить надзор" if supervision_enabled else "Запустить надзор",
            "toggleSupervision",
            958,
            350,
            250,
            46,
            "#242a31" if supervision_enabled else THEME["blue"],
            THEME["text"] if supervision_enabled else "#00111f",
        ))
    items.extend([
        _button("return_to_kiosk_button", "Вернуться в киоск", "returnToKiosk", 958, 408, 250, 46, "#101820", THEME["accent"], "#374151"),
        _button("change_application_button", "Изменить приложение", "changeApplication", 958, 466, 250, 46, "#242a31", THEME["text"]),
        _button("restore_button", "Восстановить Windows", "restore", 958, 524, 250, 46, "#3a1616", THEME["danger"], "#7f1d1d"),
        _text("admin_timeout_hint", "Админ-сессия завершится автоматически по таймауту.", 958, 590, 360, 56, 12, THEME["muted"]),
    ])
    return items


def build_dialog_spec():
    return {
        "title": "Вход администратора Windows",
        "message": "Введите данные локальной учетной записи администратора.",
        "modal": True,
        "keepKeyboardGuard": True,
        "fields": [
            {"name": "username", "label": "Пользователь", "show": ""},
            {"name": "password", "label": "Пароль", "show": "*"},
        ],
        "acceptText": "ОК",
        "cancelText": "Отмена",
    }
