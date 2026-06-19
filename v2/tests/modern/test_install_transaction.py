# -*- coding: utf-8 -*-
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.app.transaction import (
    InstallTransaction,
    Operation,
    TransactionFailure,
)


class InstallTransactionTests(unittest.TestCase):
    def test_dry_run_returns_plan_without_invoking_operations(self):
        calls = []
        operations = [
            Operation(
                "protect_files",
                apply=lambda: calls.append("apply"),
                rollback=lambda: calls.append("rollback"),
                verify=lambda: calls.append("verify"),
            ),
            Operation(
                "set_shell",
                apply=lambda: calls.append("shell"),
                rollback=lambda: calls.append("shell_rollback"),
                verify=lambda: calls.append("shell_verify"),
                is_shell=True,
            ),
        ]

        result = InstallTransaction(operations).execute(dry_run=True)

        self.assertEqual(("protect_files", "set_shell"), result.planned_ids)
        self.assertEqual((), result.applied_ids)
        self.assertEqual([], calls)

    def test_apply_and_verify_run_in_stable_order(self):
        calls = []

        def operation(name):
            return Operation(
                name,
                apply=lambda: calls.append("apply:" + name),
                rollback=lambda: calls.append("rollback:" + name),
                verify=lambda: calls.append("verify:" + name),
                is_shell=name == "set_shell",
            )

        result = InstallTransaction(
            [operation("protect_files"), operation("set_shell")]
        ).execute()

        self.assertEqual(
            [
                "apply:protect_files",
                "verify:protect_files",
                "apply:set_shell",
                "verify:set_shell",
            ],
            calls,
        )
        self.assertEqual(("protect_files", "set_shell"), result.applied_ids)
        self.assertTrue(result.succeeded)

    def test_failure_rolls_applied_operations_back_in_reverse_order(self):
        calls = []

        def first(name):
            return Operation(
                name,
                apply=lambda: calls.append("apply:" + name),
                rollback=lambda: calls.append("rollback:" + name),
                verify=lambda: calls.append("verify:" + name),
            )

        def fail_apply():
            calls.append("apply:policies")
            raise RuntimeError("write failed")

        transaction = InstallTransaction(
            [
                first("protect_files"),
                first("write_config"),
                Operation("policies", fail_apply, lambda: None, lambda: None),
            ]
        )

        with self.assertRaises(TransactionFailure) as caught:
            transaction.execute()

        self.assertEqual("policies", caught.exception.failed_operation_id)
        self.assertEqual(("write_config", "protect_files"), caught.exception.rolled_back_ids)
        self.assertEqual((), caught.exception.rollback_failures)
        self.assertEqual(
            [
                "apply:protect_files",
                "verify:protect_files",
                "apply:write_config",
                "verify:write_config",
                "apply:policies",
                "rollback:write_config",
                "rollback:protect_files",
            ],
            calls,
        )

    def test_verify_failure_rolls_back_the_just_applied_operation(self):
        calls = []

        def fail_verify():
            calls.append("verify")
            raise RuntimeError("mismatch")

        operation = Operation(
            "policies",
            apply=lambda: calls.append("apply"),
            rollback=lambda: calls.append("rollback"),
            verify=fail_verify,
        )

        with self.assertRaises(TransactionFailure) as caught:
            InstallTransaction([operation]).execute()

        self.assertEqual(["apply", "verify", "rollback"], calls)
        self.assertEqual(("policies",), caught.exception.rolled_back_ids)

    def test_rollback_failures_are_reported_without_stopping_other_rollbacks(self):
        calls = []

        def broken_rollback():
            calls.append("rollback:second")
            raise RuntimeError("rollback failed")

        transaction = InstallTransaction(
            [
                Operation(
                    "first",
                    lambda: calls.append("apply:first"),
                    lambda: calls.append("rollback:first"),
                    lambda: None,
                ),
                Operation(
                    "second",
                    lambda: calls.append("apply:second"),
                    broken_rollback,
                    lambda: None,
                ),
                Operation(
                    "failure",
                    lambda: (_ for _ in ()).throw(RuntimeError("failure")),
                    lambda: None,
                    lambda: None,
                ),
            ]
        )

        with self.assertRaises(TransactionFailure) as caught:
            transaction.execute()

        self.assertEqual(
            ["rollback:second", "rollback:first"],
            [call for call in calls if call.startswith("rollback:")],
        )
        self.assertEqual(("first",), caught.exception.rolled_back_ids)
        self.assertEqual(("second",), caught.exception.rollback_failures)

    def test_shell_operation_must_be_unique_and_last(self):
        regular = Operation("policies", lambda: None, lambda: None, lambda: None)
        shell = Operation(
            "set_shell",
            lambda: None,
            lambda: None,
            lambda: None,
            is_shell=True,
        )

        with self.assertRaises(ValueError):
            InstallTransaction([shell, regular])
        with self.assertRaises(ValueError):
            InstallTransaction([shell, shell])


if __name__ == "__main__":
    unittest.main()
