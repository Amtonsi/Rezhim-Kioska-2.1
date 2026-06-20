# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Operation(object):
    def __init__(self, operation_id, apply, rollback, verify, is_shell=False):
        if not operation_id:
            raise ValueError("operation_id is required")
        if not callable(apply) or not callable(rollback) or not callable(verify):
            raise TypeError("operation callbacks must be callable")
        self.operation_id = operation_id
        self.apply = apply
        self.rollback = rollback
        self.verify = verify
        self.is_shell = bool(is_shell)


class TransactionResult(object):
    def __init__(self, planned_ids, applied_ids=(), succeeded=True, dry_run=False):
        self.planned_ids = tuple(planned_ids)
        self.applied_ids = tuple(applied_ids)
        self.succeeded = bool(succeeded)
        self.dry_run = bool(dry_run)


class TransactionFailure(RuntimeError):
    def __init__(self, failed_operation_id, applied_ids, rolled_back_ids, rollback_failures):
        RuntimeError.__init__(
            self,
            "transaction failed at operation: {0}".format(failed_operation_id),
        )
        self.failed_operation_id = failed_operation_id
        self.applied_ids = tuple(applied_ids)
        self.rolled_back_ids = tuple(rolled_back_ids)
        self.rollback_failures = tuple(rollback_failures)


class InstallTransaction(object):
    def __init__(self, operations):
        self.operations = tuple(operations)
        identifiers = [item.operation_id for item in self.operations]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("operation IDs must be unique")
        shell_indexes = [
            index for index, item in enumerate(self.operations) if item.is_shell
        ]
        if len(shell_indexes) > 1:
            raise ValueError("only one shell operation is allowed")
        if shell_indexes and shell_indexes[0] != len(self.operations) - 1:
            raise ValueError("shell operation must be last")

    def execute(self, dry_run=False):
        planned = tuple(item.operation_id for item in self.operations)
        if dry_run:
            return TransactionResult(planned, dry_run=True)
        applied = []
        current = None
        try:
            for current in self.operations:
                current.apply()
                applied.append(current)
                if current.verify() is False:
                    raise RuntimeError("operation verification failed")
        except Exception:
            rolled_back = []
            rollback_failures = []
            for item in reversed(applied):
                try:
                    item.rollback()
                except Exception:
                    rollback_failures.append(item.operation_id)
                else:
                    rolled_back.append(item.operation_id)
            raise TransactionFailure(
                current.operation_id if current is not None else "unknown",
                [item.operation_id for item in applied],
                rolled_back,
                rollback_failures,
            )
        return TransactionResult(
            planned,
            applied_ids=[item.operation_id for item in applied],
        )
