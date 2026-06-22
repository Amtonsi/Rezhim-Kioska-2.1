# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

import kiosk_v2_legacy.configurator as configurator_module
from kiosk_v2_legacy.configurator import ApplicationConfigurator, ConfiguratorError


class FakeRepository(object):
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.saved = []
        self.load_requirements = []

    def load(self, require_existing_app=False):
        self.load_requirements.append(require_existing_app)
        return copy.deepcopy(self.config)

    def save(self, config, require_existing_app=False):
        self.saved.append((copy.deepcopy(config), require_existing_app))
        self.config = copy.deepcopy(config)
        return copy.deepcopy(config)


class FakePicker(object):
    def __init__(self, selected):
        self.selected = selected

    def choose_executable(self, initial_path):
        return self.selected


def config():
    return {
        "allowedApplication": {
            "path": r"C:\Old\Old.exe",
            "workingDirectory": r"C:\Old",
            "arguments": [],
        }
    }


class LegacyConfiguratorTests(unittest.TestCase):
    def test_missing_previous_directory_uses_windows_fallback(self):
        select_initial_directory = getattr(
            configurator_module,
            "select_initial_directory",
            None,
        )
        self.assertIsNotNone(select_initial_directory)
        selected = select_initial_directory(
            r"F:\Telegram Desktop\Telegram.exe",
            directory_exists=lambda _path: False,
            fallback=r"C:\Windows",
        )

        self.assertEqual(r"C:\Windows", selected)

    def test_selected_executable_updates_path_and_working_directory(self):
        repository = FakeRepository(config())
        service = ApplicationConfigurator(
            repository,
            FakePicker(r"C:\Program Files\Vendor\New.exe"),
            file_exists=lambda path: path.endswith("New.exe"),
            is_elevated=lambda: True,
        )

        self.assertTrue(service.run())
        self.assertEqual([False], repository.load_requirements)
        saved, require_existing = repository.saved[0]
        self.assertTrue(require_existing)
        self.assertTrue(saved["allowedApplication"]["configured"])
        self.assertEqual(r"C:\Program Files\Vendor\New.exe", saved["allowedApplication"]["path"])
        self.assertEqual(r"C:\Program Files\Vendor", saved["allowedApplication"]["workingDirectory"])

    def test_cancel_does_not_change_configuration(self):
        repository = FakeRepository(config())
        service = ApplicationConfigurator(
            repository,
            FakePicker(""),
            file_exists=lambda _path: True,
            is_elevated=lambda: True,
        )

        self.assertFalse(service.run())
        self.assertEqual([], repository.saved)

    def test_non_elevated_process_is_rejected(self):
        service = ApplicationConfigurator(
            FakeRepository(config()),
            FakePicker(r"C:\Program Files\Vendor\New.exe"),
            file_exists=lambda _path: True,
            is_elevated=lambda: False,
        )

        with self.assertRaises(ConfiguratorError):
            service.run()


if __name__ == "__main__":
    unittest.main()
