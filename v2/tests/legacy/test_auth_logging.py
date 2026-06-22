# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.admin_auth_service import RateLimitedAdminAuth
from kiosk_v2_legacy.platform.admin_auth import (
    AuthResult,
    NativeAuthApi,
    WindowsAdminAuth,
    WindowsAuthError,
)
from kiosk_v2_legacy.platform.audit_log import AuditLogger, SafeEvent


class FakeAuthApi(object):
    def __init__(self, valid=True, administrator=True):
        self.valid = valid
        self.administrator = administrator
        self.local_group_administrator = administrator
        self.token = 77
        self.closed = []
        self.calls = []

    def logon_local(self, username, password):
        self.calls.append((username, bool(password)))
        if not self.valid:
            raise WindowsAuthError(1326)
        return self.token

    def is_local_administrator(self, token):
        return self.administrator

    def user_in_local_administrators(self, username):
        return self.local_group_administrator

    def close_token(self, token):
        self.closed.append(token)


class MembershipNative(NativeAuthApi):
    def __init__(self):
        self.calls = []
        self.closed = []
        self.duplicate = 88

    def _create_administrators_sid(self):
        return "sid"

    def _check_token_membership(self, token, sid):
        self.calls.append(token)
        if token == 77:
            raise WindowsAuthError(1309)
        return True

    def _duplicate_impersonation_token(self, token):
        return self.duplicate

    def _close_handle(self, handle):
        self.closed.append(handle)


class FakeClock(object):
    def __init__(self, value=0.0):
        self.value = value

    def monotonic(self):
        return self.value

    def utcnow(self):
        return datetime.datetime(2026, 6, 19, 12, 30, 45, 123456)


class FakeAuth(object):
    def __init__(self, results):
        self.results = list(results)
        self.call_count = 0

    def authenticate(self, username, password):
        self.call_count += 1
        return self.results.pop(0)


def denied():
    return AuthResult(False, "bad_credentials", "Admin", 1326)


class LegacyAuthLoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kiosk-v2-legacy-log-")
        self.log_path = os.path.join(self.temp_dir, "legacy.jsonl")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_local_admin_auth_accepts_admin_and_closes_token(self):
        api = FakeAuthApi(valid=True, administrator=True)

        result = WindowsAdminAuth(api).authenticate("Admin", "secret")

        self.assertTrue(result.success)
        self.assertEqual([77], api.closed)
        self.assertNotIn("secret", repr(result.to_log_data()))

    def test_local_admin_auth_rejects_nonadmin_bad_password_and_domain_name(self):
        nonadmin = FakeAuthApi(valid=True, administrator=False)
        nonadmin.local_group_administrator = False
        result = WindowsAdminAuth(nonadmin).authenticate("User", "secret")
        self.assertEqual("not_administrator", result.code)
        self.assertEqual([77], nonadmin.closed)

        invalid = FakeAuthApi(valid=False)
        result = WindowsAdminAuth(invalid).authenticate("Admin", "wrong")
        self.assertEqual("bad_credentials", result.code)

        untouched = FakeAuthApi()
        result = WindowsAdminAuth(untouched).authenticate("DOMAIN\\Admin", "secret")
        self.assertEqual("invalid_local_username", result.code)
        self.assertEqual([], untouched.calls)

    def test_local_admin_group_accepts_uac_filtered_token(self):
        api = FakeAuthApi(valid=True, administrator=False)
        api.local_group_administrator = True

        result = WindowsAdminAuth(api).authenticate("impal", "secret")

        self.assertTrue(result.success)
        self.assertEqual("success", result.code)
        self.assertEqual([77], api.closed)

    def test_membership_1309_uses_duplicate_and_closes_it(self):
        native = MembershipNative()

        self.assertTrue(native.is_local_administrator(77))

        self.assertEqual([77, 88], native.calls)
        self.assertEqual([88], native.closed)

    def test_rate_limit_skips_windows_api_during_delay_and_resets_on_success(self):
        clock = FakeClock(0.0)
        auth = FakeAuth(
            [denied(), denied(), denied(), AuthResult(True, "success", "Admin")]
        )
        service = RateLimitedAdminAuth(auth, clock, max_failures=3)

        service.authenticate("Admin", "one")
        service.authenticate("Admin", "two")
        third = service.authenticate("Admin", "three")
        locked = service.authenticate("Admin", "four")
        clock.value = 2.1
        success = service.authenticate("Admin", "correct")

        self.assertEqual(2, third.retry_after_seconds)
        self.assertEqual("locked_out", locked.code)
        self.assertEqual(4, auth.call_count)
        self.assertTrue(success.success)
        self.assertNotIn("correct", repr(service.__dict__))

    def test_safe_event_redacts_immediately_and_drops_exception_message(self):
        event = SafeEvent(
            "auth_attempt",
            "Warning",
            {
                "username": "Admin",
                "password": "hunter2",
                "arguments": ["--secret", "value"],
                "error": RuntimeError("password=hunter2"),
            },
            clock=FakeClock(),
        )

        self.assertNotIn("hunter2", repr(event.__dict__))
        data = event.to_dict()
        self.assertEqual("[REDACTED]", data["password"])
        self.assertEqual("[REDACTED]", data["arguments"])
        self.assertEqual({"errorType": "RuntimeError"}, data["error"])

    def test_audit_log_writes_utf8_jsonl_and_rotates(self):
        logger = AuditLogger(
            self.log_path,
            max_bytes=240,
            backup_count=2,
            level="Debug",
            clock=FakeClock(),
        )
        for index in range(20):
            logger.emit(
                "diagnostic",
                level="Debug",
                sequence=index,
                description="Режим киоска",
                payload="x" * 80,
            )
        logger.close()

        paths = [
            path
            for path in (
                self.log_path,
                self.log_path + ".1",
                self.log_path + ".2",
            )
            if os.path.exists(path)
        ]
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            with io.open(path, "r", encoding="utf-8") as stream:
                for line in stream:
                    self.assertEqual("diagnostic", json.loads(line)["event"])


if __name__ == "__main__":
    unittest.main()
