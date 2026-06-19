# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json
import logging
import logging.handlers
import os
import threading


try:
    string_types = (basestring,)
    integer_types = (int, long)
except NameError:
    string_types = (str,)
    integer_types = (int,)


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "credential",
    "typedtext",
    "inputtext",
    "keystroke",
    "arguments",
    "commandline",
    "argv",
)
LEVELS = {
    "Debug": logging.DEBUG,
    "Info": logging.INFO,
    "Warning": logging.WARNING,
    "Error": logging.ERROR,
}


class SystemClock(object):
    def utcnow(self):
        return datetime.datetime.utcnow()


def _normalized_key(key):
    if not isinstance(key, string_types):
        return "nonstringkey"
    return "".join(character.lower() for character in key if character.isalnum())


def _safe_value(value, key=""):
    normalized = _normalized_key(key)
    if any(part in normalized for part in SENSITIVE_KEY_PARTS):
        return REDACTED
    if isinstance(value, BaseException):
        return {"errorType": value.__class__.__name__}
    if value is None or isinstance(value, (bool, float) + integer_types + string_types):
        return value
    if isinstance(value, dict):
        result = {}
        for item_key, item_value in value.items():
            safe_key = item_key if isinstance(item_key, string_types) else "nonStringKey"
            result[safe_key] = _safe_value(item_value, safe_key)
        return result
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    return {"valueType": value.__class__.__name__}


class SafeEvent(object):
    def __init__(self, event_name, level, fields=None, clock=None):
        if not event_name or level not in LEVELS:
            raise ValueError("Invalid audit event")
        self.event_name = event_name
        self.level = level
        self.fields = _safe_value(dict(fields or {}))
        self.clock = clock or SystemClock()

    def to_dict(self):
        now = self.clock.utcnow()
        event = {
            "timestampUtc": now.strftime("%Y-%m-%dT%H:%M:%S.")
            + "{0:03d}Z".format(now.microsecond // 1000),
            "event": self.event_name,
            "level": self.level,
        }
        event.update(self.fields)
        return event


class AuditLogger(object):
    def __init__(
        self,
        log_path,
        max_bytes,
        backup_count,
        level="Info",
        clock=None,
    ):
        directory = os.path.dirname(os.path.abspath(log_path))
        if not os.path.isdir(directory):
            os.makedirs(directory)
        self.clock = clock or SystemClock()
        self.closed = False
        self._lock = threading.RLock()
        self._logger = logging.Logger(
            "kiosk_v2_legacy_audit_{0}".format(id(self)),
            level=LEVELS[level],
        )
        self._logger.propagate = False
        self._handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=int(max_bytes),
            backupCount=int(backup_count),
            encoding="utf-8",
        )
        self._handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(self._handler)

    def emit(self, event_name, level="Info", **fields):
        with self._lock:
            if self.closed:
                raise RuntimeError("Audit logger is closed")
            event = SafeEvent(event_name, level, fields, self.clock).to_dict()
            line = json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            self._logger.log(LEVELS[level], line)

    def close(self):
        with self._lock:
            if self.closed:
                return
            self._handler.flush()
            self._logger.removeHandler(self._handler)
            self._handler.close()
            self.closed = True
