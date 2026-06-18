try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.admin_actions import AdminActions
from python_kiosk.config import KioskConfig, load_config, save_config
from python_kiosk.security import hash_password, verify_password
from python_kiosk.system_backend import ADMIN_RIGHTS_REQUIRED_MESSAGE


class FakeBackend(object):
    def __init__(self, admin):
        self.admin = admin

    def is_admin(self):
        return self.admin


class AdminActionsTests(unittest.TestCase):
    def _write_config(self, path, app_path):
        password = hash_password("admin-pass", iterations=1000)
        config = KioskConfig(
            app_path=app_path,
            operator_user="KioskOperator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
        )
        save_config(config, path)

    def test_set_allowed_app_path_requires_existing_exe(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=True))

        new_app_path = os.path.join(temp_dir, "new.exe")
        open(new_app_path, "w").close()
        actions.set_allowed_app_path(new_app_path)

        self.assertEqual(new_app_path, load_config(config_path).app_path)

    def test_set_allowed_app_path_refuses_without_windows_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=False))

        new_app_path = os.path.join(temp_dir, "new.exe")
        open(new_app_path, "w").close()
        with self.assertRaises(PermissionError) as error:
            actions.set_allowed_app_path(new_app_path)

        self.assertEqual(ADMIN_RIGHTS_REQUIRED_MESSAGE, str(error.exception))
        self.assertEqual(app_path, load_config(config_path).app_path)

    def test_change_kiosk_admin_password_rehashes_with_new_salt(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        old_config = load_config(config_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=True))

        actions.change_kiosk_admin_password("new-pass")

        new_config = load_config(config_path)
        self.assertNotEqual(old_config.admin_password_salt, new_config.admin_password_salt)
        self.assertTrue(
            verify_password(
                "new-pass",
                {
                    "iterations": new_config.admin_password_iterations,
                    "salt": new_config.admin_password_salt,
                    "hash": new_config.admin_password_hash,
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
