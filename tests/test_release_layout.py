# -*- coding: utf-8 -*-

import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DualReleaseLayoutTests(unittest.TestCase):
    def setUp(self):
        path = os.path.join(PROJECT_ROOT, "build_release.ps1")
        with open(path, "r", encoding="utf-8") as stream:
            self.script = stream.read()
        self.lower = self.script.lower()

    def test_requires_both_prebuilt_family_artifacts(self):
        self.assertIn("release\\modern\\RezhimKioska-Modern.exe", self.script)
        self.assertIn("release\\legacy\\RezhimKioska-Legacy.exe", self.script)
        self.assertIn("Required tested artifact is missing", self.script)

    def test_packager_never_builds_or_substitutes_old_single_exe(self):
        self.assertNotIn("pyinstaller", self.lower)
        self.assertNotIn("dist\\rezhimkioska.exe", self.lower)
        self.assertNotIn("remove-item -literalpath $releasedir", self.lower)

    def test_writes_hash_and_json_manifests(self):
        self.assertIn("Get-FileHash", self.script)
        self.assertIn("SHA256SUMS.txt", self.script)
        self.assertIn("build-manifest.json", self.script)
        self.assertIn("ConvertTo-Json", self.script)

    def test_packages_source_without_transient_or_sensitive_directories(self):
        for directory in (
            "python_kiosk",
            "legacy_kiosk",
            "tests",
            "legacy_tests",
            "docs",
            "contracts",
            "config",
            "scripts",
            "src",
        ):
            self.assertIn('"{0}"'.format(directory), self.script)
        for forbidden in (".venv", "__pycache__", ".kiosk-state", "backup"):
            self.assertIn(forbidden, self.script)


if __name__ == "__main__":
    unittest.main()
