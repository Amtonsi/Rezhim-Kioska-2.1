# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from kiosk_v2_legacy.app.process_supervisor import ApplicationSettings
from kiosk_v2_legacy.platform.log_path import resolve_log_directory


try:
    text_type = unicode
except NameError:
    text_type = str


SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "credential",
)


class WindowSettings(object):
    __slots__ = ("bring_to_front", "start_maximized", "restore_if_minimized")

    def __init__(self, bring_to_front, start_maximized, restore_if_minimized):
        self.bring_to_front = bool(bring_to_front)
        self.start_maximized = bool(start_maximized)
        self.restore_if_minimized = bool(restore_if_minimized)


class SecuritySettings(object):
    __slots__ = (
        "admin_session_timeout_seconds",
        "explorer_guard_interval_ms",
        "allow_win_l",
        "keyboard_guard_required",
    )

    def __init__(
        self,
        admin_session_timeout_seconds,
        explorer_guard_interval_ms,
        allow_win_l,
        keyboard_guard_required,
    ):
        self.admin_session_timeout_seconds = int(admin_session_timeout_seconds)
        self.explorer_guard_interval_ms = int(explorer_guard_interval_ms)
        self.allow_win_l = bool(allow_win_l)
        self.keyboard_guard_required = bool(keyboard_guard_required)


class LoggingSettings(object):
    __slots__ = ("log_directory", "level", "max_bytes", "backup_count")

    def __init__(self, log_directory, level, max_bytes, backup_count):
        self.log_directory = log_directory
        self.level = level
        self.max_bytes = int(max_bytes)
        self.backup_count = int(backup_count)


class TestingSettings(object):
    __slots__ = (
        "require_backup_before_test",
        "restore_after_test",
        "test_only_separate_operator_user",
    )

    def __init__(
        self,
        require_backup_before_test,
        restore_after_test,
        test_only_separate_operator_user,
    ):
        self.require_backup_before_test = bool(require_backup_before_test)
        self.restore_after_test = bool(restore_after_test)
        self.test_only_separate_operator_user = bool(
            test_only_separate_operator_user
        )


class RuntimeSettings(object):
    __slots__ = (
        "operator_user",
        "application_configured",
        "application",
        "window",
        "security",
        "logging",
        "testing",
    )

    def __init__(
        self,
        operator_user,
        application_configured,
        application,
        window,
        security,
        logging_settings,
        testing,
    ):
        self.operator_user = operator_user
        self.application_configured = bool(application_configured)
        self.application = application
        self.window = window
        self.security = security
        self.logging = logging_settings
        self.testing = testing


class RuntimeSettingsFactory(object):
    def __init__(self, argument_parser):
        self.argument_parser = argument_parser

    def build(self, config):
        self._reject_sensitive_keys(config)
        application_data = config["allowedApplication"]
        application = ApplicationSettings(
            path=application_data["path"],
            arguments=tuple(
                self.argument_parser.parse(application_data["arguments"])
            ),
            working_directory=application_data["workingDirectory"],
            restart_on_exit=application_data["restartOnExit"],
            restart_delay_ms=application_data["restartDelayMs"],
            single_instance=application_data["singleInstance"],
            max_restart_attempts=application_data["maxRestartAttempts"],
            restart_window_seconds=application_data["restartWindowSeconds"],
        )
        window = WindowSettings(
            application_data["bringToFront"],
            application_data["startMaximized"],
            application_data["restoreIfMinimized"],
        )
        kiosk_data = config["kiosk"]
        security = SecuritySettings(
            kiosk_data["adminSessionTimeoutSeconds"],
            kiosk_data["explorerGuardIntervalMs"],
            kiosk_data["allowWinL"],
            kiosk_data["keyboardGuardRequired"],
        )
        log_data = config["logging"]
        logging_settings = LoggingSettings(
            resolve_log_directory(log_data["logDirectory"]),
            log_data["level"],
            log_data["maxBytes"],
            log_data["backupCount"],
        )
        test_data = config["testing"]
        testing = TestingSettings(
            test_data["requireBackupBeforeTest"],
            test_data["restoreAfterTest"],
            test_data["testOnlySeparateOperatorUser"],
        )
        return RuntimeSettings(
            config["operatorUser"],
            application_data.get("configured", True),
            application,
            window,
            security,
            logging_settings,
            testing,
        )

    def _reject_sensitive_keys(self, value, path="$"):
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = "".join(
                    character.lower()
                    for character in text_type(key)
                    if character.isalnum()
                )
                if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                    raise ValueError(
                        "Sensitive field is not allowed in runtime settings: {0}".format(
                            path
                        )
                    )
                self._reject_sensitive_keys(item, "{0}.{1}".format(path, key))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                self._reject_sensitive_keys(item, "{0}[{1}]".format(path, index))
