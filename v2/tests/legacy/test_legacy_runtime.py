# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.app.application_runtime import ApplicationRuntime
from kiosk_v2_legacy.app.config_repository import (
    LegacyConfigRepository,
    LegacyConfigValidator,
)
from kiosk_v2_legacy.app.controller import AppController, EffectExecutionError
from kiosk_v2_legacy.app.effects import RuntimeEffects
from kiosk_v2_legacy.app.window_coordinator import WindowCoordinator
from kiosk_v2_legacy.domain.state_machine import StateMachine


def load_json(path):
    with io.open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


class FakeAcl(object):
    def __init__(self):
        self.calls = []

    def protect_admin_write(self, path):
        self.calls.append(path)


class FakeReplacer(object):
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def replace(self, source, target):
        self.calls.append((source, target))
        if self.error is not None:
            raise self.error
        if os.path.exists(target):
            os.unlink(target)
        os.rename(source, target)


class Toggle(object):
    def __init__(self):
        self.running = False
        self.calls = []

    def start(self):
        self.running = True
        self.calls.append("start")

    def stop(self):
        self.running = False
        self.calls.append("stop")


class SupervisorToggle(Toggle):
    def stop_supervision(self):
        self.stop()


class FakeView(object):
    def __init__(self):
        self.calls = []

    def show_operator(self):
        self.calls.append("operator")

    def show_admin_dialog(self):
        self.calls.append("dialog")

    def show_auth_error(self):
        self.calls.append("auth_error")

    def show_admin_session(self):
        self.calls.append("admin")

    def show_restore_result(self):
        self.calls.append("restore")


class FakeRestore(object):
    def run(self):
        return None


class FakeAudit(object):
    def __init__(self):
        self.events = []

    def emit(self, name, level="Info", **fields):
        self.events.append((name, level, fields))


class ProcessResult(object):
    def __init__(self, status, pid=None):
        self.status = status
        self.pid = pid
        self.error_code = None
        self.conflict_pids = ()
        self.failure_count = 0


class FakeSupervisor(object):
    def __init__(self):
        self.pid = None
        self.start_calls = 0
        self.tick_calls = 0

    def start(self):
        self.start_calls += 1
        self.pid = 10
        return ProcessResult("started", 10)

    def tick(self):
        self.tick_calls += 1
        return ProcessResult("running", self.pid)

    def stop_supervision(self):
        previous = self.pid
        self.pid = None
        return ProcessResult("stopped", previous)


class FakeWindowApi(object):
    def __init__(self):
        self.minimized = set()
        self.restore_calls = []
        self.foreground_calls = []

    def windows_for_pid(self, pid):
        return [100] if pid == 10 else []

    def is_minimized(self, hwnd):
        return hwnd in self.minimized

    def restore_window(self, hwnd, maximized=False):
        self.restore_calls.append((hwnd, maximized))
        self.minimized.discard(hwnd)
        return True

    def bring_to_front(self, hwnd):
        self.foreground_calls.append(hwnd)
        return True


class LegacyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kiosk-v2-legacy-runtime-")
        self.config_path = os.path.join(self.temp_dir, "kiosk.v2.json")
        self.schema = load_json(
            os.path.join(V2_ROOT, "contracts", "kiosk-config-v2.schema.json")
        )
        self.default = load_json(
            os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json")
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_repository_reads_bom_and_writes_through_replacer_then_acl(self):
        raw = json.dumps(self.default, ensure_ascii=False).encode("utf-8")
        with open(self.config_path, "wb") as stream:
            stream.write(b"\xef\xbb\xbf" + raw)
        replacer = FakeReplacer()
        acl = FakeAcl()
        repository = LegacyConfigRepository(
            self.config_path,
            LegacyConfigValidator(self.schema),
            replacer=replacer,
            acl=acl,
        )

        self.assertEqual(self.default, repository.load())
        updated = copy.deepcopy(self.default)
        updated["operatorUser"] = "test"
        repository.save(updated)

        self.assertEqual(1, len(replacer.calls))
        self.assertEqual([self.config_path], acl.calls)
        self.assertEqual("test", repository.load()["operatorUser"])

    def test_legacy_repository_replace_failure_preserves_previous_bytes(self):
        before = b"previous-bytes"
        with open(self.config_path, "wb") as stream:
            stream.write(before)
        repository = LegacyConfigRepository(
            self.config_path,
            LegacyConfigValidator(self.schema),
            replacer=FakeReplacer(OSError("replace failed")),
            acl=FakeAcl(),
        )

        with self.assertRaises(OSError):
            repository.save(self.default)

        with open(self.config_path, "rb") as stream:
            self.assertEqual(before, stream.read())

    def test_controller_keeps_guards_through_dialog_and_stops_after_success(self):
        behavior = load_json(
            os.path.join(V2_ROOT, "contracts", "behavior-cases.json")
        )
        desktop = Toggle()
        keyboard = Toggle()
        supervisor = SupervisorToggle()
        view = FakeView()
        effects = RuntimeEffects(
            desktop, keyboard, supervisor, view, FakeRestore()
        )
        audit = FakeAudit()
        controller = AppController(StateMachine(behavior), effects, audit=audit)

        controller.handle("boot_completed")
        controller.handle("unlock_requested")
        self.assertTrue(desktop.running)
        self.assertTrue(keyboard.running)
        controller.handle("auth_succeeded")

        self.assertFalse(desktop.running)
        self.assertFalse(keyboard.running)
        self.assertEqual("ADMIN_SESSION", controller.state)
        self.assertEqual(3, len(audit.events))

    def test_controller_rolls_back_completed_effects_on_failure(self):
        behavior = load_json(
            os.path.join(V2_ROOT, "contracts", "behavior-cases.json")
        )

        class FailingEffects(object):
            def __init__(self):
                self.completed = []
                self.rolled_back = []

            def run(self, name):
                if name == "start_supervisor":
                    raise RuntimeError("secret message")
                self.completed.append(name)

            def rollback(self, name):
                self.rolled_back.append(name)

        effects = FailingEffects()
        controller = AppController(StateMachine(behavior), effects)

        with self.assertRaises(EffectExecutionError) as raised:
            controller.handle("boot_completed")

        self.assertEqual("STARTING", controller.state)
        self.assertEqual(
            ["start_keyboard_guard", "start_desktop_isolation"],
            effects.rolled_back,
        )
        self.assertNotIn("secret message", str(raised.exception))

    def test_application_runtime_reports_minimized_without_duplicate_then_restores(self):
        supervisor = FakeSupervisor()
        windows = FakeWindowApi()
        runtime = ApplicationRuntime(
            supervisor,
            WindowCoordinator(windows),
            start_maximized=False,
        )
        runtime.start()
        windows.foreground_calls = []
        windows.minimized.add(100)

        minimized = runtime.tick()
        self.assertEqual("minimized", minimized.window_status)
        self.assertEqual([], windows.restore_calls)
        restored = runtime.restore_application()

        self.assertEqual("visible", restored.window_status)
        self.assertEqual([(100, False)], windows.restore_calls)
        self.assertEqual(1, supervisor.start_calls)


if __name__ == "__main__":
    unittest.main()
