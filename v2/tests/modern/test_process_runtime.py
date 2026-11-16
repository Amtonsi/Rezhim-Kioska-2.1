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
    def broker_family_for_launcher(self, path):
        return None

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


class FakeHandoffNative(object):
    def broker_family_for_launcher(self, path):
        return None

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

    def broker_family_for_launcher(self, path):
        return "expected_family" if path == APP_PATH else None

    def package_family(self, pid):
        return "expected_family"

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


class TrackingNativeRuntime(NativeProcessRuntimeApi):
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

    def _query_process_path_from_handle(self, handle):
        if self.query_error is not None:
            raise self.query_error
        return self.path

    def _wait_for_process(self, handle):
        return self.wait_result

    def _close_handle(self, handle):
        self.closed.append(handle)


class ProcessRuntimeTests(unittest.TestCase):
    def setUp(self):
        FakePopen.next_pid = 100

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

    def test_finds_running_same_name_child_handoff_with_actual_runtime_path(self):
        runtime = WindowsProcessRuntime(
            native=FakeHandoffNative(),
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([200], [item.pid for item in found])
        self.assertEqual(FakeHandoffNative.HANDOFF_PATH, found[0].path)

    def test_finds_new_same_name_broker_process_outside_launcher_tree(self):
        native = FakeBrokerNative()
        runtime = WindowsProcessRuntime(
            native=native,
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        native.after_launch = True
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([301], [item.pid for item in found])
        self.assertEqual(FakeBrokerNative.NEW_PATH, found[0].path)

    def test_does_not_adopt_same_name_process_present_before_launch(self):
        native = FakeBrokerNative()
        runtime = WindowsProcessRuntime(
            native=native,
            popen_factory=PopenFactory(),
        )

        runtime.start(ApplicationSettings(APP_PATH))
        found = runtime.find_handoff(100, APP_PATH)

        self.assertEqual([], found)

    def test_process_with_same_basename_in_unrelated_directory_is_not_adopted(self):
        native = FakeBrokerNative()
        native.after_launch = True
        runtime = WindowsProcessRuntime(native=native, popen_factory=PopenFactory())
        self.assertEqual([], runtime.find_by_exact_path(APP_PATH))
        self.assertEqual([], runtime.find_handoff(999, APP_PATH))
        native.package_family = lambda pid: "unrelated_family"
        self.assertEqual([], runtime.find_existing_broker(APP_PATH))
        runtime.start(ApplicationSettings(APP_PATH))
        self.assertEqual([], runtime.find_handoff(100, APP_PATH))

    def test_broker_family_may_only_be_used_for_trusted_system_launcher(self):
        native = TrackingNativeRuntime()
        native._get_package_family = object()
        native._notepad_launchers = {r"c:\windows\system32\notepad.exe"}
        self.assertIsNone(native.broker_family_for_launcher(r"C:\Untrusted\notepad.exe"))
        self.assertEqual(
            "Microsoft.WindowsNotepad_8wekyb3d8bbwe",
            native.broker_family_for_launcher(r"C:\Windows\System32\notepad.exe"),
        )

    def test_liveness_requires_current_user_and_session(self):
        native = TrackingNativeRuntime()
        for other_identity in ((b"another_user", 1), (b"operator", 2)):
            native.candidate_identity = other_identity
            self.assertFalse(native.is_process_running(10, APP_PATH))
        self.assertEqual([88, 88], native.closed)

    def test_snapshot_failure_does_not_prevent_allowed_application_start(self):
        factory = PopenFactory()
        runtime = WindowsProcessRuntime(
            native=SnapshotFailingNative(),
            popen_factory=factory,
        )

        process = runtime.start(ApplicationSettings(APP_PATH))

        self.assertEqual(100, process.pid)
        self.assertEqual(1, len(factory.calls))

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
