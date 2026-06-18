# -*- coding: utf-8 -*-

import unittest

from legacy_kiosk.local_admin_auth import (
    AUTH_ACCOUNT_DISABLED,
    AUTH_BAD_CREDENTIALS,
    AUTH_NOT_ADMIN,
    AUTH_SUCCESS,
    LocalAdminAuthenticator,
)
from legacy_kiosk.win32_accounts import (
    ERROR_ACCOUNT_DISABLED,
    ERROR_LOGON_FAILURE,
    ERROR_NO_IMPERSONATION_TOKEN,
    WindowsAccountBackend,
    WindowsAuthError,
)


class FakeLogger(object):
    def __init__(self):
        self.records = []

    def log(self, event, data):
        self.records.append((event, data))


class FakeAccountBackend(object):
    def __init__(self, token=None, is_admin=False, error=None, admin_error=None):
        self.token = token
        self.is_admin = is_admin
        self.error = error
        self.admin_error = admin_error
        self.calls = []

    def logon_local_user(self, account_name, password):
        self.calls.append(("logon", account_name, password))
        if self.error is not None:
            raise self.error
        return self.token

    def token_is_local_admin(self, token):
        self.calls.append(("admin", token))
        if self.admin_error is not None:
            raise self.admin_error
        return self.is_admin

    def close_handle(self, token):
        self.calls.append(("close", token))


class LegacyLocalAdminAuthTests(unittest.TestCase):
    def test_accepts_valid_local_administrator_and_closes_token(self):
        backend = FakeAccountBackend(token="admin-token", is_admin=True)
        logger = FakeLogger()
        authenticator = LocalAdminAuthenticator(backend=backend, logger=logger)

        result = authenticator.authenticate("Admin", "secret")

        self.assertTrue(result.success)
        self.assertEqual(AUTH_SUCCESS, result.code)
        self.assertEqual("Admin", result.account_name)
        self.assertEqual(("close", "admin-token"), backend.calls[-1])
        self.assertNotIn("secret", repr(logger.records))

    def test_rejects_bad_credentials_without_logging_password(self):
        backend = FakeAccountBackend(
            error=WindowsAuthError("LogonUserW", ERROR_LOGON_FAILURE)
        )
        logger = FakeLogger()
        authenticator = LocalAdminAuthenticator(backend=backend, logger=logger)

        result = authenticator.authenticate("Admin", "wrong-password")

        self.assertFalse(result.success)
        self.assertEqual(AUTH_BAD_CREDENTIALS, result.code)
        self.assertNotIn("wrong-password", repr(logger.records))

    def test_rejects_disabled_account_with_specific_result(self):
        backend = FakeAccountBackend(
            error=WindowsAuthError("LogonUserW", ERROR_ACCOUNT_DISABLED)
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate("DisabledAdmin", "secret")

        self.assertFalse(result.success)
        self.assertEqual(AUTH_ACCOUNT_DISABLED, result.code)
        self.assertIn(u"отключена", result.message.lower())

    def test_rejects_valid_non_administrator_and_closes_token(self):
        backend = FakeAccountBackend(token="user-token", is_admin=False)
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate("User", "secret")

        self.assertFalse(result.success)
        self.assertEqual(AUTH_NOT_ADMIN, result.code)
        self.assertEqual(("close", "user-token"), backend.calls[-1])

    def test_closes_token_when_admin_membership_check_fails(self):
        backend = FakeAccountBackend(
            token="admin-token",
            admin_error=WindowsAuthError("CheckTokenMembership", 5),
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate("Admin", "secret")

        self.assertFalse(result.success)
        self.assertEqual(("close", "admin-token"), backend.calls[-1])

    def test_rejects_domain_qualified_account_names(self):
        backend = FakeAccountBackend(token="unused", is_admin=True)
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate("DOMAIN\\Admin", "secret")

        self.assertFalse(result.success)
        self.assertEqual(AUTH_BAD_CREDENTIALS, result.code)
        self.assertEqual([], backend.calls)

    def test_backend_retries_membership_with_impersonation_token_on_1309(self):
        class Backend(WindowsAccountBackend):
            def __init__(self):
                self.calls = []

            def _allocate_admin_sid(self):
                self.calls.append(("allocate",))
                return "admin-sid"

            def _free_sid(self, sid):
                self.calls.append(("free", sid))

            def _check_token_membership(self, token, sid):
                self.calls.append(("check", token, sid))
                if token == "primary-token":
                    raise WindowsAuthError(
                        "CheckTokenMembership", ERROR_NO_IMPERSONATION_TOKEN
                    )
                return True

            def _duplicate_for_membership(self, token):
                self.calls.append(("duplicate", token))
                return "impersonation-token"

            def close_handle(self, token):
                self.calls.append(("close", token))

            def _token_contains_group_sid(self, token, sid):
                self.calls.append(("scan", token, sid))
                return False

        backend = Backend()

        self.assertTrue(backend.token_is_local_admin("primary-token"))
        self.assertEqual(
            [
                ("allocate",),
                ("check", "primary-token", "admin-sid"),
                ("duplicate", "primary-token"),
                ("check", "impersonation-token", "admin-sid"),
                ("close", "impersonation-token"),
                ("free", "admin-sid"),
            ],
            backend.calls,
        )

    def test_backend_accepts_admin_sid_from_filtered_token_groups(self):
        class Backend(WindowsAccountBackend):
            def __init__(self):
                self.calls = []

            def _allocate_admin_sid(self):
                return "admin-sid"

            def _free_sid(self, sid):
                self.calls.append(("free", sid))

            def _check_membership_with_fallback(self, token, sid):
                self.calls.append(("active", token, sid))
                return False

            def _token_contains_group_sid(self, token, sid):
                self.calls.append(("scan", token, sid))
                return True

        backend = Backend()

        self.assertTrue(backend.token_is_local_admin("filtered-token"))
        self.assertEqual(
            [
                ("active", "filtered-token", "admin-sid"),
                ("scan", "filtered-token", "admin-sid"),
                ("free", "admin-sid"),
            ],
            backend.calls,
        )


if __name__ == "__main__":
    unittest.main()
