# -*- coding: utf-8 -*-
import copy
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.runtime_settings import RuntimeSettingsFactory
from kiosk_v2_modern.platform.command_line import WindowsArgumentParser


class FakeArgumentParser(object):
    def __init__(self, result=()):
        self.result = tuple(result)
        self.calls = []

    def parse(self, value):
        self.calls.append(value)
        return self.result


def default_config():
    with open(
        os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class RuntimeSettingsTests(unittest.TestCase):
    def test_maps_every_runtime_setting_and_preserves_path_with_spaces(self):
        config = default_config()
        config["operatorUser"] = "test"
        application = config["allowedApplication"]
        application["path"] = r"C:\Program Files\Vendor\Any App.exe"
        application["arguments"] = '--profile "Operator One"'
        application["workingDirectory"] = r"C:\Program Files\Vendor"
        application["restartDelayMs"] = 2500
        application["maxRestartAttempts"] = 4
        application["restartWindowSeconds"] = 45
        config["kiosk"]["adminSessionTimeoutSeconds"] = 420
        config["kiosk"]["explorerGuardIntervalMs"] = 750
        parser = FakeArgumentParser(("--profile", "Operator One"))

        runtime = RuntimeSettingsFactory(parser).build(config)

        self.assertEqual([application["arguments"]], parser.calls)
        self.assertEqual(application["path"], runtime.application.path)
        self.assertEqual(("--profile", "Operator One"), runtime.application.arguments)
        self.assertEqual(application["workingDirectory"], runtime.application.working_directory)
        self.assertEqual(2500, runtime.application.restart_delay_ms)
        self.assertEqual(4, runtime.application.max_restart_attempts)
        self.assertEqual(45, runtime.application.restart_window_seconds)
        self.assertFalse(runtime.application_configured)
        self.assertEqual("test", runtime.operator_user)
        self.assertTrue(runtime.window.bring_to_front)
        self.assertFalse(runtime.window.start_maximized)
        self.assertFalse(runtime.window.restore_if_minimized)
        self.assertEqual(420, runtime.security.admin_session_timeout_seconds)
        self.assertEqual(750, runtime.security.explorer_guard_interval_ms)
        self.assertTrue(runtime.security.allow_win_l)
        self.assertTrue(runtime.security.keyboard_guard_required)
        self.assertTrue(os.path.isabs(runtime.logging.log_directory))
        self.assertTrue(runtime.logging.log_directory.endswith(os.path.join("RezhimKioska", "Logs")))
        self.assertEqual("Info", runtime.logging.level)
        self.assertEqual(1048576, runtime.logging.max_bytes)
        self.assertEqual(5, runtime.logging.backup_count)
        self.assertTrue(runtime.testing.restore_after_test)

    def test_build_does_not_mutate_configuration(self):
        config = default_config()
        before = copy.deepcopy(config)

        RuntimeSettingsFactory(FakeArgumentParser()).build(config)

        self.assertEqual(before, config)

    def test_missing_configured_field_keeps_legacy_configuration_enabled(self):
        config = default_config()
        del config["allowedApplication"]["configured"]

        runtime = RuntimeSettingsFactory(FakeArgumentParser()).build(config)

        self.assertTrue(runtime.application_configured)

    def test_password_like_field_is_rejected_without_value_in_error(self):
        config = default_config()
        config["adminPassword"] = "hunter2"

        with self.assertRaises(ValueError) as raised:
            RuntimeSettingsFactory(FakeArgumentParser()).build(config)

        self.assertNotIn("hunter2", str(raised.exception))

    def test_windows_argument_parser_preserves_quoted_argument(self):
        parsed = WindowsArgumentParser().parse('--profile "Operator One" --flag')

        self.assertEqual(("--profile", "Operator One", "--flag"), parsed)

    def test_windows_argument_parser_returns_empty_tuple_for_blank_input(self):
        self.assertEqual((), WindowsArgumentParser().parse("   "))


if __name__ == "__main__":
    unittest.main()
