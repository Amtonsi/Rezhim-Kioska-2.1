try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.config import (
    AllowedApplicationConfig,
    DEFAULT_ALLOWED_APP_PATH,
    KioskConfig,
    ensure_default_config,
    load_config,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_config_round_trips_through_json_file(self):
        config = KioskConfig(
            app_path=r"C:\Program Files\Vendor\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash-value",
            admin_password_salt="salt-value",
            policy_profile="win7_srp",
            restart_delay_seconds=3,
        )

        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "kiosk.json")

        save_config(config, path)
        loaded = load_config(path)

        self.assertEqual(config.to_dict(), loaded.to_dict())

    def test_load_config_accepts_utf8_bom_files(self):
        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "kiosk.json")
        with open(path, "w", encoding="utf-8-sig") as config_file:
            config_file.write(
                '{'
                '"operatorUser":"Operator",'
                '"allowedApplication":{"path":"C:\\\\Windows\\\\System32\\\\notepad.exe"}'
                '}'
            )

        loaded = load_config(path)

        self.assertEqual("Operator", loaded.operator_user)
        self.assertEqual(r"C:\Windows\System32\notepad.exe", loaded.app_path)

    def test_validate_rejects_missing_app_path(self):
        config = KioskConfig(
            app_path="",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
        )

        with self.assertRaises(ValueError) as error:
            config.validate()

        self.assertIn("app_path", str(error.exception))

    def test_validate_rejects_non_positive_restart_delay(self):
        config = KioskConfig(
            app_path=r"C:\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
            restart_delay_seconds=0,
        )

        with self.assertRaises(ValueError) as error:
            config.validate()

        self.assertIn("restart_delay_seconds", str(error.exception))

    def test_password_iterations_round_trip_with_default(self):
        config = KioskConfig(
            app_path=r"C:\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
        )

        data = config.to_dict()
        loaded = KioskConfig.from_dict(data)

        self.assertEqual(200000, loaded.admin_password_iterations)
        self.assertEqual("pbkdf2_hmac_sha256", loaded.admin_password_algorithm)

    def test_ensure_default_config_creates_required_nested_kiosk_json(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "config", "kiosk.json")

        created = ensure_default_config(config_path)
        loaded = load_config(config_path)

        self.assertEqual(config_path, created)
        self.assertTrue(os.path.exists(config_path))
        self.assertEqual(DEFAULT_ALLOWED_APP_PATH, loaded.allowed_application.path)
        self.assertEqual("KioskOperator", loaded.operator_user)
        self.assertFalse(loaded.allowed_application.restore_if_minimized)
        self.assertEqual(300, loaded.kiosk["adminSessionTimeoutSeconds"])
        self.assertTrue(loaded.kiosk["blockWinKey"])
        self.assertTrue(loaded.testing["requireBackupBeforeTest"])
        self.assertTrue(loaded.testing["restoreAfterTest"])
        self.assertTrue(loaded.testing["testOnlySeparateOperatorUser"])
        self.assertNotIn("windows_admin_password", loaded.to_dict())
        self.assertNotIn("password", loaded.to_dict().get("allowedApplication", {}))

    def test_load_config_reads_required_nested_model(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write(
                """
{
  "operatorUser": "KioskOperator",
  "allowedApplication": {
    "path": "C:\\\\Windows\\\\System32\\\\notepad.exe",
    "arguments": "",
    "workingDirectory": "C:\\\\Windows\\\\System32",
    "restartOnExit": true,
    "bringToFront": true,
    "bringExistingToFront": true,
    "singleInstance": true,
    "restoreIfMinimized": true,
    "startMaximized": false,
    "restartDelayMs": 2000
  },
  "kiosk": {
    "blockDesktop": true,
    "disableStartMenu": true,
    "disableExplorer": true,
    "allowWinL": true,
    "blockWinKey": true,
    "adminSessionTimeoutSeconds": 300
  },
  "testing": {
    "requireBackupBeforeTest": true,
    "restoreAfterTest": true,
    "testOnlySeparateOperatorUser": true
  },
  "logging": {
    "logDirectory": "C:\\\\ProgramData\\\\Kiosk\\\\Logs",
    "level": "Info"
  }
}
"""
            )

        config = load_config(config_path)

        self.assertEqual(r"C:\Windows\System32\notepad.exe", config.app_path)
        self.assertEqual("", config.allowed_application.arguments)
        self.assertEqual(r"C:\Windows\System32", config.allowed_application.working_directory)
        self.assertTrue(config.allowed_application.restart_on_exit)
        self.assertTrue(config.allowed_application.bring_to_front)
        self.assertTrue(config.allowed_application.bring_existing_to_front)
        self.assertTrue(config.allowed_application.single_instance)
        self.assertTrue(config.allowed_application.restore_if_minimized)
        self.assertFalse(config.allowed_application.start_maximized)
        self.assertEqual(2000, config.allowed_application.restart_delay_ms)
        self.assertTrue(config.kiosk["blockWinKey"])
        self.assertTrue(config.testing["requireBackupBeforeTest"])

    def test_save_config_writes_nested_model_without_kiosk_password_requirement(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        config = KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="KioskOperator",
        )

        save_config(config, config_path)

        with open(config_path, "r", encoding="utf-8") as config_file:
            text = config_file.read()
        self.assertIn('"allowedApplication"', text)
        self.assertIn('"operatorUser"', text)
        self.assertIn('"singleInstance": true', text)
        self.assertIn('"restartDelayMs": 2000', text)
        self.assertNotIn("admin_password_hash", text)

    def test_allowed_application_command_strips_windows_argument_quotes(self):
        allowed = AllowedApplicationConfig(
            path=r"C:\Tools\Launcher.exe",
            arguments=(
                r'"C:\Program Files\Vendor App\app.exe" '
                r'"C:\ProgramData\Kiosk Files\capture.txt"'
            ),
        )

        self.assertEqual(
            [
                r"C:\Tools\Launcher.exe",
                r"C:\Program Files\Vendor App\app.exe",
                r"C:\ProgramData\Kiosk Files\capture.txt",
            ],
            allowed.command(),
        )


if __name__ == "__main__":
    unittest.main()
