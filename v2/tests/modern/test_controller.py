# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.controller import AppController, EffectExecutionError
from kiosk_v2_modern.app.effects import RuntimeEffects
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


class SecretFailingEffects(FailingEffects):
    def run(self, name):
        if name == self.failed_name:
            raise RuntimeError("password=hunter2")
        super(FailingEffects, self).run(name)


class FakeAudit(object):
    def __init__(self, fail=False):
        self.fail = fail
        self.events = []

    def emit(self, event_name, level="Info", **fields):
        if self.fail:
            raise OSError("audit unavailable")
        self.events.append((event_name, level, fields))


class AppControllerTests(unittest.TestCase):
    def test_supervisor_start_rollback_stops_supervision_without_terminating_app(self):
        calls = []

        class Stub(object):
            def start(self):
                pass

            def stop(self):
                pass

            def run(self):
                pass

            def show_operator(self):
                pass

            def show_admin_dialog(self):
                pass

            def show_auth_error(self):
                pass

            def show_admin_session(self):
                pass

            def show_restore_result(self):
                pass

        class Supervisor(object):
            def start(self):
                calls.append("start")

            def stop_supervision(self):
                calls.append("stop_supervision")

        effects = RuntimeEffects(
            desktop=Stub(),
            keyboard=Stub(),
            supervisor=Supervisor(),
            view=Stub(),
            restore=Stub(),
        )

        effects.rollback("start_supervisor")

        self.assertEqual(["stop_supervision"], calls)

    def test_successful_transition_emits_safe_structured_audit_event(self):
        effects = FakeEffects()
        audit = FakeAudit()
        controller = AppController(StateMachine(behavior()), effects, audit=audit)

        transition = controller.handle("boot_completed")

        self.assertEqual("OPERATOR", transition.to_state)
        self.assertEqual(1, len(audit.events))
        event_name, level, fields = audit.events[0]
        self.assertEqual("state_transition", event_name)
        self.assertEqual("Info", level)
        self.assertEqual("STARTING", fields["fromState"])
        self.assertEqual("OPERATOR", fields["toState"])
        self.assertEqual("boot_completed", fields["transitionEvent"])
        self.assertEqual(tuple(transition.effects), fields["effects"])

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

    def test_effect_failure_audit_never_contains_exception_message(self):
        effects = SecretFailingEffects("start_supervisor")
        audit = FakeAudit()
        controller = AppController(StateMachine(behavior()), effects, audit=audit)

        effects.failed_name = "start_supervisor"
        with self.assertRaises(EffectExecutionError) as raised:
            controller.handle("boot_completed")

        self.assertNotIn("password", str(raised.exception).lower())
        self.assertEqual(1, len(audit.events))
        event_name, level, fields = audit.events[0]
        self.assertEqual("effect_failed", event_name)
        self.assertEqual("Error", level)
        self.assertEqual("RuntimeError", fields["errorType"])
        self.assertEqual("start_supervisor", fields["failedEffect"])
        self.assertNotIn("password", repr(fields).lower())

    def test_audit_failure_does_not_undo_successful_security_transition(self):
        effects = FakeEffects()
        controller = AppController(
            StateMachine(behavior()),
            effects,
            audit=FakeAudit(fail=True),
        )

        result = controller.handle("boot_completed")

        self.assertEqual("OPERATOR", result.to_state)
        self.assertEqual("OPERATOR", controller.state)
        self.assertEqual(
            [
                "start_desktop_isolation",
                "start_keyboard_guard",
                "start_supervisor",
                "show_operator_ui",
            ],
            effects.calls,
        )


if __name__ == "__main__":
    unittest.main()
