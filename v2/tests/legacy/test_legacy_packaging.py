# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.platform.runtime_path import coerce_runtime_directory


try:
    text_type = unicode
except NameError:
    text_type = str


def filesystem_text(value):
    if isinstance(value, text_type):
        return value
    return value.decode(sys.getfilesystemencoding() or "mbcs")


def read_text(relative_path):
    with io.open(os.path.join(PROJECT_ROOT, relative_path), "r", encoding="utf-8") as stream:
        return stream.read()


class LegacyPackagingTests(unittest.TestCase):
    def test_legacy_specs_use_onedir_collect_not_onefile_archive(self):
        spec_names = [
            "legacy-launcher.spec",
            "legacy-configurator.spec",
            "legacy-restore.spec",
        ]

        for spec_name in spec_names:
            spec = read_text(os.path.join("v2", "build", spec_name))
            self.assertIn("exclude_binaries=True", spec)
            self.assertIn("COLLECT(", spec)
            self.assertNotIn("a.binaries,\n    a.zipfiles,\n    a.datas,\n    name=", spec)

    def test_legacy_build_flattens_onedir_outputs_into_single_portable_folder(self):
        script = read_text(os.path.join("v2", "scripts", "build-legacy.ps1"))

        self.assertIn("Merge-LegacyOnedirOutput", script)
        self.assertIn("$stagingDistPath", script)
        self.assertIn("RezhimKioska-V2-Legacy.exe", script)
        self.assertIn("Configurator-V2-Legacy.exe", script)
        self.assertIn("Restore-V2-Legacy.exe", script)

    def test_runtime_directory_recovers_utf8_bytes_path_from_legacy_bootloader(self):
        temp_root = filesystem_text(tempfile.gettempdir())
        runtime_directory = os.path.join(temp_root, u"КиоскLegacyRuntimePath")
        if os.path.isdir(runtime_directory):
            shutil.rmtree(runtime_directory)
        os.makedirs(os.path.join(runtime_directory, "config"))
        try:
            raw_bootloader_path = runtime_directory.encode("utf-8")

            normalized = coerce_runtime_directory(
                raw_bootloader_path,
                required_children=("config",),
            )

            self.assertEqual(
                os.path.normcase(runtime_directory),
                os.path.normcase(normalized),
            )
        finally:
            if os.path.isdir(runtime_directory):
                shutil.rmtree(runtime_directory)


if __name__ == "__main__":
    unittest.main()
