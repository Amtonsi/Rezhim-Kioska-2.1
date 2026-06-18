# -*- coding: utf-8 -*-

import os
import subprocess

from python_kiosk.logging_service import KioskLogger


class WindowsSessionLockdown(object):
    def __init__(self, backend=None, logger=None, enabled=True):
        self.backend = backend or WindowsDesktopBackend()
        self.logger = logger or KioskLogger()
        self.enabled = bool(enabled)
        self.active = False

    def activate_operator_mode(self):
        if not self.enabled:
            return {"disabled": True}
        try:
            result = self.backend.lockdown_current_desktop_shell()
            self.active = True
            self.logger.info("session.lockdown_enabled", **result)
            return result
        except Exception as error:
            self.logger.warning("session.lockdown_failed", error=str(error))
            return {"error": str(error)}

    def release_operator_mode(self):
        if not self.active:
            return {"inactive": True}
        try:
            result = self.backend.restore_current_desktop_shell()
            self.active = False
            self.logger.info("session.lockdown_released", **result)
            return result
        except Exception as error:
            self.logger.warning("session.lockdown_release_failed", error=str(error))
            return {"error": str(error)}


class WindowsDesktopBackend(object):
    SW_HIDE = 0
    SW_SHOW = 5

    SHELL_WINDOW_CLASSES = (
        "Shell_TrayWnd",
        "Progman",
        "WorkerW",
    )

    def __init__(self):
        self.hidden_windows = []

    def lockdown_current_desktop_shell(self):
        if os.name != "nt":
            return {"platform": "non-windows", "hidden_windows": []}
        windows = self._find_shell_windows()
        for hwnd in windows:
            self._show_window(hwnd, self.SW_HIDE)
        shell_window = self._find_window("Shell_TrayWnd")
        self.hidden_windows = windows
        return {
            "shell_window": int(shell_window or 0),
            "hidden_windows": [int(hwnd) for hwnd in windows],
            "closed_explorer": False,
        }

    def restore_current_desktop_shell(self):
        if os.name != "nt":
            return {"platform": "non-windows", "restored_windows": []}
        if not self.hidden_windows:
            self.hidden_windows = self._find_shell_windows()
        restored = []
        for hwnd in self.hidden_windows:
            if self._is_window(hwnd):
                self._show_window(hwnd, self.SW_SHOW)
                restored.append(hwnd)
        self.hidden_windows = []
        return {"restored_windows": [int(hwnd) for hwnd in restored]}

    def _find_shell_windows(self):
        windows = []
        for class_name in self.SHELL_WINDOW_CLASSES:
            windows.extend(self._find_windows_by_class(class_name))
        unique = []
        for hwnd in windows:
            if hwnd and hwnd not in unique:
                unique.append(hwnd)
        return unique

    def _find_window(self, class_name):
        import ctypes

        return ctypes.windll.user32.FindWindowW(class_name, None)

    def _find_windows_by_class(self, class_name):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, l_param):
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buffer, 256)
            if buffer.value == class_name:
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found

    def _show_window(self, hwnd, command):
        import ctypes

        return bool(ctypes.windll.user32.ShowWindow(hwnd, command))

    def _is_window(self, hwnd):
        import ctypes

        return bool(ctypes.windll.user32.IsWindow(hwnd))


def recover_current_desktop(backend=None, process_factory=None):
    backend = backend or WindowsDesktopBackend()
    result = backend.restore_current_desktop_shell()
    started_explorer = False
    if os.name == "nt":
        factory = process_factory or subprocess.Popen
        try:
            factory(["explorer.exe"])
            started_explorer = True
        except Exception as error:
            result["explorer_error"] = str(error)
    result["started_explorer"] = started_explorer
    return result
