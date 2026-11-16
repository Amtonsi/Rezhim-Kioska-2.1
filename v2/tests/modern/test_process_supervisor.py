# -*- coding: utf-8 -*-
import ntpath
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.process_supervisor import (
    ApplicationSettings,
    ProcessRef,
    ProcessSupervisor,
)


APP_PATH = r"C:\Program Files\Vendor\Allowed.exe"


def normalize(path):
    return ntpath.normcase(ntpath.normpath(path))


def settings(**overrides):
    values = {
        "path": APP_PATH,
        "arguments": ("--mode", "operator"),
        "working_directory": r"C:\Program Files\Vendor",
        "restart_on_exit": True,
        "restart_delay_ms": 2000,
        "single_instance": True,
        "max_restart_attempts": 5,
        "restart_window_seconds": 30,
    }
    values.update(overrides)
    return ApplicationSettings(**values)


class FakeClock(object):
    def __init__(self, value=0.0):
        self.value = value

    def monotonic(self):
        return self.value


class FakeProcessApi(object):
    def __init__(self, existing=None):
        self.existing = list(existing or [])
        self.running = dict((item.pid, item.running) for item in self.existing)
        self.paths = dict((item.pid, item.path) for item in self.existing)
        self.start_calls = []
        self.terminate_calls = []
        self.start_errors = []
        self.next_pid = 100

    def find_by_exact_path(self, path):
        expected = normalize(path)
        return [
            ProcessRef(item.pid, item.path, self.running.get(item.pid, False))
            for item in self.existing
            if normalize(item.path) == expected
        ]

    def find_handoff(self, parent_pid, path):
        return []

    def start(self, application_settings):
        self.start_calls.append(application_settings)
        if self.start_errors:
            raise self.start_errors.pop(0)
        process = ProcessRef(self.next_pid, application_settings.path, True)
        self.next_pid += 1
        self.existing.append(process)
        self.running[process.pid] = True
        self.paths[process.pid] = process.path
        return process

    def is_running(self, pid, expected_path):
        return self.running.get(pid, False) and (
            normalize(self.paths.get(pid, "")) == normalize(expected_path)
        )

    def terminate(self, pid):
        self.terminate_calls.append(pid)
        self.running[pid] = False


class HandOffProcessApi(FakeProcessApi):
    def __init__(self, handoff_pid=200):
        super(HandOffProcessApi, self).__init__(existing=[])
        self.handoff_pid = handoff_pid

    def start(self, application_settings):
        self.start_calls.append(application_settings)
        launcher_pid = self.next_pid
        self.next_pid += 1
        launcher = ProcessRef(launcher_pid, application_settings.path, False)
        self.existing.append(launcher)
        self.running[launcher.pid] = False
        self.paths[launcher.pid] = launcher.path

        handoff = ProcessRef(self.handoff_pid, application_settings.path, True)
        self.existing.append(handoff)
        self.running[handoff.pid] = True
        self.paths[handoff.pid] = handoff.path
        return launcher


class DelayedDifferentPathHandoffApi(FakeProcessApi):
    HANDOFF_PATH = (
        r"C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_1.0_x64"
        r"\Notepad\Notepad.exe"
    )

    def __init__(self, handoff_pid=250):
        super(DelayedDifferentPathHandoffApi, self).__init__(existing=[])
        self.handoff_pid = handoff_pid
        self.handoff_ready = False
        self.launcher_pid = None
        self.cleared_handoffs = []

    def start(self, application_settings):
        self.start_calls.append(application_settings)
        self.launcher_pid = self.next_pid
        self.next_pid += 1
        self.running[self.launcher_pid] = False
        self.paths[self.launcher_pid] = application_settings.path
        return ProcessRef(self.launcher_pid, application_settings.path, False)

    def find_handoff(self, parent_pid, path):
        if not self.handoff_ready or parent_pid != self.launcher_pid:
            return []
        self.running[self.handoff_pid] = True
        self.paths[self.handoff_pid] = self.HANDOFF_PATH
        return [ProcessRef(self.handoff_pid, self.HANDOFF_PATH, True)]

    def clear_handoff(self, parent_pid):
        self.cleared_handoffs.append(parent_pid)


class ExistingNameHandoffApi(FakeProcessApi):
    HANDOFF_PATH = (
        r"C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_1.0_x64"
        r"\Notepad\Notepad.exe"
    )

    def __init__(self, handoff_pid=250):
        super(ExistingNameHandoffApi, self).__init__(existing=[])
        self.handoff_pid = handoff_pid
        self.find_by_name_calls = 0
        self.running[handoff_pid] = True
        self.paths[handoff_pid] = self.HANDOFF_PATH

    def find_existing_broker(self, path):
        self.find_by_name_calls += 1
        return [ProcessRef(self.handoff_pid, self.HANDOFF_PATH, True)]


class RunningThenHandoffApi(DelayedDifferentPathHandoffApi):
    def start(self, application_settings):
        process = super(RunningThenHandoffApi, self).start(application_settings)
        process.running = True
        self.running[process.pid] = True
        return process


class TemporarilyFailingHandoffApi(DelayedDifferentPathHandoffApi):
    def __init__(self):
        super(TemporarilyFailingHandoffApi, self).__init__()
        self.handoff_checks = 0

    def find_handoff(self, parent_pid, path):
        self.handoff_checks += 1
        if self.handoff_checks == 1:
            return []
        raise OSError("snapshot temporarily unavailable")


class ProcessSupervisorTests(unittest.TestCase):
    def test_tracks_wow64_redirected_image_but_launches_configured_name(self):
        configured = r"C:\Windows\System32\notepad.exe"
        physical = r"C:\Windows\SysWOW64\notepad.exe"

        class RedirectedApi(FakeProcessApi):
            def resolve_configured_path(self, path):
                return physical

            def start(self, application):
                process = super(RedirectedApi, self).start(application)
                self.paths[process.pid] = physical
                self.existing[0].path = physical
                return ProcessRef(process.pid, configured, True)

        api = RedirectedApi(existing=[])
        supervisor = ProcessSupervisor(settings(path=configured), api, FakeClock())
        self.assertEqual("started", supervisor.start().status)
        self.assertEqual("running", supervisor.tick().status)
        self.assertEqual(configured, api.start_calls[0].path)
        second = ProcessSupervisor(settings(path=configured), api, FakeClock())
        self.assertEqual("adopted", second.start().status)
        self.assertEqual(1, len(api.start_calls))

    def test_adopts_one_existing_exact_path_process_without_starting_duplicate(self):
        existing = ProcessRef(10, r"c:/program files/vendor/ALLOWED.exe", True)
        api = FakeProcessApi(existing=[existing])
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        result = supervisor.start()

        self.assertEqual("adopted", result.status)
        self.assertEqual(10, result.pid)
        self.assertEqual([], api.start_calls)

    def test_starts_exactly_once_when_no_matching_process_exists(self):
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        first = supervisor.start()
        second = supervisor.start()

        self.assertEqual("started", first.status)
        self.assertEqual("running", second.status)
        self.assertEqual(first.pid, second.pid)
        self.assertEqual(1, len(api.start_calls))

    def test_restarts_once_after_delay_when_process_exits(self):
        clock = FakeClock(100.0)
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(settings(restart_delay_ms=2000), api, clock)
        first = supervisor.start()
        api.running[first.pid] = False

        waiting = supervisor.tick()
        clock.value = 101.9
        still_waiting = supervisor.tick()
        clock.value = 102.1
        restarted = supervisor.tick()

        self.assertEqual("waiting_restart", waiting.status)
        self.assertEqual("waiting_restart", still_waiting.status)
        self.assertEqual("restarted", restarted.status)
        self.assertNotEqual(first.pid, restarted.pid)
        self.assertEqual(2, len(api.start_calls))

    def test_adopts_handoff_process_when_launcher_pid_exits_immediately(self):
        api = HandOffProcessApi(handoff_pid=250)
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        result = supervisor.start()

        self.assertEqual("adopted", result.status)
        self.assertEqual(250, result.pid)
        self.assertEqual(1, len(api.start_calls))
        self.assertEqual(0, result.failure_count)

    def test_restart_adopts_existing_handoff_before_opening_duplicate(self):
        clock = FakeClock(10.0)
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(settings(restart_delay_ms=1000), api, clock)
        first = supervisor.start()
        api.running[first.pid] = False
        handoff = ProcessRef(250, APP_PATH, True)
        api.existing.append(handoff)
        api.running[250] = True
        api.paths[250] = APP_PATH

        adopted = supervisor.tick()

        self.assertEqual("adopted", adopted.status)
        self.assertEqual(250, adopted.pid)
        self.assertEqual(1, len(api.start_calls))

    def test_waits_for_delayed_different_path_handoff_without_duplicate_launch(self):
        clock = FakeClock(10.0)
        api = DelayedDifferentPathHandoffApi(handoff_pid=250)
        supervisor = ProcessSupervisor(settings(), api, clock)

        waiting = supervisor.start()
        api.handoff_ready = True
        adopted = supervisor.tick()
        running = supervisor.tick()

        self.assertEqual("waiting_handoff", waiting.status)
        self.assertEqual("adopted", adopted.status)
        self.assertEqual(250, adopted.pid)
        self.assertEqual("running", running.status)
        self.assertEqual(1, len(api.start_calls))
        self.assertEqual([api.launcher_pid], api.cleared_handoffs)

    def test_adopts_existing_same_name_broker_process_without_duplicate_launch(self):
        api = ExistingNameHandoffApi(handoff_pid=250)
        supervisor = ProcessSupervisor(
            settings(path=r"C:\Windows\System32\notepad.exe"),
            api,
            FakeClock(),
        )

        result = supervisor.start()
        again = supervisor.start()

        self.assertEqual("adopted", result.status)
        self.assertEqual(250, result.pid)
        self.assertEqual("running", again.status)
        self.assertEqual([], api.start_calls)
        self.assertEqual(1, api.find_by_name_calls)

    def test_short_lived_launcher_is_replaced_by_its_handoff_child(self):
        api = RunningThenHandoffApi(handoff_pid=260)
        supervisor = ProcessSupervisor(settings(), api, FakeClock())
        started = supervisor.start()
        api.running[started.pid] = False
        api.handoff_ready = True

        adopted = supervisor.tick()

        self.assertEqual("adopted", adopted.status)
        self.assertEqual(260, adopted.pid)
        self.assertEqual(1, len(api.start_calls))

    def test_temporary_handoff_discovery_error_does_not_crash_tick(self):
        api = TemporarilyFailingHandoffApi()
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        self.assertEqual("waiting_handoff", supervisor.start().status)
        result = supervisor.tick()

        self.assertEqual("waiting_handoff", result.status)
        self.assertEqual(1, len(api.start_calls))

    def test_alive_process_is_not_reopened(self):
        api = FakeProcessApi(existing=[ProcessRef(10, APP_PATH, True)])
        supervisor = ProcessSupervisor(settings(), api, FakeClock())
        supervisor.start()

        result = supervisor.tick()

        self.assertEqual("running", result.status)
        self.assertEqual(10, result.pid)
        self.assertEqual([], api.start_calls)

    def test_disabled_restart_stops_after_observed_exit(self):
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(
            settings(restart_on_exit=False), api, FakeClock()
        )
        first = supervisor.start()
        api.running[first.pid] = False

        result = supervisor.tick()

        self.assertEqual("stopped", result.status)
        self.assertIsNone(result.pid)
        self.assertEqual(1, len(api.start_calls))

    def test_failed_start_waits_before_retrying(self):
        clock = FakeClock(50.0)
        api = FakeProcessApi(existing=[])
        api.start_errors.append(OSError("start failed"))
        supervisor = ProcessSupervisor(settings(restart_delay_ms=1000), api, clock)

        failed = supervisor.start()
        clock.value = 50.5
        waiting = supervisor.tick()
        clock.value = 51.1
        restarted = supervisor.tick()

        self.assertEqual("start_failed", failed.status)
        self.assertEqual("OSError", failed.error_code)
        self.assertEqual("waiting_restart", waiting.status)
        self.assertEqual("restarted", restarted.status)
        self.assertEqual(2, len(api.start_calls))

    def test_multiple_existing_instances_report_conflict_without_new_launch(self):
        api = FakeProcessApi(
            existing=[
                ProcessRef(10, APP_PATH, True),
                ProcessRef(11, APP_PATH.lower(), True),
            ]
        )
        supervisor = ProcessSupervisor(settings(single_instance=True), api, FakeClock())

        result = supervisor.start()

        self.assertEqual("conflict", result.status)
        self.assertEqual((10, 11), result.conflict_pids)
        self.assertEqual([], api.start_calls)

    def test_stop_supervision_never_terminates_application_and_restart_adopts_it(self):
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(settings(), api, FakeClock())
        started = supervisor.start()

        stopped = supervisor.stop_supervision()
        resumed = supervisor.start()

        self.assertEqual("stopped", stopped.status)
        self.assertTrue(api.running[started.pid])
        self.assertEqual([], api.terminate_calls)
        self.assertEqual("adopted", resumed.status)
        self.assertEqual(started.pid, resumed.pid)
        self.assertEqual(1, len(api.start_calls))

    def test_pid_reuse_with_different_path_is_treated_as_exit(self):
        clock = FakeClock(10.0)
        api = FakeProcessApi(existing=[ProcessRef(10, APP_PATH, True)])
        supervisor = ProcessSupervisor(settings(restart_delay_ms=1000), api, clock)
        supervisor.start()
        api.paths[10] = r"C:\Windows\System32\notepad.exe"

        result = supervisor.tick()

        self.assertEqual("waiting_restart", result.status)
        self.assertIsNone(result.pid)
        self.assertEqual(10, result.previous_pid)

    def test_rapid_exits_open_circuit_and_prevent_further_launch(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(
            settings(
                restart_delay_ms=100,
                max_restart_attempts=2,
                restart_window_seconds=10,
            ),
            api,
            clock,
        )
        first = supervisor.start()
        api.running[first.pid] = False
        self.assertEqual("waiting_restart", supervisor.tick().status)
        clock.value = 0.2
        second = supervisor.tick()
        api.running[second.pid] = False

        crash_loop = supervisor.tick()
        clock.value = 100.0
        still_blocked = supervisor.tick()

        self.assertEqual("crash_loop", crash_loop.status)
        self.assertEqual(2, crash_loop.failure_count)
        self.assertEqual("crash_loop", still_blocked.status)
        self.assertEqual(2, len(api.start_calls))

    def test_repeated_launch_failures_open_circuit_without_tight_loop(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi(existing=[])
        api.start_errors.extend([OSError("first"), OSError("second")])
        supervisor = ProcessSupervisor(
            settings(
                restart_delay_ms=100,
                max_restart_attempts=2,
                restart_window_seconds=10,
            ),
            api,
            clock,
        )

        first = supervisor.start()
        clock.value = 0.2
        second = supervisor.tick()
        clock.value = 20.0
        third = supervisor.tick()

        self.assertEqual("start_failed", first.status)
        self.assertEqual("crash_loop", second.status)
        self.assertEqual("crash_loop", third.status)
        self.assertEqual(2, len(api.start_calls))

    def test_stable_run_clears_old_failure_before_next_exit(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(
            settings(
                restart_delay_ms=100,
                max_restart_attempts=2,
                restart_window_seconds=5,
            ),
            api,
            clock,
        )
        first = supervisor.start()
        api.running[first.pid] = False
        supervisor.tick()
        clock.value = 0.2
        second = supervisor.tick()
        clock.value = 6.0
        self.assertEqual("running", supervisor.tick().status)
        api.running[second.pid] = False

        result = supervisor.tick()

        self.assertEqual("waiting_restart", result.status)
        self.assertEqual(1, result.failure_count)

    def test_restart_supervision_resets_open_circuit_without_termination(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi(existing=[])
        supervisor = ProcessSupervisor(
            settings(
                restart_delay_ms=100,
                max_restart_attempts=1,
                restart_window_seconds=10,
            ),
            api,
            clock,
        )
        first = supervisor.start()
        api.running[first.pid] = False
        self.assertEqual("crash_loop", supervisor.tick().status)

        supervisor.stop_supervision()
        resumed = supervisor.start()

        self.assertEqual("started", resumed.status)
        self.assertEqual(0, resumed.failure_count)
        self.assertEqual([], api.terminate_calls)


if __name__ == "__main__":
    unittest.main()
