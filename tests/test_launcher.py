try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest
from unittest import mock

from python_kiosk.config import KioskConfig
from python_kiosk.launcher import KioskLauncher
from python_kiosk.local_admin_auth import AuthResult, AUTH_SUCCESS
from python_kiosk.security import hash_password


class LauncherTests(unittest.TestCase):
    def _config(self, app_path=r"C:\Missing\app.exe"):
        password = hash_password("admin-pass", iterations=1000)
        return KioskConfig(
            app_path=app_path,
            operator_user="Operator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
            logging={"logDirectory": _test_environment.TEST_LOG_DIRECTORY},
        )

    def test_admin_password_is_required_for_unlock(self):
        launcher = KioskLauncher(self._config())

        self.assertTrue(launcher.verify_admin_password("admin-pass"))
        self.assertFalse(launcher.verify_admin_password("wrong"))

    def test_local_admin_credentials_are_required_for_desktop_unlock(self):
        class FakeAuthenticator(object):
            def __init__(self):
                self.calls = []

            def authenticate(self, username, password):
                self.calls.append((username, password))
                return username == "Admin" and password == "secret"

        authenticator = FakeAuthenticator()
        launcher = KioskLauncher(self._config(), admin_authenticator=authenticator)

        self.assertTrue(launcher.verify_admin_credentials("Admin", "secret"))
        self.assertFalse(launcher.verify_admin_credentials("Operator", "secret"))
        self.assertEqual(
            [("Admin", "secret"), ("Operator", "secret")],
            authenticator.calls,
        )

    def test_launcher_exposes_structured_admin_credential_result(self):
        class FakeAuthenticator(object):
            def authenticate_result(self, username, password):
                return AuthResult(
                    AUTH_SUCCESS,
                    username=username,
                    domain=".",
                    message="Доступ разрешён.",
                )

        launcher = KioskLauncher(
            self._config(),
            admin_authenticator=FakeAuthenticator(),
        )

        result = launcher.verify_admin_credentials_result("Admin", "secret")

        self.assertTrue(result.success)
        self.assertEqual("Admin", result.username)

    def test_create_watchdog_rejects_missing_allowed_executable(self):
        launcher = KioskLauncher(self._config(app_path=r"C:\Missing\app.exe"))

        with self.assertRaises(ValueError) as error:
            launcher.create_watchdog()

        self.assertIn("Разрешенное приложение не найдено", str(error.exception))

    def test_create_watchdog_passes_duplicate_process_checker(self):
        created = []

        class FakeWatchdog(object):
            def __init__(
                self,
                command,
                restart_delay_seconds,
                process_running,
                working_directory=None,
                restart_on_exit=True,
                wait_for_input_idle=True,
                start_maximized=False,
                single_instance=True,
                bring_existing_to_front=None,
                logger=None,
            ):
                created.append(
                    {
                        "command": command,
                        "restart_delay_seconds": restart_delay_seconds,
                        "process_running": process_running,
                        "working_directory": working_directory,
                        "restart_on_exit": restart_on_exit,
                        "wait_for_input_idle": wait_for_input_idle,
                        "start_maximized": start_maximized,
                        "single_instance": single_instance,
                        "bring_existing_to_front": bring_existing_to_front,
                        "logger": logger,
                    }
                )

        config = KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="Operator",
            logging={"logDirectory": _test_environment.TEST_LOG_DIRECTORY},
        )
        config.allowed_application.arguments = "--safe-mode"
        config.allowed_application.working_directory = r"C:\Windows\System32"
        config.allowed_application.restart_on_exit = False
        config.allowed_application.start_maximized = True
        config.allowed_application.single_instance = True
        config.allowed_application.bring_existing_to_front = True
        config.allowed_application.restart_delay_ms = 1500
        launcher = KioskLauncher(config, watchdog_class=FakeWatchdog)

        with mock.patch("python_kiosk.launcher.os.path.isfile", return_value=True):
            launcher.create_watchdog()

        self.assertEqual(
            [r"C:\Windows\System32\notepad.exe", "--safe-mode"],
            created[0]["command"],
        )
        self.assertEqual(r"C:\Windows\System32", created[0]["working_directory"])
        self.assertFalse(created[0]["restart_on_exit"])
        self.assertTrue(created[0]["start_maximized"])
        self.assertEqual(1.5, created[0]["restart_delay_seconds"])
        self.assertTrue(created[0]["single_instance"])
        self.assertTrue(callable(created[0]["bring_existing_to_front"]))
        self.assertTrue(callable(created[0]["process_running"]))


if __name__ == "__main__":
    unittest.main()
