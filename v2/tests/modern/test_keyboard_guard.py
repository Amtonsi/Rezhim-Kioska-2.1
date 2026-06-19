# -*- coding: utf-8 -*-
import os
import sys
import threading
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.keyboard_guard import (
    HookDispatcher,
    KeyboardGuard,
    KeyboardState,
    NativeHookLoop,
    VK_CONTROL,
    VK_ESCAPE,
    VK_LWIN,
    VK_MENU,
    VK_SHIFT,
    VK_TAB,
    WM_KEYDOWN,
    WM_KEYUP,
)


class FakeHookLoop(object):
    def __init__(self):
        self.start_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1


class FakeNativeHookApi(object):
    def __init__(self):
        self.callback = None
        self.hook_handle = 500
        self.thread_id = 77
        self.stop_event = threading.Event()
        self.uninstalled = []
        self.next_calls = []
        self.blocked_shortcuts = []
        self.down = set()
        self.lock_calls = 0

    def create_callback(self, callback):
        self.callback = callback
        return callback

    def current_thread_id(self):
        return self.thread_id

    def install(self, callback):
        self.callback = callback
        return self.hook_handle

    def run_message_loop(self):
        self.stop_event.wait(2.0)

    def request_stop(self, thread_id):
        self.asserted_thread_id = thread_id
        self.stop_event.set()
        return True

    def uninstall(self, hook_handle):
        self.uninstalled.append(hook_handle)
        return True

    def keyboard_vk_code(self, raw_event):
        return int(raw_event)

    def call_next(self, hook_handle, n_code, message, raw_event):
        self.next_calls.append((hook_handle, n_code, message, raw_event))
        return 42

    def modifier_down(self, vk_code):
        return vk_code in self.down

    def lock_workstation(self):
        self.lock_calls += 1
        return True


class KeyboardGuardTests(unittest.TestCase):
    def test_blocks_alt_tab_but_passes_text_and_keyup(self):
        state = KeyboardState()
        state.on_key(VK_MENU, WM_KEYDOWN)

        self.assertTrue(state.on_key(VK_TAB, WM_KEYDOWN).blocked)
        self.assertFalse(state.on_key(VK_TAB, WM_KEYUP).blocked)
        state.reset()
        self.assertFalse(state.on_key(ord("A"), WM_KEYDOWN).blocked)

    def test_blocks_ctrl_alt_tab_and_ctrl_shift_escape(self):
        state = KeyboardState()
        state.on_key(VK_CONTROL, WM_KEYDOWN)
        state.on_key(VK_MENU, WM_KEYDOWN)
        decision = state.on_key(VK_TAB, WM_KEYDOWN)
        self.assertTrue(decision.blocked)
        self.assertEqual("Ctrl+Alt+Tab", decision.shortcut)

        state.reset()
        state.on_key(VK_CONTROL, WM_KEYDOWN)
        state.on_key(VK_SHIFT, WM_KEYDOWN)
        decision = state.on_key(VK_ESCAPE, WM_KEYDOWN)
        self.assertTrue(decision.blocked)
        self.assertEqual("Ctrl+Shift+Esc", decision.shortcut)

    def test_win_l_locks_and_does_not_open_start(self):
        locks = []
        state = KeyboardState(lock_workstation=lambda: locks.append(True))
        state.on_key(VK_LWIN, WM_KEYDOWN)

        decision = state.on_key(ord("L"), WM_KEYDOWN)

        self.assertTrue(decision.blocked)
        self.assertEqual("Win+L", decision.shortcut)
        self.assertEqual([True], locks)

    def test_win_keyup_is_also_blocked_to_prevent_start_menu(self):
        state = KeyboardState()

        down = state.on_key(VK_LWIN, WM_KEYDOWN)
        up = state.on_key(VK_LWIN, WM_KEYUP)

        self.assertTrue(down.blocked)
        self.assertTrue(up.blocked)

    def test_guard_remains_running_during_admin_dialog(self):
        hook = FakeHookLoop()
        guard = KeyboardGuard(hook)
        guard.start()

        guard.enter_admin_dialog()

        self.assertTrue(guard.running)
        self.assertEqual(1, hook.start_calls)
        self.assertEqual(0, hook.stop_calls)

        guard.authentication_succeeded()
        self.assertFalse(guard.running)
        self.assertEqual(1, hook.stop_calls)

        guard.return_to_operator()
        self.assertTrue(guard.running)
        self.assertEqual(2, hook.start_calls)

    def test_dispatcher_calls_next_for_text_and_negative_hook_codes(self):
        next_calls = []
        dispatcher = HookDispatcher(
            KeyboardState(),
            call_next=lambda n_code, message, vk_code: next_calls.append(
                (n_code, message, vk_code)
            ) or 42,
        )

        self.assertEqual(42, dispatcher.handle(0, WM_KEYDOWN, ord("A")))
        self.assertEqual(42, dispatcher.handle(-1, WM_KEYDOWN, ord("B")))
        self.assertEqual(
            [(0, WM_KEYDOWN, ord("A")), (-1, WM_KEYDOWN, ord("B"))],
            next_calls,
        )

    def test_dispatcher_does_not_call_next_for_blocked_shortcut(self):
        next_calls = []
        state = KeyboardState()
        dispatcher = HookDispatcher(
            state,
            call_next=lambda *args: next_calls.append(args) or 42,
        )
        dispatcher.handle(0, WM_KEYDOWN, VK_MENU)

        result = dispatcher.handle(0, WM_KEYDOWN, VK_TAB)

        self.assertEqual(1, result)
        self.assertEqual(1, len(next_calls))

    def test_native_loop_forwards_text_and_blocks_only_forbidden_shortcut(self):
        native = FakeNativeHookApi()
        loop = NativeHookLoop(native=native)

        text_result = loop.dispatch_for_test(0, WM_KEYDOWN, ord("A"))
        native.down.add(VK_MENU)
        loop.dispatch_for_test(0, WM_KEYDOWN, VK_MENU)
        blocked_result = loop.dispatch_for_test(0, WM_KEYDOWN, VK_TAB)

        self.assertEqual(42, text_result)
        self.assertEqual(1, blocked_result)
        self.assertEqual(
            [(None, 0, WM_KEYDOWN, ord("A")), (None, 0, WM_KEYDOWN, VK_MENU)],
            native.next_calls,
        )

    def test_native_loop_installs_and_uninstalls_hook_on_its_message_thread(self):
        native = FakeNativeHookApi()
        loop = NativeHookLoop(native=native)

        loop.start()
        self.assertTrue(loop.running)
        loop.stop()

        self.assertFalse(loop.running)
        self.assertEqual(77, native.asserted_thread_id)
        self.assertEqual([500], native.uninstalled)


if __name__ == "__main__":
    unittest.main()
