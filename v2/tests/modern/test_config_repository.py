# -*- coding: utf-8 -*-
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(V2_ROOT)
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.config_repository import (
    ConfigRepository,
    ConfigValidationError,
    ConfigValidator,
)


def load_json(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as stream:
        return json.load(stream)


class FakeAcl(object):
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def protect_admin_write(self, path):
        self.calls.append(path)
        if self.error is not None:
            raise self.error


class ConfigRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kiosk-v2-config-")
        self.config_path = os.path.join(self.temp_dir, "kiosk.v2.json")
        self.schema = load_json(
            os.path.join(V2_ROOT, "contracts", "kiosk-config-v2.schema.json")
        )
        self.default = load_json(
            os.path.join(PROJECT_ROOT, "config", "kiosk.v2.default.json")
        )
        self.validator = ConfigValidator(self.schema)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def repository(self, acl=None, replace_func=None):
        return ConfigRepository(
            self.config_path,
            validator=self.validator,
            acl=acl or FakeAcl(),
            replace_func=replace_func,
        )

    def test_default_is_valid_and_load_accepts_utf8_bom(self):
        raw = json.dumps(self.default, ensure_ascii=False, indent=2).encode("utf-8")
        with open(self.config_path, "wb") as stream:
            stream.write(b"\xef\xbb\xbf" + raw)

        loaded = self.repository().load()

        self.assertEqual(self.default, loaded)

    def test_load_returns_deep_copy_not_repository_state(self):
        self.repository().save(self.default)

        first = self.repository().load()
        first["allowedApplication"]["path"] = r"C:\Changed.exe"
        second = self.repository().load()

        self.assertEqual(
            r"C:\Windows\System32\notepad.exe",
            second["allowedApplication"]["path"],
        )

    def test_validator_rejects_unknown_and_password_like_fields(self):
        invalid = copy.deepcopy(self.default)
        invalid["password"] = "hunter2"
        with self.assertRaises(ConfigValidationError) as raised:
            self.validator.validate(invalid)
        self.assertNotIn("hunter2", str(raised.exception))

        invalid = copy.deepcopy(self.default)
        invalid["allowedApplication"]["unexpected"] = True
        with self.assertRaises(ConfigValidationError):
            self.validator.validate(invalid)

    def test_validator_rejects_wrong_boolean_range_and_relative_executable(self):
        invalid_boolean = copy.deepcopy(self.default)
        invalid_boolean["kiosk"]["allowWinL"] = 1
        with self.assertRaises(ConfigValidationError):
            self.validator.validate(invalid_boolean)

        invalid_range = copy.deepcopy(self.default)
        invalid_range["allowedApplication"]["restartDelayMs"] = 10
        with self.assertRaises(ConfigValidationError):
            self.validator.validate(invalid_range)

        relative = copy.deepcopy(self.default)
        relative["allowedApplication"]["path"] = r"tools\app.exe"
        with self.assertRaises(ConfigValidationError):
            self.validator.validate(relative)

    def test_require_existing_app_rejects_missing_and_accepts_any_existing_exe(self):
        missing = copy.deepcopy(self.default)
        missing["allowedApplication"]["path"] = os.path.join(
            self.temp_dir, "missing.exe"
        )
        with self.assertRaises(ConfigValidationError):
            self.validator.validate(missing, require_existing_app=True)

        existing_path = os.path.join(self.temp_dir, "Any Allowed Program.exe")
        with open(existing_path, "wb") as stream:
            stream.write(b"MZ")
        valid = copy.deepcopy(self.default)
        valid["allowedApplication"]["path"] = existing_path
        valid["allowedApplication"]["workingDirectory"] = self.temp_dir

        self.validator.validate(valid, require_existing_app=True)

    def test_save_atomically_replaces_then_applies_acl(self):
        acl = FakeAcl()
        repository = self.repository(acl=acl)
        updated = copy.deepcopy(self.default)
        updated["operatorUser"] = "test"

        saved = repository.save(updated)

        self.assertEqual("test", saved["operatorUser"])
        self.assertEqual(updated, repository.load())
        self.assertEqual([self.config_path], acl.calls)
        self.assertEqual([], self._temp_files())

    def test_replace_failure_preserves_old_target_and_removes_temp_file(self):
        old = copy.deepcopy(self.default)
        old["operatorUser"] = "old-user"
        ConfigRepository(
            self.config_path,
            validator=self.validator,
            acl=FakeAcl(),
        ).save(old)
        before = self._read_bytes(self.config_path)
        acl = FakeAcl()

        def fail_replace(_source, _target):
            raise OSError("replace failed")

        repository = self.repository(acl=acl, replace_func=fail_replace)
        updated = copy.deepcopy(self.default)
        updated["operatorUser"] = "new-user"

        with self.assertRaises(OSError):
            repository.save(updated)

        self.assertEqual(before, self._read_bytes(self.config_path))
        self.assertEqual([], acl.calls)
        self.assertEqual([], self._temp_files())

    def test_acl_failure_restores_previous_target(self):
        old = copy.deepcopy(self.default)
        old["operatorUser"] = "old-user"
        self.repository().save(old)
        before = self._read_bytes(self.config_path)
        acl = FakeAcl(error=OSError("acl failed"))
        updated = copy.deepcopy(self.default)
        updated["operatorUser"] = "new-user"

        with self.assertRaises(OSError):
            self.repository(acl=acl).save(updated)

        self.assertEqual(before, self._read_bytes(self.config_path))
        self.assertEqual([self.config_path], acl.calls)
        self.assertEqual([], self._temp_files())

    def _temp_files(self):
        return [
            name
            for name in os.listdir(self.temp_dir)
            if name.startswith(".kiosk-v2-") and name.endswith(".tmp")
        ]

    @staticmethod
    def _read_bytes(path):
        with open(path, "rb") as stream:
            return stream.read()


if __name__ == "__main__":
    unittest.main()
