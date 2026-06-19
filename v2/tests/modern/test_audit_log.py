# -*- coding: utf-8 -*-
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.audit_log import AuditLogger, SafeEvent


class FakeClock(object):
    def utcnow(self):
        return datetime.datetime(2026, 6, 19, 12, 30, 45, 123456)


class AuditLogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kiosk-v2-log-")
        self.log_path = os.path.join(self.temp_dir, "kiosk.jsonl")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_event_recursively_redacts_secret_and_input_fields(self):
        safe_event = SafeEvent(
            "auth_attempt",
            "Warning",
            {
                "username": "Admin",
                "password": "hunter2",
                "nested": {
                    "apiToken": "secret-token",
                    "typedText": "operator input",
                    "arguments": ["--password", "hunter2"],
                    "commandLine": "tool.exe --secret value",
                },
                "items": [{"credentialValue": "private"}, {"status": "denied"}],
            },
            clock=FakeClock(),
        )
        self.assertNotIn("hunter2", repr(safe_event.__dict__))
        self.assertNotIn("secret-token", repr(safe_event.__dict__))

        event = safe_event.to_dict()

        rendered = json.dumps(event, ensure_ascii=False)
        self.assertEqual("Admin", event["username"])
        self.assertEqual("[REDACTED]", event["password"])
        self.assertEqual("[REDACTED]", event["nested"]["apiToken"])
        self.assertEqual("[REDACTED]", event["nested"]["typedText"])
        self.assertEqual("[REDACTED]", event["nested"]["arguments"])
        self.assertEqual("[REDACTED]", event["nested"]["commandLine"])
        self.assertEqual("[REDACTED]", event["items"][0]["credentialValue"])
        self.assertNotIn("hunter2", rendered)
        self.assertNotIn("secret-token", rendered)
        self.assertNotIn("operator input", rendered)

    def test_exception_message_is_never_serialized(self):
        event = SafeEvent(
            "runtime_failure",
            "Error",
            {"error": RuntimeError("password=hunter2")},
            clock=FakeClock(),
        ).to_dict()

        rendered = json.dumps(event, ensure_ascii=False)
        self.assertEqual({"errorType": "RuntimeError"}, event["error"])
        self.assertNotIn("hunter2", rendered)
        self.assertNotIn("password=", rendered)

    def test_logger_writes_one_utf8_json_object_per_line(self):
        logger = AuditLogger(
            self.log_path,
            max_bytes=65536,
            backup_count=2,
            level="Info",
            clock=FakeClock(),
        )
        logger.emit(
            "operator_started",
            level="Info",
            state="OPERATOR",
            description="Режим киоска запущен",
        )
        logger.close()

        with open(self.log_path, "r", encoding="utf-8") as stream:
            lines = stream.readlines()
        self.assertEqual(1, len(lines))
        event = json.loads(lines[0])
        self.assertEqual("2026-06-19T12:30:45.123Z", event["timestampUtc"])
        self.assertEqual("operator_started", event["event"])
        self.assertEqual("Info", event["level"])
        self.assertEqual("Режим киоска запущен", event["description"])
        self.assertTrue(logger.closed)

    def test_logger_rotates_by_size_and_preserves_valid_json_lines(self):
        logger = AuditLogger(
            self.log_path,
            max_bytes=240,
            backup_count=2,
            level="Debug",
            clock=FakeClock(),
        )
        for index in range(20):
            logger.emit(
                "diagnostic",
                level="Debug",
                sequence=index,
                payload="x" * 80,
            )
        logger.close()

        paths = [
            path
            for path in (
                self.log_path,
                self.log_path + ".1",
                self.log_path + ".2",
            )
            if os.path.exists(path)
        ]
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            with open(path, "r", encoding="utf-8") as stream:
                for line in stream:
                    self.assertEqual("diagnostic", json.loads(line)["event"])

    def test_level_filter_drops_debug_below_configured_level(self):
        logger = AuditLogger(
            self.log_path,
            max_bytes=65536,
            backup_count=1,
            level="Info",
            clock=FakeClock(),
        )
        logger.emit("hidden", level="Debug", value=1)
        logger.emit("visible", level="Info", value=2)
        logger.close()

        with open(self.log_path, "r", encoding="utf-8") as stream:
            events = [json.loads(line)["event"] for line in stream]
        self.assertEqual(["visible"], events)


if __name__ == "__main__":
    unittest.main()
