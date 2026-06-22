# -*- coding: utf-8 -*-
import ntpath
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.application_runtime import ApplicationRuntime
from kiosk_v2_modern.app.process_supervisor import (
    ApplicationSettings,
    ProcessRef,
    ProcessSupervisor,
)
from kiosk_v2_modern.app.window_coordinator import WindowCoordinator


APP_PATH = r"C:\Program Files\Vendor\Allowed.exe"


def normalize(path):
    return ntpath.normcase(ntpath.normpath(path))


class FakeClock(object):
    def __init__(self, value=0.0):
        self.value = value

    def monotonic(self):
        return self.value


class FakeProcessApi(object):
    def __init__(self, existing=None):
        self.processes = list(existing or [])
        self.paths = dict((item.pid, item.path) for item in self.processes)
        self.running = dict((item.pid, item.running) for item in self.processes)
        self.start_calls = []
        self.next_pid = 100

    def find_by_exact_path(self, path):
        expected = normalize(path)
        return [
            ProcessRef(item.pid, item.path, self.running.get(item.pid, False))
            for item in self.processes
            if normalize(item.path) == expected
        ]

    def start(self, settings):
        self.start_calls.append(settings)
        process = ProcessRef(self.next_pid, settings.path, True)
        self.next_pid += 1
        self.processes.append(process)
        self.paths[process.pid] = process.path
        self.running[process.pid] = True
        return process

    def is_running(self, pid, expected_path):
        return self.running.get(pid, False) and (
            normalize(self.paths.get(pid, "")) == normalize(expected_path)
        )


class FakeWindowApi(object):
    def __init__(self):
        self.windows = {100: [1000], 101: [1001]}
        self.minimized = set()
        self.restore_calls = []
        self.foreground_calls = []
        self.foreground_succeeds = True

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
        return self.foreground_succeeds


def create_runtime(clock=None, process_api=None, window_api=None):
    clock = clock or FakeClock()
    process_api = process_api or FakeProcessApi()
    window_api = window_api or FakeWindowApi()
    settings = ApplicationSettings(
        APP_PATH,
        arguments=(),
        working_directory=r"C:\Program Files\Vendor",
        restart_on_exit=True,
        restart_delay_ms=1000,
        single_instance=True,
    )
    supervisor = ProcessSupervisor(settings, process_api, clock)
    coordinator = WindowCoordinator(window_api)
    return (
        ApplicationRuntime(supervisor, coordinator, start_maximized=False),
        process_api,
        window_api,
        clock,
    )


class ApplicationRuntimeTests(unittest.TestCase):
    def test_start_and_tick_keep_one_instance_and_do_not_steal_focus_repeatedly(self):
        runtime, process_api, window_api, _clock = create_runtime()

        started = runtime.start()
        running = runtime.tick()

        self.assertEqual("started", started.process_status)
        self.assertEqual("visible", started.window_status)
        self.assertEqual("running", running.process_status)
        self.assertEqual(1, len(process_api.start_calls))
        self.assertEqual([1000], window_api.foreground_calls)

    def test_minimize_is_reported_without_restore_or_duplicate_then_button_restores(self):
        runtime, process_api, window_api, _clock = create_runtime()
        runtime.start()
        window_api.foreground_calls = []
        window_api.minimized.add(1000)

        minimized = runtime.tick()

        self.assertEqual("minimized", minimized.window_status)
        self.assertEqual([], window_api.restore_calls)
        self.assertEqual([], window_api.foreground_calls)

        restored = runtime.restore_application()

        self.assertEqual("visible", restored.window_status)
        self.assertEqual([(1000, False)], window_api.restore_calls)
        self.assertEqual([1000], window_api.foreground_calls)
        self.assertEqual(1, len(process_api.start_calls))

    def test_failed_initial_foreground_attempt_does_not_restore_on_later_tick(self):
        runtime, process_api, window_api, _clock = create_runtime()
        window_api.foreground_succeeds = False

        started = runtime.start()
        window_api.minimized.add(1000)
        minimized = runtime.tick()

        self.assertEqual("foreground_failed", started.window_status)
        self.assertEqual("minimized", minimized.window_status)
        self.assertEqual([], window_api.restore_calls)
        self.assertEqual([1000], window_api.foreground_calls)
        self.assertEqual(1, len(process_api.start_calls))

    def test_shell_interaction_brings_visible_application_to_front(self):
        runtime, _process_api, window_api, _clock = create_runtime()
        runtime.start()
        window_api.foreground_calls = []

        result = runtime.bring_to_front()

        self.assertEqual("visible", result.window_status)
        self.assertEqual([1000], window_api.foreground_calls)
        self.assertEqual([], window_api.restore_calls)

    def test_shell_interaction_does_not_restore_minimized_application(self):
        runtime, _process_api, window_api, _clock = create_runtime()
        runtime.start()
        window_api.foreground_calls = []
        window_api.minimized.add(1000)

        result = runtime.bring_to_front()

        self.assertEqual("minimized", result.window_status)
        self.assertEqual([], window_api.foreground_calls)
        self.assertEqual([], window_api.restore_calls)

    def test_shell_interaction_is_suppressed_during_admin_dialog(self):
        runtime, _process_api, window_api, _clock = create_runtime()
        runtime.start()
        window_api.foreground_calls = []

        result = runtime.bring_to_front(admin_dialog_open=True)

        self.assertEqual("suppressed", result.window_status)
        self.assertEqual([], window_api.foreground_calls)

    def test_exit_restarts_once_after_delay_and_activates_new_window(self):
        runtime, process_api, window_api, clock = create_runtime()
        first = runtime.start()
        process_api.running[first.pid] = False

        waiting = runtime.tick()
        clock.value = 1.1
        restarted = runtime.tick()

        self.assertEqual("waiting_restart", waiting.process_status)
        self.assertEqual("restarted", restarted.process_status)
        self.assertEqual(101, restarted.pid)
        self.assertEqual(2, len(process_api.start_calls))
        self.assertEqual([1000, 1001], window_api.foreground_calls)

    def test_restart_during_admin_dialog_never_covers_credentials(self):
        runtime, process_api, window_api, clock = create_runtime()
        first = runtime.start()
        process_api.running[first.pid] = False
        runtime.tick(admin_dialog_open=True)
        clock.value = 1.1

        suppressed = runtime.tick(admin_dialog_open=True)
        still_suppressed = runtime.tick(admin_dialog_open=True)

        self.assertEqual("visible", suppressed.window_status)
        self.assertEqual("visible", still_suppressed.window_status)
        self.assertEqual([1000], window_api.foreground_calls)

        activated = runtime.tick(admin_dialog_open=False)

        self.assertEqual("visible", activated.window_status)
        self.assertEqual([1000], window_api.foreground_calls)

    def test_pending_window_during_admin_dialog_updates_status_without_focus_steal(self):
        runtime, _process_api, window_api, _clock = create_runtime()
        window_api.windows[100] = []

        started = runtime.start()
        window_api.windows[100] = [1000]
        visible = runtime.tick(admin_dialog_open=True)

        self.assertEqual("no_window", started.window_status)
        self.assertEqual("visible", visible.window_status)
        self.assertEqual([], window_api.restore_calls)
        self.assertEqual([], window_api.foreground_calls)

    def test_pending_window_during_admin_session_reports_minimized_without_focus_steal(self):
        runtime, _process_api, window_api, _clock = create_runtime()
        window_api.windows[100] = []

        runtime.start()
        window_api.windows[100] = [1000]
        window_api.minimized.add(1000)
        minimized = runtime.tick(admin_session_active=True)
        later = runtime.tick(admin_session_active=True)

        self.assertEqual("minimized", minimized.window_status)
        self.assertEqual("minimized", later.window_status)
        self.assertEqual([], window_api.restore_calls)
        self.assertEqual([], window_api.foreground_calls)

    def test_stop_leaves_process_alive_and_resume_adopts_without_activation_or_launch(self):
        runtime, process_api, window_api, _clock = create_runtime()
        started = runtime.start()
        window_api.foreground_calls = []

        stopped = runtime.stop_supervision()
        resumed = runtime.resume_supervision()

        self.assertEqual("stopped", stopped.process_status)
        self.assertTrue(process_api.running[started.pid])
        self.assertEqual("adopted", resumed.process_status)
        self.assertEqual(started.pid, resumed.pid)
        self.assertEqual(1, len(process_api.start_calls))
        self.assertEqual([], window_api.foreground_calls)

    def test_existing_exact_path_process_is_adopted_without_duplicate(self):
        process_api = FakeProcessApi(existing=[ProcessRef(10, APP_PATH, True)])
        window_api = FakeWindowApi()
        window_api.windows[10] = [500]
        runtime, process_api, window_api, _clock = create_runtime(
            process_api=process_api,
            window_api=window_api,
        )

        result = runtime.start()

        self.assertEqual("adopted", result.process_status)
        self.assertEqual(10, result.pid)
        self.assertEqual([], process_api.start_calls)
        self.assertEqual([500], window_api.foreground_calls)


if __name__ == "__main__":
    unittest.main()
