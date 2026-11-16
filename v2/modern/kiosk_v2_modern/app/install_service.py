# -*- coding: utf-8 -*-
import os

from kiosk_v2_modern.app.transaction import InstallTransaction, Operation
from kiosk_v2_modern.platform.operator_registry import (
    OPERATOR_POLICY_VALUES,
    REG_SZ,
)


SHELL_KEY_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
SHELL_VALUE_NAME = "Shell"


class InstallResult(object):
    def __init__(
        self,
        operation_ids,
        succeeded,
        dry_run,
        backup_path=None,
        transaction_result=None,
    ):
        self.operation_ids = tuple(operation_ids)
        self.succeeded = bool(succeeded)
        self.dry_run = bool(dry_run)
        self.backup_path = backup_path
        self.transaction_result = transaction_result


class InstallService(object):
    def __init__(
        self,
        preflight,
        profile_locator,
        registry_factory,
        acl_manager,
        artifacts,
        backup_store,
        install_directory,
        launcher_path,
        config_path,
        protect_allowed_app=True,
    ):
        self.preflight = preflight
        self.profile_locator = profile_locator
        self.registry_factory = registry_factory
        self.acl_manager = acl_manager
        self.artifacts = artifacts
        self.protect_allowed_app = protect_allowed_app
        self.backup_store = backup_store
        self.install_directory = self._normalize(install_directory)
        self.launcher_path = self._normalize(launcher_path)
        self.config_path = self._normalize(config_path)

    def plan(self, config, launcher_command):
        operator_user, allowed_path = self._validate_request(config, launcher_command)
        identity = self.preflight.validate(operator_user)
        self.profile_locator.get_profile_path(identity.sid)
        acl_targets = self._acl_targets(allowed_path)
        operation_ids = ["install_artifacts"]
        operation_ids.extend("protect_acl:{0}".format(label) for label, _path, _execute in acl_targets)
        operation_ids.extend(
            "set_policy:{0}".format(value_name)
            for _key_path, value_name, _value_type, _value_data in OPERATOR_POLICY_VALUES
        )
        operation_ids.append("set_operator_shell")
        return tuple(operation_ids)

    def apply(self, config, launcher_command, dry_run=False):
        return self._apply(
            config,
            launcher_command,
            dry_run=dry_run,
            save_original_backup=True,
        )

    def repair(self, config, launcher_command, dry_run=False):
        return self._apply(
            config,
            launcher_command,
            dry_run=dry_run,
            save_original_backup=False,
        )

    def _apply(
        self,
        config,
        launcher_command,
        dry_run,
        save_original_backup,
    ):
        operator_user, allowed_path = self._validate_request(config, launcher_command)
        identity = self.preflight.validate(operator_user)
        profile_path = self.profile_locator.get_profile_path(identity.sid)
        operation_ids = self._operation_ids(allowed_path)
        if dry_run:
            if not save_original_backup or os.path.exists(self.backup_store.path):
                self.backup_store.load("modern", identity.sid)
            return InstallResult(operation_ids, True, True)

        registry = self.registry_factory(identity.sid, profile_path)
        policy_snapshots = []
        for key_path, value_name, _value_type, _value_data in OPERATOR_POLICY_VALUES:
            policy_snapshots.append(registry.capture(key_path, value_name))
        shell_snapshot = registry.capture(SHELL_KEY_PATH, SHELL_VALUE_NAME)

        acl_targets = self._acl_targets(allowed_path)
        acl_snapshots = [
            self.acl_manager.capture(path) for _label, path, _execute in acl_targets
        ]
        artifact_snapshot = self.artifacts.capture()
        metadata = {
            "schemaVersion": 2,
            "buildFamily": "modern",
            "operatorSid": identity.sid,
            "operatorUser": identity.username,
            "originalShell": (
                shell_snapshot.value_data
                if shell_snapshot.existed and isinstance(shell_snapshot.value_data, str)
                else ""
            ),
            "registryValues": [
                snapshot.to_dict()
                for snapshot in policy_snapshots + [shell_snapshot]
            ],
            "fileAcls": [snapshot.to_dict() for snapshot in acl_snapshots],
            "configBackup": artifact_snapshot,
        }
        if save_original_backup and not os.path.exists(self.backup_store.path):
            self.backup_store.save(metadata)
        self.backup_store.load(
            expected_build_family="modern",
            expected_operator_sid=identity.sid,
        )

        operations = [
            Operation(
                "install_artifacts",
                apply=self.artifacts.install,
                rollback=lambda: self.artifacts.restore(artifact_snapshot),
                verify=self.artifacts.verify,
            )
        ]
        for target, snapshot in zip(acl_targets, acl_snapshots):
            label, path, execute = target
            expected = {}

            def apply_acl(path=path, execute=execute, expected=expected):
                expected["sddl"] = self.acl_manager.protect_for_operator(
                    path,
                    identity.sid,
                    execute=execute,
                )

            def verify_acl(path=path, expected=expected):
                return self.acl_manager.verify(path, expected["sddl"])

            operations.append(
                Operation(
                    "protect_acl:{0}".format(label),
                    apply=apply_acl,
                    rollback=lambda snapshot=snapshot: self.acl_manager.restore(snapshot),
                    verify=verify_acl,
                )
            )

        for policy, snapshot in zip(OPERATOR_POLICY_VALUES, policy_snapshots):
            key_path, value_name, value_type, value_data = policy
            operations.append(
                Operation(
                    "set_policy:{0}".format(value_name),
                    apply=lambda key_path=key_path, value_name=value_name, value_type=value_type, value_data=value_data: registry.apply(
                        key_path,
                        value_name,
                        value_type,
                        value_data,
                    ),
                    rollback=lambda snapshot=snapshot: registry.restore(snapshot),
                    verify=lambda key_path=key_path, value_name=value_name, value_type=value_type, value_data=value_data: registry.verify(
                        key_path,
                        value_name,
                        value_type,
                        value_data,
                    ),
                )
            )

        def verify_shell_and_backup():
            if not registry.verify(
                SHELL_KEY_PATH,
                SHELL_VALUE_NAME,
                REG_SZ,
                launcher_command,
            ):
                return False
            self.backup_store.load(
                expected_build_family="modern",
                expected_operator_sid=identity.sid,
            )
            return True

        operations.append(
            Operation(
                "set_operator_shell",
                apply=lambda: registry.apply(
                    SHELL_KEY_PATH,
                    SHELL_VALUE_NAME,
                    REG_SZ,
                    launcher_command,
                ),
                rollback=lambda: registry.restore(shell_snapshot),
                verify=verify_shell_and_backup,
                is_shell=True,
            )
        )
        transaction_result = InstallTransaction(operations).execute()
        return InstallResult(
            operation_ids,
            True,
            False,
            backup_path=self.backup_store.path,
            transaction_result=transaction_result,
        )

    def _operation_ids(self, allowed_path):
        operation_ids = ["install_artifacts"]
        operation_ids.extend(
            "protect_acl:{0}".format(label)
            for label, _path, _execute in self._acl_targets(allowed_path)
        )
        operation_ids.extend(
            "set_policy:{0}".format(value_name)
            for _key_path, value_name, _value_type, _value_data in OPERATOR_POLICY_VALUES
        )
        operation_ids.append("set_operator_shell")
        return tuple(operation_ids)

    def _acl_targets(self, allowed_path):
        candidates = [
            ("install_directory", self.install_directory, True),
            ("launcher", self.launcher_path, True),
            ("config", self.config_path, False),
        ]
        if self.protect_allowed_app and self._is_inside_install_directory(allowed_path):
            candidates.append(("allowed_application", allowed_path, True))
        unique = []
        seen = set()
        for target in candidates:
            normalized = self._normalize(target[1])
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append((target[0], normalized, target[2]))
        return tuple(unique)

    def _validate_request(self, config, launcher_command):
        if not isinstance(config, dict):
            raise ValueError("configuration must be an object")
        operator_user = str(config.get("operatorUser") or "").strip()
        application = config.get("allowedApplication")
        if not isinstance(application, dict):
            raise ValueError("allowedApplication is required")
        allowed_path = self._normalize(application.get("path") or "")
        if not os.path.isabs(allowed_path) or not allowed_path.lower().endswith(".exe"):
            raise ValueError("allowed application must be an absolute .exe path")
        if not os.path.isfile(allowed_path):
            raise ValueError("allowed application does not exist")
        if not operator_user:
            raise ValueError("operatorUser is required")
        if not str(launcher_command or "").strip():
            raise ValueError("launcher command is required")
        return operator_user, allowed_path

    def _is_inside_install_directory(self, path):
        try:
            return os.path.commonpath((self.install_directory, self._normalize(path))) == self.install_directory
        except ValueError:
            return False

    def _normalize(self, path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))
