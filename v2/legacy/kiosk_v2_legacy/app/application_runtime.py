# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ApplicationRuntimeResult(object):
    __slots__ = (
        "process_status",
        "pid",
        "window_status",
        "error_code",
        "conflict_pids",
        "failure_count",
    )

    def __init__(
        self,
        process_status,
        pid=None,
        window_status="no_window",
        error_code=None,
        conflict_pids=(),
        failure_count=0,
    ):
        self.process_status = process_status
        self.pid = pid
        self.window_status = window_status
        self.error_code = error_code
        self.conflict_pids = tuple(conflict_pids)
        self.failure_count = int(failure_count)


class ApplicationRuntime(object):
    def __init__(self, supervisor, window_coordinator, start_maximized=False):
        self.supervisor = supervisor
        self.window_coordinator = window_coordinator
        self.start_maximized = bool(start_maximized)
        self._pending_activation_pid = None

    def start(self, admin_dialog_open=False, admin_session_active=False):
        process = self.supervisor.start()
        if process.pid is not None:
            self._pending_activation_pid = process.pid
        return self._observe(process, admin_dialog_open, admin_session_active)

    def tick(self, admin_dialog_open=False, admin_session_active=False):
        process = self.supervisor.tick()
        if process.status == "restarted" and process.pid is not None:
            self._pending_activation_pid = process.pid
        return self._observe(process, admin_dialog_open, admin_session_active)

    def restore_application(
        self, admin_dialog_open=False, admin_session_active=False
    ):
        pid = self.supervisor.pid
        if pid is None:
            return ApplicationRuntimeResult("stopped")
        window = self.window_coordinator.restore(
            pid,
            maximized=self.start_maximized,
            admin_dialog_open=admin_dialog_open,
            admin_session_active=admin_session_active,
        )
        return ApplicationRuntimeResult(
            "running", pid=pid, window_status=window.status
        )

    def stop_supervision(self):
        process = self.supervisor.stop_supervision()
        self._pending_activation_pid = None
        return self._result(process, "no_window")

    def resume_supervision(self):
        process = self.supervisor.start()
        if process.status == "started" and process.pid is not None:
            self._pending_activation_pid = process.pid
            return self._observe(process, False, False)
        self._pending_activation_pid = None
        window_status = "no_window"
        if process.pid is not None:
            window_status = self.window_coordinator.inspect(process.pid).status
        return self._result(process, window_status)

    def _observe(self, process, admin_dialog_open, admin_session_active):
        if process.pid is None:
            if process.status != "waiting_restart":
                self._pending_activation_pid = None
            return self._result(process, "no_window")
        if self._pending_activation_pid == process.pid:
            window = self.window_coordinator.activate_initial(
                process.pid,
                maximized=self.start_maximized,
                admin_dialog_open=admin_dialog_open,
                admin_session_active=admin_session_active,
            )
            if window.succeeded:
                self._pending_activation_pid = None
        else:
            window = self.window_coordinator.inspect(process.pid)
        return self._result(process, window.status)

    @staticmethod
    def _result(process, window_status):
        return ApplicationRuntimeResult(
            process.status,
            pid=process.pid,
            window_status=window_status,
            error_code=process.error_code,
            conflict_pids=process.conflict_pids,
            failure_count=process.failure_count,
        )
