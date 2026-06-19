# -*- coding: utf-8 -*-


class Operation(object):
    def __init__(
        self,
        operation_id,
        apply,
        rollback,
        verify,
        is_shell=False,
    ):
        operation_id = str(operation_id or "").strip()
        if not operation_id:
            raise ValueError("operation_id is required")
        for name, callback in (
            ("apply", apply),
            ("rollback", rollback),
            ("verify", verify),
        ):
            if not callable(callback):
                raise TypeError("{0} must be callable".format(name))
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
    def __init__(
        self,
        failed_operation_id,
        applied_ids,
        rolled_back_ids,
        rollback_failures,
    ):
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
        identifiers = [operation.operation_id for operation in self.operations]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("operation IDs must be unique")
        shell_indexes = [
            index for index, operation in enumerate(self.operations) if operation.is_shell
        ]
        if len(shell_indexes) > 1:
            raise ValueError("only one shell operation is allowed")
        if shell_indexes and shell_indexes[0] != len(self.operations) - 1:
            raise ValueError("shell operation must be last")

    def execute(self, dry_run=False):
        planned_ids = tuple(operation.operation_id for operation in self.operations)
        if dry_run:
            return TransactionResult(planned_ids, dry_run=True)

        applied = []
        current = None
        try:
            for current in self.operations:
                current.apply()
                applied.append(current)
                verified = current.verify()
                if verified is False:
                    raise RuntimeError("operation verification failed")
        except Exception:
            rolled_back = []
            rollback_failures = []
            for operation in reversed(applied):
                try:
                    operation.rollback()
                except Exception:
                    rollback_failures.append(operation.operation_id)
                else:
                    rolled_back.append(operation.operation_id)
            raise TransactionFailure(
                current.operation_id if current is not None else "unknown",
                [operation.operation_id for operation in applied],
                rolled_back,
                rollback_failures,
            )

        return TransactionResult(
            planned_ids,
            applied_ids=[operation.operation_id for operation in applied],
        )
