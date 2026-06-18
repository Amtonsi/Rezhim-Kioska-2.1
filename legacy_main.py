# -*- coding: utf-8 -*-

import argparse
import os
import sys

from legacy_kiosk.config import ensure_default_config, load_config, save_config
from legacy_kiosk.desktop_manager import WindowsDesktopSessionManager
from legacy_kiosk.logging_service import LegacyLogger, resolve_log_directory
from legacy_kiosk.platform_detect import detect_windows_info, validate_legacy_platform
from legacy_kiosk.runtime import LegacyRuntime
from legacy_kiosk.shell_ui import LegacyShellWindow
from legacy_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    INSTALL_ORDER,
    AccessDeniedError,
    LegacyInstallContext,
    LegacyTransaction,
    create_windows_system_backend,
)


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNSUPPORTED_PLATFORM = 3
EXIT_ACCESS_DENIED = 5


def default_config_path(executable=None, frozen=None):
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    executable = executable or sys.executable
    if frozen:
        base_directory = os.path.dirname(os.path.abspath(executable))
    else:
        base_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_directory, "config", "kiosk.json")


def default_backup_path(config_path):
    config_directory = os.path.dirname(os.path.abspath(config_path))
    base_directory = os.path.dirname(config_directory)
    return os.path.join(base_directory, "backup", "legacy-backup.json")


def build_parser():
    parser = argparse.ArgumentParser(prog="RezhimKioska-Legacy")
    parser.add_argument("--config", default=None, help=u"Путь к kiosk.json")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("launch", help=u"Запустить оболочку киоска")
    for command in ("install", "repair", "restore", "uninstall"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--apply", action="store_true", help=u"Применить изменения"
        )
    subparsers.add_parser("recover-desktop")
    subparsers.add_parser("status")
    subparsers.add_parser("test-mode")
    set_app = subparsers.add_parser("set-app")
    set_app.add_argument("path")
    return parser


def _run_shell(config, config_path):
    try:
        import Tkinter as tkinter
    except ImportError:
        import tkinter
    runtime = LegacyRuntime(config, config_path)
    root = tkinter.Tk()
    try:
        LegacyShellWindow(root, runtime).start()
    finally:
        runtime.close()


def _default_desktop_recoverer():
    return WindowsDesktopSessionManager().open_current_desktop()


def _emit(message, error=False):
    stream = sys.stderr if error else sys.stdout
    try:
        stream.write(message + u"\n")
    except UnicodeEncodeError:
        stream.write((message + u"\n").encode("utf-8"))


def _show_error_dialog(message):
    try:
        import Tkinter as tkinter
        import tkMessageBox as messagebox
    except ImportError:
        import tkinter
        from tkinter import messagebox
    root = tkinter.Tk()
    root.withdraw()
    try:
        messagebox.showerror(u"Режим киоска", message, parent=root)
    finally:
        root.destroy()


def _report_error(message, reporter=None):
    _emit(message, error=True)
    if reporter is not None:
        try:
            reporter(message)
        except Exception:
            pass


def _check_admin(backend):
    return bool(backend.account_inspector.is_current_process_admin())


def main(
    argv=None,
    platform_detector=None,
    backend_factory=None,
    shell_runner=None,
    desktop_recoverer=None,
    launcher_path=None,
    error_reporter=None,
):
    argument_list = list(sys.argv[1:] if argv is None else argv)
    commands = frozenset(
        (
            "launch",
            "install",
            "repair",
            "restore",
            "uninstall",
            "recover-desktop",
            "status",
            "test-mode",
            "set-app",
        )
    )
    if not any(value in commands for value in argument_list) and not any(
        value in ("-h", "--help") for value in argument_list
    ):
        argument_list.append("launch")
    args = build_parser().parse_args(argument_list)
    command = args.command or "launch"
    platform_detector = platform_detector or detect_windows_info
    backend_factory = backend_factory or create_windows_system_backend
    shell_runner = shell_runner or _run_shell
    desktop_recoverer = desktop_recoverer or _default_desktop_recoverer
    launcher_path = launcher_path or (
        sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    )
    if error_reporter is None and getattr(sys, "frozen", False):
        error_reporter = _show_error_dialog

    try:
        windows_info = platform_detector()
        compatibility = validate_legacy_platform(windows_info)
        if not compatibility.supported:
            _report_error(compatibility.message, error_reporter)
            return EXIT_UNSUPPORTED_PLATFORM

        config_path = os.path.abspath(
            args.config or default_config_path(executable=launcher_path)
        )
        if command in ("launch", "status", "test-mode"):
            ensure_default_config(config_path)
        config = load_config(
            config_path,
            require_existing_app=command not in ("restore", "uninstall", "recover-desktop"),
        )
        logger = LegacyLogger(
            path=os.path.join(
                resolve_log_directory(
                    config.get("logging", {}).get("logDirectory", ""),
                    nt_major=windows_info.major,
                ),
                "kiosk.log",
            )
        )
        logger.log("cli.command", {"command": command})

        if command == "launch":
            shell_runner(config, config_path)
            return EXIT_OK

        if command == "recover-desktop":
            desktop_recoverer()
            return EXIT_OK

        if command == "status":
            _emit(u"Профиль: %s" % compatibility.profile)
            _emit(u"Оператор: %s" % config["operatorUser"])
            _emit(u"Приложение: %s" % config["allowedApplication"]["path"])
            return EXIT_OK

        if command == "test-mode":
            _emit(u"Конфигурация и Legacy-платформа проверены. Изменения не применялись.")
            return EXIT_OK

        backend = backend_factory()
        if command == "set-app":
            if not _check_admin(backend):
                _report_error(ADMIN_RIGHTS_REQUIRED_MESSAGE, error_reporter)
                return EXIT_ACCESS_DENIED
            app_path = os.path.abspath(args.path)
            if not os.path.isfile(app_path) or os.path.splitext(app_path)[1].lower() != ".exe":
                raise ValueError(u"Разрешённое приложение не найдено: %s" % app_path)
            config["allowedApplication"]["path"] = app_path
            config["allowedApplication"]["workingDirectory"] = os.path.dirname(app_path)
            save_config(config, config_path)
            return EXIT_OK

        apply_changes = bool(getattr(args, "apply", False))
        if not apply_changes:
            action = u"установка" if command in ("install", "repair") else u"восстановление"
            _emit(u"Dry-run: %s. Изменения не применялись." % action)
            if command in ("install", "repair"):
                for operation_name in INSTALL_ORDER:
                    _emit(u"- %s" % operation_name)
            return EXIT_OK

        if not _check_admin(backend):
            _report_error(ADMIN_RIGHTS_REQUIRED_MESSAGE, error_reporter)
            return EXIT_ACCESS_DENIED

        context = LegacyInstallContext(
            config=config,
            launcher_path=launcher_path,
            config_path=config_path,
            backup_path=default_backup_path(config_path),
            platform_info=windows_info,
        )
        if command in ("install", "repair"):
            LegacyTransaction(backend).apply(context)
        else:
            backend.restore(context)
        return EXIT_OK
    except AccessDeniedError as error:
        _report_error(unicode(error), error_reporter)
        return EXIT_ACCESS_DENIED
    except Exception as error:
        _report_error(u"Ошибка: %s" % error, error_reporter)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
