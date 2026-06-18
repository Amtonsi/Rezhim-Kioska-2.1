# -*- coding: utf-8 -*-

import ctypes
import os
import subprocess
import time
from ctypes import wintypes


class LegacyProcessWatchdog(object):
    def __init__(
        self,
        executable_path,
        arguments="",
        working_directory="",
        restart_on_exit=True,
        restart_delay_seconds=2,
        single_instance=True,
        start_maximized=False,
        backend=None,
        clock=None,
        logger=None,
    ):
        self.executable_path = executable_path
        self.arguments = arguments or ""
        self.working_directory = working_directory or ""
        self.restart_on_exit = bool(restart_on_exit)
        self.restart_delay_seconds = float(restart_delay_seconds)
        self.single_instance = bool(single_instance)
        self.start_maximized = bool(start_maximized)
        self.backend = backend or NativeProcessBackend()
        self.clock = clock or time.time
        self.logger = logger
        self.process = None
        self.supervision_enabled = True
        self.next_restart_time = None
        self.has_started = False

    def tick(self):
        if not self.supervision_enabled:
            return "stopped"

        now = float(self.clock())
        if self.process is not None:
            if self.backend.is_process_running(self.process, self.executable_path):
                return "running"
            self.process = None
            if not self.restart_on_exit:
                return "exited"
            self.next_restart_time = now + self.restart_delay_seconds
            self._log("watchdog.exited")
            return "exited"

        if self.single_instance:
            process_ids = self.backend.find_process_ids(self.executable_path)
            if process_ids:
                self.process = self.backend.adopt_process(process_ids[0])
                self.has_started = True
                self.next_restart_time = None
                self._log("watchdog.adopted")
                return "adopted"

        if self.next_restart_time is not None and now < self.next_restart_time:
            return "waiting"

        restarted = self.has_started
        self.process = self.backend.start_process(
            self.executable_path,
            self.arguments,
            self.working_directory,
            self.start_maximized,
        )
        self.has_started = True
        self.next_restart_time = None
        status = "restarted" if restarted else "started"
        self._log("watchdog.%s" % status)
        return status

    def stop_supervision(self):
        self.supervision_enabled = False

    def start_supervision(self):
        self.supervision_enabled = True

    def _log(self, event):
        if self.logger is None:
            return
        try:
            self.logger.log(
                event,
                {
                    "executable": self.executable_path,
                    "argument_count": 1 if self.arguments else 0,
                },
            )
        except Exception:
            pass


class NativeProcessBackend(object):
    def __init__(self, api=None):
        self.api = api or NativeProcessApi()

    def find_process_ids(self, executable_path):
        return self.api.process_ids_for_path(executable_path)

    def adopt_process(self, process_id):
        return AdoptedProcess(process_id)

    def start_process(
        self, executable_path, arguments, working_directory, start_maximized
    ):
        return self.api.start_process(
            executable_path, arguments, working_directory, start_maximized
        )

    def is_process_running(self, process, executable_path):
        if isinstance(process, AdoptedProcess):
            return self.api.process_id_matches_path(process.pid, executable_path)
        poll = getattr(process, "poll", None)
        if poll is None:
            return False
        return poll() is None


class AdoptedProcess(object):
    def __init__(self, process_id):
        self.pid = int(process_id)


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = (
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
    )


def _normalize_path(path):
    return os.path.normcase(os.path.abspath(os.path.expandvars(path or ""))).rstrip(
        "\\/"
    )


class NativeProcessApi(object):
    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    SW_MAXIMIZE = 3
    STARTF_USESHOWWINDOW = 0x00000001

    def __init__(self, kernel32=None, psapi=None, shell32=None, user32=None):
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self.psapi = psapi or ctypes.WinDLL("psapi", use_last_error=True)
        self.shell32 = shell32 or ctypes.WinDLL("shell32", use_last_error=True)
        self.user32 = user32 or ctypes.WinDLL("user32", use_last_error=True)
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.CreateToolhelp32Snapshot.argtypes = (
            wintypes.DWORD,
            wintypes.DWORD,
        )
        self.kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.kernel32.Process32FirstW.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESSENTRY32W),
        )
        self.kernel32.Process32FirstW.restype = wintypes.BOOL
        self.kernel32.Process32NextW.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESSENTRY32W),
        )
        self.kernel32.Process32NextW.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
        self.kernel32.LocalFree.restype = ctypes.c_void_p
        self.psapi.GetModuleFileNameExW.argtypes = (
            wintypes.HANDLE,
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
        )
        self.psapi.GetModuleFileNameExW.restype = wintypes.DWORD
        self.shell32.CommandLineToArgvW.argtypes = (
            wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_int),
        )
        self.shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
        self.user32.WaitForInputIdle.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        self.user32.WaitForInputIdle.restype = wintypes.DWORD

    def _process_ids(self):
        snapshot = self.kernel32.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        invalid_handle = ctypes.c_void_p(-1).value
        snapshot_value = getattr(snapshot, "value", snapshot)
        if snapshot_value == invalid_handle:
            return []
        process_ids = []
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        try:
            if not self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                return []
            while True:
                process_ids.append(int(entry.th32ProcessID))
                if not self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
        finally:
            self.kernel32.CloseHandle(snapshot)
        return process_ids

    def _process_path(self, process_id):
        handle = self.kernel32.OpenProcess(
            self.PROCESS_QUERY_INFORMATION | self.PROCESS_VM_READ,
            False,
            int(process_id),
        )
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = self.psapi.GetModuleFileNameExW(
                handle, None, buffer, len(buffer)
            )
            return buffer.value if length else ""
        finally:
            self.kernel32.CloseHandle(handle)

    def process_ids_for_path(self, executable_path):
        expected = _normalize_path(executable_path)
        return [
            process_id
            for process_id in self._process_ids()
            if _normalize_path(self._process_path(process_id)) == expected
        ]

    def process_id_matches_path(self, process_id, executable_path):
        return _normalize_path(self._process_path(process_id)) == _normalize_path(
            executable_path
        )

    def _split_arguments(self, arguments):
        arguments = arguments or ""
        if not arguments.strip():
            return []
        if not isinstance(arguments, unicode):
            arguments = arguments.decode("utf-8")
        count = ctypes.c_int(0)
        argv = self.shell32.CommandLineToArgvW(arguments, ctypes.byref(count))
        if not argv:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return [argv[index] for index in range(count.value)]
        finally:
            self.kernel32.LocalFree(argv)

    def start_process(
        self, executable_path, arguments, working_directory, start_maximized
    ):
        command = [executable_path]
        command.extend(self._split_arguments(arguments))
        startup_info = None
        if start_maximized:
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= self.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = self.SW_MAXIMIZE
        process = subprocess.Popen(
            command,
            cwd=working_directory or None,
            shell=False,
            startupinfo=startup_info,
        )
        handle = getattr(process, "_handle", None)
        if handle:
            self.user32.WaitForInputIdle(handle, 5000)
        return process
