# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.backup_store import (
    BackupIntegrityError,
    BackupStore,
    BackupValidationError,
)


def valid_metadata():
    return {
        "schemaVersion": 2,
        "buildFamily": "modern",
        "operatorSid": "S-1-5-21-1-2-3-1001",
        "operatorUser": "test",
        "originalShell": "explorer.exe",
        "registryValues": [],
        "fileAcls": [],
        "configBackup": {"existed": False, "path": r"C:\ProgramData\Kiosk\kiosk.json"},
    }


class RecordingAcl(object):
    def __init__(self, failure=None):
        self.paths = []
        self.failure = failure

    def protect_backup(self, path):
        self.paths.append(path)
        if self.failure is not None:
            raise self.failure


class BackupStoreTests(unittest.TestCase):
    def test_save_adds_digest_and_load_verifies_expected_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "backup.json")
            acl = RecordingAcl()
            store = BackupStore(path, acl)

            saved = store.save(valid_metadata())
            loaded = store.load(
                expected_build_family="modern",
                expected_operator_sid="S-1-5-21-1-2-3-1001",
            )

            self.assertRegex(saved["integritySha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(saved, loaded)
            self.assertEqual([path], acl.paths)

    def test_tampering_is_rejected_before_identity_is_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "backup.json")
            store = BackupStore(path, RecordingAcl())
            store.save(valid_metadata())
            with open(path, "r", encoding="utf-8") as stream:
                tampered = json.load(stream)
            tampered["operatorUser"] = "other"
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(tampered, stream)

            with self.assertRaises(BackupIntegrityError):
                store.load()

    def test_wrong_build_or_sid_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "backup.json")
            store = BackupStore(path, RecordingAcl())
            store.save(valid_metadata())

            with self.assertRaises(BackupValidationError):
                store.load(expected_build_family="legacy")
            with self.assertRaises(BackupValidationError):
                store.load(expected_operator_sid="S-1-5-21-other")

    def test_unknown_or_missing_metadata_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = BackupStore(os.path.join(directory, "backup.json"), RecordingAcl())
            unknown = valid_metadata()
            unknown["password"] = "must-not-exist"
            with self.assertRaises(BackupValidationError):
                store.save(unknown)
            missing = valid_metadata()
            del missing["operatorSid"]
            with self.assertRaises(BackupValidationError):
                store.save(missing)

    def test_acl_failure_restores_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "backup.json")
            previous = b"previous backup evidence\n"
            with open(path, "wb") as stream:
                stream.write(previous)
            store = BackupStore(path, RecordingAcl(RuntimeError("acl failed")))

            with self.assertRaises(RuntimeError):
                store.save(valid_metadata())

            with open(path, "rb") as stream:
                self.assertEqual(previous, stream.read())
            self.assertEqual([], [name for name in os.listdir(directory) if name.endswith(".tmp")])


if __name__ == "__main__":
    unittest.main()
