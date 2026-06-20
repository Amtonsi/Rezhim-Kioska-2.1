# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.install_artifacts import (
    FileArtifactManager,
    InvalidArtifactSnapshot,
)
from kiosk_v2_modern.platform.profile_path import (
    ProfilePathError,
    WindowsProfileLocator,
)


class FakeProfileRegistry(object):
    def __init__(self, value):
        self.value = value
        self.sids = []

    def read_profile_path(self, sid):
        self.sids.append(sid)
        return self.value


class FailSecondWriteArtifactManager(FileArtifactManager):
    def __init__(self, *args, **kwargs):
        FileArtifactManager.__init__(self, *args, **kwargs)
        self.write_count = 0
        self.failed = False

    def _atomic_write(self, path, data):
        self.write_count += 1
        if self.write_count == 2 and not self.failed:
            self.failed = True
            raise OSError("injected write failure")
        return FileArtifactManager._atomic_write(self, path, data)


class InstallArtifactTests(unittest.TestCase):
    def test_profile_locator_expands_and_requires_existing_ntuser_hive(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = os.path.join(directory, "test")
            os.makedirs(profile)
            open(os.path.join(profile, "NTUSER.DAT"), "wb").close()
            registry = FakeProfileRegistry(r"%KIOSK_PROFILE%")
            locator = WindowsProfileLocator(
                registry=registry,
                environment={"KIOSK_PROFILE": profile},
            )

            result = locator.get_profile_path("S-1-5-21-1-2-3-1001")

            self.assertEqual(os.path.normcase(os.path.realpath(profile)), result)
            self.assertEqual(["S-1-5-21-1-2-3-1001"], registry.sids)

    def test_profile_locator_rejects_missing_or_relative_profile(self):
        for value in (None, "relative", r"C:\missing-kiosk-profile"):
            locator = WindowsProfileLocator(registry=FakeProfileRegistry(value))
            with self.assertRaises(ProfilePathError):
                locator.get_profile_path("S-1-5-21-1-2-3-1001")

    def test_install_verify_and_restore_preserve_exact_previous_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source_directory = os.path.join(directory, "source")
            target_directory = os.path.join(directory, "target")
            os.makedirs(source_directory)
            os.makedirs(target_directory)
            source_a = os.path.join(source_directory, "launcher.exe")
            source_b = os.path.join(source_directory, "kiosk.json")
            target_a = os.path.join(target_directory, "launcher.exe")
            target_b = os.path.join(target_directory, "config", "kiosk.json")
            with open(source_a, "wb") as stream:
                stream.write(b"new launcher")
            with open(source_b, "wb") as stream:
                stream.write(b"new config")
            with open(target_a, "wb") as stream:
                stream.write(b"old launcher")
            manager = FileArtifactManager(
                [(source_a, target_a), (source_b, target_b)],
                [target_directory],
            )

            snapshot = manager.capture()
            manager.install()

            self.assertTrue(manager.verify())
            with open(target_a, "rb") as stream:
                self.assertEqual(b"new launcher", stream.read())
            self.assertTrue(os.path.isfile(target_b))

            manager.restore(snapshot)

            with open(target_a, "rb") as stream:
                self.assertEqual(b"old launcher", stream.read())
            self.assertFalse(os.path.exists(target_b))
            self.assertTrue(manager.verify_snapshot(snapshot))

    def test_partial_install_failure_restores_all_previous_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            source_a = os.path.join(directory, "source-a")
            source_b = os.path.join(directory, "source-b")
            target_a = os.path.join(directory, "target-a")
            target_b = os.path.join(directory, "target-b")
            for path, data in ((source_a, b"new-a"), (source_b, b"new-b"), (target_a, b"old-a")):
                with open(path, "wb") as stream:
                    stream.write(data)
            manager = FailSecondWriteArtifactManager(
                [(source_a, target_a), (source_b, target_b)],
                [directory],
            )
            manager.capture()

            with self.assertRaises(OSError):
                manager.install()

            with open(target_a, "rb") as stream:
                self.assertEqual(b"old-a", stream.read())
            self.assertFalse(os.path.exists(target_b))

    def test_tampered_snapshot_is_rejected_before_target_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source")
            target = os.path.join(directory, "target")
            with open(source, "wb") as stream:
                stream.write(b"new")
            with open(target, "wb") as stream:
                stream.write(b"old")
            manager = FileArtifactManager([(source, target)], [directory])
            snapshot = manager.capture()
            snapshot["files"][0]["data"] = "dGFtcGVyZWQ="

            with self.assertRaises(InvalidArtifactSnapshot):
                manager.restore(snapshot)

            with open(target, "rb") as stream:
                self.assertEqual(b"old", stream.read())

    def test_targets_outside_approved_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source")
            open(source, "wb").close()
            with self.assertRaises(ValueError):
                FileArtifactManager(
                    [(source, os.path.join(directory, "outside.exe"))],
                    [os.path.join(directory, "approved")],
                )

    def test_snapshot_is_json_serializable_and_remove_owned_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source")
            target = os.path.join(directory, "target")
            with open(source, "wb") as stream:
                stream.write(b"new")
            manager = FileArtifactManager([(source, target)], [directory])
            snapshot = manager.capture()
            json.dumps(snapshot)
            manager.install()

            manager.remove_owned(snapshot)

            self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
