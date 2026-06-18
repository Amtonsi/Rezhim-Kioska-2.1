# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import unittest

from legacy_kiosk.backup_store import BackupError, LegacyBackupStore


class LegacyBackupStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.temp_dir, "backup.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_round_trip_versioned_backup(self):
        payload = {
            "schemaVersion": 1,
            "buildFamily": "legacy",
            "operatorSid": "S-1-5-21-1001",
            "registry": [],
            "security": [],
        }
        store = LegacyBackupStore()

        store.save(self.path, payload)

        self.assertEqual(payload, store.load(self.path))

    def test_rejects_wrong_build_family(self):
        store = LegacyBackupStore()
        store.save(
            self.path,
            {
                "schemaVersion": 1,
                "buildFamily": "modern",
                "operatorSid": "S-1-5-21-1001",
                "registry": [],
                "security": [],
            },
        )

        with self.assertRaises(BackupError):
            store.load(self.path)


if __name__ == "__main__":
    unittest.main()
