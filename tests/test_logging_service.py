try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import json
import os
import tempfile
import unittest
from unittest import mock

from python_kiosk.config import KioskConfig
from python_kiosk.logging_service import (
    KioskLogger,
    configured_log_path,
    create_configured_logger,
)


class LoggingServiceTests(unittest.TestCase):
    def test_logger_writes_json_lines_without_touching_system_logs(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        logger = KioskLogger(log_path=log_path)

        logger.info("install.plan", operator="Operator", dry_run=True)
        logger.error("policy.failed", error="access denied")

        with open(log_path, "r", encoding="utf-8") as log_file:
            rows = [json.loads(line) for line in log_file.read().splitlines()]

        self.assertEqual("install.plan", rows[0]["event"])
        self.assertEqual("info", rows[0]["level"])
        self.assertEqual(True, rows[0]["data"]["dry_run"])
        self.assertIn("session_id", rows[0])
        self.assertIn("process_id", rows[0])
        self.assertEqual("policy.failed", rows[1]["event"])
        self.assertEqual("error", rows[1]["level"])

    def test_default_logger_uses_environment_log_path_override(self):
        temp_dir = tempfile.mkdtemp()
        env_log_path = os.path.join(temp_dir, "isolated", "kiosk.log")

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": env_log_path}):
            logger = KioskLogger()
            logger.info("environment.log_path")

        self.assertEqual(os.path.abspath(env_log_path), os.path.abspath(logger.log_path))
        self.assertTrue(os.path.exists(env_log_path))

    def test_logger_falls_back_to_user_home_when_primary_path_fails(self):
        temp_dir = tempfile.mkdtemp()
        primary_path = os.path.join(temp_dir, "primary", "kiosk.log")
        fallback_home = os.path.join(temp_dir, "home")
        real_open = open

        def guarded_open(path, *args, **kwargs):
            if path == os.path.abspath(primary_path):
                raise OSError("denied")
            return real_open(path, *args, **kwargs)

        with mock.patch("python_kiosk.logging_service.open", guarded_open, create=True):
            with mock.patch(
                "python_kiosk.logging_service.os.path.expanduser",
                return_value=fallback_home,
            ):
                KioskLogger(primary_path).info("fallback.event")

        fallback_path = os.path.join(
            fallback_home,
            "PythonKiosk",
            "logs",
            "kiosk.log",
        )
        self.assertTrue(os.path.exists(fallback_path))

    def test_logger_rotates_when_file_exceeds_limit(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("x" * 20)

        logger = KioskLogger(log_path=log_path, max_bytes=10, backup_count=2)
        logger.info("rotate.event")

        self.assertTrue(os.path.exists(log_path))
        self.assertTrue(os.path.exists(log_path + ".1"))
        with open(log_path, "r", encoding="utf-8") as log_file:
            self.assertIn("rotate.event", log_file.read())

    def test_logger_redacts_sensitive_fields(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        logger = KioskLogger(log_path=log_path, session_id="test-session")

        logger.warning(
            "admin.unlock_denied",
            username="Admin",
            password="secret",
            nested={"admin_password": "another-secret"},
        )

        with open(log_path, "r", encoding="utf-8") as log_file:
            row = json.loads(log_file.read().splitlines()[0])

        self.assertEqual("test-session", row["session_id"])
        self.assertEqual("***REDACTED***", row["data"]["password"])
        self.assertEqual("***REDACTED***", row["data"]["nested"]["admin_password"])
        self.assertNotIn("secret", json.dumps(row, ensure_ascii=False))

    def test_configured_logger_uses_config_log_directory(self):
        temp_dir = tempfile.mkdtemp()
        config = KioskConfig(logging={"logDirectory": temp_dir, "level": "Debug"})

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": ""}):
            logger = create_configured_logger(config, session_id="configured")
            logger.info("diagnostic.test")
            configured_path = configured_log_path(config)

        self.assertEqual(os.path.join(temp_dir, "kiosk.log"), configured_path)
        with open(os.path.join(temp_dir, "kiosk.log"), "r", encoding="utf-8") as log_file:
            row = json.loads(log_file.read().splitlines()[0])
        self.assertEqual("configured", row["session_id"])
        self.assertEqual("diagnostic.test", row["event"])

    def test_configured_logger_uses_environment_log_path_override(self):
        temp_dir = tempfile.mkdtemp()
        env_log_path = os.path.join(temp_dir, "configured", "kiosk.log")
        config = KioskConfig(logging={"logDirectory": r"C:\ProgramData\Kiosk\Logs"})

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": env_log_path}):
            logger = create_configured_logger(config, session_id="configured-env")
            logger.info("configured.environment")

        self.assertEqual(os.path.abspath(env_log_path), os.path.abspath(logger.log_path))
        self.assertTrue(os.path.exists(env_log_path))


if __name__ == "__main__":
    unittest.main()
