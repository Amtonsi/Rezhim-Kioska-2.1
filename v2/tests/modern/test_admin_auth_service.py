# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.admin_auth_service import RateLimitedAdminAuth
from kiosk_v2_modern.platform.admin_auth import AuthResult


class FakeClock(object):
    def __init__(self, value=0.0):
        self.value = value

    def monotonic(self):
        return self.value


class FakeAuth(object):
    def __init__(self, results=None, error=None):
        self.results = list(results or [])
        self.error = error
        self.call_count = 0
        self.usernames = []
        self.password_was_forwarded = []

    def authenticate(self, username, password):
        self.call_count += 1
        self.usernames.append(username)
        self.password_was_forwarded.append(bool(password))
        if self.error is not None:
            raise self.error
        return self.results.pop(0)


def denied(username="Admin"):
    return AuthResult(False, "bad_credentials", username, 1326)


def allowed(username="Admin"):
    return AuthResult(True, "success", username, 0)


class RateLimitedAdminAuthTests(unittest.TestCase):
    def test_third_failure_starts_delay_and_locked_attempt_skips_windows_api(self):
        clock = FakeClock(0.0)
        auth = FakeAuth([denied(), denied(), denied()])
        service = RateLimitedAdminAuth(
            auth,
            clock,
            max_failures=3,
            base_delay_seconds=2,
            max_delay_seconds=30,
        )

        first = service.authenticate("Admin", "first")
        second = service.authenticate("Admin", "second")
        third = service.authenticate("Admin", "third")
        locked = service.authenticate("OtherAdmin", "fourth")

        self.assertEqual(0, first.retry_after_seconds)
        self.assertEqual(0, second.retry_after_seconds)
        self.assertEqual(2, third.retry_after_seconds)
        self.assertEqual("locked_out", locked.code)
        self.assertEqual(2, locked.retry_after_seconds)
        self.assertEqual(3, auth.call_count)

    def test_delay_increases_after_each_post_threshold_failure(self):
        clock = FakeClock(0.0)
        auth = FakeAuth([denied(), denied(), denied(), denied(), denied()])
        service = RateLimitedAdminAuth(
            auth,
            clock,
            max_failures=3,
            base_delay_seconds=2,
            max_delay_seconds=30,
        )
        service.authenticate("Admin", "one")
        service.authenticate("Admin", "two")
        third = service.authenticate("Admin", "three")
        clock.value = 2.1
        fourth = service.authenticate("Admin", "four")
        clock.value = 6.2
        fifth = service.authenticate("Admin", "five")

        self.assertEqual(2, third.retry_after_seconds)
        self.assertEqual(4, fourth.retry_after_seconds)
        self.assertEqual(8, fifth.retry_after_seconds)
        self.assertEqual(5, auth.call_count)

    def test_success_resets_failure_count_and_delay(self):
        clock = FakeClock(0.0)
        auth = FakeAuth([denied(), denied(), denied(), allowed(), denied()])
        service = RateLimitedAdminAuth(auth, clock, max_failures=3)
        service.authenticate("Admin", "one")
        service.authenticate("Admin", "two")
        service.authenticate("Admin", "three")
        clock.value = 2.1

        success = service.authenticate("Admin", "correct")
        after_success = service.authenticate("Admin", "wrong-again")

        self.assertTrue(success.success)
        self.assertEqual(0, success.retry_after_seconds)
        self.assertFalse(after_success.success)
        self.assertEqual(0, after_success.retry_after_seconds)

    def test_password_is_forwarded_once_but_never_retained_or_logged(self):
        auth = FakeAuth([denied()])
        service = RateLimitedAdminAuth(auth, FakeClock())

        result = service.authenticate("Admin", "hunter2")

        self.assertEqual([True], auth.password_was_forwarded)
        self.assertNotIn("hunter2", repr(service.__dict__))
        self.assertNotIn("password", repr(result.to_log_data()).lower())
        self.assertNotIn("hunter2", repr(result.to_log_data()))

    def test_unexpected_auth_exception_is_safe_denial(self):
        auth = FakeAuth(error=RuntimeError("password=hunter2"))
        service = RateLimitedAdminAuth(auth, FakeClock())

        result = service.authenticate("Admin", "hunter2")

        self.assertFalse(result.success)
        self.assertEqual("api_error", result.code)
        self.assertEqual("RuntimeError", result.error_type)
        self.assertNotIn("hunter2", repr(result.to_log_data()))


if __name__ == "__main__":
    unittest.main()
