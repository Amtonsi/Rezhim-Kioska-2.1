# -*- coding: utf-8 -*-
import io
import json
import ntpath
import os
import sys
import time


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
    def __init__(self, family_guard, bootstrap_factory, config_check):
        self.family_guard = family_guard
        self.bootstrap_factory = bootstrap_factory
        self.config_check = config_check

    def run(self, argv):
        arguments = list(argv or ())
        if arguments == ["--platform-check"]:
            try:
                self.family_guard.check()
                return 0
            except Exception:
                return 4
        if arguments == ["--check-config"]:
            self.family_guard.check()
            return self.config_check.run()
        if arguments:
            raise ValueError("Unsupported launcher arguments")
        return LauncherEntrypoint(
            self.family_guard,
            self.bootstrap_factory,
        ).run()


class MonotonicClock(object):
    def monotonic(self):
        return time.monotonic()


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
            for resource in reversed(self.resources):
                try:
                    resource.close()
                except Exception:
                    pass


def build_native_bootstrap(files, root_factory=None):
    from kiosk_v2_modern.app.admin_auth_service import RateLimitedAdminAuth
    from kiosk_v2_modern.app.application_runtime import ApplicationRuntime
    from kiosk_v2_modern.app.bootstrap import LauncherBootstrap
    from kiosk_v2_modern.app.config_repository import ConfigRepository, ConfigValidator
    from kiosk_v2_modern.app.controller import AppController
    from kiosk_v2_modern.app.effects import RuntimeEffects
    from kiosk_v2_modern.app.process_supervisor import ProcessSupervisor
    from kiosk_v2_modern.app.runtime_settings import RuntimeSettingsFactory
    from kiosk_v2_modern.app.session import LauncherSession, ObservedApplication
    from kiosk_v2_modern.app.window_coordinator import WindowCoordinator
    from kiosk_v2_modern.domain.state_machine import StateMachine
    from kiosk_v2_modern.platform.admin_actions import AdminActionLauncher
    from kiosk_v2_modern.platform.admin_auth import WindowsAdminAuth
    from kiosk_v2_modern.platform.audit_log import AuditLogger
    from kiosk_v2_modern.platform.command_line import WindowsArgumentParser
    from kiosk_v2_modern.platform.desktop_isolation import (
        DesktopIsolation,
        WindowsProcessApi,
        WindowsShellSurfaceApi,
    )
    from kiosk_v2_modern.platform.desktop_recovery import WindowsDesktopRecovery
    from kiosk_v2_modern.platform.dpi import WindowsDpiAwareness
    from kiosk_v2_modern.platform.keyboard_guard import KeyboardGuard, NativeHookLoop
    from kiosk_v2_modern.platform.process_runtime import WindowsProcessRuntime
    from kiosk_v2_modern.platform.window_api import WindowsWindowApi
    from kiosk_v2_modern.ui.tk_view import KioskCanvasView

    if root_factory is None:
        import tkinter

        root_factory = tkinter.Tk

    schema = _load_json(files.schema_path)
    behavior = _load_json(files.behavior_path)
    repository = ConfigRepository(
        files.config_path,
        ConfigValidator(schema),
    )
    settings_factory = RuntimeSettingsFactory(WindowsArgumentParser())

    def create_session(root, settings, _config):
        clock = MonotonicClock()
        process_api = WindowsProcessApi()
        surface_api = WindowsShellSurfaceApi()
        desktop = DesktopIsolation(process_api, surface_api)
        recovery = WindowsDesktopRecovery(process_api, surface_api)
        keyboard = KeyboardGuard(NativeHookLoop())
        supervisor = ProcessSupervisor(
            settings.application,
            WindowsProcessRuntime(),
            clock,
        )
        runtime = ApplicationRuntime(
            supervisor,
            WindowCoordinator(WindowsWindowApi()),
            start_maximized=settings.window.start_maximized,
        )
        application = ObservedApplication(runtime, settings.application.path)
        auth = RateLimitedAdminAuth(WindowsAdminAuth(), clock)
        log_path = os.path.join(
            settings.logging.log_directory,
            "kiosk-v2-modern.jsonl",
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
        view = KioskCanvasView(
            root,
            model_provider=lambda: holder["session"].model(),
            action_handler=lambda action: holder["session"].handle_action(action),
            auth_submit=lambda username, password: holder["session"].submit_credentials(
                username,
                password,
            ),
            auth_cancel=lambda: holder["session"].cancel_authentication(),
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
            change_application=admin_actions.change_application,
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
    )


def run_default(argv=None, executable_directory=None, resource_directory=None):
    executable_directory = executable_directory or os.path.dirname(
        os.path.abspath(sys.executable)
    )
    resource_directory = resource_directory or getattr(
        sys,
        "_MEIPASS",
        executable_directory,
    )
    files = resolve_runtime_files(executable_directory, resource_directory)
    from kiosk_v2_modern.app.config_repository import ConfigRepository, ConfigValidator
    from kiosk_v2_modern.app.runtime_settings import RuntimeSettingsFactory
    from kiosk_v2_modern.platform.command_line import WindowsArgumentParser
    from kiosk_v2_modern.platform.family_guard import WindowsFamilyGuard

    schema = _load_json(files.schema_path)
    config_check = ConfigCheck(
        ConfigRepository(files.config_path, ConfigValidator(schema)),
        RuntimeSettingsFactory(WindowsArgumentParser()),
    )
    return LauncherCommand(
        WindowsFamilyGuard(),
        lambda: build_native_bootstrap(files),
        config_check,
    ).run(sys.argv[1:] if argv is None else argv)


def _load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return json.load(stream)
