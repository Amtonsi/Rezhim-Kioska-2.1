# -*- coding: utf-8 -*-
import ctypes
import os
import re

from ctypes import wintypes


SE_FILE_OBJECT = 1
DACL_SECURITY_INFORMATION = 0x00000004
UNPROTECTED_DACL_SECURITY_INFORMATION = 0x20000000
PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
SE_DACL_PROTECTED = 0x1000
SDDL_REVISION_1 = 1


class PathNotApprovedError(ValueError):
    pass


class AclSnapshot(object):
    def __init__(self, path, existed, sddl=None):
        self.path = os.path.abspath(path)
        self.existed = bool(existed)
        self.sddl = sddl
        if self.existed and not isinstance(sddl, str):
            raise ValueError("existing ACL snapshot requires SDDL")
        if not self.existed and sddl is not None:
            raise ValueError("missing ACL snapshot cannot contain SDDL")

    def to_dict(self):
        return {
            "path": self.path,
            "existed": self.existed,
            "sddl": self.sddl,
        }

    @classmethod
    def from_dict(cls, document):
        if not isinstance(document, dict) or set(document) != {"path", "existed", "sddl"}:
            raise ValueError("invalid ACL snapshot")
        return cls(document["path"], document["existed"], document["sddl"])


def comparable_file_dacl(sddl):
    # NTFS may set AUTO_INHERITED even when applying a protected DACL.
    # Preserve every ACE, its order and the DACL protection flag.
    flags, separator, aces = sddl.partition("(")
    return flags.replace("AI", "") + separator + aces


class FileAclManager(object):
    def __init__(self, approved_roots, native=None):
        roots = tuple(self._normalize(path) for path in approved_roots)
        if not roots:
            raise ValueError("at least one approved ACL root is required")
        self.approved_roots = roots
        self.native = native or NativeFileAclApi()

    def capture(self, path):
        normalized = self._require_approved(path)
        if not os.path.exists(normalized):
            return AclSnapshot(normalized, False)
        return AclSnapshot(normalized, True, self.native.capture_sddl(normalized))

    def protect_for_operator(self, path, operator_sid, execute=False):
        normalized = self._require_approved(path)
        if not os.path.exists(normalized):
            raise OSError("ACL target does not exist")
        if not re.match(r"^S-\d+(?:-\d+)+$", str(operator_sid or "")):
            raise ValueError("valid operator SID is required")
        directory = os.path.isdir(normalized)
        inheritance = "OICI" if directory else ""
        # Use FILE_GENERIC_READ | FILE_GENERIC_EXECUTE to keep inheritable ACEs intact.
        operator_rights = "0x1200a9" if execute else "FR"
        sddl = "D:P(A;{0};FA;;;SY)(A;{0};FA;;;BA)(A;{0};{1};;;{2})".format(
            inheritance,
            operator_rights,
            operator_sid,
        )
        self.native.apply_sddl(normalized, sddl)
        return sddl

    def protect_backup(self, path):
        normalized = self._require_approved(path)
        if not os.path.exists(normalized):
            raise OSError("backup ACL target does not exist")
        sddl = "D:P(A;;FA;;;SY)(A;;FA;;;BA)"
        self.native.apply_sddl(normalized, sddl)
        return sddl

    def restore(self, snapshot):
        normalized = self._require_approved(snapshot.path)
        if not snapshot.existed:
            return
        if not os.path.exists(normalized):
            raise OSError("ACL restore target does not exist")
        self.native.apply_sddl(normalized, snapshot.sddl)

    def verify(self, path, expected_sddl):
        normalized = self._require_approved(path)
        if not os.path.exists(normalized):
            return False
        return comparable_file_dacl(self.native.capture_sddl(normalized)) == comparable_file_dacl(expected_sddl)

    def verify_snapshot(self, snapshot):
        normalized = self._require_approved(snapshot.path)
        if not snapshot.existed:
            return not os.path.exists(normalized)
        if not os.path.exists(normalized):
            return False
        return comparable_file_dacl(self.native.capture_sddl(normalized)) == comparable_file_dacl(snapshot.sddl)

    def _require_approved(self, path):
        normalized = self._normalize(path)
        for root in self.approved_roots:
            try:
                if os.path.commonpath((root, normalized)) == root:
                    return normalized
            except ValueError:
                continue
        raise PathNotApprovedError("path is outside approved ACL roots")

    def _normalize(self, path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class NativeFileAclApi(object):
    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        void_pointer_pointer = ctypes.POINTER(wintypes.LPVOID)
        self.advapi32.GetNamedSecurityInfoW.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            void_pointer_pointer,
            void_pointer_pointer,
            void_pointer_pointer,
            void_pointer_pointer,
            void_pointer_pointer,
        ]
        self.advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            void_pointer_pointer,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
        self.advapi32.GetSecurityDescriptorDacl.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.BOOL),
            void_pointer_pointer,
            ctypes.POINTER(wintypes.BOOL),
        ]
        self.advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
        self.advapi32.GetSecurityDescriptorControl.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.WORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
        self.advapi32.SetNamedSecurityInfoW.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.LPVOID,
        ]
        self.advapi32.SetNamedSecurityInfoW.restype = wintypes.DWORD
        self.kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        self.kernel32.LocalFree.restype = wintypes.HLOCAL
        self.kernel32.GetLastError.argtypes = []
        self.kernel32.GetLastError.restype = wintypes.DWORD

    def capture_sddl(self, path):
        descriptor = wintypes.LPVOID()
        status = int(
            self.advapi32.GetNamedSecurityInfoW(
                path,
                SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION,
                None,
                None,
                None,
                None,
                ctypes.byref(descriptor),
            )
        )
        if status != 0:
            raise OSError(status, "GetNamedSecurityInfoW failed")
        string_descriptor = wintypes.LPWSTR()
        try:
            length = wintypes.DWORD()
            if not self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor,
                SDDL_REVISION_1,
                DACL_SECURITY_INFORMATION,
                ctypes.byref(string_descriptor),
                ctypes.byref(length),
            ):
                self._raise_last_error(
                    "ConvertSecurityDescriptorToStringSecurityDescriptorW"
                )
            return string_descriptor.value
        finally:
            if string_descriptor:
                self.kernel32.LocalFree(string_descriptor)
            if descriptor:
                self.kernel32.LocalFree(descriptor)

    def apply_sddl(self, path, sddl):
        descriptor = wintypes.LPVOID()
        descriptor_size = wintypes.DWORD()
        if not self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            SDDL_REVISION_1,
            ctypes.byref(descriptor),
            ctypes.byref(descriptor_size),
        ):
            self._raise_last_error(
                "ConvertStringSecurityDescriptorToSecurityDescriptorW"
            )
        try:
            dacl_present = wintypes.BOOL()
            dacl_defaulted = wintypes.BOOL()
            dacl = wintypes.LPVOID()
            if not self.advapi32.GetSecurityDescriptorDacl(
                descriptor,
                ctypes.byref(dacl_present),
                ctypes.byref(dacl),
                ctypes.byref(dacl_defaulted),
            ):
                self._raise_last_error("GetSecurityDescriptorDacl")
            control = wintypes.WORD()
            revision = wintypes.DWORD()
            if not self.advapi32.GetSecurityDescriptorControl(
                descriptor,
                ctypes.byref(control),
                ctypes.byref(revision),
            ):
                self._raise_last_error("GetSecurityDescriptorControl")
            information = DACL_SECURITY_INFORMATION
            if int(control.value) & SE_DACL_PROTECTED:
                information |= PROTECTED_DACL_SECURITY_INFORMATION
            else:
                information |= UNPROTECTED_DACL_SECURITY_INFORMATION
            status = int(
                self.advapi32.SetNamedSecurityInfoW(
                    path,
                    SE_FILE_OBJECT,
                    information,
                    None,
                    None,
                    dacl if dacl_present else None,
                    None,
                )
            )
            if status != 0:
                raise OSError(status, "SetNamedSecurityInfoW failed")
        finally:
            if descriptor:
                self.kernel32.LocalFree(descriptor)

    def _raise_last_error(self, api_name):
        code = int(self.kernel32.GetLastError())
        raise OSError(code, "{0} failed".format(api_name))
