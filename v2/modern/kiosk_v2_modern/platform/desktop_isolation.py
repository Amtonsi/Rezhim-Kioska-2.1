# -*- coding: utf-8 -*-
import ctypes
import ntpath

from ctypes import wintypes


TH32CS_SNAPPROCESS = 0x00000002
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_PROCESS_PATH = 32768


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


class IsolationResult(object):
    def __init__(self, terminated_pids=(), failed_pids=()):
        self.terminated_pids = tuple(terminated_pids)
        self.failed_pids = tuple(failed_pids)


class DesktopIsolation(object):
    def __init__(self, process_api):
        self.process_api = process_api
        self.running = False

    def start(self):
        self.running = True
        return self.enforce()

    def stop(self):
        self.running = False

    def tick(self):
        if not self.running:
            return IsolationResult()
        return self.enforce()

    def enforce(self):
        current_session = int(self.process_api.current_session_id())
        terminated = []
        failed = []
        for process in self.process_api.list_processes():
            if process.session_id != current_session:
                continue
            if ntpath.basename(ntpath.normpath(process.image_path)).lower() != "explorer.exe":
                continue
            if self.process_api.terminate_process(process.pid):
                terminated.append(process.pid)
            else:
                failed.append(process.pid)
        return IsolationResult(terminated, failed)


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
