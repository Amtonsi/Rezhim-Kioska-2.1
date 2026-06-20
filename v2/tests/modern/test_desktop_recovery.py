# -*- coding: utf-8 -*-
import inspect
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform import desktop_recovery
from kiosk_v2_modern.platform.desktop_isolation import ProcessRecord, ShellSurface
from kiosk_v2_modern.platform.desktop_recovery import WindowsDesktopRecovery


class FakeProcessApi(object):
    def __init__(self, processes):
        self.processes = list(processes)

    def current_session_id(self):
        return 7

    def list_processes(self):
        return list(self.processes)


class FakeSurfaceApi(object):
    def __init__(self):
        self.shown = []

    def list_shell_surfaces(self):
        return [
            ShellSurface(100, "Shell_TrayWnd", 10, 7),
            ShellSurface(101, "Shell_TrayWnd", 11, 8),
        ]

    def show_window(self, hwnd):
        self.shown.append(hwnd)
        return True


class FakeLauncher(object):
    def __init__(self):
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)


class DesktopRecoveryTests(unittest.TestCase):
    def test_restores_only_current_session_shell_surfaces(self):
        surfaces = FakeSurfaceApi()
        recovery = WindowsDesktopRecovery(
            FakeProcessApi([]),
            surfaces,
            process_launcher=FakeLauncher(),
        )

        recovery.restore_shell_surfaces()

        self.assertEqual([100], surfaces.shown)

    def test_explorer_detection_requires_exact_name_and_current_session(self):
        recovery = WindowsDesktopRecovery(
            FakeProcessApi(
                [
                    ProcessRecord(10, r"C:\Windows\explorer.exe", 8),
                    ProcessRecord(11, r"C:\Tools\myexplorer.exe", 7),
                ]
            ),
            FakeSurfaceApi(),
            process_launcher=FakeLauncher(),
        )
        self.assertFalse(recovery.explorer_running())

        recovery.process_api.processes.append(
            ProcessRecord(12, r"C:\Windows\EXPLORER.EXE", 7)
        )
        self.assertTrue(recovery.explorer_running())

    def test_start_explorer_is_structured_and_skips_existing_instance(self):
        processes = FakeProcessApi([])
        launcher = FakeLauncher()
        recovery = WindowsDesktopRecovery(
            processes,
            FakeSurfaceApi(),
            process_launcher=launcher,
            explorer_path=r"C:\Windows\explorer.exe",
        )

        recovery.start_explorer()
        processes.processes.append(ProcessRecord(12, r"C:\Windows\explorer.exe", 7))
        recovery.start_explorer()

        self.assertEqual([[r"C:\Windows\explorer.exe"]], launcher.commands)

    def test_recovery_source_contains_no_termination_or_mass_process_logic(self):
        source = inspect.getsource(desktop_recovery).lower()
        self.assertNotIn("terminateprocess", source)
        self.assertNotIn("taskkill", source)
        self.assertNotIn("kill(", source)


if __name__ == "__main__":
    unittest.main()
