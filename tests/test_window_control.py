try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.window_control import AppWindowController


class FakeWindowBackend(object):
    def __init__(self, windows=None):
        self.minimized = False
        self.calls = []
        self.windows = windows or [100]
        self.minimized_by_hwnd = {}

    def find_windows_for_executable(self, executable_path):
        self.calls.append(("find", executable_path))
        return list(self.windows)

    def is_minimized(self, hwnd):
        self.calls.append(("is_minimized", hwnd))
        if hwnd in self.minimized_by_hwnd:
            return self.minimized_by_hwnd[hwnd]
        return self.minimized

    def bring_to_front(self, hwnd):
        self.calls.append(("bring_to_front", hwnd))

    def restore(self, hwnd):
        self.calls.append(("restore", hwnd))
        self.minimized = False

    def maximize(self, hwnd):
        self.calls.append(("maximize", hwnd))

    def wait_for_window(self, executable_path, timeout_seconds=5):
        self.calls.append(("wait_for_window", executable_path, timeout_seconds))
        return 100

    def clear_topmost(self, hwnd):
        self.calls.append(("clear_topmost", hwnd))


class AppWindowControllerTests(unittest.TestCase):
    def test_reports_minimized_when_allowed_app_window_is_iconic(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.is_minimized(r"C:\App\app.exe"))

    def test_reports_minimized_when_any_allowed_app_window_is_iconic(self):
        backend = FakeWindowBackend(windows=[100, 200])
        backend.minimized_by_hwnd = {100: False, 200: True}
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.is_minimized(r"C:\App\app.exe"))
        self.assertIn(("is_minimized", 100), backend.calls)
        self.assertIn(("is_minimized", 200), backend.calls)

    def test_bring_to_front_marks_allowed_window_topmost(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.bring_to_front(r"C:\App\app.exe"))
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_restore_unminimizes_allowed_window(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.restore(r"C:\App\app.exe"))
        self.assertFalse(backend.minimized)
        self.assertIn(("restore", 100), backend.calls)

    def test_ensure_foreground_restores_and_places_allowed_app_topmost(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.ensure_foreground(r"C:\App\app.exe"))

        self.assertFalse(backend.minimized)
        self.assertIn(("restore", 100), backend.calls)
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_ensure_foreground_can_wait_for_window_and_maximize(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(
            controller.ensure_foreground(
                r"C:\App\app.exe",
                wait=True,
                timeout_seconds=7,
                start_maximized=True,
            )
        )

        self.assertIn(("wait_for_window", r"C:\App\app.exe", 7), backend.calls)
        self.assertIn(("maximize", 100), backend.calls)
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_release_topmost_clears_allowed_window_topmost_state(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.release_topmost(r"C:\App\app.exe"))
        self.assertIn(("clear_topmost", 100), backend.calls)

    def test_window_backend_falls_back_to_image_name_when_exact_path_has_no_pids(self):
        from python_kiosk.window_control import WindowsWindowBackend

        class Backend(WindowsWindowBackend):
            def __init__(self):
                pass

            def _process_ids_for_exact_path(self, executable_path):
                return set()

            def _process_ids_for_image_name(self, executable_path):
                return set([101])

        backend = Backend()

        self.assertEqual(set([101]), backend._process_ids_for_executable(r"C:\Windows\System32\notepad.exe"))

    def test_windows_backend_uses_thread_input_and_alt_fallback_to_force_foreground(self):
        from python_kiosk.window_control import WindowsWindowBackend

        class FakeWin32Api(object):
            def __init__(self):
                self.calls = []
                self.foreground = 200
                self.alt_sent = False

            def is_iconic(self, hwnd):
                self.calls.append(("is_iconic", hwnd))
                return False

            def show_window(self, hwnd, command):
                self.calls.append(("show_window", hwnd, command))

            def set_window_pos(self, hwnd, insert_after, flags):
                self.calls.append(("set_window_pos", hwnd, insert_after, flags))

            def get_foreground_window(self):
                self.calls.append(("get_foreground_window",))
                return self.foreground

            def get_current_thread_id(self):
                self.calls.append(("get_current_thread_id",))
                return 33

            def get_window_thread_process_id(self, hwnd):
                self.calls.append(("get_window_thread_process_id", hwnd))
                return {100: 11, 200: 22}.get(hwnd, 0)

            def attach_thread_input(self, source_thread, target_thread, attach):
                self.calls.append(
                    ("attach_thread_input", source_thread, target_thread, attach)
                )
                return True

            def bring_window_to_top(self, hwnd):
                self.calls.append(("bring_window_to_top", hwnd))

            def set_active_window(self, hwnd):
                self.calls.append(("set_active_window", hwnd))

            def set_focus(self, hwnd):
                self.calls.append(("set_focus", hwnd))

            def set_foreground_window(self, hwnd):
                self.calls.append(("set_foreground_window", hwnd))
                if self.alt_sent:
                    self.foreground = hwnd
                    return True
                return False

            def send_alt_keypress(self):
                self.calls.append(("send_alt_keypress",))
                self.alt_sent = True

        api = FakeWin32Api()
        backend = WindowsWindowBackend(api=api, is_windows=True)

        backend.bring_to_front(100)

        self.assertIn(("attach_thread_input", 33, 11, True), api.calls)
        self.assertIn(("attach_thread_input", 33, 22, True), api.calls)
        self.assertIn(("bring_window_to_top", 100), api.calls)
        self.assertIn(("set_active_window", 100), api.calls)
        self.assertIn(("set_focus", 100), api.calls)
        self.assertIn(("send_alt_keypress",), api.calls)
        self.assertIn(("set_foreground_window", 100), api.calls)
        self.assertIn(("attach_thread_input", 33, 11, False), api.calls)
        self.assertIn(("attach_thread_input", 33, 22, False), api.calls)


if __name__ == "__main__":
    unittest.main()
