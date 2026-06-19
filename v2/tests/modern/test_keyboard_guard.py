# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.keyboard_guard import (
    HookDispatcher,
    KeyboardGuard,
    KeyboardState,
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


if __name__ == "__main__":
    unittest.main()
