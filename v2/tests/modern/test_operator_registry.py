# -*- coding: utf-8 -*-
import inspect
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform import operator_registry
from kiosk_v2_modern.platform.operator_registry import (
    OPERATOR_POLICY_VALUES,
    OperatorRegistryStore,
    RegistryValueSnapshot,
)


class FakeRegistryApi(object):
    def __init__(self):
        self.values = {}
        self.mounts = []
        self.unmounts = []
        self.writes = []
        self.deletes = []
        self.fail_read = False

    def mount_operator_hive(self, sid, profile_path):
        self.mounts.append((sid, profile_path))
        return "ROOT:" + sid

    def unmount_operator_hive(self, root):
        self.unmounts.append(root)

    def read_value(self, root, key_path, value_name):
        if self.fail_read:
            raise OSError("read failed")
        key = (root, key_path, value_name)
        return self.values.get(key)

    def write_value(self, root, key_path, value_name, value_type, value_data):
        key = (root, key_path, value_name)
        self.values[key] = (value_type, value_data)
        self.writes.append((root, key_path, value_name, value_type, value_data))

    def delete_value(self, root, key_path, value_name):
        key = (root, key_path, value_name)
        self.values.pop(key, None)
        self.deletes.append((root, key_path, value_name))


class OperatorRegistryTests(unittest.TestCase):
    def make_store(self, api):
        return OperatorRegistryStore(
            "S-1-5-21-1-2-3-1001",
            r"C:\Users\test",
            api=api,
        )

    def test_capture_preserves_exact_present_type_and_data(self):
        api = FakeRegistryApi()
        root = "ROOT:S-1-5-21-1-2-3-1001"
        api.values[(root, r"Software\Kiosk", "Setting")] = (4, 7)

        snapshot = self.make_store(api).capture(r"Software\Kiosk", "Setting")

        self.assertTrue(snapshot.existed)
        self.assertEqual(4, snapshot.value_type)
        self.assertEqual(7, snapshot.value_data)
        self.assertEqual([(self.make_store(api).operator_sid, r"C:\Users\test")], api.mounts)
        self.assertEqual([root], api.unmounts)

    def test_capture_absent_value_and_unmount_on_read_failure(self):
        api = FakeRegistryApi()
        snapshot = self.make_store(api).capture(r"Software\Kiosk", "Missing")
        self.assertFalse(snapshot.existed)
        self.assertIsNone(snapshot.value_type)

        api.fail_read = True
        with self.assertRaises(OSError):
            self.make_store(api).capture(r"Software\Kiosk", "Setting")
        self.assertEqual(2, len(api.unmounts))

    def test_apply_and_verify_use_only_operator_sid_root(self):
        api = FakeRegistryApi()
        store = self.make_store(api)

        store.apply(r"Software\Kiosk", "Setting", 4, 1)

        self.assertTrue(store.verify(r"Software\Kiosk", "Setting", 4, 1))
        self.assertEqual(
            "ROOT:S-1-5-21-1-2-3-1001",
            api.writes[0][0],
        )

    def test_restore_deletes_originally_absent_value(self):
        api = FakeRegistryApi()
        store = self.make_store(api)
        store.apply(r"Software\Kiosk", "Setting", 4, 1)
        snapshot = RegistryValueSnapshot(
            r"Software\Kiosk",
            "Setting",
            existed=False,
        )

        store.restore(snapshot)

        self.assertEqual(
            [("ROOT:S-1-5-21-1-2-3-1001", r"Software\Kiosk", "Setting")],
            api.deletes,
        )
        self.assertTrue(store.verify_snapshot(snapshot))

    def test_restore_recreates_original_type_and_data(self):
        api = FakeRegistryApi()
        store = self.make_store(api)
        snapshot = RegistryValueSnapshot(
            r"Software\Kiosk",
            "Setting",
            existed=True,
            value_type=1,
            value_data="original",
        )

        store.restore(snapshot)

        self.assertTrue(store.verify_snapshot(snapshot))
        self.assertEqual((1, "original"), api.values[(
            "ROOT:S-1-5-21-1-2-3-1001",
            r"Software\Kiosk",
            "Setting",
        )])

    def test_snapshot_json_round_trip_preserves_binary_and_multi_string(self):
        for value_type, value_data in ((3, b"\x00\xff"), (7, ["a", "b"])):
            original = RegistryValueSnapshot(
                r"Software\Kiosk",
                "Setting",
                True,
                value_type,
                value_data,
            )

            restored = RegistryValueSnapshot.from_dict(original.to_dict())

            self.assertEqual(original.value_type, restored.value_type)
            self.assertEqual(original.value_data, restored.value_data)

    def test_policy_allowlist_contains_shell_and_operator_restrictions_only(self):
        names = [item[1] for item in OPERATOR_POLICY_VALUES]

        self.assertEqual(
            [
                "DisableTaskMgr",
                "DisableRegistryTools",
                "DisableCMD",
                "NoRun",
                "NoControlPanel",
                "NoViewContextMenu",
                "NoTrayContextMenu",
                "NoSetTaskbar",
                "NoWinKeys",
            ],
            names,
        )
        self.assertNotIn("Shell", names)

    def test_source_never_writes_current_administrator_hkcu(self):
        source = inspect.getsource(operator_registry)

        self.assertNotIn("HKEY_CURRENT_USER", source)
        self.assertNotIn("HKCU", source)
        self.assertNotIn("subprocess", source)


class NativeHiveUnloadTests(unittest.TestCase):
    def test_only_owned_hives_are_unloaded_and_errors_preserve_ownership(self):
        from kiosk_v2_modern.platform.operator_registry import WindowsRegistryApi, winreg

        class Native(object):
            def __init__(self):
                self.calls = []
                self.status = 5

            def RegUnLoadKeyW(self, parent, name):
                self.calls.append((parent, name))
                return self.status

        native = Native()
        api = WindowsRegistryApi.__new__(WindowsRegistryApi)
        api.advapi32 = native
        api._loaded_roots = set(("KioskV2_test",))
        api.unmount_operator_hive("already_logged_in")
        self.assertEqual([], native.calls)
        with self.assertRaises(OSError):
            api.unmount_operator_hive("KioskV2_test")
        self.assertIn("KioskV2_test", api._loaded_roots)
        native.status = 0
        api.unmount_operator_hive("KioskV2_test")
        self.assertEqual([(winreg.HKEY_USERS, "KioskV2_test")] * 2, native.calls)
        self.assertFalse(api._loaded_roots)


if __name__ == "__main__":
    unittest.main()
