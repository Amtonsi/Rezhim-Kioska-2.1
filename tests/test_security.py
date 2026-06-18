try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.security import FailedAttemptLimiter, hash_password, verify_password


class PasswordSecurityTests(unittest.TestCase):
    def test_password_hash_verifies_original_password(self):
        record = hash_password("change-me")

        self.assertTrue(verify_password("change-me", record))

    def test_wrong_password_does_not_verify(self):
        record = hash_password("change-me")

        self.assertFalse(verify_password("wrong-password", record))

    def test_same_password_uses_different_salts(self):
        first = hash_password("change-me")
        second = hash_password("change-me")

        self.assertNotEqual(first["salt"], second["salt"])
        self.assertNotEqual(first["hash"], second["hash"])
        self.assertNotIn("change-me", first["hash"])

    def test_failed_attempt_limiter_adds_delay_after_threshold(self):
        limiter = FailedAttemptLimiter(
            threshold=2,
            base_delay_seconds=3,
            max_delay_seconds=9,
        )

        self.assertEqual(0, limiter.record_failure())
        self.assertEqual(3, limiter.record_failure())
        self.assertEqual(6, limiter.record_failure())
        self.assertEqual(9, limiter.record_failure())

        limiter.record_success()

        self.assertEqual(0, limiter.record_failure())


if __name__ == "__main__":
    unittest.main()
