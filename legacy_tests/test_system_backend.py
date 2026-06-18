# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import unittest

from legacy_kiosk.backup_store import BackupError, LegacyBackupStore
from legacy_kiosk.system_backend import (
    AccessDeniedError,
    INSTALL_ORDER,
    LegacyInstallContext,
    LegacySystemBackend,
    LegacyTransaction,
    NativeAccountInspectionApi,
    NativeFileSecurityApi,
    NativeOperatorRegistryApi,
    WindowsAccountInspector,
    WindowsFileSecurity,
    WindowsOperatorRegistry,
    create_windows_system_backend,
)


class RecordingTransactionBackend(object):
    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.calls = []

    def __getattr__(self, name):
        if name in INSTALL_ORDER:
            def execute(context):
                self.calls.append(("apply", name))
                if name == self.fail_on:
                    raise RuntimeError("planned failure")
            return execute
        raise AttributeError(name)

    def rollback(self, operation_name, context):
        self.calls.append(("rollback", operation_name))


class FakeAccountInspector(object):
    def __init__(self, is_admin=True, operator_is_admin=False):
        self.is_admin = is_admin
        self.operator_is_admin = operator_is_admin

    def is_current_process_admin(self):
        return self.is_admin

    def inspect_local_operator(self, account_name):
        return {
            "account_name": account_name,
            "sid": "S-1-5-21-100-200-300-1001",
            "profile_path": r"C:\Documents and Settings\test",
            "is_admin": self.operator_is_admin,
        }


class FakeRegistryAdapter(object):
    def __init__(self):
        self.snapshots = [
            {
                "group": "policy",
                "key": r"Software\Policies\Kiosk",
                "name": "NoRun",
                "exists": True,
                "type": 4,
                "data": 0,
            },
            {
                "group": "shell",
                "key": r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
                "name": "Shell",
                "exists": False,
                "type": None,
                "data": None,
            },
        ]
        self.writes = []
        self.restores = []

    def snapshot_values(self, operator_sid, profile_path, targets):
        return list(self.snapshots)

    def write_values(self, operator_sid, profile_path, targets):
        self.writes.extend(targets)

    def restore_values(self, operator_sid, profile_path, records):
        self.restores.extend(records)

    def verify_values(self, operator_sid, profile_path, targets):
        return True


class FakeSecurityAdapter(object):
    def __init__(self):
        self.snapshots = []
        self.protected = []
        self.restored = []

    def snapshot_paths(self, paths):
        self.snapshots = [{"path": path, "sddl": "D:PAI"} for path in paths]
        return list(self.snapshots)

    def protect_paths(self, paths, operator_sid):
        self.protected.extend(paths)

    def restore_paths(self, records):
        self.restored.extend(records)


class FakeAccountApi(object):
    def is_current_process_admin(self):
        return True

    def resolve_local_account_sid(self, account_name):
        return "S-1-5-21-100-200-300-1001"

    def profile_path_for_sid(self, sid):
        return r"C:\Documents and Settings\test"

    def is_user_local_admin(self, account_name):
        return False


class FakeNativeRegistryApi(object):
    def __init__(self):
        self.values = {}
        self.calls = []

    def with_operator_hive(self, operator_sid, profile_path, callback):
        self.calls.append(("hive", operator_sid, profile_path))
        return callback("mounted")

    def read_value(self, root_name, key_path, value_name):
        return self.values.get((key_path, value_name), (False, None, None))

    def write_value(self, root_name, key_path, value_name, value_type, value_data):
        self.values[(key_path, value_name)] = (True, value_type, value_data)

    def delete_value(self, root_name, key_path, value_name):
        self.values.pop((key_path, value_name), None)


class FakeSecurityApi(object):
    def __init__(self):
        self.sddl = {}
        self.set_calls = []

    def get_sddl(self, path):
        return self.sddl[path]

    def set_sddl(self, path, sddl):
        self.sddl[path] = sddl
        self.set_calls.append((path, sddl))


class LegacySystemBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.backup_path = os.path.join(self.temp_dir, "backup.json")
        self.launcher_path = os.path.join(self.temp_dir, "RezhimKioska-Legacy.exe")
        self.config_path = os.path.join(self.temp_dir, "kiosk.json")
        self.allowed_path = os.path.join(self.temp_dir, "allowed.exe")
        for path in (self.launcher_path, self.config_path, self.allowed_path):
            with open(path, "wb") as stream:
                stream.write(b"test")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _context(self):
        config = {
            "operatorUser": "test",
            "allowedApplication": {"path": self.allowed_path},
        }
        return LegacyInstallContext(
            config=config,
            launcher_path=self.launcher_path,
            config_path=self.config_path,
            backup_path=self.backup_path,
        )

    def test_transaction_applies_backup_before_writes_and_shell_last(self):
        backend = RecordingTransactionBackend()

        LegacyTransaction(backend).apply(self._context())

        self.assertEqual(
            [("apply", name) for name in INSTALL_ORDER], backend.calls
        )
        self.assertLess(
            backend.calls.index(("apply", "create_backup")),
            backend.calls.index(("apply", "protect_files")),
        )
        self.assertLess(
            backend.calls.index(("apply", "apply_operator_policies")),
            backend.calls.index(("apply", "set_operator_shell")),
        )

    def test_launcher_shell_command_places_global_config_before_subcommand(self):
        context = self._context()

        self.assertEqual(
            u'"%s" --config "%s" launch'
            % (self.launcher_path, self.config_path),
            context.launcher_command,
        )

    def test_transaction_rolls_back_completed_steps_in_reverse_order(self):
        backend = RecordingTransactionBackend(fail_on="apply_operator_policies")

        with self.assertRaises(RuntimeError):
            LegacyTransaction(backend).apply(self._context())

        self.assertEqual(
            [
                ("rollback", "apply_operator_policies"),
                ("rollback", "protect_files"),
                ("rollback", "create_backup"),
                ("rollback", "validate_allowed_app"),
                ("rollback", "validate_operator"),
            ],
            [call for call in backend.calls if call[0] == "rollback"],
        )

    def test_backup_and_restore_use_only_recorded_values_and_acls(self):
        registry = FakeRegistryAdapter()
        security = FakeSecurityAdapter()
        backend = LegacySystemBackend(
            account_inspector=FakeAccountInspector(),
            registry_adapter=registry,
            security_adapter=security,
            backup_store=LegacyBackupStore(),
        )
        context = self._context()
        backend.validate_operator(context)
        backend.create_backup(context)

        backend.restore(context)

        self.assertEqual(registry.snapshots, registry.restores)
        self.assertEqual(security.snapshots, security.restored)

    def test_restore_rejects_backup_for_another_operator_sid(self):
        store = LegacyBackupStore()
        store.save(
            self.backup_path,
            {
                "schemaVersion": 1,
                "buildFamily": "legacy",
                "operatorSid": "S-1-5-21-other",
                "registry": [],
                "security": [],
            },
        )
        backend = LegacySystemBackend(
            account_inspector=FakeAccountInspector(),
            registry_adapter=FakeRegistryAdapter(),
            security_adapter=FakeSecurityAdapter(),
            backup_store=store,
        )

        with self.assertRaises(BackupError):
            backend.restore(self._context())

    def test_backend_has_no_forbidden_service_driver_startup_or_mass_kill_operations(self):
        for name in (
            "stop_services",
            "disable_services",
            "disable_drivers",
            "clear_startup",
            "kill_processes",
            "terminate_processes",
        ):
            self.assertFalse(hasattr(LegacySystemBackend, name))

    def test_validate_operator_refuses_without_administrator_rights(self):
        backend = LegacySystemBackend(
            account_inspector=FakeAccountInspector(is_admin=False),
            registry_adapter=FakeRegistryAdapter(),
            security_adapter=FakeSecurityAdapter(),
        )

        with self.assertRaises(AccessDeniedError):
            backend.validate_operator(self._context())

    def test_windows_account_inspector_returns_sid_profile_and_admin_state(self):
        inspector = WindowsAccountInspector(api=FakeAccountApi())

        result = inspector.inspect_local_operator("test")

        self.assertEqual("S-1-5-21-100-200-300-1001", result["sid"])
        self.assertEqual(r"C:\Documents and Settings\test", result["profile_path"])
        self.assertFalse(result["is_admin"])

    def test_registry_adapter_restores_existing_and_absent_values_exactly(self):
        api = FakeNativeRegistryApi()
        api.values[("Software\\Example", "Existing")] = (True, 4, 7)
        adapter = WindowsOperatorRegistry(api=api)
        targets = (
            {
                "group": "policy",
                "key": "Software\\Example",
                "name": "Existing",
                "type": 4,
                "data": 1,
            },
            {
                "group": "policy",
                "key": "Software\\Example",
                "name": "Absent",
                "type": 4,
                "data": 1,
            },
        )

        records = adapter.snapshot_values("sid", "profile", targets)
        adapter.write_values("sid", "profile", targets)
        adapter.restore_values("sid", "profile", records)

        self.assertEqual((True, 4, 7), api.values[("Software\\Example", "Existing")])
        self.assertNotIn(("Software\\Example", "Absent"), api.values)

    def test_file_security_protects_with_operator_read_execute_and_restores_sddl(self):
        api = FakeSecurityApi()
        api.sddl[self.launcher_path] = "D:AI(A;;FA;;;BA)"
        adapter = WindowsFileSecurity(api=api)

        records = adapter.snapshot_paths((self.launcher_path,))
        adapter.protect_paths((self.launcher_path,), "S-1-5-21-1001")
        protected_sddl = api.sddl[self.launcher_path]
        adapter.restore_paths(records)

        self.assertIn("S-1-5-21-1001", protected_sddl)
        self.assertIn("GRGX", protected_sddl)
        self.assertEqual("D:AI(A;;FA;;;BA)", api.sddl[self.launcher_path])

    def test_protected_paths_include_kiosk_directory_and_config_not_allowed_app(self):
        paths = self._context().protected_paths()

        self.assertIn(os.path.dirname(self.launcher_path), paths)
        self.assertIn(self.launcher_path, paths)
        self.assertIn(self.config_path, paths)
        self.assertNotIn(self.allowed_path, paths)

    def test_native_windows_adapters_construct_under_python_27(self):
        account_api = NativeAccountInspectionApi()
        registry_api = NativeOperatorRegistryApi()
        security_api = NativeFileSecurityApi()

        self.assertIsNotNone(account_api.advapi32)
        self.assertIsNotNone(registry_api.registry)
        self.assertIsNotNone(security_api.advapi32)

    def test_factory_builds_complete_windows_backend(self):
        backend = create_windows_system_backend()

        self.assertIsInstance(backend.account_inspector, WindowsAccountInspector)
        self.assertIsInstance(backend.registry_adapter, WindowsOperatorRegistry)
        self.assertIsInstance(backend.security_adapter, WindowsFileSecurity)


if __name__ == "__main__":
    unittest.main()
