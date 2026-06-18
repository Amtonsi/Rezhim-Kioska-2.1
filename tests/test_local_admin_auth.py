try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_NOT_ADMIN,
    AUTH_SUCCESS,
    AUTH_WINDOWS_ERROR,
    ERROR_NO_IMPERSONATION_TOKEN,
    LocalAdminAuthenticator,
    WindowsAuthBackend,
    WindowsAuthError,
    parse_windows_account_name,
)


class FakeWindowsAuthBackend(object):
    def __init__(self, accepted=None, admins=None, logon_error=None, admin_error=None):
        self.accepted = accepted or set()
        self.admins = admins or set()
        self.logon_error = logon_error
        self.admin_error = admin_error
        self.calls = []

    def logon_user(self, username, domain, password):
        self.calls.append(("logon", username, domain, password))
        if self.logon_error is not None:
            raise self.logon_error
        token = (domain, username)
        return token if token in self.accepted else None

    def is_local_admin(self, token):
        self.calls.append(("admin", token))
        if self.admin_error is not None:
            raise self.admin_error
        return token in self.admins

    def close_token(self, token):
        self.calls.append(("close", token))


class LocalAdminAuthTests(unittest.TestCase):
    def test_parse_account_name_defaults_to_local_computer(self):
        self.assertEqual((".", "Admin"), parse_windows_account_name("Admin"))
        self.assertEqual((".", "Admin"), parse_windows_account_name(".\\Admin"))
        self.assertEqual(("PC", "Admin"), parse_windows_account_name("PC\\Admin"))

    def test_authenticate_accepts_local_admin_credentials(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        self.assertTrue(authenticator.authenticate("Admin", "secret"))
        self.assertEqual(
            [
                ("logon", "Admin", ".", "secret"),
                ("admin", (".", "Admin")),
                ("close", (".", "Admin")),
            ],
            backend.calls,
        )

    def test_authenticate_rejects_non_admin_even_with_valid_password(self):
        backend = FakeWindowsAuthBackend(accepted={(".", "Operator")}, admins=set())
        authenticator = LocalAdminAuthenticator(backend=backend)

        self.assertFalse(authenticator.authenticate(".\\Operator", "secret"))
        self.assertIn(("close", (".", "Operator")), backend.calls)

    def test_authenticate_rejects_blank_credentials(self):
        authenticator = LocalAdminAuthenticator(backend=FakeWindowsAuthBackend())

        self.assertFalse(authenticator.authenticate("", "secret"))
        self.assertFalse(authenticator.authenticate("Admin", ""))

    def test_authenticate_result_accepts_local_admin_credentials(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "secret")

        self.assertEqual(AUTH_SUCCESS, result.code)
        self.assertTrue(result.success)
        self.assertEqual("Admin", result.username)
        self.assertEqual(".", result.domain)
        self.assertNotIn("secret", str(result.to_log_data()))

    def test_authenticate_result_rejects_bad_credentials(self):
        backend = FakeWindowsAuthBackend()
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "wrong")

        self.assertEqual(AUTH_BAD_CREDENTIALS, result.code)
        self.assertFalse(result.success)
        self.assertEqual(
            "Отказано в доступе. Неверное имя пользователя или пароль.",
            result.message,
        )

    def test_authenticate_result_rejects_non_admin_credentials(self):
        backend = FakeWindowsAuthBackend(accepted={(".", "Operator")}, admins=set())
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result(".\\Operator", "secret")

        self.assertEqual(AUTH_NOT_ADMIN, result.code)
        self.assertFalse(result.success)
        self.assertEqual(
            "Отказано в доступе. Указанная учётная запись не является администратором Windows.",
            result.message,
        )
        self.assertIn(("close", (".", "Operator")), backend.calls)

    def test_authenticate_result_reports_windows_api_error_and_closes_token(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
            admin_error=OSError("api failed"),
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "secret")

        self.assertEqual(AUTH_WINDOWS_ERROR, result.code)
        self.assertFalse(result.success)
        self.assertIn("ошибка Windows/API", result.message)
        self.assertIn(("close", (".", "Admin")), backend.calls)


    def test_windows_backend_retries_admin_check_with_impersonation_token_on_1309(self):
        class Backend(WindowsAuthBackend):
            def __init__(self):
                self.calls = []

            def _allocate_admin_sid(self):
                self.calls.append(("allocate_sid",))
                return "admin-sid"

            def _free_sid(self, sid):
                self.calls.append(("free_sid", sid))

            def _check_token_membership(self, token, sid):
                self.calls.append(("check", token, sid))
                if token == "primary-token":
                    raise WindowsAuthError(
                        "CheckTokenMembership",
                        ERROR_NO_IMPERSONATION_TOKEN,
                    )
                return token == "impersonation-token"

            def _duplicate_token_for_membership(self, token):
                self.calls.append(("duplicate", token))
                return "impersonation-token"

            def close_token(self, token):
                self.calls.append(("close", token))

        backend = Backend()

        self.assertTrue(backend.is_local_admin("primary-token"))
        self.assertEqual(
            [
                ("allocate_sid",),
                ("check", "primary-token", "admin-sid"),
                ("duplicate", "primary-token"),
                ("check", "impersonation-token", "admin-sid"),
                ("close", "impersonation-token"),
                ("free_sid", "admin-sid"),
            ],
            backend.calls,
        )

    def test_windows_backend_accepts_admin_sid_present_as_deny_only_group(self):
        class Backend(WindowsAuthBackend):
            def __init__(self):
                self.calls = []

            def _allocate_admin_sid(self):
                self.calls.append(("allocate_sid",))
                return "admin-sid"

            def _free_sid(self, sid):
                self.calls.append(("free_sid", sid))

            def _check_token_membership_with_fallback(self, token, sid):
                self.calls.append(("active_check", token, sid))
                return False

            def _token_contains_group_sid(self, token, sid):
                self.calls.append(("group_scan", token, sid))
                return True

        backend = Backend()

        self.assertTrue(backend.is_local_admin("filtered-admin-token"))
        self.assertEqual(
            [
                ("allocate_sid",),
                ("active_check", "filtered-admin-token", "admin-sid"),
                ("group_scan", "filtered-admin-token", "admin-sid"),
                ("free_sid", "admin-sid"),
            ],
            backend.calls,
        )

    def test_windows_backend_configures_64bit_safe_token_api_signatures(self):
        class FakeFunction(object):
            def __init__(self):
                self.restype = None
                self.argtypes = None

        class FakeAdvapi32(object):
            def __init__(self):
                self.GetTokenInformation = FakeFunction()
                self.EqualSid = FakeFunction()

        backend = WindowsAuthBackend()
        advapi32 = FakeAdvapi32()

        backend._configure_token_query_api(advapi32)

        self.assertIsNotNone(advapi32.GetTokenInformation.restype)
        self.assertIsNotNone(advapi32.GetTokenInformation.argtypes)
        self.assertIsNotNone(advapi32.EqualSid.restype)
        self.assertIsNotNone(advapi32.EqualSid.argtypes)


if __name__ == "__main__":
    unittest.main()
