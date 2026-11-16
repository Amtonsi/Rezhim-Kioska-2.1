# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.platform.admin_actions import (
    AdminActionError,
    AdminActionLauncher,
    NativeAdminActionApi,
)


class FakeAdminApi(object):
    def __init__(self, exit_codes):
        self.exit_codes = list(exit_codes)
        self.calls = []

    def run_elevated(self, executable, arguments):
        self.calls.append((executable, arguments))
        return self.exit_codes.pop(0)


class LegacyAdminActionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="kiosk-v2-legacy-admin-")
        self.restore = os.path.join(self.directory, "Restore.exe")
        self.configurator = os.path.join(self.directory, "Configurator.exe")
        open(self.restore, "wb").close()

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_manual_run_without_backup_needs_no_elevated_child(self):
        api = FakeAdminApi([0])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        self.assertTrue(action.run())
        self.assertEqual(
            [],
            api.calls,
        )

    def test_installed_restore_runs_restore_then_recovers_current_desktop(self):
        state = os.path.join(self.directory, "state")
        os.makedirs(state)
        open(os.path.join(state, "backup-v2.json"), "wb").close()
        api = FakeAdminApi([0])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        self.assertTrue(action.run())
        self.assertEqual(
            [
                (self.restore, "restore --apply"),
            ],
            api.calls,
        )

    def test_nonzero_restore_exit_is_failure(self):
        state = os.path.join(self.directory, "state")
        os.makedirs(state)
        open(os.path.join(state, "backup-v2.json"), "wb").close()
        api = FakeAdminApi([3])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        with self.assertRaises(AdminActionError):
            action.run()

        self.assertEqual([(self.restore, "restore --apply")], api.calls)

    def test_native_api_exposes_waiting_process_exit_code_contract(self):
        self.assertTrue(hasattr(NativeAdminActionApi, "run_elevated"))


if __name__ == "__main__":
    unittest.main()
