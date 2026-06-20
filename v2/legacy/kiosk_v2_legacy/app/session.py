# -*- coding: utf-8 -*-
from __future__ import unicode_literals


AUTH_MESSAGES = {
    "bad_credentials": "Отказано в доступе. Неверное имя пользователя или пароль.",
    "not_administrator": (
        "Отказано в доступе. Указанная учетная запись не является "
        "администратором Windows."
    ),
    "invalid_local_username": (
        "Отказано в доступе. Укажите имя локальной учетной записи без домена."
    ),
    "disabled_account": "Отказано в доступе. Указанная учетная запись отключена.",
}


class LauncherSession(object):
    def __init__(
        self,
        root,
        controller,
        application,
        desktop,
        keyboard,
        view,
        auth,
        recovery,
        clock,
        admin_timeout_seconds,
        tick_interval_ms=250,
        audit=None,
        change_application=None,
    ):
        self.root = root
        self.controller = controller
        self.application = application
        self.desktop = desktop
        self.keyboard = keyboard
        self.view = view
        self.auth = auth
        self.recovery = recovery
        self.clock = clock
        self.admin_timeout_seconds = int(admin_timeout_seconds)
        self.tick_interval_ms = max(50, int(tick_interval_ms))
        self.audit = audit
        self.change_application = change_application
        self.admin_expires_at = None
        self.running = False
        self.isolation_degraded = False

    def start(self):
        if self.running:
            return
        self.controller.handle("boot_completed")
        self.running = True
        self._schedule_tick()

    def close(self):
        if not self.running:
            return
        self.running = False
        try:
            self.keyboard.stop()
        finally:
            self.desktop.stop()

    def handle_action(self, action):
        state = self.controller.state
        if action == "unlock" and state == "OPERATOR":
            self.controller.handle("unlock_requested")
            return
        if action == "restoreApplication" and state in ("OPERATOR", "ADMIN_DIALOG"):
            self.application.restore_application(
                admin_dialog_open=state == "ADMIN_DIALOG",
                admin_session_active=False,
            )
            self.view.refresh()
            return
        if state != "ADMIN_SESSION":
            return
        if action == "unlockDesktop":
            self.recovery.restore_shell_surfaces()
            self.recovery.start_explorer()
        elif action == "toggleSupervision":
            if self.application.enabled:
                self.application.stop_supervision()
            else:
                self.application.resume_supervision()
        elif action == "returnToKiosk":
            self.admin_expires_at = None
            self.controller.handle("return_to_kiosk")
        elif action == "changeApplication" and self.change_application is not None:
            self.change_application()
        elif action == "restore":
            self.application.stop_supervision()
            self.controller.handle("restore_requested")
            self.controller.handle("restore_completed")
        self.view.refresh()

    def submit_credentials(self, username, password):
        result = self.auth.authenticate(username, password)
        self._audit("admin_authentication", result.to_log_data())
        if result.success:
            self.admin_expires_at = self._now() + self.admin_timeout_seconds
            self.controller.handle("auth_succeeded")
            return True
        self.view.set_auth_error(self._auth_message(result))
        self.controller.handle("auth_failed")
        return False

    def cancel_authentication(self):
        if self.controller.state == "ADMIN_DIALOG":
            self.controller.handle("auth_cancelled")

    def tick(self):
        state = self.controller.state
        if (
            state == "ADMIN_SESSION"
            and self.admin_expires_at is not None
            and self._now() >= self.admin_expires_at
        ):
            self.admin_expires_at = None
            self.controller.handle("return_to_kiosk")
            state = self.controller.state
        if state in ("OPERATOR", "ADMIN_DIALOG"):
            isolation = self.desktop.tick()
            failed = getattr(isolation, "failed_pids", ()) if isolation is not None else ()
            self.isolation_degraded = bool(failed)
        self.application.tick(
            admin_dialog_open=state == "ADMIN_DIALOG",
            admin_session_active=state == "ADMIN_SESSION",
        )
        self.view.refresh()
        if self.running:
            self._schedule_tick()

    def model(self):
        result = getattr(self.application, "latest_result", None)
        window_status = getattr(result, "window_status", "no_window")
        return {
            "application_path": getattr(self.application, "application_path", ""),
            "app_status": "minimized" if window_status == "minimized" else "running",
            "supervision_enabled": bool(self.application.enabled),
            "isolation_degraded": self.isolation_degraded,
        }

    def _schedule_tick(self):
        self.root.after(self.tick_interval_ms, self.tick)

    def _auth_message(self, result):
        if result.code == "locked_out":
            return "Слишком много попыток. Повторите через {0} сек.".format(
                result.retry_after_seconds
            )
        if result.code in AUTH_MESSAGES:
            return AUTH_MESSAGES[result.code]
        return "Отказано в доступе. Ошибка Windows/API."

    def _audit(self, event_name, fields):
        if self.audit is None:
            return
        try:
            self.audit.emit(event_name, level="Info", **dict(fields or {}))
        except Exception:
            return

    def _now(self):
        return float(self.clock.monotonic())


class ObservedApplication(object):
    def __init__(self, runtime, application_path):
        self.runtime = runtime
        self.application_path = application_path
        self.latest_result = None

    @property
    def enabled(self):
        return bool(self.runtime.supervisor.enabled)

    def start(self):
        self.latest_result = self.runtime.start()
        return self.latest_result

    def tick(self, **context):
        self.latest_result = self.runtime.tick(**context)
        return self.latest_result

    def restore_application(self, **context):
        self.latest_result = self.runtime.restore_application(**context)
        return self.latest_result

    def stop_supervision(self):
        self.latest_result = self.runtime.stop_supervision()
        return self.latest_result

    def resume_supervision(self):
        self.latest_result = self.runtime.resume_supervision()
        return self.latest_result
