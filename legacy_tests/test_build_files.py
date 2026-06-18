# -*- coding: utf-8 -*-

import json
import os
import unittest

from legacy_kiosk.config import build_default_config


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LegacyBuildFileTests(unittest.TestCase):
    def _read(self, name):
        path = os.path.join(PROJECT_ROOT, name)
        self.assertTrue(os.path.isfile(path), path)
        with open(path, "rb") as stream:
            return stream.read().decode("utf-8")

    def test_build_files_exist_and_target_separate_legacy_artifact(self):
        requirements = self._read("requirements-legacy-build.txt")
        spec = self._read("RezhimKioska.Legacy.spec")
        builder = self._read("build_legacy.cmd")

        self.assertIn("pyinstaller==3.2.1", requirements.lower())
        self.assertIn("pefile==2017.11.5", requirements.lower())
        self.assertIn("RezhimKioska-Legacy", spec)
        self.assertIn("console=False", spec)
        self.assertIn("python 2.7", builder.lower())
        self.assertIn("32", builder)
        self.assertIn("ensurepip", builder.lower())
        self.assertIn(r"release\legacy", builder)
        self.assertIn("legacy_tests", builder)

    def test_all_build_dependencies_are_fully_pinned(self):
        requirements = self._read("requirements-legacy-build.txt")
        entries = [
            line.strip()
            for line in requirements.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertTrue(entries)
        self.assertTrue(all("==" in entry for entry in entries))

    def test_python_probe_escapes_batch_percent_formatting(self):
        builder = self._read("build_legacy.cmd")

        self.assertIn("Python 2.7 x86: %%s", builder)

    def test_portable_pywin32_paths_are_explicit(self):
        builder = self._read("build_legacy.cmd")

        self.assertIn(
            'set "PYTHONPATH=%PACKAGES%;%PACKAGES%\\win32;%PACKAGES%\\win32\\lib"',
            builder,
        )
        self.assertIn('set "PATH=%PACKAGES%\\pywin32_system32;%PATH%"', builder)

    def test_legacy_release_stages_its_own_config_template(self):
        spec = self._read("RezhimKioska.Legacy.spec")
        builder = self._read("build_legacy.cmd")
        template = json.loads(self._read(os.path.join("config", "kiosk.legacy.json")))

        self.assertEqual(build_default_config(), template)
        self.assertIn("kiosk.legacy.json", spec)
        self.assertIn("kiosk.legacy.json", builder)


if __name__ == "__main__":
    unittest.main()
