# -*- coding: utf-8 -*-
import copy
import json
import os


ALLOWED_APPLICATION_FIELDS = (
    "path",
    "arguments",
    "workingDirectory",
    "restartOnExit",
    "singleInstance",
    "bringToFront",
    "startMaximized",
    "restoreIfMinimized",
    "restartDelayMs",
)


class ConfigMigrationError(ValueError):
    pass


class MigrationResult(object):
    __slots__ = ("status", "config", "backup_path")

    def __init__(self, status, config, backup_path=""):
        self.status = status
        self.config = copy.deepcopy(config)
        self.backup_path = backup_path


class V1ConfigMigrator(object):
    def __init__(
        self,
        source_path,
        backup_path,
        v2_repository,
        default_config,
    ):
        self.source_path = os.path.abspath(source_path)
        self.backup_path = os.path.abspath(backup_path)
        self.v2_repository = v2_repository
        self.default_config = copy.deepcopy(default_config)

    def migrate(self, force=False, require_existing_app=False):
        if os.path.exists(self.v2_repository.config_path) and not force:
            existing = self.v2_repository.load(
                require_existing_app=require_existing_app
            )
            return MigrationResult("existing", existing)

        source_bytes = self._read_source_bytes()
        source_data = self._decode_source(source_bytes)
        migrated = self._build_v2(source_data)
        actual_backup = self._write_exact_backup(source_bytes)
        saved = self.v2_repository.save(
            migrated,
            require_existing_app=require_existing_app,
        )
        return MigrationResult("migrated", saved, actual_backup)

    def _read_source_bytes(self):
        with open(self.source_path, "rb") as stream:
            return stream.read()

    @staticmethod
    def _decode_source(source_bytes):
        try:
            data = json.loads(source_bytes.decode("utf-8-sig"))
        except (UnicodeError, ValueError):
            raise ConfigMigrationError("Invalid V1 configuration JSON")
        if not isinstance(data, dict):
            raise ConfigMigrationError("V1 configuration must be an object")
        return data

    def _build_v2(self, source):
        target = copy.deepcopy(self.default_config)

        operator = source.get("operatorUser", source.get("operator_user"))
        if operator is not None:
            target["operatorUser"] = operator

        old_application = source.get("allowedApplication")
        if isinstance(old_application, dict):
            for name in ALLOWED_APPLICATION_FIELDS:
                if name in old_application:
                    target["allowedApplication"][name] = copy.deepcopy(
                        old_application[name]
                    )
        elif "app_path" in source:
            target["allowedApplication"]["path"] = source["app_path"]

        old_kiosk = source.get("kiosk")
        if isinstance(old_kiosk, dict) and "adminSessionTimeoutSeconds" in old_kiosk:
            target["kiosk"]["adminSessionTimeoutSeconds"] = old_kiosk[
                "adminSessionTimeoutSeconds"
            ]
        target["kiosk"]["allowWinL"] = True
        target["kiosk"]["keyboardGuardRequired"] = True

        old_logging = source.get("logging")
        if isinstance(old_logging, dict):
            for name in ("logDirectory", "level"):
                if name in old_logging:
                    target["logging"][name] = copy.deepcopy(old_logging[name])

        target["testing"] = {
            "requireBackupBeforeTest": True,
            "restoreAfterTest": True,
            "testOnlySeparateOperatorUser": True,
        }
        return target

    def _write_exact_backup(self, source_bytes):
        directory = os.path.dirname(self.backup_path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        index = 0
        while True:
            candidate = self.backup_path if index == 0 else "{0}.{1}".format(
                self.backup_path,
                index,
            )
            if os.path.exists(candidate):
                if self._read_bytes(candidate) == source_bytes:
                    return candidate
                index += 1
                continue
            try:
                with open(candidate, "xb") as stream:
                    stream.write(source_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                return candidate
            except FileExistsError:
                index += 1

    @staticmethod
    def _read_bytes(path):
        with open(path, "rb") as stream:
            return stream.read()
