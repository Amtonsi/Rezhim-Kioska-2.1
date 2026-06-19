# -*- coding: utf-8 -*-
import subprocess

from ctypes import wintypes

from kiosk_v2_modern.app.process_supervisor import (
    ProcessRef,
    normalize_executable_path,
)
from kiosk_v2_modern.platform.desktop_isolation import (
    NativeProcessApi,
    PROCESS_QUERY_LIMITED_INFORMATION,
)


SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102


class WindowsProcessRuntime(object):
    def __init__(self, native=None, popen_factory=None):
        self.native = native or NativeProcessRuntimeApi()
        self.popen_factory = popen_factory or subprocess.Popen
        self._started_processes = {}

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

    def start(self, application_settings):
        command = [application_settings.path]
        command.extend(application_settings.arguments)
        working_directory = application_settings.working_directory or None
        process = self.popen_factory(
            command,
            cwd=working_directory,
            shell=False,
        )
        self._started_processes[int(process.pid)] = process
        return ProcessRef(process.pid, application_settings.path, True)

    def is_running(self, pid, expected_path):
        try:
            running = bool(self.native.is_process_running(pid, expected_path))
        except (OSError, RuntimeError):
            running = False
        if not running:
            self._started_processes.pop(int(pid), None)
        return running


class NativeProcessRuntimeApi(NativeProcessApi):
    def _configure_signatures(self):
        super(NativeProcessRuntimeApi, self)._configure_signatures()
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD

    def is_process_running(self, pid, expected_path):
        access = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        handle = self._open_process(pid, access)
        try:
            image_path = self._query_process_path_from_handle(handle)
            if normalize_executable_path(image_path) != normalize_executable_path(
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

    def _wait_for_process(self, handle):
        return int(self.kernel32.WaitForSingleObject(handle, 0))
