# -*- coding: utf-8 -*-

import os

from python_kiosk.config import load_config, save_config
from python_kiosk.logging_service import KioskLogger
from python_kiosk.security import hash_password
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class AdminActions(object):
    def __init__(self, config_path, logger=None, backend=None):
        self.config_path = config_path
        self.logger = logger or KioskLogger()
        self.backend = backend or WindowsSystemBackend()

    def _require_admin(self, action):
        if not self.backend.is_admin():
            self.logger.warning("admin.action_denied", action=action)
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

    def set_allowed_app_path(self, app_path):
        self._require_admin("set_allowed_app_path")
        if not os.path.isfile(app_path):
            raise ValueError(
                "Разрешённое приложение не найдено: {0}".format(app_path)
            )
        config = load_config(self.config_path)
        previous = config.app_path
        config.app_path = app_path
        save_config(config, self.config_path)
        self.logger.info("admin.set_app_path", previous=previous, current=app_path)

    def change_kiosk_admin_password(self, new_password):
        self._require_admin("change_kiosk_admin_password")
        if not new_password:
            raise ValueError("Новый пароль обязателен.")
        config = load_config(self.config_path)
        record = hash_password(new_password)
        config.admin_password_hash = record["hash"]
        config.admin_password_salt = record["salt"]
        config.admin_password_algorithm = record["algorithm"]
        config.admin_password_iterations = record["iterations"]
        save_config(config, self.config_path)
        self.logger.info("admin.change_password")
