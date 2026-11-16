# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import ctypes
import io
import json
import ntpath
import os
import sys
import tempfile

from kiosk_v2_legacy.platform.log_path import PROFILE_LOG_DIRECTORY

from ctypes import wintypes


try:
    string_types = (basestring,)
    integer_types = (int, long)
    text_type = unicode
except NameError:
    string_types = (str,)
    integer_types = (int,)
    text_type = str


MOVEFILE_REPLACE_EXISTING = 0x00000001
MOVEFILE_WRITE_THROUGH = 0x00000008


class ConfigValidationError(ValueError):
    def __init__(self, path, code):
        self.path = path
        self.code = code
        ValueError.__init__(
            self,
            "Invalid kiosk configuration at {0}: {1}".format(path, code),
        )


class LegacyConfigValidator(object):
    def __init__(self, schema):
        self.schema = copy.deepcopy(schema)

    def validate(self, data, require_existing_app=False):
        self._validate_node(data, self.schema, "$")
        app = data["allowedApplication"]
        executable = app["path"].strip()
        if not ntpath.isabs(executable):
            raise ConfigValidationError("$.allowedApplication.path", "absolute_path_required")
        if ntpath.splitext(executable)[1].lower() != ".exe":
            raise ConfigValidationError("$.allowedApplication.path", "exe_required")
        if require_existing_app and not os.path.isfile(executable):
            raise ConfigValidationError("$.allowedApplication.path", "file_not_found")
        if app["workingDirectory"] and not ntpath.isabs(app["workingDirectory"]):
            raise ConfigValidationError(
                "$.allowedApplication.workingDirectory", "absolute_path_required"
            )
        log_directory = data["logging"]["logDirectory"].strip()
        if log_directory != PROFILE_LOG_DIRECTORY and not ntpath.isabs(log_directory):
            raise ConfigValidationError("$.logging.logDirectory", "absolute_path_required")
        return copy.deepcopy(data)

    def _validate_node(self, value, schema, path):
        expected = schema.get("type")
        if expected is not None and not self._matches_type(value, expected):
            raise ConfigValidationError(path, "wrong_type")
        if "const" in schema and not self._same_scalar(value, schema["const"]):
            raise ConfigValidationError(path, "const_mismatch")
        if "enum" in schema and not any(
            self._same_scalar(value, item) for item in schema["enum"]
        ):
            raise ConfigValidationError(path, "not_in_enum")
        if isinstance(value, string_types):
            if len(value) < int(schema.get("minLength", 0)):
                raise ConfigValidationError(path, "too_short")
        if isinstance(value, integer_types) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise ConfigValidationError(path, "below_minimum")
            if "maximum" in schema and value > schema["maximum"]:
                raise ConfigValidationError(path, "above_maximum")
        if isinstance(value, dict):
            properties = schema.get("properties", {})
            for name in schema.get("required", []):
                if name not in value:
                    raise ConfigValidationError(path + "." + name, "required")
            if schema.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        raise ConfigValidationError(path + "." + name, "unknown_field")
            for name, item in value.items():
                if name in properties:
                    self._validate_node(item, properties[name], path + "." + name)

    @staticmethod
    def _matches_type(value, expected):
        if expected == "object":
            return isinstance(value, dict)
        if expected == "string":
            return isinstance(value, string_types)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, integer_types) and not isinstance(value, bool)
        raise ValueError("Unsupported schema type")

    @staticmethod
    def _same_scalar(left, right):
        return type(left) is type(right) and left == right


class NoOpAcl(object):
    def protect_admin_write(self, unused):
        return None


class LegacyConfigRepository(object):
    def __init__(self, path, validator, replacer=None, acl=None):
        self.config_path = os.path.abspath(path)
        self.validator = validator
        self.replacer = replacer or LegacyAtomicReplacer()
        self.acl = acl or NoOpAcl()

    def load(self, require_existing_app=False):
        try:
            with io.open(self.config_path, "r", encoding="utf-8-sig") as stream:
                data = json.load(stream)
        except (UnicodeError, ValueError):
            raise ConfigValidationError("$", "invalid_json")
        return self.validator.validate(data, require_existing_app)

    def save(self, data, require_existing_app=False):
        validated = self.validator.validate(data, require_existing_app)
        previous = self._read_existing()
        payload = (
            json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        self._atomic_write(payload)
        try:
            self.acl.protect_admin_write(self.config_path)
        except Exception:
            self._restore(previous)
            raise
        return copy.deepcopy(validated)

    def _atomic_write(self, payload):
        directory = os.path.dirname(self.config_path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        descriptor, temp_path = tempfile.mkstemp(
            prefix=".kiosk-v2-legacy-", suffix=".tmp", dir=directory
        )
        try:
            stream = os.fdopen(descriptor, "wb")
            descriptor = None
            with stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self.replacer.replace(temp_path, self.config_path)
            temp_path = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _read_existing(self):
        if not os.path.exists(self.config_path):
            return None
        with open(self.config_path, "rb") as stream:
            return stream.read()

    def _restore(self, previous):
        if previous is None:
            if os.path.exists(self.config_path):
                os.unlink(self.config_path)
        else:
            self._atomic_write(previous)


class LegacyAtomicReplacer(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.kernel32.MoveFileExW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        self.kernel32.MoveFileExW.restype = wintypes.BOOL

    def replace(self, source, target):
        flags = MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
        if not self.kernel32.MoveFileExW(
            self._unicode_path(source),
            self._unicode_path(target),
            flags,
        ):
            code = int(self.kernel32.GetLastError())
            raise OSError(code, "MoveFileExW failed with Windows error {0}".format(code))

    @staticmethod
    def _unicode_path(path):
        if isinstance(path, text_type):
            return path
        return path.decode(sys.getfilesystemencoding() or "mbcs")
