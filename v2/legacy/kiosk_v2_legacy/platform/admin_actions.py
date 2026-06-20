# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes

from ctypes import wintypes


SW_SHOWNORMAL = 1


class AdminActionLauncher(object):
    def __init__(
        self,
        restore_executable,
        configurator_executable,
        api=None,
    ):
        self.restore_executable = restore_executable
        self.configurator_executable = configurator_executable
        self.api = api or NativeAdminActionApi()

    def run(self):
        return self.api.run_elevated(
            self.restore_executable,
            "restore --apply",
        )

    def change_application(self):
        return self.api.run_elevated(
            self.configurator_executable,
            "configure-application",
        )


class NativeAdminActionApi(object):
    def __init__(self, shell32=None):
        self.shell32 = shell32 or ctypes.windll.shell32
        self.shell32.ShellExecuteW.argtypes = [
            wintypes.HWND,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            ctypes.c_int,
        ]
        self.shell32.ShellExecuteW.restype = wintypes.HINSTANCE

    def run_elevated(self, executable, arguments):
        result = self.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            arguments,
            None,
            SW_SHOWNORMAL,
        )
        value = int(result)
        if value <= 32:
            raise OSError(value, "ShellExecuteW runas failed")
        return True
