# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
        from kiosk_v2_legacy.app.install_artifacts import FileArtifactManager
        from kiosk_v2_legacy.app.restore_service import RestoreService

        document = self.backup_store.load(
            expected_build_family=self.build_family,
            expected_operator_sid=None,
        )
        targets = tuple(
            item["path"] for item in document["configBackup"]["files"]
        )
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
        from kiosk_v2_legacy.platform.operator_account import PreflightError

        if not self.preflight.account_api.is_elevated():
            raise PreflightError("elevation_required")


class UnsupportedInstallService(object):
    def apply(self, *unused, **unused_keywords):
        raise RuntimeError("install is not available in Restore")

    def repair(self, *unused, **unused_keywords):
        raise RuntimeError("repair is not available in Restore")


def build_native_restore_entrypoint(executable_directory=None):
    from kiosk_v2_legacy.app.backup_store import BackupStore
    from kiosk_v2_legacy.cli import KioskCli
    from kiosk_v2_legacy.platform.desktop_isolation import LegacyDesktopApi
    from kiosk_v2_legacy.platform.desktop_recovery import WindowsDesktopRecovery
    from kiosk_v2_legacy.platform.file_acl import FileAclManager
    from kiosk_v2_legacy.platform.operator_account import OperatorPreflight
    from kiosk_v2_legacy.platform.operator_registry import OperatorRegistryStore
    from kiosk_v2_legacy.platform.profile_path import WindowsProfileLocator

    directory = os.path.abspath(
        executable_directory
        or os.path.dirname(os.path.abspath(sys.executable))
    )
    backup_path = os.path.join(directory, "state", "backup-v2.json")
    acl = FileAclManager((directory,))
    backup = BackupStore(backup_path, acl)
    preflight = OperatorPreflight()
    profile_locator = WindowsProfileLocator()
    recovery = WindowsDesktopRecovery(LegacyDesktopApi())

    def service_factory():
        return NativeRestoreService(
            "legacy",
            backup,
            preflight,
            profile_locator,
            lambda sid, profile: OperatorRegistryStore(sid, profile),
            acl,
            directory,
            os.path.abspath(sys.executable),
        )

    def cli_factory():
        return KioskCli(
            UnsupportedInstallService(),
            LazyRestoreService(service_factory),
            config_loader=lambda unused: {},
            recovery_api=recovery,
        )

    return RestoreEntrypoint(cli_factory)


def run_default(argv=None, executable_directory=None):
    return build_native_restore_entrypoint(executable_directory).run(
        list(sys.argv[1:] if argv is None else argv)
    )
