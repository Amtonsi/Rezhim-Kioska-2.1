# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.process_supervisor import ApplicationSettings
from kiosk_v2_legacy.app.window_coordinator import WindowCoordinator
from kiosk_v2_legacy.platform.process_runtime import (
    LegacyProcessRuntime,
    NativeLegacyProcessApi,
)
from kiosk_v2_legacy.platform.window_api import LegacyWindowApi


APP_PATH = r"C:\Program Files\Vendor\Allowed.exe"


class FakeProcessNative(object):
    def __init__(self):
        self.paths = {
            10: r"c:/program files/vendor/ALLOWED.exe",
            11: r"C:\Windows\notepad.exe",
            12: APP_PATH,
        }
        self.running = {10: True, 11: True, 12: False}
        self.queries = []
        self.checks = []

    def process_ids(self):
        return [10, 11, 12, 13]

    def query_image_path(self, pid):
        self.queries.append(pid)
        if pid == 13:
            raise OSError("gone")
        return self.paths[pid]

    def is_process_running(self, pid, expected_path):
        self.checks.append((pid, expected_path))
        return self.running.get(pid, False)


class FakeHandoffNative(object):
    HANDOFF_PATH = r"C:\Program Files\WindowsApps\Vendor_1.0\Allowed.exe"

    def process_parent_map(self):
        return {200: 100, 201: 100, 202: 999}

    def query_image_path(self, pid):
        return {
            200: self.HANDOFF_PATH,
            201: r"C:\Program Files\WindowsApps\Vendor_1.0\Helper.exe",
            202: self.HANDOFF_PATH,
        }[pid]

    def is_process_running(self, pid, expected_path):
        return pid == 200 and expected_path == self.HANDOFF_PATH


class FakeBrokerNative(object):
    EXISTING_PATH = r"C:\Program Files\WindowsApps\Vendor_1.0\Allowed.exe"
    NEW_PATH = r"C:\Program Files\WindowsApps\Vendor_2.0\Allowed.exe"

    def __init__(self):
        self.after_launch = False

    def process_ids(self):
        if self.after_launch:
            return [300, 301]
        return [300]

    def process_parent_map(self):
        return {300: 999, 301: 999}

    def query_image_path(self, pid):
        return {
            300: self.EXISTING_PATH,
            301: self.NEW_PATH,
        }[pid]

    def is_process_running(self, pid, expected_path):
        return expected_path == self.query_image_path(pid)


class SnapshotFailingNative(FakeBrokerNative):
    def process_ids(self):
        raise OSError("snapshot unavailable")


class FakePopen(object):
    next_pid = 100

    def __init__(self, command, cwd=None, shell=False):
        self.command = list(command)
        self.cwd = cwd
        self.shell = shell
        self.pid = FakePopen.next_pid
        FakePopen.next_pid += 1


class PopenFactory(object):
    def __init__(self):
        self.calls = []

    def __call__(self, command, cwd=None, shell=False):
        process = FakePopen(command, cwd=cwd, shell=shell)
        self.calls.append(process)
        return process


class TrackingProcessNative(NativeLegacyProcessApi):
    def __init__(self):
        self.closed = []
        self.operator_identity = (b"operator", 1)
        self.candidate_identity = self.operator_identity
        self.path = APP_PATH
        self.wait_result = 0x00000102
        self.query_error = None

    def _process_identity(self, handle):
        return self.candidate_identity

    def _open_process(self, pid, access):
        return 88

    def _query_path_from_handle(self, handle):
        if self.query_error is not None:
            raise self.query_error
        return self.path

    def _wait_for_process(self, handle):
        return self.wait_result

    def _close_handle(self, handle):
        self.closed.append(handle)


class FakeWindowApi(object):
    def __init__(self):
        self.windows = {10: [100]}
        self.minimized = set([100])
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


class FakeWindowNative(object):
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


class LegacyProcessWindowRuntimeTests(unittest.TestCase):
    def setUp(self):
        FakePopen.next_pid = 100

    def test_process_runtime_filters_exact_full_path_and_liveness(self):
        native = FakeProcessNative()
        runtime = LegacyProcessRuntime(native=native, popen_factory=PopenFactory())

        found = runtime.find_by_exact_path(APP_PATH)

        self.assertEqual([10], [item.pid for item in found])
        self.assertEqual([10, 11, 12, 13], native.queries)
        self.assertEqual([(10, APP_PATH), (12, APP_PATH)], native.checks)

    def test_process_runtime_starts_structured_command_once_without_shell(self):
        factory = PopenFactory()
        runtime = LegacyProcessRuntime(native=FakeProcessNative(), popen_factory=factory)
        settings = ApplicationSettings(
            APP_PATH,
            arguments=("--profile", "Operator One"),
            working_directory=r"C:\Program Files\Vendor",
        )

        process = runtime.start(settings)

        self.assertEqual(100, process.pid)
        self.assertEqual(1, len(factory.calls))
        self.assertEqual([APP_PATH, "--profile", "Operator One"], factory.calls[0].command)
        self.assertFalse(factory.calls[0].shell)

    def test_finds_running_same_name_child_handoff_with_actual_runtime_path(self):
        runtime = LegacyProcessRuntime(
            native=FakeHandoffNative(),
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([200], [item.pid for item in found])
        self.assertEqual(FakeHandoffNative.HANDOFF_PATH, found[0].path)

    def test_rejects_unrelated_new_same_name_process(self):
        native = FakeBrokerNative()
        runtime = LegacyProcessRuntime(
            native=native,
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        native.after_launch = True
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([], found)

    def test_does_not_adopt_same_name_process_present_before_launch(self):
        native = FakeBrokerNative()
        runtime = LegacyProcessRuntime(
            native=native,
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([], found)

    def test_process_with_same_basename_in_unrelated_directory_is_not_adopted(self):
        native = FakeBrokerNative()
        native.after_launch = True
        runtime = LegacyProcessRuntime(native=native, popen_factory=PopenFactory())
        self.assertEqual([], runtime.find_by_exact_path(APP_PATH))
        self.assertEqual([], runtime.find_handoff(999, APP_PATH))

    def test_liveness_requires_current_user_and_session(self):
        native = TrackingProcessNative()
        for other_identity in ((b"another_user", 1), (b"operator", 2)):
            native.candidate_identity = other_identity
            self.assertFalse(native.is_process_running(10, APP_PATH))
        self.assertEqual([88, 88], native.closed)

    def test_snapshot_failure_does_not_prevent_allowed_application_start(self):
        factory = PopenFactory()
        runtime = LegacyProcessRuntime(
            native=SnapshotFailingNative(),
            popen_factory=factory,
        )

        process = runtime.start(ApplicationSettings(APP_PATH))

        self.assertEqual(100, process.pid)
        self.assertEqual(1, len(factory.calls))

    def test_native_process_query_and_liveness_always_close_handle(self):
        native = TrackingProcessNative()

        self.assertEqual(APP_PATH, native.query_image_path(10))
        self.assertEqual([88], native.closed)
        native.closed = []
        self.assertTrue(native.is_process_running(10, APP_PATH))
        self.assertEqual([88], native.closed)
        native.closed = []
        native.query_error = RuntimeError("query failed")
        with self.assertRaises(RuntimeError):
            native.is_process_running(10, APP_PATH)
        self.assertEqual([88], native.closed)

    def test_legacy_process_source_uses_psapi_not_modern_or_termination_api(self):
        source = inspect.getsource(
            sys.modules["kiosk_v2_legacy.platform.process_runtime"]
        ).lower()

        self.assertIn("getmodulefilenameexw", source)
        self.assertNotIn("queryfullprocessimagenamew", source)
        self.assertNotIn("terminateprocess", source)
        self.assertNotIn("kiosk_v2_modern", source)

    def test_minimized_window_is_only_reported_until_explicit_restore(self):
        api = FakeWindowApi()
        coordinator = WindowCoordinator(api)

        minimized = coordinator.inspect(10)
        self.assertEqual("minimized", minimized.status)
        self.assertEqual([], api.restore_calls)

        restored = coordinator.restore(10)
        self.assertTrue(restored.succeeded)
        self.assertEqual([(100, False)], api.restore_calls)
        self.assertEqual([100], api.foreground_calls)

    def test_admin_dialog_suppresses_foreground_and_restore(self):
        api = FakeWindowApi()
        coordinator = WindowCoordinator(api)

        result = coordinator.restore(10, admin_dialog_open=True)

        self.assertEqual("suppressed", result.status)
        self.assertEqual([], api.restore_calls)
        self.assertEqual([], api.foreground_calls)

    def test_window_adapter_filters_visible_windows_by_pid(self):
        native = FakeWindowNative()
        api = LegacyWindowApi(native=native)

        self.assertEqual([100], api.windows_for_pid(10))
        self.assertTrue(api.is_minimized(100))
        self.assertTrue(api.restore_window(100, maximized=True))
        self.assertTrue(api.bring_to_front(100))
        self.assertEqual([(100, 3)], native.show_calls)
        self.assertEqual([100], native.position_calls)
        self.assertEqual([100], native.foreground_calls)


if __name__ == "__main__":
    unittest.main()
