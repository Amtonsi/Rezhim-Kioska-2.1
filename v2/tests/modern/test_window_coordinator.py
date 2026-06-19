# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.window_coordinator import WindowCoordinator
from kiosk_v2_modern.platform.window_api import WindowsWindowApi


class FakeWindowApi(object):
    def __init__(self, windows=None, minimized=None):
        self.windows = dict(windows or {})
        self.minimized = set(minimized or set())
        self.restore_calls = []
        self.foreground_calls = []

    def windows_for_pid(self, pid):
        return list(self.windows.get(pid, []))

    def is_minimized(self, hwnd):
        return hwnd in self.minimized

    def restore_window(self, hwnd, maximized=False):
        self.restore_calls.append((hwnd, maximized))
        self.minimized.discard(hwnd)
        return True

    def bring_to_front(self, hwnd):
        self.foreground_calls.append(hwnd)
        return True


class FakeNativeWindowApi(object):
    def __init__(self):
        self.pids = {100: 10, 101: 10, 102: 11}
        self.visible = {100: True, 101: False, 102: True}
        self.iconic = {100: True, 101: False, 102: False}
        self.show_calls = []
        self.position_calls = []
        self.foreground_calls = []

    def enumerate_windows(self):
        return [100, 101, 102]

    def window_process_id(self, hwnd):
        return self.pids[hwnd]

    def is_window_visible(self, hwnd):
        return self.visible[hwnd]

    def is_iconic(self, hwnd):
        return self.iconic[hwnd]

    def show_window(self, hwnd, command):
        self.show_calls.append((hwnd, command))
        return True

    def position_at_top(self, hwnd):
        self.position_calls.append(hwnd)
        return True

    def set_foreground_window(self, hwnd):
        self.foreground_calls.append(hwnd)
        return True


class WindowCoordinatorTests(unittest.TestCase):
    def test_minimized_window_is_reported_without_restore(self):
        api = FakeWindowApi(windows={10: [100]}, minimized={100})
        coordinator = WindowCoordinator(api)

        result = coordinator.inspect(10)

        self.assertEqual("minimized", result.status)
        self.assertEqual(100, result.hwnd)
        self.assertEqual([], api.restore_calls)
        self.assertEqual([], api.foreground_calls)

    def test_restore_button_restores_existing_window_only(self):
        api = FakeWindowApi(windows={10: [100]}, minimized={100})
        coordinator = WindowCoordinator(api)

        result = coordinator.restore(10)

        self.assertTrue(result.succeeded)
        self.assertEqual("visible", result.status)
        self.assertEqual([(100, False)], api.restore_calls)
        self.assertEqual([100], api.foreground_calls)

    def test_restore_can_honor_start_maximized_setting(self):
        api = FakeWindowApi(windows={10: [100]}, minimized={100})
        coordinator = WindowCoordinator(api)

        result = coordinator.restore(10, maximized=True)

        self.assertTrue(result.succeeded)
        self.assertEqual([(100, True)], api.restore_calls)

    def test_admin_dialog_prevents_all_foreground_changes(self):
        api = FakeWindowApi(windows={10: [100]})
        coordinator = WindowCoordinator(api)

        result = coordinator.bring_to_front(10, admin_dialog_open=True)

        self.assertFalse(result.succeeded)
        self.assertEqual("suppressed", result.status)
        self.assertEqual([], api.restore_calls)
        self.assertEqual([], api.foreground_calls)

    def test_minimized_window_is_not_restored_by_background_activation(self):
        api = FakeWindowApi(windows={10: [100]}, minimized={100})
        coordinator = WindowCoordinator(api)

        result = coordinator.bring_to_front(10)

        self.assertFalse(result.succeeded)
        self.assertEqual("minimized", result.status)
        self.assertEqual([], api.restore_calls)
        self.assertEqual([], api.foreground_calls)

    def test_initial_activation_may_restore_window_before_operator_uses_it(self):
        api = FakeWindowApi(windows={10: [100]}, minimized={100})
        coordinator = WindowCoordinator(api)

        result = coordinator.activate_initial(10, maximized=True)

        self.assertTrue(result.succeeded)
        self.assertEqual([(100, True)], api.restore_calls)
        self.assertEqual([100], api.foreground_calls)

    def test_missing_window_is_reported_without_side_effects(self):
        api = FakeWindowApi(windows={})
        coordinator = WindowCoordinator(api)

        result = coordinator.inspect(10)

        self.assertEqual("no_window", result.status)
        self.assertFalse(result.succeeded)
        self.assertEqual([], api.restore_calls)
        self.assertEqual([], api.foreground_calls)

    def test_windows_adapter_filters_visible_top_level_windows_by_exact_pid(self):
        native = FakeNativeWindowApi()
        api = WindowsWindowApi(native=native)

        self.assertEqual([100], api.windows_for_pid(10))
        self.assertEqual([102], api.windows_for_pid(11))
        self.assertTrue(api.is_minimized(100))

    def test_windows_adapter_restores_and_activates_selected_window(self):
        native = FakeNativeWindowApi()
        api = WindowsWindowApi(native=native)

        restored = api.restore_window(100, maximized=True)
        activated = api.bring_to_front(100)

        self.assertTrue(restored)
        self.assertTrue(activated)
        self.assertEqual([(100, 3)], native.show_calls)
        self.assertEqual([100], native.position_calls)
        self.assertEqual([100], native.foreground_calls)


if __name__ == "__main__":
    unittest.main()
