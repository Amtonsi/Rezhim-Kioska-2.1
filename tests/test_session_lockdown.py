try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.session_lockdown import (
    WindowsDesktopBackend,
    WindowsSessionLockdown,
    recover_current_desktop,
)


class FakeDesktopBackend(object):
    def __init__(self):
        self.calls = []

    def lockdown_current_desktop_shell(self):
        self.calls.append("lockdown_current_desktop_shell")
        return {
            "shell_window": 100,
            "hidden_windows": [100, 200],
            "closed_explorer": False,
        }

    def restore_current_desktop_shell(self):
        self.calls.append("restore_current_desktop_shell")
        return {"restored_windows": [100, 200]}


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class FakeWindowsDesktopBackend(WindowsDesktopBackend):
    def __init__(self):
        super(FakeWindowsDesktopBackend, self).__init__()
        self.show_calls = []
        self.close_calls = []

    def _find_shell_windows(self):
        return [100, 200]

    def _find_window(self, class_name):
        return 100 if class_name == "Shell_TrayWnd" else 0

    def _show_window(self, hwnd, command):
        self.show_calls.append((hwnd, command))
        return True

    def _post_close(self, hwnd):
        self.close_calls.append(hwnd)
        return True

    def _is_window(self, hwnd):
        return True


class SessionLockdownTests(unittest.TestCase):
    def test_operator_mode_locks_only_current_desktop_shell(self):
        backend = FakeDesktopBackend()
        logger = FakeLogger()
        lockdown = WindowsSessionLockdown(backend=backend, logger=logger)

        result = lockdown.activate_operator_mode()

        self.assertEqual(["lockdown_current_desktop_shell"], backend.calls)
        self.assertFalse(result["closed_explorer"])
        self.assertIn(("info", "session.lockdown_enabled"), [(level, event) for level, event, _ in logger.events])
        logged_text = str(logger.events)
        self.assertNotIn("stop_services", logged_text)
        self.assertNotIn("clear_startup", logged_text)
        self.assertNotIn("kill_processes", logged_text)

    def test_desktop_backend_hides_shell_without_posting_wm_close(self):
        backend = FakeWindowsDesktopBackend()

        result = backend.lockdown_current_desktop_shell()

        self.assertEqual(
            [(100, WindowsDesktopBackend.SW_HIDE), (200, WindowsDesktopBackend.SW_HIDE)],
            backend.show_calls,
        )
        self.assertEqual([], backend.close_calls)
        self.assertFalse(result["closed_explorer"])

    def test_release_restores_hidden_current_desktop_windows(self):
        backend = FakeDesktopBackend()
        logger = FakeLogger()
        lockdown = WindowsSessionLockdown(backend=backend, logger=logger)

        lockdown.activate_operator_mode()
        result = lockdown.release_operator_mode()

        self.assertEqual(
            ["lockdown_current_desktop_shell", "restore_current_desktop_shell"],
            backend.calls,
        )
        self.assertEqual([100, 200], result["restored_windows"])
        self.assertIn(("info", "session.lockdown_released"), [(level, event) for level, event, _ in logger.events])

    def test_desktop_backend_restore_finds_shell_windows_when_state_was_lost(self):
        backend = FakeWindowsDesktopBackend()

        result = backend.restore_current_desktop_shell()

        self.assertEqual(
            [(100, WindowsDesktopBackend.SW_SHOW), (200, WindowsDesktopBackend.SW_SHOW)],
            backend.show_calls,
        )
        self.assertEqual([100, 200], result["restored_windows"])

    def test_recover_current_desktop_restores_windows_and_starts_explorer(self):
        backend = FakeWindowsDesktopBackend()
        process_calls = []

        result = recover_current_desktop(
            backend=backend,
            process_factory=lambda command: process_calls.append(command),
        )

        self.assertEqual([["explorer.exe"]], process_calls)
        self.assertTrue(result["started_explorer"])
        self.assertEqual([100, 200], result["restored_windows"])


if __name__ == "__main__":
    unittest.main()
