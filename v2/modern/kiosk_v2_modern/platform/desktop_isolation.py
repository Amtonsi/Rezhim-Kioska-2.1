# -*- coding: utf-8 -*-
import ctypes
import ntpath

from ctypes import wintypes


TH32CS_SNAPPROCESS = 0x00000002
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_PROCESS_PATH = 32768
SW_HIDE = 0
SW_SHOW = 5
SHELL_CLASS_KEYS = frozenset(
    (
        "shelltraywnd",
        "shellsecondarytraywnd",
        "progman",
        "workerw",
        "dv2controlhost",
        "basebar",
        "button",
    )
)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class ProcessRecord(object):
    def __init__(self, pid, image_path, session_id):
        self.pid = int(pid)
        self.image_path = image_path or ""
        self.session_id = int(session_id)


class ShellSurface(object):
    def __init__(self, hwnd, class_name, pid, session_id):
        self.hwnd = int(hwnd)
        self.class_name = class_name or ""
        self.pid = int(pid)
        self.session_id = int(session_id)


class IsolationResult(object):
    def __init__(
        self,
        terminated_pids=(),
        failed_pids=(),
        hidden_hwnds=(),
        fallback_active=False,
    ):
        self.terminated_pids = tuple(terminated_pids)
        self.failed_pids = tuple(failed_pids)
        self.hidden_hwnds = tuple(hidden_hwnds)
        self.fallback_active = bool(fallback_active)


class DesktopIsolation(object):
    def __init__(self, process_api, surface_api=None, terminate_explorer=True):
        self.process_api = process_api
        self.surface_api = surface_api
        self.terminate_explorer = bool(terminate_explorer)
        self.running = False
        self._hidden_set = set()
        self._hidden_order = []

    def start(self):
        self.running = True
        return self.enforce()

    def stop(self):
        self.running = False
        if self.surface_api is not None:
            for hwnd in self._hidden_order:
                try:
                    self.surface_api.show_window(hwnd)
                except (OSError, RuntimeError):
                    pass
        self._hidden_set = set()
        self._hidden_order = []

    def tick(self):
        if not self.running:
            return IsolationResult()
        return self.enforce()

    def enforce(self):
        current_session = int(self.process_api.current_session_id())
        explorer_pids = set()
        terminated = []
        failed = []
        for process in self.process_api.list_processes():
            if process.session_id != current_session:
                continue
            if ntpath.basename(ntpath.normpath(process.image_path)).lower() != "explorer.exe":
                continue
            explorer_pids.add(process.pid)
            if not self.terminate_explorer:
                continue
            if self.process_api.terminate_process(process.pid):
                terminated.append(process.pid)
            else:
                failed.append(process.pid)

        hidden = []
        if self.surface_api is not None:
            for surface in self.surface_api.list_shell_surfaces():
                if surface.session_id != current_session:
                    continue
                if surface.pid not in explorer_pids:
                    continue
                normalized = surface.class_name.replace("_", "").lower()
                if normalized not in SHELL_CLASS_KEYS:
                    continue
                try:
                    was_hidden = self.surface_api.hide_window(surface.hwnd)
                except (OSError, RuntimeError):
                    was_hidden = False
                if not was_hidden:
                    continue
                hidden.append(surface.hwnd)
                if surface.hwnd not in self._hidden_set:
                    self._hidden_set.add(surface.hwnd)
                    self._hidden_order.append(surface.hwnd)
        return IsolationResult(
            terminated,
            failed,
            hidden,
            fallback_active=bool(explorer_pids) and not self.terminate_explorer,
        )


class WindowsProcessApi(object):
    def __init__(self, native=None):
        self.native = native or NativeProcessApi()

    def current_session_id(self):
        return self.native.process_session_id(self.native.current_process_id())

    def list_processes(self):
        records = []
        for pid in self.native.process_ids():
            try:
                image_path = self.native.query_image_path(pid)
                session_id = self.native.process_session_id(pid)
            except (OSError, RuntimeError):
                continue
            records.append(ProcessRecord(pid, image_path, session_id))
        return records

    def terminate_process(self, pid):
        try:
            return bool(self.native.terminate_process(pid))
        except (OSError, RuntimeError):
            return False


class WindowsShellSurfaceApi(object):
    def __init__(self, native=None):
        self.native = native or NativeShellSurfaceApi()

    def list_shell_surfaces(self):
        surfaces = []
        for hwnd, class_name, pid in self.native.enumerate_surfaces():
            try:
                session_id = self.native.process_session_id(pid)
            except (OSError, RuntimeError):
                continue
            surfaces.append(ShellSurface(hwnd, class_name, pid, session_id))
        return surfaces

    def hide_window(self, hwnd):
        return self.native.show_window(hwnd, SW_HIDE)

    def show_window(self, hwnd):
        return self.native.show_window(hwnd, SW_SHOW)


class NativeShellSurfaceApi(object):
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
        self.kernel32.ProcessIdToSessionId.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.ProcessIdToSessionId.restype = wintypes.BOOL

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

    def process_session_id(self, pid):
        session_id = wintypes.DWORD()
        if not self.kernel32.ProcessIdToSessionId(int(pid), ctypes.byref(session_id)):
            raise self._error("ProcessIdToSessionId")
        return int(session_id.value)

    def show_window(self, hwnd, command):
        self.user32.ShowWindow(hwnd, int(command))
        return True

    def _class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        length = int(self.user32.GetClassNameW(hwnd, buffer, len(buffer)))
        if length <= 0:
            return ""
        return buffer.value

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(code, "{0} failed with Windows error {1}".format(api_name, code))


class NativeProcessApi(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self.kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        self.kernel32.Process32FirstW.restype = wintypes.BOOL
        self.kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        self.kernel32.Process32NextW.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.kernel32.ProcessIdToSessionId.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
        self.kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateProcess.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.GetCurrentProcessId.argtypes = []
        self.kernel32.GetCurrentProcessId.restype = wintypes.DWORD

    def current_process_id(self):
        return int(self.kernel32.GetCurrentProcessId())

    def process_ids(self):
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        invalid = ctypes.c_void_p(-1).value
        if not snapshot or int(snapshot) == invalid:
            raise self._error("CreateToolhelp32Snapshot")
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            if not self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                raise self._error("Process32FirstW")
            pids = []
            while True:
                pids.append(int(entry.th32ProcessID))
                if not self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
            return pids
        finally:
            self._close_handle(snapshot)

    def process_session_id(self, pid):
        session_id = wintypes.DWORD()
        if not self.kernel32.ProcessIdToSessionId(int(pid), ctypes.byref(session_id)):
            raise self._error("ProcessIdToSessionId")
        return int(session_id.value)

    def query_image_path(self, pid):
        handle = self._open_process(pid, PROCESS_QUERY_LIMITED_INFORMATION)
        try:
            return self._query_process_path_from_handle(handle)
        finally:
            self._close_handle(handle)

    def terminate_process(self, pid):
        handle = self._open_process(pid, PROCESS_TERMINATE)
        try:
            return self._terminate_process_handle(handle)
        finally:
            self._close_handle(handle)

    def _open_process(self, pid, access):
        handle = self.kernel32.OpenProcess(access, False, int(pid))
        if not handle:
            raise self._error("OpenProcess")
        return handle

    def _query_process_path_from_handle(self, handle):
        buffer = ctypes.create_unicode_buffer(MAX_PROCESS_PATH)
        size = wintypes.DWORD(len(buffer))
        if not self.kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(size),
        ):
            raise self._error("QueryFullProcessImageNameW")
        return buffer.value

    def _terminate_process_handle(self, handle):
        if not self.kernel32.TerminateProcess(handle, 0):
            raise self._error("TerminateProcess")
        return True

    def _close_handle(self, handle):
        if handle:
            self.kernel32.CloseHandle(handle)

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(code, "{0} failed with Windows error {1}".format(api_name, code))
