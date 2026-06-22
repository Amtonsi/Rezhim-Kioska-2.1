# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes

from ctypes import wintypes


ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_DISABLED = 1331
ERROR_NO_IMPERSONATION_TOKEN = 1309
NERR_SUCCESS = 0
LOGON32_LOGON_INTERACTIVE = 2
LOGON32_PROVIDER_DEFAULT = 0
SECURITY_IMPERSONATION = 2
WIN_BUILTIN_ADMINISTRATORS_SID = 26
SECURITY_MAX_SID_SIZE = 68
LG_INCLUDE_INDIRECT = 0x0001
MAX_PREFERRED_LENGTH = 0xFFFFFFFF


class LOCALGROUP_USERS_INFO_0(ctypes.Structure):
    _fields_ = [("lgrui0_name", wintypes.LPWSTR)]


class WindowsAuthError(Exception):
    def __init__(self, code):
        self.code = int(code)
        Exception.__init__(self, "Windows authentication failed")


class AuthResult(object):
    __slots__ = ("success", "code", "username", "windows_error")

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
            if not self._is_local_administrator(username, token):
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

    @staticmethod
    def _is_local_username(username):
        return bool(username) and not any(
            separator in username for separator in ("\\", "/", "@")
        )

    def _is_local_administrator(self, username, token):
        if hasattr(self.api, "user_in_local_administrators"):
            try:
                if self.api.user_in_local_administrators(username):
                    return True
            except WindowsAuthError:
                pass
        return self.api.is_local_administrator(token)

    @staticmethod
    def _code_for_windows_error(code):
        if int(code) == ERROR_LOGON_FAILURE:
            return "bad_credentials"
        if int(code) == ERROR_ACCOUNT_DISABLED:
            return "disabled_account"
        return "api_error"


class NativeAuthApi(object):
    def __init__(self, advapi32=None, kernel32=None, netapi32=None):
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.netapi32 = netapi32 or ctypes.windll.netapi32
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
        self.advapi32.LookupAccountSidW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPVOID,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.LookupAccountSidW.restype = wintypes.BOOL
        self.netapi32.NetUserGetLocalGroups.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPVOID),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.netapi32.NetUserGetLocalGroups.restype = wintypes.DWORD
        self.netapi32.NetApiBufferFree.argtypes = [wintypes.LPVOID]
        self.netapi32.NetApiBufferFree.restype = wintypes.DWORD
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def logon_local(self, username, password):
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

    def is_local_administrator(self, token):
        sid = self._create_administrators_sid()
        try:
            return self._check_token_membership(token, sid)
        except WindowsAuthError as error:
            if error.code != ERROR_NO_IMPERSONATION_TOKEN:
                raise
        duplicate = self._duplicate_impersonation_token(token)
        try:
            return self._check_token_membership(duplicate, sid)
        finally:
            self._close_handle(duplicate)

    def close_token(self, token):
        self._close_handle(token)

    def user_in_local_administrators(self, username):
        administrators_group = self._localized_administrators_group_name()
        groups = self._local_group_names_for_user(username)
        expected = administrators_group.lower()
        for group in groups:
            if (group or "").lower() == expected:
                return True
        return False

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

    def _localized_administrators_group_name(self):
        sid = self._create_administrators_sid()
        name = ctypes.create_unicode_buffer(256)
        name_size = wintypes.DWORD(len(name))
        domain = ctypes.create_unicode_buffer(256)
        domain_size = wintypes.DWORD(len(domain))
        sid_type = wintypes.DWORD()
        if not self.advapi32.LookupAccountSidW(
            None,
            sid,
            name,
            ctypes.byref(name_size),
            domain,
            ctypes.byref(domain_size),
            ctypes.byref(sid_type),
        ):
            return "Administrators"
        return name.value or "Administrators"

    def _local_group_names_for_user(self, username):
        buffer = wintypes.LPVOID()
        entries_read = wintypes.DWORD()
        total_entries = wintypes.DWORD()
        status = int(
            self.netapi32.NetUserGetLocalGroups(
                None,
                username,
                0,
                LG_INCLUDE_INDIRECT,
                ctypes.byref(buffer),
                MAX_PREFERRED_LENGTH,
                ctypes.byref(entries_read),
                ctypes.byref(total_entries),
            )
        )
        if status != NERR_SUCCESS:
            raise WindowsAuthError(status)
        try:
            group_array = ctypes.cast(
                buffer,
                ctypes.POINTER(LOCALGROUP_USERS_INFO_0 * entries_read.value),
            ).contents
            return [
                group_array[index].lgrui0_name
                for index in range(entries_read.value)
            ]
        finally:
            if buffer:
                self.netapi32.NetApiBufferFree(buffer)

    def _check_token_membership(self, token, sid):
        is_member = wintypes.BOOL()
        if not self.advapi32.CheckTokenMembership(
            token, sid, ctypes.byref(is_member)
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

    def _close_handle(self, handle):
        if handle:
            self.kernel32.CloseHandle(handle)

    def _error(self):
        return WindowsAuthError(int(self.kernel32.GetLastError()))
