# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ntpath


HANDOFF_GRACE_SECONDS = 5.0


try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


def normalize_executable_path(path):
    if not isinstance(path, string_types) or not path.strip():
        raise ValueError("Application path is required")
    return ntpath.normcase(ntpath.normpath(path.strip()))


class ApplicationSettings(object):
    __slots__ = (
        "path",
        "arguments",
        "working_directory",
        "restart_on_exit",
        "restart_delay_ms",
        "single_instance",
        "max_restart_attempts",
        "restart_window_seconds",
    )

    def __init__(
        self,
        path,
        arguments=(),
        working_directory="",
        restart_on_exit=True,
        restart_delay_ms=2000,
        single_instance=True,
        max_restart_attempts=5,
        restart_window_seconds=30,
    ):
        self.path = path
        normalize_executable_path(path)
        if isinstance(arguments, string_types):
            raise TypeError("Application arguments must be a sequence")
        self.arguments = tuple(arguments)
        self.working_directory = working_directory or ""
        self.restart_on_exit = bool(restart_on_exit)
        self.restart_delay_ms = int(restart_delay_ms)
        if self.restart_delay_ms < 0:
            raise ValueError("Restart delay cannot be negative")
        self.single_instance = bool(single_instance)
        self.max_restart_attempts = int(max_restart_attempts)
        if self.max_restart_attempts < 1:
            raise ValueError("Maximum restart attempts must be positive")
        self.restart_window_seconds = float(restart_window_seconds)
        if self.restart_window_seconds <= 0:
            raise ValueError("Restart window must be positive")


class ProcessRef(object):
    __slots__ = ("pid", "path", "running")

    def __init__(self, pid, path, running=True):
        self.pid = int(pid)
        self.path = path
        self.running = bool(running)


class SupervisorResult(object):
    __slots__ = (
        "status",
        "pid",
        "error_code",
        "conflict_pids",
        "previous_pid",
        "failure_count",
    )

    def __init__(
        self,
        status,
        pid=None,
        error_code=None,
        conflict_pids=(),
        previous_pid=None,
        failure_count=0,
    ):
        self.status = status
        self.pid = pid
        self.error_code = error_code
        self.conflict_pids = tuple(conflict_pids)
        self.previous_pid = previous_pid
        self.failure_count = int(failure_count)


class ProcessSupervisor(object):
    def __init__(self, settings, process_api, clock):
        self.settings = settings
        self.process_api = process_api
        self.clock = clock
        self._enabled = False
        self._pid = None
        self._restart_due_at = None
        self._conflict_pids = ()
        self._failure_times = []
        self._breaker_open = False
        self._tracked_since = None
        self._runtime_path = None
        self._handoff_parent_pid = None
        self._handoff_due_at = None

    @property
    def pid(self):
        return self._pid

    @property
    def enabled(self):
        return self._enabled

    def start(self):
        if self._enabled and self._tracked_process_is_running():
            self._clear_failures_after_stable_run()
            return SupervisorResult(
                "running",
                pid=self._pid,
                failure_count=len(self._failure_times),
            )
        if self._enabled and self._handoff_parent_pid is not None:
            return self._poll_handoff()
        self._enabled = True
        self._pid = None
        self._runtime_path = None
        self._restart_due_at = None
        self._conflict_pids = ()
        self._handoff_parent_pid = None
        self._handoff_due_at = None
        self._reset_breaker()
        discovery = self._discover_existing()
        if discovery is not None:
            return discovery
        discovery = self._discover_existing_by_name()
        if discovery is not None:
            return discovery
        return self._launch("started")

    def tick(self):
        if not self._enabled:
            return SupervisorResult("stopped")
        if self._handoff_parent_pid is not None:
            return self._poll_handoff()
        if self._breaker_open:
            return SupervisorResult(
                "crash_loop",
                failure_count=len(self._failure_times),
            )
        if self._tracked_process_is_running():
            self._clear_failures_after_stable_run()
            return SupervisorResult(
                "running",
                pid=self._pid,
                failure_count=len(self._failure_times),
            )

        previous_pid = self._pid
        previous_tracked_since = self._tracked_since
        self._pid = None
        self._runtime_path = None
        discovery = self._discover_existing()
        if discovery is not None:
            return discovery
        discovery = self._discover_existing_by_name()
        if discovery is not None:
            return discovery
        short_lived = (
            previous_pid is not None
            and previous_tracked_since is not None
            and self._now() - previous_tracked_since <= HANDOFF_GRACE_SECONDS
        )
        if short_lived:
            handoff = self._discover_handoff(previous_pid)
            if handoff is not None:
                return handoff
        if previous_pid is not None and not self.settings.restart_on_exit:
            self._enabled = False
            self._restart_due_at = None
            self._tracked_since = None
            return SupervisorResult("stopped", previous_pid=previous_pid)
        if previous_pid is not None:
            self._clear_failures_after_stable_run()
            self._record_failure()
            self._tracked_since = None
            if self._breaker_open:
                return SupervisorResult(
                    "crash_loop",
                    previous_pid=previous_pid,
                    failure_count=len(self._failure_times),
                )
        if self._restart_due_at is None:
            self._restart_due_at = self._now() + self._restart_delay_seconds()
        if self._now() < self._restart_due_at:
            return SupervisorResult(
                "waiting_restart",
                previous_pid=previous_pid,
                failure_count=len(self._failure_times),
            )
        discovery = self._discover_existing()
        if discovery is not None:
            self._restart_due_at = None
            return discovery
        discovery = self._discover_existing_by_name()
        if discovery is not None:
            self._restart_due_at = None
            return discovery
        return self._launch("restarted", previous_pid=previous_pid)

    def stop_supervision(self):
        previous_pid = self._pid
        handoff_parent_pid = self._handoff_parent_pid
        self._clear_handoff(previous_pid)
        self._clear_handoff(handoff_parent_pid)
        self._enabled = False
        self._pid = None
        self._runtime_path = None
        self._restart_due_at = None
        self._conflict_pids = ()
        self._tracked_since = None
        self._handoff_parent_pid = None
        self._handoff_due_at = None
        self._reset_breaker()
        return SupervisorResult("stopped", previous_pid=previous_pid)

    def _discover_existing(self):
        expected = normalize_executable_path(self.settings.path)
        candidates = []
        for process in self.process_api.find_by_exact_path(self.settings.path):
            try:
                exact_path = normalize_executable_path(process.path) == expected
            except (TypeError, ValueError):
                exact_path = False
            if (
                exact_path
                and process.running
                and self.process_api.is_running(process.pid, self.settings.path)
            ):
                candidates.append(process)
        candidates.sort(key=lambda item: item.pid)
        if len(candidates) > 1 and self.settings.single_instance:
            self._conflict_pids = tuple(item.pid for item in candidates)
            return SupervisorResult(
                "conflict",
                conflict_pids=self._conflict_pids,
                failure_count=len(self._failure_times),
            )
        if candidates:
            self._pid = candidates[0].pid
            self._runtime_path = candidates[0].path
            self._conflict_pids = ()
            self._tracked_since = self._now()
            return SupervisorResult("adopted", pid=self._pid)
        self._conflict_pids = ()
        return None

    def _discover_existing_by_name(self):
        finder = getattr(self.process_api, "find_existing_by_name", None)
        if finder is None:
            return None
        try:
            discovered = tuple(finder(self.settings.path))
        except (OSError, RuntimeError):
            return None
        candidates = []
        for process in discovered:
            if process.running and self.process_api.is_running(
                process.pid,
                process.path,
            ):
                candidates.append(process)
        candidates.sort(key=lambda item: item.pid)
        if len(candidates) > 1 and self.settings.single_instance:
            self._conflict_pids = tuple(item.pid for item in candidates)
            return SupervisorResult(
                "conflict",
                conflict_pids=self._conflict_pids,
                failure_count=len(self._failure_times),
            )
        if not candidates:
            return None
        self._pid = candidates[0].pid
        self._runtime_path = candidates[0].path
        self._conflict_pids = ()
        self._tracked_since = self._now()
        return SupervisorResult(
            "adopted",
            pid=self._pid,
            failure_count=len(self._failure_times),
        )

    def _tracked_process_is_running(self):
        return self._pid is not None and self.process_api.is_running(
            self._pid,
            self._runtime_path or self.settings.path,
        )

    def _discover_handoff(self, parent_pid):
        finder = getattr(self.process_api, "find_handoff", None)
        if finder is None:
            return None
        try:
            discovered = tuple(finder(parent_pid, self.settings.path))
        except (OSError, RuntimeError):
            return None
        candidates = []
        for process in discovered:
            if process.running and self.process_api.is_running(
                process.pid,
                process.path,
            ):
                candidates.append(process)
        candidates.sort(key=lambda item: item.pid)
        if len(candidates) > 1 and self.settings.single_instance:
            self._conflict_pids = tuple(item.pid for item in candidates)
            self._clear_handoff(parent_pid)
            self._handoff_parent_pid = None
            self._handoff_due_at = None
            return SupervisorResult(
                "conflict",
                conflict_pids=self._conflict_pids,
                failure_count=len(self._failure_times),
            )
        if not candidates:
            return None
        self._pid = candidates[0].pid
        self._runtime_path = candidates[0].path
        self._conflict_pids = ()
        self._tracked_since = self._now()
        self._clear_handoff(parent_pid)
        self._handoff_parent_pid = None
        self._handoff_due_at = None
        return SupervisorResult(
            "adopted",
            pid=self._pid,
            failure_count=len(self._failure_times),
        )

    def _poll_handoff(self):
        parent_pid = self._handoff_parent_pid
        discovered = self._discover_handoff(parent_pid)
        if discovered is not None:
            return discovered
        if self._now() < self._handoff_due_at:
            return SupervisorResult(
                "waiting_handoff",
                previous_pid=parent_pid,
                failure_count=len(self._failure_times),
            )
        self._clear_handoff(parent_pid)
        self._handoff_parent_pid = None
        self._handoff_due_at = None
        self._record_failure()
        if self._breaker_open:
            return SupervisorResult(
                "crash_loop",
                previous_pid=parent_pid,
                failure_count=len(self._failure_times),
            )
        self._restart_due_at = self._now() + self._restart_delay_seconds()
        return SupervisorResult(
            "waiting_restart",
            previous_pid=parent_pid,
            failure_count=len(self._failure_times),
        )

    def _launch(self, success_status, previous_pid=None):
        try:
            process = self.process_api.start(self.settings)
            if normalize_executable_path(process.path) != normalize_executable_path(
                self.settings.path
            ):
                raise ValueError("Started process path mismatch")
            if not self.process_api.is_running(process.pid, self.settings.path):
                discovery = self._discover_existing()
                if discovery is not None:
                    self._restart_due_at = None
                    return discovery
                discovery = self._discover_existing_by_name()
                if discovery is not None:
                    self._restart_due_at = None
                    return discovery
                handoff = self._discover_handoff(process.pid)
                if handoff is not None:
                    self._restart_due_at = None
                    return handoff
                self._pid = None
                self._runtime_path = None
                self._tracked_since = None
                self._restart_due_at = None
                self._handoff_parent_pid = process.pid
                self._handoff_due_at = self._now() + HANDOFF_GRACE_SECONDS
                return SupervisorResult(
                    "waiting_handoff",
                    previous_pid=process.pid,
                    failure_count=len(self._failure_times),
                )
        except Exception as error:
            self._pid = None
            self._tracked_since = None
            self._record_failure()
            if self._breaker_open:
                self._restart_due_at = None
                return SupervisorResult(
                    "crash_loop",
                    error_code=error.__class__.__name__,
                    previous_pid=previous_pid,
                    failure_count=len(self._failure_times),
                )
            self._restart_due_at = self._now() + self._restart_delay_seconds()
            return SupervisorResult(
                "start_failed",
                error_code=error.__class__.__name__,
                previous_pid=previous_pid,
                failure_count=len(self._failure_times),
            )
        self._pid = process.pid
        self._runtime_path = process.path
        self._restart_due_at = None
        self._conflict_pids = ()
        self._tracked_since = self._now()
        return SupervisorResult(
            success_status,
            pid=self._pid,
            previous_pid=previous_pid,
            failure_count=len(self._failure_times),
        )

    def _record_failure(self):
        now = self._now()
        oldest = now - self.settings.restart_window_seconds
        self._failure_times = [
            value for value in self._failure_times if value >= oldest
        ]
        self._failure_times.append(now)
        if len(self._failure_times) >= self.settings.max_restart_attempts:
            self._breaker_open = True

    def _clear_failures_after_stable_run(self):
        if self._tracked_since is None:
            return
        if self._now() - self._tracked_since >= HANDOFF_GRACE_SECONDS:
            self._clear_handoff(self._pid)
        if self._now() - self._tracked_since >= self.settings.restart_window_seconds:
            self._failure_times = []
            self._breaker_open = False

    def _clear_handoff(self, parent_pid):
        if parent_pid is None:
            return
        cleaner = getattr(self.process_api, "clear_handoff", None)
        if cleaner is None:
            return
        try:
            cleaner(parent_pid)
        except (OSError, RuntimeError):
            return

    def _reset_breaker(self):
        self._failure_times = []
        self._breaker_open = False

    def _now(self):
        return float(self.clock.monotonic())

    def _restart_delay_seconds(self):
        return self.settings.restart_delay_ms / 1000.0
