# -*- coding: utf-8 -*-

import os
import time

from python_kiosk.process_watchdog import (
    windows_process_ids_for_name,
    windows_process_ids_for_path,
)


class AppWindowController(object):
    def __init__(self, backend=None):
        self.backend = backend or WindowsWindowBackend()

    def _first_window(self, executable_path):
        windows = self.backend.find_windows_for_executable(executable_path)
        return windows[0] if windows else None

    def is_minimized(self, executable_path):
        windows = self.backend.find_windows_for_executable(executable_path)
        return bool(windows and any(self.backend.is_minimized(hwnd) for hwnd in windows))

    def bring_to_front(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.bring_to_front(hwnd)
        return True

    def ensure_foreground(
        self,
        executable_path,
        wait=False,
        timeout_seconds=5,
        start_maximized=False,
    ):
        if wait and hasattr(self.backend, "wait_for_window"):
            hwnd = self.backend.wait_for_window(executable_path, timeout_seconds)
        else:
            hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        if self.backend.is_minimized(hwnd):
            self.backend.restore(hwnd)
        if start_maximized and hasattr(self.backend, "maximize"):
            self.backend.maximize(hwnd)
        self.backend.bring_to_front(hwnd)
        return True

    def restore(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.restore(hwnd)
        self.backend.bring_to_front(hwnd)
        return True

    def release_topmost(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.clear_topmost(hwnd)
        return True


class WindowsWindowBackend(object):
    SW_RESTORE = 9
    SW_SHOWNORMAL = 1
    SW_MAXIMIZE = 3
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    ASFW_ANY = -1

    def __init__(self, api=None, is_windows=None):
        self.is_windows = os.name == "nt" if is_windows is None else bool(is_windows)
        self.api = api
        if self.api is None and self.is_windows:
            self.api = _Win32WindowApi()

    def wait_for_window(self, executable_path, timeout_seconds=5):
        deadline = time.time() + float(timeout_seconds)
        while time.time() <= deadline:
            hwnd = None
            windows = self.find_windows_for_executable(executable_path)
            if windows:
                hwnd = windows[0]
            if hwnd:
                return hwnd
            time.sleep(0.1)
        return None

    def find_windows_for_executable(self, executable_path):
        if not self.is_windows:
            return []

        pids = self._process_ids_for_executable(executable_path)
        if not pids:
            return []

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, l_param):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if int(pid.value) in pids:
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found

    def _process_ids_for_executable(self, executable_path):
        pids = self._process_ids_for_exact_path(executable_path)
        if pids:
            return pids
        return self._process_ids_for_image_name(executable_path)

    def _process_ids_for_exact_path(self, executable_path):
        return windows_process_ids_for_path(executable_path)

    def _process_ids_for_image_name(self, executable_path):
        return windows_process_ids_for_name(executable_path)

    def is_minimized(self, hwnd):
        if not self.is_windows or self.api is None:
            return False

        return bool(self.api.is_iconic(hwnd))

    def bring_to_front(self, hwnd):
        if not self.is_windows or self.api is None:
            return False
        if self.api.is_iconic(hwnd):
            self.api.show_window(hwnd, self.SW_RESTORE)
        self.api.set_window_pos(
            hwnd,
            self.HWND_TOPMOST,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )
        self._force_foreground(hwnd)
        self.api.set_window_pos(
            hwnd,
            self.HWND_NOTOPMOST,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )
        return self._is_foreground(hwnd)

    def _force_foreground(self, hwnd):
        try:
            self.api.allow_set_foreground_window(self.ASFW_ANY)
        except Exception:
            pass

        current_thread = self.api.get_current_thread_id()
        target_thread = self.api.get_window_thread_process_id(hwnd)
        foreground_hwnd = self.api.get_foreground_window()
        foreground_thread = (
            self.api.get_window_thread_process_id(foreground_hwnd)
            if foreground_hwnd
            else 0
        )
        attached_threads = []
        try:
            for thread_id in (target_thread, foreground_thread):
                if not thread_id or thread_id == current_thread:
                    continue
                if thread_id in attached_threads:
                    continue
                if self.api.attach_thread_input(current_thread, thread_id, True):
                    attached_threads.append(thread_id)
            self._activate_window(hwnd)
            if not self._is_foreground(hwnd):
                self.api.send_alt_keypress()
                self._activate_window(hwnd)
        finally:
            for thread_id in reversed(attached_threads):
                try:
                    self.api.attach_thread_input(current_thread, thread_id, False)
                except Exception:
                    pass

    def _activate_window(self, hwnd):
        self.api.bring_window_to_top(hwnd)
        self.api.set_active_window(hwnd)
        self.api.set_focus(hwnd)
        self.api.set_foreground_window(hwnd)

    def _is_foreground(self, hwnd):
        return _hwnd_value(self.api.get_foreground_window()) == _hwnd_value(hwnd)

    def maximize(self, hwnd):
        if not self.is_windows or self.api is None:
            return

        self.api.show_window(hwnd, self.SW_MAXIMIZE)

    def clear_topmost(self, hwnd):
        if not self.is_windows or self.api is None:
            return

        self.api.set_window_pos(
            hwnd,
            self.HWND_NOTOPMOST,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )

    def restore(self, hwnd):
        if not self.is_windows or self.api is None:
            return

        self.api.show_window(hwnd, self.SW_RESTORE)


def _hwnd_value(hwnd):
    try:
        return int(hwnd)
    except TypeError:
        return int(getattr(hwnd, "value", 0) or 0)


class _Win32WindowApi(object):
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def is_iconic(self, hwnd):
        return bool(self.user32.IsIconic(hwnd))

    def show_window(self, hwnd, command):
        return bool(self.user32.ShowWindow(hwnd, command))

    def set_window_pos(self, hwnd, insert_after, flags):
        return bool(
            self.user32.SetWindowPos(
                hwnd,
                insert_after,
                0,
                0,
                0,
                0,
                flags,
            )
        )

    def get_foreground_window(self):
        return self.user32.GetForegroundWindow()

    def get_current_thread_id(self):
        return int(self.kernel32.GetCurrentThreadId())

    def get_window_thread_process_id(self, hwnd):
        process_id = self.wintypes.DWORD()
        return int(
            self.user32.GetWindowThreadProcessId(
                hwnd,
                self.ctypes.byref(process_id),
            )
        )

    def allow_set_foreground_window(self, process_id):
        return bool(self.user32.AllowSetForegroundWindow(process_id))

    def attach_thread_input(self, source_thread, target_thread, attach):
        return bool(
            self.user32.AttachThreadInput(
                source_thread,
                target_thread,
                bool(attach),
            )
        )

    def bring_window_to_top(self, hwnd):
        return bool(self.user32.BringWindowToTop(hwnd))

    def set_active_window(self, hwnd):
        return self.user32.SetActiveWindow(hwnd)

    def set_focus(self, hwnd):
        return self.user32.SetFocus(hwnd)

    def set_foreground_window(self, hwnd):
        return bool(self.user32.SetForegroundWindow(hwnd))

    def send_alt_keypress(self):
        self.user32.keybd_event(self.VK_MENU, 0, 0, 0)
        self.user32.keybd_event(self.VK_MENU, 0, self.KEYEVENTF_KEYUP, 0)
