# -*- coding: utf-8 -*-
import datetime
import json
import logging
import logging.handlers
import os
import threading


REDACTED = "[REDACTED]"
RESERVED_FIELDS = frozenset(("timestampUtc", "event", "level"))
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
    if not isinstance(key, str):
        return "nonstringkey"
    return "".join(character.lower() for character in key if character.isalnum())


def _is_sensitive_key(key):
    normalized = _normalized_key(key)
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _safe_value(value, key=""):
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, BaseException):
        return {"errorType": value.__class__.__name__}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"valueType": "bytes", "length": len(value)}
    if isinstance(value, dict):
        result = {}
        for item_key, item_value in value.items():
            safe_key = item_key if isinstance(item_key, str) else "nonStringKey"
            result[safe_key] = _safe_value(item_value, safe_key)
        return result
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    return {"valueType": value.__class__.__name__}


def _utc_timestamp(clock):
    value = clock.utcnow()
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + "{0:03d}Z".format(
        value.microsecond // 1000
    )


class SafeEvent(object):
    def __init__(self, event_name, level, fields=None, clock=None):
        if not isinstance(event_name, str) or not event_name.strip():
            raise ValueError("Audit event name is required")
        if level not in LEVELS:
            raise ValueError("Unsupported audit level")
        fields = dict(fields or {})
        reserved = RESERVED_FIELDS.intersection(fields)
        if reserved:
            raise ValueError("Reserved audit fields cannot be overridden")
        self.event_name = event_name.strip()
        self.level = level
        self.fields = _safe_value(fields)
        self.clock = clock or SystemClock()

    def to_dict(self):
        event = {
            "timestampUtc": _utc_timestamp(self.clock),
            "event": self.event_name,
            "level": self.level,
        }
        for key, value in self.fields.items():
            safe_key = key if isinstance(key, str) else "nonStringKey"
            event[safe_key] = _safe_value(value, safe_key)
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
        if level not in LEVELS:
            raise ValueError("Unsupported audit level")
        if int(max_bytes) <= 0:
            raise ValueError("max_bytes must be positive")
        if int(backup_count) < 1:
            raise ValueError("backup_count must be positive")
        directory = os.path.dirname(os.path.abspath(log_path))
        if not os.path.isdir(directory):
            os.makedirs(directory)
        self.clock = clock or SystemClock()
        self.closed = False
        self._lock = threading.RLock()
        self._logger = logging.Logger(
            "kiosk_v2_audit_{0}".format(id(self)),
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
            if level not in LEVELS:
                raise ValueError("Unsupported audit level")
            event = SafeEvent(
                event_name,
                level,
                fields,
                clock=self.clock,
            ).to_dict()
            line = json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
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
