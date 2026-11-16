# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.controller import AppController
from kiosk_v2_legacy.app.effects import RuntimeEffects
from kiosk_v2_legacy.app.session import LauncherSession
from kiosk_v2_legacy.domain.state_machine import StateMachine
from kiosk_v2_legacy.platform.desktop_isolation import IsolationResult
from kiosk_v2_legacy.ui.tk_view import KioskCanvasView


def behavior():
    with io.open(os.path.join(V2_ROOT, "contracts", "behavior-cases.json"), "r", encoding="utf-8") as stream:
        return json.load(stream)


class Root(object):
    def __init__(self):
        self.destroyed = False

    def after(self, *_args):
        return None

    def destroy(self):
        self.destroyed = True


class Toggle(object):
    def __init__(self):
        self.running = False

    def start(self): self.running = True
    def stop(self): self.running = False
    def tick(self): return None


class Application(Toggle):
    def __init__(self):
        Toggle.__init__(self)
        self.enabled = True
        self.resume_calls = 0
        self.stop_calls = 0
        self.bring_to_front_calls = 0
        self.latest_result = None
        self.application_path = r"C:\Allowed.exe"

    def stop_supervision(self):
        self.enabled = False
        self.stop_calls += 1

    def resume_supervision(self):
        self.enabled = True
        self.resume_calls += 1

    def tick(self, **_context): return None

    def bring_to_front(self, **_context):
        self.bring_to_front_calls += 1


class View(object):
    def __init__(self):
        self.calls = []
        self.restore_error = ""

    def show_operator(self): self.calls.append("operator")
    def show_admin_dialog(self): self.calls.append("dialog")
    def show_auth_error(self): self.calls.append("auth_error")
    def show_admin_session(self): self.calls.append("admin")
    def show_restore_result(self): self.calls.append("restore_result")
    def show_restore_error(self): self.calls.append("restore_error")
    def set_restore_error(self, message): self.restore_error = message
    def refresh(self): self.calls.append("refresh")


class Restore(object):
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def run(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return True


class OperatorRecovery(object):
    def __init__(self):
        self.calls = []

    def restore_shell_surfaces(self):
        self.calls.append("surfaces")

    def start_explorer(self):
        self.calls.append("explorer")


class Clock(object):
    def monotonic(self): return 0.0


class DeferredRoot(object):
    def __init__(self):
        self.callbacks = []

    def after(self, milliseconds, callback):
        self.callbacks.append((milliseconds, callback))


class SessionRestoreTests(unittest.TestCase):
    def build_session(self, restore, change_application=None):
        root = Root()
        desktop = Toggle()
        keyboard = Toggle()
        application = Application()
        view = View()
        effects = RuntimeEffects(desktop, keyboard, application, view, restore)
        controller = AppController(StateMachine(behavior()), effects)
        controller.handle("boot_completed")
        controller.handle("unlock_requested")
        controller.handle("auth_succeeded")
        session = LauncherSession(
            root=root,
            controller=controller,
            application=application,
            desktop=desktop,
            keyboard=keyboard,
            view=view,
            auth=None,
            recovery=OperatorRecovery(),
            clock=Clock(),
            admin_timeout_seconds=300,
            restore_action=restore,
            change_application=change_application,
        )
        session.running = True
        return session, root, application, view

    def test_reappearing_explorer_keeps_warning_between_enforcement_ticks(self):
        session = self.build_session(Restore())[0]
        session.running = True
        result = IsolationResult(terminated_pids=(123,))
        session.desktop.tick = lambda: result
        session.tick()
        self.assertTrue(session.model()["isolation_degraded"])
        session.desktop.tick = lambda: None
        session.tick()
        self.assertTrue(session.model()["isolation_degraded"])
        session.handle_action("returnToKiosk")
        self.assertFalse(session.model()["isolation_degraded"])
        session.tick()
        self.assertFalse(session.model()["isolation_degraded"])

    def test_restore_failure_keeps_admin_session_and_buttons_available(self):
        session, root, application, view = self.build_session(
            Restore(RuntimeError("exit code 3"))
        )

        session.handle_action("restore")

        self.assertEqual("ADMIN_SESSION", session.controller.state)
        self.assertTrue(session.running)
        self.assertEqual([], session.recovery.calls)
        self.assertFalse(root.destroyed)
        self.assertEqual(1, application.resume_calls)
        self.assertIn("restore_error", view.calls)

    def test_restore_success_closes_kiosk_after_child_completed(self):
        restore = Restore()
        session, root, application, view = self.build_session(restore)

        session.handle_action("restore")

        self.assertEqual(1, restore.calls)
        self.assertEqual(["surfaces", "explorer"], session.recovery.calls)
        self.assertFalse(session.running)
        session.close()
        self.assertEqual(["surfaces", "explorer"], session.recovery.calls)
        self.assertEqual("STOPPED", session.controller.state)
        self.assertTrue(root.destroyed)
        self.assertIn("restore_result", view.calls)

    def test_change_application_replaces_supervisor_and_starts_new_app(self):
        replacement = Application()
        replacement.application_path = r"C:\New\New.exe"
        session, _root, previous, _view = self.build_session(
            Restore(),
            change_application=lambda: replacement,
        )

        session.handle_action("changeApplication")

        self.assertEqual(1, previous.stop_calls)
        self.assertIs(replacement, session.application)
        self.assertTrue(replacement.running)

    def test_shell_interaction_only_brings_application_forward_in_operator_state(self):
        session, _root, application, _view = self.build_session(Restore())
        session.controller.handle("return_to_kiosk")

        session.handle_shell_interaction()
        session.controller.handle("unlock_requested")
        session.handle_shell_interaction()

        self.assertEqual(1, application.bring_to_front_calls)

    def test_canvas_click_defers_shell_interaction_until_button_action_finishes(self):
        calls = []
        root = DeferredRoot()
        view = KioskCanvasView.__new__(KioskCanvasView)
        view.root = root
        view.shell_interaction = lambda: calls.append("shell")

        view._on_shell_click(None)

        self.assertEqual(1, len(root.callbacks))
        self.assertEqual(0, root.callbacks[0][0])
        self.assertEqual([], calls)
        root.callbacks[0][1]()
        self.assertEqual(["shell"], calls)


if __name__ == "__main__":
    unittest.main()
