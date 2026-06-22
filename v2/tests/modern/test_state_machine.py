# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.domain.state_machine import InvalidTransition, StateMachine


def behavior():
    with open(
        os.path.join(V2_ROOT, "contracts", "behavior-cases.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class ModernStateMachineTests(unittest.TestCase):
    def test_walks_secure_unlock_flow(self):
        machine = StateMachine(behavior())

        boot = machine.dispatch("boot_completed")
        request = machine.dispatch("unlock_requested")
        failure = machine.dispatch("auth_failed")

        self.assertEqual("OPERATOR", boot.to_state)
        self.assertEqual("ADMIN_DIALOG", request.to_state)
        self.assertNotIn("stop_keyboard_guard", request.effects)
        self.assertNotIn("stop_desktop_isolation", request.effects)
        self.assertEqual("OPERATOR", failure.to_state)

    def test_stops_keyboard_only_after_authentication_success(self):
        machine = StateMachine(behavior())
        machine.dispatch("boot_completed")
        machine.dispatch("unlock_requested")

        result = machine.dispatch("auth_succeeded")

        self.assertEqual("ADMIN_SESSION", result.to_state)
        self.assertIn("stop_keyboard_guard", result.effects)
        self.assertNotIn("stop_desktop_isolation", result.effects)

    def test_rejects_undefined_transition_without_changing_state(self):
        machine = StateMachine(behavior())

        with self.assertRaises(InvalidTransition):
            machine.dispatch("auth_succeeded")

        self.assertEqual("STARTING", machine.state)


if __name__ == "__main__":
    unittest.main()
