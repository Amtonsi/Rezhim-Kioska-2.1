# -*- coding: utf-8 -*-

import json
import os
import shutil
import tempfile
import unittest

from python_kiosk.backup_store import BackupStore
from python_kiosk.config import KioskConfig
from python_kiosk.shell_ui import build_shell_layout


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_ROOT = os.path.join(PROJECT_ROOT, "contracts")


def load_contract(name):
    with open(os.path.join(CONTRACT_ROOT, name), "r", encoding="utf-8") as stream:
        return json.load(stream)


class FakePlan(object):
    def to_dict(self):
        return {"operations": []}


class ModernCrossBuildContractTests(unittest.TestCase):
    def test_modern_round_trips_canonical_config_without_credentials(self):
        source = load_contract("kiosk-config-v1.json")

        result = KioskConfig.from_dict(source).to_dict()

        self.assertEqual(source, result)
        self.assertNotIn("password", json.dumps(result).lower())

    def test_modern_backup_contains_versioned_common_metadata(self):
        contract = load_contract("backup-metadata-v1.json")
        temp_dir = tempfile.mkdtemp()
        try:
            config = KioskConfig.from_dict(load_contract("kiosk-config-v1.json"))
            path = BackupStore(temp_dir).create_backup(
                config, FakePlan(), allow_user_fallback=False
            )
            with open(path, "r", encoding="utf-8") as stream:
                payload = json.load(stream)
        finally:
            shutil.rmtree(temp_dir)

        self.assertEqual(contract["schemaVersion"], payload["schemaVersion"])
        self.assertEqual("modern", payload["buildFamily"])
        for field in contract["requiredCommonFields"]:
            self.assertIn(field, payload)
        for field in contract["families"]["modern"]:
            self.assertIn(field, payload)

    def test_modern_layout_matches_shared_russian_labels(self):
        expected = load_contract("ui-labels-v1.json")
        items = {}
        for state in (
            {},
            {"app_status": "minimized"},
            {"admin_session_active": True},
        ):
            items.update(
                {
                    item["name"]: item.get("text")
                    for item in build_shell_layout(
                        r"C:\Windows\notepad.exe", **state
                    )
                    if item.get("kind") == "text"
                }
            )

        for name, text in expected.items():
            self.assertEqual(text, items[name])


if __name__ == "__main__":
    unittest.main()
