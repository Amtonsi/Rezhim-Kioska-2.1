# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import ntpath

from ctypes import wintypes

from kiosk_v2_legacy.platform.process_runtime import NativeLegacyProcessApi


PROCESS_TERMINATE = 0x0001
SW_HIDE = 0
SW_SHOW = 5
SHELL_CLASSES = frozenset(
    (
        "shell_traywnd",
        "shell_secondarytraywnd",
        "progman",
        "workerw",
        "dv2controlhost",
        "basebar",
        "button",
    )
)
SHELL_CLASS_KEYS = frozenset(name.replace("_", "") for name in SHELL_CLASSES)


class ProcessRecord(object):
    __slots__ = ("pid", "image_path", "session_id")

    def __init__(self, pid, image_path, session_id):
        self.pid = int(pid)
        self.image_path = image_path or ""
        self.session_id = int(session_id)


class ShellSurface(object):
    __slots__ = ("hwnd", "class_name", "pid", "session_id")

    def __init__(self, hwnd, class_name, pid, session_id):
        self.hwnd = int(hwnd)
        self.class_name = class_name or ""
        self.pid = int(pid)
        self.session_id = int(session_id)


class IsolationResult(object):
    __slots__ = ("terminated_pids", "failed_pids", "hidden_hwnds")

    def __init__(self, terminated_pids=(), failed_pids=(), hidden_hwnds=()):
        self.terminated_pids = tuple(terminated_pids)
        self.failed_pids = tuple(failed_pids)
        self.hidden_hwnds = tuple(hidden_hwnds)


class DesktopIsolation(object):
    def __init__(self, desktop_api):
        self.desktop_api = desktop_api
        self.running = False
        self._hidden_set = set()
        self._hidden_order = []

    def start(self):
        self.running = True
        return self.enforce()

    def tick(self):
        if not self.running:
            return IsolationResult()
        return self.enforce()

    def stop(self):
        self.running = False
        for hwnd in self._hidden_order:
            try:
                self.desktop_api.show_window(hwnd)
            except (OSError, RuntimeError):
                pass
        self._hidden_set = set()
        self._hidden_order = []

    def enforce(self):
        current_session = int(self.desktop_api.current_session_id())
        explorer_pids = set()
        terminated = []
        failed = []
        for process in self.desktop_api.list_processes():
            if process.session_id != current_session:
                continue
            basename = ntpath.basename(ntpath.normpath(process.image_path)).lower()
            if basename != "explorer.exe":
                continue
            explorer_pids.add(process.pid)
            if self.desktop_api.terminate_process(process.pid):
                terminated.append(process.pid)
            else:
                failed.append(process.pid)

        hidden = []
        for surface in self.desktop_api.list_shell_surfaces():
            if surface.session_id != current_session:
                continue
            if surface.pid not in explorer_pids:
                continue
            normalized = surface.class_name.replace("_", "").lower()
            if normalized not in SHELL_CLASS_KEYS:
                continue
            if self.desktop_api.hide_window(surface.hwnd):
                hidden.append(surface.hwnd)
                if surface.hwnd not in self._hidden_set:
                    self._hidden_set.add(surface.hwnd)
                    self._hidden_order.append(surface.hwnd)
        return IsolationResult(terminated, failed, hidden)


class LegacyDesktopApi(object):
    def __init__(self, process_api=None, desktop_native=None, shell_native=None):
        self.process_api = process_api or NativeLegacyProcessApi()
        self.desktop_native = desktop_native or NativeDesktopProcessApi()
        self.shell_native = shell_native or NativeShellSurfaceApi()

    def current_session_id(self):
        return self.desktop_native.process_session_id(
            self.desktop_native.current_process_id()
        )

    def list_processes(self):
        records = []
        for pid in self.process_api.process_ids():
            try:
                path = self.process_api.query_image_path(pid)
                session_id = self.desktop_native.process_session_id(pid)
            except (OSError, RuntimeError):
                continue
            records.append(ProcessRecord(pid, path, session_id))
        return records

    def terminate_process(self, pid):
        try:
            return bool(self.desktop_native.terminate_process(pid))
        except (OSError, RuntimeError):
            return False

    def list_shell_surfaces(self):
        surfaces = []
        for hwnd, class_name, pid in self.shell_native.enumerate_surfaces():
            try:
                session_id = self.desktop_native.process_session_id(pid)
            except (OSError, RuntimeError):
                continue
            surfaces.append(ShellSurface(hwnd, class_name, pid, session_id))
        return surfaces

    def hide_window(self, hwnd):
        return self.shell_native.show_window(hwnd, SW_HIDE)

    def show_window(self, hwnd):
        return self.shell_native.show_window(hwnd, SW_SHOW)


class NativeDesktopProcessApi(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.GetCurrentProcessId.argtypes = []
        self.kernel32.GetCurrentProcessId.restype = wintypes.DWORD
        self.kernel32.ProcessIdToSessionId.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateProcess.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def current_process_id(self):
        return int(self.kernel32.GetCurrentProcessId())

    def process_session_id(self, pid):
        session_id = wintypes.DWORD()
        if not self.kernel32.ProcessIdToSessionId(int(pid), ctypes.byref(session_id)):
            raise self._error("ProcessIdToSessionId")
        return int(session_id.value)

    def terminate_process(self, pid):
        handle = self._open_terminate_handle(pid)
        try:
            return self._terminate_handle(handle)
        finally:
            self._close_handle(handle)

    def _open_terminate_handle(self, pid):
        handle = self.kernel32.OpenProcess(PROCESS_TERMINATE, False, int(pid))
        if not handle:
            raise self._error("OpenProcess")
        return handle

    def _terminate_handle(self, handle):
        if not self.kernel32.TerminateProcess(handle, 0):
            raise self._error("TerminateProcess")
        return True

    def _close_handle(self, handle):
        if handle:
            self.kernel32.CloseHandle(handle)

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(code, "{0} failed with Windows error {1}".format(api_name, code))


class NativeShellSurfaceApi(object):
    def __init__(self, user32=None):
        self.user32 = user32 or ctypes.windll.user32
        self._callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )
        self._configure_signatures()

    def _configure_signatures(self):
        self.user32.EnumWindows.argtypes = [self._callback_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.EnumChildWindows.argtypes = [
            wintypes.HWND,
            self._callback_type,
            wintypes.LPARAM,
        ]
        self.user32.EnumChildWindows.restype = wintypes.BOOL
        self.user32.GetClassNameW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindow.restype = wintypes.BOOL

    def enumerate_surfaces(self):
        handles = []
        seen = set()

        def add(hwnd):
            value = int(hwnd)
            if value not in seen:
                seen.add(value)
                handles.append(value)

        @self._callback_type
        def collect_child(hwnd, unused):
            add(hwnd)
            return True

        @self._callback_type
        def collect_top(hwnd, unused):
            add(hwnd)
            self.user32.EnumChildWindows(hwnd, collect_child, 0)
            return True

        self.user32.EnumWindows(collect_top, 0)
        surfaces = []
        for hwnd in handles:
            class_name = self._class_name(hwnd)
            if class_name.replace("_", "").lower() not in SHELL_CLASS_KEYS:
                continue
            process_id = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            surfaces.append((hwnd, class_name, int(process_id.value)))
        return surfaces

    def show_window(self, hwnd, command):
        self.user32.ShowWindow(hwnd, int(command))
        return True

    def _class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        length = int(self.user32.GetClassNameW(hwnd, buffer, len(buffer)))
        if length <= 0:
            return ""
        return buffer.value
