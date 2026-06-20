# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import os
import re

from ctypes import wintypes


try:
    text_type = unicode
except NameError:
    text_type = str


SE_FILE_OBJECT = 1
DACL_SECURITY_INFORMATION = 0x00000004
UNPROTECTED_DACL_SECURITY_INFORMATION = 0x20000000
PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
SE_DACL_PROTECTED = 0x1000
SDDL_REVISION_1 = 1


class PathNotApprovedError(ValueError):
    pass


class AclSnapshot(object):
    __slots__ = ("path", "existed", "sddl")

    def __init__(self, path, existed, sddl=None):
        self.path = os.path.abspath(path)
        self.existed = bool(existed)
        self.sddl = sddl
        if self.existed and not isinstance(sddl, text_type):
            raise ValueError("existing ACL requires SDDL")
        if not self.existed and sddl is not None:
            raise ValueError("missing ACL cannot contain SDDL")

    def to_dict(self):
        return {"path": self.path, "existed": self.existed, "sddl": self.sddl}

    @classmethod
    def from_dict(cls, document):
        if not isinstance(document, dict) or set(document) != set(("path", "existed", "sddl")):
            raise ValueError("invalid ACL snapshot")
        return cls(document["path"], document["existed"], document["sddl"])


class FileAclManager(object):
    def __init__(self, approved_roots, native=None):
        self.approved_roots = tuple(self._normalize(path) for path in approved_roots)
        if not self.approved_roots:
            raise ValueError("approved roots required")
        self.native = native or NativeFileAclApi()

    def capture(self, path):
        path = self._approved(path)
        if not os.path.exists(path):
            return AclSnapshot(path, False)
        return AclSnapshot(path, True, self.native.capture_sddl(path))

    def protect_for_operator(self, path, operator_sid, execute=False):
        path = self._approved(path)
        if not os.path.exists(path):
            raise OSError("ACL target missing")
        if not re.match(r"^S-\d+(?:-\d+)+$", operator_sid or ""):
            raise ValueError("valid operator SID required")
        flags = "OICI" if os.path.isdir(path) else ""
        rights = "GRGX" if execute else "GR"
        sddl = "D:P(A;{0};FA;;;SY)(A;{0};FA;;;BA)(A;{0};{1};;;{2})".format(
            flags, rights, operator_sid
        )
        self.native.apply_sddl(path, sddl)
        return sddl

    def protect_backup(self, path):
        path = self._approved(path)
        sddl = "D:P(A;;FA;;;SY)(A;;FA;;;BA)"
        self.native.apply_sddl(path, sddl)
        return sddl

    def restore(self, snapshot):
        path = self._approved(snapshot.path)
        if snapshot.existed:
            self.native.apply_sddl(path, snapshot.sddl)

    def verify(self, path, sddl):
        path = self._approved(path)
        return os.path.exists(path) and self.native.capture_sddl(path) == sddl

    def verify_snapshot(self, snapshot):
        path = self._approved(snapshot.path)
        if not snapshot.existed:
            return not os.path.exists(path)
        return os.path.exists(path) and self.native.capture_sddl(path) == snapshot.sddl

    def _approved(self, path):
        path = self._normalize(path)
        for root in self.approved_roots:
            prefix = root.rstrip("\\/") + os.sep
            if path == root or path.startswith(prefix):
                return path
        raise PathNotApprovedError("path outside approved roots")

    @staticmethod
    def _normalize(path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))


class NativeFileAclApi(object):
    def __init__(self, advapi32=None, kernel32=None):
        self.advapi32 = advapi32 or ctypes.windll.advapi32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure()

    def _configure(self):
        ppvoid = ctypes.POINTER(wintypes.LPVOID)
        self.advapi32.GetNamedSecurityInfoW.argtypes = [
            wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
            ppvoid, ppvoid, ppvoid, ppvoid, ppvoid
        ]
        self.advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)
        ]
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, ppvoid, ctypes.POINTER(wintypes.DWORD)
        ]
        self.advapi32.GetSecurityDescriptorDacl.argtypes = [
            wintypes.LPVOID, ctypes.POINTER(wintypes.BOOL), ppvoid,
            ctypes.POINTER(wintypes.BOOL)
        ]
        self.advapi32.GetSecurityDescriptorControl.argtypes = [
            wintypes.LPVOID, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)
        ]
        self.advapi32.SetNamedSecurityInfoW.argtypes = [
            wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID
        ]
        self.advapi32.SetNamedSecurityInfoW.restype = wintypes.DWORD
        self.kernel32.LocalFree.argtypes = [wintypes.HLOCAL]

    def capture_sddl(self, path):
        descriptor = wintypes.LPVOID()
        status = int(self.advapi32.GetNamedSecurityInfoW(
            path, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
            None, None, None, None, ctypes.byref(descriptor)
        ))
        if status:
            raise OSError(status, "GetNamedSecurityInfoW failed")
        text = wintypes.LPWSTR()
        try:
            length = wintypes.DWORD()
            if not self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, SDDL_REVISION_1, DACL_SECURITY_INFORMATION,
                ctypes.byref(text), ctypes.byref(length)
            ):
                raise OSError(int(self.kernel32.GetLastError()), "SDDL conversion failed")
            return text.value
        finally:
            if text:
                self.kernel32.LocalFree(text)
            if descriptor:
                self.kernel32.LocalFree(descriptor)

    def apply_sddl(self, path, sddl):
        descriptor = wintypes.LPVOID()
        size = wintypes.DWORD()
        if not self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, SDDL_REVISION_1, ctypes.byref(descriptor), ctypes.byref(size)
        ):
            raise OSError(int(self.kernel32.GetLastError()), "SDDL parse failed")
        try:
            present = wintypes.BOOL()
            defaulted = wintypes.BOOL()
            dacl = wintypes.LPVOID()
            if not self.advapi32.GetSecurityDescriptorDacl(
                descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)
            ):
                raise OSError(int(self.kernel32.GetLastError()), "DACL read failed")
            control = wintypes.WORD()
            revision = wintypes.DWORD()
            if not self.advapi32.GetSecurityDescriptorControl(
                descriptor, ctypes.byref(control), ctypes.byref(revision)
            ):
                raise OSError(int(self.kernel32.GetLastError()), "control read failed")
            information = DACL_SECURITY_INFORMATION
            if int(control.value) & SE_DACL_PROTECTED:
                information |= PROTECTED_DACL_SECURITY_INFORMATION
            else:
                information |= UNPROTECTED_DACL_SECURITY_INFORMATION
            status = int(self.advapi32.SetNamedSecurityInfoW(
                path, SE_FILE_OBJECT, information, None, None,
                dacl if present else None, None
            ))
            if status:
                raise OSError(status, "SetNamedSecurityInfoW failed")
        finally:
            if descriptor:
                self.kernel32.LocalFree(descriptor)
