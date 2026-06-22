# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import ntpath
import subprocess

from ctypes import wintypes

from kiosk_v2_legacy.app.process_supervisor import (
    ProcessRef,
    normalize_executable_path,
)


TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
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


class LegacyProcessRuntime(object):
    def __init__(self, native=None, popen_factory=None):
        self.native = native or NativeLegacyProcessApi()
        self.popen_factory = popen_factory or subprocess.Popen
        self._started_processes = {}
        self._handoff_baselines = {}

    def find_by_exact_path(self, path):
        expected = normalize_executable_path(path)
        processes = []
        for pid in self.native.process_ids():
            try:
                image_path = self.native.query_image_path(pid)
            except (OSError, RuntimeError):
                continue
            try:
                matches = normalize_executable_path(image_path) == expected
            except (TypeError, ValueError):
                matches = False
            if matches and self.is_running(pid, path):
                processes.append(ProcessRef(pid, image_path, True))
        return processes

    def find_existing_by_name(self, path):
        expected_name = ntpath.basename(normalize_executable_path(path))
        processes = []
        for pid in self.native.process_ids():
            try:
                image_path = self.native.query_image_path(pid)
                same_name = ntpath.basename(
                    normalize_executable_path(image_path)
                ) == expected_name
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
            if same_name and self.is_running(pid, image_path):
                processes.append(ProcessRef(pid, image_path, True))
        return processes

    def start(self, application_settings):
        command = [application_settings.path]
        command.extend(application_settings.arguments)
        try:
            baseline = self._same_name_process_ids(application_settings.path)
        except (OSError, RuntimeError):
            baseline = None
        process = self.popen_factory(
            command,
            cwd=application_settings.working_directory or None,
            shell=False,
        )
        self._started_processes[int(process.pid)] = process
        self._handoff_baselines[int(process.pid)] = baseline
        return ProcessRef(process.pid, application_settings.path, True)

    def find_handoff(self, parent_pid, configured_path):
        expected_name = ntpath.basename(
            normalize_executable_path(configured_path)
        )
        parent_map = self.native.process_parent_map()
        descendants = set()
        frontier = [int(parent_pid)]
        while frontier:
            current = frontier.pop(0)
            children = [
                pid for pid, parent in parent_map.items()
                if parent == current and pid not in descendants
            ]
            descendants.update(children)
            frontier.extend(children)

        candidate_pids = set(descendants)
        baseline = self._handoff_baselines.get(int(parent_pid))
        if baseline is not None:
            candidate_pids.update(
                self._same_name_process_ids(configured_path) - baseline
            )

        found = []
        for pid in sorted(candidate_pids):
            try:
                image_path = self.native.query_image_path(pid)
                same_name = ntpath.basename(
                    normalize_executable_path(image_path)
                ) == expected_name
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
            if same_name and self.is_running(pid, image_path):
                found.append(ProcessRef(pid, image_path, True))
        return found

    def clear_handoff(self, parent_pid):
        self._handoff_baselines.pop(int(parent_pid), None)

    def _same_name_process_ids(self, configured_path):
        expected_name = ntpath.basename(
            normalize_executable_path(configured_path)
        )
        found = set()
        for pid in self.native.process_ids():
            try:
                image_path = self.native.query_image_path(pid)
                same_name = ntpath.basename(
                    normalize_executable_path(image_path)
                ) == expected_name
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
            if same_name and self.is_running(pid, image_path):
                found.add(int(pid))
        return found

    def is_running(self, pid, expected_path):
        try:
            running = bool(self.native.is_process_running(pid, expected_path))
        except (OSError, RuntimeError):
            running = False
        if not running:
            self._started_processes.pop(int(pid), None)
        return running


class NativeLegacyProcessApi(object):
    def __init__(self, kernel32=None, psapi=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.psapi = psapi or ctypes.windll.psapi
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self.kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESSENTRY32W),
        ]
        self.kernel32.Process32FirstW.restype = wintypes.BOOL
        self.kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESSENTRY32W),
        ]
        self.kernel32.Process32NextW.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.psapi.GetModuleFileNameExW.argtypes = [
            wintypes.HANDLE,
            wintypes.HMODULE,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        self.psapi.GetModuleFileNameExW.restype = wintypes.DWORD

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

    def process_parent_map(self):
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        invalid = ctypes.c_void_p(-1).value
        if not snapshot or int(snapshot) == invalid:
            raise self._error("CreateToolhelp32Snapshot")
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            if not self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                raise self._error("Process32FirstW")
            parents = {}
            while True:
                parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                if not self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
            return parents
        finally:
            self._close_handle(snapshot)

    def query_image_path(self, pid):
        access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        handle = self._open_process(pid, access)
        try:
            return self._query_path_from_handle(handle)
        finally:
            self._close_handle(handle)

    def is_process_running(self, pid, expected_path):
        access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE
        handle = self._open_process(pid, access)
        try:
            actual_path = self._query_path_from_handle(handle)
            if normalize_executable_path(actual_path) != normalize_executable_path(
                expected_path
            ):
                return False
            wait_result = self._wait_for_process(handle)
            if wait_result == WAIT_TIMEOUT:
                return True
            if wait_result == WAIT_OBJECT_0:
                return False
            raise self._error("WaitForSingleObject")
        finally:
            self._close_handle(handle)

    def _open_process(self, pid, access):
        handle = self.kernel32.OpenProcess(access, False, int(pid))
        if not handle:
            raise self._error("OpenProcess")
        return handle

    def _query_path_from_handle(self, handle):
        buffer = ctypes.create_unicode_buffer(MAX_PROCESS_PATH)
        length = int(
            self.psapi.GetModuleFileNameExW(
                handle,
                None,
                buffer,
                len(buffer),
            )
        )
        if length <= 0:
            raise self._error("GetModuleFileNameExW")
        return buffer.value

    def _wait_for_process(self, handle):
        return int(self.kernel32.WaitForSingleObject(handle, 0))

    def _close_handle(self, handle):
        if handle:
            self.kernel32.CloseHandle(handle)

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(
            code,
            "{0} failed with Windows error {1}".format(api_name, code),
        )
