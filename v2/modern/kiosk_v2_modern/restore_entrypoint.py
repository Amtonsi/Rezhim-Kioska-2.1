# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes
import io
import json
import os
import sys


class RestoreEntrypoint(object):
    def __init__(self, cli_factory):
        self.cli_factory = cli_factory

    def run(self, argv):
        return self.cli_factory().run(argv)


class LazyRestoreService(object):
    def __init__(self, service_factory):
        self.service_factory = service_factory

    def restore(self):
        return self.service_factory().restore()

    def uninstall(self):
        return self.service_factory().uninstall()

    def recover_desktop(self, recovery):
        return self.service_factory().recover_desktop(recovery)


class NativeRestoreService(object):
    def __init__(
        self,
        build_family,
        backup_store,
        preflight,
        profile_locator,
        registry_factory,
        acl_manager,
        approved_root,
        artifact_source,
    ):
        self.build_family = build_family
        self.backup_store = backup_store
        self.preflight = preflight
        self.profile_locator = profile_locator
        self.registry_factory = registry_factory
        self.acl_manager = acl_manager
        self.approved_root = os.path.abspath(approved_root)
        self.artifact_source = artifact_source

    def restore(self):
        return self._service().restore()

    def uninstall(self):
        return self._service().uninstall()

    def recover_desktop(self, recovery):
        self._require_elevation()
        recovery.restore_shell_surfaces()
        if not recovery.explorer_running():
            recovery.start_explorer()

    def _service(self):
        from kiosk_v2_modern.app.install_artifacts import FileArtifactManager
        from kiosk_v2_modern.app.restore_service import RestoreService

        validate_package_directory(self.approved_root, (self.backup_store.path,))
        document = self.backup_store.load(
            expected_build_family=self.build_family,
            expected_operator_sid=None,
        )
        snapshot = document["configBackup"]
        if snapshot == PortableArtifacts.snapshot():
            from kiosk_v2_modern.app.install_service import SHELL_KEY_PATH, SHELL_VALUE_NAME
            from kiosk_v2_modern.platform.operator_registry import OPERATOR_POLICY_VALUES

            expected_registry = set((key, name) for key, name, _type, _data in OPERATOR_POLICY_VALUES)
            expected_registry.add((SHELL_KEY_PATH, SHELL_VALUE_NAME))
            registry = [(item["keyPath"], item["valueName"]) for item in document["registryValues"]]
            if set(registry) != expected_registry or len(registry) != len(expected_registry):
                raise ValueError("unexpected registry targets in portable backup")
            paths = [item["path"] for item in document["fileAcls"]]
            expected = (self.approved_root,
                        os.path.join(self.approved_root, "RezhimKioska-V2-Modern.exe"),
                        os.path.join(self.approved_root, "config", "kiosk.v2.json"))
            if set(map(normalized, paths)) != set(map(normalized, expected)) or len(paths) != len(expected):
                raise ValueError("unexpected ACL targets in portable backup")
            validate_package_directory(self.approved_root, paths)
            artifacts = PortableArtifacts(())
        else:
            targets = tuple(item["path"] for item in snapshot["files"])
            artifacts = FileArtifactManager(
                tuple((self.artifact_source, target) for target in targets),
                (self.approved_root,),
            )
        return RestoreService(
            self.backup_store,
            self.preflight,
            self.profile_locator,
            self.registry_factory,
            self.acl_manager,
            artifacts,
        )

    def _require_elevation(self):
        from kiosk_v2_modern.platform.operator_account import PreflightError

        if not self.preflight.account_api.is_elevated():
            raise PreflightError("elevation_required")


class PortableArtifacts(object):
    """The unpacked package is already in place. Own no user files."""

    def __init__(self, required_files):
        self.required_files = tuple(required_files)

    @staticmethod
    def snapshot():
        return {"kind": "preinstalled", "schemaVersion": 1}

    def capture(self):
        return self.snapshot()

    def install(self):
        if not self.verify():
            raise ValueError("incomplete portable package")

    def verify(self):
        return all(os.path.isfile(path) for path in self.required_files)

    def verify_snapshot(self, snapshot):
        return snapshot == self.snapshot()

    def restore(self, snapshot):
        if not self.verify_snapshot(snapshot):
            raise ValueError("invalid portable package backup")

    remove_owned = restore


def normalized(path):
    return os.path.normcase(os.path.abspath(path))


def validate_package_directory(directory, paths):
    root = normalized(directory)
    if root == os.path.dirname(root) or root.startswith("\\\\"):
        raise ValueError("use a dedicated local kiosk directory")
    reserved = ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432",
                "ProgramData", "USERPROFILE", "PUBLIC", "ALLUSERSPROFILE")
    for name in reserved:
        value = os.environ.get(name)
        if value and root == normalized(value):
            raise ValueError("use a dedicated kiosk directory")
    windows = os.environ.get("SystemRoot")
    if windows and root.startswith(normalized(windows) + os.sep):
        raise ValueError("place the kiosk outside the Windows directory")

    attributes = ctypes.windll.kernel32.GetFileAttributesW
    attributes.argtypes = [wintypes.LPCWSTR]
    attributes.restype = wintypes.DWORD
    checked = set()
    for path in paths:
        child = normalized(path)
        while child not in checked:
            checked.add(child)
            if os.path.exists(child):
                result = attributes(child)
                if result == 0xffffffff or result & 0x400:
                    raise ValueError("package paths must not traverse reparse points")
            parent = os.path.dirname(child)
            if parent == child:
                break
            child = parent


class MaintenanceLock(object):
    """Serialize registry and backup mutations across administrator sessions."""

    def __enter__(self):
        kernel = ctypes.windll.kernel32
        kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = kernel.CreateMutexW(None, False, u"Global\\RezhimKioska.V2.Maintenance")
        if not self.handle:
            raise ctypes.WinError()
        if kernel.WaitForSingleObject(self.handle, 0) not in (0, 0x80):
            kernel.CloseHandle(self.handle)
            raise RuntimeError("another kiosk maintenance command is running")
        return self

    def __exit__(self, *_unused):
        kernel = ctypes.windll.kernel32
        kernel.ReleaseMutex(self.handle)
        kernel.CloseHandle(self.handle)


class PackageInstall(object):
    def __init__(self, directory, schema_path, service, artifacts, family_guard):
        self.directory = directory
        self.config = os.path.join(directory, "config", "kiosk.v2.json")
        self.launcher = os.path.join(directory, "RezhimKioska-V2-Modern.exe")
        self.schema_path = schema_path
        self.service = service
        self.artifacts = artifacts
        self.family_guard = family_guard

    def load(self, path):
        from kiosk_v2_modern.app.config_repository import ConfigRepository, ConfigValidator
        from kiosk_v2_modern.app.runtime_settings import RuntimeSettingsFactory
        from kiosk_v2_modern.platform.command_line import WindowsArgumentParser

        self.family_guard.check()
        validate_package_directory(self.directory, self.artifacts.required_files + (
            os.path.join(self.directory, "state", "backup-v2.json"),
        ))
        if normalized(path) != normalized(self.config):
            raise ValueError("use the package config/kiosk.v2.json")
        if not self.artifacts.verify():
            raise ValueError("incomplete portable package")
        with io.open(self.schema_path, "r", encoding="utf-8-sig") as stream:
            validator = ConfigValidator(json.load(stream))
        config = ConfigRepository(self.config, validator).load(require_existing_app=True)
        if not config["allowedApplication"].get("configured", True):
            raise ValueError("configure the allowed application first")
        RuntimeSettingsFactory(WindowsArgumentParser()).build(config)
        return config

    def _command(self, launcher_command):
        command = launcher_command
        if len(command) >= 2 and command.startswith('"') and command.endswith('"'):
            command = command[1:-1]
        if normalized(command) != normalized(self.launcher):
            raise ValueError("use the launcher in this package without arguments")
        return '"{0}"'.format(self.launcher)

    def apply(self, config, launcher_command, dry_run=False):
        return self.service.apply(config, self._command(launcher_command), dry_run=dry_run)

    def repair(self, config, launcher_command, dry_run=False):
        return self.service.repair(config, self._command(launcher_command), dry_run=dry_run)


def build_native_restore_entrypoint(executable_directory=None):
    from kiosk_v2_modern.app.install_service import InstallService
    from kiosk_v2_modern.platform.family_guard import WindowsFamilyGuard
    from kiosk_v2_modern.app.backup_store import BackupStore
    from kiosk_v2_modern.cli import KioskCli
    from kiosk_v2_modern.platform.desktop_isolation import (
        WindowsProcessApi,
        WindowsShellSurfaceApi,
    )
    from kiosk_v2_modern.platform.desktop_recovery import WindowsDesktopRecovery
    from kiosk_v2_modern.platform.file_acl import FileAclManager
    from kiosk_v2_modern.platform.operator_account import OperatorPreflight
    from kiosk_v2_modern.platform.operator_registry import OperatorRegistryStore
    from kiosk_v2_modern.platform.profile_path import WindowsProfileLocator

    directory = os.path.abspath(
        executable_directory
        or os.path.dirname(os.path.abspath(sys.executable))
    )
    backup_path = os.path.join(directory, "state", "backup-v2.json")
    acl = FileAclManager((directory,))
    backup = BackupStore(backup_path, acl)
    preflight = OperatorPreflight()
    profile_locator = WindowsProfileLocator()
    process_api = WindowsProcessApi()
    surface_api = WindowsShellSurfaceApi()
    recovery = WindowsDesktopRecovery(process_api, surface_api)

    def service_factory():
        return NativeRestoreService(
            "modern",
            backup,
            preflight,
            profile_locator,
            lambda sid, profile: OperatorRegistryStore(sid, profile),
            acl,
            directory,
            os.path.abspath(sys.executable),
        )

    launcher = os.path.join(directory, "RezhimKioska-V2-Modern.exe")
    config = os.path.join(directory, "config", "kiosk.v2.json")
    resources = getattr(sys, "_MEIPASS", directory)
    artifacts = PortableArtifacts((
        launcher, config, os.path.join(directory, "Restore.exe"),
        os.path.join(directory, "Configurator.exe"),
    ))
    install = InstallService(
        preflight, profile_locator,
        lambda sid, profile: OperatorRegistryStore(sid, profile),
        acl, artifacts, backup, directory, launcher, config,
        protect_allowed_app=False,
    )
    package = PackageInstall(
        directory, os.path.join(resources, "contracts", "kiosk-config-v2.schema.json"),
        install, artifacts, WindowsFamilyGuard(),
    )

    def cli_factory():
        return KioskCli(
            package,
            LazyRestoreService(service_factory),
            config_loader=package.load,
            recovery_api=recovery,
            config_path=config,
            launcher_command=launcher,
        )

    return RestoreEntrypoint(cli_factory)


def run_default(argv=None, executable_directory=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    entrypoint = build_native_restore_entrypoint(executable_directory)
    if arguments and arguments[0] in ("install", "repair", "restore", "uninstall", "test-mode") and "--apply" in arguments:
        try:
            with MaintenanceLock():
                return entrypoint.run(arguments)
        except (OSError, RuntimeError) as error:
            sys.stderr.write("kiosk-v2: {0!r}\n".format(error))
            return 2
    return entrypoint.run(arguments)
