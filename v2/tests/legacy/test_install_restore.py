# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.backup_store import (
    BackupIntegrityError,
    BackupStore,
)
from kiosk_v2_legacy.app.transaction import (
    InstallTransaction,
    Operation,
    TransactionFailure,
)
from kiosk_v2_legacy.platform.operator_account import (
    OperatorIdentity,
    OperatorPreflight,
    PreflightError,
)


def backup_metadata():
    return {
        "schemaVersion": 2,
        "buildFamily": "legacy",
        "operatorSid": "S-1-5-21-1-2-3-1001",
        "operatorUser": "test",
        "originalShell": "explorer.exe",
        "registryValues": [],
        "fileAcls": [],
        "configBackup": {"files": [], "ownedPaths": []},
    }


class FakeAcl(object):
    def __init__(self):
        self.paths = []

    def protect_backup(self, path):
        self.paths.append(path)


class FakeAccountApi(object):
    def __init__(self, elevated=True, identity=None):
        self.elevated = elevated
        self.identity = identity
        self.lookups = []

    def is_elevated(self):
        return self.elevated

    def get_identity(self, username):
        self.lookups.append(username)
        return self.identity


class LegacyInstallRestoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="kiosk-v2-legacy-")

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_transaction_dry_run_and_reverse_rollback(self):
        calls = []

        def operation(name, fail=False, shell=False):
            def apply():
                calls.append("apply:" + name)
                if fail:
                    raise RuntimeError("failure")

            return Operation(
                name,
                apply,
                lambda: calls.append("rollback:" + name),
                lambda: calls.append("verify:" + name),
                is_shell=shell,
            )

        dry = InstallTransaction(
            [operation("files"), operation("shell", shell=True)]
        ).execute(dry_run=True)
        self.assertEqual(("files", "shell"), dry.planned_ids)
        self.assertEqual([], calls)

        with self.assertRaises(TransactionFailure) as caught:
            InstallTransaction(
                [operation("files"), operation("policy"), operation("failure", True)]
            ).execute()
        self.assertEqual(("policy", "files"), caught.exception.rolled_back_ids)
        self.assertEqual(
            ["rollback:policy", "rollback:files"],
            [item for item in calls if item.startswith("rollback:")],
        )

    def test_transaction_rejects_nonfinal_or_duplicate_shell(self):
        regular = Operation("regular", lambda: None, lambda: None, lambda: None)
        shell = Operation(
            "shell", lambda: None, lambda: None, lambda: None, is_shell=True
        )
        with self.assertRaises(ValueError):
            InstallTransaction([shell, regular])
        with self.assertRaises(ValueError):
            InstallTransaction([shell, shell])

    def test_backup_round_trip_and_tamper_detection(self):
        path = os.path.join(self.directory, "backup.json")
        acl = FakeAcl()
        store = BackupStore(path, acl)

        saved = store.save(backup_metadata())
        loaded = store.load("legacy", "S-1-5-21-1-2-3-1001")

        self.assertEqual(saved, loaded)
        self.assertEqual([path], acl.paths)
        self.assertEqual(64, len(saved["integritySha256"]))

        with open(path, "rb") as stream:
            tampered = json.loads(stream.read().decode("utf-8"))
        tampered["operatorUser"] = "other"
        with open(path, "wb") as stream:
            stream.write(json.dumps(tampered).encode("utf-8"))
        with self.assertRaises(BackupIntegrityError):
            store.load()

    def test_legacy_backup_source_uses_movefile_write_through(self):
        import inspect
        from kiosk_v2_legacy.app import backup_store

        source = inspect.getsource(backup_store)
        self.assertIn("MOVEFILE_WRITE_THROUGH", source)
        self.assertNotIn("os.replace", source)

    def test_legacy_operator_preflight_denies_nonadmin_or_admin_operator(self):
        api = FakeAccountApi(elevated=False)
        with self.assertRaises(PreflightError) as denied:
            OperatorPreflight(api).validate("test")
        self.assertEqual("elevation_required", denied.exception.code)
        self.assertEqual([], api.lookups)

        identity = OperatorIdentity(
            "test", "S-1-5-21-1-2-3-1001", True, True
        )
        with self.assertRaises(PreflightError) as admin:
            OperatorPreflight(FakeAccountApi(identity=identity)).validate("test")
        self.assertEqual("operator_is_administrator", admin.exception.code)

    def test_legacy_operator_preflight_accepts_enabled_standard_local_user(self):
        identity = OperatorIdentity(
            "test", "S-1-5-21-1-2-3-1001", True, False
        )
        result = OperatorPreflight(FakeAccountApi(identity=identity)).validate("test")
        self.assertIs(identity, result)


if __name__ == "__main__":
    unittest.main()
