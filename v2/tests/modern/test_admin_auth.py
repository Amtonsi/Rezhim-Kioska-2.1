# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.admin_auth import (
    AuthResult,
    WindowsAdminAuth,
    WindowsAuthError,
)


class FakeAuthApi(object):
    def __init__(self, valid=True, administrator=True, error_code=1326):
        self.valid = valid
        self.administrator = administrator
        self.error_code = error_code
        self.token = 77
        self.closed = []
        self.logon_calls = []

    def logon_local(self, username, password):
        self.logon_calls.append((username, password))
        if not self.valid:
            raise WindowsAuthError(self.error_code)
        return self.token

    def is_local_administrator(self, token):
        return self.administrator

    def close_token(self, token):
        self.closed.append(token)


class WindowsAdminAuthTests(unittest.TestCase):
    def test_accepts_valid_local_administrator_and_closes_token(self):
        api = FakeAuthApi(valid=True, administrator=True)
        auth = WindowsAdminAuth(api)

        result = auth.authenticate("Admin", "secret")

        self.assertTrue(result.success)
        self.assertEqual("success", result.code)
        self.assertEqual([api.token], api.closed)
        self.assertNotIn("secret", repr(auth.__dict__))
        self.assertNotIn("secret", repr(result.to_log_data()))

    def test_rejects_valid_non_admin_and_closes_token(self):
        api = FakeAuthApi(valid=True, administrator=False)

        result = WindowsAdminAuth(api).authenticate("User", "secret")

        self.assertFalse(result.success)
        self.assertEqual("not_administrator", result.code)
        self.assertEqual([api.token], api.closed)

    def test_maps_bad_credentials_without_token_or_password_log(self):
        api = FakeAuthApi(valid=False, error_code=1326)

        result = WindowsAdminAuth(api).authenticate("Admin", "secret")

        self.assertEqual("bad_credentials", result.code)
        self.assertEqual([], api.closed)
        self.assertNotIn("secret", repr(result.to_log_data()))
        self.assertNotIn("password", repr(result.to_log_data()).lower())

    def test_rejects_domain_qualified_names_before_logon(self):
        for username in (r"PC\Admin", r".\Admin", "admin@example.test", "a/b"):
            api = FakeAuthApi()

            result = WindowsAdminAuth(api).authenticate(username, "secret")

            self.assertEqual("invalid_local_username", result.code)
            self.assertEqual([], api.logon_calls)

    def test_auth_result_log_data_contains_only_safe_fields(self):
        result = AuthResult(False, "api_error", "Admin", 5)

        self.assertEqual(
            {
                "success": False,
                "code": "api_error",
                "username": "Admin",
                "windows_error": 5,
            },
            result.to_log_data(),
        )


if __name__ == "__main__":
    unittest.main()
