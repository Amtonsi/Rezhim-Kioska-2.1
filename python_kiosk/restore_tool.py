# -*- coding: utf-8 -*-

from python_kiosk.backup_store import default_state_dir
from python_kiosk.logging_service import KioskLogger
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class RestoreResult(object):
    def __init__(self, plan, applied):
        self.plan = plan
        self.applied = bool(applied)


class RestoreTool(object):
    def __init__(
        self,
        backend=None,
        state_dir=None,
        logger=None,
        policy_engine=None,
    ):
        self.backend = backend or WindowsSystemBackend()
        self.state_dir = state_dir or default_state_dir()
        self.logger = logger or KioskLogger()
        self.policy_engine = policy_engine or PolicyEngine()

    def restore(self, config, apply=False):
        config.validate()
        if apply and not self.backend.is_admin():
            self.logger.error("restore.denied", reason="admin rights required")
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

        plan = self.policy_engine.build_restore_plan(config, dry_run=not apply)
        self.logger.info(
            "restore.plan",
            operator=config.operator_user,
            dry_run=not apply,
            state_dir=self.state_dir,
        )

        if apply:
            for operation in plan.operations:
                self.backend.apply_operation(operation)
                self.logger.info("restore.operation", operation=operation.name)

        return RestoreResult(plan, applied=apply)
