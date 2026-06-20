# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import os
import sys
import threading
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.platform.desktop_isolation import (
    DesktopIsolation,
    NativeDesktopProcessApi,
    ProcessRecord,
    ShellSurface,
)
from kiosk_v2_legacy.platform.keyboard_guard import (
    KeyboardGuard,
    KeyboardState,
    NativeHookLoop,
    VK_CONTROL,
    VK_ESCAPE,
    VK_LWIN,
    VK_MENU,
    VK_SHIFT,
    VK_TAB,
    WM_KEYDOWN,
    WM_KEYUP,
)


class FakeDesktopApi(object):
    def __init__(self):
        self.current_session = 7
        self.processes = [
            ProcessRecord(10, r"C:\Windows\explorer.exe", 7),
            ProcessRecord(11, r"C:\Windows\explorer.exe", 8),
            ProcessRecord(12, r"C:\Windows\notepad.exe", 7),
        ]
        self.surfaces = [
            ShellSurface(100, "Shell_TrayWnd", 10, 7),
            ShellSurface(101, "Button", 10, 7),
            ShellSurface(102, "Progman", 11, 8),
            ShellSurface(103, "Button", 12, 7),
        ]
        self.failed_pids = set()
        self.terminate_calls = []
        self.hide_calls = []
        self.show_calls = []

    def current_session_id(self):
        return self.current_session

    def list_processes(self):
        return list(self.processes)

    def terminate_process(self, pid):
        self.terminate_calls.append(pid)
        return pid not in self.failed_pids

    def list_shell_surfaces(self):
        return list(self.surfaces)

    def hide_window(self, hwnd):
        self.hide_calls.append(hwnd)
        return True

    def show_window(self, hwnd):
        self.show_calls.append(hwnd)
        return True


class TrackingDesktopNative(NativeDesktopProcessApi):
    def __init__(self):
        self.closed = []
        self.error = None

    def _open_terminate_handle(self, pid):
        return 77

    def _terminate_handle(self, handle):
        if self.error is not None:
            raise self.error
        return True

    def _close_handle(self, handle):
        self.closed.append(handle)


class FakeHookNative(object):
    def __init__(self):
        self.callback = None
        self.hook_handle = 500
        self.thread_id = 77
        self.stop_event = threading.Event()
        self.uninstalled = []
        self.next_calls = []
        self.down = set()
        self.lock_calls = 0

    def create_callback(self, callback):
        self.callback = callback
        return callback

    def current_thread_id(self):
        return self.thread_id

    def install(self, callback):
        self.callback = callback
        return self.hook_handle

    def run_message_loop(self):
        self.stop_event.wait(2.0)

    def request_stop(self, thread_id):
        self.asserted_thread_id = thread_id
        self.stop_event.set()
        return True

    def uninstall(self, hook_handle):
        self.uninstalled.append(hook_handle)
        return True

    def keyboard_vk_code(self, raw_event):
        return int(raw_event)

    def call_next(self, hook_handle, n_code, message, raw_event):
        self.next_calls.append((hook_handle, n_code, message, raw_event))
        return 42

    def modifier_down(self, vk_code):
        return vk_code in self.down

    def lock_workstation(self):
        self.lock_calls += 1
        return True


class FakeHookLoop(object):
    def __init__(self):
        self.start_calls = 0
        self.stop_calls = 0
        self.running = False

    def start(self):
        self.start_calls += 1
        self.running = True

    def stop(self):
        self.stop_calls += 1
        self.running = False


class LegacySecurityGuardTests(unittest.TestCase):
    def test_desktop_guard_targets_only_current_session_explorer_and_surfaces(self):
        api = FakeDesktopApi()
        api.failed_pids.add(10)
        guard = DesktopIsolation(api)

        result = guard.start()

        self.assertEqual([10], api.terminate_calls)
        self.assertEqual((10,), result.failed_pids)
        self.assertEqual([100, 101], api.hide_calls)
        self.assertEqual((100, 101), result.hidden_hwnds)

    def test_desktop_guard_rechecks_and_stop_restores_only_hidden_surfaces(self):
        api = FakeDesktopApi()
        guard = DesktopIsolation(api)
        guard.start()
        api.processes = [ProcessRecord(20, r"C:\Windows\explorer.exe", 7)]
        api.surfaces = [ShellSurface(200, "Shell_TrayWnd", 20, 7)]

        guard.tick()
        guard.stop()

        self.assertEqual([10, 20], api.terminate_calls)
        self.assertEqual([100, 101, 200], api.show_calls)

    def test_native_desktop_termination_closes_handle_on_success_and_error(self):
        native = TrackingDesktopNative()
        self.assertTrue(native.terminate_process(10))
        self.assertEqual([77], native.closed)

        native.closed = []
        native.error = RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            native.terminate_process(10)
        self.assertEqual([77], native.closed)

    def test_desktop_source_has_no_mass_or_service_commands(self):
        source = inspect.getsource(
            sys.modules["kiosk_v2_legacy.platform.desktop_isolation"]
        ).lower()
        for forbidden in ("taskkill", "net stop", "sc stop", "kiosk_v2_modern"):
            self.assertNotIn(forbidden, source)

    def test_keyboard_blocks_escape_shortcuts_but_passes_text(self):
        state = KeyboardState()
        self.assertFalse(state.on_key(ord("A"), WM_KEYDOWN).blocked)
        state.on_key(VK_MENU, WM_KEYDOWN)
        self.assertTrue(state.on_key(VK_TAB, WM_KEYDOWN).blocked)
        state.reset()
        state.on_key(VK_CONTROL, WM_KEYDOWN)
        state.on_key(VK_MENU, WM_KEYDOWN)
        self.assertEqual(
            "Ctrl+Alt+Tab",
            state.on_key(VK_TAB, WM_KEYDOWN).shortcut,
        )
        state.reset()
        state.on_key(VK_CONTROL, WM_KEYDOWN)
        state.on_key(VK_SHIFT, WM_KEYDOWN)
        self.assertTrue(state.on_key(VK_ESCAPE, WM_KEYDOWN).blocked)

    def test_win_press_release_are_blocked_and_win_l_locks(self):
        locks = []
        state = KeyboardState(lock_workstation=lambda: locks.append(True))
        self.assertTrue(state.on_key(VK_LWIN, WM_KEYDOWN).blocked)
        self.assertEqual("Win+L", state.on_key(ord("L"), WM_KEYDOWN).shortcut)
        self.assertTrue(state.on_key(VK_LWIN, WM_KEYUP).blocked)
        self.assertEqual([True], locks)

    def test_native_hook_loop_passes_text_blocks_alt_tab_and_uninstalls(self):
        native = FakeHookNative()
        loop = NativeHookLoop(native=native)

        self.assertEqual(42, loop.dispatch_for_test(0, WM_KEYDOWN, ord("A")))
        native.down.add(VK_MENU)
        loop.dispatch_for_test(0, WM_KEYDOWN, VK_MENU)
        self.assertEqual(1, loop.dispatch_for_test(0, WM_KEYDOWN, VK_TAB))
        loop.start()
        loop.stop()

        self.assertEqual(77, native.asserted_thread_id)
        self.assertEqual([500], native.uninstalled)

    def test_keyboard_guard_stays_active_through_dialog_then_stops_on_success(self):
        hook = FakeHookLoop()
        guard = KeyboardGuard(hook)
        guard.start()

        guard.enter_admin_dialog()
        self.assertTrue(guard.running)
        self.assertEqual(0, hook.stop_calls)
        guard.authentication_succeeded()
        self.assertFalse(guard.running)
        guard.return_to_operator()
        self.assertTrue(guard.running)

    def test_dialog_restarts_guard_when_hook_loop_has_stopped(self):
        hook = FakeHookLoop()
        guard = KeyboardGuard(hook)
        guard.start()
        hook.running = False

        guard.enter_admin_dialog()

        self.assertTrue(guard.running)
        self.assertTrue(hook.running)
        self.assertEqual(2, hook.start_calls)
        self.assertEqual(0, hook.stop_calls)


if __name__ == "__main__":
    unittest.main()
