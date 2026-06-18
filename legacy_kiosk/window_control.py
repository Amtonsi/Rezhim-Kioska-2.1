# -*- coding: utf-8 -*-

import ctypes
import time
from ctypes import wintypes


class LegacyWindowController(object):
    def __init__(self, process_backend, window_api=None, clock=None, sleeper=None):
        self.process_backend = process_backend
        self.window_api = window_api or NativeWindowApi()
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep

    def _windows(self, executable_path):
        process_ids = self.process_backend.find_process_ids(executable_path)
        if not process_ids:
            return []
        return self.window_api.visible_windows_for_pids(process_ids)

    def is_minimized(self, executable_path):
        return any(
            self.window_api.is_iconic(hwnd)
            for hwnd, _process_id in self._windows(executable_path)
        )

    def bring_to_front(self, executable_path):
        windows = self._windows(executable_path)
        if not windows:
            return False
        self.window_api.bring_to_front(windows[0][0])
        return True

    def restore(self, executable_path):
        windows = self._windows(executable_path)
        if not windows:
            return False
        hwnd = windows[0][0]
        if self.window_api.is_iconic(hwnd):
            self.window_api.restore(hwnd)
        self.window_api.bring_to_front(hwnd)
        return True

    def maximize(self, executable_path):
        windows = self._windows(executable_path)
        if not windows:
            return False
        hwnd = windows[0][0]
        self.window_api.maximize(hwnd)
        self.window_api.bring_to_front(hwnd)
        return True

    def wait_and_bring_to_front(
        self, executable_path, timeout_seconds=5, start_maximized=False
    ):
        deadline = float(self.clock()) + float(timeout_seconds)
        while float(self.clock()) <= deadline:
            windows = self._windows(executable_path)
            if windows:
                hwnd = windows[0][0]
                if start_maximized:
                    self.window_api.maximize(hwnd)
                self.window_api.bring_to_front(hwnd)
                return True
            self.sleeper(0.1)
        return False


class NativeWindowApi(object):
    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, user32=None, kernel32=None):
        self.user32 = user32 or ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self.enum_proc_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        self._configure_signatures()

    def _configure_signatures(self):
        self.user32.EnumWindows.argtypes = (self.enum_proc_type, wintypes.LPARAM)
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = (wintypes.HWND,)
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.IsIconic.argtypes = (wintypes.HWND,)
        self.user32.IsIconic.restype = wintypes.BOOL
        self.user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
        self.user32.ShowWindow.restype = wintypes.BOOL
        self.user32.SetWindowPos.argtypes = (
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        )
        self.user32.SetWindowPos.restype = wintypes.BOOL
        self.user32.BringWindowToTop.argtypes = (wintypes.HWND,)
        self.user32.BringWindowToTop.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
        self.user32.SetForegroundWindow.restype = wintypes.BOOL

    def visible_windows_for_pids(self, process_ids):
        expected = set(int(process_id) for process_id in process_ids)
        result = []

        def callback(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            process_id = wintypes.DWORD(0)
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if int(process_id.value) in expected:
                result.append((hwnd, int(process_id.value)))
            return True

        callback_reference = self.enum_proc_type(callback)
        self.user32.EnumWindows(callback_reference, 0)
        return result

    def is_iconic(self, hwnd):
        return bool(self.user32.IsIconic(hwnd))

    def restore(self, hwnd):
        self.user32.ShowWindow(hwnd, self.SW_RESTORE)

    def maximize(self, hwnd):
        self.user32.ShowWindow(hwnd, self.SW_MAXIMIZE)

    def bring_to_front(self, hwnd):
        flags = self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW
        self.user32.SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, flags)
        self.user32.BringWindowToTop(hwnd)
        self.user32.SetForegroundWindow(hwnd)
        self.user32.SetWindowPos(hwnd, ctypes.c_void_p(-2), 0, 0, 0, 0, flags)
