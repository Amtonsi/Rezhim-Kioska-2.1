try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.process_watchdog import (
    ProcessWatchdog,
    windows_allowed_process_running,
    windows_process_ids_for_name,
    windows_process_name_running,
)
from python_kiosk.process_watchdog import windows_process_path_running


class FakeProcess(object):
    def __init__(self, return_code=None):
        self.return_code = return_code

    def poll(self):
        return self.return_code


class FakeFactory(object):
    def __init__(self, processes):
        self.processes = list(processes)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self.processes.pop(0)


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class ProcessWatchdogTests(unittest.TestCase):
    def test_tick_starts_process_when_none_is_running(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual([([r"C:\App\app.exe"], {})], factory.calls)

    def test_tick_keeps_running_process(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)
        watchdog.tick()

        action = watchdog.tick()

        self.assertEqual("running", action)
        self.assertEqual(1, len(factory.calls))

    def test_tick_restarts_finished_process(self):
        first = FakeProcess(return_code=0)
        second = FakeProcess(return_code=None)
        factory = FakeFactory([first, second])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("restarted", action)
        self.assertEqual(1, len(factory.calls))

    def test_watchdog_logs_start_and_restart(self):
        first = FakeProcess(return_code=0)
        second = FakeProcess(return_code=None)
        factory = FakeFactory([first, second])
        logger = FakeLogger()
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            logger=logger,
        )

        self.assertEqual("started", watchdog.tick())
        watchdog.process = first
        self.assertEqual("restarted", watchdog.tick())

        events = [(level, event) for level, event, _ in logger.events]
        self.assertIn(("info", "watchdog.started"), events)
        self.assertIn(("warning", "watchdog.restarted"), events)

    def test_watchdog_logs_do_not_store_full_command_arguments(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        logger = FakeLogger()
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe", "--password", "secret-pass"],
            process_factory=factory,
            logger=logger,
        )

        watchdog.tick()

        self.assertEqual(r"C:\App\app.exe", logger.events[0][2]["executable"])
        self.assertEqual(2, logger.events[0][2]["argument_count"])
        logged_text = str(logger.events)
        self.assertIn("argument_count", logged_text)
        self.assertNotIn("secret-pass", logged_text)
        self.assertNotIn("--password", logged_text)

    def test_tick_does_not_start_duplicate_when_same_app_is_already_running(self):
        first = FakeProcess(return_code=0)
        factory = FakeFactory([FakeProcess(return_code=None)])
        bring_calls = []
        watchdog = ProcessWatchdog(
            [r"C:\Windows\System32\notepad.exe"],
            process_factory=factory,
            process_running=lambda: True,
            bring_existing_to_front=lambda: bring_calls.append("front"),
        )
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("running", action)
        self.assertEqual([], factory.calls)
        self.assertEqual(["front"], bring_calls)

    def test_tick_starts_second_instance_only_when_single_instance_disabled(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog(
            [r"C:\Windows\System32\notepad.exe"],
            process_factory=factory,
            process_running=lambda: True,
            single_instance=False,
        )

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual(1, len(factory.calls))

    def test_start_passes_working_directory_and_waits_for_input_idle(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        wait_calls = []
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            working_directory=r"C:\App",
            input_idle_waiter=lambda process, timeout: wait_calls.append((process, timeout)),
        )

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual(r"C:\App", factory.calls[0][1]["cwd"])
        self.assertEqual([(watchdog.process, 5)], wait_calls)

    def test_tick_does_not_restart_when_restart_on_exit_is_disabled(self):
        first = FakeProcess(return_code=0)
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            restart_on_exit=False,
        )
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("exited", action)
        self.assertEqual([], factory.calls)

    def test_windows_process_name_running_detects_image_name_from_tasklist(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            return b"notepad.exe                  1234 Console"

        running = windows_process_name_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)
        self.assertEqual("tasklist", calls[0][0])

    def test_windows_process_path_running_matches_exact_executable_path(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Windows\\System32\\notepad.exe,100\r\n"
                "PC,C:\\Temp\\notepad.exe,101\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)
        self.assertEqual("wmic", calls[0][0])

    def test_windows_process_path_running_rejects_same_name_different_path(self):
        def fake_runner(command, **kwargs):
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Temp\\notepad.exe,101\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertFalse(running)

    def test_allowed_process_running_falls_back_to_image_name_for_delegating_exe(self):
        calls = []

        def fake_path_runner(command, **kwargs):
            calls.append(("path", command[0]))
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad\\Notepad.exe,101\r\n"
            ).encode("utf-8")

        def fake_name_runner(command, **kwargs):
            calls.append(("name", command[0]))
            return (
                "Node,ProcessId\r\n"
                "PC,101\r\n"
            ).encode("utf-8")

        running = windows_allowed_process_running(
            r"C:\Windows\System32\notepad.exe",
            path_command_runner=fake_path_runner,
            name_command_runner=fake_name_runner,
        )

        self.assertTrue(running)
        self.assertEqual([("path", "wmic"), ("name", "wmic")], calls)

    def test_allowed_process_running_uses_wmic_name_before_tasklist_fallback(self):
        calls = []

        def fake_path_runner(command, **kwargs):
            calls.append(("path", command[0]))
            return "Node,ExecutablePath,ProcessId\r\n".encode("utf-8")

        def fake_name_runner(command, **kwargs):
            calls.append(("name", command[0]))
            return (
                "Node,ProcessId\r\n"
                "PC,202\r\n"
            ).encode("utf-8")

        running = windows_allowed_process_running(
            r"C:\Windows\System32\notepad.exe",
            path_command_runner=fake_path_runner,
            name_command_runner=fake_name_runner,
            tasklist_command_runner=lambda command, **kwargs: calls.append(("tasklist", command[0])),
        )

        self.assertTrue(running)
        self.assertEqual([("path", "wmic"), ("name", "wmic")], calls)

    def test_windows_process_ids_for_name_reads_wmic_process_ids(self):
        def fake_runner(command, **kwargs):
            return (
                "Node,ProcessId\r\n"
                "PC,101\r\n"
                "PC,102\r\n"
            ).encode("utf-8")

        pids = windows_process_ids_for_name(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertEqual(set([101, 102]), pids)

    def test_windows_process_path_running_accepts_bom_and_blank_wmic_lines(self):
        def fake_runner(command, **kwargs):
            return (
                "\r\n"
                "\ufeffNode,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Windows\\System32\\notepad.exe,100\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)


if __name__ == "__main__":
    unittest.main()
