# -*- coding: utf-8 -*-
import inspect
import os
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform import file_acl
from kiosk_v2_modern.platform.file_acl import (
    AclSnapshot,
    FileAclManager,
    PathNotApprovedError,
)


class FakeAclNative(object):
    def __init__(self):
        self.sddl = {}
        self.applied = []

    def capture_sddl(self, path):
        return self.sddl.get(self._normalize(path), "D:(A;;FA;;;BA)")

    def apply_sddl(self, path, sddl):
        normalized = self._normalize(path)
        self.sddl[normalized] = sddl
        self.applied.append((normalized, sddl))

    def _normalize(self, path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class FileAclTests(unittest.TestCase):
    def test_capture_and_restore_preserve_exact_dacl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "KioskLauncher.exe")
            open(path, "wb").close()
            native = FakeAclNative()
            original = "D:AI(A;;FA;;;BA)(A;;GR;;;BU)"
            native.sddl[native._normalize(path)] = original
            manager = FileAclManager([directory], native=native)

            snapshot = manager.capture(path)
            manager.protect_for_operator(path, "S-1-5-21-1-2-3-1001", execute=True)
            manager.restore(snapshot)

            self.assertTrue(snapshot.existed)
            self.assertEqual(original, snapshot.sddl)
            self.assertTrue(manager.verify_snapshot(snapshot))

    def test_config_acl_grants_operator_read_but_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "kiosk.json")
            open(path, "wb").close()
            native = FakeAclNative()
            manager = FileAclManager([directory], native=native)

            sddl = manager.protect_for_operator(
                path,
                "S-1-5-21-1-2-3-1001",
                execute=False,
            )

            self.assertIn("(A;;GR;;;S-1-5-21-1-2-3-1001)", sddl)
            self.assertNotIn("GW;;;S-1-5-21-1-2-3-1001", sddl)
            self.assertNotIn("GA;;;S-1-5-21-1-2-3-1001", sddl)
            self.assertTrue(manager.verify(path, sddl))

    def test_directory_acl_is_inheritable_read_execute_only(self):
        with tempfile.TemporaryDirectory() as directory:
            native = FakeAclNative()
            manager = FileAclManager([directory], native=native)

            sddl = manager.protect_for_operator(
                directory,
                "S-1-5-21-1-2-3-1001",
                execute=True,
            )

            self.assertIn("(A;OICI;GRGX;;;S-1-5-21-1-2-3-1001)", sddl)
            self.assertIn("(A;OICI;FA;;;SY)", sddl)
            self.assertIn("(A;OICI;FA;;;BA)", sddl)

    def test_backup_acl_excludes_operator_and_other_users(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "backup.json")
            open(path, "wb").close()
            native = FakeAclNative()
            manager = FileAclManager([directory], native=native)

            sddl = manager.protect_backup(path)

            self.assertEqual("D:P(A;;FA;;;SY)(A;;FA;;;BA)", sddl)
            self.assertNotIn("BU", sddl)

    def test_path_outside_approved_roots_is_rejected_before_native_call(self):
        with tempfile.TemporaryDirectory() as directory:
            native = FakeAclNative()
            manager = FileAclManager([os.path.join(directory, "approved")], native=native)
            outside = os.path.join(directory, "outside.exe")
            open(outside, "wb").close()

            with self.assertRaises(PathNotApprovedError):
                manager.capture(outside)
            with self.assertRaises(PathNotApprovedError):
                manager.protect_for_operator(outside, "S-1-5-21-1-2-3-1001", True)

            self.assertEqual([], native.applied)

    def test_missing_path_snapshot_round_trips_without_acl_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "future.exe")
            native = FakeAclNative()
            manager = FileAclManager([directory], native=native)

            snapshot = manager.capture(path)
            restored = AclSnapshot.from_dict(snapshot.to_dict())
            manager.restore(restored)

            self.assertFalse(restored.existed)
            self.assertEqual([], native.applied)

    def test_source_uses_security_descriptor_api_not_command_tools(self):
        source = inspect.getsource(file_acl)

        self.assertIn("GetNamedSecurityInfoW", source)
        self.assertIn("SetNamedSecurityInfoW", source)
        self.assertNotIn("icacls", source.lower())
        self.assertNotIn("subprocess", source.lower())


if __name__ == "__main__":
    unittest.main()
