# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BuildContractTests(unittest.TestCase):
    def test_family_entrypoints_are_independent_and_restore_has_no_ui_imports(self):
        expected = (
            ("modern", "kiosk_v2_modern"),
            ("legacy", "kiosk_v2_legacy"),
        )
        for family, package in expected:
            launcher = self._read(family, "launcher_main.py")
            restore = self._read(family, "restore_main.py")
            other = "kiosk_v2_legacy" if family == "modern" else "kiosk_v2_modern"

            self.assertIn("from {0}.launcher import run_default".format(package), launcher)
            self.assertNotIn(other, launcher)
            self.assertIn(
                "from {0}.restore_entrypoint import run_default".format(package),
                restore,
            )
            self.assertNotIn(other, restore)
            self.assertNotIn(".ui", restore)
            self.assertNotIn("keyboard_guard", restore)

    def test_four_specs_have_stable_names_and_only_launcher_bundles_contracts(self):
        expected = {
            "modern-launcher.spec": "RezhimKioska-V2-Modern",
            "modern-restore.spec": "Restore-V2-Modern",
            "legacy-launcher.spec": "RezhimKioska-V2-Legacy",
            "legacy-restore.spec": "Restore-V2-Legacy",
        }
        for filename, executable_name in expected.items():
            source = self._read("build", filename)
            self.assertIn("name={0!r}".format(executable_name), source)
            self.assertIn("console=False" if "launcher" in filename else "console=True", source)
            if "launcher" in filename:
                self.assertIn("contracts", source)
            else:
                self.assertNotIn("datas=[('v2/contracts'", source.replace('\\', '/'))

    def test_build_scripts_package_runtime_config_and_restore_alias(self):
        modern = self._read("scripts", "build-modern.ps1")
        legacy = self._read("scripts", "build-legacy.ps1")

        for source, family in ((modern, "modern"), (legacy, "legacy")):
            self.assertIn("kiosk.v2.default.json", source)
            self.assertIn("kiosk.v2.json", source)
            self.assertIn("Restore.exe", source)
            self.assertIn("v2\\dist\\{0}".format(family), source)

        self.assertIn("PYTHONPATH", legacy)
        self.assertIn("win32\\lib", legacy)
        self.assertIn("pywin32_system32", legacy)

    def _read(self, directory, filename):
        path = os.path.join(V2_ROOT, directory, filename)
        with open(path, "rb") as stream:
            return stream.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()
