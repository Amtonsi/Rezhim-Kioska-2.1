# -*- coding: utf-8 -*-

import time

from python_kiosk.logging_service import KioskLogger


DEFAULT_ADMIN_SESSION_TIMEOUT_SECONDS = 300


class AdminSession(object):
    def __init__(
        self,
        timeout_seconds=DEFAULT_ADMIN_SESSION_TIMEOUT_SECONDS,
        time_func=None,
        logger=None,
    ):
        self.timeout_seconds = int(timeout_seconds)
        self.time_func = time_func or time.time
        self.logger = logger or KioskLogger()
        self.active = False
        self.username = ""
        self.expires_at = None
        self.desktop_unlocked = False
        self.kiosk_disabled = False
        self._timeout_logged = False

    def start(self, username):
        self.active = True
        self.username = username
        self.expires_at = self.time_func() + self.timeout_seconds
        self.desktop_unlocked = False
        self.kiosk_disabled = False
        self._timeout_logged = False
        self.logger.info("admin.session_started", **self.to_log_data())

    def is_active(self):
        if not self.active:
            return False
        if self.kiosk_disabled:
            return True
        if self.time_func() <= self.expires_at:
            return True
        self.active = False
        if not self._timeout_logged:
            self.logger.warning("admin.session_timeout", **self.to_log_data())
            self._timeout_logged = True
        return False

    def close(self, reason="manual"):
        was_active = self.active
        self.active = False
        self.desktop_unlocked = False
        if was_active:
            self.logger.info("admin.session_closed", reason=reason, **self.to_log_data())

    def mark_desktop_unlocked(self):
        self.desktop_unlocked = True
        self.logger.info("admin.desktop_unlocked", **self.to_log_data())

    def disable_kiosk(self):
        self.kiosk_disabled = True
        self.logger.warning("admin.kiosk_disabled", **self.to_log_data())

    def to_log_data(self):
        return {
            "username": self.username,
            "expires_at": self.expires_at,
            "desktop_unlocked": self.desktop_unlocked,
            "kiosk_disabled": self.kiosk_disabled,
        }
