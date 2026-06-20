# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_modern.app.bootstrap import LauncherBootstrap as ModernBootstrap
from kiosk_v2_modern.app.controller import AppController as ModernController
from kiosk_v2_modern.app.effects import RuntimeEffects as ModernEffects
from kiosk_v2_modern.app.session import LauncherSession as ModernSession
from kiosk_v2_modern.domain.state_machine import StateMachine as ModernMachine
from kiosk_v2_modern.launcher import LauncherEntrypoint as ModernLauncherEntrypoint
from kiosk_v2_modern.launcher import build_native_bootstrap as modern_native_bootstrap
from kiosk_v2_modern.launcher import resolve_runtime_files as modern_runtime_files
from kiosk_v2_modern.platform.admin_actions import AdminActionLauncher as ModernAdminActions
from kiosk_v2_modern.restore_entrypoint import RestoreEntrypoint as ModernRestoreEntrypoint
from kiosk_v2_modern.restore_entrypoint import LazyRestoreService as ModernLazyRestore
from kiosk_v2_legacy.app.bootstrap import LauncherBootstrap as LegacyBootstrap
from kiosk_v2_legacy.app.controller import AppController as LegacyController
from kiosk_v2_legacy.app.effects import RuntimeEffects as LegacyEffects
from kiosk_v2_legacy.app.session import LauncherSession as LegacySession
from kiosk_v2_legacy.domain.state_machine import StateMachine as LegacyMachine
from kiosk_v2_legacy.launcher import LauncherEntrypoint as LegacyLauncherEntrypoint
from kiosk_v2_legacy.launcher import build_native_bootstrap as legacy_native_bootstrap
from kiosk_v2_legacy.launcher import resolve_runtime_files as legacy_runtime_files
from kiosk_v2_legacy.platform.admin_actions import AdminActionLauncher as LegacyAdminActions
from kiosk_v2_legacy.restore_entrypoint import RestoreEntrypoint as LegacyRestoreEntrypoint
from kiosk_v2_legacy.restore_entrypoint import LazyRestoreService as LegacyLazyRestore


class FakeConfigRepository(object):
    def __init__(self, calls):
        self.calls = calls

    def load(self, require_existing_app=False):
        self.calls.append(("config", require_existing_app))
        return {"operatorUser": "test"}


class FakeSettingsFactory(object):
    def __init__(self, calls):
        self.calls = calls

    def build(self, config):
        self.calls.append(("settings", config["operatorUser"]))
        return object()


class FakeDpi(object):
    def __init__(self, calls):
        self.calls = calls

    def enable(self):
        self.calls.append("dpi")


class FakeRoot(object):
    def __init__(self, calls):
        self.calls = calls
        self.after_calls = []

    def mainloop(self):
        self.calls.append("mainloop")

    def after(self, milliseconds, callback):
        self.after_calls.append((milliseconds, callback))
        return len(self.after_calls)


class FakeBuiltSession(object):
    def __init__(self, calls):
        self.calls = calls

    def start(self):
        self.calls.append("session.start")

    def close(self):
        self.calls.append("session.close")


class OrderedComponent(object):
    def __init__(self, calls, name):
        self.calls = calls
        self.name = name
        self.running = False

    def start(self):
        self.calls.append(self.name + ".start")
        self.running = True

    def stop(self):
        self.calls.append(self.name + ".stop")
        self.running = False

    def tick(self):
        self.calls.append(self.name + ".tick")


class OrderedApplication(OrderedComponent):
    def __init__(self, calls):
        OrderedComponent.__init__(self, calls, "application")
        self.enabled = False
        self.latest_result = None

    def start(self):
        OrderedComponent.start(self)
        self.enabled = True

    def stop_supervision(self):
        self.calls.append("application.stop_supervision")
        self.enabled = False

    def resume_supervision(self):
        self.calls.append("application.resume_supervision")
        self.enabled = True

    def restore_application(self, **unused):
        self.calls.append("application.restore")

    def tick(self, **unused):
        self.calls.append("application.tick")


class FakeView(object):
    def __init__(self, calls):
        self.calls = calls

    def show_operator(self):
        self.calls.append("view.operator")

    def show_admin_dialog(self):
        self.calls.append("view.dialog")

    def show_auth_error(self):
        self.calls.append("view.auth_error")

    def show_admin_session(self):
        self.calls.append("view.admin")

    def show_restore_result(self):
        self.calls.append("view.restore_result")

    def refresh(self):
        self.calls.append("view.refresh")

    def set_auth_error(self, message):
        self.calls.append(("view.auth_message", message))


class FakeRestore(object):
    def __init__(self, calls):
        self.calls = calls

    def run(self):
        self.calls.append("restore.run")


class FakeRecovery(object):
    def restore_shell_surfaces(self):
        return ()

    def start_explorer(self):
        return True


class FakeClock(object):
    def __init__(self):
        self.value = 100.0

    def monotonic(self):
        return self.value


class FakeAuthResult(object):
    def __init__(self, success, code="success", retry_after_seconds=0):
        self.success = success
        self.code = code
        self.retry_after_seconds = retry_after_seconds

    def to_log_data(self):
        return {"success": self.success, "code": self.code}


class FakeAuth(object):
    def __init__(self, result):
        self.result = result

    def authenticate(self, username, password):
        return self.result


class FakeGuard(object):
    def __init__(self, calls):
        self.calls = calls

    def check(self):
        self.calls.append("guard")


class FakeBootstrap(object):
    def __init__(self, calls):
        self.calls = calls

    def run(self):
        self.calls.append("bootstrap.run")
        return 0


class FakeCli(object):
    def __init__(self, calls):
        self.calls = calls

    def run(self, argv):
        self.calls.append(("cli.run", tuple(argv)))
        return 0


class FakeAdminActionApi(object):
    def __init__(self):
        self.calls = []

    def run_elevated(self, executable, arguments):
        self.calls.append((executable, arguments))
        return True


class FakeRestoreService(object):
    def __init__(self, calls):
        self.calls = calls

    def restore(self):
        self.calls.append("restore")
        return "restored"

    def uninstall(self):
        self.calls.append("uninstall")
        return "uninstalled"

    def recover_desktop(self, recovery):
        self.calls.append(("recover", recovery))
        return "recovered"


def behavior_contract():
    with open(os.path.join(V2_ROOT, "contracts", "behavior-cases.json"), "rb") as stream:
        return json.loads(stream.read().decode("utf-8"))


class BootstrapTests(unittest.TestCase):
    def test_config_is_validated_and_dpi_precedes_tk_for_both_builds(self):
        for bootstrap_class in (ModernBootstrap, LegacyBootstrap):
            calls = []
            root = FakeRoot(calls)

            def root_factory():
                calls.append("tk")
                return root

            def session_factory(created_root, settings, config):
                self.assertIs(root, created_root)
                self.assertEqual("test", config["operatorUser"])
                calls.append("session.factory")
                return FakeBuiltSession(calls)

            bootstrap = bootstrap_class(
                FakeConfigRepository(calls),
                FakeSettingsFactory(calls),
                FakeDpi(calls),
                root_factory,
                session_factory,
            )
            bootstrap.run()
            self.assertEqual(
                [
                    ("config", True),
                    ("settings", "test"),
                    "dpi",
                    "tk",
                    "session.factory",
                    "session.start",
                    "mainloop",
                    "session.close",
                ],
                calls,
            )

    def test_family_guard_precedes_launcher_composition_for_both_builds(self):
        for entrypoint_class in (ModernLauncherEntrypoint, LegacyLauncherEntrypoint):
            calls = []

            def bootstrap_factory():
                calls.append("bootstrap.factory")
                return FakeBootstrap(calls)

            result = entrypoint_class(
                FakeGuard(calls),
                bootstrap_factory,
            ).run()

            self.assertEqual(0, result)
            self.assertEqual(
                ["guard", "bootstrap.factory", "bootstrap.run"],
                calls,
            )

    def test_restore_entrypoint_delegates_without_launcher_runtime(self):
        for entrypoint_class in (ModernRestoreEntrypoint, LegacyRestoreEntrypoint):
            calls = []
            entrypoint = entrypoint_class(lambda: FakeCli(calls))

            result = entrypoint.run(["restore", "--apply"])

            self.assertEqual(0, result)
            self.assertEqual([("cli.run", ("restore", "--apply"))], calls)

    def test_restore_service_is_built_lazily_and_recovery_stays_independent(self):
        for lazy_class in (ModernLazyRestore, LegacyLazyRestore):
            calls = []

            def service_factory():
                calls.append("factory")
                return FakeRestoreService(calls)

            lazy = lazy_class(service_factory)
            self.assertEqual([], calls)
            self.assertEqual("recovered", lazy.recover_desktop("desktop-api"))
            self.assertEqual(
                ["factory", ("recover", "desktop-api")],
                calls,
            )
            calls[:] = []
            self.assertEqual("restored", lazy.restore())
            self.assertEqual(["factory", "restore"], calls)

    def test_restore_sources_do_not_import_ui_launcher_or_keyboard_hook(self):
        paths = (
            os.path.join(V2_ROOT, "modern", "kiosk_v2_modern", "restore_entrypoint.py"),
            os.path.join(V2_ROOT, "legacy", "kiosk_v2_legacy", "restore_entrypoint.py"),
        )
        for path in paths:
            with open(path, "rb") as stream:
                source = stream.read().decode("utf-8").lower()
            self.assertNotIn(".ui", source)
            self.assertNotIn("keyboard_guard", source)
            self.assertNotIn("from kiosk_v2_modern.launcher", source)
            self.assertNotIn("from kiosk_v2_legacy.launcher", source)

    def test_admin_actions_use_external_elevation_without_credentials(self):
        for action_class in (ModernAdminActions, LegacyAdminActions):
            api = FakeAdminActionApi()
            actions = action_class(
                restore_executable="Restore.exe",
                configurator_executable="Configurator.exe",
                api=api,
            )

            self.assertTrue(actions.run())
            self.assertTrue(actions.change_application())

            self.assertEqual(
                [
                    ("Restore.exe", 'restore --apply'),
                    ("Configurator.exe", 'configure-application'),
                ],
                api.calls,
            )
            serialized = repr(api.calls).lower()
            self.assertNotIn("password", serialized)
            self.assertNotIn("credential", serialized)

    def test_frozen_runtime_files_keep_configuration_external(self):
        for resolver in (modern_runtime_files, legacy_runtime_files):
            files = resolver(
                executable_directory="C:\\KioskV2",
                resource_directory="C:\\KioskV2\\resources",
            )

            self.assertEqual(
                "C:\\KioskV2\\config\\kiosk.v2.json",
                files.config_path,
            )
            self.assertEqual(
                "C:\\KioskV2\\resources\\contracts\\kiosk-config-v2.schema.json",
                files.schema_path,
            )
            self.assertEqual(
                "C:\\KioskV2\\resources\\contracts\\behavior-cases.json",
                files.behavior_path,
            )
            self.assertEqual(
                "C:\\KioskV2\\Restore.exe",
                files.restore_executable,
            )
            self.assertEqual(
                "C:\\KioskV2\\Configurator.exe",
                files.configurator_executable,
            )

    def test_native_composition_builds_bootstrap_without_starting_tk_or_guards(self):
        config_path = os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json")
        schema_path = os.path.join(
            V2_ROOT,
            "contracts",
            "kiosk-config-v2.schema.json",
        )
        behavior_path = os.path.join(
            V2_ROOT,
            "contracts",
            "behavior-cases.json",
        )
        for resolver, builder in (
            (modern_runtime_files, modern_native_bootstrap),
            (legacy_runtime_files, legacy_native_bootstrap),
        ):
            files = resolver(PROJECT_ROOT, V2_ROOT)
            files.config_path = config_path
            files.schema_path = schema_path
            files.behavior_path = behavior_path
            bootstrap = builder(files, root_factory=lambda: None)

            self.assertTrue(hasattr(bootstrap, "run"))
            self.assertEqual(config_path, bootstrap.config_repository.config_path)


class SessionTests(unittest.TestCase):
    def _build(self, family, auth_result=None):
        calls = []
        root = FakeRoot(calls)
        desktop = OrderedComponent(calls, "desktop")
        keyboard = OrderedComponent(calls, "keyboard")
        application = OrderedApplication(calls)
        view = FakeView(calls)
        restore = FakeRestore(calls)
        clock = FakeClock()
        if family == "modern":
            machine = ModernMachine(behavior_contract())
            effects = ModernEffects(desktop, keyboard, application, view, restore)
            controller = ModernController(machine, effects)
            session_class = ModernSession
        else:
            machine = LegacyMachine(behavior_contract())
            effects = LegacyEffects(desktop, keyboard, application, view, restore)
            controller = LegacyController(machine, effects)
            session_class = LegacySession
        session = session_class(
            root=root,
            controller=controller,
            application=application,
            desktop=desktop,
            keyboard=keyboard,
            view=view,
            auth=FakeAuth(auth_result or FakeAuthResult(True)),
            recovery=FakeRecovery(),
            clock=clock,
            admin_timeout_seconds=30,
            tick_interval_ms=250,
        )
        return session, calls, root, clock

    def test_guards_start_before_allowed_application(self):
        for family in ("modern", "legacy"):
            session, calls, root, _clock = self._build(family)
            session.start()
            self.assertEqual(
                [
                    "desktop.start",
                    "keyboard.start",
                    "application.start",
                    "view.operator",
                ],
                calls[:4],
            )
            self.assertEqual(1, len(root.after_calls))

    def test_keyboard_guard_stays_active_during_dialog_and_stops_after_success(self):
        for family in ("modern", "legacy"):
            session, calls, _root, _clock = self._build(family)
            session.start()
            session.handle_action("unlock")
            self.assertIn("view.dialog", calls)
            self.assertNotIn("keyboard.stop", calls)
            session.submit_credentials("Administrator", "not-logged")
            self.assertIn("keyboard.stop", calls)
            self.assertIn("desktop.stop", calls)
            self.assertEqual("ADMIN_SESSION", session.controller.state)

    def test_failed_auth_returns_to_operator_without_stopping_guards(self):
        for family in ("modern", "legacy"):
            session, calls, _root, _clock = self._build(
                family,
                FakeAuthResult(False, "not_administrator"),
            )
            session.start()
            session.handle_action("unlock")
            session.submit_credentials("test", "not-logged")
            self.assertEqual("OPERATOR", session.controller.state)
            self.assertNotIn("keyboard.stop", calls)
            messages = [item for item in calls if isinstance(item, tuple)]
            self.assertTrue(messages)
            message = messages[-1][1]
            if not isinstance(message, type(u"")):
                message = message.decode("utf-8")
            self.assertIn(u"не является администратором", message)

    def test_admin_timeout_restores_operator_guards(self):
        for family in ("modern", "legacy"):
            session, calls, root, clock = self._build(family)
            session.start()
            session.handle_action("unlock")
            session.submit_credentials("Administrator", "not-logged")
            clock.value += 31
            session.tick()
            self.assertEqual("OPERATOR", session.controller.state)
            self.assertGreaterEqual(calls.count("keyboard.start"), 2)
            self.assertGreaterEqual(calls.count("desktop.start"), 2)


if __name__ == "__main__":
    unittest.main()
