# -*- coding: utf-8 -*-

import datetime
import io
import json
import os
import sys
import tempfile
import threading

from legacy_kiosk.compat import string_types, text_type


REDACTED = u"[СКРЫТО]"
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "credential",
    "secret",
    "token",
    "typedtext",
    "inputtext",
    "keystroke",
)


def legacy_log_directory(environment=None, nt_major=None):
    environment = environment or os.environ
    if nt_major is None:
        try:
            nt_major = int(sys.getwindowsversion()[0])
        except Exception:
            nt_major = 6
    if int(nt_major) <= 5:
        all_users = environment.get("ALLUSERSPROFILE", r"C:\Documents and Settings\All Users")
        return os.path.join(all_users, "Application Data", "Kiosk", "Logs")
    program_data = environment.get("PROGRAMDATA") or environment.get("ALLUSERSPROFILE")
    return os.path.join(program_data or r"C:\ProgramData", "Kiosk", "Logs")


def resolve_log_directory(configured_path, environment=None, nt_major=None):
    if nt_major is None:
        try:
            nt_major = int(sys.getwindowsversion()[0])
        except Exception:
            nt_major = 6
    if not configured_path:
        return legacy_log_directory(environment=environment, nt_major=nt_major)
    modern_default = os.path.normcase(
        os.path.normpath(r"C:\ProgramData\Kiosk\Logs")
    )
    configured = os.path.normcase(os.path.normpath(configured_path))
    if int(nt_major) <= 5 and configured == modern_default:
        return legacy_log_directory(environment=environment, nt_major=nt_major)
    return configured_path


def _normalized_key(key):
    if not isinstance(key, string_types):
        key = text_type(key)
    return u"".join(character for character in key.lower() if character.isalnum())


def _sanitize(value):
    if isinstance(value, dict):
        result = {}
        for key, nested in value.items():
            normalized = _normalized_key(key)
            if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                result[key] = REDACTED
            else:
                result[key] = _sanitize(nested)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize(nested) for nested in value]
    if value is None or isinstance(value, (bool, int, long, float) + string_types):
        return value
    return text_type(value)


class LegacyLogger(object):
    def __init__(self, path=None, max_bytes=1024 * 1024, backup_count=3):
        self.path = path or os.path.join(legacy_log_directory(), "kiosk.log")
        self.max_bytes = int(max_bytes)
        self.backup_count = max(0, int(backup_count))
        self.lock = threading.RLock()

    def log(self, event, data=None, level="INFO"):
        record = {
            "timestampUtc": datetime.datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "data": _sanitize(data or {}),
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + u"\n"
        encoded_size = len(line.encode("utf-8"))
        with self.lock:
            try:
                self._ensure_directory(self.path)
                self._rotate_if_needed(encoded_size)
                with io.open(self.path, "a", encoding="utf-8", newline="\n") as stream:
                    stream.write(line)
            except (IOError, OSError):
                fallback = os.path.join(tempfile.gettempdir(), "RezhimKioska-Legacy.log")
                if os.path.abspath(fallback) == os.path.abspath(self.path):
                    return False
                self.path = fallback
                self._ensure_directory(self.path)
                with io.open(self.path, "a", encoding="utf-8", newline="\n") as stream:
                    stream.write(line)
        return True

    def info(self, event, **data):
        return self.log(event, data, level="INFO")

    def warning(self, event, **data):
        return self.log(event, data, level="WARNING")

    def error(self, event, **data):
        return self.log(event, data, level="ERROR")

    def _ensure_directory(self, path):
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

    def _rotate_if_needed(self, incoming_size):
        if self.max_bytes <= 0 or not os.path.isfile(self.path):
            return
        if os.path.getsize(self.path) + incoming_size <= self.max_bytes:
            return
        if self.backup_count <= 0:
            os.remove(self.path)
            return
        oldest = "%s.%s" % (self.path, self.backup_count)
        if os.path.exists(oldest):
            os.remove(oldest)
        for index in range(self.backup_count - 1, 0, -1):
            source = "%s.%s" % (self.path, index)
            destination = "%s.%s" % (self.path, index + 1)
            if os.path.exists(source):
                os.rename(source, destination)
        os.rename(self.path, self.path + ".1")
