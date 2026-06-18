# -*- coding: utf-8 -*-

import json
import os
import shutil
import tempfile
import unittest

from legacy_kiosk.local_admin_auth import AUTH_SUCCESS, AuthResult
from legacy_kiosk.runtime import LegacyRuntime
from legacy_kiosk.system_backend import AccessDeniedError


class FakeAdminSession(object):
    def __init__(self):
        self.calls = []
        self.closed = False

    def run(self, callback):
        self.calls.append("run")
        return callback()

    def close(self):
        self.closed = True
        self.calls.append("close")


class FakeAuthenticator(object):
    def __init__(self):
        self.session = FakeAdminSession()
        self.calls = []

    def begin_session(self, username, password):
        self.calls.append((username, password))
        return AuthResult(AUTH_SUCCESS, u"Доступ разрешён.", username), self.session


class FakeWatchdog(object):
    def __init__(self, path):
        self.path = path
        self.enabled = True
        self.calls = []

    def tick(self):
        self.calls.append("tick")
        return "started" if len(self.calls) == 1 else "running"

    def stop_supervision(self):
        self.enabled = False
        self.calls.append("stop")

    def start_supervision(self):
        self.enabled = True
        self.calls.append("start")


class FakeWindowController(object):
    def __init__(self):
        self.minimized = False
        self.calls = []

    def is_minimized(self, path):
        return self.minimized

    def wait_and_bring_to_front(self, path, timeout_seconds=5, start_maximized=False):
        self.calls.append(("wait_front", path, start_maximized))
        return True

    def bring_to_front(self, path):
        self.calls.append(("front", path))
        return True

    def restore(self, path):
        self.calls.append(("restore", path))
        self.minimized = False
        return True


class FakeKeyboardFilter(object):
    def start(self):
        pass

    def stop(self):
        pass


class FakeDesktopManager(object):
    def __init__(self):
        self.calls = []

    def open_current_desktop(self):
        self.calls.append("open")

    def hide_current_desktop(self):
        self.calls.append("hide")


class LegacyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.first_app = os.path.join(self.temp_dir, "First.exe")
        self.second_app = os.path.join(self.temp_dir, "Second.exe")
        for path in (self.first_app, self.second_app):
            with open(path, "wb") as stream:
                stream.write(b"test")
        self.config_path = os.path.join(self.temp_dir, "kiosk.json")
        self.config = {
            "operatorUser": "test",
            "allowedApplication": {
                "path": self.first_app,
                "arguments": "",
                "workingDirectory": self.temp_dir,
                "restartOnExit": True,
                "bringToFront": True,
                "singleInstance": True,
                "restoreIfMinimized": False,
                "startMaximized": False,
                "restartDelayMs": 2000,
            },
            "kiosk": {"allowWinL": True, "adminSessionTimeoutSeconds": 300},
            "logging": {"logDirectory": self.temp_dir, "level": "Info"},
        }
        with open(self.config_path, "wb") as stream:
            stream.write(json.dumps(self.config).encode("utf-8"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _runtime(self):
        self.authenticator = FakeAuthenticator()
        self.window_controller = FakeWindowController()
        self.desktop_manager = FakeDesktopManager()
        self.watchdogs = []

        def watchdog_factory(config):
            watchdog = FakeWatchdog(config["allowedApplication"]["path"])
            self.watchdogs.append(watchdog)
            return watchdog

        return LegacyRuntime(
            self.config,
            self.config_path,
            authenticator=self.authenticator,
            keyboard_filter=FakeKeyboardFilter(),
            window_controller=self.window_controller,
            desktop_manager=self.desktop_manager,
            watchdog_factory=watchdog_factory,
        )

    def test_change_application_requires_active_admin_session(self):
        runtime = self._runtime()

        with self.assertRaises(AccessDeniedError):
            runtime.change_allowed_application(self.second_app)

    def test_change_application_saves_under_impersonation_and_starts_one_new_watchdog(self):
        runtime = self._runtime()
        result = runtime.authenticate("Admin", "secret")
        self.assertTrue(result.success)

        runtime.change_allowed_application(self.second_app)

        self.assertEqual(self.second_app, runtime.config["allowedApplication"]["path"])
        self.assertEqual(["run"], self.authenticator.session.calls)
        with open(self.config_path, "rb") as stream:
            saved = json.loads(stream.read().decode("utf-8"))
        self.assertEqual(self.second_app, saved["allowedApplication"]["path"])
        self.assertEqual(2, len(self.watchdogs))
        self.assertEqual(["tick"], self.watchdogs[-1].calls)

    def test_runtime_reports_minimized_and_restores_without_reopening(self):
        runtime = self._runtime()
        self.window_controller.minimized = True

        self.assertTrue(runtime.is_allowed_application_minimized())
        self.assertTrue(runtime.restore_allowed_application())

        self.assertEqual(1, len(self.watchdogs))
        self.assertIn(("restore", self.first_app), self.window_controller.calls)

    def test_return_to_kiosk_hides_current_desktop_and_closes_admin_token(self):
        runtime = self._runtime()
        runtime.authenticate("Admin", "secret")
        runtime.open_desktop()

        runtime.return_to_kiosk()

        self.assertEqual(["open", "hide"], self.desktop_manager.calls)
        self.assertTrue(self.authenticator.session.closed)

    def test_stop_and_start_supervision_reuse_same_watchdog(self):
        runtime = self._runtime()
        runtime.authenticate("Admin", "secret")
        watchdog = runtime.watchdog

        runtime.stop_supervision()
        runtime.start_supervision()

        self.assertIs(watchdog, runtime.watchdog)
        self.assertEqual(["stop", "start"], watchdog.calls)


if __name__ == "__main__":
    unittest.main()
