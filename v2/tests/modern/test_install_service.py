# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.install_service import InstallService
from kiosk_v2_modern.platform.file_acl import AclSnapshot
from kiosk_v2_modern.platform.operator_account import OperatorIdentity
from kiosk_v2_modern.platform.operator_registry import RegistryValueSnapshot


def config_for(app_path):
    return {
        "operatorUser": "test",
        "allowedApplication": {"path": app_path},
    }


class FakePreflight(object):
    def __init__(self, calls):
        self.calls = calls
        self.identity = OperatorIdentity(
            "test", "S-1-5-21-1-2-3-1001", True, False
        )

    def validate(self, username):
        self.calls.append("preflight")
        return self.identity


class FakeProfileLocator(object):
    def __init__(self, calls):
        self.calls = calls

    def get_profile_path(self, sid):
        self.calls.append("profile")
        return r"C:\Users\test"


class FakeRegistry(object):
    def __init__(self, calls, failure_name=None):
        self.calls = calls
        self.failure_name = failure_name
        self.snapshots = {}

    def capture(self, key_path, value_name):
        self.calls.append("capture_registry:" + value_name)
        snapshot = RegistryValueSnapshot(key_path, value_name, False)
        self.snapshots[value_name] = snapshot
        return snapshot

    def apply(self, key_path, value_name, value_type, value_data):
        self.calls.append("apply_registry:" + value_name)
        if self.failure_name == value_name:
            raise RuntimeError("injected registry failure")

    def verify(self, key_path, value_name, value_type, value_data):
        self.calls.append("verify_registry:" + value_name)
        return True

    def restore(self, snapshot):
        self.calls.append("restore_registry:" + snapshot.value_name)


class FakeRegistryFactory(object):
    def __init__(self, registry):
        self.registry = registry
        self.args = []

    def __call__(self, sid, profile_path):
        self.args.append((sid, profile_path))
        return self.registry


class FakeAcl(object):
    def __init__(self, calls):
        self.calls = calls

    def capture(self, path):
        self.calls.append("capture_acl:" + os.path.basename(path))
        return AclSnapshot(path, os.path.exists(path), "D:(A;;FA;;;BA)" if os.path.exists(path) else None)

    def protect_for_operator(self, path, sid, execute=False):
        self.calls.append("protect_acl:" + os.path.basename(path))
        return "D:P"

    def verify(self, path, expected):
        self.calls.append("verify_acl:" + os.path.basename(path))
        return True

    def restore(self, snapshot):
        self.calls.append("restore_acl:" + os.path.basename(snapshot.path))


class FakeArtifacts(object):
    def __init__(self, calls):
        self.calls = calls
        self.snapshot = {
            "path": r"C:\ProgramData\Kiosk\config\kiosk.json",
            "existed": False,
            "encoding": "base64",
            "data": "",
            "ownedPaths": [],
        }

    def capture(self):
        self.calls.append("capture_artifacts")
        return dict(self.snapshot)

    def install(self):
        self.calls.append("install_artifacts")

    def verify(self):
        self.calls.append("verify_artifacts")
        return True

    def restore(self, snapshot):
        self.calls.append("restore_artifacts")


class FakeBackupStore(object):
    def __init__(self, calls):
        self.calls = calls
        self.saved = None
        self.path = r"C:\ProgramData\Kiosk\backups\backup.json"

    def save(self, metadata):
        self.calls.append("save_backup")
        self.saved = dict(metadata)
        result = dict(metadata)
        result["integritySha256"] = "a" * 64
        return result

    def load(self, expected_build_family=None, expected_operator_sid=None):
        self.calls.append("verify_backup")
        result = dict(self.saved)
        result["integritySha256"] = "a" * 64
        return result


class InstallServiceTests(unittest.TestCase):
    def make_fixture(self, directory, failure_name=None):
        calls = []
        app_path = os.path.join(directory, "allowed.exe")
        launcher_path = os.path.join(directory, "KioskLauncher.exe")
        config_path = os.path.join(directory, "config", "kiosk.json")
        os.makedirs(os.path.dirname(config_path))
        for path in (app_path, launcher_path, config_path):
            open(path, "wb").close()
        registry = FakeRegistry(calls, failure_name=failure_name)
        service = InstallService(
            preflight=FakePreflight(calls),
            profile_locator=FakeProfileLocator(calls),
            registry_factory=FakeRegistryFactory(registry),
            acl_manager=FakeAcl(calls),
            artifacts=FakeArtifacts(calls),
            backup_store=FakeBackupStore(calls),
            install_directory=directory,
            launcher_path=launcher_path,
            config_path=config_path,
        )
        return service, calls, app_path

    def test_dry_run_is_side_effect_free_and_shell_is_last(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, app_path = self.make_fixture(directory)

            result = service.apply(
                config_for(app_path),
                launcher_command='"{0}"'.format(service.launcher_path),
                dry_run=True,
            )

            self.assertTrue(result.dry_run)
            self.assertIsNone(result.backup_path)
            self.assertEqual("set_operator_shell", result.operation_ids[-1])
            self.assertNotIn("save_backup", calls)
            self.assertFalse(any(call.startswith("apply_") for call in calls))
            self.assertNotIn("install_artifacts", calls)

    def test_apply_saves_complete_backup_before_first_write_and_shell_last(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, app_path = self.make_fixture(directory)

            result = service.apply(
                config_for(app_path),
                launcher_command='"{0}"'.format(service.launcher_path),
            )

            self.assertTrue(result.succeeded)
            first_write = min(
                calls.index("install_artifacts"),
                min(index for index, call in enumerate(calls) if call.startswith("protect_acl:")),
                min(index for index, call in enumerate(calls) if call.startswith("apply_registry:")),
            )
            self.assertLess(calls.index("save_backup"), first_write)
            apply_registry = [call for call in calls if call.startswith("apply_registry:")]
            self.assertEqual("apply_registry:Shell", apply_registry[-1])
            self.assertEqual("verify_backup", calls[-1])
            self.assertEqual("modern", service.backup_store.saved["buildFamily"])
            self.assertEqual(
                "S-1-5-21-1-2-3-1001",
                service.backup_store.saved["operatorSid"],
            )
            self.assertTrue(service.backup_store.saved["registryValues"])
            self.assertTrue(service.backup_store.saved["fileAcls"])

    def test_policy_failure_rolls_back_completed_registry_acl_and_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, app_path = self.make_fixture(
                directory,
                failure_name="NoRun",
            )

            with self.assertRaises(Exception):
                service.apply(
                    config_for(app_path),
                    launcher_command='"{0}"'.format(service.launcher_path),
                )

            self.assertIn("save_backup", calls)
            self.assertNotIn("apply_registry:Shell", calls)
            self.assertIn("restore_artifacts", calls)
            rollback_positions = [
                index
                for index, call in enumerate(calls)
                if call.startswith("restore_registry:")
                or call.startswith("restore_acl:")
                or call == "restore_artifacts"
            ]
            self.assertEqual(sorted(rollback_positions), rollback_positions)

    def test_external_allowed_application_is_validated_but_acl_is_untouched(self):
        with tempfile.TemporaryDirectory() as install_directory:
            with tempfile.TemporaryDirectory() as external_directory:
                service, calls, _ = self.make_fixture(install_directory)
                external_app = os.path.join(external_directory, "external.exe")
                open(external_app, "wb").close()

                service.apply(
                    config_for(external_app),
                    launcher_command='"{0}"'.format(service.launcher_path),
                )

                external_name = os.path.basename(external_app)
                self.assertNotIn("capture_acl:" + external_name, calls)
                self.assertNotIn("protect_acl:" + external_name, calls)

    def test_clean_install_allows_launcher_target_to_be_created_by_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, app_path = self.make_fixture(directory)
            os.remove(service.launcher_path)

            result = service.apply(
                config_for(app_path),
                launcher_command='"{0}"'.format(service.launcher_path),
            )

            self.assertTrue(result.succeeded)
            self.assertIn("install_artifacts", calls)

    def test_missing_or_non_exe_allowed_application_aborts_before_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, _ = self.make_fixture(directory)
            for path in (os.path.join(directory, "missing.exe"), os.path.join(directory, "bad.txt")):
                if path.endswith(".txt"):
                    open(path, "wb").close()
                with self.assertRaises(ValueError):
                    service.apply(
                        config_for(path),
                        launcher_command='"{0}"'.format(service.launcher_path),
                    )
            self.assertNotIn("save_backup", calls)

    def test_repair_reapplies_configuration_without_replacing_original_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            service, calls, app_path = self.make_fixture(directory)
            service.backup_store.saved = {
                "schemaVersion": 2,
                "buildFamily": "modern",
                "operatorSid": "S-1-5-21-1-2-3-1001",
                "operatorUser": "test",
                "originalShell": "explorer.exe",
                "registryValues": [],
                "fileAcls": [],
                "configBackup": {},
            }

            result = service.repair(
                config_for(app_path),
                launcher_command='"{0}"'.format(service.launcher_path),
            )

            self.assertTrue(result.succeeded)
            self.assertNotIn("save_backup", calls)
            self.assertIn("install_artifacts", calls)
            self.assertEqual("apply_registry:Shell", [
                call for call in calls if call.startswith("apply_registry:")
            ][-1])


if __name__ == "__main__":
    unittest.main()
