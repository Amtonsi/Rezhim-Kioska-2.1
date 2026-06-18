try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.shell_ui import (
    SHELL_THEME,
    ShellWindow,
    StyledPasswordDialog,
    WindowsKeyFilter,
    build_login_entry_options,
    build_shell_layout,
    build_unlock_dialog_layout,
    combine_windows_account_name,
    scaled_unlock_dialog_geometry,
    run_shell,
    unlock_desktop,
)
from python_kiosk.security import FailedAttemptLimiter


class FakeRoot(object):
    def __init__(self):
        self.attributes_calls = []
        self.protocol_calls = []
        self.bind_calls = []
        self.after_calls = []
        self.config_values = {}
        self.title_value = None
        self.mainloop_called = False
        self.destroy_called = False
        self.screen_width = 1440
        self.screen_height = 900
        self.state_calls = []
        self.deiconify_called = False
        self.lift_called = False
        self.focus_force_called = False
        self.lower_called = False

    def title(self, value):
        self.title_value = value

    def configure(self, **kwargs):
        self.config_values.update(kwargs)

    def attributes(self, name, value):
        self.attributes_calls.append((name, value))

    def protocol(self, name, callback):
        self.protocol_calls.append((name, callback))

    def bind(self, event, callback):
        self.bind_calls.append((event, callback))

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))

    def mainloop(self):
        self.mainloop_called = True

    def destroy(self):
        self.destroy_called = True

    def state(self, value):
        self.state_calls.append(value)

    def deiconify(self):
        self.deiconify_called = True

    def lift(self):
        self.lift_called = True

    def focus_force(self):
        self.focus_force_called = True

    def lower(self):
        self.lower_called = True

    def winfo_screenwidth(self):
        return self.screen_width

    def winfo_screenheight(self):
        return self.screen_height


class FakeTkFactory(object):
    def __init__(self):
        self.root = FakeRoot()

    def Tk(self):
        return self.root


class FakeCanvas(object):
    def __init__(self):
        self.pack_calls = []
        self.configure_calls = []
        self.bind_calls = []
        self.rectangle_calls = []
        self.polygon_calls = []
        self.text_calls = []
        self.tag_bind_calls = []
        self.tag_configs = []

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def bind(self, event, callback):
        self.bind_calls.append((event, callback))

    def tag_bind(self, tag, event, callback):
        self.tag_bind_calls.append((tag, event, callback))

    def tag_configure(self, tag, **kwargs):
        self.tag_configs.append((tag, kwargs))

    def delete(self, tag):
        pass

    def create_rectangle(self, *args, **kwargs):
        self.rectangle_calls.append((args, kwargs))

    def create_polygon(self, *args, **kwargs):
        self.polygon_calls.append((args, kwargs))

    def create_text(self, *args, **kwargs):
        self.text_calls.append((args, kwargs))


class FakeWatchdog(object):
    def __init__(self, actions):
        self.actions = list(actions)
        self.tick_count = 0
        self.stop_called = False

    def tick(self):
        self.tick_count += 1
        return self.actions.pop(0) if self.actions else "running"

    def stop(self):
        self.stop_called = True


class FakeLauncher(object):
    def __init__(self, watchdog, restore_if_minimized=False):
        self.watchdog = watchdog
        self.unlock_attempts = []
        self.changed_app_paths = []
        self.config = type(
            "Config",
            (),
            {
                "app_path": r"C:\Program Files\Vendor\App\VendorApp.exe",
                "kiosk": {"blockDesktop": True},
                "allowed_application": type(
                    "Allowed",
                    (),
                    {
                        "start_maximized": False,
                        "restore_if_minimized": restore_if_minimized,
                    },
                )(),
            },
        )()
        self.logger = FakeLogger()

    def create_watchdog(self):
        return self.watchdog

    def verify_admin_password(self, password):
        self.unlock_attempts.append(password)
        return password == "admin-pass"

    def verify_admin_credentials(self, username, password):
        self.unlock_attempts.append((username, password))
        return username == "Admin" and password == "secret"

    def set_allowed_application_path(self, app_path):
        self.changed_app_paths.append(app_path)
        self.config.app_path = app_path
        return True


class SequenceLauncher(FakeLauncher):
    def __init__(self, watchdogs, restore_if_minimized=False):
        self.watchdogs = list(watchdogs)
        self.created_watchdogs = []
        super(SequenceLauncher, self).__init__(self.watchdogs[0], restore_if_minimized)

    def create_watchdog(self):
        watchdog = self.watchdogs.pop(0)
        self.created_watchdogs.append(watchdog)
        return watchdog


class FakeHotkeyService(object):
    def __init__(self):
        self.started = []
        self.stopped = []

    def start(self, root, callback):
        self.started.append((root, callback))

    def stop(self):
        self.stopped.append("stopped")


class FakeKeyboardFilterService(object):
    def __init__(self):
        self.started = []
        self.stopped = []
        self.reset_calls = []

    def start(self):
        self.started.append("started")

    def stop(self):
        self.stopped.append("stopped")

    def reset_state(self):
        self.reset_calls.append("reset")


class FakeSessionLockdown(object):
    def __init__(self):
        self.activated = []
        self.released = []

    def activate_operator_mode(self):
        self.activated.append("activated")
        return {"closed_explorer": True}

    def release_operator_mode(self):
        self.released.append("released")
        return {"restored_windows": []}


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class FakeAppWindowController(object):
    def __init__(self, minimized=False):
        self.minimized = minimized
        self.calls = []

    def is_minimized(self, app_path):
        self.calls.append(("is_minimized", app_path))
        return self.minimized

    def bring_to_front(self, app_path):
        self.calls.append(("bring_to_front", app_path))
        return True

    def ensure_foreground(self, app_path, **kwargs):
        self.calls.append(("ensure_foreground", app_path))
        self.calls.append(("ensure_foreground_kwargs", kwargs))
        return True

    def restore(self, app_path):
        self.calls.append(("restore", app_path))
        self.minimized = False
        return True

    def release_topmost(self, app_path):
        self.calls.append(("release_topmost", app_path))
        return True


class ShellWindowTests(unittest.TestCase):
    def test_shell_layout_matches_approved_mockup_structure(self):
        layout = build_shell_layout(r"C:\Program Files\Vendor\App\VendorApp.exe")
        by_name = dict((item["name"], item) for item in layout)

        self.assertEqual("#050505", by_name["background"]["fill"])
        self.assertEqual((50, 150, 820, 560, 14), by_name["left_panel"]["rect"])
        self.assertEqual((920, 150, 470, 560, 14), by_name["right_panel"]["rect"])
        self.assertEqual((50, 760, 1340, 86, 12), by_name["safety_strip"]["rect"])
        self.assertEqual("Режим киоска", by_name["header_title"]["text"])
        self.assertEqual("VendorApp.exe", by_name["app_name"]["text"])
        self.assertEqual("Надзор: включен", by_name["watchdog_status"]["text"])
        self.assertEqual("Разблокировать", by_name["unlock_button_text"]["text"])
        self.assertIn("Win+L остается доступен", by_name["safety_message"]["text"])
        self.assertEqual(
            "разработал: Абдрахманов Амаль Даулетович",
            by_name["developer_credit"]["text"],
        )
        self.assertEqual("#6b7280", by_name["developer_credit"]["fill"])

    def test_shell_layout_shows_stopped_watchdog_state(self):
        layout = build_shell_layout(
            r"C:\Program Files\Vendor\App\VendorApp.exe",
            watchdog_enabled=False,
        )
        by_name = dict((item["name"], item) for item in layout)

        self.assertEqual("Надзор: остановлен", by_name["watchdog_status"]["text"])
        self.assertEqual(SHELL_THEME["muted"], by_name["watchdog_status"]["fill"])

    def test_unlock_dialog_layout_matches_approved_mockup(self):
        layout = build_unlock_dialog_layout()
        by_name = dict((item["name"], item) for item in layout)

        self.assertEqual((965, 270, 380, 350, 12), by_name["unlock_dialog"]["rect"])
        self.assertEqual("Вход администратора Windows", by_name["unlock_title"]["text"])
        self.assertEqual((1000, 391, 300, 42, 8), by_name["username_input"]["rect"])
        self.assertNotIn("domain_label", by_name)
        self.assertNotIn("domain_input", by_name)
        self.assertEqual((1000, 458, 300, 42, 8), by_name["password_input"]["rect"])
        self.assertEqual("#0ea5e9", by_name["unlock_button"]["fill"])
        self.assertEqual("Отмена", by_name["cancel_button_text"]["text"])
        self.assertEqual("#38bdf8", SHELL_THEME["accent"])

    def test_combine_windows_account_name_uses_domain_field_when_present(self):
        self.assertEqual("Admin", combine_windows_account_name("Admin", ""))
        self.assertEqual(".\\Admin", combine_windows_account_name("Admin", "."))
        self.assertEqual("PC\\Admin", combine_windows_account_name("Admin", "PC"))
        self.assertEqual("PC\\Admin", combine_windows_account_name("PC\\Admin", "OTHER"))

    def test_login_entry_options_make_typed_input_visible_and_mask_password(self):
        username_options = build_login_entry_options(masked=False)
        password_options = build_login_entry_options(masked=True)

        self.assertEqual(SHELL_THEME["text"], username_options["fg"])
        self.assertNotIn("show", username_options)
        self.assertEqual(SHELL_THEME["text"], password_options["fg"])
        self.assertEqual("*", password_options["show"])

    def test_unlock_dialog_geometry_uses_mockup_position(self):
        geometry = scaled_unlock_dialog_geometry(1440, 900)

        self.assertEqual("380x350+965+270", geometry)

    def test_configure_window_renders_design_to_canvas(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
        )
        shell.configure_window()

        rendered_text = [call[1]["text"] for call in canvas.text_calls]
        self.assertEqual([{"fill": "both", "expand": True}], canvas.pack_calls)
        self.assertIn("VendorApp.exe", rendered_text)
        self.assertIn("Режим киоска", rendered_text)
        self.assertIn("разработал: Абдрахманов Амаль Даулетович", rendered_text)
        self.assertNotIn("Пароль администратора", rendered_text)
        self.assertNotIn("Отмена", rendered_text)
        self.assertTrue(canvas.polygon_calls)

    def test_canvas_unlock_button_is_clickable(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("unlock"),
            canvas_factory=lambda parent: canvas,
        )

        shell.configure_window()
        unlock_bindings = [
            call for call in canvas.tag_bind_calls if call[0] == "unlock_click" and call[1] in ("<Button-1>", "<ButtonPress-1>")
        ]
        self.assertEqual(1, len(unlock_bindings))
        self.assertEqual("<Button-1>", unlock_bindings[0][1])

        unlock_bindings[0][2](None)

        self.assertEqual([], unlock_calls)
        self.assertTrue(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_default_password_provider_uses_styled_dialog(self):
        root = FakeRoot()
        dialog = type("Dialog", (), {"ask": lambda self: ("Admin", "secret")})()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(
            root,
            launcher,
            credential_dialog_factory=lambda parent: dialog,
        )

        self.assertEqual(("Admin", "secret"), shell._default_credential_provider())

    def test_shell_configures_fullscreen_background_and_blocks_close(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))
        shell.configure_window()

        self.assertIn(("-fullscreen", True), root.attributes_calls)
        self.assertNotIn(("-topmost", True), root.attributes_calls)
        self.assertEqual("Режим киоска", root.title_value)
        self.assertEqual(SHELL_THEME["background"], root.config_values["bg"])
        self.assertEqual("WM_DELETE_WINDOW", root.protocol_calls[0][0])
        self.assertEqual(["<FocusOut>", "<Unmap>"], [call[0] for call in root.bind_calls])

    def test_focus_guard_restores_fullscreen_window(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))

        shell.enforce_shell_focus()

        self.assertIn("normal", root.state_calls)
        self.assertTrue(root.deiconify_called)
        self.assertFalse(root.lift_called)
        self.assertFalse(root.focus_force_called)
        self.assertIn(("-fullscreen", True), root.attributes_calls)
        self.assertNotIn(("-topmost", True), root.attributes_calls)

    def test_focus_guard_tick_keeps_shell_behind_running_allowed_app(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._focus_guard_tick()

        self.assertEqual([], root.state_calls)
        self.assertFalse(root.deiconify_called)
        self.assertNotIn(("-fullscreen", True), root.attributes_calls)
        self.assertTrue(root.lower_called)

    def test_focus_guard_tick_does_not_cover_admin_session_windows(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Admin", "secret"))
        shell.handle_admin_unlock()

        root.state_calls = []
        root.deiconify_called = False
        root.attributes_calls = []
        root.lower_called = False
        shell._focus_guard_tick()

        self.assertEqual([], root.state_calls)
        self.assertFalse(root.deiconify_called)
        self.assertNotIn(("-fullscreen", True), root.attributes_calls)
        self.assertTrue(root.lower_called)

    def test_admin_unlock_lowers_background_before_modal_dialog(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))

        def credential_provider():
            self.assertTrue(root.lower_called)
            return None

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=credential_provider,
        )

        self.assertFalse(shell.handle_admin_unlock())

    def test_shell_does_not_start_global_hotkey_service(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        hotkey_service = FakeHotkeyService()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            hotkey_service=hotkey_service,
        )
        shell.configure_window()

        self.assertEqual([], hotkey_service.started)

    def test_shell_starts_windows_key_filter_when_present(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        keyboard_filter_service = FakeKeyboardFilterService()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        self.assertEqual(["started"], keyboard_filter_service.started)

    def test_shell_activates_operator_session_lockdown_on_start(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        session_lockdown = FakeSessionLockdown()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            session_lockdown=session_lockdown,
        )
        shell.configure_window()

        self.assertEqual(["activated"], session_lockdown.activated)

    def test_start_ticks_watchdog_and_schedules_next_tick(self):
        root = FakeRoot()
        watchdog = FakeWatchdog(["started"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))

        shell.start()

        self.assertEqual(1, watchdog.tick_count)
        self.assertEqual((2000, shell._watchdog_tick), root.after_calls[-1])
        self.assertTrue(root.mainloop_called)

    def test_start_releases_restrictions_when_mainloop_returns(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        session_lockdown = FakeSessionLockdown()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
            session_lockdown=session_lockdown,
        )

        shell.start()

        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertEqual(["released"], session_lockdown.released)

    def test_admin_button_opens_admin_session_after_windows_admin_password(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("unlock"),
        )

        shell.handle_admin_unlock()

        self.assertEqual([("Admin", "secret")], launcher.unlock_attempts)
        self.assertEqual([], unlock_calls)
        self.assertTrue(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_admin_unlock_resets_keyboard_filter_before_dialog(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()

        def credential_provider():
            self.assertEqual(["reset"], keyboard_filter_service.reset_calls)
            self.assertEqual(["stopped"], keyboard_filter_service.stopped)
            return None

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=credential_provider,
            keyboard_filter_service=keyboard_filter_service,
        )

        self.assertFalse(shell.handle_admin_unlock())
        self.assertEqual(["started"], keyboard_filter_service.started)

    def test_successful_admin_unlock_temporarily_stops_keyboard_filter(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        self.assertEqual(["started"], keyboard_filter_service.started)

        shell.handle_admin_unlock()

        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertTrue(shell.admin_session.is_active())

        shell.handle_return_to_kiosk()

        self.assertEqual(["started", "started"], keyboard_filter_service.started)

    def test_failed_admin_unlock_keeps_keyboard_filter_active(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        shell.handle_admin_unlock()

        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertFalse(shell.admin_session.is_active())
        self.assertEqual(["started", "started"], keyboard_filter_service.started)

    def test_admin_session_unlock_desktop_stops_restrictions_and_launches_explorer(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        hotkey_service = FakeHotkeyService()
        keyboard_filter_service = FakeKeyboardFilterService()
        app_windows = FakeAppWindowController()
        session_lockdown = FakeSessionLockdown()
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("explorer"),
            hotkey_service=hotkey_service,
            keyboard_filter_service=keyboard_filter_service,
            app_window_controller=app_windows,
            session_lockdown=session_lockdown,
        )

        shell.handle_admin_unlock()
        shell.handle_unlock_desktop()

        self.assertEqual(["stopped"], hotkey_service.stopped)
        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertEqual(["released"], shell.session_lockdown.released)
        self.assertIn(("release_topmost", launcher.config.app_path), app_windows.calls)
        self.assertEqual(["explorer"], unlock_calls)
        self.assertFalse(root.destroy_called)

    def test_admin_session_can_stop_watchdog(self):
        root = FakeRoot()
        watchdog = FakeWatchdog(["running"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
        )
        shell._watchdog_tick()
        shell.handle_admin_unlock()

        shell.handle_stop_watchdog()

        self.assertTrue(watchdog.stop_called)
        self.assertTrue(shell.watchdog_disabled)

    def test_stop_watchdog_rerenders_disabled_state(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        watchdog = FakeWatchdog(["running"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            canvas_factory=lambda parent: canvas,
        )
        shell.configure_window()
        shell._watchdog_tick()
        shell.handle_admin_unlock()
        canvas.text_calls = []

        shell.handle_stop_watchdog()

        rendered_text = [call[1]["text"] for call in canvas.text_calls]
        self.assertIn("Надзор: остановлен", rendered_text)

    def test_watchdog_tick_does_not_force_allowed_app_above_admin_session(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            app_window_controller=app_windows,
        )
        shell.handle_admin_unlock()

        root.lower_called = False
        shell._watchdog_tick()

        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertFalse(root.lower_called)

    def test_return_to_kiosk_closes_admin_session(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
        )
        shell.handle_admin_unlock()

        shell.handle_return_to_kiosk()

        self.assertFalse(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_bad_admin_credentials_do_not_unlock(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            unlock_action=lambda: unlock_calls.append("unlock"),
        )

        shell.handle_admin_unlock()

        self.assertEqual([("Operator", "bad")], launcher.unlock_attempts)
        self.assertEqual([], unlock_calls)
        self.assertFalse(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_bad_admin_credentials_are_logged_and_delayed(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        logger = FakeLogger()
        sleep_calls = []
        errors = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "secret-pass-should-not-log"),
            unlock_action=lambda: None,
            failed_attempt_limiter=FailedAttemptLimiter(
                threshold=1,
                base_delay_seconds=4,
                max_delay_seconds=4,
            ),
            sleep_func=lambda seconds: sleep_calls.append(seconds),
            logger=logger,
            error_reporter=lambda message: errors.append(message),
        )

        shell.handle_admin_unlock()

        self.assertEqual([4], sleep_calls)
        self.assertIn(("warning", "admin.unlock_denied"), [(level, event) for level, event, _ in logger.events])
        logged_text = str(logger.events)
        self.assertIn("bad_credentials", logged_text)
        self.assertNotIn("secret-pass-should-not-log", logged_text)
        self.assertEqual(1, len(errors))
        self.assertIn("Отказано", errors[0])

    def test_admin_session_can_change_allowed_application_path(self):
        root = FakeRoot()
        watchdog = FakeWatchdog(["running"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            allowed_app_selector=lambda: r"C:\Windows\System32\notepad.exe",
        )
        shell.handle_admin_unlock()

        self.assertTrue(shell.handle_change_allowed_app())

        self.assertEqual([r"C:\Windows\System32\notepad.exe"], launcher.changed_app_paths)
        self.assertIs(watchdog, shell.watchdog)
        self.assertEqual(1, watchdog.tick_count)

    def test_changing_app_reenables_watchdog_and_starts_new_application(self):
        root = FakeRoot()
        old_watchdog = FakeWatchdog(["running"])
        new_watchdog = FakeWatchdog(["started"])
        launcher = SequenceLauncher([old_watchdog, new_watchdog])
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            allowed_app_selector=lambda: r"C:\Program Files\App\NewApp.exe",
        )
        shell._watchdog_tick()
        shell.handle_admin_unlock()
        shell.handle_stop_watchdog()

        self.assertTrue(shell.handle_change_allowed_app())

        self.assertFalse(shell.watchdog_disabled)
        self.assertIs(new_watchdog, shell.watchdog)
        self.assertEqual(1, new_watchdog.tick_count)
        self.assertEqual("running", shell.app_status)

    def test_return_to_kiosk_after_stopping_watchdog_starts_fresh_watchdog(self):
        root = FakeRoot()
        old_watchdog = FakeWatchdog(["running"])
        new_watchdog = FakeWatchdog(["started"])
        launcher = SequenceLauncher([old_watchdog, new_watchdog])
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
        )
        shell._watchdog_tick()
        shell.handle_admin_unlock()
        shell.handle_stop_watchdog()

        shell.handle_return_to_kiosk()
        shell._watchdog_tick()

        self.assertIs(new_watchdog, shell.watchdog)
        self.assertEqual(1, new_watchdog.tick_count)

    def test_admin_session_layout_has_change_application_button(self):
        layout = build_shell_layout(
            r"C:\Program Files\Vendor\App\VendorApp.exe",
            admin_session_active=True,
        )
        by_name = dict((item["name"], item) for item in layout)

        self.assertIn("change_app_button", by_name)
        self.assertEqual("Изменить приложение", by_name["change_app_button_text"]["text"])

    def test_watchdog_tick_marks_minimized_app_and_renders_restore_button(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=True)
        logger = FakeLogger()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
            app_window_controller=app_windows,
            logger=logger,
        )
        shell.configure_window()

        shell._watchdog_tick()

        rendered_text = [call[1]["text"] for call in canvas.text_calls]
        self.assertIn("Свернуто", rendered_text)
        self.assertIn("Развернуть приложение", rendered_text)
        self.assertIn(
            ("info", "shell.app_status_changed"),
            [(level, event) for level, event, _ in logger.events],
        )
        self.assertNotIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_watchdog_tick_restores_minimized_allowed_app_when_configured(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]), restore_if_minimized=True)
        app_windows = FakeAppWindowController(minimized=True)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._watchdog_tick()

        self.assertIn(("restore", launcher.config.app_path), app_windows.calls)
        self.assertEqual("running", shell.app_status)
        self.assertTrue(root.lower_called)

    def test_watchdog_tick_does_not_steal_focus_while_admin_dialog_is_open(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.admin_dialog_open = True

        shell._watchdog_tick()

        self.assertEqual(0, launcher.watchdog.tick_count)
        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertFalse(root.lower_called)

    def test_watchdog_tick_does_not_restart_minimized_app_until_restore_button(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["restarted"]))
        app_windows = FakeAppWindowController(minimized=True)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._watchdog_tick()

        self.assertEqual(0, launcher.watchdog.tick_count)
        self.assertEqual("minimized", shell.app_status)
        self.assertNotIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_minimized_app_stays_minimized_until_restore_button(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.app_status = "minimized"

        shell._watchdog_tick()

        self.assertEqual("minimized", shell.app_status)
        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertNotIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_watchdog_restart_resets_minimized_status(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["restarted"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.app_status = "minimized"

        shell._watchdog_tick()

        self.assertEqual("running", shell.app_status)
        self.assertIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)

    def test_minimized_layout_separates_notification_from_restore_button(self):
        layout = build_shell_layout(
            r"C:\Program Files\Vendor\App\VendorApp.exe",
            app_status="minimized",
        )
        by_name = dict((item["name"], item) for item in layout)

        self.assertIn("minimized_alert", by_name)
        self.assertEqual((135, 558, 520, 42, 8), by_name["minimized_alert"]["rect"])
        self.assertEqual((135, 615, 255, 44, 8), by_name["restore_app_button"]["rect"])

    def test_watchdog_tick_keeps_allowed_app_foreground_above_shell(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._watchdog_tick()

        self.assertIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertNotIn(("bring_to_front", launcher.config.app_path), app_windows.calls)
        self.assertTrue(root.lower_called)

    def test_restore_button_restores_allowed_application(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=True)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
            app_window_controller=app_windows,
        )
        shell.configure_window()
        shell._watchdog_tick()
        restore_bindings = [
            call for call in canvas.tag_bind_calls if call[0] == "restore_app_click" and call[1] == "<Button-1>"
        ]

        self.assertEqual(1, len(restore_bindings))
        restore_bindings[0][2](None)

        self.assertIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_unlock_desktop_launches_explorer(self):
        calls = []

        unlock_desktop(process_factory=lambda command: calls.append(command))

        self.assertEqual([["explorer.exe"]], calls)

    def test_windows_key_filter_blocks_win_key_and_allows_win_l_lock(self):
        lock_calls = []
        key_filter = WindowsKeyFilter(
            lock_workstation=lambda: lock_calls.append("lock"),
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.VK_RWIN),
        )

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_LWIN,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertTrue(
            key_filter.should_block_key(
                ord("D"),
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertEqual([], lock_calls)

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_L,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertEqual(["lock"], lock_calls)

        self.assertFalse(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_LWIN,
                WindowsKeyFilter.WM_KEYUP,
            )
        )
        self.assertFalse(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_L,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )

    def test_windows_key_filter_blocks_required_win_shortcuts(self):
        for vk_code in [ord("R"), ord("E"), ord("X"), ord("S"), ord("D"), ord("M"), WindowsKeyFilter.VK_TAB]:
            key_filter = WindowsKeyFilter(
                key_state_checker=lambda key: key
                in (WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.VK_RWIN)
            )
            self.assertTrue(
                key_filter.should_block_key(
                    WindowsKeyFilter.VK_LWIN,
                    WindowsKeyFilter.WM_KEYDOWN,
                )
            )
            self.assertTrue(
                key_filter.should_block_key(vk_code, WindowsKeyFilter.WM_KEYDOWN)
            )

    def test_windows_key_filter_blocks_task_switching_shortcuts(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_F4, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.VK_LCONTROL)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (
                WindowsKeyFilter.VK_CONTROL,
                WindowsKeyFilter.VK_LCONTROL,
                WindowsKeyFilter.VK_SHIFT,
                WindowsKeyFilter.VK_LSHIFT,
            )
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_SHIFT, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_blocks_ctrl_alt_tab_switcher(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (
                WindowsKeyFilter.VK_CONTROL,
                WindowsKeyFilter.VK_LCONTROL,
                WindowsKeyFilter.VK_MENU,
                WindowsKeyFilter.VK_LMENU,
            )
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYUP))

    def test_windows_key_filter_never_blocks_keyup_events(self):
        key_filter = WindowsKeyFilter()

        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.WM_KEYDOWN))

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.WM_KEYUP))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_SYSKEYUP))

    def test_windows_key_filter_fails_open_when_physical_key_state_is_unavailable(self):
        def broken_key_state(_vk_code):
            raise OSError("GetAsyncKeyState failed")

        key_filter = WindowsKeyFilter(key_state_checker=broken_key_state)
        key_filter.win_down = True

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.win_down)

    def test_windows_key_filter_blocks_alt_f4_when_alt_is_physically_down(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda key: key
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_F4,
                WindowsKeyFilter.WM_SYSKEYDOWN,
            )
        )

    def test_windows_key_filter_passes_normal_text_and_dialog_input_keys(self):
        for vk_code in [
            ord("A"),
            ord("Z"),
            ord("0"),
            WindowsKeyFilter.VK_SPACE,
            WindowsKeyFilter.VK_BACK,
            WindowsKeyFilter.VK_DELETE,
            WindowsKeyFilter.VK_RETURN,
            WindowsKeyFilter.VK_TAB,
        ]:
            key_filter = WindowsKeyFilter()
            self.assertFalse(
                key_filter.should_block_key(vk_code, WindowsKeyFilter.WM_KEYDOWN),
                "vk {0} must pass through".format(vk_code),
            )

    def test_windows_key_filter_recovers_from_stale_win_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.win_down = True

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.win_down)

    def test_windows_key_filter_recovers_from_stale_alt_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.alt_down = True

        self.assertFalse(
            key_filter.should_block_key(WindowsKeyFilter.VK_F4, WindowsKeyFilter.WM_SYSKEYDOWN)
        )
        self.assertFalse(key_filter.alt_down)

    def test_windows_key_filter_recovers_from_stale_ctrl_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.ctrl_down = True

        self.assertFalse(
            key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN)
        )
        self.assertFalse(key_filter.ctrl_down)

    def test_windows_key_filter_allows_regular_ctrl_alt_shift_k_input(self):
        key_filter = WindowsKeyFilter()

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_SHIFT, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(ord("K"), WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_tracks_left_and_right_modifier_keys(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code == WindowsKeyFilter.VK_LMENU
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_LMENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code == WindowsKeyFilter.VK_RCONTROL
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_RCONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_logs_only_blocked_shortcuts_not_text_input(self):
        logger = FakeLogger()
        key_filter = WindowsKeyFilter(
            logger=logger,
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU),
        )

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertEqual([], logger.events)

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        self.assertIn(
            ("warning", "keyboard_filter.blocked_shortcut"),
            [(level, event) for level, event, _ in logger.events],
        )
        logged_text = str(logger.events)
        self.assertIn("Alt+Tab", logged_text)
        self.assertNotIn("'A'", logged_text)

    def test_windows_key_filter_configures_64bit_safe_hook_api_signatures(self):
        class FakeFunction(object):
            def __init__(self):
                self.restype = None
                self.argtypes = None

        class FakeUser32(object):
            def __init__(self):
                self.SetWindowsHookExW = FakeFunction()
                self.CallNextHookEx = FakeFunction()
                self.UnhookWindowsHookEx = FakeFunction()
                self.GetMessageW = FakeFunction()
                self.PostThreadMessageW = FakeFunction()

        class FakeKernel32(object):
            def __init__(self):
                self.GetCurrentThreadId = FakeFunction()
                self.GetLastError = FakeFunction()

        key_filter = WindowsKeyFilter()
        user32 = FakeUser32()
        kernel32 = FakeKernel32()

        key_filter._configure_hook_api(user32, kernel32, object, object)

        self.assertIsNotNone(user32.SetWindowsHookExW.restype)
        self.assertIsNotNone(user32.SetWindowsHookExW.argtypes)
        self.assertIsNotNone(user32.CallNextHookEx.restype)
        self.assertIsNotNone(user32.CallNextHookEx.argtypes)
        self.assertIsNotNone(user32.UnhookWindowsHookEx.restype)
        self.assertIsNotNone(user32.UnhookWindowsHookEx.argtypes)
        self.assertIsNotNone(user32.GetMessageW.restype)
        self.assertIsNotNone(user32.GetMessageW.argtypes)
        self.assertIsNotNone(user32.PostThreadMessageW.restype)
        self.assertIsNotNone(user32.PostThreadMessageW.argtypes)
        self.assertIsNotNone(kernel32.GetCurrentThreadId.restype)
        self.assertIsNotNone(kernel32.GetLastError.restype)

    def test_run_shell_passes_launcher_logger_to_shell_and_keyboard_filter(self):
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        created = {}

        class FakeFilter(object):
            def __init__(self, logger=None, **kwargs):
                created["filter_logger"] = logger

            def start(self):
                pass

            def stop(self):
                pass

        class FakeShell(object):
            def __init__(self, root, shell_launcher, **kwargs):
                created["shell_logger"] = kwargs.get("logger")
                created["keyboard_filter"] = kwargs.get("keyboard_filter_service")

            def start(self):
                created["started"] = True

        run_shell(
            launcher,
            tkinter_module=FakeTkFactory(),
            shell_window_class=FakeShell,
            keyboard_filter_class=FakeFilter,
        )

        self.assertIs(launcher.logger, created["filter_logger"])
        self.assertIs(launcher.logger, created["shell_logger"])
        self.assertTrue(created["started"])


if __name__ == "__main__":
    unittest.main()
