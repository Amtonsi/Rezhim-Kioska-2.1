# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import io
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.runtime_settings import RuntimeSettingsFactory
from kiosk_v2_legacy.platform.command_line import WindowsArgumentParser
from kiosk_v2_legacy.platform.desktop_isolation import ProcessRecord, ShellSurface
from kiosk_v2_legacy.platform.desktop_recovery import WindowsDesktopRecovery


class FakeArgumentParser(object):
    def __init__(self, result=()):
        self.result = tuple(result)
        self.calls = []

    def parse(self, value):
        self.calls.append(value)
        return self.result


class FakeDesktopApi(object):
    def __init__(self, processes=()):
        self.processes = list(processes)
        self.shown = []

    def current_session_id(self):
        return 7

    def list_processes(self):
        return list(self.processes)

    def list_shell_surfaces(self):
        return [
            ShellSurface(100, "Shell_TrayWnd", 10, 7),
            ShellSurface(101, "Shell_TrayWnd", 11, 8),
        ]

    def show_window(self, hwnd):
        self.shown.append(hwnd)
        return True


class FakeLauncher(object):
    def __init__(self):
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)


def default_config():
    with io.open(
        os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class LegacyCompositionAdapterTests(unittest.TestCase):
    def test_runtime_settings_map_complete_config_without_mutation(self):
        config = default_config()
        config["operatorUser"] = "test"
        config["allowedApplication"]["path"] = (
            "C:\\Program Files\\Vendor\\Any App.exe"
        )
        config["allowedApplication"]["arguments"] = '--profile "Operator One"'
        before = copy.deepcopy(config)
        parser = FakeArgumentParser(("--profile", "Operator One"))

        runtime = RuntimeSettingsFactory(parser).build(config)

        self.assertEqual(before, config)
        self.assertEqual([config["allowedApplication"]["arguments"]], parser.calls)
        self.assertEqual("test", runtime.operator_user)
        self.assertEqual(config["allowedApplication"]["path"], runtime.application.path)
        self.assertEqual(("--profile", "Operator One"), runtime.application.arguments)
        self.assertTrue(runtime.security.allow_win_l)
        self.assertTrue(runtime.security.keyboard_guard_required)
        self.assertTrue(runtime.testing.restore_after_test)

    def test_runtime_settings_reject_password_like_field_without_value(self):
        config = default_config()
        config["adminPassword"] = "not-for-logs"

        with self.assertRaises(ValueError) as raised:
            RuntimeSettingsFactory(FakeArgumentParser()).build(config)

        self.assertNotIn("not-for-logs", str(raised.exception))

    def test_windows_argument_parser_preserves_quoted_argument(self):
        parsed = WindowsArgumentParser().parse('--profile "Operator One" --flag')

        self.assertEqual(("--profile", "Operator One", "--flag"), parsed)

    def test_desktop_recovery_is_current_session_only_and_starts_once(self):
        desktop = FakeDesktopApi()
        launcher = FakeLauncher()
        recovery = WindowsDesktopRecovery(
            desktop,
            process_launcher=launcher,
            explorer_path="C:\\Windows\\explorer.exe",
        )

        recovery.restore_shell_surfaces()
        recovery.start_explorer()
        desktop.processes.append(
            ProcessRecord(12, "C:\\Windows\\EXPLORER.EXE", 7)
        )
        recovery.start_explorer()

        self.assertEqual([100], desktop.shown)
        self.assertEqual([["C:\\Windows\\explorer.exe"]], launcher.commands)


if __name__ == "__main__":
    unittest.main()
