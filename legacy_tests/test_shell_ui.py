# -*- coding: utf-8 -*-

import unittest

from legacy_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_SUCCESS,
    AuthResult,
    MESSAGE_BAD_CREDENTIALS,
)
from legacy_kiosk.shell_ui import (
    LegacyShellWindow,
    build_login_entry_options,
    build_shell_layout,
    login_dialog_geometry,
)


class FakeRoot(object):
    def __init__(self):
        self.scheduled = []

    def after(self, delay, callback):
        self.scheduled.append((delay, callback))

    def winfo_screenwidth(self):
        return 1440

    def winfo_screenheight(self):
        return 900


class FakeKeyboardFilter(object):
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")


class FakeRuntime(object):
    def __init__(self, auth_result=None):
        self.config = {
            "allowedApplication": {
                "path": r"C:\Windows\notepad.exe",
                "startMaximized": False,
                "restoreIfMinimized": False,
            },
            "kiosk": {"adminSessionTimeoutSeconds": 300},
        }
        self.keyboard_filter = FakeKeyboardFilter()
        self.auth_result = auth_result or AuthResult(
            AUTH_SUCCESS, u"Доступ разрешён.", "Admin"
        )
        self.calls = []
        self.minimized = False
        self.watchdog_enabled = True

    def authenticate(self, username, password):
        self.calls.append(("authenticate", username, password))
        return self.auth_result

    def tick_watchdog(self):
        self.calls.append(("tick",))
        return "running"

    def is_allowed_application_minimized(self):
        return self.minimized

    def bring_allowed_application_to_front(self, wait=False):
        self.calls.append(("front", wait))
        return True

    def restore_allowed_application(self):
        self.calls.append(("restore",))
        self.minimized = False
        return True

    def open_desktop(self):
        self.calls.append(("desktop",))

    def stop_supervision(self):
        self.watchdog_enabled = False
        self.calls.append(("stop_supervision",))

    def start_supervision(self):
        self.watchdog_enabled = True
        self.calls.append(("start_supervision",))

    def change_allowed_application(self, path):
        self.config["allowedApplication"]["path"] = path
        self.calls.append(("change_app", path))

    def return_to_kiosk(self):
        self.calls.append(("return_to_kiosk",))


class LegacyShellUiTests(unittest.TestCase):
    def _items(self, **kwargs):
        return dict(
            (item["name"], item)
            for item in build_shell_layout(r"C:\Windows\notepad.exe", **kwargs)
        )

    def test_layout_matches_russian_brand_and_contains_no_hotkey_hint(self):
        items = self._items()
        all_text = u" ".join(
            item.get("text", u"") for item in items.values()
        )

        self.assertEqual(u"РК", items["header_mark_text"]["text"])
        self.assertEqual(u"Режим киоска", items["header_title"]["text"])
        self.assertEqual(u"2026", items["header_year_text"]["text"])
        self.assertEqual(u"Разблокировать", items["unlock_button_text"]["text"])
        self.assertIn(u"Абдрахманов Амаль Даулетович", all_text)
        self.assertNotIn(u"Хоткей", all_text)
        self.assertNotIn(u"Компьютер", all_text)
        self.assertNotIn(u"Домен", all_text)

    def test_minimized_layout_has_notice_and_restore_button(self):
        items = self._items(app_status="minimized")

        self.assertEqual(
            u"Приложение свернуто", items["minimized_alert_text"]["text"]
        )
        self.assertEqual(
            u"Развернуть приложение", items["restore_app_button_text"]["text"]
        )

    def test_admin_layout_has_desktop_watchdog_return_and_change_controls(self):
        items = self._items(admin_session_active=True)

        self.assertEqual(
            u"Открыть рабочий стол", items["unlock_desktop_button_text"]["text"]
        )
        self.assertEqual(
            u"Остановить надзор", items["watchdog_button_text"]["text"]
        )
        self.assertEqual(
            u"Вернуться в киоск", items["return_kiosk_button_text"]["text"]
        )
        self.assertEqual(
            u"Изменить приложение", items["change_app_button_text"]["text"]
        )

    def test_login_entry_shows_username_and_masks_each_password_character(self):
        username_options = build_login_entry_options(masked=False)
        password_options = build_login_entry_options(masked=True)

        self.assertNotIn("show", username_options)
        self.assertEqual("*", password_options["show"])

    def test_unlock_stops_keyboard_filter_before_credentials_and_keeps_it_off_on_success(self):
        runtime = FakeRuntime()
        observations = []

        def credentials():
            observations.extend(runtime.keyboard_filter.calls)
            return "Admin", "secret"

        shell = LegacyShellWindow(
            FakeRoot(), runtime, credential_provider=credentials, clock=lambda: 10
        )

        self.assertTrue(shell.handle_admin_unlock())
        self.assertEqual(["stop"], observations)
        self.assertTrue(shell.admin_session_active)
        self.assertEqual(["stop"], runtime.keyboard_filter.calls)

    def test_failed_unlock_restarts_keyboard_filter(self):
        runtime = FakeRuntime(
            auth_result=AuthResult(
                AUTH_BAD_CREDENTIALS, MESSAGE_BAD_CREDENTIALS, "Admin"
            )
        )
        shell = LegacyShellWindow(
            FakeRoot(),
            runtime,
            credential_provider=lambda: ("Admin", "wrong"),
            error_reporter=lambda message: None,
        )

        self.assertFalse(shell.handle_admin_unlock())
        self.assertEqual(["stop", "start"], runtime.keyboard_filter.calls)
        self.assertFalse(shell.admin_session_active)

    def test_authentication_exception_restarts_keyboard_filter(self):
        runtime = FakeRuntime()

        def fail_authentication(username, password):
            raise RuntimeError("api failure")

        runtime.authenticate = fail_authentication
        errors = []
        shell = LegacyShellWindow(
            FakeRoot(),
            runtime,
            credential_provider=lambda: ("Admin", "secret"),
            error_reporter=errors.append,
        )

        self.assertFalse(shell.handle_admin_unlock())
        self.assertEqual(["stop", "start"], runtime.keyboard_filter.calls)
        self.assertEqual(1, len(errors))

    def test_minimized_watchdog_tick_notifies_without_restoring(self):
        runtime = FakeRuntime()
        runtime.minimized = True
        shell = LegacyShellWindow(FakeRoot(), runtime)

        shell.watchdog_tick()

        self.assertEqual("minimized", shell.app_status)
        self.assertNotIn(("restore",), runtime.calls)

    def test_restore_button_restores_existing_window(self):
        runtime = FakeRuntime()
        runtime.minimized = True
        shell = LegacyShellWindow(FakeRoot(), runtime)
        shell.app_status = "minimized"

        self.assertTrue(shell.handle_restore_app())

        self.assertIn(("restore",), runtime.calls)
        self.assertEqual("running", shell.app_status)

    def test_admin_session_timeout_returns_to_kiosk_and_restarts_filter(self):
        now = [10.0]
        runtime = FakeRuntime()
        shell = LegacyShellWindow(
            FakeRoot(),
            runtime,
            credential_provider=lambda: ("Admin", "secret"),
            clock=lambda: now[0],
        )
        shell.handle_admin_unlock()
        now[0] = 311.0

        shell.watchdog_tick()

        self.assertFalse(shell.admin_session_active)
        self.assertIn(("return_to_kiosk",), runtime.calls)
        self.assertEqual(["stop", "start"], runtime.keyboard_filter.calls)

    def test_admin_buttons_toggle_watchdog_and_change_application(self):
        runtime = FakeRuntime()
        shell = LegacyShellWindow(
            FakeRoot(),
            runtime,
            application_selector=lambda: r"C:\Apps\Custom.exe",
        )
        shell.admin_session_active = True

        self.assertTrue(shell.handle_watchdog_toggle())
        self.assertFalse(runtime.watchdog_enabled)
        self.assertTrue(shell.handle_watchdog_toggle())
        self.assertTrue(runtime.watchdog_enabled)
        self.assertTrue(shell.handle_change_application())
        self.assertEqual(r"C:\Apps\Custom.exe", shell.app_path)

    def test_login_dialog_geometry_stays_inside_small_screen(self):
        geometry = login_dialog_geometry(800, 600)
        width, height, x, y = [int(value) for value in geometry.replace("+", "x").split("x")]

        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x + width, 800)
        self.assertLessEqual(y + height, 600)


if __name__ == "__main__":
    unittest.main()
