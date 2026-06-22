# -*- coding: utf-8 -*-
import json
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRACTS = os.path.join(ROOT, "contracts")
PROJECT_ROOT = os.path.dirname(ROOT)


def load(name):
    with open(os.path.join(CONTRACTS, name), "r", encoding="utf-8") as stream:
        return json.load(stream)


class ContractDocumentTests(unittest.TestCase):
    def test_v2_default_matches_every_required_contract_field(self):
        schema = load("kiosk-config-v2.schema.json")
        with open(
            os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json"),
            "r",
            encoding="utf-8",
        ) as stream:
            default = json.load(stream)

        self.assertEqual(set(schema["required"]), set(default))
        for section in ("allowedApplication", "kiosk", "logging", "testing"):
            section_schema = schema["properties"][section]
            required = set(section_schema["required"])
            properties = set(section_schema["properties"])
            actual = set(default[section])
            self.assertTrue(required.issubset(actual))
            self.assertTrue(actual.issubset(properties))
        self.assertEqual(2, default["schemaVersion"])
        self.assertEqual(r"C:\Windows\System32\notepad.exe", default["allowedApplication"]["path"])
        self.assertFalse(default["allowedApplication"]["configured"])
        self.assertEqual(
            "boolean",
            schema["properties"]["allowedApplication"]["properties"]["configured"]["type"],
        )
        self.assertNotIn(
            "configured",
            schema["properties"]["allowedApplication"]["required"],
        )
        self.assertFalse(default["allowedApplication"]["restoreIfMinimized"])
        self.assertTrue(default["kiosk"]["allowWinL"])
        self.assertTrue(default["testing"]["requireBackupBeforeTest"])
        self.assertTrue(default["testing"]["restoreAfterTest"])
        self.assertTrue(default["testing"]["testOnlySeparateOperatorUser"])

    def test_config_schema_is_version_two_and_contains_no_credentials(self):
        schema = load("kiosk-config-v2.schema.json")
        text = json.dumps(schema, ensure_ascii=False).lower()

        self.assertEqual(2, schema["properties"]["schemaVersion"]["const"])
        self.assertEqual(
            [
                "schemaVersion",
                "operatorUser",
                "allowedApplication",
                "kiosk",
                "logging",
                "testing",
            ],
            schema["required"],
        )
        for forbidden in ("password", "credential", "token", "secret"):
            self.assertNotIn(forbidden, text)
        allowed = schema["properties"]["allowedApplication"]
        self.assertIn("maxRestartAttempts", allowed["required"])
        self.assertIn("restartWindowSeconds", allowed["required"])

    def test_backup_schema_binds_build_operator_and_original_shell(self):
        schema = load("backup-v2.schema.json")
        required = schema["required"]

        for name in (
            "schemaVersion",
            "buildFamily",
            "operatorSid",
            "operatorUser",
            "originalShell",
            "registryValues",
            "fileAcls",
            "configBackup",
            "integritySha256",
        ):
            self.assertIn(name, required)

    def test_ui_contract_preserves_exact_brand_and_design_surface(self):
        ui = load("ui-layout-v2.json")

        self.assertEqual({"width": 1440, "height": 900}, ui["designSurface"])
        self.assertEqual("РК", ui["brand"]["logoText"])
        self.assertEqual("Режим киоска", ui["brand"]["title"])
        self.assertEqual("2026", ui["brand"]["year"])
        self.assertEqual(
            "разработал: Абдрахманов Амаль Даулетович",
            ui["brand"]["developer"],
        )

    def test_behavior_contract_keeps_guards_active_in_admin_dialog(self):
        behavior = load("behavior-cases.json")
        unlock = next(
            item
            for item in behavior["transitions"]
            if item["from"] == "OPERATOR" and item["event"] == "unlock_requested"
        )

        self.assertEqual("ADMIN_DIALOG", unlock["to"])
        self.assertIn("show_admin_dialog", unlock["effects"])
        self.assertNotIn("stop_keyboard_guard", unlock["effects"])
        self.assertNotIn("stop_desktop_isolation", unlock["effects"])


if __name__ == "__main__":
    unittest.main()
