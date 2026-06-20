# -*- coding: utf-8 -*-
import base64
import ctypes
import os
import re
import winreg

from ctypes import wintypes


REG_SZ = 1
REG_BINARY = 3
REG_DWORD = 4
REG_MULTI_SZ = 7
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
ERROR_NOT_ALL_ASSIGNED = 1300

OPERATOR_POLICY_VALUES = (
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "DisableTaskMgr", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "DisableRegistryTools", REG_DWORD, 1),
    (r"Software\Policies\Microsoft\Windows\System", "DisableCMD", REG_DWORD, 2),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoRun", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoControlPanel", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoViewContextMenu", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoTrayContextMenu", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoSetTaskbar", REG_DWORD, 1),
    (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoWinKeys", REG_DWORD, 1),
)


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1),
    ]


class RegistryValueSnapshot(object):
    def __init__(
        self,
        key_path,
        value_name,
        existed,
        value_type=None,
        value_data=None,
    ):
        self.key_path = str(key_path)
        self.value_name = str(value_name)
        self.existed = bool(existed)
        self.value_type = int(value_type) if value_type is not None else None
        self.value_data = value_data
        if self.existed and self.value_type is None:
            raise ValueError("present registry value requires a type")
        if not self.existed and (value_type is not None or value_data is not None):
            raise ValueError("absent registry value cannot contain data")

    def to_dict(self):
        return {
            "keyPath": self.key_path,
            "valueName": self.value_name,
            "existed": self.existed,
            "valueType": self.value_type,
            "valueData": _encode_registry_data(self.value_data),
        }

    @classmethod
    def from_dict(cls, document):
        expected = {"keyPath", "valueName", "existed", "valueType", "valueData"}
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError("invalid registry snapshot")
        return cls(
            document["keyPath"],
            document["valueName"],
            document["existed"],
            document["valueType"],
            _decode_registry_data(document["valueData"]),
        )


class OperatorRegistryStore(object):
    def __init__(self, operator_sid, profile_path, api=None):
        operator_sid = str(operator_sid or "").strip()
        if not operator_sid.startswith("S-1-"):
            raise ValueError("valid operator SID is required")
        self.operator_sid = operator_sid
        self.profile_path = os.path.abspath(profile_path)
        self.api = api or WindowsRegistryApi()

    def capture(self, key_path, value_name):
        root = self.api.mount_operator_hive(self.operator_sid, self.profile_path)
        try:
            current = self.api.read_value(root, key_path, value_name)
            if current is None:
                return RegistryValueSnapshot(key_path, value_name, False)
            return RegistryValueSnapshot(
                key_path,
                value_name,
                True,
                current[0],
                current[1],
            )
        finally:
            self.api.unmount_operator_hive(root)

    def apply(self, key_path, value_name, value_type, value_data):
        root = self.api.mount_operator_hive(self.operator_sid, self.profile_path)
        try:
            self.api.write_value(
                root,
                key_path,
                value_name,
                int(value_type),
                value_data,
            )
        finally:
            self.api.unmount_operator_hive(root)

    def restore(self, snapshot):
        root = self.api.mount_operator_hive(self.operator_sid, self.profile_path)
        try:
            if snapshot.existed:
                self.api.write_value(
                    root,
                    snapshot.key_path,
                    snapshot.value_name,
                    snapshot.value_type,
                    snapshot.value_data,
                )
            else:
                self.api.delete_value(root, snapshot.key_path, snapshot.value_name)
        finally:
            self.api.unmount_operator_hive(root)

    def verify(self, key_path, value_name, value_type, value_data):
        root = self.api.mount_operator_hive(self.operator_sid, self.profile_path)
        try:
            return self.api.read_value(root, key_path, value_name) == (
                int(value_type),
                value_data,
            )
        finally:
            self.api.unmount_operator_hive(root)

    def verify_snapshot(self, snapshot):
        root = self.api.mount_operator_hive(self.operator_sid, self.profile_path)
        try:
            current = self.api.read_value(root, snapshot.key_path, snapshot.value_name)
            if not snapshot.existed:
                return current is None
            return current == (snapshot.value_type, snapshot.value_data)
        finally:
            self.api.unmount_operator_hive(root)


class WindowsRegistryApi(object):
    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._loaded_roots = set()
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.GetCurrentProcess.argtypes = []
        self.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        self.kernel32.GetLastError.argtypes = []
        self.kernel32.GetLastError.restype = wintypes.DWORD
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        self.advapi32.OpenProcessToken.restype = wintypes.BOOL
        self.advapi32.LookupPrivilegeValueW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            ctypes.POINTER(LUID),
        ]
        self.advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
        self.advapi32.AdjustTokenPrivileges.argtypes = [
            wintypes.HANDLE,
            wintypes.BOOL,
            ctypes.POINTER(TOKEN_PRIVILEGES),
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.LPVOID,
        ]
        self.advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL

    def mount_operator_hive(self, sid, profile_path):
        if self._key_exists(sid):
            return sid
        ntuser_path = os.path.join(profile_path, "NTUSER.DAT")
        if not os.path.isfile(ntuser_path):
            raise OSError("operator profile hive does not exist")
        self._enable_privilege("SeBackupPrivilege")
        self._enable_privilege("SeRestorePrivilege")
        root = "KioskV2_{0}".format(re.sub(r"[^A-Za-z0-9_]", "_", sid))
        winreg.LoadKey(winreg.HKEY_USERS, root, ntuser_path)
        self._loaded_roots.add(root)
        return root

    def unmount_operator_hive(self, root):
        if root not in self._loaded_roots:
            return
        try:
            winreg.UnloadKey(winreg.HKEY_USERS, root)
        finally:
            self._loaded_roots.discard(root)

    def read_value(self, root, key_path, value_name):
        full_path = root + "\\" + key_path
        try:
            with winreg.OpenKey(winreg.HKEY_USERS, full_path, 0, winreg.KEY_READ) as key:
                value_data, value_type = winreg.QueryValueEx(key, value_name)
                return value_type, value_data
        except FileNotFoundError:
            return None

    def write_value(self, root, key_path, value_name, value_type, value_data):
        full_path = root + "\\" + key_path
        with winreg.CreateKeyEx(
            winreg.HKEY_USERS,
            full_path,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        ) as key:
            winreg.SetValueEx(key, value_name, 0, int(value_type), value_data)
            winreg.FlushKey(key)

    def delete_value(self, root, key_path, value_name):
        full_path = root + "\\" + key_path
        try:
            with winreg.OpenKey(
                winreg.HKEY_USERS,
                full_path,
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                try:
                    winreg.DeleteValue(key, value_name)
                except FileNotFoundError:
                    return
                winreg.FlushKey(key)
        except FileNotFoundError:
            return

    def _key_exists(self, path):
        try:
            with winreg.OpenKey(winreg.HKEY_USERS, path, 0, winreg.KEY_READ):
                return True
        except FileNotFoundError:
            return False

    def _enable_privilege(self, privilege_name):
        token = wintypes.HANDLE()
        access = TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY
        if not self.advapi32.OpenProcessToken(
            self.kernel32.GetCurrentProcess(),
            access,
            ctypes.byref(token),
        ):
            self._raise_last_error("OpenProcessToken")
        try:
            luid = LUID()
            if not self.advapi32.LookupPrivilegeValueW(
                None,
                privilege_name,
                ctypes.byref(luid),
            ):
                self._raise_last_error("LookupPrivilegeValueW")
            privileges = TOKEN_PRIVILEGES()
            privileges.PrivilegeCount = 1
            privileges.Privileges[0].Luid = luid
            privileges.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
            if not self.advapi32.AdjustTokenPrivileges(
                token,
                False,
                ctypes.byref(privileges),
                0,
                None,
                None,
            ):
                self._raise_last_error("AdjustTokenPrivileges")
            if int(self.kernel32.GetLastError()) == ERROR_NOT_ALL_ASSIGNED:
                raise OSError(ERROR_NOT_ALL_ASSIGNED, "privilege not assigned")
        finally:
            self.kernel32.CloseHandle(token)

    def _raise_last_error(self, api_name):
        code = int(self.kernel32.GetLastError())
        raise OSError(code, "{0} failed".format(api_name))


def _encode_registry_data(value):
    if isinstance(value, bytes):
        return {
            "encoding": "base64",
            "data": base64.b64encode(value).decode("ascii"),
        }
    return value


def _decode_registry_data(value):
    if isinstance(value, dict):
        if set(value) != {"encoding", "data"} or value["encoding"] != "base64":
            raise ValueError("invalid encoded registry value")
        return base64.b64decode(value["data"].encode("ascii"), validate=True)
    return value
