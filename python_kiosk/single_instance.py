# -*- coding: utf-8 -*-

import hashlib
import os


class SingleInstanceGuard(object):
    ERROR_ALREADY_EXISTS = 183

    def __init__(self, name):
        self.name = self._safe_name(name)
        self.handle = None
        self.acquired = False

    @classmethod
    def for_config(cls, config_path):
        normalized = os.path.normcase(os.path.abspath(config_path or "default"))
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
        return cls("Local\\PythonKiosk-{0}".format(digest))

    @classmethod
    def for_operator(cls, operator_user):
        normalized = str(operator_user or "default").strip().lower() or "default"
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
        return cls("Local\\PythonKiosk-Operator-{0}".format(digest))

    def acquire(self):
        if os.name != "nt":
            self.acquired = True
            return True
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateMutexW(None, True, self.name)
        if not handle:
            self.acquired = False
            return False
        self.handle = handle
        if kernel32.GetLastError() == self.ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            self.handle = None
            self.acquired = False
            return False
        self.acquired = True
        return True

    def release(self):
        if os.name != "nt":
            self.acquired = False
            return
        if not self.handle:
            self.acquired = False
            return
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if self.acquired:
            kernel32.ReleaseMutex(self.handle)
        kernel32.CloseHandle(self.handle)
        self.handle = None
        self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    @staticmethod
    def _safe_name(name):
        return str(name or "Local\\PythonKiosk").replace("/", "_")
