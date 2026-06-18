# -*- coding: utf-8 -*-

from legacy_kiosk.win32_accounts import (
    ERROR_ACCOUNT_DISABLED,
    LOGON_DENIED_ERRORS,
    WindowsAccountBackend,
    WindowsAuthError,
)


AUTH_SUCCESS = "success"
AUTH_BAD_CREDENTIALS = "bad_credentials"
AUTH_ACCOUNT_DISABLED = "account_disabled"
AUTH_NOT_ADMIN = "not_admin"
AUTH_WINDOWS_ERROR = "windows_error"

MESSAGE_BAD_CREDENTIALS = (
    u"Отказано в доступе. Неверное имя пользователя или пароль."
)
MESSAGE_ACCOUNT_DISABLED = (
    u"Отказано в доступе. Указанная локальная учётная запись отключена."
)
MESSAGE_NOT_ADMIN = (
    u"Отказано в доступе. Указанная учётная запись не является "
    u"администратором Windows."
)
MESSAGE_WINDOWS_ERROR = u"Отказано в доступе. Ошибка Windows/API."


class AuthResult(object):
    def __init__(self, code, message, account_name=u"", error_code=None):
        self.code = code
        self.message = message
        self.account_name = account_name
        self.error_code = error_code

    @property
    def success(self):
        return self.code == AUTH_SUCCESS

    def to_log_data(self):
        data = {"code": self.code, "account_name": self.account_name}
        if self.error_code is not None:
            data["error_code"] = int(self.error_code)
        return data


def normalize_local_account_name(account_name):
    account_name = (account_name or u"").strip()
    if account_name.startswith(u".\\"):
        account_name = account_name[2:].strip()
    if u"\\" in account_name or u"@" in account_name:
        return u""
    return account_name


class LocalAdminAuthenticator(object):
    def __init__(self, backend=None, logger=None):
        self.backend = backend or WindowsAccountBackend()
        self.logger = logger

    def authenticate(self, account_name, password):
        local_name = normalize_local_account_name(account_name)
        if not local_name or not password:
            result = AuthResult(
                AUTH_BAD_CREDENTIALS, MESSAGE_BAD_CREDENTIALS, local_name
            )
            self._log_result(result)
            return result

        token = None
        try:
            token = self.backend.logon_local_user(local_name, password)
            if not token:
                result = AuthResult(
                    AUTH_BAD_CREDENTIALS, MESSAGE_BAD_CREDENTIALS, local_name
                )
            elif self.backend.token_is_local_admin(token):
                result = AuthResult(
                    AUTH_SUCCESS, u"Доступ разрешён.", local_name
                )
            else:
                result = AuthResult(AUTH_NOT_ADMIN, MESSAGE_NOT_ADMIN, local_name)
        except WindowsAuthError as error:
            result = self._result_for_windows_error(local_name, error)
        except Exception:
            result = AuthResult(AUTH_WINDOWS_ERROR, MESSAGE_WINDOWS_ERROR, local_name)
        finally:
            if token is not None:
                self.backend.close_handle(token)
            password = None

        self._log_result(result)
        return result

    def _result_for_windows_error(self, account_name, error):
        if error.error_code == ERROR_ACCOUNT_DISABLED:
            return AuthResult(
                AUTH_ACCOUNT_DISABLED,
                MESSAGE_ACCOUNT_DISABLED,
                account_name,
                error.error_code,
            )
        if error.error_code in LOGON_DENIED_ERRORS:
            return AuthResult(
                AUTH_BAD_CREDENTIALS,
                MESSAGE_BAD_CREDENTIALS,
                account_name,
                error.error_code,
            )
        return AuthResult(
            AUTH_WINDOWS_ERROR,
            MESSAGE_WINDOWS_ERROR,
            account_name,
            error.error_code,
        )

    def _log_result(self, result):
        if self.logger is None:
            return
        try:
            self.logger.log("admin_authentication", result.to_log_data())
        except Exception:
            pass

