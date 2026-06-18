try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.policy_engine import PolicyOperation
from python_kiosk.system_backend import WindowsSystemBackend


class FakeCompleted(object):
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class FakeRunner(object):
    def __init__(self):
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        text = " ".join(command).lower()
        if command[:2] == ["wmic", "useraccount"]:
            return FakeCompleted("SID=S-1-5-21-100-200-300-1007\r\n")
        if command[:2] == ["reg", "query"]:
            return FakeCompleted("", 0)
        if command[:2] == ["net", "user"]:
            return FakeCompleted("User name                    test\r\n", 0)
        if command[:2] == ["net", "localgroup"]:
            return FakeCompleted("Users\r\n", 0)
        if "profileimagepath" in text:
            return FakeCompleted("ProfileImagePath    REG_EXPAND_SZ    C:\\Users\\test\r\n", 0)
        return FakeCompleted("", 0)


class MissingUserRunner(FakeRunner):
    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        if command[:2] == ["net", "user"]:
            return FakeCompleted("The user name could not be found.", 2)
        return FakeCompleted("", 0)


class AdminOperatorRunner(FakeRunner):
    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        if command[:2] == ["net", "user"]:
            return FakeCompleted("User name                    test\r\n", 0)
        if command[:4] == ["wmic", "group", "where", "sid='S-1-5-32-544'"]:
            return FakeCompleted("Name=Administrators\r\n", 0)
        if command[:3] == ["net", "localgroup", "Administrators"]:
            return FakeCompleted("Alias name     Administrators\r\n-------------------------------------------------------------------------------\r\ntest\r\n", 0)
        return FakeCompleted("", 0)


class WindowsSystemBackendTests(unittest.TestCase):
    def test_set_operator_shell_writes_shell_under_operator_hku(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "set_operator_shell",
                "set shell",
                data={
                    "operator_user": "test",
                    "shell_command": '"C:\\Kiosk\\RezhimKioska.exe" launch --config "C:\\Kiosk\\config\\kiosk.json"',
                },
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("Winlogon" in command and "Shell" in command for command in commands))
        self.assertTrue(any("RezhimKioska.exe" in command for command in commands))
        self.assertFalse(any("stop" in command.lower() for command in commands))

    def test_restore_operator_shell_sets_explorer_and_removes_known_policies(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "restore_operator_shell",
                "restore shell",
                data={"operator_user": "test", "shell": "explorer.exe"},
            )
        )
        backend.apply_operation(
            PolicyOperation(
                "restore_operator_policies",
                "restore policies",
                data={"operator_user": "test"},
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("explorer.exe" in command for command in commands))
        self.assertTrue(any("reg delete" in command and "DisableTaskMgr" in command for command in commands))
        self.assertFalse(any("taskkill" in command.lower() for command in commands))

    def test_apply_operator_policies_uses_only_registry_values(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "apply_hkcu_operator_policies",
                "apply policies",
                data={"operator_user": "test"},
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("DisableTaskMgr" in command for command in commands))
        self.assertTrue(any("NoRun" in command for command in commands))
        self.assertFalse(any("net stop" in command.lower() for command in commands))
        self.assertFalse(any("sc.exe" in command.lower() for command in commands))

    def test_ensure_operator_user_rejects_missing_account(self):
        backend = WindowsSystemBackend(command_runner=MissingUserRunner())

        with self.assertRaises(RuntimeError):
            backend.apply_operation(
                PolicyOperation(
                    "ensure_operator_user",
                    "ensure user",
                    data={"operator_user": "test"},
                )
            )

    def test_ensure_operator_user_rejects_local_admin_operator(self):
        backend = WindowsSystemBackend(command_runner=AdminOperatorRunner())

        with self.assertRaises(RuntimeError):
            backend.apply_operation(
                PolicyOperation(
                    "ensure_operator_user",
                    "ensure user",
                    data={"operator_user": "test"},
                )
            )


if __name__ == "__main__":
    unittest.main()
