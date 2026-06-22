# -*- coding: utf-8 -*-
import os
import shutil
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.platform.admin_actions import (
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


class FakeFunction(object):
    def __init__(self, callback):
        self.callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.callback(*args)


class FakeShell32(object):
    def __init__(self):
        self.calls = []
        self.ShellExecuteExW = FakeFunction(self._execute)

    def _execute(self, info_pointer):
        info = info_pointer._obj
        self.calls.append((info.lpFile, info.lpParameters))
        info.hProcess = 123
        return True


class FakeKernel32(object):
    def __init__(self, exit_code):
        self.exit_code = exit_code
        self.wait_calls = []
        self.close_calls = []
        self.WaitForSingleObject = FakeFunction(self._wait)
        self.GetExitCodeProcess = FakeFunction(self._get_exit_code)
        self.CloseHandle = FakeFunction(self._close)

    def _wait(self, handle, timeout):
        self.wait_calls.append((int(handle), int(timeout)))
        return 0

    def _get_exit_code(self, handle, exit_code_pointer):
        exit_code_pointer._obj.value = self.exit_code
        return True

    def _close(self, handle):
        self.close_calls.append(int(handle))
        return True


class AdminActionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="kiosk-v2-admin-action-")
        self.restore = os.path.join(self.directory, "Restore.exe")
        self.configurator = os.path.join(self.directory, "Configurator.exe")
        open(self.restore, "wb").close()

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_manual_run_without_backup_recovers_desktop_and_reports_success(self):
        api = FakeAdminApi([0])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        self.assertTrue(action.run())
        self.assertEqual(
            [(self.restore, "recover-desktop --apply")],
            api.calls,
        )

    def test_installed_restore_waits_for_restore_then_recovers_current_desktop(self):
        state = os.path.join(self.directory, "state")
        os.makedirs(state)
        open(os.path.join(state, "backup-v2.json"), "wb").close()
        api = FakeAdminApi([0, 0])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        self.assertTrue(action.run())
        self.assertEqual(
            [
                (self.restore, "restore --apply"),
                (self.restore, "recover-desktop --apply"),
            ],
            api.calls,
        )

    def test_nonzero_restore_exit_is_failure_and_does_not_claim_completion(self):
        state = os.path.join(self.directory, "state")
        os.makedirs(state)
        open(os.path.join(state, "backup-v2.json"), "wb").close()
        api = FakeAdminApi([3])
        action = AdminActionLauncher(self.restore, self.configurator, api=api)

        with self.assertRaises(AdminActionError):
            action.run()

        self.assertEqual([(self.restore, "restore --apply")], api.calls)

    def test_native_elevation_waits_and_returns_child_exit_code(self):
        shell32 = FakeShell32()
        kernel32 = FakeKernel32(exit_code=3)
        api = NativeAdminActionApi(shell32=shell32, kernel32=kernel32)

        result = api.run_elevated(self.restore, "restore --apply")

        self.assertEqual(3, result)
        self.assertEqual([(123, 0xFFFFFFFF)], kernel32.wait_calls)
        self.assertEqual([123], kernel32.close_calls)


if __name__ == "__main__":
    unittest.main()
