# -*- coding: utf-8 -*-
import base64
import copy
import hashlib
import os
import tempfile


class InvalidArtifactSnapshot(ValueError):
    pass


class FileArtifactManager(object):
    def __init__(self, source_target_pairs, approved_target_roots):
        self.approved_roots = tuple(
            self._normalize(path) for path in approved_target_roots
        )
        if not self.approved_roots:
            raise ValueError("approved target roots are required")
        self.artifacts = []
        seen_targets = set()
        for source, target in source_target_pairs:
            source = self._normalize(source)
            target = self._require_approved(target)
            if not os.path.isfile(source):
                raise ValueError("artifact source does not exist")
            if target in seen_targets:
                raise ValueError("duplicate artifact target")
            seen_targets.add(target)
            self.artifacts.append((source, target))
        if not self.artifacts:
            raise ValueError("at least one artifact is required")
        self.artifacts = tuple(self.artifacts)
        self._last_snapshot = None

    def capture(self):
        files = []
        owned_paths = []
        for _source, target in self.artifacts:
            existed = os.path.isfile(target)
            data = self._read_bytes(target) if existed else b""
            if not existed:
                owned_paths.append(target)
            files.append(
                {
                    "path": target,
                    "existed": existed,
                    "encoding": "base64",
                    "data": base64.b64encode(data).decode("ascii"),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        snapshot = {
            "schemaVersion": 1,
            "files": files,
            "ownedPaths": owned_paths,
        }
        self._last_snapshot = copy.deepcopy(snapshot)
        return copy.deepcopy(snapshot)

    def install(self):
        if self._last_snapshot is None:
            raise RuntimeError("artifact snapshot is required before install")
        source_data = [
            (target, self._read_bytes(source)) for source, target in self.artifacts
        ]
        try:
            for target, data in source_data:
                self._atomic_write(target, data)
        except Exception:
            self.restore(self._last_snapshot)
            raise

    def verify(self):
        for source, target in self.artifacts:
            if not os.path.isfile(target):
                return False
            if self._hash_file(source) != self._hash_file(target):
                return False
        return True

    def restore(self, snapshot):
        records = self._validated_records(snapshot)
        for record, data in records:
            path = record["path"]
            if record["existed"]:
                self._atomic_write(path, data)
            elif os.path.exists(path):
                os.remove(path)

    def verify_snapshot(self, snapshot):
        records = self._validated_records(snapshot)
        for record, data in records:
            path = record["path"]
            if not record["existed"]:
                if os.path.exists(path):
                    return False
                continue
            if not os.path.isfile(path):
                return False
            if hashlib.sha256(self._read_bytes(path)).hexdigest() != record["sha256"]:
                return False
            if self._read_bytes(path) != data:
                return False
        return True

    def remove_owned(self, snapshot):
        self._validated_records(snapshot)
        for path in snapshot["ownedPaths"]:
            normalized = self._require_exact_target(path)
            if os.path.isfile(normalized):
                os.remove(normalized)

    def _validated_records(self, snapshot):
        if not isinstance(snapshot, dict) or set(snapshot) != {
            "schemaVersion",
            "files",
            "ownedPaths",
        }:
            raise InvalidArtifactSnapshot("invalid artifact snapshot fields")
        if snapshot["schemaVersion"] != 1:
            raise InvalidArtifactSnapshot("unsupported artifact snapshot")
        if not isinstance(snapshot["files"], list) or not isinstance(
            snapshot["ownedPaths"], list
        ):
            raise InvalidArtifactSnapshot("invalid artifact snapshot collections")
        expected_targets = {target for _source, target in self.artifacts}
        records = []
        seen = set()
        absent = set()
        for record in snapshot["files"]:
            if not isinstance(record, dict) or set(record) != {
                "path",
                "existed",
                "encoding",
                "data",
                "sha256",
            }:
                raise InvalidArtifactSnapshot("invalid artifact record")
            path = self._require_exact_target(record["path"])
            if path in seen:
                raise InvalidArtifactSnapshot("duplicate artifact record")
            seen.add(path)
            if record["encoding"] != "base64" or not isinstance(record["existed"], bool):
                raise InvalidArtifactSnapshot("invalid artifact encoding")
            try:
                data = base64.b64decode(record["data"].encode("ascii"), validate=True)
            except Exception as error:
                raise InvalidArtifactSnapshot("invalid artifact data") from error
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise InvalidArtifactSnapshot("artifact digest mismatch")
            if not record["existed"]:
                if data:
                    raise InvalidArtifactSnapshot("absent artifact contains data")
                absent.add(path)
            normalized_record = dict(record)
            normalized_record["path"] = path
            records.append((normalized_record, data))
        if seen != expected_targets:
            raise InvalidArtifactSnapshot("artifact target set mismatch")
        owned = {self._require_exact_target(path) for path in snapshot["ownedPaths"]}
        if owned != absent:
            raise InvalidArtifactSnapshot("owned path set mismatch")
        return records

    def _require_exact_target(self, path):
        normalized = self._require_approved(path)
        if normalized not in {target for _source, target in self.artifacts}:
            raise InvalidArtifactSnapshot("unrecognized artifact target")
        return normalized

    def _require_approved(self, path):
        normalized = self._normalize(path)
        for root in self.approved_roots:
            try:
                if os.path.commonpath((root, normalized)) == root:
                    return normalized
            except ValueError:
                continue
        raise ValueError("artifact target is outside approved roots")

    def _atomic_write(self, path, data):
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".kiosk-v2-",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

    def _hash_file(self, path):
        return hashlib.sha256(self._read_bytes(path)).hexdigest()

    def _read_bytes(self, path):
        with open(path, "rb") as stream:
            return stream.read()

    def _normalize(self, path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))
