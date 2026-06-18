# -*- coding: utf-8 -*-

import ctypes
import os
import re
import subprocess
import time
from ctypes import wintypes

try:
    import _winreg as winreg
except ImportError:
    import winreg

from legacy_kiosk.compat import text_type

from legacy_kiosk.backup_store import (
    LEGACY_BACKUP_SCHEMA_VERSION,
    LEGACY_BUILD_FAMILY,
    LegacyBackupStore,
)


ADMIN_RIGHTS_REQUIRED_MESSAGE = (
    u"Отказано в доступе. Для выполнения действия требуются права "
    u"администратора Windows."
)


class AccessDeniedError(OSError):
    pass


class WindowsOperationError(OSError):
    def __init__(self, operation, error_code):
        self.operation = operation
        self.error_code = int(error_code)
        OSError.__init__(
            self,
            self.error_code,
            "%s failed with code %s" % (operation, error_code),
        )

REG_SZ = 1
REG_DWORD = 4

SHELL_TARGET = {
    "group": "shell",
    "key": r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
    "name": "Shell",
    "type": REG_SZ,
}

POLICY_TARGETS = (
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "name": "DisableTaskMgr",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "name": "DisableRegistryTools",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Policies\Microsoft\Windows\System",
        "name": "DisableCMD",
        "type": REG_DWORD,
        "data": 2,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "name": "NoRun",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "name": "NoControlPanel",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "name": "NoViewContextMenu",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "name": "NoTrayContextMenu",
        "type": REG_DWORD,
        "data": 1,
    },
    {
        "group": "policy",
        "key": r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "name": "NoSetTaskbar",
        "type": REG_DWORD,
        "data": 1,
    },
)

INSTALL_ORDER = (
    "validate_operator",
    "validate_allowed_app",
    "create_backup",
    "protect_files",
    "apply_operator_policies",
    "set_operator_shell",
    "verify_install",
)


ERROR_INSUFFICIENT_BUFFER = 122
NERR_SUCCESS = 0
LG_INCLUDE_INDIRECT = 1
MAX_PREFERRED_LENGTH = 0xFFFFFFFF
SID_TYPE_USER = 1
SE_FILE_OBJECT = 1
SDDL_REVISION_1 = 1
DACL_SECURITY_INFORMATION = 0x00000004
PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
UNPROTECTED_DACL_SECURITY_INFORMATION = 0x20000000


class _LOCALGROUP_USERS_INFO_0(ctypes.Structure):
    _fields_ = (("lgrui0_name", wintypes.LPWSTR),)


def _as_unicode(value):
    if isinstance(value, text_type):
        return value
    if isinstance(value, str):
        return value.decode("utf-8")
    return text_type(value)


class NativeAccountInspectionApi(object):
    def __init__(
        self,
        advapi32=None,
        kernel32=None,
        shell32=None,
        netapi32=None,
        registry=None,
    ):
        self.advapi32 = advapi32 or ctypes.WinDLL("advapi32", use_last_error=True)
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self.shell32 = shell32 or ctypes.WinDLL("shell32", use_last_error=True)
        self.netapi32 = netapi32 or ctypes.WinDLL("netapi32", use_last_error=True)
        self.registry = registry or winreg
        self._configure_signatures()

    def _configure_signatures(self):
        self.shell32.IsUserAnAdmin.argtypes = ()
        self.shell32.IsUserAnAdmin.restype = wintypes.BOOL
        self.kernel32.GetComputerNameW.argtypes = (
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.kernel32.GetComputerNameW.restype = wintypes.BOOL
        self.kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
        self.kernel32.LocalFree.restype = ctypes.c_void_p
        self.advapi32.LookupAccountNameW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        )
        self.advapi32.LookupAccountNameW.restype = wintypes.BOOL
        self.advapi32.ConvertSidToStringSidW.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.LPWSTR),
        )
        self.advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        self.advapi32.ConvertStringSidToSidW.argtypes = (
            wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_void_p),
        )
        self.advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
        self.advapi32.LookupAccountSidW.argtypes = (
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        )
        self.advapi32.LookupAccountSidW.restype = wintypes.BOOL
        self.netapi32.NetUserGetLocalGroups.argtypes = (
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        )
        self.netapi32.NetUserGetLocalGroups.restype = wintypes.DWORD
        self.netapi32.NetApiBufferFree.argtypes = (ctypes.c_void_p,)
        self.netapi32.NetApiBufferFree.restype = wintypes.DWORD

    def is_current_process_admin(self):
        return bool(self.shell32.IsUserAnAdmin())

    def _computer_name(self):
        size = wintypes.DWORD(256)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not self.kernel32.GetComputerNameW(buffer, ctypes.byref(size)):
            raise WindowsOperationError("GetComputerNameW", ctypes.get_last_error())
        return buffer.value

    def resolve_local_account_sid(self, account_name):
        qualified_name = u"%s\\%s" % (
            self._computer_name(),
            _as_unicode(account_name),
        )
        sid_size = wintypes.DWORD(0)
        domain_size = wintypes.DWORD(0)
        sid_type = wintypes.DWORD(0)
        ctypes.set_last_error(0)
        self.advapi32.LookupAccountNameW(
            None,
            qualified_name,
            None,
            ctypes.byref(sid_size),
            None,
            ctypes.byref(domain_size),
            ctypes.byref(sid_type),
        )
        error_code = ctypes.get_last_error()
        if error_code != ERROR_INSUFFICIENT_BUFFER or not sid_size.value:
            raise WindowsOperationError("LookupAccountNameW", error_code)

        sid_buffer = ctypes.create_string_buffer(sid_size.value)
        domain_buffer = ctypes.create_unicode_buffer(max(1, domain_size.value))
        if not self.advapi32.LookupAccountNameW(
            None,
            qualified_name,
            sid_buffer,
            ctypes.byref(sid_size),
            domain_buffer,
            ctypes.byref(domain_size),
            ctypes.byref(sid_type),
        ):
            raise WindowsOperationError("LookupAccountNameW", ctypes.get_last_error())
        if sid_type.value != SID_TYPE_USER:
            raise ValueError(u"Указанное имя не является локальной учётной записью.")

        sid_string = wintypes.LPWSTR()
        if not self.advapi32.ConvertSidToStringSidW(
            sid_buffer, ctypes.byref(sid_string)
        ):
            raise WindowsOperationError(
                "ConvertSidToStringSidW", ctypes.get_last_error()
            )
        try:
            return sid_string.value
        finally:
            self.kernel32.LocalFree(sid_string)

    def profile_path_for_sid(self, sid):
        key_path = (
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\%s" % sid
        )
        try:
            key = self.registry.OpenKey(
                self.registry.HKEY_LOCAL_MACHINE, key_path, 0, self.registry.KEY_READ
            )
        except WindowsError:
            raise ValueError(
                u"Профиль операторской учётной записи не создан. "
                u"Войдите в неё один раз и повторите установку."
            )
        try:
            value, _value_type = self.registry.QueryValueEx(key, "ProfileImagePath")
        finally:
            key.Close()
        return os.path.expandvars(value)

    def _local_admin_group_name(self):
        sid = ctypes.c_void_p()
        if not self.advapi32.ConvertStringSidToSidW(
            u"S-1-5-32-544", ctypes.byref(sid)
        ):
            raise WindowsOperationError(
                "ConvertStringSidToSidW", ctypes.get_last_error()
            )
        try:
            name_size = wintypes.DWORD(0)
            domain_size = wintypes.DWORD(0)
            sid_type = wintypes.DWORD(0)
            ctypes.set_last_error(0)
            self.advapi32.LookupAccountSidW(
                None,
                sid,
                None,
                ctypes.byref(name_size),
                None,
                ctypes.byref(domain_size),
                ctypes.byref(sid_type),
            )
            error_code = ctypes.get_last_error()
            if error_code != ERROR_INSUFFICIENT_BUFFER:
                raise WindowsOperationError("LookupAccountSidW", error_code)
            name = ctypes.create_unicode_buffer(max(1, name_size.value))
            domain = ctypes.create_unicode_buffer(max(1, domain_size.value))
            if not self.advapi32.LookupAccountSidW(
                None,
                sid,
                name,
                ctypes.byref(name_size),
                domain,
                ctypes.byref(domain_size),
                ctypes.byref(sid_type),
            ):
                raise WindowsOperationError(
                    "LookupAccountSidW", ctypes.get_last_error()
                )
            return name.value
        finally:
            self.kernel32.LocalFree(sid)

    def is_user_local_admin(self, account_name):
        buffer = ctypes.c_void_p()
        entries_read = wintypes.DWORD(0)
        total_entries = wintypes.DWORD(0)
        status = self.netapi32.NetUserGetLocalGroups(
            None,
            _as_unicode(account_name),
            0,
            LG_INCLUDE_INDIRECT,
            ctypes.byref(buffer),
            MAX_PREFERRED_LENGTH,
            ctypes.byref(entries_read),
            ctypes.byref(total_entries),
        )
        if status != NERR_SUCCESS:
            raise WindowsOperationError("NetUserGetLocalGroups", status)
        try:
            group_name = self._local_admin_group_name().lower()
            if not entries_read.value:
                return False
            groups = ctypes.cast(
                buffer,
                ctypes.POINTER(_LOCALGROUP_USERS_INFO_0 * entries_read.value),
            ).contents
            return any(
                (groups[index].lgrui0_name or u"").lower() == group_name
                for index in range(entries_read.value)
            )
        finally:
            if buffer:
                self.netapi32.NetApiBufferFree(buffer)


class NativeOperatorRegistryApi(object):
    def __init__(self, registry=None, command_runner=None):
        self.registry = registry or winreg
        self.command_runner = command_runner or self._run_reg_command

    def _run_reg_command(self, command):
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creation_flags,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise WindowsOperationError(" ".join(command), process.returncode)
        return stdout, stderr

    def _key_exists(self, root, path):
        try:
            key = self.registry.OpenKey(root, path, 0, self.registry.KEY_READ)
        except WindowsError:
            return False
        key.Close()
        return True

    def with_operator_hive(self, operator_sid, profile_path, callback):
        loaded_here = False
        root_name = operator_sid
        if not self._key_exists(self.registry.HKEY_USERS, operator_sid):
            ntuser_path = os.path.join(os.path.expandvars(profile_path), "NTUSER.DAT")
            if not os.path.isfile(ntuser_path):
                raise ValueError(u"Не найден файл профиля оператора: %s" % ntuser_path)
            root_name = "RezhimKioska_%s" % re.sub(
                r"[^A-Za-z0-9_]", "_", operator_sid
            )
            self.command_runner(
                ["reg.exe", "load", "HKU\\%s" % root_name, ntuser_path]
            )
            loaded_here = True
        try:
            return callback(root_name)
        finally:
            if loaded_here:
                self.command_runner(["reg.exe", "unload", "HKU\\%s" % root_name])

    def _full_key_path(self, root_name, key_path):
        return "%s\\%s" % (root_name, key_path)

    def read_value(self, root_name, key_path, value_name):
        try:
            key = self.registry.OpenKey(
                self.registry.HKEY_USERS,
                self._full_key_path(root_name, key_path),
                0,
                self.registry.KEY_READ,
            )
        except WindowsError:
            return False, None, None
        try:
            try:
                data, value_type = self.registry.QueryValueEx(key, value_name)
                return True, value_type, data
            except WindowsError:
                return False, None, None
        finally:
            key.Close()

    def write_value(self, root_name, key_path, value_name, value_type, value_data):
        key = self.registry.CreateKey(
            self.registry.HKEY_USERS,
            self._full_key_path(root_name, key_path),
        )
        try:
            self.registry.SetValueEx(key, value_name, 0, value_type, value_data)
        finally:
            key.Close()

    def delete_value(self, root_name, key_path, value_name):
        try:
            key = self.registry.OpenKey(
                self.registry.HKEY_USERS,
                self._full_key_path(root_name, key_path),
                0,
                self.registry.KEY_SET_VALUE,
            )
        except WindowsError:
            return
        try:
            try:
                self.registry.DeleteValue(key, value_name)
            except WindowsError:
                pass
        finally:
            key.Close()


class NativeFileSecurityApi(object):
    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.WinDLL("advapi32", use_last_error=True)
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_signatures()

    def _configure_signatures(self):
        self.advapi32.GetNamedSecurityInfoW.argtypes = (
            wintypes.LPWSTR,
            ctypes.c_int,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        )
        self.advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(wintypes.DWORD),
        )
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.DWORD),
        )
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
        self.advapi32.GetSecurityDescriptorDacl.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.BOOL),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.BOOL),
        )
        self.advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
        self.advapi32.SetNamedSecurityInfoW.argtypes = (
            wintypes.LPWSTR,
            ctypes.c_int,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self.advapi32.SetNamedSecurityInfoW.restype = wintypes.DWORD
        self.kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
        self.kernel32.LocalFree.restype = ctypes.c_void_p

    def get_sddl(self, path):
        security_descriptor = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        result = self.advapi32.GetNamedSecurityInfoW(
            _as_unicode(path),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            None,
            None,
            ctypes.byref(dacl),
            None,
            ctypes.byref(security_descriptor),
        )
        if result != 0:
            raise WindowsOperationError("GetNamedSecurityInfoW", result)
        sddl = wintypes.LPWSTR()
        try:
            if not self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                security_descriptor,
                SDDL_REVISION_1,
                DACL_SECURITY_INFORMATION,
                ctypes.byref(sddl),
                None,
            ):
                raise WindowsOperationError(
                    "ConvertSecurityDescriptorToStringSecurityDescriptorW",
                    ctypes.get_last_error(),
                )
            return sddl.value
        finally:
            if sddl:
                self.kernel32.LocalFree(sddl)
            if security_descriptor:
                self.kernel32.LocalFree(security_descriptor)

    def set_sddl(self, path, sddl):
        security_descriptor = ctypes.c_void_p()
        if not self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            _as_unicode(sddl),
            SDDL_REVISION_1,
            ctypes.byref(security_descriptor),
            None,
        ):
            raise WindowsOperationError(
                "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                ctypes.get_last_error(),
            )
        try:
            dacl_present = wintypes.BOOL()
            dacl_defaulted = wintypes.BOOL()
            dacl = ctypes.c_void_p()
            if not self.advapi32.GetSecurityDescriptorDacl(
                security_descriptor,
                ctypes.byref(dacl_present),
                ctypes.byref(dacl),
                ctypes.byref(dacl_defaulted),
            ):
                raise WindowsOperationError(
                    "GetSecurityDescriptorDacl", ctypes.get_last_error()
                )
            protection_flag = (
                PROTECTED_DACL_SECURITY_INFORMATION
                if "D:P" in sddl
                else UNPROTECTED_DACL_SECURITY_INFORMATION
            )
            result = self.advapi32.SetNamedSecurityInfoW(
                _as_unicode(path),
                SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION | protection_flag,
                None,
                None,
                dacl,
                None,
            )
            if result != 0:
                raise WindowsOperationError("SetNamedSecurityInfoW", result)
        finally:
            if security_descriptor:
                self.kernel32.LocalFree(security_descriptor)


class LegacyInstallContext(object):
    def __init__(
        self,
        config,
        launcher_path,
        config_path,
        backup_path,
        platform_info=None,
    ):
        self.config = config
        self.launcher_path = os.path.abspath(launcher_path)
        self.config_path = os.path.abspath(config_path)
        self.backup_path = os.path.abspath(backup_path)
        self.platform_info = platform_info
        self.operator_sid = None
        self.profile_path = None

    @property
    def operator_user(self):
        return self.config.get("operatorUser", "")

    @property
    def allowed_app_path(self):
        return self.config.get("allowedApplication", {}).get("path", "")

    @property
    def launcher_command(self):
        return u'"%s" --config "%s" launch' % (
            self.launcher_path,
            self.config_path,
        )

    def protected_paths(self):
        paths = [
            os.path.dirname(self.launcher_path),
            self.launcher_path,
            self.config_path,
        ]
        result = []
        for path in paths:
            if path not in result:
                result.append(path)
        return tuple(result)


class WindowsAccountInspector(object):
    def __init__(self, api=None):
        self.api = api or NativeAccountInspectionApi()

    def is_current_process_admin(self):
        return self.api.is_current_process_admin()

    def inspect_local_operator(self, account_name):
        if not account_name:
            raise ValueError(u"Не указана операторская учётная запись.")
        sid = self.api.resolve_local_account_sid(account_name)
        return {
            "account_name": account_name,
            "sid": sid,
            "profile_path": self.api.profile_path_for_sid(sid),
            "is_admin": self.api.is_user_local_admin(account_name),
        }


class WindowsOperatorRegistry(object):
    def __init__(self, api=None):
        self.api = api or NativeOperatorRegistryApi()

    def snapshot_values(self, operator_sid, profile_path, targets):
        def snapshot(root_name):
            records = []
            for target in targets:
                exists, value_type, value_data = self.api.read_value(
                    root_name, target["key"], target["name"]
                )
                records.append(
                    {
                        "group": target["group"],
                        "key": target["key"],
                        "name": target["name"],
                        "exists": bool(exists),
                        "type": value_type,
                        "data": value_data,
                    }
                )
            return records

        return self.api.with_operator_hive(operator_sid, profile_path, snapshot)

    def write_values(self, operator_sid, profile_path, targets):
        def write(root_name):
            for target in targets:
                self.api.write_value(
                    root_name,
                    target["key"],
                    target["name"],
                    target["type"],
                    target["data"],
                )

        return self.api.with_operator_hive(operator_sid, profile_path, write)

    def restore_values(self, operator_sid, profile_path, records):
        def restore(root_name):
            for record in records:
                if record.get("exists"):
                    self.api.write_value(
                        root_name,
                        record["key"],
                        record["name"],
                        record["type"],
                        record.get("data"),
                    )
                else:
                    self.api.delete_value(
                        root_name, record["key"], record["name"]
                    )

        return self.api.with_operator_hive(operator_sid, profile_path, restore)

    def verify_values(self, operator_sid, profile_path, targets):
        def verify(root_name):
            for target in targets:
                exists, value_type, value_data = self.api.read_value(
                    root_name, target["key"], target["name"]
                )
                if not exists:
                    return False
                if int(value_type) != int(target["type"]):
                    return False
                if value_data != target["data"]:
                    return False
            return True

        return self.api.with_operator_hive(operator_sid, profile_path, verify)


class WindowsFileSecurity(object):
    def __init__(self, api=None):
        self.api = api or NativeFileSecurityApi()

    def snapshot_paths(self, paths):
        return [
            {"path": path, "sddl": self.api.get_sddl(path)} for path in paths
        ]

    def protect_paths(self, paths, operator_sid):
        for path in paths:
            inheritance = "OICI" if os.path.isdir(path) else ""
            sddl = (
                "D:P(A;%s;FA;;;SY)(A;%s;FA;;;BA)(A;%s;GRGX;;;%s)"
                % (inheritance, inheritance, inheritance, operator_sid)
            )
            self.api.set_sddl(path, sddl)

    def restore_paths(self, records):
        for record in records:
            self.api.set_sddl(record["path"], record["sddl"])


class LegacyTransaction(object):
    def __init__(self, backend):
        self.backend = backend

    def apply(self, context):
        completed = []
        try:
            for operation_name in INSTALL_ORDER:
                completed.append(operation_name)
                getattr(self.backend, operation_name)(context)
        except Exception:
            for operation_name in reversed(completed):
                self.backend.rollback(operation_name, context)
            raise


class LegacySystemBackend(object):
    def __init__(
        self,
        account_inspector,
        registry_adapter,
        security_adapter,
        backup_store=None,
        logger=None,
    ):
        self.account_inspector = account_inspector
        self.registry_adapter = registry_adapter
        self.security_adapter = security_adapter
        self.backup_store = backup_store or LegacyBackupStore()
        self.logger = logger

    def validate_operator(self, context):
        if not self.account_inspector.is_current_process_admin():
            raise AccessDeniedError(ADMIN_RIGHTS_REQUIRED_MESSAGE)
        operator = self.account_inspector.inspect_local_operator(context.operator_user)
        if operator.get("is_admin"):
            raise ValueError(
                u"Операторская учётная запись не должна иметь права администратора."
            )
        context.operator_sid = operator["sid"]
        context.profile_path = operator["profile_path"]

    def validate_allowed_app(self, context):
        if not context.allowed_app_path or not os.path.isfile(context.allowed_app_path):
            raise ValueError(
                u"Разрешённое приложение не найдено: %s" % context.allowed_app_path
            )
        if os.path.splitext(context.allowed_app_path)[1].lower() != ".exe":
            raise ValueError(u"Разрешённое приложение должно быть EXE-файлом.")
        if not os.path.isfile(context.launcher_path):
            raise ValueError(u"Legacy-загрузчик не найден: %s" % context.launcher_path)
        if not os.path.isfile(context.config_path):
            raise ValueError(u"Файл конфигурации не найден: %s" % context.config_path)

    def create_backup(self, context):
        registry_targets = list(POLICY_TARGETS) + [SHELL_TARGET]
        registry_records = self.registry_adapter.snapshot_values(
            context.operator_sid, context.profile_path, registry_targets
        )
        security_records = self.security_adapter.snapshot_paths(
            context.protected_paths()
        )
        platform = context.platform_info
        os_data = None
        if platform is not None:
            os_data = {
                "major": platform.major,
                "minor": platform.minor,
                "build": platform.build,
                "servicePackMajor": platform.service_pack_major,
                "productType": platform.product_type,
                "architecture": platform.architecture,
            }
        self.backup_store.save(
            context.backup_path,
            {
                "schemaVersion": LEGACY_BACKUP_SCHEMA_VERSION,
                "buildFamily": LEGACY_BUILD_FAMILY,
                "createdUnixTime": int(time.time()),
                "operatorSid": context.operator_sid,
                "operatorUser": context.operator_user,
                "os": os_data,
                "registry": registry_records,
                "security": security_records,
            },
        )

    def protect_files(self, context):
        self.security_adapter.protect_paths(
            context.protected_paths(), context.operator_sid
        )

    def apply_operator_policies(self, context):
        self.registry_adapter.write_values(
            context.operator_sid, context.profile_path, POLICY_TARGETS
        )

    def set_operator_shell(self, context):
        shell_target = dict(SHELL_TARGET)
        shell_target["data"] = context.launcher_command
        self.registry_adapter.write_values(
            context.operator_sid, context.profile_path, (shell_target,)
        )

    def verify_install(self, context):
        shell_target = dict(SHELL_TARGET)
        shell_target["data"] = context.launcher_command
        targets = list(POLICY_TARGETS) + [shell_target]
        if not self.registry_adapter.verify_values(
            context.operator_sid, context.profile_path, targets
        ):
            raise RuntimeError(u"Проверка установленных политик завершилась ошибкой.")

    def rollback(self, operation_name, context):
        if operation_name not in (
            "protect_files",
            "apply_operator_policies",
            "set_operator_shell",
        ):
            return
        payload = self.backup_store.load_for_operator(
            context.backup_path, context.operator_sid
        )
        if operation_name == "protect_files":
            self.security_adapter.restore_paths(payload["security"])
            return
        group = "shell" if operation_name == "set_operator_shell" else "policy"
        records = [
            record for record in payload["registry"] if record.get("group") == group
        ]
        self.registry_adapter.restore_values(
            context.operator_sid, context.profile_path, records
        )

    def restore(self, context):
        self.validate_operator(context)
        payload = self.backup_store.load_for_operator(
            context.backup_path, context.operator_sid
        )
        self.registry_adapter.restore_values(
            context.operator_sid, context.profile_path, payload["registry"]
        )
        self.security_adapter.restore_paths(payload["security"])


def create_windows_system_backend(backup_store=None, logger=None):
    return LegacySystemBackend(
        account_inspector=WindowsAccountInspector(),
        registry_adapter=WindowsOperatorRegistry(),
        security_adapter=WindowsFileSecurity(),
        backup_store=backup_store or LegacyBackupStore(),
        logger=logger,
    )
