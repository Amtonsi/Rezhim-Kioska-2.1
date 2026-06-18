try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.platform_detect import WindowsInfo
from python_kiosk.policy_plan import build_install_plan, build_restore_plan


class PolicyPlanTests(unittest.TestCase):
    def _config(self):
        return KioskConfig(
            app_path=r"C:\Program Files\Vendor\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
            restart_delay_seconds=2,
        )

    def test_install_plan_is_dry_run_and_mentions_core_restrictions(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Enterprise")

        plan = build_install_plan(self._config(), info)
        text = plan.to_text()

        self.assertTrue(plan.dry_run)
        self.assertIn("Назначить оболочку Operator на KioskLauncher", text)
        self.assertIn("Отключить диспетчер задач", text)
        self.assertIn("Не отключать службы", text)
        self.assertIn("Оставить Win+L доступным", text)
        self.assertIn("Shell Launcher", text)

    def test_restore_plan_returns_shell_without_touching_startup_services(self):
        plan = build_restore_plan(self._config())
        text = plan.to_text()

        self.assertTrue(plan.dry_run)
        self.assertIn("Вернуть оболочку Operator на explorer.exe", text)
        self.assertIn("Не удалять элементы автозагрузки", text)
        self.assertIn("Не останавливать службы", text)


if __name__ == "__main__":
    unittest.main()
