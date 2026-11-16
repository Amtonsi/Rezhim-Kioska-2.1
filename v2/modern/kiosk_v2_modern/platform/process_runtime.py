# -*- coding: utf-8 -*-
import ctypes
import ntpath
import os
import subprocess

from ctypes import wintypes

from kiosk_v2_modern.app.process_supervisor import (
    ProcessRef,
    normalize_executable_path,
)
from kiosk_v2_modern.platform.desktop_isolation import (
    NativeProcessApi,
    PROCESSENTRY32W,
    PROCESS_QUERY_LIMITED_INFORMATION,
    TH32CS_SNAPPROCESS,
)


TOKEN_QUERY = 0x0008
TOKEN_USER = 1
TOKEN_SESSION_ID = 12
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102


class WindowsProcessRuntime(object):
    def __init__(self, native=None, popen_factory=None):
        self.native = native or NativeProcessRuntimeApi()
        self.popen_factory = popen_factory or subprocess.Popen
        self._launches = {}

    @staticmethod
    def resolve_configured_path(path):
        # Opening the configured path resolves WOW64 redirection and junctions.
        # Keep launching the original name so Sysnative still selects 64-bit binaries.
        return os.path.realpath(path)

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
            if not matches:
                continue
            if self.is_running(pid, path):
                processes.append(ProcessRef(pid, image_path, True))
        return processes

    def find_existing_broker(self, path):
        family = self.native.broker_family_for_launcher(path)
        if not family:
            return []
        expected_name = ntpath.basename(normalize_executable_path(path))
        found = []
        for pid in self.native.process_ids():
            try:
                image_path = self.native.query_image_path(pid)
                if ntpath.basename(normalize_executable_path(image_path)) != expected_name:
                    continue
                if self.is_running(pid, image_path) and self.native.package_family(pid) == family:
                    found.append(ProcessRef(pid, image_path, True))
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
        return found

    def start(self, application_settings):
        command = [application_settings.path]
        command.extend(application_settings.arguments)
        working_directory = application_settings.working_directory or None
        try:
            baseline = {item.pid for item in self.find_existing_broker(application_settings.path)}
        except (OSError, RuntimeError):
            baseline = None
        process = self.popen_factory(
            command,
            cwd=working_directory,
            shell=False,
        )
        # The process handle pins the launcher PID during the short handoff window.
        self._launches.clear()
        self._launches[int(process.pid)] = (process, baseline)
        return ProcessRef(process.pid, application_settings.path, True)

    def find_handoff(self, parent_pid, configured_path):
        if parent_pid not in self._launches:
            return []
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

        candidate_pids = descendants
        _launcher, baseline = self._launches[parent_pid]
        if baseline is not None:
            candidate_pids.update(
                item.pid for item in self.find_existing_broker(configured_path)
                if item.pid not in baseline
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
        self._launches.pop(int(parent_pid), None)

    def is_running(self, pid, expected_path):
        try:
            return bool(self.native.is_process_running(pid, expected_path))
        except (OSError, RuntimeError):
            return False


class NativeProcessRuntimeApi(NativeProcessApi):
    def _configure_signatures(self):
        super(NativeProcessRuntimeApi, self)._configure_signatures()
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self._configure_operator_identity()
        self._get_package_family = getattr(self.kernel32, "GetPackageFamilyName", None)
        self._notepad_launchers = set()
        if self._get_package_family is not None:
            self._get_package_family.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR
            ]
            self._get_package_family.restype = wintypes.LONG
            self.kernel32.GetSystemWindowsDirectoryW.argtypes = [
                wintypes.LPWSTR, wintypes.UINT
            ]
            self.kernel32.GetSystemWindowsDirectoryW.restype = wintypes.UINT
            directory = ctypes.create_unicode_buffer(32768)
            length = self.kernel32.GetSystemWindowsDirectoryW(directory, len(directory))
            if 0 < length < len(directory):
                self._notepad_launchers = {
                    normalize_executable_path(ntpath.join(directory.value, folder, "notepad.exe"))
                    for folder in ("System32", "SysWOW64", "Sysnative")
                }

    def _configure_operator_identity(self):
        self.advapi32 = ctypes.windll.advapi32
        self.advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
        ]
        self.advapi32.OpenProcessToken.restype = wintypes.BOOL
        self.advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.GetTokenInformation.restype = wintypes.BOOL
        self.advapi32.GetLengthSid.argtypes = [wintypes.LPVOID]
        self.advapi32.GetLengthSid.restype = wintypes.DWORD
        self.operator_identity = self._process_identity(wintypes.HANDLE(-1))

    def _process_identity(self, handle):
        token = wintypes.HANDLE()
        if not self.advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            raise self._error("OpenProcessToken")
        try:
            # TOKEN_USER begins with the SID pointer. Keep its buffer alive until copied.
            user = ctypes.create_string_buffer(256)
            size = wintypes.DWORD()
            if not self.advapi32.GetTokenInformation(
                token, TOKEN_USER, user, len(user), ctypes.byref(size)
            ):
                raise self._error("GetTokenInformation(TokenUser)")
            sid = ctypes.cast(user, ctypes.POINTER(wintypes.LPVOID))[0]
            sid_bytes = ctypes.string_at(sid, self.advapi32.GetLengthSid(sid))
            session = wintypes.DWORD()
            if not self.advapi32.GetTokenInformation(
                token, TOKEN_SESSION_ID, ctypes.byref(session),
                ctypes.sizeof(session), ctypes.byref(size),
            ):
                raise self._error("GetTokenInformation(TokenSessionId)")
            return sid_bytes, int(session.value)
        finally:
            self._close_handle(token)

    def broker_family_for_launcher(self, path):
        if self._get_package_family is None:
            return None
        expected = normalize_executable_path(path)
        if expected in self._notepad_launchers:
            return "Microsoft.WindowsNotepad_8wekyb3d8bbwe"
        return None

    def package_family(self, pid):
        if self._get_package_family is None:
            return None
        handle = self._open_process(pid, PROCESS_QUERY_LIMITED_INFORMATION)
        try:
            # PACKAGE_FAMILY_NAME_MAX_LENGTH includes the terminating NUL.
            name = ctypes.create_unicode_buffer(65)
            size = wintypes.DWORD(len(name))
            status = self._get_package_family(handle, ctypes.byref(size), name)
            return name.value if status == 0 else None
        finally:
            self._close_handle(handle)

    def is_process_running(self, pid, expected_path):
        access = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        handle = self._open_process(pid, access)
        try:
            image_path = self._query_process_path_from_handle(handle)
            if normalize_executable_path(image_path) != normalize_executable_path(
                expected_path
            ):
                return False
            if self._process_identity(handle) != self.operator_identity:
                return False
            wait_result = self._wait_for_process(handle)
            if wait_result == WAIT_TIMEOUT:
                return True
            if wait_result == WAIT_OBJECT_0:
                return False
            raise self._error("WaitForSingleObject")
        finally:
            self._close_handle(handle)

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

    def _wait_for_process(self, handle):
        return int(self.kernel32.WaitForSingleObject(handle, 0))
