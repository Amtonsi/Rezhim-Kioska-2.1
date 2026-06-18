try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import sys
import tempfile
import unittest
from unittest import mock

import main
from python_kiosk.config import load_config, save_config
from python_kiosk.logging_service import configured_log_path
from python_kiosk.platform_detect import WindowsInfo
from python_kiosk.system_backend import ADMIN_RIGHTS_REQUIRED_MESSAGE


class CliTests(unittest.TestCase):
    def test_modern_guard_rejects_xp_before_launch(self):
        output = []
        shell_calls = []
        info = WindowsInfo(
            5,
            1,
            2600,
            "Professional",
            service_pack_major=3,
        )

        code = main.main(
            ["launch", "--config", os.path.join(tempfile.mkdtemp(), "missing.json")],
            stdout=output.append,
            shell_runner=lambda launcher: shell_calls.append(launcher),
            platform_detector=lambda: info,
            enforce_platform=True,
        )

        self.assertEqual(2, code)
        self.assertEqual([], shell_calls)
        self.assertIn("Legacy", "\n".join(output))

    def test_modern_guard_rejects_server_before_install(self):
        output = []
        info = WindowsInfo(10, 0, 20348, "Server", product_type=3)

        with mock.patch.object(main, "Configurator") as configurator:
            code = main.main(
                ["install", "--config", os.path.join(tempfile.mkdtemp(), "missing.json")],
                stdout=output.append,
                platform_detector=lambda: info,
                enforce_platform=True,
            )

        self.assertEqual(2, code)
        configurator.assert_not_called()
        self.assertIn("Windows Server", "\n".join(output))

    def test_frozen_default_config_resolves_to_persistent_path_next_to_exe(self):
        temp_dir = tempfile.mkdtemp()
        bundle_dir = os.path.join(temp_dir, "bundle")
        os.mkdir(bundle_dir)
        bundled_config = os.path.join(bundle_dir, "kiosk_config.json")
        open(bundled_config, "w").close()
        persistent_config = os.path.join(temp_dir, "kiosk_config.json")

        with mock.patch.object(main, "DEFAULT_CONFIG_PATH", "kiosk_config.json"):
            with mock.patch.object(main.sys, "frozen", True, create=True):
                with mock.patch.object(main.sys, "_MEIPASS", bundle_dir, create=True):
                    with mock.patch.object(
                        main.sys,
                        "executable",
                        os.path.join(temp_dir, "RezhimKioska.exe"),
                    ):
                        self.assertEqual(persistent_config, main.resolve_default_config_path())

    def test_frozen_absolute_bundle_config_resolves_to_external_config_folder(self):
        temp_dir = tempfile.mkdtemp()
        bundle_dir = os.path.join(temp_dir, "_MEI123")
        exe_dir = os.path.join(temp_dir, "release")
        os.makedirs(os.path.join(bundle_dir, "config"))
        os.makedirs(os.path.join(exe_dir, "config"))
        bundled_config = os.path.join(bundle_dir, "config", "kiosk.json")
        external_config = os.path.join(exe_dir, "config", "kiosk.json")
        open(bundled_config, "w").close()
        open(external_config, "w").close()

        with mock.patch.object(main, "DEFAULT_CONFIG_PATH", bundled_config):
            with mock.patch.object(main.sys, "frozen", True, create=True):
                with mock.patch.object(main.sys, "_MEIPASS", bundle_dir, create=True):
                    with mock.patch.object(
                        main.sys,
                        "executable",
                        os.path.join(exe_dir, "RezhimKioska.exe"),
                    ):
                        self.assertEqual(external_config, main.resolve_default_config_path())

    def test_no_arguments_launches_gui_shell_from_default_config(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        with mock.patch.object(main, "DEFAULT_CONFIG_PATH", config_path):
            code = main.main(
                [],
                stdout=output.append,
                shell_runner=lambda launcher: shell_calls.append(launcher.config.app_path),
            )

        self.assertEqual(0, code)
        self.assertEqual([sys.executable], shell_calls)
        self.assertEqual([], output)

    def test_init_writes_config_and_check_password_verifies_it(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")

        init_code = main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        check_output = []
        check_code = main.main(
            [
                "check-password",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=check_output.append,
        )

        self.assertEqual(0, init_code)
        self.assertEqual(0, check_code)
        self.assertTrue(os.path.exists(config_path))
        self.assertIn("Пароль принят", "\n".join(check_output))

    def test_plan_prints_dry_run_policy_plan(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["plan", "--config", config_path], stdout=output.append)

        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", "\n".join(output))

    def test_install_command_is_dry_run_by_default_and_creates_backup(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["install", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", joined)
        self.assertIn("create_backup", joined)
        self.assertIn("Backup:", joined)

    def test_launcher_shell_command_points_to_configured_launch_command(self):
        config_path = os.path.join(tempfile.mkdtemp(), "kiosk.json")

        command = main.build_launcher_shell_command(config_path)

        self.assertIn("launch", command)
        self.assertIn("--config", command)
        self.assertIn(os.path.abspath(config_path), command)

    def test_restore_command_is_dry_run_by_default_and_targets_explorer(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["restore", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", joined)
        self.assertIn("restore_operator_shell", joined)
        self.assertIn("explorer.exe", joined)

    def test_set_app_command_refuses_without_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(
            ["set-app", "--config", config_path, "--app-path", app_path],
            stdout=output.append,
        )

        self.assertEqual(1, code)
        self.assertIn(ADMIN_RIGHTS_REQUIRED_MESSAGE, "\n".join(output))
        self.assertEqual(sys.executable, main.load_config(config_path).app_path)

    def test_change_password_command_refuses_without_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "old-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(
            ["change-password", "--config", config_path, "--password", "new-pass"],
            stdout=output.append,
        )

        self.assertEqual(1, code)
        self.assertIn(ADMIN_RIGHTS_REQUIRED_MESSAGE, "\n".join(output))

    def test_status_command_prints_profile_and_paths(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["status", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Оператор: Operator", joined)
        self.assertIn(sys.executable, joined)
        self.assertIn("Профиль политики:", joined)

    def test_launch_uses_gui_shell_by_default(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        code = main.main(
            ["launch", "--config", config_path],
            stdout=lambda text: None,
            shell_runner=lambda launcher: shell_calls.append(launcher.config.app_path),
        )

        self.assertEqual(0, code)
        self.assertEqual([sys.executable], shell_calls)

    def test_launch_exits_when_same_config_instance_is_already_running(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        class LockedGuard(object):
            acquired = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with mock.patch.object(main.SingleInstanceGuard, "for_operator", return_value=LockedGuard()):
            code = main.main(
                ["launch", "--config", config_path],
                stdout=output.append,
                shell_runner=lambda launcher: shell_calls.append(launcher),
            )

        self.assertEqual(0, code)
        self.assertEqual([], shell_calls)
        self.assertIn("Киоск уже запущен", "\n".join(output))

    def test_launch_single_instance_guard_is_scoped_to_operator(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        guards = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        class OpenGuard(object):
            acquired = True

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def guard_for_operator(operator_user):
            guards.append(operator_user)
            return OpenGuard()

        with mock.patch.object(main.SingleInstanceGuard, "for_operator", side_effect=guard_for_operator):
            main.main(
                ["launch", "--config", config_path],
                stdout=lambda text: None,
                shell_runner=lambda launcher: None,
            )

        self.assertEqual(["Operator"], guards)

    def test_recover_desktop_command_runs_current_session_recovery(self):
        output = []

        with mock.patch.object(
            main,
            "recover_current_desktop",
            return_value={"started_explorer": True, "restored_windows": [100]},
        ) as recovery:
            code = main.main(["recover-desktop"], stdout=output.append)

        self.assertEqual(0, code)
        self.assertTrue(recovery.called)
        self.assertIn("Рабочий стол текущей сессии восстановлен.", "\n".join(output))

    def test_log_path_command_prints_and_touches_diagnostic_log(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        log_dir = os.path.join(temp_dir, "logs")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        config = load_config(config_path)
        config.logging["logDirectory"] = log_dir
        save_config(config, config_path)

        code = main.main(["log-path", "--config", config_path], stdout=output.append)

        self.assertEqual(0, code)
        self.assertIn(configured_log_path(config), "\n".join(output))
        with open(configured_log_path(config), "r", encoding="utf-8") as log_file:
            self.assertIn("diagnostic.log_ready", log_file.read())


if __name__ == "__main__":
    unittest.main()
