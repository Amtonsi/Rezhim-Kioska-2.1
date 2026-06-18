# -*- coding: utf-8 -*-

import copy
import os

from legacy_kiosk.config import save_config
from legacy_kiosk.desktop_manager import WindowsDesktopSessionManager
from legacy_kiosk.keyboard_filter import KeyboardFilterService, KeyboardFilterState
from legacy_kiosk.local_admin_auth import LocalAdminAuthenticator
from legacy_kiosk.logging_service import LegacyLogger
from legacy_kiosk.process_watchdog import LegacyProcessWatchdog, NativeProcessBackend
from legacy_kiosk.system_backend import AccessDeniedError
from legacy_kiosk.window_control import LegacyWindowController, NativeWindowApi


class LegacyRuntime(object):
    def __init__(
        self,
        config,
        config_path,
        logger=None,
        authenticator=None,
        keyboard_filter=None,
        process_backend=None,
        window_controller=None,
        desktop_manager=None,
        watchdog_factory=None,
    ):
        self.config = config
        self.config_path = os.path.abspath(config_path)
        self.logger = logger or LegacyLogger()
        self.authenticator = authenticator or LocalAdminAuthenticator(
            logger=self.logger
        )
        self.process_backend = process_backend or NativeProcessBackend()
        self.window_controller = window_controller or LegacyWindowController(
            self.process_backend, NativeWindowApi()
        )
        self.keyboard_filter = keyboard_filter or KeyboardFilterService(
            state=KeyboardFilterState(logger=self.logger)
        )
        self.desktop_manager = desktop_manager or WindowsDesktopSessionManager(
            process_backend=self.process_backend
        )
        self.watchdog_factory = watchdog_factory or self._create_watchdog
        self.watchdog = self.watchdog_factory(self.config)
        self.admin_session = None

    @property
    def app_path(self):
        return self.config["allowedApplication"]["path"]

    @property
    def watchdog_enabled(self):
        return bool(getattr(self.watchdog, "supervision_enabled", True))

    def _create_watchdog(self, config):
        application = config["allowedApplication"]
        restart_delay_ms = int(application.get("restartDelayMs", 2000))
        return LegacyProcessWatchdog(
            executable_path=application["path"],
            arguments=application.get("arguments", ""),
            working_directory=application.get("workingDirectory", ""),
            restart_on_exit=application.get("restartOnExit", True),
            restart_delay_seconds=float(restart_delay_ms) / 1000.0,
            single_instance=application.get("singleInstance", True),
            start_maximized=application.get("startMaximized", False),
            backend=self.process_backend,
            logger=self.logger,
        )

    def authenticate(self, username, password):
        self._close_admin_session()
        result, session = self.authenticator.begin_session(username, password)
        if result.success:
            self.admin_session = session
        return result

    def tick_watchdog(self):
        return self.watchdog.tick()

    def is_allowed_application_minimized(self):
        return self.window_controller.is_minimized(self.app_path)

    def bring_allowed_application_to_front(self, wait=False):
        if wait:
            return self.window_controller.wait_and_bring_to_front(
                self.app_path,
                timeout_seconds=5,
                start_maximized=self.config["allowedApplication"].get(
                    "startMaximized", False
                ),
            )
        return self.window_controller.bring_to_front(self.app_path)

    def restore_allowed_application(self):
        return self.window_controller.restore(self.app_path)

    def _require_admin_session(self):
        if self.admin_session is None or self.admin_session.closed:
            raise AccessDeniedError(
                u"Отказано в доступе. Требуется активная сессия администратора Windows."
            )

    def stop_supervision(self):
        self._require_admin_session()
        self.watchdog.stop_supervision()

    def start_supervision(self):
        self._require_admin_session()
        self.watchdog.start_supervision()

    def change_allowed_application(self, path):
        self._require_admin_session()
        path = os.path.abspath(path)
        if not os.path.isfile(path) or os.path.splitext(path)[1].lower() != ".exe":
            raise ValueError(u"Разрешённое приложение не найдено: %s" % path)

        previous_config = copy.deepcopy(self.config)
        updated_config = copy.deepcopy(self.config)
        application = updated_config["allowedApplication"]
        application["path"] = path
        application["workingDirectory"] = os.path.dirname(path)

        def write_updated():
            save_config(updated_config, self.config_path)

        self.admin_session.run(write_updated)
        previous_watchdog = self.watchdog
        previous_watchdog.stop_supervision()
        try:
            next_watchdog = self.watchdog_factory(updated_config)
            next_watchdog.tick()
        except Exception:
            self.admin_session.run(
                lambda: save_config(previous_config, self.config_path)
            )
            previous_watchdog.start_supervision()
            raise
        self.config = updated_config
        self.watchdog = next_watchdog
        self.bring_allowed_application_to_front(wait=True)
        self.logger.log("admin.change_allowed_application", {"path": path})

    def open_desktop(self):
        self._require_admin_session()
        return self.desktop_manager.open_current_desktop()

    def return_to_kiosk(self):
        self.desktop_manager.hide_current_desktop()
        self._close_admin_session()
        self.watchdog.start_supervision()

    def _close_admin_session(self):
        if self.admin_session is not None:
            self.admin_session.close()
            self.admin_session = None

    def close(self):
        self.keyboard_filter.stop()
        self._close_admin_session()
