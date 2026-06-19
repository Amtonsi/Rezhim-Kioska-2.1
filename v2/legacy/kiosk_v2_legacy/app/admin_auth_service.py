# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import threading


class AuthAttemptResult(object):
    __slots__ = (
        "success",
        "code",
        "username",
        "windows_error",
        "failure_count",
        "retry_after_seconds",
        "error_type",
    )

    def __init__(
        self,
        success,
        code,
        username,
        windows_error=0,
        failure_count=0,
        retry_after_seconds=0,
        error_type="",
    ):
        self.success = bool(success)
        self.code = code
        self.username = username
        self.windows_error = int(windows_error or 0)
        self.failure_count = int(failure_count)
        self.retry_after_seconds = int(retry_after_seconds)
        self.error_type = error_type or ""

    def to_log_data(self):
        return {
            "success": self.success,
            "code": self.code,
            "username": self.username,
            "windowsError": self.windows_error,
            "failureCount": self.failure_count,
            "retryAfterSeconds": self.retry_after_seconds,
            "errorType": self.error_type,
        }


class RateLimitedAdminAuth(object):
    def __init__(
        self,
        windows_auth,
        clock,
        max_failures=3,
        base_delay_seconds=2,
        max_delay_seconds=30,
    ):
        self.windows_auth = windows_auth
        self.clock = clock
        self.max_failures = int(max_failures)
        self.base_delay_seconds = float(base_delay_seconds)
        self.max_delay_seconds = float(max_delay_seconds)
        if self.max_failures < 1 or self.base_delay_seconds <= 0:
            raise ValueError("Invalid authentication throttle")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("Invalid authentication throttle maximum")
        self.failure_count = 0
        self.next_allowed_at = 0.0
        self._lock = threading.RLock()

    def authenticate(self, username, password):
        with self._lock:
            now = float(self.clock.monotonic())
            if now < self.next_allowed_at:
                return AuthAttemptResult(
                    False,
                    "locked_out",
                    (username or "").strip(),
                    failure_count=self.failure_count,
                    retry_after_seconds=max(
                        1, int(math.ceil(self.next_allowed_at - now))
                    ),
                )
            try:
                auth_result = self.windows_auth.authenticate(username, password)
            except Exception as error:
                return self._failed(
                    (username or "").strip(),
                    "api_error",
                    0,
                    error.__class__.__name__,
                    now,
                )
            if auth_result.success:
                self.failure_count = 0
                self.next_allowed_at = 0.0
                return AuthAttemptResult(
                    True,
                    auth_result.code,
                    auth_result.username,
                    windows_error=auth_result.windows_error,
                )
            return self._failed(
                auth_result.username,
                auth_result.code,
                auth_result.windows_error,
                "",
                now,
            )

    def _failed(self, username, code, windows_error, error_type, now):
        self.failure_count += 1
        delay = 0.0
        if self.failure_count >= self.max_failures:
            exponent = self.failure_count - self.max_failures
            delay = min(
                self.base_delay_seconds * (2 ** exponent),
                self.max_delay_seconds,
            )
            self.next_allowed_at = now + delay
        else:
            self.next_allowed_at = 0.0
        return AuthAttemptResult(
            False,
            code,
            username,
            windows_error=windows_error,
            failure_count=self.failure_count,
            retry_after_seconds=int(math.ceil(delay)),
            error_type=error_type,
        )
