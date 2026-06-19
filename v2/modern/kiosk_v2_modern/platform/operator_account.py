# -*- coding: utf-8 -*-
import ctypes

from ctypes import wintypes


ADMINISTRATORS_SID = "S-1-5-32-544"
NERR_SUCCESS = 0
NERR_USER_NOT_FOUND = 2221
UF_ACCOUNTDISABLE = 0x0002
LG_INCLUDE_INDIRECT = 0x0001
MAX_PREFERRED_LENGTH = 0xFFFFFFFF
ERROR_INSUFFICIENT_BUFFER = 122


class USER_INFO_1(ctypes.Structure):
    _fields_ = [
        ("usri1_name", wintypes.LPWSTR),
        ("usri1_password", wintypes.LPWSTR),
        ("usri1_password_age", wintypes.DWORD),
        ("usri1_priv", wintypes.DWORD),
        ("usri1_home_dir", wintypes.LPWSTR),
        ("usri1_comment", wintypes.LPWSTR),
        ("usri1_flags", wintypes.DWORD),
        ("usri1_script_path", wintypes.LPWSTR),
    ]


class LOCALGROUP_USERS_INFO_0(ctypes.Structure):
    _fields_ = [("lgrui0_name", wintypes.LPWSTR)]


class OperatorIdentity(object):
    def __init__(self, username, sid, enabled, is_administrator):
        self.username = username
        self.sid = sid
        self.enabled = bool(enabled)
        self.is_administrator = bool(is_administrator)


class PreflightError(RuntimeError):
    def __init__(self, code):
        RuntimeError.__init__(self, code)
        self.code = code


class OperatorPreflight(object):
    def __init__(self, account_api=None):
        self.account_api = account_api or WindowsOperatorAccountApi()

    def validate(self, username):
        username = str(username or "").strip()
        if not username or any(marker in username for marker in ("\\", "/", "@")):
            raise PreflightError("local_operator_required")
        if not self.account_api.is_elevated():
            raise PreflightError("elevation_required")
        try:
            identity = self.account_api.get_identity(username)
        except (OSError, RuntimeError):
            raise PreflightError("operator_lookup_failed")
        if identity is None:
            raise PreflightError("operator_not_found")
        if not identity.enabled:
            raise PreflightError("operator_disabled")
        if identity.is_administrator:
            raise PreflightError("operator_is_administrator")
        return identity


class WindowsOperatorAccountApi(object):
    def __init__(self, native=None):
        self.native = native or NativeOperatorAccountApi()

    def is_elevated(self):
        return bool(self.native.is_elevated())

    def get_identity(self, username):
        info = self.native.local_user_info(username)
        if info is None:
            return None
        sid = self.native.account_sid(info["name"])
        group_sids = set()
        for group_name in self.native.local_group_names(info["name"]):
            group_sids.add(self.native.account_sid(group_name))
        return OperatorIdentity(
            info["name"],
            sid,
            info["enabled"],
            ADMINISTRATORS_SID in group_sids,
        )


class NativeOperatorAccountApi(object):
    def __init__(
        self,
        netapi32=None,
        advapi32=None,
        shell32=None,
        kernel32=None,
    ):
        self.netapi32 = netapi32 or ctypes.windll.netapi32
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.shell32 = shell32 or ctypes.windll.shell32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        byte_pointer = ctypes.POINTER(wintypes.BYTE)
        self.shell32.IsUserAnAdmin.argtypes = []
        self.shell32.IsUserAnAdmin.restype = wintypes.BOOL
        self.netapi32.NetUserGetInfo.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(byte_pointer),
        ]
        self.netapi32.NetUserGetInfo.restype = wintypes.DWORD
        self.netapi32.NetUserGetLocalGroups.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(byte_pointer),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.netapi32.NetUserGetLocalGroups.restype = wintypes.DWORD
        self.netapi32.NetApiBufferFree.argtypes = [wintypes.LPVOID]
        self.netapi32.NetApiBufferFree.restype = wintypes.DWORD
        self.advapi32.LookupAccountNameW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.LookupAccountNameW.restype = wintypes.BOOL
        self.advapi32.ConvertSidToStringSidW.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        self.advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        self.kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        self.kernel32.LocalFree.restype = wintypes.HLOCAL
        self.kernel32.GetLastError.argtypes = []
        self.kernel32.GetLastError.restype = wintypes.DWORD

    def is_elevated(self):
        return bool(self.shell32.IsUserAnAdmin())

    def local_user_info(self, username):
        buffer = ctypes.POINTER(wintypes.BYTE)()
        status = int(
            self.netapi32.NetUserGetInfo(None, username, 1, ctypes.byref(buffer))
        )
        if status == NERR_USER_NOT_FOUND:
            return None
        if status != NERR_SUCCESS:
            raise OSError(status, "NetUserGetInfo failed")
        try:
            info = ctypes.cast(buffer, ctypes.POINTER(USER_INFO_1)).contents
            return {
                "name": info.usri1_name or username,
                "enabled": not bool(int(info.usri1_flags) & UF_ACCOUNTDISABLE),
            }
        finally:
            self.netapi32.NetApiBufferFree(buffer)

    def local_group_names(self, username):
        buffer = ctypes.POINTER(wintypes.BYTE)()
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
            raise OSError(status, "NetUserGetLocalGroups failed")
        try:
            if not buffer or not entries_read.value:
                return []
            records = ctypes.cast(
                buffer,
                ctypes.POINTER(LOCALGROUP_USERS_INFO_0),
            )
            return [
                records[index].lgrui0_name
                for index in range(int(entries_read.value))
                if records[index].lgrui0_name
            ]
        finally:
            if buffer:
                self.netapi32.NetApiBufferFree(buffer)

    def account_sid(self, account_name):
        sid_size = wintypes.DWORD()
        domain_size = wintypes.DWORD()
        sid_use = wintypes.DWORD()
        self.advapi32.LookupAccountNameW(
            None,
            account_name,
            None,
            ctypes.byref(sid_size),
            None,
            ctypes.byref(domain_size),
            ctypes.byref(sid_use),
        )
        error = int(self.kernel32.GetLastError())
        if not sid_size.value or error != ERROR_INSUFFICIENT_BUFFER:
            raise OSError(error, "LookupAccountNameW sizing failed")

        sid_buffer = ctypes.create_string_buffer(int(sid_size.value))
        domain_buffer = ctypes.create_unicode_buffer(max(1, int(domain_size.value)))
        if not self.advapi32.LookupAccountNameW(
            None,
            account_name,
            sid_buffer,
            ctypes.byref(sid_size),
            domain_buffer,
            ctypes.byref(domain_size),
            ctypes.byref(sid_use),
        ):
            error = int(self.kernel32.GetLastError())
            raise OSError(error, "LookupAccountNameW failed")

        string_sid = wintypes.LPWSTR()
        if not self.advapi32.ConvertSidToStringSidW(
            sid_buffer,
            ctypes.byref(string_sid),
        ):
            error = int(self.kernel32.GetLastError())
            raise OSError(error, "ConvertSidToStringSidW failed")
        try:
            return string_sid.value
        finally:
            self.kernel32.LocalFree(string_sid)
