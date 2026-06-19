# -*- coding: utf-8 -*-
import copy
import hashlib
import json
import os
import tempfile


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


class BackupStore(object):
    def __init__(self, path, acl):
        self.path = os.path.abspath(path)
        self.acl = acl

    def save(self, metadata):
        document = copy.deepcopy(metadata)
        self._validate(document, require_integrity=False)
        document["integritySha256"] = self._digest(document)
        encoded = self._encode(document)

        previous_exists = os.path.isfile(self.path)
        previous_bytes = self._read_bytes(self.path) if previous_exists else None
        directory = os.path.dirname(self.path)
        if not os.path.isdir(directory):
            os.makedirs(directory)

        try:
            self._atomic_write(encoded)
            self.acl.protect_backup(self.path)
        except Exception:
            self._restore_previous(previous_exists, previous_bytes)
            raise
        return copy.deepcopy(document)

    def load(self, expected_build_family=None, expected_operator_sid=None):
        try:
            with open(self.path, "r", encoding="utf-8-sig") as stream:
                document = json.load(stream)
        except (OSError, ValueError) as error:
            raise BackupValidationError("backup cannot be read") from error
        self._validate(document, require_integrity=True)
        if document["integritySha256"] != self._digest(document):
            raise BackupIntegrityError("backup integrity check failed")
        if (
            expected_build_family is not None
            and document["buildFamily"] != expected_build_family
        ):
            raise BackupValidationError("backup build family mismatch")
        if (
            expected_operator_sid is not None
            and document["operatorSid"] != expected_operator_sid
        ):
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
            if not isinstance(document.get(field), str) or not document[field].strip():
                raise BackupValidationError("invalid {0}".format(field))
        if not isinstance(document.get("originalShell"), str):
            raise BackupValidationError("invalid originalShell")
        for field in ("registryValues", "fileAcls"):
            if not isinstance(document.get(field), list):
                raise BackupValidationError("invalid {0}".format(field))
        if not isinstance(document.get("configBackup"), dict):
            raise BackupValidationError("invalid configBackup")
        if require_integrity:
            digest = document.get("integritySha256")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise BackupValidationError("invalid backup digest")
        try:
            self._encode(document)
        except (TypeError, ValueError) as error:
            raise BackupValidationError("backup is not JSON serializable") from error

    def _digest(self, document):
        payload = {
            key: value for key, value in document.items() if key != "integritySha256"
        }
        return hashlib.sha256(self._canonical_bytes(payload)).hexdigest()

    def _canonical_bytes(self, document):
        return json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def _encode(self, document):
        return (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")

    def _atomic_write(self, data):
        directory = os.path.dirname(self.path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".backup-v2-",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

    def _restore_previous(self, previous_exists, previous_bytes):
        if previous_exists:
            self._atomic_write(previous_bytes)
        elif os.path.exists(self.path):
            os.remove(self.path)

    def _read_bytes(self, path):
        with open(path, "rb") as stream:
            return stream.read()
