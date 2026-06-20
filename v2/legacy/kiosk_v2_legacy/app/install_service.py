# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from kiosk_v2_legacy.app.transaction import InstallTransaction, Operation
from kiosk_v2_legacy.platform.operator_registry import OPERATOR_POLICY_VALUES, REG_SZ


try:
    text_type = unicode
except NameError:
    text_type = str


SHELL_KEY_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
SHELL_VALUE_NAME = "Shell"


class InstallResult(object):
    def __init__(self, operation_ids, succeeded, dry_run, backup_path=None, transaction_result=None):
        self.operation_ids = tuple(operation_ids)
        self.succeeded = bool(succeeded)
        self.dry_run = bool(dry_run)
        self.backup_path = backup_path
        self.transaction_result = transaction_result


class InstallService(object):
    def __init__(self, preflight, profile_locator, registry_factory, acl_manager,
                 artifacts, backup_store, install_directory, launcher_path, config_path):
        self.preflight = preflight
        self.profile_locator = profile_locator
        self.registry_factory = registry_factory
        self.acl_manager = acl_manager
        self.artifacts = artifacts
        self.backup_store = backup_store
        self.install_directory = self._normalize(install_directory)
        self.launcher_path = self._normalize(launcher_path)
        self.config_path = self._normalize(config_path)

    def plan(self, config, launcher_command):
        user, allowed = self._validate(config, launcher_command)
        identity = self.preflight.validate(user)
        self.profile_locator.get_profile_path(identity.sid)
        return self._operation_ids(allowed)

    def apply(self, config, launcher_command, dry_run=False):
        return self._apply(config, launcher_command, dry_run, True)

    def repair(self, config, launcher_command, dry_run=False):
        return self._apply(config, launcher_command, dry_run, False)

    def _apply(self, config, launcher_command, dry_run, save_backup):
        user, allowed = self._validate(config, launcher_command)
        identity = self.preflight.validate(user)
        profile = self.profile_locator.get_profile_path(identity.sid)
        operation_ids = self._operation_ids(allowed)
        if dry_run:
            return InstallResult(operation_ids, True, True)
        registry = self.registry_factory(identity.sid, profile)
        policy_snapshots = [
            registry.capture(key, name)
            for key, name, unused_type, unused_data in OPERATOR_POLICY_VALUES
        ]
        shell_snapshot = registry.capture(SHELL_KEY_PATH, SHELL_VALUE_NAME)
        targets = self._acl_targets(allowed)
        acl_snapshots = [self.acl_manager.capture(path) for unused, path, execute in targets]
        artifact_snapshot = self.artifacts.capture()
        metadata = {
            "schemaVersion": 2,
            "buildFamily": "legacy",
            "operatorSid": identity.sid,
            "operatorUser": identity.username,
            "originalShell": shell_snapshot.value_data
                if shell_snapshot.existed and isinstance(shell_snapshot.value_data, text_type)
                else "",
            "registryValues": [item.to_dict() for item in policy_snapshots + [shell_snapshot]],
            "fileAcls": [item.to_dict() for item in acl_snapshots],
            "configBackup": artifact_snapshot,
        }
        if save_backup:
            self.backup_store.save(metadata)
        self.backup_store.load("legacy", identity.sid)

        operations = [Operation(
            "install_artifacts",
            self.artifacts.install,
            lambda: self.artifacts.restore(artifact_snapshot),
            self.artifacts.verify,
        )]
        for target, snapshot in zip(targets, acl_snapshots):
            label, path, execute = target
            holder = {}

            def apply_acl(path=path, execute=execute, holder=holder):
                holder["sddl"] = self.acl_manager.protect_for_operator(
                    path, identity.sid, execute
                )

            operations.append(Operation(
                "protect_acl:{0}".format(label),
                apply_acl,
                lambda snapshot=snapshot: self.acl_manager.restore(snapshot),
                lambda path=path, holder=holder: self.acl_manager.verify(path, holder["sddl"]),
            ))
        for policy, snapshot in zip(OPERATOR_POLICY_VALUES, policy_snapshots):
            key, name, value_type, data = policy
            operations.append(Operation(
                "set_policy:{0}".format(name),
                lambda key=key, name=name, value_type=value_type, data=data: registry.apply(
                    key, name, value_type, data
                ),
                lambda snapshot=snapshot: registry.restore(snapshot),
                lambda key=key, name=name, value_type=value_type, data=data: registry.verify(
                    key, name, value_type, data
                ),
            ))

        def verify_shell():
            if not registry.verify(
                SHELL_KEY_PATH, SHELL_VALUE_NAME, REG_SZ, launcher_command
            ):
                return False
            self.backup_store.load("legacy", identity.sid)
            return True

        operations.append(Operation(
            "set_operator_shell",
            lambda: registry.apply(
                SHELL_KEY_PATH, SHELL_VALUE_NAME, REG_SZ, launcher_command
            ),
            lambda: registry.restore(shell_snapshot),
            verify_shell,
            is_shell=True,
        ))
        transaction = InstallTransaction(operations).execute()
        return InstallResult(
            operation_ids, True, False, self.backup_store.path, transaction
        )

    def _operation_ids(self, allowed):
        result = ["install_artifacts"]
        result.extend("protect_acl:{0}".format(item[0]) for item in self._acl_targets(allowed))
        result.extend("set_policy:{0}".format(item[1]) for item in OPERATOR_POLICY_VALUES)
        result.append("set_operator_shell")
        return tuple(result)

    def _acl_targets(self, allowed):
        result = [
            ("install_directory", self.install_directory, True),
            ("launcher", self.launcher_path, True),
            ("config", self.config_path, False),
        ]
        if self._inside(allowed):
            result.append(("allowed_application", allowed, True))
        unique = []
        seen = set()
        for label, path, execute in result:
            path = self._normalize(path)
            if path not in seen:
                seen.add(path)
                unique.append((label, path, execute))
        return tuple(unique)

    def _validate(self, config, launcher_command):
        if not isinstance(config, dict):
            raise ValueError("configuration object required")
        user = text_type(config.get("operatorUser") or "").strip()
        app = config.get("allowedApplication")
        if not isinstance(app, dict):
            raise ValueError("allowedApplication required")
        allowed = self._normalize(app.get("path") or "")
        if not os.path.isabs(allowed) or not allowed.lower().endswith(".exe"):
            raise ValueError("absolute .exe required")
        if not os.path.isfile(allowed):
            raise ValueError("allowed application missing")
        if not user or not launcher_command:
            raise ValueError("operator and launcher required")
        return user, allowed

    def _inside(self, path):
        path = self._normalize(path)
        return path == self.install_directory or path.startswith(
            self.install_directory.rstrip("\\/") + os.sep
        )

    @staticmethod
    def _normalize(path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))
