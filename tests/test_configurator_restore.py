try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.configurator import Configurator
from python_kiosk.restore_tool import RestoreTool
from python_kiosk.security import hash_password
from python_kiosk.system_backend import WindowsSystemBackend


class FakeSystemBackend(object):
    def __init__(self, admin=True, fail_on=None):
        self.admin = admin
        self.fail_on = fail_on
        self.applied = []

    def is_admin(self):
        return self.admin

    def apply_operation(self, operation):
        self.applied.append(operation.name)
        if operation.name == self.fail_on:
            raise RuntimeError("boom")


class ConfiguratorRestoreTests(unittest.TestCase):
    def _config(self):
        password = hash_password("admin-pass", iterations=1000)
        return KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="KioskOperator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
        )

    def test_install_is_dry_run_by_default_and_creates_backup_plan(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True)
        configurator = Configurator(backend=backend, state_dir=temp_dir)

        result = configurator.install(self._config(), apply=False)

        self.assertFalse(result.applied)
        self.assertTrue(os.path.exists(result.backup_path))
        self.assertEqual([], backend.applied)
        self.assertIn("create_backup", [op.name for op in result.plan.operations])

    def test_install_refuses_apply_without_admin_rights(self):
        backend = FakeSystemBackend(admin=False)
        configurator = Configurator(
            backend=backend,
            state_dir=tempfile.mkdtemp(),
        )

        with self.assertRaises(PermissionError) as error:
            configurator.install(self._config(), apply=True)

        self.assertEqual(
            "Отказано в доступе. Для выполнения действия требуются права администратора Windows.",
            str(error.exception),
        )
        self.assertEqual([], backend.applied)

    def test_restore_refuses_apply_without_admin_rights(self):
        backend = FakeSystemBackend(admin=False)
        restore = RestoreTool(
            backend=backend,
            state_dir=tempfile.mkdtemp(),
        )

        with self.assertRaises(PermissionError) as error:
            restore.restore(self._config(), apply=True)

        self.assertEqual(
            "Отказано в доступе. Для выполнения действия требуются права администратора Windows.",
            str(error.exception),
        )
        self.assertEqual([], backend.applied)

    def test_restore_is_dry_run_by_default_and_targets_explorer_shell(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True)
        restore = RestoreTool(backend=backend, state_dir=temp_dir)

        result = restore.restore(self._config(), apply=False)

        self.assertFalse(result.applied)
        self.assertEqual([], backend.applied)
        self.assertIn("restore_operator_shell", [op.name for op in result.plan.operations])
        self.assertIn("explorer.exe", result.plan.to_text().lower())

    def test_install_apply_failure_attempts_safe_restore_plan(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True, fail_on="set_operator_shell")
        configurator = Configurator(backend=backend, state_dir=temp_dir)
        config = self._config()

        with self.assertRaises(RuntimeError):
            configurator.install(config, apply=True)

        self.assertIn("set_operator_shell", backend.applied)
        self.assertIn("restore_operator_shell", backend.applied)
        self.assertIn("restore_operator_policies", backend.applied)

    def test_system_backend_rejects_forbidden_operations(self):
        class Operation(object):
            name = "stop_services"

        with self.assertRaises(ValueError):
            WindowsSystemBackend().apply_operation(Operation())


if __name__ == "__main__":
    unittest.main()
