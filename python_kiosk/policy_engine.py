# -*- coding: utf-8 -*-

import json
import os

from python_kiosk.platform_detect import select_policy_profile


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILES_PATH = os.path.join(PROJECT_ROOT, "config", "policy-profiles.json")


class PolicyOperation(object):
    def __init__(self, name, description, reversible=True, data=None):
        self.name = name
        self.description = description
        self.reversible = bool(reversible)
        self.data = data or {}

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "reversible": self.reversible,
            "data": self.data,
        }


class PolicyExecutionPlan(object):
    def __init__(self, title, profile, operations, dry_run=True):
        self.title = title
        self.profile = profile
        self.operations = list(operations)
        self.dry_run = bool(dry_run)

    def to_text(self):
        mode = "dry-run" if self.dry_run else "apply"
        lines = [
            self.title,
            "Профиль: {0}".format(self.profile),
            "Режим: {0}".format(mode),
        ]
        for operation in self.operations:
            lines.append("- {0}: {1}".format(operation.name, operation.description))
        return "\n".join(lines)

    def to_dict(self):
        return {
            "title": self.title,
            "profile": self.profile,
            "dry_run": self.dry_run,
            "operations": [operation.to_dict() for operation in self.operations],
        }


class PolicyEngine(object):
    @staticmethod
    def load_profiles(path=None):
        path = path or DEFAULT_PROFILES_PATH
        with open(path, "r", encoding="utf-8") as profiles_file:
            return json.load(profiles_file)

    def build_install_plan(self, config, windows_info, dry_run=True, launcher_command=None):
        config.validate()
        profile = (
            config.policy_profile
            if config.policy_profile != "auto"
            else select_policy_profile(windows_info)
        )
        operations = [
            PolicyOperation(
                "create_backup",
                "Сохранить текущую shell-оболочку оператора и значения политик перед изменениями.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "ensure_operator_user",
                "Создать или проверить отдельную локальную учетную запись оператора без прав администратора.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "set_operator_shell",
                "Назначить KioskLauncher shell-оболочкой только для учетной записи оператора.",
                data={
                    "operator_user": config.operator_user,
                    "shell_command": launcher_command or "KioskLauncher.exe launch",
                },
            ),
            PolicyOperation(
                "apply_hkcu_operator_policies",
                "Ограничить Run, Task Manager, командные оболочки, Registry Editor, Control Panel и обходные пути Explorer для оператора.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "allow_fixed_executable",
                "Разрешить только настроенный фиксированный путь Win32-приложения в выбранном профиле.",
                data={"app_path": config.app_path},
            ),
            PolicyOperation(
                "preserve_services_drivers_startup",
                "Не останавливать службы, драйверы, системные процессы и существующие записи автозагрузки.",
                reversible=True,
            ),
        ]
        operations.extend(self._profile_operations(profile, config))
        return PolicyExecutionPlan(
            "План установки PythonKiosk",
            profile,
            operations,
            dry_run=dry_run,
        )

    def build_restore_plan(self, config, dry_run=True):
        config.validate()
        operations = [
            PolicyOperation(
                "load_backup",
                "Загрузить backup-метаданные, созданные перед применением политик киоска.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "restore_operator_shell",
                "Вернуть explorer.exe как shell-оболочку учетной записи оператора.",
                data={"shell": "explorer.exe", "operator_user": config.operator_user},
            ),
            PolicyOperation(
                "restore_operator_policies",
                "Откатить только значения политик, созданные PythonKiosk.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "preserve_services_drivers_startup",
                "Оставить службы, драйверы, системные процессы и автозагрузку без изменений.",
            ),
        ]
        return PolicyExecutionPlan(
            "План восстановления PythonKiosk",
            "restore",
            operations,
            dry_run=dry_run,
        )

    def _profile_operations(self, profile, config):
        if profile == "xp_legacy":
            return [
                PolicyOperation(
                    "apply_xp_legacy_registry_policy",
                    "Использовать shell replacement и политики реестра, доступные на Windows XP.",
                )
            ]
        if profile == "win7_srp":
            return [
                PolicyOperation(
                    "prepare_srp_rules",
                    "Подготовить Software Restriction Policies для launcher и фиксированного пути приложения.",
                    data={"app_path": config.app_path},
                )
            ]
        if profile == "win10_applocker":
            return [
                PolicyOperation(
                    "prepare_applocker_rules",
                    "Подготовить правила AppLocker для .exe там, где редакция Windows поддерживает enforcement.",
                    data={"app_path": config.app_path},
                )
            ]
        if profile == "win10_shelllauncher":
            return [
                PolicyOperation(
                    "prepare_shelllauncher_config",
                    "Подготовить конфигурацию Shell Launcher там, где редакция Windows это поддерживает.",
                )
            ]
        return [
            PolicyOperation(
                "apply_home_fallback_policy",
                "Использовать shell replacement и пользовательские политики реестра с пониженной гарантией на Home-редакциях.",
            )
        ]
