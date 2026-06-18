# -*- coding: utf-8 -*-

import codecs
import json
import os
import shutil
import tempfile
import unittest

from legacy_kiosk.config import ConfigError, load_config, save_config


class LegacyConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.temp_dir, "kiosk.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _current_contract(self):
        return {
            "operatorUser": "test",
            "allowedApplication": {
                "path": r"C:\Windows\notepad.exe",
                "arguments": "",
                "workingDirectory": r"C:\Windows",
                "restartOnExit": True,
                "bringToFront": True,
                "bringExistingToFront": True,
                "singleInstance": True,
                "restoreIfMinimized": False,
                "startMaximized": False,
                "restartDelayMs": 2000,
            },
            "kiosk": {
                "blockDesktop": True,
                "disableStartMenu": True,
                "disableExplorer": True,
                "allowWinL": True,
                "blockWinKey": True,
                "adminSessionTimeoutSeconds": 300,
            },
            "logging": {
                "logDirectory": r"C:\ProgramData\Kiosk\Logs",
                "level": "Info",
            },
            "policyProfile": "auto",
            "restartDelaySeconds": 2,
            "restoreMetadata": {},
            "featureFlags": {},
            "testing": {
                "requireBackupBeforeTest": True,
                "restoreAfterTest": True,
                "testOnlySeparateOperatorUser": True,
            },
        }

    def test_round_trip_current_contract(self):
        source = self._current_contract()

        save_config(source, self.path)

        self.assertEqual(source, load_config(self.path))

    def test_load_accepts_utf8_bom(self):
        source = self._current_contract()
        payload = json.dumps(source, ensure_ascii=False).encode("utf-8")
        with open(self.path, "wb") as stream:
            stream.write(codecs.BOM_UTF8 + payload)

        self.assertEqual(source, load_config(self.path))

    def test_rejects_windows_credentials(self):
        source = self._current_contract()
        source["windowsPassword"] = "must-not-be-saved"

        with self.assertRaises(ConfigError):
            save_config(source, self.path)

        self.assertFalse(os.path.exists(self.path))

    def test_require_existing_app_rejects_missing_executable(self):
        source = self._current_contract()
        source["allowedApplication"]["path"] = os.path.join(
            self.temp_dir, "missing.exe"
        )
        save_config(source, self.path)

        with self.assertRaises(ConfigError):
            load_config(self.path, require_existing_app=True)


if __name__ == "__main__":
    unittest.main()
