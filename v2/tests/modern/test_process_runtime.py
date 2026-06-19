# -*- coding: utf-8 -*-
import inspect
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.process_supervisor import ApplicationSettings
from kiosk_v2_modern.platform.process_runtime import (
    NativeProcessRuntimeApi,
    WindowsProcessRuntime,
)


APP_PATH = r"C:\Program Files\Vendor\Allowed.exe"


class FakeNativeApi(object):
    def __init__(self):
        self.paths = {
            10: r"c:/program files/vendor/ALLOWED.exe",
            11: r"C:\Windows\System32\notepad.exe",
            12: APP_PATH,
        }
        self.running = {10: True, 11: True, 12: False}
        self.queries = []
        self.liveness_checks = []

    def process_ids(self):
        return [10, 11, 12, 13]

    def query_image_path(self, pid):
        self.queries.append(pid)
        if pid == 13:
            raise OSError("process exited")
        return self.paths[pid]

    def is_process_running(self, pid, expected_path):
        self.liveness_checks.append((pid, expected_path))
        return self.running.get(pid, False)


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


class TrackingNativeRuntime(NativeProcessRuntimeApi):
    def __init__(self):
        self.closed = []
        self.path = APP_PATH
        self.wait_result = 0x00000102
        self.query_error = None

    def _open_process(self, pid, access):
        return 88

    def _query_process_path_from_handle(self, handle):
        if self.query_error is not None:
            raise self.query_error
        return self.path

    def _wait_for_process(self, handle):
        return self.wait_result

    def _close_handle(self, handle):
        self.closed.append(handle)


class ProcessRuntimeTests(unittest.TestCase):
    def test_finds_only_running_processes_with_exact_normalized_full_path(self):
        native = FakeNativeApi()
        runtime = WindowsProcessRuntime(native=native, popen_factory=PopenFactory())

        found = runtime.find_by_exact_path(APP_PATH)

        self.assertEqual([10], [item.pid for item in found])
        self.assertEqual([10, 11, 12, 13], native.queries)
        self.assertEqual([(10, APP_PATH), (12, APP_PATH)], native.liveness_checks)

    def test_start_forwards_structured_arguments_and_working_directory_once(self):
        native = FakeNativeApi()
        factory = PopenFactory()
        runtime = WindowsProcessRuntime(native=native, popen_factory=factory)
        application = ApplicationSettings(
            path=APP_PATH,
            arguments=("--mode", "operator value"),
            working_directory=r"C:\Program Files\Vendor",
        )

        process = runtime.start(application)

        self.assertEqual(100, process.pid)
        self.assertEqual(1, len(factory.calls))
        self.assertEqual(
            [APP_PATH, "--mode", "operator value"],
            factory.calls[0].command,
        )
        self.assertEqual(r"C:\Program Files\Vendor", factory.calls[0].cwd)
        self.assertFalse(factory.calls[0].shell)

    def test_runtime_rechecks_path_when_reporting_liveness(self):
        native = FakeNativeApi()
        runtime = WindowsProcessRuntime(native=native, popen_factory=PopenFactory())

        self.assertTrue(runtime.is_running(10, APP_PATH))
        self.assertEqual([(10, APP_PATH)], native.liveness_checks)

    def test_runtime_maps_query_failures_to_not_running(self):
        class FailingNative(FakeNativeApi):
            def is_process_running(self, pid, expected_path):
                raise OSError("access denied")

        runtime = WindowsProcessRuntime(
            native=FailingNative(), popen_factory=PopenFactory()
        )

        self.assertFalse(runtime.is_running(10, APP_PATH))

    def test_native_liveness_closes_handle_on_success_mismatch_and_error(self):
        native = TrackingNativeRuntime()

        self.assertTrue(native.is_process_running(10, APP_PATH))
        self.assertEqual([88], native.closed)

        native.closed = []
        native.path = r"C:\Windows\System32\notepad.exe"
        self.assertFalse(native.is_process_running(10, APP_PATH))
        self.assertEqual([88], native.closed)

        native.closed = []
        native.query_error = RuntimeError("query failed")
        with self.assertRaises(RuntimeError):
            native.is_process_running(10, APP_PATH)
        self.assertEqual([88], native.closed)

    def test_native_reports_exited_process(self):
        native = TrackingNativeRuntime()
        native.wait_result = 0x00000000

        self.assertFalse(native.is_process_running(10, APP_PATH))
        self.assertEqual([88], native.closed)

    def test_runtime_has_no_process_termination_primitive(self):
        source = inspect.getsource(
            sys.modules["kiosk_v2_modern.platform.process_runtime"]
        ).lower()

        self.assertNotIn("terminateprocess", source)
        self.assertNotIn("taskkill", source)
        self.assertFalse(hasattr(WindowsProcessRuntime, "terminate"))


if __name__ == "__main__":
    unittest.main()
