# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.domain.state_machine import InvalidTransition, StateMachine


def behavior():
    with io.open(
        os.path.join(V2_ROOT, "contracts", "behavior-cases.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class LegacyStateMachineTests(unittest.TestCase):
    def test_secure_unlock_and_return_flow(self):
        machine = StateMachine(behavior())
        machine.dispatch("boot_completed")
        request = machine.dispatch("unlock_requested")
        self.assertEqual("ADMIN_DIALOG", request.to_state)
        self.assertNotIn("stop_keyboard_guard", request.effects)
        success = machine.dispatch("auth_succeeded")
        self.assertEqual("ADMIN_SESSION", success.to_state)
        self.assertNotIn("stop_desktop_isolation", success.effects)
        returned = machine.dispatch("return_to_kiosk")
        self.assertEqual("OPERATOR", returned.to_state)
        self.assertIn("start_keyboard_guard", returned.effects)

    def test_invalid_event_preserves_state(self):
        machine = StateMachine(behavior())
        with self.assertRaises(InvalidTransition):
            machine.dispatch("restore_completed")
        self.assertEqual("STARTING", machine.state)


if __name__ == "__main__":
    unittest.main()
