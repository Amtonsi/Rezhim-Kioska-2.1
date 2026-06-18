# -*- coding: utf-8 -*-

import io
import json
import os
import unittest

from legacy_kiosk.config import validate_config
from legacy_kiosk.shell_ui import build_shell_layout
from legacy_kiosk.system_backend import LegacyInstallContext, LegacySystemBackend


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_ROOT = os.path.join(PROJECT_ROOT, "contracts")


def load_contract(name):
    with io.open(os.path.join(CONTRACT_ROOT, name), "r", encoding="utf-8") as stream:
        return json.load(stream)


class CapturingBackupStore(object):
    def __init__(self):
        self.payload = None

    def save(self, path, payload):
        self.payload = payload


class FakeAccountInspector(object):
    def is_current_process_admin(self):
        return True

    def inspect_local_operator(self, account_name):
        return {
            "account_name": account_name,
            "sid": "S-1-5-21-TEST-1001",
            "profile_path": r"C:\Documents and Settings\KioskOperator",
            "is_admin": False,
        }


class FakeRegistry(object):
    def snapshot_values(self, operator_sid, profile_path, targets):
        return [
            {
                "group": target["group"],
                "key": target["key"],
                "name": target["name"],
                "exists": target["group"] == "shell",
                "type": 1 if target["group"] == "shell" else None,
                "data": "explorer.exe" if target["group"] == "shell" else None,
            }
            for target in targets
        ]


class FakeSecurity(object):
    def snapshot_paths(self, paths):
        return []


class LegacyCrossBuildContractTests(unittest.TestCase):
    def test_legacy_accepts_canonical_config_without_credentials(self):
        source = load_contract("kiosk-config-v1.json")

        result = validate_config(source)

        self.assertEqual(source, result)
        self.assertNotIn("password", json.dumps(result).lower())

    def test_legacy_backup_contains_versioned_common_metadata(self):
        contract = load_contract("backup-metadata-v1.json")
        store = CapturingBackupStore()
        backend = LegacySystemBackend(
            account_inspector=FakeAccountInspector(),
            registry_adapter=FakeRegistry(),
            security_adapter=FakeSecurity(),
            backup_store=store,
        )
        context = LegacyInstallContext(
            config={
                "operatorUser": "KioskOperator",
                "allowedApplication": {"path": r"C:\Windows\notepad.exe"},
            },
            launcher_path=r"C:\Kiosk\RezhimKioska-Legacy.exe",
            config_path=r"C:\Kiosk\config\kiosk.json",
            backup_path=r"C:\Kiosk\backup\legacy-backup.json",
        )
        backend.validate_operator(context)
        backend.create_backup(context)
        payload = store.payload

        self.assertEqual(contract["schemaVersion"], payload["schemaVersion"])
        self.assertEqual("legacy", payload["buildFamily"])
        for field in contract["requiredCommonFields"]:
            self.assertIn(field, payload)
        for field in contract["families"]["legacy"]:
            self.assertIn(field, payload)

    def test_legacy_layout_matches_shared_russian_labels(self):
        expected = load_contract("ui-labels-v1.json")
        items = {}
        for state in (
            {},
            {"app_status": "minimized"},
            {"admin_session_active": True},
        ):
            items.update(
                dict(
                    (item["name"], item.get("text"))
                    for item in build_shell_layout(
                        r"C:\Windows\notepad.exe", **state
                    )
                    if item.get("kind") == "text"
                )
            )

        for name, text in expected.items():
            self.assertEqual(text, items[name])


if __name__ == "__main__":
    unittest.main()
