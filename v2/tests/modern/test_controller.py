# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.controller import AppController, EffectExecutionError
from kiosk_v2_modern.domain.state_machine import StateMachine


def behavior():
    with open(
        os.path.join(V2_ROOT, "contracts", "behavior-cases.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        return json.load(stream)


class FakeEffects(object):
    def __init__(self):
        self.calls = []
        self.rollback_calls = []

    def run(self, name):
        self.calls.append(name)

    def rollback(self, name):
        self.rollback_calls.append(name)


class FailingEffects(FakeEffects):
    def __init__(self, failed_name):
        super(FailingEffects, self).__init__()
        self.failed_name = failed_name

    def run(self, name):
        if name == self.failed_name:
            raise RuntimeError(name)
        super(FailingEffects, self).run(name)


class AppControllerTests(unittest.TestCase):
    def test_unlock_request_keeps_guards_running(self):
        effects = FakeEffects()
        controller = AppController(StateMachine(behavior()), effects)
        controller.handle("boot_completed")
        effects.calls = []

        result = controller.handle("unlock_requested")

        self.assertEqual("ADMIN_DIALOG", result.to_state)
        self.assertEqual(["show_admin_dialog"], effects.calls)

    def test_auth_success_stops_guards_after_validation_event(self):
        effects = FakeEffects()
        controller = AppController(StateMachine(behavior()), effects)
        controller.handle("boot_completed")
        controller.handle("unlock_requested")
        effects.calls = []

        controller.handle("auth_succeeded")

        self.assertEqual(
            [
                "stop_keyboard_guard",
                "stop_desktop_isolation",
                "show_admin_session",
            ],
            effects.calls,
        )

    def test_effect_failure_rolls_back_completed_effects_and_state(self):
        effects = FailingEffects("start_supervisor")
        controller = AppController(StateMachine(behavior()), effects)

        with self.assertRaises(EffectExecutionError):
            controller.handle("boot_completed")

        self.assertEqual("STARTING", controller.state)
        self.assertEqual(
            ["start_keyboard_guard", "start_desktop_isolation"],
            effects.rollback_calls,
        )


if __name__ == "__main__":
    unittest.main()
