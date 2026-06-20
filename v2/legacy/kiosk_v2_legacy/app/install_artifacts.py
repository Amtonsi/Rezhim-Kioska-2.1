# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import copy
import hashlib
import os
import tempfile

from kiosk_v2_legacy.app.backup_store import LegacyAtomicReplacer


class InvalidArtifactSnapshot(ValueError):
    pass


class FileArtifactManager(object):
    def __init__(self, source_target_pairs, approved_target_roots, replacer=None):
        self.roots = tuple(self._normalize(path) for path in approved_target_roots)
        if not self.roots:
            raise ValueError("approved roots required")
        self.replacer = replacer or LegacyAtomicReplacer()
        artifacts = []
        targets = set()
        for source, target in source_target_pairs:
            source = self._normalize(source)
            target = self._approved(target)
            if not os.path.isfile(source):
                raise ValueError("artifact source missing")
            if target in targets:
                raise ValueError("duplicate artifact target")
            targets.add(target)
            artifacts.append((source, target))
        if not artifacts:
            raise ValueError("artifacts required")
        self.artifacts = tuple(artifacts)
        self._snapshot = None

    def capture(self):
        files = []
        owned = []
        owned_directories = self._missing_directories()
        for unused, target in self.artifacts:
            existed = os.path.isfile(target)
            data = self._read(target) if existed else b""
            if not existed:
                owned.append(target)
            files.append({
                "path": target,
                "existed": existed,
                "encoding": "base64",
                "data": base64.b64encode(data).decode("ascii"),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        result = {
            "schemaVersion": 1,
            "files": files,
            "ownedPaths": owned,
            "ownedDirectories": owned_directories,
        }
        self._snapshot = copy.deepcopy(result)
        return copy.deepcopy(result)

    def install(self):
        if self._snapshot is None:
            raise RuntimeError("snapshot required before install")
        pending = [(target, self._read(source)) for source, target in self.artifacts]
        try:
            for target, data in pending:
                self._atomic_write(target, data)
        except Exception:
            self.restore(self._snapshot)
            raise

    def verify(self):
        for source, target in self.artifacts:
            if not os.path.isfile(target):
                return False
            if hashlib.sha256(self._read(source)).digest() != hashlib.sha256(self._read(target)).digest():
                return False
        return True

    def restore(self, snapshot):
        records = self._records(snapshot)
        for record, data in records:
            if record["existed"]:
                self._atomic_write(record["path"], data)
            elif os.path.exists(record["path"]):
                os.remove(record["path"])
        self._remove_directories(snapshot)

    def verify_snapshot(self, snapshot):
        for record, data in self._records(snapshot):
            path = record["path"]
            if not record["existed"]:
                if os.path.exists(path):
                    return False
            elif not os.path.isfile(path) or self._read(path) != data:
                return False
        return True

    def remove_owned(self, snapshot):
        self._records(snapshot)
        for path in snapshot["ownedPaths"]:
            path = self._exact(path)
            if os.path.isfile(path):
                os.remove(path)
        self._remove_directories(snapshot)

    def _records(self, snapshot):
        expected_fields = set(("schemaVersion", "files", "ownedPaths", "ownedDirectories"))
        if not isinstance(snapshot, dict) or set(snapshot) != expected_fields:
            raise InvalidArtifactSnapshot("invalid snapshot")
        if snapshot["schemaVersion"] != 1:
            raise InvalidArtifactSnapshot("unsupported snapshot")
        records = []
        seen = set()
        absent = set()
        expected_targets = set(target for unused, target in self.artifacts)
        for record in snapshot["files"]:
            fields = set(("path", "existed", "encoding", "data", "sha256"))
            if not isinstance(record, dict) or set(record) != fields:
                raise InvalidArtifactSnapshot("invalid file record")
            path = self._exact(record["path"])
            if path in seen or record["encoding"] != "base64":
                raise InvalidArtifactSnapshot("invalid file record")
            seen.add(path)
            try:
                data = base64.b64decode(record["data"])
            except Exception:
                raise InvalidArtifactSnapshot("invalid base64")
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise InvalidArtifactSnapshot("digest mismatch")
            if not record["existed"]:
                if data:
                    raise InvalidArtifactSnapshot("absent file has data")
                absent.add(path)
            item = dict(record)
            item["path"] = path
            records.append((item, data))
        if seen != expected_targets:
            raise InvalidArtifactSnapshot("target set mismatch")
        owned = set(self._exact(path) for path in snapshot["ownedPaths"])
        if owned != absent:
            raise InvalidArtifactSnapshot("owned set mismatch")
        for directory in snapshot["ownedDirectories"]:
            self._approved(directory)
        return records

    def _missing_directories(self):
        missing = set()
        for unused, target in self.artifacts:
            current = os.path.dirname(target)
            while any(
                current == root or current.startswith(root.rstrip("\\/") + os.sep)
                for root in self.roots
            ):
                if os.path.isdir(current):
                    break
                missing.add(current)
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent
        return sorted(missing, key=len, reverse=True)

    def _remove_directories(self, snapshot):
        directories = sorted(
            (self._approved(path) for path in snapshot["ownedDirectories"]),
            key=len,
            reverse=True,
        )
        for directory in directories:
            if os.path.isdir(directory):
                try:
                    os.rmdir(directory)
                except OSError:
                    pass

    def _exact(self, path):
        path = self._approved(path)
        if path not in set(target for unused, target in self.artifacts):
            raise InvalidArtifactSnapshot("unknown target")
        return path

    def _approved(self, path):
        path = self._normalize(path)
        for root in self.roots:
            if path == root or path.startswith(root.rstrip("\\/") + os.sep):
                return path
        raise ValueError("target outside approved roots")

    def _atomic_write(self, path, data):
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        descriptor, temporary = tempfile.mkstemp(prefix=".kiosk-v2-", suffix=".tmp", dir=directory)
        try:
            stream = os.fdopen(descriptor, "wb")
            descriptor = None
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                stream.close()
            self.replacer.replace(temporary, path)
            temporary = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary and os.path.exists(temporary):
                os.remove(temporary)

    @staticmethod
    def _read(path):
        stream = open(path, "rb")
        try:
            return stream.read()
        finally:
            stream.close()

    @staticmethod
    def _normalize(path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))
