# -*- coding: utf-8 -*-

import json
import os
import shutil
import tempfile
import unittest

import legacy_main
from legacy_kiosk.platform_detect import LegacyWindowsInfo


class FakeBackend(object):
    def __init__(self, is_admin=True):
        self.account_inspector = self
        self.is_admin = is_admin
        self.calls = []

    def is_current_process_admin(self):
        return self.is_admin

    def __getattr__(self, name):
        def call(context):
            self.calls.append(name)
        return call

    def rollback(self, operation_name, context):
        self.calls.append("rollback:" + operation_name)

    def restore(self, context):
        self.calls.append("restore")


class LegacyCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app_path = os.path.join(self.temp_dir, "Allowed.exe")
        self.launcher_path = os.path.join(self.temp_dir, "RezhimKioska-Legacy.exe")
        self.config_path = os.path.join(self.temp_dir, "config", "kiosk.json")
        for path in (self.app_path, self.launcher_path):
            with open(path, "wb") as stream:
                stream.write(b"test")
        os.makedirs(os.path.dirname(self.config_path))
        self.config = {
            "operatorUser": "test",
            "allowedApplication": {
                "path": self.app_path,
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

    def _supported_platform(self):
        return LegacyWindowsInfo(5, 1, 2600, 3, 1, "x86")

    def _unsupported_platform(self):
        return LegacyWindowsInfo(6, 1, 7601, 1, 1, "x86")

    def _main(self, argv, **overrides):
        options = {
            "platform_detector": self._supported_platform,
            "backend_factory": lambda: FakeBackend(),
            "launcher_path": self.launcher_path,
        }
        options.update(overrides)
        return legacy_main.main(argv, **options)

    def test_no_arguments_launches_shell_from_config(self):
        calls = []

        result = self._main(
            ["--config", self.config_path],
            shell_runner=lambda config, path: calls.append((config, path)),
        )

        self.assertEqual(0, result)
        self.assertEqual(self.config_path, calls[0][1])
        self.assertEqual(self.app_path, calls[0][0]["allowedApplication"]["path"])

    def test_wrong_platform_refuses_before_shell_launch(self):
        calls = []
        reported_errors = []

        result = self._main(
            ["--config", self.config_path],
            platform_detector=self._unsupported_platform,
            shell_runner=lambda config, path: calls.append((config, path)),
            error_reporter=reported_errors.append,
        )

        self.assertEqual(3, result)
        self.assertEqual([], calls)
        self.assertEqual(1, len(reported_errors))
        self.assertIn(u"Windows XP SP1+", reported_errors[0])

    def test_install_is_dry_run_by_default(self):
        backend = FakeBackend()

        result = self._main(
            ["--config", self.config_path, "install"],
            backend_factory=lambda: backend,
        )

        self.assertEqual(0, result)
        self.assertEqual([], backend.calls)

    def test_install_apply_refuses_without_administrator_rights(self):
        backend = FakeBackend(is_admin=False)

        result = self._main(
            ["--config", self.config_path, "install", "--apply"],
            backend_factory=lambda: backend,
        )

        self.assertEqual(5, result)
        self.assertEqual([], backend.calls)

    def test_install_apply_runs_transaction_and_creates_backup_path(self):
        backend = FakeBackend(is_admin=True)

        result = self._main(
            ["--config", self.config_path, "install", "--apply"],
            backend_factory=lambda: backend,
        )

        self.assertEqual(0, result)
        self.assertIn("create_backup", backend.calls)
        self.assertIn("set_operator_shell", backend.calls)

    def test_restore_apply_runs_independent_restore_backend(self):
        backend = FakeBackend(is_admin=True)

        result = self._main(
            ["--config", self.config_path, "restore", "--apply"],
            backend_factory=lambda: backend,
        )

        self.assertEqual(0, result)
        self.assertEqual(["restore"], backend.calls)

    def test_recover_desktop_uses_only_explicit_recovery_callback(self):
        calls = []

        result = self._main(
            ["--config", self.config_path, "recover-desktop"],
            desktop_recoverer=lambda: calls.append("recover"),
        )

        self.assertEqual(0, result)
        self.assertEqual(["recover"], calls)

    def test_frozen_default_config_is_external_next_to_executable(self):
        executable = os.path.join(self.temp_dir, "RezhimKioska-Legacy.exe")

        result = legacy_main.default_config_path(
            executable=executable, frozen=True
        )

        self.assertEqual(
            os.path.join(self.temp_dir, "config", "kiosk.json"), result
        )


if __name__ == "__main__":
    unittest.main()
