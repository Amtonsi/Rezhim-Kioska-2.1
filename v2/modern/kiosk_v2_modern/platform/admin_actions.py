# -*- coding: utf-8 -*-
import ctypes
import os

from ctypes import wintypes


SW_SHOWNORMAL = 1
SEE_MASK_NOCLOSEPROCESS = 0x00000040
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", wintypes.LPVOID),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class AdminActionError(RuntimeError):
    def __init__(self, action, exit_code):
        self.action = action
        self.exit_code = int(exit_code)
        super(AdminActionError, self).__init__(
            "{0} failed with exit code {1}".format(action, exit_code)
        )


class AdminActionLauncher(object):
    def __init__(
        self,
        restore_executable,
        configurator_executable,
        api=None,
    ):
        self.restore_executable = restore_executable
        self.configurator_executable = configurator_executable
        self.api = api or NativeAdminActionApi()

    def run(self):
        directory = os.path.dirname(os.path.abspath(self.restore_executable))
        backup_path = os.path.join(directory, "state", "backup-v2.json")
        if os.path.isfile(backup_path):
            self._run_checked(self.restore_executable, "restore --apply")
        return True

    def change_application(self):
        self._run_checked(
            self.configurator_executable,
            "configure-application",
        )
        return True

    def _run_checked(self, executable, arguments):
        exit_code = self.api.run_elevated(executable, arguments)
        if exit_code is True:
            exit_code = 0
        if int(exit_code) != 0:
            raise AdminActionError(arguments.split(" ", 1)[0], exit_code)


class NativeAdminActionApi(object):
    def __init__(self, shell32=None, kernel32=None):
        self.shell32 = shell32 or ctypes.windll.shell32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.shell32.ShellExecuteExW.argtypes = [
            ctypes.POINTER(SHELLEXECUTEINFOW)
        ]
        self.shell32.ShellExecuteExW.restype = wintypes.BOOL
        self.kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def run_elevated(self, executable, arguments):
        info = SHELLEXECUTEINFOW()
        info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "runas"
        info.lpFile = executable
        info.lpParameters = arguments
        info.nShow = SW_SHOWNORMAL
        if not self.shell32.ShellExecuteExW(ctypes.byref(info)):
            raise OSError("ShellExecuteExW runas failed")
        if not info.hProcess:
            raise OSError("ShellExecuteExW did not return a process handle")
        try:
            wait_result = int(
                self.kernel32.WaitForSingleObject(info.hProcess, INFINITE)
            )
            if wait_result != WAIT_OBJECT_0:
                raise OSError("WaitForSingleObject failed")
            exit_code = wintypes.DWORD()
            if not self.kernel32.GetExitCodeProcess(
                info.hProcess,
                ctypes.byref(exit_code),
            ):
                raise OSError("GetExitCodeProcess failed")
            return int(exit_code.value)
        finally:
            self.kernel32.CloseHandle(info.hProcess)
