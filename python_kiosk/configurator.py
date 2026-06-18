# -*- coding: utf-8 -*-

from python_kiosk.backup_store import BackupStore, default_state_dir
from python_kiosk.logging_service import KioskLogger
from python_kiosk.platform_detect import detect_windows_info
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class ConfigurationResult(object):
    def __init__(self, plan, backup_path, applied):
        self.plan = plan
        self.backup_path = backup_path
        self.applied = bool(applied)


class Configurator(object):
    def __init__(
        self,
        backend=None,
        state_dir=None,
        logger=None,
        policy_engine=None,
        windows_info=None,
        launcher_command=None,
    ):
        self.backend = backend or WindowsSystemBackend()
        self.state_dir = state_dir or default_state_dir()
        self.logger = logger or KioskLogger()
        self.policy_engine = policy_engine or PolicyEngine()
        self.windows_info = windows_info
        self.launcher_command = launcher_command

    def install(self, config, apply=False):
        config.validate()
        if apply and not self.backend.is_admin():
            self.logger.error("install.denied", reason="admin rights required")
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

        windows_info = self.windows_info or detect_windows_info()
        plan = self.policy_engine.build_install_plan(
            config,
            windows_info,
            dry_run=not apply,
            launcher_command=self.launcher_command,
        )
        backup_path = BackupStore(self.state_dir).create_backup(
            config,
            plan,
            allow_user_fallback=not apply,
        )
        self.logger.info(
            "install.plan",
            operator=config.operator_user,
            profile=plan.profile,
            dry_run=not apply,
            backup_path=backup_path,
        )

        if apply:
            try:
                for operation in plan.operations:
                    self.backend.apply_operation(operation)
                    self.logger.info("install.operation", operation=operation.name)
            except Exception as error:
                self.logger.error(
                    "install.failed",
                    operation=getattr(operation, "name", "unknown"),
                    error=str(error),
                )
                self._attempt_safe_rollback(config)
                raise

        return ConfigurationResult(plan, backup_path, applied=apply)

    def _attempt_safe_rollback(self, config):
        rollback_plan = self.policy_engine.build_restore_plan(config, dry_run=False)
        for operation in rollback_plan.operations:
            self.backend.apply_operation(operation)
            self.logger.warning("install.rollback_operation", operation=operation.name)
