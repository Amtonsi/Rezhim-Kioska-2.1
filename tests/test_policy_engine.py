try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.platform_detect import WindowsInfo
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.security import hash_password


class PolicyEngineTests(unittest.TestCase):
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

    def test_builds_reversible_operator_only_install_plan(self):
        engine = PolicyEngine()
        plan = engine.build_install_plan(
            self._config(),
            WindowsInfo(10, 0, 22631, "Home", "Microsoft Windows 11 Home"),
            launcher_command=r'"C:\Kiosk\RezhimKioska.exe" launch --config "C:\Kiosk\config\kiosk.json"',
        )

        operation_names = [operation.name for operation in plan.operations]
        shell_operation = [
            operation for operation in plan.operations if operation.name == "set_operator_shell"
        ][0]
        self.assertEqual("home_fallback", plan.profile)
        self.assertIn("create_backup", operation_names)
        self.assertIn("ensure_operator_user", operation_names)
        self.assertIn("set_operator_shell", operation_names)
        self.assertIn("apply_hkcu_operator_policies", operation_names)
        self.assertNotIn("stop_services", operation_names)
        self.assertNotIn("clear_startup", operation_names)
        self.assertEqual(
            r'"C:\Kiosk\RezhimKioska.exe" launch --config "C:\Kiosk\config\kiosk.json"',
            shell_operation.data["shell_command"],
        )

    def test_policy_profiles_file_contains_required_profiles(self):
        profiles = PolicyEngine.load_profiles()

        for profile in [
            "xp_legacy",
            "win7_srp",
            "win10_applocker",
            "win10_shelllauncher",
            "home_fallback",
        ]:
            self.assertIn(profile, profiles)
            self.assertIn("description", profiles[profile])


if __name__ == "__main__":
    unittest.main()
