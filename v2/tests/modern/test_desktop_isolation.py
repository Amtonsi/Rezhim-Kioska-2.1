# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.desktop_isolation import (
    DesktopIsolation,
    NativeProcessApi,
    ProcessRecord,
    WindowsProcessApi,
)


class FakeProcessApi(object):
    def __init__(self, current_session, processes):
        self.current_session = current_session
        self.processes = list(processes)
        self.terminated = []
        self.failed_pids = set()

    def current_session_id(self):
        return self.current_session

    def list_processes(self):
        return list(self.processes)

    def terminate_process(self, pid):
        self.terminated.append(pid)
        return pid not in self.failed_pids


class FakeNativeProcessApi(object):
    def __init__(self):
        self.terminated = []

    def current_process_id(self):
        return 900

    def process_ids(self):
        return [10, 11]

    def process_session_id(self, pid):
        return {900: 7, 10: 7, 11: 8}[pid]

    def query_image_path(self, pid):
        return {
            10: r"C:\Windows\explorer.exe",
            11: r"C:\Windows\notepad.exe",
        }[pid]

    def terminate_process(self, pid):
        self.terminated.append(pid)
        return True


class TrackingNativeProcessApi(NativeProcessApi):
    def __init__(self):
        self.closed = []
        self.query_error = None
        self.terminate_error = None

    def _open_process(self, pid, access):
        return 99

    def _query_process_path_from_handle(self, handle):
        if self.query_error is not None:
            raise self.query_error
        return r"C:\Windows\explorer.exe"

    def _terminate_process_handle(self, handle):
        if self.terminate_error is not None:
            raise self.terminate_error
        return True

    def _close_handle(self, handle):
        self.closed.append(handle)


class DesktopIsolationTests(unittest.TestCase):
    def test_guard_terminates_every_explorer_only_in_operator_session(self):
        api = FakeProcessApi(
            current_session=7,
            processes=[
                ProcessRecord(10, r"C:\Windows\explorer.exe", 7),
                ProcessRecord(11, r"C:\Windows\explorer.exe", 8),
                ProcessRecord(12, r"C:\Windows\notepad.exe", 7),
                ProcessRecord(13, r"C:\Windows\EXPLORER.EXE", 7),
            ],
        )
        guard = DesktopIsolation(api)

        result = guard.enforce()

        self.assertEqual([10, 13], api.terminated)
        self.assertEqual((10, 13), result.terminated_pids)
        self.assertEqual((), result.failed_pids)

    def test_guard_rechecks_and_terminates_restarted_operator_explorer(self):
        api = FakeProcessApi(current_session=7, processes=[])
        guard = DesktopIsolation(api)
        guard.start()
        api.processes = [ProcessRecord(20, r"C:\Windows\explorer.exe", 7)]

        result = guard.tick()

        self.assertEqual([20], api.terminated)
        self.assertEqual((20,), result.terminated_pids)

    def test_stopped_guard_never_terminates_explorer(self):
        api = FakeProcessApi(
            current_session=7,
            processes=[ProcessRecord(30, r"C:\Windows\explorer.exe", 7)],
        )
        guard = DesktopIsolation(api)

        guard.stop()
        result = guard.tick()

        self.assertEqual([], api.terminated)
        self.assertEqual((), result.terminated_pids)

    def test_reports_exact_pid_failure_without_touching_other_processes(self):
        api = FakeProcessApi(
            current_session=7,
            processes=[
                ProcessRecord(40, r"C:\Windows\explorer.exe", 7),
                ProcessRecord(41, r"C:\Windows\cmd.exe", 7),
            ],
        )
        api.failed_pids.add(40)
        guard = DesktopIsolation(api)

        result = guard.enforce()

        self.assertEqual([40], api.terminated)
        self.assertEqual((), result.terminated_pids)
        self.assertEqual((40,), result.failed_pids)

    def test_windows_adapter_builds_records_and_terminates_exact_pid(self):
        native = FakeNativeProcessApi()
        api = WindowsProcessApi(native=native)

        records = api.list_processes()
        terminated = api.terminate_process(10)

        self.assertEqual(7, api.current_session_id())
        self.assertEqual([10, 11], [item.pid for item in records])
        self.assertEqual([7, 8], [item.session_id for item in records])
        self.assertTrue(terminated)
        self.assertEqual([10], native.terminated)

    def test_native_query_closes_handle_on_success_and_error(self):
        native = TrackingNativeProcessApi()

        self.assertEqual(r"C:\Windows\explorer.exe", native.query_image_path(10))
        self.assertEqual([99], native.closed)

        native.closed = []
        native.query_error = RuntimeError("query failed")
        with self.assertRaises(RuntimeError):
            native.query_image_path(10)
        self.assertEqual([99], native.closed)

    def test_native_termination_closes_handle_on_success_and_error(self):
        native = TrackingNativeProcessApi()

        self.assertTrue(native.terminate_process(10))
        self.assertEqual([99], native.closed)

        native.closed = []
        native.terminate_error = RuntimeError("terminate failed")
        with self.assertRaises(RuntimeError):
            native.terminate_process(10)
        self.assertEqual([99], native.closed)


if __name__ == "__main__":
    unittest.main()
