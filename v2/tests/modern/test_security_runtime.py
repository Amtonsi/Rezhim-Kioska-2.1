# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.controller import AppController
from kiosk_v2_modern.app.effects import RuntimeEffects
from kiosk_v2_modern.domain.state_machine import StateMachine


def behavior():
    with open(
        os.path.join(V2_ROOT, "contracts", "behavior-cases.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class TogglePort(object):
    def __init__(self):
        self.running = False
        self.calls = []

    def start(self):
        self.running = True
        self.calls.append("start")

    def stop(self):
        self.running = False
        self.calls.append("stop")


class FakeView(object):
    def __init__(self):
        self.calls = []

    def show_operator(self):
        self.calls.append("operator")

    def show_admin_dialog(self):
        self.calls.append("admin_dialog")

    def show_auth_error(self):
        self.calls.append("auth_error")

    def show_admin_session(self):
        self.calls.append("admin_session")

    def show_restore_result(self):
        self.calls.append("restore_result")

    def show_restore_error(self):
        self.calls.append("restore_error")


class FakeRestore(object):
    def __init__(self):
        self.calls = []

    def run(self):
        self.calls.append("restore")


class SecurityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.desktop = TogglePort()
        self.keyboard = TogglePort()
        self.supervisor = TogglePort()
        self.view = FakeView()
        self.restore = FakeRestore()
        effects = RuntimeEffects(
            desktop=self.desktop,
            keyboard=self.keyboard,
            supervisor=self.supervisor,
            view=self.view,
            restore=self.restore,
        )
        self.controller = AppController(StateMachine(behavior()), effects)

    def test_guards_remain_active_until_authentication_succeeds(self):
        self.controller.handle("boot_completed")
        self.assertTrue(self.desktop.running)
        self.assertTrue(self.keyboard.running)
        self.assertTrue(self.supervisor.running)

        self.controller.handle("unlock_requested")
        self.assertTrue(self.desktop.running)
        self.assertTrue(self.keyboard.running)

        self.controller.handle("auth_failed")
        self.assertTrue(self.desktop.running)
        self.assertTrue(self.keyboard.running)

        self.controller.handle("unlock_requested")
        self.controller.handle("auth_succeeded")
        self.assertTrue(self.desktop.running)
        self.assertFalse(self.keyboard.running)

        self.controller.handle("return_to_kiosk")
        self.assertTrue(self.desktop.running)
        self.assertTrue(self.keyboard.running)

    def test_restore_transition_stops_guards_before_session_runs_restore(self):
        self.controller.handle("boot_completed")
        self.controller.handle("unlock_requested")
        self.controller.handle("auth_succeeded")

        self.controller.handle("restore_requested")

        self.assertFalse(self.desktop.running)
        self.assertFalse(self.keyboard.running)
        self.assertEqual([], self.restore.calls)


if __name__ == "__main__":
    unittest.main()
