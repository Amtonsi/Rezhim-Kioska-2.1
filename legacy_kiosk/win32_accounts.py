# -*- coding: utf-8 -*-

import ctypes
from ctypes import wintypes

from legacy_kiosk.compat import text_type


ERROR_INSUFFICIENT_BUFFER = 122
ERROR_NO_IMPERSONATION_TOKEN = 1309
ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_RESTRICTION = 1327
ERROR_INVALID_LOGON_HOURS = 1328
ERROR_INVALID_WORKSTATION = 1329
ERROR_PASSWORD_EXPIRED = 1330
ERROR_ACCOUNT_DISABLED = 1331
ERROR_ACCOUNT_EXPIRED = 1793
ERROR_ACCOUNT_LOCKED_OUT = 1909

LOGON_DENIED_ERRORS = frozenset(
    (
        ERROR_LOGON_FAILURE,
        ERROR_ACCOUNT_RESTRICTION,
        ERROR_INVALID_LOGON_HOURS,
        ERROR_INVALID_WORKSTATION,
        ERROR_PASSWORD_EXPIRED,
        ERROR_ACCOUNT_DISABLED,
        ERROR_ACCOUNT_EXPIRED,
        ERROR_ACCOUNT_LOCKED_OUT,
    )
)


class WindowsAuthError(Exception):
    def __init__(self, api_name, error_code):
        self.api_name = api_name
        self.error_code = int(error_code)
        Exception.__init__(self, "%s failed with code %s" % (api_name, error_code))


class _SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
    _fields_ = (("Value", ctypes.c_ubyte * 6),)


class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = (
        ("Sid", ctypes.c_void_p),
        ("Attributes", wintypes.DWORD),
    )


class _TOKEN_GROUPS_HEADER(ctypes.Structure):
    _fields_ = (
        ("GroupCount", wintypes.DWORD),
        ("Groups", _SID_AND_ATTRIBUTES * 1),
    )


def _windows_text(value):
    if isinstance(value, text_type):
        return value
    if isinstance(value, str):
        return value.decode("utf-8")
    return text_type(value)


class WindowsAccountBackend(object):
    LOGON32_LOGON_INTERACTIVE = 2
    LOGON32_PROVIDER_DEFAULT = 0
    SECURITY_BUILTIN_DOMAIN_RID = 0x00000020
    DOMAIN_ALIAS_RID_ADMINS = 0x00000220
    SECURITY_IMPERSONATION = 2
    TOKEN_GROUPS = 2

    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.WinDLL("advapi32", use_last_error=True)
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_signatures()

    def _configure_signatures(self):
        self.advapi32.LogonUserW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        )
        self.advapi32.LogonUserW.restype = wintypes.BOOL
        self.advapi32.AllocateAndInitializeSid.argtypes = (
            ctypes.POINTER(_SID_IDENTIFIER_AUTHORITY),
            wintypes.BYTE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
        )
        self.advapi32.AllocateAndInitializeSid.restype = wintypes.BOOL
        self.advapi32.FreeSid.argtypes = (ctypes.c_void_p,)
        self.advapi32.FreeSid.restype = ctypes.c_void_p
        self.advapi32.CheckTokenMembership.argtypes = (
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.BOOL),
        )
        self.advapi32.CheckTokenMembership.restype = wintypes.BOOL
        self.advapi32.DuplicateToken.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.POINTER(wintypes.HANDLE),
        )
        self.advapi32.DuplicateToken.restype = wintypes.BOOL
        self.advapi32.GetTokenInformation.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.advapi32.GetTokenInformation.restype = wintypes.BOOL
        self.advapi32.EqualSid.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        self.advapi32.EqualSid.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def logon_local_user(self, account_name, password):
        token = wintypes.HANDLE()
        ok = self.advapi32.LogonUserW(
            _windows_text(account_name),
            u".",
            _windows_text(password),
            self.LOGON32_LOGON_INTERACTIVE,
            self.LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token),
        )
        if not ok:
            raise WindowsAuthError("LogonUserW", ctypes.get_last_error())
        return token

    def token_is_local_admin(self, token):
        admin_sid = self._allocate_admin_sid()
        try:
            if self._check_membership_with_fallback(token, admin_sid):
                return True
            return self._token_contains_group_sid(token, admin_sid)
        finally:
            self._free_sid(admin_sid)

    def _allocate_admin_sid(self):
        nt_authority = _SID_IDENTIFIER_AUTHORITY((0, 0, 0, 0, 0, 5))
        admin_sid = ctypes.c_void_p()
        ok = self.advapi32.AllocateAndInitializeSid(
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
            raise WindowsAuthError(
                "AllocateAndInitializeSid", ctypes.get_last_error()
            )
        return admin_sid

    def _free_sid(self, sid):
        if sid:
            self.advapi32.FreeSid(sid)

    def _check_membership_with_fallback(self, token, admin_sid):
        try:
            return self._check_token_membership(token, admin_sid)
        except WindowsAuthError as error:
            if (
                error.api_name != "CheckTokenMembership"
                or error.error_code != ERROR_NO_IMPERSONATION_TOKEN
            ):
                raise

        impersonation_token = self._duplicate_for_membership(token)
        try:
            return self._check_token_membership(impersonation_token, admin_sid)
        finally:
            self.close_handle(impersonation_token)

    def _check_token_membership(self, token, admin_sid):
        is_member = wintypes.BOOL()
        ok = self.advapi32.CheckTokenMembership(
            token, admin_sid, ctypes.byref(is_member)
        )
        if not ok:
            raise WindowsAuthError("CheckTokenMembership", ctypes.get_last_error())
        return bool(is_member.value)

    def _duplicate_for_membership(self, token):
        duplicate = wintypes.HANDLE()
        ok = self.advapi32.DuplicateToken(
            token, self.SECURITY_IMPERSONATION, ctypes.byref(duplicate)
        )
        if not ok:
            raise WindowsAuthError("DuplicateToken", ctypes.get_last_error())
        return duplicate

    def _token_contains_group_sid(self, token, expected_sid):
        required_size = wintypes.DWORD(0)
        self.advapi32.GetTokenInformation(
            token,
            self.TOKEN_GROUPS,
            None,
            0,
            ctypes.byref(required_size),
        )
        error_code = ctypes.get_last_error()
        if error_code != ERROR_INSUFFICIENT_BUFFER or not required_size.value:
            raise WindowsAuthError("GetTokenInformation", error_code)

        buffer = ctypes.create_string_buffer(required_size.value)
        ok = self.advapi32.GetTokenInformation(
            token,
            self.TOKEN_GROUPS,
            buffer,
            required_size.value,
            ctypes.byref(required_size),
        )
        if not ok:
            raise WindowsAuthError("GetTokenInformation", ctypes.get_last_error())

        header = ctypes.cast(
            buffer, ctypes.POINTER(_TOKEN_GROUPS_HEADER)
        ).contents
        count = int(header.GroupCount)
        groups_address = ctypes.addressof(buffer) + _TOKEN_GROUPS_HEADER.Groups.offset
        groups = ctypes.cast(
            groups_address, ctypes.POINTER(_SID_AND_ATTRIBUTES * count)
        ).contents
        for index in range(count):
            sid = groups[index].Sid
            if sid and self.advapi32.EqualSid(sid, expected_sid):
                return True
        return False

    def close_handle(self, handle):
        if handle:
            self.kernel32.CloseHandle(handle)

