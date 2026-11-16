# -*- coding: utf-8 -*-
import copy
import json
import ntpath
import os
import tempfile

from kiosk_v2_modern.platform.log_path import PROFILE_LOG_DIRECTORY


class ConfigValidationError(ValueError):
    def __init__(self, path, code):
        self.path = path
        self.code = code
        super(ConfigValidationError, self).__init__(
            "Invalid kiosk configuration at {0}: {1}".format(path, code)
        )


class ConfigValidator(object):
    def __init__(self, schema):
        self.schema = copy.deepcopy(schema)

    def validate(self, data, require_existing_app=False):
        self._validate_node(data, self.schema, "$")
        self._validate_windows_semantics(data, require_existing_app)
        return copy.deepcopy(data)

    def _validate_node(self, value, schema, path):
        expected_type = schema.get("type")
        if expected_type is not None and not self._matches_type(value, expected_type):
            raise ConfigValidationError(path, "wrong_type")

        if "const" in schema and not self._same_scalar(value, schema["const"]):
            raise ConfigValidationError(path, "const_mismatch")

        if "enum" in schema and not any(
            self._same_scalar(value, allowed) for allowed in schema["enum"]
        ):
            raise ConfigValidationError(path, "not_in_enum")

        if isinstance(value, str):
            if len(value) < int(schema.get("minLength", 0)):
                raise ConfigValidationError(path, "too_short")

        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise ConfigValidationError(path, "below_minimum")
            if "maximum" in schema and value > schema["maximum"]:
                raise ConfigValidationError(path, "above_maximum")

        if isinstance(value, dict):
            required = schema.get("required", [])
            for name in required:
                if name not in value:
                    raise ConfigValidationError(
                        self._child_path(path, name),
                        "required",
                    )
            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        raise ConfigValidationError(
                            self._child_path(path, name),
                            "unknown_field",
                        )
            for name, item in value.items():
                child_schema = properties.get(name)
                if child_schema is not None:
                    self._validate_node(
                        item,
                        child_schema,
                        self._child_path(path, name),
                    )

    def _validate_windows_semantics(self, data, require_existing_app):
        operator = data["operatorUser"].strip()
        if any(separator in operator for separator in ("\\", "/", "@")):
            raise ConfigValidationError("$.operatorUser", "local_user_required")

        application = data["allowedApplication"]
        executable = application["path"].strip()
        if not ntpath.isabs(executable):
            raise ConfigValidationError(
                "$.allowedApplication.path",
                "absolute_path_required",
            )
        if ntpath.splitext(executable)[1].lower() != ".exe":
            raise ConfigValidationError(
                "$.allowedApplication.path",
                "exe_required",
            )
        working_directory = application["workingDirectory"].strip()
        if working_directory and not ntpath.isabs(working_directory):
            raise ConfigValidationError(
                "$.allowedApplication.workingDirectory",
                "absolute_path_required",
            )
        if require_existing_app and not os.path.isfile(executable):
            raise ConfigValidationError(
                "$.allowedApplication.path",
                "file_not_found",
            )

        log_directory = data["logging"]["logDirectory"].strip()
        if log_directory != PROFILE_LOG_DIRECTORY and not ntpath.isabs(log_directory):
            raise ConfigValidationError(
                "$.logging.logDirectory",
                "absolute_path_required",
            )

    @staticmethod
    def _matches_type(value, expected_type):
        checks = {
            "object": lambda item: isinstance(item, dict),
            "string": lambda item: isinstance(item, str),
            "boolean": lambda item: isinstance(item, bool),
            "integer": lambda item: isinstance(item, int)
            and not isinstance(item, bool),
        }
        check = checks.get(expected_type)
        if check is None:
            raise ValueError("Unsupported schema type: {0}".format(expected_type))
        return check(value)

    @staticmethod
    def _same_scalar(left, right):
        return type(left) is type(right) and left == right

    @staticmethod
    def _child_path(path, name):
        return "{0}.{1}".format(path, name)


class NoOpConfigAcl(object):
    def protect_admin_write(self, _path):
        return None


class ConfigRepository(object):
    def __init__(
        self,
        config_path,
        validator,
        acl=None,
        replace_func=None,
    ):
        self.config_path = os.path.abspath(config_path)
        self.validator = validator
        self.acl = acl or NoOpConfigAcl()
        self.replace_func = replace_func or os.replace

    def load(self, require_existing_app=False):
        try:
            with open(self.config_path, "r", encoding="utf-8-sig") as stream:
                data = json.load(stream)
        except (UnicodeError, json.JSONDecodeError):
            raise ConfigValidationError("$", "invalid_json")
        return self.validator.validate(
            data,
            require_existing_app=require_existing_app,
        )

    def save(self, data, require_existing_app=False):
        validated = self.validator.validate(
            data,
            require_existing_app=require_existing_app,
        )
        previous_bytes = self._read_existing_bytes()
        payload = (
            json.dumps(
                validated,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        self._atomic_write(payload)
        try:
            self.acl.protect_admin_write(self.config_path)
        except Exception:
            self._restore_previous(previous_bytes)
            raise
        return copy.deepcopy(validated)

    def _atomic_write(self, payload):
        directory = os.path.dirname(self.config_path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        descriptor, temp_path = tempfile.mkstemp(
            prefix=".kiosk-v2-",
            suffix=".tmp",
            dir=directory,
        )
        try:
            stream = os.fdopen(descriptor, "wb")
            descriptor = None
            with stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self.replace_func(temp_path, self.config_path)
            temp_path = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _read_existing_bytes(self):
        if not os.path.exists(self.config_path):
            return None
        with open(self.config_path, "rb") as stream:
            return stream.read()

    def _restore_previous(self, previous_bytes):
        if previous_bytes is None:
            if os.path.exists(self.config_path):
                os.unlink(self.config_path)
            return
        self._atomic_write(previous_bytes)
