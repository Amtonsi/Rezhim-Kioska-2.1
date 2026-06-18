# -*- coding: utf-8 -*-

import json
import os
import shutil
import tempfile
import unittest

from legacy_kiosk.logging_service import LegacyLogger, legacy_log_directory


class LegacyLoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.temp_dir, "kiosk.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_writes_utf8_json_line_without_sensitive_fields(self):
        logger = LegacyLogger(path=self.path)

        logger.log(
            "admin_authentication",
            {
                "account_name": u"Администратор",
                "password": "secret",
                "token": "handle",
                "typed_text": "private input",
            },
        )

        with open(self.path, "rb") as stream:
            raw = stream.read()
        record = json.loads(raw.decode("utf-8"))
        self.assertEqual("admin_authentication", record["event"])
        self.assertEqual(u"Администратор", record["data"]["account_name"])
        self.assertNotIn("secret", raw)
        self.assertNotIn("handle", raw)
        self.assertNotIn("private input", raw)

    def test_rotates_log_files_at_size_limit(self):
        logger = LegacyLogger(path=self.path, max_bytes=80, backup_count=2)

        for index in range(8):
            logger.log("event", {"index": index, "message": "x" * 30})

        self.assertTrue(os.path.isfile(self.path))
        self.assertTrue(os.path.isfile(self.path + ".1"))
        self.assertLessEqual(
            len([name for name in os.listdir(self.temp_dir) if name.startswith("kiosk.log")]),
            3,
        )

    def test_xp_default_log_directory_uses_all_users_application_data(self):
        environment = {
            "ALLUSERSPROFILE": r"C:\Documents and Settings\All Users",
        }

        result = legacy_log_directory(environment=environment, nt_major=5)

        self.assertEqual(
            r"C:\Documents and Settings\All Users\Application Data\Kiosk\Logs",
            result,
        )


if __name__ == "__main__":
    unittest.main()
