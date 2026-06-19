# -*- coding: utf-8 -*-
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, PROJECT_ROOT)

from v2.migration.config_v1_to_v2 import V1ConfigMigrator
from kiosk_v2_modern.app.config_repository import ConfigRepository, ConfigValidator


def load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


class NoOpAcl(object):
    def protect_admin_write(self, _path):
        return None


class FailingRepository(object):
    def __init__(self, config_path):
        self.config_path = config_path
        self.calls = []

    def save(self, data, require_existing_app=False):
        self.calls.append((copy.deepcopy(data), require_existing_app))
        raise OSError("save failed")

    def load(self, require_existing_app=False):
        raise AssertionError("load must not be called with force=True")


class ConfigMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kiosk-v2-migrate-")
        self.source_path = os.path.join(self.temp_dir, "kiosk.json")
        self.target_path = os.path.join(self.temp_dir, "kiosk.v2.json")
        self.backup_path = os.path.join(self.temp_dir, "kiosk.v1.source.backup.json")
        schema = load_json(
            os.path.join(V2_ROOT, "contracts", "kiosk-config-v2.schema.json")
        )
        self.default = load_json(
            os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json")
        )
        self.repository = ConfigRepository(
            self.target_path,
            validator=ConfigValidator(schema),
            acl=NoOpAcl(),
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def v1_data(self):
        return {
            "operatorUser": "test",
            "allowedApplication": {
                "path": r"C:\Program Files\Vendor\Any App.exe",
                "arguments": '--profile "Operator One"',
                "workingDirectory": r"C:\Program Files\Vendor",
                "restartOnExit": True,
                "singleInstance": True,
                "bringToFront": True,
                "startMaximized": False,
                "restoreIfMinimized": False,
                "restartDelayMs": 2500,
                "bringExistingToFront": True,
                "unknownAppField": "ignored",
            },
            "kiosk": {
                "allowWinL": False,
                "adminSessionTimeoutSeconds": 420,
                "disableExplorer": True,
                "unknownKioskField": "ignored",
            },
            "logging": {
                "logDirectory": r"C:\ProgramData\Kiosk\CustomLogs",
                "level": "Debug",
            },
            "testing": {
                "requireBackupBeforeTest": False,
                "restoreAfterTest": False,
                "testOnlySeparateOperatorUser": False,
            },
            "admin_password_hash": "hash-secret",
            "admin_password_salt": "salt-secret",
            "token": "api-token",
            "featureFlags": {"unknown": True},
            "restoreMetadata": {"secret": "value"},
            "unknownTopLevel": "ignored",
        }

    def write_source(self, data, bom=True):
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        raw = (b"\xef\xbb\xbf" if bom else b"") + payload
        with open(self.source_path, "wb") as stream:
            stream.write(raw)
        return raw

    def migrator(self, repository=None):
        return V1ConfigMigrator(
            self.source_path,
            self.backup_path,
            repository or self.repository,
            default_config=self.default,
        )

    def test_migrates_only_allowlisted_fields_and_keeps_exact_source_backup(self):
        original = self.write_source(self.v1_data(), bom=True)

        result = self.migrator().migrate()

        self.assertEqual("migrated", result.status)
        self.assertEqual(original, self._read_bytes(self.source_path))
        self.assertEqual(original, self._read_bytes(result.backup_path))
        migrated = self.repository.load()
        self.assertEqual("test", migrated["operatorUser"])
        self.assertEqual(
            r"C:\Program Files\Vendor\Any App.exe",
            migrated["allowedApplication"]["path"],
        )
        self.assertEqual(2500, migrated["allowedApplication"]["restartDelayMs"])
        self.assertEqual(5, migrated["allowedApplication"]["maxRestartAttempts"])
        self.assertEqual(30, migrated["allowedApplication"]["restartWindowSeconds"])
        self.assertTrue(migrated["kiosk"]["allowWinL"])
        self.assertEqual(420, migrated["kiosk"]["adminSessionTimeoutSeconds"])
        self.assertEqual(1048576, migrated["logging"]["maxBytes"])
        self.assertEqual(5, migrated["logging"]["backupCount"])
        self.assertTrue(migrated["testing"]["requireBackupBeforeTest"])
        self.assertTrue(migrated["testing"]["restoreAfterTest"])
        self.assertTrue(migrated["testing"]["testOnlySeparateOperatorUser"])
        rendered = json.dumps(migrated, ensure_ascii=False).lower()
        for forbidden in ("password", "hash-secret", "salt-secret", "api-token"):
            self.assertNotIn(forbidden, rendered)

    def test_existing_different_backup_is_preserved_and_numbered_backup_is_used(self):
        original = self.write_source(self.v1_data())
        existing = b"do-not-overwrite"
        with open(self.backup_path, "wb") as stream:
            stream.write(existing)

        result = self.migrator().migrate()

        self.assertEqual(existing, self._read_bytes(self.backup_path))
        self.assertEqual(self.backup_path + ".1", result.backup_path)
        self.assertEqual(original, self._read_bytes(result.backup_path))

    def test_existing_identical_backup_is_reused(self):
        original = self.write_source(self.v1_data())
        with open(self.backup_path, "wb") as stream:
            stream.write(original)

        result = self.migrator().migrate()

        self.assertEqual(self.backup_path, result.backup_path)
        self.assertEqual(original, self._read_bytes(self.backup_path))

    def test_existing_v2_is_loaded_without_rewriting_or_new_backup(self):
        self.repository.save(self.default)
        before = self._read_bytes(self.target_path)
        self.write_source(self.v1_data())

        result = self.migrator().migrate()

        self.assertEqual("existing", result.status)
        self.assertEqual(before, self._read_bytes(self.target_path))
        self.assertFalse(os.path.exists(self.backup_path))

    def test_save_failure_keeps_previous_v2_and_source_unchanged(self):
        original = self.write_source(self.v1_data())
        previous_v2 = b"previous-v2-bytes"
        with open(self.target_path, "wb") as stream:
            stream.write(previous_v2)
        repository = FailingRepository(self.target_path)

        with self.assertRaises(OSError):
            self.migrator(repository=repository).migrate(force=True)

        self.assertEqual(original, self._read_bytes(self.source_path))
        self.assertEqual(previous_v2, self._read_bytes(self.target_path))
        self.assertEqual(original, self._read_bytes(self.backup_path))
        self.assertEqual(1, len(repository.calls))

    def test_invalid_migrated_path_creates_backup_but_not_v2(self):
        data = self.v1_data()
        data["allowedApplication"]["path"] = r"relative\app.exe"
        original = self.write_source(data)

        with self.assertRaises(ValueError):
            self.migrator().migrate()

        self.assertEqual(original, self._read_bytes(self.source_path))
        self.assertEqual(original, self._read_bytes(self.backup_path))
        self.assertFalse(os.path.exists(self.target_path))

    @staticmethod
    def _read_bytes(path):
        with open(path, "rb") as stream:
            return stream.read()


if __name__ == "__main__":
    unittest.main()
