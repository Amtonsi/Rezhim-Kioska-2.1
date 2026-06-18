# -*- coding: utf-8 -*-

import getpass
import inspect
import os

from python_kiosk.config import save_config
from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_SUCCESS,
    AuthResult,
    LocalAdminAuthenticator,
    MESSAGE_BAD_CREDENTIALS,
)
from python_kiosk.logging_service import create_configured_logger
from python_kiosk.process_watchdog import ProcessWatchdog, windows_allowed_process_running
from python_kiosk.window_control import AppWindowController
from python_kiosk.security import verify_password


class KioskLauncher(object):
    def __init__(
        self,
        config,
        config_path=None,
        watchdog_class=ProcessWatchdog,
        admin_authenticator=None,
        logger=None,
    ):
        self.config = config
        self.config_path = config_path
        self.watchdog_class = watchdog_class
        self.admin_authenticator = admin_authenticator or LocalAdminAuthenticator()
        self.logger = logger or create_configured_logger(config)
        self.app_window_controller = AppWindowController()
        self.logger.info(
            "launcher.initialized",
            operator=config.operator_user,
            app_path=config.app_path,
            config_path=config_path or "",
        )

    def _password_record(self):
        return {
            "algorithm": self.config.admin_password_algorithm,
            "iterations": self.config.admin_password_iterations,
            "salt": self.config.admin_password_salt,
            "hash": self.config.admin_password_hash,
        }

    def verify_admin_password(self, password):
        if not self.config.admin_password_hash or not self.config.admin_password_salt:
            return False
        return verify_password(password, self._password_record())

    def verify_admin_credentials(self, username, password):
        return self.verify_admin_credentials_result(username, password).success

    def verify_admin_credentials_result(self, username, password):
        if hasattr(self.admin_authenticator, "authenticate_result"):
            return self.admin_authenticator.authenticate_result(username, password)
        if self.admin_authenticator.authenticate(username, password):
            return AuthResult(
                AUTH_SUCCESS,
                username=username,
                domain="",
                message="Доступ разрешён.",
            )
        return AuthResult(
            AUTH_BAD_CREDENTIALS,
            username=username,
            domain="",
            message=MESSAGE_BAD_CREDENTIALS,
        )

    def create_watchdog(self):
        if not os.path.isfile(self.config.app_path):
            self.logger.error("launcher.allowed_app_missing", app_path=self.config.app_path)
            raise ValueError(
                "Разрешенное приложение не найдено: {0}".format(
                    self.config.app_path
                )
            )
        allowed_app = self.config.allowed_application
        restart_delay_seconds = float(
            getattr(allowed_app, "restart_delay_ms", self.config.restart_delay_seconds * 1000)
        ) / 1000.0
        kwargs = {
            "restart_delay_seconds": restart_delay_seconds,
            "process_running": lambda: windows_allowed_process_running(self.config.app_path),
            "working_directory": allowed_app.working_directory or None,
            "restart_on_exit": allowed_app.restart_on_exit,
            "wait_for_input_idle": True,
            "start_maximized": allowed_app.start_maximized,
            "single_instance": allowed_app.single_instance,
            "bring_existing_to_front": (
                lambda: self.app_window_controller.ensure_foreground(
                    self.config.app_path,
                    wait=False,
                    start_maximized=allowed_app.start_maximized,
                )
                if allowed_app.bring_existing_to_front
                else False
            ),
        }
        if self._watchdog_accepts_logger():
            kwargs["logger"] = self.logger
        self.logger.info(
            "launcher.watchdog_created",
            app_path=self.config.app_path,
            restart_on_exit=allowed_app.restart_on_exit,
            single_instance=allowed_app.single_instance,
            restore_if_minimized=allowed_app.restore_if_minimized,
        )
        return self.watchdog_class(allowed_app.command(), **kwargs)

    def set_allowed_application_path(self, app_path):
        if not os.path.isfile(app_path):
            raise ValueError(
                "Р Р°Р·СЂРµС€РµРЅРЅРѕРµ РїСЂРёР»РѕР¶РµРЅРёРµ РЅРµ РЅР°Р№РґРµРЅРѕ: {0}".format(
                    app_path
                )
            )
        previous = self.config.app_path
        self.config.app_path = app_path
        if self.config_path:
            save_config(self.config, self.config_path)
        self.logger.info("admin.set_app_path", previous=previous, current=app_path)
        return True

    def _watchdog_accepts_logger(self):
        try:
            parameters = inspect.signature(self.watchdog_class).parameters.values()
        except (TypeError, ValueError):
            return False
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "logger":
                return True
        return False

    def run(self):
        self.logger.info("launcher.run_forever_started")
        watchdog = self.create_watchdog()
        try:
            watchdog.run_forever()
        finally:
            self.logger.info("launcher.run_forever_stopped")


def prompt_admin_unlock(launcher, prompt="Kiosk admin password: "):
    password = getpass.getpass(prompt)
    return launcher.verify_admin_password(password)
