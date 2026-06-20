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
from kiosk_v2_legacy.platform.operator_registry import (
    OperatorRegistryStore,
    RegistryValueSnapshot,
)
from kiosk_v2_legacy.platform.file_acl import AclSnapshot, FileAclManager
from kiosk_v2_legacy.app.install_artifacts import FileArtifactManager
from kiosk_v2_legacy.platform.profile_path import WindowsProfileLocator
from kiosk_v2_legacy.app.install_service import InstallService
from kiosk_v2_legacy.app.restore_service import RestoreService


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


class FakeRegistryApi(object):
    def __init__(self):
        self.values = {}
        self.unmounted = []

    def mount_operator_hive(self, sid, profile_path):
        return "ROOT:" + sid

    def unmount_operator_hive(self, root):
        self.unmounted.append(root)

    def read_value(self, root, key_path, value_name):
        return self.values.get((root, key_path, value_name))

    def write_value(self, root, key_path, value_name, value_type, value_data):
        self.values[(root, key_path, value_name)] = (value_type, value_data)

    def delete_value(self, root, key_path, value_name):
        self.values.pop((root, key_path, value_name), None)


class FakeAclNative(object):
    def __init__(self):
        self.sddl = {}

    def capture_sddl(self, path):
        return self.sddl.get(path, "D:(A;;FA;;;BA)")

    def apply_sddl(self, path, sddl):
        self.sddl[path] = sddl


class FakeProfileRegistry(object):
    def __init__(self, path):
        self.path = path

    def read_profile_path(self, sid):
        return self.path


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

    def test_legacy_registry_restores_exact_present_and_absent_values(self):
        api = FakeRegistryApi()
        store = OperatorRegistryStore(
            "S-1-5-21-1-2-3-1001", "C:\\Users\\test", api=api
        )
        store.apply(r"Software\Kiosk", "Value", 4, 1)
        present = store.capture(r"Software\Kiosk", "Value")
        store.apply(r"Software\Kiosk", "Value", 4, 2)
        store.restore(present)
        self.assertTrue(store.verify_snapshot(present))

        absent = RegistryValueSnapshot(r"Software\Kiosk", "Missing", False)
        store.apply(r"Software\Kiosk", "Missing", 4, 1)
        store.restore(absent)
        self.assertTrue(store.verify_snapshot(absent))
        self.assertTrue(api.unmounted)

    def test_legacy_acl_protects_operator_read_execute_and_restores(self):
        path = os.path.join(self.directory, "launcher.exe")
        open(path, "wb").close()
        native = FakeAclNative()
        manager = FileAclManager([self.directory], native=native)
        snapshot = manager.capture(path)

        protected = manager.protect_for_operator(
            path, "S-1-5-21-1-2-3-1001", execute=True
        )
        self.assertIn("GRGX;;;S-1-5-21-1-2-3-1001", protected)
        manager.restore(snapshot)
        self.assertTrue(manager.verify_snapshot(snapshot))

        restored = AclSnapshot.from_dict(snapshot.to_dict())
        self.assertEqual(snapshot.sddl, restored.sddl)

    def test_legacy_profile_and_artifacts_install_then_restore_exact_bytes(self):
        profile = os.path.join(self.directory, "profile")
        os.makedirs(profile)
        open(os.path.join(profile, "NTUSER.DAT"), "wb").close()
        locator = WindowsProfileLocator(registry=FakeProfileRegistry(profile))
        self.assertEqual(
            os.path.normcase(os.path.realpath(profile)),
            locator.get_profile_path("S-1-5-21-1-2-3-1001"),
        )

        source = os.path.join(self.directory, "source.exe")
        target = os.path.join(self.directory, "target.exe")
        with open(source, "wb") as stream:
            stream.write(b"new")
        with open(target, "wb") as stream:
            stream.write(b"old")
        manager = FileArtifactManager([(source, target)], [self.directory])
        snapshot = manager.capture()
        manager.install()
        self.assertTrue(manager.verify())
        manager.restore(snapshot)
        with open(target, "rb") as stream:
            self.assertEqual(b"old", stream.read())
        self.assertTrue(manager.verify_snapshot(snapshot))

    def test_legacy_install_then_restore_is_shell_last_and_reversible(self):
        source_launcher = os.path.join(self.directory, "source-launcher.exe")
        source_config = os.path.join(self.directory, "source-kiosk.json")
        install_directory = os.path.join(self.directory, "installed")
        launcher = os.path.join(install_directory, "KioskLauncherLegacy.exe")
        config_path = os.path.join(install_directory, "config", "kiosk.json")
        allowed = os.path.join(self.directory, "allowed.exe")
        profile = os.path.join(self.directory, "profile")
        os.makedirs(profile)
        open(os.path.join(profile, "NTUSER.DAT"), "wb").close()
        for path, data in (
            (source_launcher, b"launcher"),
            (source_config, b"{}"),
            (allowed, b"allowed"),
        ):
            with open(path, "wb") as stream:
                stream.write(data)

        calls = []
        identity = OperatorIdentity(
            "test", "S-1-5-21-1-2-3-1001", True, False
        )
        preflight = FakeAccountApi(identity=identity)
        profile_locator = WindowsProfileLocator(registry=FakeProfileRegistry(profile))
        registry_api = FakeRegistryApi()
        registry_factory = lambda sid, path: OperatorRegistryStore(sid, path, registry_api)
        acl = FileAclManager([install_directory], native=FakeAclNative())
        artifacts = FileArtifactManager(
            [(source_launcher, launcher), (source_config, config_path)],
            [install_directory],
        )
        backup = BackupStore(os.path.join(self.directory, "backup.json"), FakeAcl())
        service = InstallService(
            preflight=OperatorPreflight(preflight),
            profile_locator=profile_locator,
            registry_factory=registry_factory,
            acl_manager=acl,
            artifacts=artifacts,
            backup_store=backup,
            install_directory=install_directory,
            launcher_path=launcher,
            config_path=config_path,
        )
        config = {
            "operatorUser": "test",
            "allowedApplication": {"path": allowed},
        }

        installed = service.apply(config, '"{0}"'.format(launcher))

        self.assertTrue(installed.succeeded)
        self.assertEqual("set_operator_shell", installed.operation_ids[-1])
        self.assertTrue(os.path.isfile(launcher))
        restored = RestoreService(
            backup, OperatorPreflight(preflight), profile_locator,
            registry_factory, acl, artifacts
        ).restore()
        self.assertEqual((), restored.failures)
        self.assertTrue(restored.succeeded)
        self.assertFalse(os.path.exists(launcher))
        self.assertFalse(os.path.exists(config_path))


if __name__ == "__main__":
    unittest.main()
