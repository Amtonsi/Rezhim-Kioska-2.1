# -*- coding: utf-8 -*-
import os

from kiosk_v2_modern.platform.file_acl import AclSnapshot
from kiosk_v2_modern.platform.operator_registry import RegistryValueSnapshot


class RestoreResult(object):
    def __init__(self, failures=(), restored_ids=(), artifact_snapshot=None):
        self.failures = tuple(failures)
        self.restored_ids = tuple(restored_ids)
        self.artifact_snapshot = artifact_snapshot
        self.succeeded = not self.failures


class RestoreService(object):
    def __init__(
        self,
        backup_store,
        preflight,
        profile_locator,
        registry_factory,
        acl_manager,
        artifacts,
    ):
        self.backup_store = backup_store
        self.preflight = preflight
        self.profile_locator = profile_locator
        self.registry_factory = registry_factory
        self.acl_manager = acl_manager
        self.artifacts = artifacts

    def restore(self, expected_operator_user=None):
        document = self.backup_store.load(
            expected_build_family="modern",
            expected_operator_sid=None,
        )
        operator_user = document["operatorUser"]
        if expected_operator_user is not None and operator_user != expected_operator_user:
            raise ValueError("backup operator user mismatch")
        identity = self.preflight.validate(operator_user)
        if identity.sid != document["operatorSid"]:
            raise ValueError("backup operator SID mismatch")
        profile_path = self.profile_locator.get_profile_path(identity.sid)

        registry_snapshots = [
            RegistryValueSnapshot.from_dict(item)
            for item in document["registryValues"]
        ]
        acl_snapshots = [
            AclSnapshot.from_dict(item) for item in document["fileAcls"]
        ]
        artifact_snapshot = document["configBackup"]
        if not isinstance(artifact_snapshot, dict):
            raise ValueError("invalid artifact backup")

        registry = self.registry_factory(identity.sid, profile_path)
        failures = []
        restored = []

        try:
            self.artifacts.restore(artifact_snapshot)
            if not self.artifacts.verify_snapshot(artifact_snapshot):
                raise RuntimeError("artifact verification failed")
        except Exception:
            failures.append("artifacts")
        else:
            restored.append("artifacts")

        for snapshot in acl_snapshots:
            item_id = "acl:{0}".format(os.path.basename(snapshot.path))
            try:
                self.acl_manager.restore(snapshot)
                if not self.acl_manager.verify_snapshot(snapshot):
                    raise RuntimeError("ACL verification failed")
            except Exception:
                failures.append(item_id)
            else:
                restored.append(item_id)

        for snapshot in registry_snapshots:
            item_id = "registry:{0}".format(snapshot.value_name)
            try:
                registry.restore(snapshot)
                if not registry.verify_snapshot(snapshot):
                    raise RuntimeError("registry verification failed")
            except Exception:
                failures.append(item_id)
            else:
                restored.append(item_id)

        return RestoreResult(failures, restored, artifact_snapshot)

    def uninstall(self, expected_operator_user=None):
        result = self.restore(expected_operator_user=expected_operator_user)
        if not result.succeeded:
            return result
        try:
            self.artifacts.remove_owned(result.artifact_snapshot)
        except Exception:
            return RestoreResult(
                failures=("remove_owned",),
                restored_ids=result.restored_ids,
                artifact_snapshot=result.artifact_snapshot,
            )
        return result

    def recover_desktop(self, recovery_api):
        recovery_api.restore_shell_surfaces()
        if not recovery_api.explorer_running():
            recovery_api.start_explorer()
