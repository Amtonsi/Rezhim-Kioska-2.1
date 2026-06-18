# -*- coding: utf-8 -*-

import argparse
import os
import sys

from python_kiosk.admin_actions import AdminActions
from python_kiosk.config import (
    DEFAULT_CONFIG_PATH,
    KioskConfig,
    ensure_default_config,
    load_config,
    save_config,
)
from python_kiosk.configurator import Configurator
from python_kiosk.launcher import KioskLauncher
from python_kiosk.platform_detect import (
    detect_windows_info,
    select_policy_profile,
    validate_modern_platform,
)
from python_kiosk.policy_plan import build_install_plan, build_restore_plan
from python_kiosk.restore_tool import RestoreTool
from python_kiosk.security import hash_password
from python_kiosk.session_lockdown import recover_current_desktop
from python_kiosk.shell_ui import run_shell
from python_kiosk.single_instance import SingleInstanceGuard
from python_kiosk.logging_service import configured_log_path, create_configured_logger


class _HelpCatchingParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

    def format_help(self):
        text = argparse.ArgumentParser.format_help(self)
        return (
            text.replace("usage:", "использование:")
            .replace("positional arguments:", "команды:")
            .replace("options:", "параметры:")
            .replace("show this help message and exit", "показать эту справку и выйти")
        )


def build_parser():
    default_config_path = resolve_default_config_path()
    parser = _HelpCatchingParser(
        prog="PythonKiosk",
        add_help=False,
        description=(
            "Подготовка и запуск оболочки киоска Windows. "
            "Без --apply команды работают в dry-run и не меняют политики Windows."
        ),
    )
    parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    subparsers = parser.add_subparsers(dest="command", title="команды")

    init_parser = subparsers.add_parser(
        "init",
        help="создать конфигурацию киоска",
        add_help=False,
    )
    init_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    init_parser.add_argument("--app-path", required=True, metavar="ПУТЬ")
    init_parser.add_argument("--operator", required=True, metavar="ПОЛЬЗОВАТЕЛЬ")
    init_parser.add_argument("--password", required=False, default="", metavar="ПАРОЛЬ")
    init_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    init_parser.add_argument("--restart-delay", type=int, default=2, metavar="СЕКУНДЫ")

    plan_parser = subparsers.add_parser(
        "plan",
        help="показать пробный план установки",
        add_help=False,
    )
    plan_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    plan_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    restore_parser = subparsers.add_parser(
        "restore-plan",
        help="показать пробный план восстановления",
        add_help=False,
    )
    restore_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    restore_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    install_parser = subparsers.add_parser(
        "install",
        help="подготовить или применить установку киоска",
        add_help=False,
    )
    install_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    install_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    install_parser.add_argument("--state-dir", default=None, metavar="КАТАЛОГ")
    install_parser.add_argument(
        "--apply",
        action="store_true",
        help="применить изменения Windows; без флага выполняется dry-run",
    )

    restore_apply_parser = subparsers.add_parser(
        "restore",
        help="подготовить или применить восстановление киоска",
        add_help=False,
    )
    restore_apply_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    restore_apply_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    restore_apply_parser.add_argument("--state-dir", default=None, metavar="КАТАЛОГ")
    restore_apply_parser.add_argument(
        "--apply",
        action="store_true",
        help="восстановить shell и политики; без флага выполняется dry-run",
    )

    check_parser = subparsers.add_parser(
        "check-password",
        help="проверить legacy-пароль администратора киоска",
        add_help=False,
    )
    check_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    check_parser.add_argument("--password", required=True, metavar="ПАРОЛЬ")
    check_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    launch_parser = subparsers.add_parser(
        "launch",
        help="запустить оболочку киоска",
        add_help=False,
    )
    launch_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    launch_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    launch_parser.add_argument(
        "--headless",
        action="store_true",
        help="запустить надзор без окна оболочки Tkinter",
    )

    recover_parser = subparsers.add_parser(
        "recover-desktop",
        help="показать рабочий стол текущей сессии после теста",
        add_help=False,
    )
    recover_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")

    log_path_parser = subparsers.add_parser(
        "log-path",
        help="показать путь диагностического журнала и записать тестовый маркер",
        add_help=False,
    )
    log_path_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    log_path_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    set_app_parser = subparsers.add_parser(
        "set-app",
        help="изменить путь к разрешённому приложению",
        add_help=False,
    )
    set_app_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    set_app_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    set_app_parser.add_argument("--app-path", required=True, metavar="ПУТЬ")

    change_password_parser = subparsers.add_parser(
        "change-password",
        help="сменить legacy-пароль администратора киоска",
        add_help=False,
    )
    change_password_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    change_password_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    change_password_parser.add_argument("--password", required=True, metavar="ПАРОЛЬ")

    status_parser = subparsers.add_parser(
        "status",
        help="показать текущую конфигурацию и выбранный профиль",
        add_help=False,
    )
    status_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    status_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    return parser


def resolve_default_config_path():
    if os.path.isabs(DEFAULT_CONFIG_PATH) and not getattr(sys, "frozen", False):
        return DEFAULT_CONFIG_PATH

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        relative_config_path = _relative_frozen_config_path(
            DEFAULT_CONFIG_PATH,
            bundle_dir,
        )
        return os.path.join(exe_dir, relative_config_path)
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.abspath(DEFAULT_CONFIG_PATH),
            os.path.join(project_dir, DEFAULT_CONFIG_PATH),
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _relative_frozen_config_path(default_config_path, bundle_dir=None):
    if not os.path.isabs(default_config_path):
        return default_config_path

    if bundle_dir:
        try:
            relative_path = os.path.relpath(
                default_config_path,
                os.path.abspath(bundle_dir),
            )
        except ValueError:
            relative_path = ""
        if relative_path and not relative_path.startswith(".."):
            return relative_path

    return os.path.join("config", os.path.basename(default_config_path))


def build_launcher_shell_command(config_path):
    config_path = os.path.abspath(config_path)
    if getattr(sys, "frozen", False):
        return '"{0}" launch --config "{1}"'.format(
            os.path.abspath(sys.executable),
            config_path,
        )
    return '"{0}" "{1}" launch --config "{2}"'.format(
        os.path.abspath(sys.executable),
        os.path.abspath(__file__),
        config_path,
    )


def _emit(stdout, text):
    stdout(text)


def _create_config(args):
    if args.password:
        password = hash_password(args.password)
        return KioskConfig(
            app_path=args.app_path,
            operator_user=args.operator,
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
            restart_delay_seconds=args.restart_delay,
        )
    return KioskConfig(
        app_path=args.app_path,
        operator_user=args.operator,
        restart_delay_seconds=args.restart_delay,
    )


def _load_config_for_command(path):
    return load_config(path, create_if_missing=True)


def main(
    argv=None,
    stdout=None,
    shell_runner=None,
    platform_detector=None,
    enforce_platform=None,
):
    argv = sys.argv[1:] if argv is None else list(argv)
    stdout = stdout or print
    shell_runner = shell_runner or run_shell
    platform_detector = platform_detector or detect_windows_info
    if enforce_platform is None:
        enforce_platform = bool(getattr(sys, "frozen", False))
    parser = build_parser()

    if not argv:
        argv = ["launch"]

    try:
        args = parser.parse_args(argv)
    except ValueError as error:
        _emit(stdout, str(error))
        _emit(stdout, parser.format_help())
        return 2

    guarded_commands = {
        "install",
        "restore",
        "launch",
        "set-app",
        "change-password",
    }
    if enforce_platform and args.command in guarded_commands:
        compatibility = validate_modern_platform(platform_detector())
        if not compatibility.supported:
            _emit(stdout, compatibility.message)
            return 2

    if args.command == "init":
        config = _create_config(args)
        save_config(config, args.config)
        _emit(stdout, "Конфигурация сохранена: {0}".format(args.config))
        return 0

    if args.command == "plan":
        config = _load_config_for_command(args.config)
        plan = build_install_plan(config, detect_windows_info())
        _emit(stdout, plan.to_text())
        return 0

    if args.command == "restore-plan":
        config = _load_config_for_command(args.config)
        plan = build_restore_plan(config)
        _emit(stdout, plan.to_text())
        return 0

    if args.command == "install":
        config = _load_config_for_command(args.config)
        try:
            result = Configurator(
                state_dir=args.state_dir,
                launcher_command=build_launcher_shell_command(args.config),
            ).install(
                config,
                apply=args.apply,
            )
        except PermissionError as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, result.plan.to_text())
        _emit(stdout, "Backup: {0}".format(result.backup_path))
        return 0

    if args.command == "restore":
        config = _load_config_for_command(args.config)
        try:
            result = RestoreTool(state_dir=args.state_dir).restore(
                config,
                apply=args.apply,
            )
        except PermissionError as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, result.plan.to_text())
        return 0

    if args.command == "check-password":
        config = _load_config_for_command(args.config)
        launcher = KioskLauncher(config)
        if launcher.verify_admin_password(args.password):
            _emit(stdout, "Пароль принят")
            return 0
        _emit(stdout, "Пароль отклонён")
        return 1

    if args.command == "launch":
        ensure_default_config(args.config)
        config = load_config(args.config)
        guard = SingleInstanceGuard.for_operator(config.operator_user)
        with guard:
            if not guard.acquired:
                _emit(stdout, "Киоск уже запущен для этой конфигурации.")
                return 0
            launcher = KioskLauncher(config, config_path=args.config)
            if args.headless:
                launcher.run()
            else:
                shell_runner(launcher)
        return 0

    if args.command == "recover-desktop":
        result = recover_current_desktop()
        _emit(stdout, "Рабочий стол текущей сессии восстановлен.")
        _emit(stdout, "Explorer: {0}".format("started" if result.get("started_explorer") else "not-started"))
        return 0

    if args.command == "log-path":
        config = _load_config_for_command(args.config)
        logger = create_configured_logger(config)
        log_path = configured_log_path(config)
        logger.info(
            "diagnostic.log_ready",
            operator=config.operator_user,
            app_path=config.app_path,
            config_path=os.path.abspath(args.config),
            log_path=log_path,
        )
        _emit(stdout, "Log: {0}".format(log_path))
        _emit(stdout, "Session: {0}".format(logger.session_id))
        return 0

    if args.command == "set-app":
        try:
            AdminActions(args.config).set_allowed_app_path(args.app_path)
        except (PermissionError, ValueError) as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, "Путь разрешённого приложения сохранён: {0}".format(args.app_path))
        return 0

    if args.command == "change-password":
        try:
            AdminActions(args.config).change_kiosk_admin_password(args.password)
        except (PermissionError, ValueError) as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, "Legacy-пароль администратора киоска изменён")
        return 0

    if args.command == "status":
        config = _load_config_for_command(args.config)
        windows_info = detect_windows_info()
        profile = (
            config.policy_profile
            if config.policy_profile != "auto"
            else select_policy_profile(windows_info)
        )
        _emit(stdout, "Оператор: {0}".format(config.operator_user))
        _emit(stdout, "Разрешённое приложение: {0}".format(config.app_path))
        _emit(stdout, "Профиль политики: {0}".format(profile))
        _emit(stdout, "Windows: {0}".format(windows_info.product_name or "не определено"))
        return 0

    _emit(stdout, parser.format_help())
    return 0


if __name__ == "__main__":
    sys.exit(main())
