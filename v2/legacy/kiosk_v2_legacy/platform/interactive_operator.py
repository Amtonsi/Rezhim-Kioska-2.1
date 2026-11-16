# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
from ctypes import wintypes

from .operator_account import ADMINISTRATORS_SID, WindowsOperatorAccountApi


TOKEN_QUERY = 0x0008
TOKEN_USER = 1
TOKEN_GROUPS = 2
ERROR_INSUFFICIENT_BUFFER = 122
WTS_CURRENT_SESSION = 0xFFFFFFFF
WTS_USER_NAME = 5
WTS_DOMAIN_NAME = 7
INTERACTIVE_SID = "S-1-5-4"


class SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", wintypes.LPVOID), ("attributes", wintypes.DWORD)]


class TokenGroupsHeader(ctypes.Structure):
    _fields_ = [("count", wintypes.DWORD), ("first", SidAndAttributes)]


class OperatorLaunchDenied(RuntimeError):
    pass


class InteractiveOperatorGuard(object):
    def __init__(self, accounts=None, token=None):
        self.accounts = accounts or WindowsOperatorAccountApi()
        self.token = token or WindowsSessionIdentity(self.accounts.native)

    def validate(self, username):
        try:
            operator = self.accounts.get_identity(username)
            if operator is None or not operator.enabled:
                raise OperatorLaunchDenied("Локальная учётная запись оператора недоступна.")
            user_sid, group_sids = self.token.process_identity()
            if operator.is_administrator or ADMINISTRATORS_SID in group_sids:
                raise OperatorLaunchDenied("Для киоска требуется оператор без прав администратора.")
            if (operator.sid != user_sid or INTERACTIVE_SID not in group_sids
                    or self.token.session_owner_sid() != user_sid):
                raise OperatorLaunchDenied("Войдите в Windows под настроенной учётной записью оператора.")
        except (OSError, ValueError):
            raise OperatorLaunchDenied("Windows не удалось подтвердить учётную запись оператора.")


class WindowsSessionIdentity(object):
    def __init__(self, native):
        self.native = native
        self.advapi = native.advapi32
        self.kernel = native.kernel32
        self.wts = ctypes.windll.wtsapi32
        self.kernel.GetCurrentProcess.argtypes = []
        self.kernel.GetCurrentProcess.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.advapi.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        self.advapi.OpenProcessToken.restype = wintypes.BOOL
        self.advapi.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)]
        self.advapi.GetTokenInformation.restype = wintypes.BOOL
        self.wts.WTSQuerySessionInformationW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.c_int,
            ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
        self.wts.WTSQuerySessionInformationW.restype = wintypes.BOOL
        self.wts.WTSFreeMemory.argtypes = [wintypes.LPVOID]
        self.wts.WTSFreeMemory.restype = None

    def process_identity(self):
        token = wintypes.HANDLE()
        if not self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)):
            raise ctypes.WinError()
        try:
            user = self._token_info(token, TOKEN_USER)
            user_sid = self._sid_string(SidAndAttributes.from_buffer(user).sid)
            groups = self._token_info(token, TOKEN_GROUPS)
            count = wintypes.DWORD.from_buffer(groups).value
            entries = (SidAndAttributes * count).from_buffer(groups, TokenGroupsHeader.first.offset)
            # Filtered administrator tokens keep Administrators as a deny-only SID.
            return user_sid, set(self._sid_string(entry.sid) for entry in entries)
        finally:
            self.kernel.CloseHandle(token)

    def _token_info(self, token, info_class):
        size = wintypes.DWORD()
        self.advapi.GetTokenInformation(token, info_class, None, 0, ctypes.byref(size))
        if self.kernel.GetLastError() != ERROR_INSUFFICIENT_BUFFER or not size.value:
            raise ctypes.WinError()
        buffer = ctypes.create_string_buffer(size.value)
        if not self.advapi.GetTokenInformation(token, info_class, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError()
        return buffer

    def _sid_string(self, sid):
        value = wintypes.LPWSTR()
        if not self.advapi.ConvertSidToStringSidW(sid, ctypes.byref(value)):
            raise ctypes.WinError()
        try:
            return value.value
        finally:
            self.kernel.LocalFree(value)

    def session_owner_sid(self):
        user = self._session_field(WTS_USER_NAME)
        domain = self._session_field(WTS_DOMAIN_NAME)
        if not user or not domain:
            raise OperatorLaunchDenied("Интерактивный сеанс оператора недоступен.")
        return self.native.account_sid(domain + "\\" + user)

    def _session_field(self, field):
        value = wintypes.LPWSTR()
        size = wintypes.DWORD()
        if not self.wts.WTSQuerySessionInformationW(None, WTS_CURRENT_SESSION, field,
                                                     ctypes.byref(value), ctypes.byref(size)):
            raise ctypes.WinError()
        try:
            return value.value
        finally:
            self.wts.WTSFreeMemory(value)
