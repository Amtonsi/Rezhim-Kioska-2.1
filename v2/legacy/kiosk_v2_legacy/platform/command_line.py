# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes

from ctypes import wintypes


class WindowsArgumentParser(object):
    def __init__(self, native=None):
        self.native = native or NativeWindowsArgumentApi()

    def parse(self, arguments):
        value = arguments or ""
        if not value.strip():
            return ()
        return tuple(self.native.parse(value.strip()))


class NativeWindowsArgumentApi(object):
    def __init__(self, shell32=None, kernel32=None):
        self.shell32 = shell32 or ctypes.windll.shell32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        self.shell32.CommandLineToArgvW.argtypes = [
            wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_int),
        ]
        self.shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
        self.kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        self.kernel32.LocalFree.restype = wintypes.HLOCAL

    def parse(self, arguments):
        count = ctypes.c_int()
        argv = self.shell32.CommandLineToArgvW(arguments, ctypes.byref(count))
        if not argv:
            code = int(self.kernel32.GetLastError())
            raise OSError(
                code,
                "CommandLineToArgvW failed with Windows error {0}".format(code),
            )
        try:
            return [argv[index] for index in range(count.value)]
        finally:
            self.kernel32.LocalFree(argv)
