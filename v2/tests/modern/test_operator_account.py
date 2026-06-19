# -*- coding: utf-8 -*-
import inspect
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform import operator_account
from kiosk_v2_modern.platform.operator_account import (
    ADMINISTRATORS_SID,
    OperatorIdentity,
    OperatorPreflight,
    PreflightError,
    WindowsOperatorAccountApi,
)


class FakeAccountApi(object):
    def __init__(self, elevated=True, identity=None):
        self.elevated = elevated
        self.identity = identity
        self.lookups = []

    def is_elevated(self):
        return self.elevated

    def get_identity(self, username):
        self.lookups.append(username)
        return self.identity


class FakeNativeAccountApi(object):
    def __init__(self):
        self.group_names = ["Users", "KioskNested"]
        self.group_sids = {
            "Users": "S-1-5-32-545",
            "KioskNested": ADMINISTRATORS_SID,
        }

    def is_elevated(self):
        return True

    def local_user_info(self, username):
        return {"name": "test", "enabled": True}

    def account_sid(self, account_name):
        if account_name == "test":
            return "S-1-5-21-1-2-3-1001"
        return self.group_sids[account_name]

    def local_group_names(self, username):
        return list(self.group_names)


class OperatorAccountTests(unittest.TestCase):
    def test_non_elevated_process_is_denied_before_user_lookup(self):
        api = FakeAccountApi(elevated=False)

        with self.assertRaises(PreflightError) as caught:
            OperatorPreflight(api).validate("test")

        self.assertEqual("elevation_required", caught.exception.code)
        self.assertEqual([], api.lookups)

    def test_missing_local_user_is_denied(self):
        api = FakeAccountApi(elevated=True, identity=None)

        with self.assertRaises(PreflightError) as caught:
            OperatorPreflight(api).validate("test")

        self.assertEqual("operator_not_found", caught.exception.code)

    def test_disabled_operator_is_denied(self):
        identity = OperatorIdentity(
            "test",
            "S-1-5-21-1-2-3-1001",
            enabled=False,
            is_administrator=False,
        )

        with self.assertRaises(PreflightError) as caught:
            OperatorPreflight(FakeAccountApi(identity=identity)).validate("test")

        self.assertEqual("operator_disabled", caught.exception.code)

    def test_direct_or_indirect_administrator_is_denied(self):
        identity = OperatorIdentity(
            "test",
            "S-1-5-21-1-2-3-1001",
            enabled=True,
            is_administrator=True,
        )

        with self.assertRaises(PreflightError) as caught:
            OperatorPreflight(FakeAccountApi(identity=identity)).validate("test")

        self.assertEqual("operator_is_administrator", caught.exception.code)

    def test_standard_local_operator_is_returned(self):
        identity = OperatorIdentity(
            "test",
            "S-1-5-21-1-2-3-1001",
            enabled=True,
            is_administrator=False,
        )

        result = OperatorPreflight(FakeAccountApi(identity=identity)).validate("test")

        self.assertIs(identity, result)

    def test_domain_qualified_or_empty_name_is_rejected_without_lookup(self):
        for username in ("", "DOMAIN\\test", ".\\test", "test@example", "a/b"):
            api = FakeAccountApi(identity=None)
            with self.assertRaises(PreflightError) as caught:
                OperatorPreflight(api).validate(username)
            self.assertEqual("local_operator_required", caught.exception.code)
            self.assertEqual([], api.lookups)

    def test_windows_adapter_marks_indirect_admin_membership_by_sid(self):
        api = WindowsOperatorAccountApi(native=FakeNativeAccountApi())

        identity = api.get_identity("test")

        self.assertEqual("test", identity.username)
        self.assertEqual("S-1-5-21-1-2-3-1001", identity.sid)
        self.assertTrue(identity.enabled)
        self.assertTrue(identity.is_administrator)

    def test_preflight_source_uses_local_apis_and_no_command_runner(self):
        source = inspect.getsource(operator_account).lower()

        for forbidden in (
            "subprocess",
            "os.system",
            "wmic.exe",
            "net.exe",
            "powershell.exe",
            "logonuser",
            "createprocess",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
