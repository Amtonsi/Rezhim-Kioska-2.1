# -*- coding: utf-8 -*-

import json
import os
import time
import uuid


SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
    "hash",
    "salt",
)

REDACTED = "***REDACTED***"


class KioskLogger(object):
    def __init__(
        self,
        log_path=None,
        max_bytes=5 * 1024 * 1024,
        backup_count=5,
        session_id=None,
    ):
        self.log_path = log_path or default_log_path()
        self.max_bytes = int(max_bytes)
        self.backup_count = int(backup_count)
        self.session_id = session_id or os.environ.get("PYTHONKIOSK_SESSION_ID") or uuid.uuid4().hex

    def info(self, event, **data):
        self._write("info", event, data)

    def warning(self, event, **data):
        self._write("warning", event, data)

    def error(self, event, **data):
        self._write("error", event, data)

    def _write(self, level, event, data):
        row = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session_id": self.session_id,
            "process_id": os.getpid(),
            "level": level,
            "event": event,
            "data": sanitize_log_data(data),
        }
        try:
            self._write_to_path(self.log_path, row)
        except OSError:
            fallback_path = fallback_log_path()
            if os.path.abspath(fallback_path) == os.path.abspath(self.log_path):
                return False
            try:
                self._write_to_path(fallback_path, row)
            except OSError:
                return False
        return True

    def _write_to_path(self, path, row):
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        self._rotate_if_needed(path)
        with open(os.path.abspath(path), "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            log_file.write("\n")

    def _rotate_if_needed(self, path):
        path = os.path.abspath(path)
        if self.max_bytes <= 0 or self.backup_count <= 0:
            return
        if not os.path.exists(path):
            return
        try:
            if os.path.getsize(path) < self.max_bytes:
                return
            for index in range(self.backup_count - 1, 0, -1):
                source = "{0}.{1}".format(path, index)
                target = "{0}.{1}".format(path, index + 1)
                if os.path.exists(source):
                    if os.path.exists(target):
                        os.remove(target)
                    os.rename(source, target)
            first_backup = "{0}.1".format(path)
            if os.path.exists(first_backup):
                os.remove(first_backup)
            os.rename(path, first_backup)
        except OSError:
            return


def default_log_path():
    override_path = environment_log_path()
    if override_path:
        return override_path
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~")
    return os.path.join(base, "PythonKiosk", "logs", "kiosk.log")


def fallback_log_path():
    return os.path.join(os.path.expanduser("~"), "PythonKiosk", "logs", "kiosk.log")


def configured_log_path(config, filename="kiosk.log"):
    override_path = environment_log_path()
    if override_path:
        if filename == os.path.basename(override_path):
            return override_path
        return os.path.join(os.path.dirname(override_path), filename)
    logging_config = getattr(config, "logging", {}) or {}
    directory = logging_config.get("logDirectory") or logging_config.get("log_directory")
    directory = directory or os.path.dirname(default_log_path())
    return os.path.join(os.path.expandvars(directory), filename)


def environment_log_path():
    override_path = os.environ.get("PYTHONKIOSK_LOG_PATH")
    if not override_path:
        return None
    return os.path.expandvars(os.path.expanduser(override_path))


def create_configured_logger(config, session_id=None, filename="kiosk.log"):
    return KioskLogger(
        log_path=configured_log_path(config, filename=filename),
        session_id=session_id,
    )


def sanitize_log_data(value, key_name=""):
    if _is_sensitive_key(key_name):
        return REDACTED
    if isinstance(value, dict):
        return dict(
            (key, sanitize_log_data(item, key))
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return [sanitize_log_data(item, key_name) for item in value]
    return value


def _is_sensitive_key(key_name):
    normalized = str(key_name or "").lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
