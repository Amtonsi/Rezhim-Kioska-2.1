# -*- coding: utf-8 -*-

from python_kiosk.platform_detect import select_policy_profile


class PolicyStep(object):
    def __init__(self, title, detail):
        self.title = title
        self.detail = detail

    def to_text(self):
        return "- {0}: {1}".format(self.title, self.detail)


class PolicyPlan(object):
    def __init__(self, title, steps, dry_run=True):
        self.title = title
        self.steps = steps
        self.dry_run = dry_run

    def to_text(self):
        lines = [
            self.title,
            "Режим: dry-run" if self.dry_run else "Режим: применение",
        ]
        lines.extend(step.to_text() for step in self.steps)
        return "\n".join(lines)


def _common_install_steps(config, profile):
    return [
        PolicyStep(
            "Сохранить текущую оболочку",
            "Сохранить текущую оболочку и значения политик для {0}".format(
                config.operator_user
            ),
        ),
        PolicyStep(
            "Назначить оболочку {0} на KioskLauncher".format(config.operator_user),
            "KioskLauncher запускается раньше explorer.exe и контролирует {0}".format(
                config.app_path
            ),
        ),
        PolicyStep(
            "Отключить диспетчер задач",
            "Применить пользовательскую политику для учетной записи оператора, где это поддерживается",
        ),
        PolicyStep(
            "Ограничить пути выхода из оболочки",
            "Отключить Выполнить, Панель управления, редактор реестра, командные оболочки и интерфейс Explorer",
        ),
        PolicyStep(
            "Оставить Win+L доступным",
            "Не применять политики, которые блокируют экран блокировки или смену пользователя",
        ),
        PolicyStep(
            "Не отключать службы",
            "Не трогать существующие службы, драйверы и фоновые процессы",
        ),
        PolicyStep(
            "Не удалять элементы автозагрузки",
            "Не трогать существующие элементы автозагрузки",
        ),
        PolicyStep(
            "Выбранный профиль политик",
            profile,
        ),
    ]


def _profile_steps(profile):
    if profile == "xp_legacy":
        return [
            PolicyStep(
                "Legacy-ограничения XP",
                "Использовать только пользовательскую оболочку и совместимые политики реестра",
            )
        ]
    if profile == "win7_srp":
        return [
            PolicyStep(
                "Software Restriction Policies",
                "Добавить разрешающие правила для kiosk launcher и настроенного исполняемого файла",
            )
        ]
    if profile == "win10_applocker":
        return [
            PolicyStep(
                "AppLocker",
                "Подготовить разрешающие правила исполняемых файлов там, где доступно применение AppLocker",
            )
        ]
    if profile == "win10_shelllauncher":
        return [
            PolicyStep(
                "Shell Launcher",
                "Использовать Windows Shell Launcher там, где редакция Windows это поддерживает",
            )
        ]
    return [
        PolicyStep(
            "Fallback для Home",
            "Использовать пользовательскую оболочку и политики реестра с ограниченными гарантиями",
        )
    ]


def build_install_plan(config, windows_info):
    config.validate()
    profile = (
        config.policy_profile
        if config.policy_profile != "auto"
        else select_policy_profile(windows_info)
    )
    steps = _common_install_steps(config, profile)
    steps.extend(_profile_steps(profile))
    return PolicyPlan("План установки PythonKiosk", steps, dry_run=True)


def build_restore_plan(config):
    config.validate()
    steps = [
        PolicyStep(
            "Вернуть оболочку {0} на explorer.exe".format(config.operator_user),
            "Использовать сохраненные данные восстановления, если они доступны",
        ),
        PolicyStep(
            "Удалить ограничения киоска",
            "Откатить значения политик, созданные PythonKiosk для учетной записи оператора",
        ),
        PolicyStep(
            "Не удалять элементы автозагрузки",
            "Элементы автозагрузки не входят в область восстановления киоска",
        ),
        PolicyStep(
            "Не останавливать службы",
            "Службы, драйверы и фоновые процессы остаются нетронутыми",
        ),
    ]
    return PolicyPlan("План восстановления PythonKiosk", steps, dry_run=True)
