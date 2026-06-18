import subprocess
import time
import os
import csv


def _normalize_windows_path(path):
    return os.path.normcase(os.path.abspath(os.path.expandvars(path or ""))).rstrip("\\/")


def windows_process_name_running(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return False
    if os.name != "nt" and command_runner is None:
        return False

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            ["tasklist", "/FI", "IMAGENAME eq {0}".format(image_name), "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")
    return image_name.lower() in output.lower()


def windows_process_ids_for_path(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return set()
    if os.name != "nt" and command_runner is None:
        return set()

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            [
                "wmic",
                "process",
                "where",
                "name='{0}'".format(image_name),
                "get",
                "ProcessId,ExecutablePath",
                "/format:csv",
            ],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return set()

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")

    expected_path = _normalize_windows_path(executable_path)
    pids = set()
    rows = [
        row
        for row in csv.reader(output.splitlines())
        if row and any(cell.strip() for cell in row)
    ]
    if not rows:
        return pids
    headers = [cell.strip().lstrip("\ufeff").lower() for cell in rows[0]]
    try:
        path_index = headers.index("executablepath")
        pid_index = headers.index("processid")
    except ValueError:
        return pids

    for row in rows[1:]:
        if len(row) <= max(path_index, pid_index):
            continue
        if _normalize_windows_path(row[path_index]) != expected_path:
            continue
        try:
            pids.add(int(row[pid_index]))
        except ValueError:
            pass
    return pids


def windows_process_ids_for_name(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return set()
    if os.name != "nt" and command_runner is None:
        return set()

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            [
                "wmic",
                "process",
                "where",
                "name='{0}'".format(image_name),
                "get",
                "ProcessId",
                "/format:csv",
            ],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return set()

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")

    pids = set()
    rows = [
        row
        for row in csv.reader(output.splitlines())
        if row and any(cell.strip() for cell in row)
    ]
    if not rows:
        return pids
    headers = [cell.strip().lstrip("\ufeff").lower() for cell in rows[0]]
    try:
        pid_index = headers.index("processid")
    except ValueError:
        return pids

    for row in rows[1:]:
        if len(row) <= pid_index:
            continue
        try:
            pids.add(int(row[pid_index]))
        except ValueError:
            pass
    return pids


def windows_process_path_running(executable_path, command_runner=None):
    return bool(windows_process_ids_for_path(executable_path, command_runner))


def windows_allowed_process_running(
    executable_path,
    path_command_runner=None,
    name_command_runner=None,
    tasklist_command_runner=None,
):
    if windows_process_path_running(executable_path, path_command_runner):
        return True
    if windows_process_ids_for_name(executable_path, name_command_runner):
        return True
    return windows_process_name_running(executable_path, tasklist_command_runner)


class ProcessWatchdog(object):
    def __init__(
        self,
        command,
        restart_delay_seconds=2,
        process_factory=None,
        process_running=None,
        logger=None,
        working_directory=None,
        restart_on_exit=True,
        wait_for_input_idle=True,
        input_idle_waiter=None,
        start_maximized=False,
        single_instance=True,
        bring_existing_to_front=None,
    ):
        self.command = list(command)
        self.restart_delay_seconds = float(restart_delay_seconds)
        self.process_factory = process_factory or subprocess.Popen
        self.process_running = process_running or (lambda: False)
        self.logger = logger
        self.working_directory = working_directory
        self.restart_on_exit = bool(restart_on_exit)
        self.wait_for_input_idle = bool(wait_for_input_idle)
        self.input_idle_waiter = input_idle_waiter or wait_for_process_input_idle
        self.start_maximized = bool(start_maximized)
        self.single_instance = bool(single_instance)
        self.bring_existing_to_front = bring_existing_to_front or (lambda: False)
        self.process = None
        self.stopped = False

    def _start(self):
        kwargs = {}
        if self.working_directory:
            kwargs["cwd"] = self.working_directory
        self.process = self.process_factory(self.command, **kwargs)
        if self.wait_for_input_idle:
            try:
                self.input_idle_waiter(self.process, 5)
            except Exception as error:
                self._log("warning", "watchdog.wait_input_idle_failed", error=str(error))

    def tick(self):
        if self.stopped:
            return "stopped"
        if self.process is None:
            if self.single_instance and self.process_running():
                self._bring_existing_to_front()
                return "running"
            self._start()
            self._log("info", "watchdog.started")
            return "started"

        if self.process.poll() is None:
            return "running"

        if self.single_instance and self.process_running():
            self._bring_existing_to_front()
            return "running"

        if not self.restart_on_exit:
            self._log("warning", "watchdog.exited")
            return "exited"

        self._start()
        self._log("warning", "watchdog.restarted")
        return "restarted"

    def _log(self, level, event, **extra):
        if self.logger is None:
            return
        log_method = getattr(self.logger, level)
        data = {
            "executable": self.command[0] if self.command else "",
            "argument_count": max(0, len(self.command) - 1),
        }
        data.update(extra)
        log_method(event, **data)

    def _bring_existing_to_front(self):
        try:
            self.bring_existing_to_front()
        except Exception as error:
            self._log("warning", "watchdog.bring_existing_failed", error=str(error))

    def run_forever(self):
        while True:
            self.tick()
            time.sleep(self.restart_delay_seconds)

    def stop(self):
        self.stopped = True


def wait_for_process_input_idle(process, timeout_seconds=5):
    if os.name != "nt":
        return False
    handle = getattr(process, "_handle", None)
    if not handle:
        return False
    import ctypes

    timeout_ms = int(float(timeout_seconds) * 1000)
    result = ctypes.windll.user32.WaitForInputIdle(handle, timeout_ms)
    return result == 0
