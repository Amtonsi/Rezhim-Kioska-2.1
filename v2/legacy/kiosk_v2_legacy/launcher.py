# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import ntpath
import os
import sys
from kiosk_v2_legacy.platform.interactive_operator import InteractiveOperatorGuard, OperatorLaunchDenied


try:
    text_type = unicode
except NameError:
    text_type = str


from kiosk_v2_legacy.platform.runtime_path import coerce_runtime_directory


class RuntimeFiles(object):
    def __init__(
        self,
        config_path,
        schema_path,
        behavior_path,
        restore_executable,
        configurator_executable,
    ):
        self.config_path = config_path
        self.schema_path = schema_path
        self.behavior_path = behavior_path
        self.restore_executable = restore_executable
        self.configurator_executable = configurator_executable


def resolve_runtime_files(executable_directory, resource_directory):
    return RuntimeFiles(
        ntpath.join(executable_directory, "config", "kiosk.v2.json"),
        ntpath.join(
            resource_directory,
            "contracts",
            "kiosk-config-v2.schema.json",
        ),
        ntpath.join(resource_directory, "contracts", "behavior-cases.json"),
        ntpath.join(executable_directory, "Restore.exe"),
        ntpath.join(executable_directory, "Configurator.exe"),
    )


class LauncherEntrypoint(object):
    def __init__(self, family_guard, bootstrap_factory):
        self.family_guard = family_guard
        self.bootstrap_factory = bootstrap_factory

    def run(self):
        self.family_guard.check()
        return self.bootstrap_factory().run()


class ConfigCheck(object):
    def __init__(self, repository, settings_factory):
        self.repository = repository
        self.settings_factory = settings_factory

    def run(self):
        config = self.repository.load(require_existing_app=True)
        self.settings_factory.build(config)
        return 0


class LauncherCommand(object):
    def __init__(
        self,
        family_guard,
        bootstrap_factory,
        config_check,
        error_handler=None,
    ):
        self.family_guard = family_guard
        self.bootstrap_factory = bootstrap_factory
        self.config_check = config_check
        self.error_handler = error_handler or (lambda _message: None)

    def run(self, argv):
        arguments = list(argv or ())
        if arguments == ["--platform-check"]:
            try:
                self.family_guard.check()
                return 0
            except Exception:
                return 4
        if arguments == ["--check-config"]:
            try:
                self.family_guard.check()
            except RuntimeError:
                return 4
            return self.config_check.run()
        if arguments:
            raise ValueError("Unsupported launcher arguments")
        try:
            return LauncherEntrypoint(
                self.family_guard,
                self.bootstrap_factory,
            ).run()
        except OperatorLaunchDenied as error:
            self.error_handler(text_type(error))
            return 5
        except RuntimeError as error:
            self.error_handler(text_type(error))
            return 4


class ManagedLauncherSession(object):
    def __init__(self, session, resources=()):
        self.session = session
        self.resources = tuple(resources)

    def __getattr__(self, name):
        return getattr(self.session, name)

    def close(self):
        try:
            self.session.close()
        finally:
            resources, self.resources = self.resources, ()
            for resource in reversed(resources):
                try:
                    resource.close()
                except Exception:
                    pass


def build_native_bootstrap(files, root_factory=None):
    from kiosk_v2_legacy.app.admin_auth_service import RateLimitedAdminAuth
    from kiosk_v2_legacy.app.application_runtime import ApplicationRuntime
    from kiosk_v2_legacy.app.bootstrap import LauncherBootstrap
    from kiosk_v2_legacy.app.config_repository import (
        LegacyConfigRepository,
        LegacyConfigValidator,
    )
    from kiosk_v2_legacy.app.controller import AppController
    from kiosk_v2_legacy.app.effects import RuntimeEffects
    from kiosk_v2_legacy.app.process_supervisor import ProcessSupervisor
    from kiosk_v2_legacy.app.runtime_settings import RuntimeSettingsFactory
    from kiosk_v2_legacy.app.session import (
        LauncherSession,
        ObservedApplication,
        select_application,
    )
    from kiosk_v2_legacy.app.window_coordinator import WindowCoordinator
    from kiosk_v2_legacy.domain.state_machine import StateMachine
    from kiosk_v2_legacy.platform.admin_actions import AdminActionLauncher
    from kiosk_v2_legacy.platform.admin_auth import WindowsAdminAuth
    from kiosk_v2_legacy.platform.audit_log import AuditLogger
    from kiosk_v2_legacy.platform.clock import TickCountClock
    from kiosk_v2_legacy.platform.command_line import WindowsArgumentParser
    from kiosk_v2_legacy.platform.desktop_isolation import (
        DesktopIsolation,
        LegacyDesktopApi,
    )
    from kiosk_v2_legacy.platform.desktop_recovery import WindowsDesktopRecovery
    from kiosk_v2_legacy.platform.dpi import WindowsDpiAwareness
    from kiosk_v2_legacy.platform.keyboard_guard import KeyboardGuard, NativeHookLoop
    from kiosk_v2_legacy.platform.process_runtime import LegacyProcessRuntime
    from kiosk_v2_legacy.platform.window_api import LegacyWindowApi
    from kiosk_v2_legacy.ui.tk_view import KioskCanvasView

    if root_factory is None:
        import Tkinter

        root_factory = Tkinter.Tk

    schema = _load_json(files.schema_path)
    behavior = _load_json(files.behavior_path)
    repository = LegacyConfigRepository(
        files.config_path,
        LegacyConfigValidator(schema),
    )
    settings_factory = RuntimeSettingsFactory(WindowsArgumentParser())

    def create_session(root, settings, _config):
        clock = TickCountClock()
        desktop_api = LegacyDesktopApi()
        desktop = DesktopIsolation(
            desktop_api,
            terminate_explorer=True,
        )
        recovery = WindowsDesktopRecovery(desktop_api)
        keyboard = KeyboardGuard(NativeHookLoop())
        def build_configured_application(runtime_settings):
            supervisor = ProcessSupervisor(
                runtime_settings.application,
                LegacyProcessRuntime(),
                clock,
            )
            runtime = ApplicationRuntime(
                supervisor,
                WindowCoordinator(LegacyWindowApi()),
                start_maximized=runtime_settings.window.start_maximized,
            )
            return ObservedApplication(runtime, runtime_settings.application.path)

        def build_application(runtime_settings):
            return select_application(
                runtime_settings,
                os.path.isfile,
                build_configured_application,
            )

        application = build_application(settings)
        auth = RateLimitedAdminAuth(WindowsAdminAuth(), clock)
        log_path = os.path.join(
            settings.logging.log_directory,
            "kiosk-v2-legacy.jsonl",
        )
        audit = AuditLogger(
            log_path,
            settings.logging.max_bytes,
            settings.logging.backup_count,
            level=settings.logging.level,
        )
        admin_actions = AdminActionLauncher(
            files.restore_executable,
            files.configurator_executable,
        )
        holder = {}

        def change_application():
            current_application = holder["session"].application
            current_path = ntpath.normcase(
                ntpath.normpath(current_application.application_path)
            )
            admin_actions.change_application()
            updated = settings_factory.build(
                repository.load(require_existing_app=False)
            )
            updated_path = ntpath.normcase(
                ntpath.normpath(updated.application.path)
            )
            replacement = build_application(updated)
            same_path = updated_path == current_path
            same_state = bool(replacement.configured) == bool(
                current_application.configured
            )
            if same_path and same_state:
                return None
            return replacement

        view = KioskCanvasView(
            root,
            model_provider=lambda: holder["session"].model(),
            action_handler=lambda action: holder["session"].handle_action(action),
            auth_submit=lambda username, password: holder["session"].submit_credentials(
                username,
                password,
            ),
            auth_cancel=lambda: holder["session"].cancel_authentication(),
            shell_interaction=lambda: holder["session"].handle_shell_interaction(),
        )
        effects = RuntimeEffects(
            desktop,
            keyboard,
            application,
            view,
            admin_actions,
        )
        controller = AppController(
            StateMachine(behavior),
            effects,
            audit=audit,
        )
        session = LauncherSession(
            root=root,
            controller=controller,
            application=application,
            desktop=desktop,
            keyboard=keyboard,
            view=view,
            auth=auth,
            recovery=recovery,
            clock=clock,
            admin_timeout_seconds=settings.security.admin_session_timeout_seconds,
            tick_interval_ms=settings.security.explorer_guard_interval_ms,
            audit=audit,
            change_application=change_application,
            restore_action=admin_actions,
        )
        managed = ManagedLauncherSession(session, (audit,))
        holder["session"] = managed
        return managed

    return LauncherBootstrap(
        repository,
        settings_factory,
        WindowsDpiAwareness(),
        root_factory,
        create_session,
        InteractiveOperatorGuard(),
    )


def run_default(argv=None, executable_directory=None, resource_directory=None):
    executable_directory = coerce_runtime_directory(
        executable_directory
        or os.path.dirname(os.path.abspath(sys.executable)),
        required_children=("config",),
    )
    resource_directory = coerce_runtime_directory(
        resource_directory or getattr(
        sys,
        "_MEIPASS",
        executable_directory,
        ),
        required_children=("contracts",),
    )
    files = resolve_runtime_files(executable_directory, resource_directory)
    from kiosk_v2_legacy.app.config_repository import (
        LegacyConfigRepository,
        LegacyConfigValidator,
    )
    from kiosk_v2_legacy.app.runtime_settings import RuntimeSettingsFactory
    from kiosk_v2_legacy.platform.command_line import WindowsArgumentParser
    from kiosk_v2_legacy.platform.error_dialog import WindowsErrorDialog
    from kiosk_v2_legacy.platform.family_guard import WindowsFamilyGuard

    schema = _load_json(files.schema_path)
    config_check = ConfigCheck(
        LegacyConfigRepository(files.config_path, LegacyConfigValidator(schema)),
        RuntimeSettingsFactory(WindowsArgumentParser()),
    )
    return LauncherCommand(
        WindowsFamilyGuard(),
        lambda: build_native_bootstrap(files),
        config_check,
        error_handler=WindowsErrorDialog().show,
    ).run(sys.argv[1:] if argv is None else argv)


def _load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return json.load(stream)
