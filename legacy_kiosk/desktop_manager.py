# -*- coding: utf-8 -*-

import ctypes
import os
import subprocess
import time
from ctypes import wintypes

from legacy_kiosk.process_watchdog import NativeProcessBackend


SHELL_WINDOW_CLASSES = frozenset((u"Shell_TrayWnd", u"Progman", u"WorkerW"))


class NativeDesktopWindowApi(object):
    SW_HIDE = 0
    SW_SHOW = 5

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
        self.user32.GetClassNameW.argtypes = (
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        )
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
        self.user32.ShowWindow.restype = wintypes.BOOL
        self.kernel32.GetCurrentProcessId.argtypes = ()
        self.kernel32.GetCurrentProcessId.restype = wintypes.DWORD
        self.kernel32.ProcessIdToSessionId.argtypes = (
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.kernel32.ProcessIdToSessionId.restype = wintypes.BOOL

    def _session_id(self, process_id):
        session_id = wintypes.DWORD(0)
        if not self.kernel32.ProcessIdToSessionId(
            int(process_id), ctypes.byref(session_id)
        ):
            return None
        return int(session_id.value)

    def current_session_id(self):
        return self._session_id(self.kernel32.GetCurrentProcessId())

    def shell_windows_for_pids(self, process_ids):
        expected_pids = set(int(value) for value in process_ids)
        expected_session = self.current_session_id()
        windows = []

        def callback(hwnd, _lparam):
            process_id = wintypes.DWORD(0)
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            pid = int(process_id.value)
            if pid not in expected_pids or self._session_id(pid) != expected_session:
                return True
            class_name = ctypes.create_unicode_buffer(256)
            self.user32.GetClassNameW(hwnd, class_name, len(class_name))
            if class_name.value in SHELL_WINDOW_CLASSES:
                windows.append(hwnd)
            return True

        callback_reference = self.enum_proc_type(callback)
        self.user32.EnumWindows(callback_reference, 0)
        return windows

    def hide(self, hwnd):
        self.user32.ShowWindow(hwnd, self.SW_HIDE)

    def show(self, hwnd):
        self.user32.ShowWindow(hwnd, self.SW_SHOW)

    def start_explorer(self):
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.Popen(
            ["explorer.exe"], shell=False, creationflags=creation_flags
        )


class WindowsDesktopSessionManager(object):
    def __init__(self, process_backend=None, window_api=None, clock=None, sleeper=None):
        self.process_backend = process_backend or NativeProcessBackend()
        self.window_api = window_api or NativeDesktopWindowApi()
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep
        self.explorer_path = os.path.join(
            os.environ.get("WINDIR", r"C:\Windows"), "explorer.exe"
        )

    def _shell_windows(self):
        process_ids = self.process_backend.find_process_ids(self.explorer_path)
        return self.window_api.shell_windows_for_pids(process_ids)

    def open_current_desktop(self, timeout_seconds=5):
        windows = self._shell_windows()
        if not windows:
            self.window_api.start_explorer()
            deadline = float(self.clock()) + float(timeout_seconds)
            while float(self.clock()) <= deadline:
                windows = self._shell_windows()
                if windows:
                    break
                self.sleeper(0.1)
        for hwnd in windows:
            self.window_api.show(hwnd)
        return bool(windows)

    def hide_current_desktop(self):
        windows = self._shell_windows()
        for hwnd in windows:
            self.window_api.hide(hwnd)
        return bool(windows)
