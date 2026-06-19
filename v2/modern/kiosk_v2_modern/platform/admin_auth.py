# -*- coding: utf-8 -*-
import ctypes

from ctypes import wintypes


ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_DISABLED = 1331
ERROR_NO_IMPERSONATION_TOKEN = 1309
LOGON32_LOGON_INTERACTIVE = 2
LOGON32_PROVIDER_DEFAULT = 0
SECURITY_IMPERSONATION = 2
WIN_BUILTIN_ADMINISTRATORS_SID = 26
SECURITY_MAX_SID_SIZE = 68


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
    def __init__(self, api=None):
        self.api = api or NativeAuthApi()

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


class NativeAuthApi(object):
    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        self.advapi32.LogonUserW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        self.advapi32.LogonUserW.restype = wintypes.BOOL
        self.advapi32.CreateWellKnownSid.argtypes = [
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.CreateWellKnownSid.restype = wintypes.BOOL
        self.advapi32.CheckTokenMembership.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.BOOL),
        ]
        self.advapi32.CheckTokenMembership.restype = wintypes.BOOL
        self.advapi32.DuplicateToken.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        self.advapi32.DuplicateToken.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.GetLastError.argtypes = []
        self.kernel32.GetLastError.restype = wintypes.DWORD

    def logon_local(self, username, password):
        return self._logon_user(username, password)

    def is_local_administrator(self, token):
        administrators_sid = self._create_administrators_sid()
        try:
            return self._check_token_membership(token, administrators_sid)
        except WindowsAuthError as error:
            if error.code != ERROR_NO_IMPERSONATION_TOKEN:
                raise
        duplicate = self._duplicate_impersonation_token(token)
        try:
            return self._check_token_membership(duplicate, administrators_sid)
        finally:
            self._close_handle(duplicate)

    def close_token(self, token):
        self._close_handle(token)

    def _logon_user(self, username, password):
        token = wintypes.HANDLE()
        if not self.advapi32.LogonUserW(
            username,
            ".",
            password,
            LOGON32_LOGON_INTERACTIVE,
            LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token),
        ):
            raise self._error()
        return token

    def _create_administrators_sid(self):
        sid = ctypes.create_string_buffer(SECURITY_MAX_SID_SIZE)
        size = wintypes.DWORD(len(sid))
        if not self.advapi32.CreateWellKnownSid(
            WIN_BUILTIN_ADMINISTRATORS_SID,
            None,
            sid,
            ctypes.byref(size),
        ):
            raise self._error()
        return sid

    def _check_token_membership(self, token, sid):
        is_member = wintypes.BOOL()
        if not self.advapi32.CheckTokenMembership(
            token,
            sid,
            ctypes.byref(is_member),
        ):
            raise self._error()
        return bool(is_member.value)

    def _duplicate_impersonation_token(self, token):
        duplicate = wintypes.HANDLE()
        if not self.advapi32.DuplicateToken(
            token,
            SECURITY_IMPERSONATION,
            ctypes.byref(duplicate),
        ):
            raise self._error()
        return duplicate

    def _close_handle(self, token):
        if token:
            self.kernel32.CloseHandle(token)

    def _error(self):
        return WindowsAuthError(int(self.kernel32.GetLastError()))
