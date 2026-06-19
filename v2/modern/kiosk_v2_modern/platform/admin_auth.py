# -*- coding: utf-8 -*-


ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_DISABLED = 1331


class WindowsAuthError(Exception):
    def __init__(self, code):
        self.code = int(code)
        super(WindowsAuthError, self).__init__("Windows authentication failed")


class AuthResult(object):
    def __init__(self, success, code, username, windows_error=0):
        self.success = bool(success)
        self.code = code
        self.username = username
        self.windows_error = int(windows_error or 0)

    def to_log_data(self):
        return {
            "success": self.success,
            "code": self.code,
            "username": self.username,
            "windows_error": self.windows_error,
        }


class WindowsAdminAuth(object):
    def __init__(self, api):
        self.api = api

    def authenticate(self, username, password):
        username = (username or "").strip()
        if not self._is_local_username(username):
            return AuthResult(False, "invalid_local_username", username)

        token = None
        try:
            token = self.api.logon_local(username, password)
            if not self.api.is_local_administrator(token):
                return AuthResult(False, "not_administrator", username)
            return AuthResult(True, "success", username)
        except WindowsAuthError as error:
            return AuthResult(
                False,
                self._code_for_windows_error(error.code),
                username,
                error.code,
            )
        finally:
            if token is not None:
                self.api.close_token(token)

    def _is_local_username(self, username):
        if not username:
            return False
        return not any(separator in username for separator in ("\\", "/", "@"))

    def _code_for_windows_error(self, code):
        if int(code) == ERROR_LOGON_FAILURE:
            return "bad_credentials"
        if int(code) == ERROR_ACCOUNT_DISABLED:
            return "disabled_account"
        return "api_error"
