# -*- coding: utf-8 -*-

import threading
import unittest

from legacy_kiosk.keyboard_filter import KeyboardFilterService, KeyboardFilterState
from legacy_kiosk.process_watchdog import (
    AdoptedProcess,
    LegacyProcessWatchdog,
    NativeProcessBackend,
)
from legacy_kiosk.window_control import LegacyWindowController, NativeWindowApi


class FakeProcess(object):
    def __init__(self, pid):
        self.pid = pid
        self.running = True


class FakeProcessBackend(object):
    def __init__(self):
        self.existing_pids = []
        self.started = []

    def find_process_ids(self, executable_path):
        return list(self.existing_pids)

    def adopt_process(self, pid):
        process = FakeProcess(pid)
        self.started.append(("adopt", pid))
        return process

    def start_process(self, executable_path, arguments, working_directory, start_maximized):
        process = FakeProcess(1000 + len(self.started))
        self.started.append(
            (
                "start",
                executable_path,
                arguments,
                working_directory,
                start_maximized,
            )
        )
        return process

    def is_process_running(self, process, executable_path):
        return process.running


class FakeWindowApi(object):
    def __init__(self):
        self.windows = []
        self.iconic = set()
        self.calls = []

    def visible_windows_for_pids(self, process_ids):
        return [window for window in self.windows if window[1] in process_ids]

    def is_iconic(self, hwnd):
        return hwnd in self.iconic

    def restore(self, hwnd):
        self.calls.append(("restore", hwnd))
        self.iconic.discard(hwnd)

    def maximize(self, hwnd):
        self.calls.append(("maximize", hwnd))

    def bring_to_front(self, hwnd):
        self.calls.append(("front", hwnd))


class DelayedWindowApi(FakeWindowApi):
    def __init__(self):
        FakeWindowApi.__init__(self)
        self.attempts = 0

    def visible_windows_for_pids(self, process_ids):
        self.attempts += 1
        if self.attempts < 3:
            return []
        return [(600, process_ids[0])]


class FakeNativeProcessApi(object):
    def __init__(self):
        self.pids = [10]
        self.started = FakeProcess(20)

    def process_ids_for_path(self, executable_path):
        return list(self.pids)

    def start_process(self, executable_path, arguments, working_directory, start_maximized):
        return self.started

    def process_id_matches_path(self, process_id, executable_path):
        return process_id in self.pids


class FakeHookLoop(object):
    def __init__(self):
        self.started = threading.Event()
        self.stopped = threading.Event()

    def run(self):
        self.started.set()
        self.stopped.wait(2.0)

    def stop(self):
        self.stopped.set()


class RuntimeControlTests(unittest.TestCase):
    def _watchdog(self, backend=None, clock=None):
        return LegacyProcessWatchdog(
            executable_path=r"C:\Apps\Allowed.exe",
            arguments="--example",
            working_directory=r"C:\Apps",
            restart_on_exit=True,
            restart_delay_seconds=2,
            single_instance=True,
            start_maximized=False,
            backend=backend or FakeProcessBackend(),
            clock=clock,
        )

    def test_watchdog_starts_exactly_one_process(self):
        backend = FakeProcessBackend()
        watchdog = self._watchdog(backend=backend, clock=lambda: 0)

        self.assertEqual("started", watchdog.tick())
        self.assertEqual("running", watchdog.tick())

        self.assertEqual(1, len([call for call in backend.started if call[0] == "start"]))

    def test_watchdog_adopts_existing_matching_process(self):
        backend = FakeProcessBackend()
        backend.existing_pids = [42]
        watchdog = self._watchdog(backend=backend, clock=lambda: 0)

        self.assertEqual("adopted", watchdog.tick())
        self.assertEqual([("adopt", 42)], backend.started)

    def test_watchdog_delays_single_restart_after_exit(self):
        now = [0.0]
        backend = FakeProcessBackend()
        watchdog = self._watchdog(backend=backend, clock=lambda: now[0])
        watchdog.tick()
        watchdog.process.running = False

        self.assertEqual("exited", watchdog.tick())
        now[0] = 1.9
        self.assertEqual("waiting", watchdog.tick())
        now[0] = 2.0
        self.assertEqual("restarted", watchdog.tick())
        self.assertEqual(2, len([call for call in backend.started if call[0] == "start"]))

    def test_stop_and_start_supervision_do_not_terminate_process(self):
        backend = FakeProcessBackend()
        watchdog = self._watchdog(backend=backend, clock=lambda: 0)
        watchdog.tick()
        process = watchdog.process

        watchdog.stop_supervision()
        self.assertEqual("stopped", watchdog.tick())
        self.assertTrue(process.running)
        watchdog.start_supervision()
        self.assertEqual("running", watchdog.tick())

    def test_minimized_window_stays_minimized_until_manual_restore(self):
        process_backend = FakeProcessBackend()
        process_backend.existing_pids = [77]
        window_api = FakeWindowApi()
        window_api.windows = [(500, 77)]
        window_api.iconic.add(500)
        controller = LegacyWindowController(process_backend, window_api)

        self.assertTrue(controller.is_minimized(r"C:\Apps\Allowed.exe"))
        self.assertEqual([], window_api.calls)

        self.assertTrue(controller.restore(r"C:\Apps\Allowed.exe"))
        self.assertEqual([("restore", 500), ("front", 500)], window_api.calls)

    def test_window_controller_brings_running_app_to_front_without_duplicate_start(self):
        process_backend = FakeProcessBackend()
        process_backend.existing_pids = [77]
        window_api = FakeWindowApi()
        window_api.windows = [(500, 77)]
        controller = LegacyWindowController(process_backend, window_api)

        self.assertTrue(controller.bring_to_front(r"C:\Apps\Allowed.exe"))
        self.assertEqual([("front", 500)], window_api.calls)
        self.assertEqual([], process_backend.started)

    def test_window_controller_waits_for_main_window_then_maximizes(self):
        process_backend = FakeProcessBackend()
        process_backend.existing_pids = [77]
        window_api = DelayedWindowApi()
        now = [0.0]

        def sleep(delay):
            now[0] += delay

        controller = LegacyWindowController(
            process_backend,
            window_api,
            clock=lambda: now[0],
            sleeper=sleep,
        )

        self.assertTrue(
            controller.wait_and_bring_to_front(
                r"C:\Apps\Allowed.exe", timeout_seconds=1, start_maximized=True
            )
        )
        self.assertEqual([("maximize", 600), ("front", 600)], window_api.calls)

    def test_keyboard_filter_blocks_escape_shortcuts_and_allows_text(self):
        pressed = set()
        locks = []
        state = KeyboardFilterState(
            lock_workstation=lambda: locks.append("lock"),
            key_state_checker=lambda key: key in pressed,
        )

        self.assertFalse(state.should_block_key(ord("A"), state.WM_KEYDOWN))

        pressed.add(state.VK_MENU)
        state.should_block_key(state.VK_MENU, state.WM_SYSKEYDOWN)
        self.assertTrue(state.should_block_key(state.VK_TAB, state.WM_SYSKEYDOWN))
        pressed.add(state.VK_CONTROL)
        state.should_block_key(state.VK_CONTROL, state.WM_KEYDOWN)
        self.assertTrue(state.should_block_key(state.VK_TAB, state.WM_SYSKEYDOWN))

        pressed.discard(state.VK_MENU)
        state.should_block_key(state.VK_MENU, state.WM_SYSKEYUP)
        pressed.add(state.VK_SHIFT)
        state.should_block_key(state.VK_SHIFT, state.WM_KEYDOWN)
        self.assertTrue(state.should_block_key(state.VK_ESCAPE, state.WM_KEYDOWN))

        pressed.discard(state.VK_SHIFT)
        state.should_block_key(state.VK_SHIFT, state.WM_KEYUP)
        self.assertTrue(state.should_block_key(state.VK_ESCAPE, state.WM_KEYDOWN))

        pressed.discard(state.VK_CONTROL)
        state.should_block_key(state.VK_CONTROL, state.WM_KEYUP)
        pressed.add(state.VK_MENU)
        state.should_block_key(state.VK_MENU, state.WM_SYSKEYDOWN)
        self.assertTrue(state.should_block_key(state.VK_F4, state.WM_SYSKEYDOWN))

        pressed.discard(state.VK_MENU)
        state.should_block_key(state.VK_MENU, state.WM_SYSKEYUP)
        pressed.add(state.VK_LWIN)
        self.assertTrue(state.should_block_key(state.VK_LWIN, state.WM_KEYDOWN))
        self.assertTrue(state.should_block_key(state.VK_L, state.WM_KEYDOWN))
        self.assertEqual(["lock"], locks)

    def test_keyboard_filter_recovers_stale_modifiers_and_never_blocks_keyup(self):
        pressed = set()
        state = KeyboardFilterState(key_state_checker=lambda key: key in pressed)
        state.win_down = True
        state.alt_down = True
        state.ctrl_down = True
        state.shift_down = True

        self.assertFalse(state.should_block_key(ord("B"), state.WM_KEYDOWN))
        self.assertFalse(state.should_block_key(state.VK_TAB, state.WM_KEYUP))
        self.assertFalse(state.win_down)
        self.assertFalse(state.alt_down)
        self.assertFalse(state.ctrl_down)
        self.assertFalse(state.shift_down)

    def test_native_process_backend_adopts_and_checks_exact_process(self):
        api = FakeNativeProcessApi()
        backend = NativeProcessBackend(api=api)

        adopted = backend.adopt_process(10)

        self.assertIsInstance(adopted, AdoptedProcess)
        self.assertTrue(backend.is_process_running(adopted, r"C:\Apps\Allowed.exe"))
        api.pids = []
        self.assertFalse(backend.is_process_running(adopted, r"C:\Apps\Allowed.exe"))

    def test_native_window_api_constructs_with_nt5_compatible_functions(self):
        api = NativeWindowApi()

        self.assertIsNotNone(api.user32)

    def test_keyboard_filter_service_stops_hook_and_resets_state(self):
        fake_loop = FakeHookLoop()
        state = KeyboardFilterState(key_state_checker=lambda key: False)
        service = KeyboardFilterService(
            state=state, loop_factory=lambda current_state: fake_loop
        )

        service.start()
        fake_loop.started.wait(1.0)
        self.assertTrue(fake_loop.started.is_set())
        state.win_down = True
        service.stop()

        self.assertTrue(fake_loop.stopped.is_set())
        self.assertFalse(state.win_down)


if __name__ == "__main__":
    unittest.main()
