# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.restore_service import RestoreService
from kiosk_v2_modern.platform.operator_account import OperatorIdentity
from kiosk_v2_modern.platform.operator_registry import RegistryValueSnapshot
from kiosk_v2_modern.platform.file_acl import AclSnapshot


def backup_document():
    registry = [
        RegistryValueSnapshot(r"Software\Kiosk", "NoRun", False).to_dict(),
        RegistryValueSnapshot(
            r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
            "Shell",
            True,
            1,
            "explorer.exe",
        ).to_dict(),
    ]
    acls = [AclSnapshot(r"C:\ProgramData\Kiosk\KioskLauncher.exe", True, "D:AI").to_dict()]
    return {
        "schemaVersion": 2,
        "buildFamily": "modern",
        "operatorSid": "S-1-5-21-1-2-3-1001",
        "operatorUser": "test",
        "originalShell": "explorer.exe",
        "registryValues": registry,
        "fileAcls": acls,
        "configBackup": {"files": [], "ownedPaths": []},
        "integritySha256": "a" * 64,
    }


class FakeBackupStore(object):
    def __init__(self, calls, document=None, failure=None):
        self.calls = calls
        self.document = document or backup_document()
        self.failure = failure

    def load(self, expected_build_family=None, expected_operator_sid=None):
        self.calls.append(("load_backup", expected_build_family, expected_operator_sid))
        if self.failure:
            raise self.failure
        return self.document


class FakePreflight(object):
    def __init__(self, calls, sid="S-1-5-21-1-2-3-1001"):
        self.calls = calls
        self.identity = OperatorIdentity("test", sid, True, False)

    def validate(self, username):
        self.calls.append("preflight:" + username)
        return self.identity


class FakeProfileLocator(object):
    def get_profile_path(self, sid):
        return r"C:\Users\test"


class FakeRestoreRegistry(object):
    def __init__(self, calls, failure_name=None):
        self.calls = calls
        self.failure_name = failure_name

    def restore(self, snapshot):
        self.calls.append("restore_registry:" + snapshot.value_name)
        if snapshot.value_name == self.failure_name:
            raise RuntimeError("injected registry restore failure")

    def verify_snapshot(self, snapshot):
        self.calls.append("verify_registry:" + snapshot.value_name)
        return True


class FakeRestoreAcl(object):
    def __init__(self, calls, fail=False):
        self.calls = calls
        self.fail = fail

    def restore(self, snapshot):
        self.calls.append("restore_acl:" + os.path.basename(snapshot.path))
        if self.fail:
            raise RuntimeError("injected ACL failure")

    def verify_snapshot(self, snapshot):
        self.calls.append("verify_acl:" + os.path.basename(snapshot.path))
        return True


class FakeRestoreArtifacts(object):
    def __init__(self, calls, fail=False):
        self.calls = calls
        self.fail = fail

    def restore(self, snapshot):
        self.calls.append("restore_artifacts")
        if self.fail:
            raise RuntimeError("injected artifact failure")

    def verify_snapshot(self, snapshot):
        self.calls.append("verify_artifacts")
        return True

    def remove_owned(self, snapshot):
        self.calls.append("remove_owned")


class FakeRecoveryApi(object):
    def __init__(self, explorer_running=False):
        self.explorer = explorer_running
        self.calls = []

    def restore_shell_surfaces(self):
        self.calls.append("restore_surfaces")

    def explorer_running(self):
        self.calls.append("check_explorer")
        return self.explorer

    def start_explorer(self):
        self.calls.append("start_explorer")
        self.explorer = True


class RestoreServiceTests(unittest.TestCase):
    def make_service(
        self,
        calls,
        document=None,
        backup_failure=None,
        registry_failure=None,
        acl_failure=False,
        artifact_failure=False,
        sid="S-1-5-21-1-2-3-1001",
    ):
        registry = FakeRestoreRegistry(calls, registry_failure)
        return RestoreService(
            backup_store=FakeBackupStore(calls, document, backup_failure),
            preflight=FakePreflight(calls, sid=sid),
            profile_locator=FakeProfileLocator(),
            registry_factory=lambda operator_sid, profile_path: registry,
            acl_manager=FakeRestoreAcl(calls, acl_failure),
            artifacts=FakeRestoreArtifacts(calls, artifact_failure),
        )

    def test_invalid_backup_aborts_before_operator_or_restore_calls(self):
        calls = []
        service = self.make_service(calls, backup_failure=ValueError("bad backup"))

        with self.assertRaises(ValueError):
            service.restore()

        self.assertEqual([("load_backup", "modern", None)], calls)

    def test_operator_sid_mismatch_aborts_before_any_restore(self):
        calls = []
        service = self.make_service(calls, sid="S-1-5-21-other")

        with self.assertRaises(ValueError):
            service.restore()

        self.assertFalse(any(str(call).startswith("restore_") for call in calls))

    def test_restore_returns_every_registry_acl_and_artifact_snapshot(self):
        calls = []
        service = self.make_service(calls)

        result = service.restore()

        self.assertTrue(result.succeeded)
        self.assertEqual((), result.failures)
        self.assertIn("restore_registry:NoRun", calls)
        self.assertIn("restore_registry:Shell", calls)
        self.assertIn("restore_acl:KioskLauncher.exe", calls)
        self.assertIn("restore_artifacts", calls)

    def test_artifact_bytes_are_restored_before_original_acls(self):
        calls = []
        service = self.make_service(calls)

        service.restore()

        self.assertLess(
            calls.index("restore_artifacts"),
            calls.index("restore_acl:KioskLauncher.exe"),
        )

    def test_restore_continues_after_each_item_failure_and_reports_all(self):
        calls = []
        service = self.make_service(
            calls,
            registry_failure="NoRun",
            acl_failure=True,
            artifact_failure=True,
        )

        result = service.restore()

        self.assertFalse(result.succeeded)
        self.assertEqual(
            (
                "artifacts",
                "acl:KioskLauncher.exe",
                "registry:NoRun",
            ),
            result.failures,
        )
        self.assertIn("restore_registry:Shell", calls)

    def test_uninstall_removes_owned_files_only_after_successful_restore(self):
        success_calls = []
        success = self.make_service(success_calls)
        self.assertTrue(success.uninstall().succeeded)
        self.assertEqual("remove_owned", success_calls[-1])

        failed_calls = []
        failed = self.make_service(failed_calls, acl_failure=True)
        self.assertFalse(failed.uninstall().succeeded)
        self.assertNotIn("remove_owned", failed_calls)

    def test_recover_desktop_restores_surfaces_and_starts_at_most_one_explorer(self):
        for running, expected in (
            (False, ["restore_surfaces", "check_explorer", "start_explorer"]),
            (True, ["restore_surfaces", "check_explorer"]),
        ):
            recovery = FakeRecoveryApi(explorer_running=running)
            service = self.make_service([])

            service.recover_desktop(recovery)

            self.assertEqual(expected, recovery.calls)


if __name__ == "__main__":
    unittest.main()
