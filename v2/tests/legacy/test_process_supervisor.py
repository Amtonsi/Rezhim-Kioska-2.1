# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ntpath
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.process_supervisor import (
    ApplicationSettings,
    ProcessRef,
    ProcessSupervisor,
)
from kiosk_v2_legacy.platform.clock import TickCountClock


APP_PATH = r"C:\Program Files\Vendor\Allowed.exe"


def normalize(path):
    return ntpath.normcase(ntpath.normpath(path))


def settings(**overrides):
    values = {
        "path": APP_PATH,
        "arguments": ("--mode", "operator"),
        "working_directory": r"C:\Program Files\Vendor",
        "restart_on_exit": True,
        "restart_delay_ms": 1000,
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


class FakeTickApi(object):
    def __init__(self, values):
        self.values = list(values)

    def get_tick_count(self):
        return self.values.pop(0)


class FakeProcessApi(object):
    def __init__(self, existing=None):
        self.existing = list(existing or [])
        self.running = dict((item.pid, item.running) for item in self.existing)
        self.paths = dict((item.pid, item.path) for item in self.existing)
        self.start_calls = []
        self.start_errors = []
        self.terminate_calls = []
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


class HandOffProcessApi(FakeProcessApi):
    def __init__(self, handoff_pid=200):
        FakeProcessApi.__init__(self)
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
        FakeProcessApi.__init__(self)
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
        r"C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_1.0_x86"
        r"\Notepad\Notepad.exe"
    )

    def __init__(self, handoff_pid=250):
        FakeProcessApi.__init__(self)
        self.handoff_pid = handoff_pid
        self.find_by_name_calls = 0
        self.running[handoff_pid] = True
        self.paths[handoff_pid] = self.HANDOFF_PATH

    def find_existing_broker(self, path):
        self.find_by_name_calls += 1
        return [ProcessRef(self.handoff_pid, self.HANDOFF_PATH, True)]


class RunningThenHandoffApi(DelayedDifferentPathHandoffApi):
    def start(self, application_settings):
        process = DelayedDifferentPathHandoffApi.start(self, application_settings)
        process.running = True
        self.running[process.pid] = True
        return process


class TemporarilyFailingHandoffApi(DelayedDifferentPathHandoffApi):
    def __init__(self):
        DelayedDifferentPathHandoffApi.__init__(self)
        self.handoff_checks = 0

    def find_handoff(self, parent_pid, path):
        self.handoff_checks += 1
        if self.handoff_checks == 1:
            return []
        raise OSError("snapshot temporarily unavailable")


class LegacyProcessSupervisorTests(unittest.TestCase):
    def test_adopts_existing_exact_path_without_duplicate(self):
        api = FakeProcessApi(
            [ProcessRef(10, r"c:/program files/vendor/ALLOWED.exe", True)]
        )
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        result = supervisor.start()

        self.assertEqual("adopted", result.status)
        self.assertEqual(10, result.pid)
        self.assertEqual([], api.start_calls)

    def test_starts_once_and_alive_process_is_never_reopened(self):
        api = FakeProcessApi()
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        started = supervisor.start()
        running = supervisor.tick()

        self.assertEqual("started", started.status)
        self.assertEqual("running", running.status)
        self.assertEqual(1, len(api.start_calls))

    def test_delayed_restart_starts_exactly_one_replacement(self):
        clock = FakeClock(10.0)
        api = FakeProcessApi()
        supervisor = ProcessSupervisor(settings(restart_delay_ms=1000), api, clock)
        first = supervisor.start()
        api.running[first.pid] = False

        self.assertEqual("waiting_restart", supervisor.tick().status)
        clock.value = 10.9
        self.assertEqual("waiting_restart", supervisor.tick().status)
        clock.value = 11.1
        restarted = supervisor.tick()

        self.assertEqual("restarted", restarted.status)
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
        api = FakeProcessApi()
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

    def test_pid_reuse_with_other_path_is_exit(self):
        api = FakeProcessApi([ProcessRef(10, APP_PATH, True)])
        supervisor = ProcessSupervisor(settings(), api, FakeClock())
        supervisor.start()
        api.paths[10] = r"C:\Windows\notepad.exe"

        result = supervisor.tick()

        self.assertEqual("waiting_restart", result.status)
        self.assertEqual(10, result.previous_pid)

    def test_multiple_existing_instances_report_conflict(self):
        api = FakeProcessApi(
            [ProcessRef(10, APP_PATH, True), ProcessRef(11, APP_PATH.lower(), True)]
        )
        supervisor = ProcessSupervisor(settings(), api, FakeClock())

        result = supervisor.start()

        self.assertEqual("conflict", result.status)
        self.assertEqual((10, 11), result.conflict_pids)
        self.assertEqual([], api.start_calls)

    def test_stop_never_terminates_and_resume_adopts(self):
        api = FakeProcessApi()
        supervisor = ProcessSupervisor(settings(), api, FakeClock())
        started = supervisor.start()

        supervisor.stop_supervision()
        resumed = supervisor.start()

        self.assertEqual("adopted", resumed.status)
        self.assertEqual(started.pid, resumed.pid)
        self.assertEqual([], api.terminate_calls)
        self.assertEqual(1, len(api.start_calls))

    def test_launch_failures_use_delay_and_open_circuit(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi()
        api.start_errors.extend([OSError("first"), OSError("second")])
        supervisor = ProcessSupervisor(
            settings(max_restart_attempts=2, restart_delay_ms=100), api, clock
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

    def test_rapid_exits_open_circuit(self):
        clock = FakeClock(0.0)
        api = FakeProcessApi()
        supervisor = ProcessSupervisor(
            settings(max_restart_attempts=2, restart_delay_ms=100), api, clock
        )
        first = supervisor.start()
        api.running[first.pid] = False
        supervisor.tick()
        clock.value = 0.2
        second = supervisor.tick()
        api.running[second.pid] = False

        result = supervisor.tick()

        self.assertEqual("crash_loop", result.status)
        self.assertEqual(2, result.failure_count)
        self.assertEqual(2, len(api.start_calls))

    def test_tick_count_clock_survives_32_bit_wrap(self):
        clock = TickCountClock(
            FakeTickApi([0xFFFFFF00, 0xFFFFFFF0, 0x00000020])
        )

        first = clock.monotonic()
        second = clock.monotonic()
        third = clock.monotonic()

        self.assertLess(first, second)
        self.assertLess(second, third)
        self.assertAlmostEqual(0.240, second - first, places=3)
        self.assertAlmostEqual(0.048, third - second, places=3)


if __name__ == "__main__":
    unittest.main()
