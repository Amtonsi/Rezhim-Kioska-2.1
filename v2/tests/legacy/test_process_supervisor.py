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
