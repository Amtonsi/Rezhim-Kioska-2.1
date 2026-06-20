# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import ctypes
import hashlib
import json
import os
import tempfile


try:
    text_type = unicode
except NameError:
    text_type = str


MOVEFILE_REPLACE_EXISTING = 0x00000001
MOVEFILE_WRITE_THROUGH = 0x00000008
BACKUP_FIELDS = frozenset(
    (
        "schemaVersion",
        "buildFamily",
        "operatorSid",
        "operatorUser",
        "originalShell",
        "registryValues",
        "fileAcls",
        "configBackup",
        "integritySha256",
    )
)
INPUT_FIELDS = BACKUP_FIELDS - frozenset(("integritySha256",))


class BackupValidationError(ValueError):
    pass


class BackupIntegrityError(BackupValidationError):
    pass


class LegacyAtomicReplacer(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.kernel32.MoveFileExW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_ulong,
        ]
        self.kernel32.MoveFileExW.restype = ctypes.c_int

    def replace(self, source, target):
        flags = MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
        if not self.kernel32.MoveFileExW(source, target, flags):
            code = int(self.kernel32.GetLastError())
            raise OSError(code, "MoveFileExW failed")


class BackupStore(object):
    def __init__(self, path, acl, replacer=None):
        self.path = os.path.abspath(path)
        self.acl = acl
        self.replacer = replacer or LegacyAtomicReplacer()

    def save(self, metadata):
        document = copy.deepcopy(metadata)
        self._validate(document, False)
        document["integritySha256"] = self._digest(document)
        encoded = self._encode(document)
        existed = os.path.isfile(self.path)
        previous = self._read(self.path) if existed else None
        directory = os.path.dirname(self.path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        try:
            self._atomic_write(encoded)
            self.acl.protect_backup(self.path)
        except Exception:
            if existed:
                self._atomic_write(previous)
            elif os.path.exists(self.path):
                os.remove(self.path)
            raise
        return copy.deepcopy(document)

    def load(self, expected_build_family=None, expected_operator_sid=None):
        try:
            raw = self._read(self.path)
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]
            document = json.loads(raw.decode("utf-8"))
        except Exception:
            raise BackupValidationError("backup cannot be read")
        self._validate(document, True)
        if document["integritySha256"] != self._digest(document):
            raise BackupIntegrityError("backup integrity check failed")
        if expected_build_family is not None and document["buildFamily"] != expected_build_family:
            raise BackupValidationError("backup build family mismatch")
        if expected_operator_sid is not None and document["operatorSid"] != expected_operator_sid:
            raise BackupValidationError("backup operator SID mismatch")
        return copy.deepcopy(document)

    def _validate(self, document, require_integrity):
        if not isinstance(document, dict):
            raise BackupValidationError("backup must be an object")
        expected = BACKUP_FIELDS if require_integrity else INPUT_FIELDS
        if set(document) != expected:
            raise BackupValidationError("backup fields do not match schema")
        if document.get("schemaVersion") != 2:
            raise BackupValidationError("unsupported backup schema")
        if document.get("buildFamily") not in ("modern", "legacy"):
            raise BackupValidationError("invalid build family")
        for field in ("operatorSid", "operatorUser"):
            if not isinstance(document.get(field), text_type) or not document[field].strip():
                raise BackupValidationError("invalid identity field")
        if not isinstance(document.get("originalShell"), text_type):
            raise BackupValidationError("invalid original shell")
        if not isinstance(document.get("registryValues"), list):
            raise BackupValidationError("invalid registry snapshots")
        if not isinstance(document.get("fileAcls"), list):
            raise BackupValidationError("invalid ACL snapshots")
        if not isinstance(document.get("configBackup"), dict):
            raise BackupValidationError("invalid artifact snapshot")
        if require_integrity:
            digest = document.get("integritySha256")
            if not isinstance(digest, text_type) or len(digest) != 64:
                raise BackupValidationError("invalid backup digest")
            if any(item not in "0123456789abcdef" for item in digest):
                raise BackupValidationError("invalid backup digest")
        try:
            self._encode(document)
        except Exception:
            raise BackupValidationError("backup is not JSON serializable")

    def _digest(self, document):
        payload = dict(
            (key, value)
            for key, value in document.items()
            if key != "integritySha256"
        )
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if isinstance(canonical, text_type):
            canonical = canonical.encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _encode(self, document):
        encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
        if isinstance(encoded, text_type):
            encoded = encoded.encode("utf-8")
        return encoded + b"\n"

    def _atomic_write(self, data):
        directory = os.path.dirname(self.path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".backup-v2-",
            suffix=".tmp",
            dir=directory,
        )
        try:
            stream = os.fdopen(descriptor, "wb")
            descriptor = None
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                stream.close()
            self.replacer.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

    def _read(self, path):
        stream = open(path, "rb")
        try:
            return stream.read()
        finally:
            stream.close()
