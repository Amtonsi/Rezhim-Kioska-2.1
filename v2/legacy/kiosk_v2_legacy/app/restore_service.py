# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from kiosk_v2_legacy.platform.file_acl import AclSnapshot
from kiosk_v2_legacy.platform.operator_registry import RegistryValueSnapshot


class RestoreResult(object):
    def __init__(self, failures=(), restored_ids=(), artifact_snapshot=None):
        self.failures = tuple(failures)
        self.restored_ids = tuple(restored_ids)
        self.artifact_snapshot = artifact_snapshot
        self.succeeded = not self.failures


class RestoreService(object):
    def __init__(self, backup_store, preflight, profile_locator, registry_factory,
                 acl_manager, artifacts):
        self.backup_store = backup_store
        self.preflight = preflight
        self.profile_locator = profile_locator
        self.registry_factory = registry_factory
        self.acl_manager = acl_manager
        self.artifacts = artifacts

    def restore(self, expected_operator_user=None):
        document = self.backup_store.load("legacy", None)
        user = document["operatorUser"]
        if expected_operator_user is not None and user != expected_operator_user:
            raise ValueError("operator mismatch")
        identity = self.preflight.validate(user)
        if identity.sid != document["operatorSid"]:
            raise ValueError("operator SID mismatch")
        profile = self.profile_locator.get_profile_path(identity.sid)
        registry_items = [RegistryValueSnapshot.from_dict(item) for item in document["registryValues"]]
        acl_items = [AclSnapshot.from_dict(item) for item in document["fileAcls"]]
        artifact = document["configBackup"]
        if not isinstance(artifact, dict):
            raise ValueError("invalid artifact backup")
        registry = self.registry_factory(identity.sid, profile)
        failures = []
        restored = []

        try:
            self.artifacts.restore(artifact)
            if not self.artifacts.verify_snapshot(artifact):
                raise RuntimeError("artifact verify failed")
        except Exception:
            failures.append("artifacts")
        else:
            restored.append("artifacts")
        for item in acl_items:
            item_id = "acl:{0}".format(os.path.basename(item.path))
            try:
                self.acl_manager.restore(item)
                if not self.acl_manager.verify_snapshot(item):
                    raise RuntimeError("ACL verify failed")
            except Exception:
                failures.append(item_id)
            else:
                restored.append(item_id)
        for item in registry_items:
            item_id = "registry:{0}".format(item.value_name)
            try:
                registry.restore(item)
                if not registry.verify_snapshot(item):
                    raise RuntimeError("registry verify failed")
            except Exception:
                failures.append(item_id)
            else:
                restored.append(item_id)
        return RestoreResult(failures, restored, artifact)

    def uninstall(self, expected_operator_user=None):
        result = self.restore(expected_operator_user)
        if result.succeeded:
            try:
                self.artifacts.remove_owned(result.artifact_snapshot)
            except Exception:
                return RestoreResult(("remove_owned",), result.restored_ids, result.artifact_snapshot)
        return result

    @staticmethod
    def recover_desktop(recovery_api):
        recovery_api.restore_shell_surfaces()
        if not recovery_api.explorer_running():
            recovery_api.start_explorer()
