# -*- coding: utf-8 -*-

import os


AUTH_SUCCESS = "success"
AUTH_BAD_CREDENTIALS = "bad_credentials"
AUTH_NOT_ADMIN = "not_admin"
AUTH_WINDOWS_ERROR = "windows_error"

ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_RESTRICTION = 1327
ERROR_INVALID_LOGON_HOURS = 1328
ERROR_INVALID_WORKSTATION = 1329
ERROR_PASSWORD_EXPIRED = 1330
ERROR_ACCOUNT_DISABLED = 1331
ERROR_ACCOUNT_EXPIRED = 1793
ERROR_ACCOUNT_LOCKED_OUT = 1909
ERROR_NO_IMPERSONATION_TOKEN = 1309
LOGON_DENIED_ERRORS = set(
    [
        ERROR_LOGON_FAILURE,
        ERROR_ACCOUNT_RESTRICTION,
        ERROR_INVALID_LOGON_HOURS,
        ERROR_INVALID_WORKSTATION,
        ERROR_PASSWORD_EXPIRED,
        ERROR_ACCOUNT_DISABLED,
        ERROR_ACCOUNT_EXPIRED,
        ERROR_ACCOUNT_LOCKED_OUT,
    ]
)

MESSAGE_BAD_CREDENTIALS = "Отказано в доступе. Неверное имя пользователя или пароль."
MESSAGE_NOT_ADMIN = (
    "Отказано в доступе. Указанная учётная запись не является администратором Windows."
)
MESSAGE_WINDOWS_ERROR = "Отказано в доступе. ошибка Windows/API: {0}"


class WindowsAuthError(Exception):
    def __init__(self, api_name, error_code=None, message=None):
        self.api_name = api_name
        self.error_code = error_code
        text = message or "{0} failed".format(api_name)
        if error_code is not None:
            text = "{0} failed with code {1}".format(api_name, error_code)
        Exception.__init__(self, text)


class AuthResult(object):
    def __init__(self, code, username="", domain="", message="", error_code=None):
        self.code = code
        self.username = username
        self.domain = domain
        self.message = message
        self.error_code = error_code

    @property
    def success(self):
        return self.code == AUTH_SUCCESS

    def to_log_data(self):
        data = {
            "code": self.code,
            "username": self.username,
            "domain": self.domain,
        }
        if self.error_code is not None:
            data["error_code"] = self.error_code
        return data


def parse_windows_account_name(account_name):
    account_name = (account_name or "").strip()
    if "\\" in account_name:
        domain, username = account_name.split("\\", 1)
        return domain or ".", username.strip()
    return ".", account_name


class WindowsAuthBackend(object):
    LOGON32_LOGON_INTERACTIVE = 2
    LOGON32_PROVIDER_DEFAULT = 0
    SECURITY_BUILTIN_DOMAIN_RID = 0x00000020
    DOMAIN_ALIAS_RID_ADMINS = 0x00000220
    SECURITY_IMPERSONATION = 2
    TOKEN_GROUPS = 2
    ERROR_INSUFFICIENT_BUFFER = 122

    def logon_user(self, username, domain, password):
        if os.name != "nt":
            return None

        import ctypes
        from ctypes import wintypes

        token = wintypes.HANDLE()
        ok = ctypes.windll.advapi32.LogonUserW(
            username,
            domain,
            password,
            self.LOGON32_LOGON_INTERACTIVE,
            self.LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token),
        )
        if not ok:
            error_code = ctypes.GetLastError()
            if error_code in LOGON_DENIED_ERRORS:
                return None
            raise WindowsAuthError("LogonUserW", error_code)
        return token

    def is_local_admin(self, token):
        if os.name != "nt" or not token:
            return False

        admin_sid = self._allocate_admin_sid()
        try:
            if self._check_token_membership_with_fallback(token, admin_sid):
                return True
            return self._token_contains_group_sid(token, admin_sid)
        finally:
            self._free_sid(admin_sid)

    def _allocate_admin_sid(self):
        import ctypes

        class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
            _fields_ = [("Value", ctypes.c_ubyte * 6)]

        nt_authority = SID_IDENTIFIER_AUTHORITY((0, 0, 0, 0, 0, 5))
        admin_sid = ctypes.c_void_p()
        ok = ctypes.windll.advapi32.AllocateAndInitializeSid(
            ctypes.byref(nt_authority),
            2,
            self.SECURITY_BUILTIN_DOMAIN_RID,
            self.DOMAIN_ALIAS_RID_ADMINS,
            0,
            0,
            0,
            0,
            0,
            0,
            ctypes.byref(admin_sid),
        )
        if not ok:
            raise WindowsAuthError("AllocateAndInitializeSid", ctypes.GetLastError())
        return admin_sid

    def _free_sid(self, sid):
        import ctypes

        ctypes.windll.advapi32.FreeSid(sid)

    def _check_token_membership_with_fallback(self, token, admin_sid):
        try:
            return self._check_token_membership(token, admin_sid)
        except WindowsAuthError as error:
            if (
                error.api_name != "CheckTokenMembership"
                or error.error_code != ERROR_NO_IMPERSONATION_TOKEN
            ):
                raise

        impersonation_token = self._duplicate_token_for_membership(token)
        try:
            return self._check_token_membership(impersonation_token, admin_sid)
        finally:
            self.close_token(impersonation_token)

    def _check_token_membership(self, token, admin_sid):
        import ctypes
        from ctypes import wintypes

        is_member = wintypes.BOOL()
        ok = ctypes.windll.advapi32.CheckTokenMembership(
            token,
            admin_sid,
            ctypes.byref(is_member),
        )
        if not ok:
            raise WindowsAuthError("CheckTokenMembership", ctypes.GetLastError())
        return bool(is_member.value)

    def _duplicate_token_for_membership(self, token):
        import ctypes
        from ctypes import wintypes

        impersonation_token = wintypes.HANDLE()
        ok = ctypes.windll.advapi32.DuplicateToken(
            token,
            self.SECURITY_IMPERSONATION,
            ctypes.byref(impersonation_token),
        )
        if not ok:
            raise WindowsAuthError("DuplicateToken", ctypes.GetLastError())
        return impersonation_token

    def _token_contains_group_sid(self, token, expected_sid):
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.windll.advapi32
        self._configure_token_query_api(advapi32)

        class SID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [
                ("Sid", ctypes.c_void_p),
                ("Attributes", wintypes.DWORD),
            ]

        class TOKEN_GROUPS_HEADER(ctypes.Structure):
            _fields_ = [
                ("GroupCount", wintypes.DWORD),
                ("Groups", SID_AND_ATTRIBUTES * 1),
            ]

        required_size = wintypes.DWORD(0)
        advapi32.GetTokenInformation(
            token,
            self.TOKEN_GROUPS,
            None,
            0,
            ctypes.byref(required_size),
        )
        error_code = ctypes.GetLastError()
        if error_code != self.ERROR_INSUFFICIENT_BUFFER or not required_size.value:
            raise WindowsAuthError("GetTokenInformation", error_code)

        buffer = ctypes.create_string_buffer(required_size.value)
        ok = advapi32.GetTokenInformation(
            token,
            self.TOKEN_GROUPS,
            buffer,
            required_size,
            ctypes.byref(required_size),
        )
        if not ok:
            raise WindowsAuthError("GetTokenInformation", ctypes.GetLastError())

        header = ctypes.cast(buffer, ctypes.POINTER(TOKEN_GROUPS_HEADER)).contents
        group_count = int(header.GroupCount)
        groups_offset = TOKEN_GROUPS_HEADER.Groups.offset
        groups_pointer = ctypes.cast(
            ctypes.addressof(buffer) + groups_offset,
            ctypes.POINTER(SID_AND_ATTRIBUTES * group_count),
        )
        groups = groups_pointer.contents
        for index in range(group_count):
            sid_pointer = groups[index].Sid
            if sid_pointer and advapi32.EqualSid(
                sid_pointer,
                expected_sid,
            ):
                return True
        return False

    def _configure_token_query_api(self, advapi32):
        import ctypes
        from ctypes import wintypes

        advapi32.GetTokenInformation.restype = wintypes.BOOL
        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi32.EqualSid.restype = wintypes.BOOL
        advapi32.EqualSid.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]

    def close_token(self, token):
        if os.name != "nt" or not token:
            return

        import ctypes

        ctypes.windll.kernel32.CloseHandle(token)


class LocalAdminAuthenticator(object):
    def __init__(self, backend=None):
        self.backend = backend or WindowsAuthBackend()

    def authenticate(self, account_name, password):
        return self.authenticate_result(account_name, password).success

    def authenticate_result(self, account_name, password):
        domain, username = parse_windows_account_name(account_name)
        if not username or not password:
            return AuthResult(
                AUTH_BAD_CREDENTIALS,
                username=username,
                domain=domain,
                message=MESSAGE_BAD_CREDENTIALS,
            )

        try:
            token = self.backend.logon_user(username, domain, password)
        except Exception as error:
            return self._windows_error_result(username, domain, error)
        if not token:
            return AuthResult(
                AUTH_BAD_CREDENTIALS,
                username=username,
                domain=domain,
                message=MESSAGE_BAD_CREDENTIALS,
            )

        try:
            if self.backend.is_local_admin(token):
                return AuthResult(
                    AUTH_SUCCESS,
                    username=username,
                    domain=domain,
                    message="Доступ разрешён.",
                )
            return AuthResult(
                AUTH_NOT_ADMIN,
                username=username,
                domain=domain,
                message=MESSAGE_NOT_ADMIN,
            )
        except Exception as error:
            return self._windows_error_result(username, domain, error)
        finally:
            self.backend.close_token(token)

    def _windows_error_result(self, username, domain, error):
        error_code = getattr(error, "error_code", None)
        details = "код {0}".format(error_code) if error_code is not None else str(error)
        return AuthResult(
            AUTH_WINDOWS_ERROR,
            username=username,
            domain=domain,
            message=MESSAGE_WINDOWS_ERROR.format(details),
            error_code=error_code,
        )
