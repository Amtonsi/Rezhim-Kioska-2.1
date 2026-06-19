# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes

from ctypes import wintypes


SW_RESTORE = 9
SW_MAXIMIZE = 3
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040


class LegacyWindowApi(object):
    def __init__(self, native=None):
        self.native = native or NativeLegacyWindowApi()

    def windows_for_pid(self, pid):
        expected = int(pid)
        windows = []
        for hwnd in self.native.enumerate_windows():
            if self.native.window_process_id(hwnd) != expected:
                continue
            if not self.native.is_window_visible(hwnd):
                continue
            windows.append(hwnd)
        return windows

    def is_minimized(self, hwnd):
        return bool(self.native.is_iconic(hwnd))

    def restore_window(self, hwnd, maximized=False):
        command = SW_MAXIMIZE if maximized else SW_RESTORE
        self.native.show_window(hwnd, command)
        return True

    def bring_to_front(self, hwnd):
        positioned = bool(self.native.position_at_top(hwnd))
        activated = bool(self.native.set_foreground_window(hwnd))
        return positioned and activated


class NativeLegacyWindowApi(object):
    def __init__(self, user32=None, kernel32=None):
        self.user32 = user32 or ctypes.windll.user32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )
        self._configure_signatures()

    def _configure_signatures(self):
        self.user32.EnumWindows.argtypes = [self._callback_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsIconic.restype = wintypes.BOOL
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindow.restype = wintypes.BOOL
        self.user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        self.user32.SetWindowPos.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL

    def enumerate_windows(self):
        windows = []

        @self._callback_type
        def collect(hwnd, unused):
            windows.append(int(hwnd))
            return True

        if not self.user32.EnumWindows(collect, 0):
            raise self._error("EnumWindows")
        return windows

    def window_process_id(self, hwnd):
        process_id = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        return int(process_id.value)

    def is_window_visible(self, hwnd):
        return bool(self.user32.IsWindowVisible(hwnd))

    def is_iconic(self, hwnd):
        return bool(self.user32.IsIconic(hwnd))

    def show_window(self, hwnd, command):
        self.user32.ShowWindow(hwnd, int(command))
        return True

    def position_at_top(self, hwnd):
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        return bool(self.user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, flags))

    def set_foreground_window(self, hwnd):
        return bool(self.user32.SetForegroundWindow(hwnd))

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(
            code,
            "{0} failed with Windows error {1}".format(api_name, code),
        )
