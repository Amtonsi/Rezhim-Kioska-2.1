# -*- coding: utf-8 -*-

import os

from legacy_kiosk.compat import read_json, string_types, text_type, write_json


class ConfigError(ValueError):
    pass


REQUIRED_SECTIONS = ("allowedApplication", "kiosk", "logging")
FORBIDDEN_CREDENTIAL_KEYS = frozenset(
    (
        "password",
        "windowspassword",
        "windowscredential",
        "windowscredentials",
        "credential",
        "credentials",
    )
)


def build_default_config():
    return {
        "operatorUser": "KioskOperator",
        "allowedApplication": {
            "path": r"C:\Windows\System32\notepad.exe",
            "arguments": "",
            "workingDirectory": r"C:\Windows\System32",
            "restartOnExit": True,
            "bringToFront": True,
            "singleInstance": True,
            "restoreIfMinimized": False,
            "startMaximized": False,
            "restartDelayMs": 2000,
        },
        "kiosk": {
            "blockDesktop": True,
            "disableStartMenu": True,
            "disableExplorer": True,
            "allowWinL": True,
            "blockWinKey": True,
            "adminSessionTimeoutSeconds": 300,
        },
        "logging": {
            "logDirectory": r"C:\ProgramData\Kiosk\Logs",
            "level": "Info",
        },
        "policyProfile": "xp_legacy",
        "restartDelaySeconds": 2,
        "restoreMetadata": {},
        "featureFlags": {},
        "testing": {
            "requireBackupBeforeTest": True,
            "restoreAfterTest": True,
            "testOnlySeparateOperatorUser": True,
        },
    }


def ensure_default_config(path):
    if not os.path.exists(path):
        save_config(build_default_config(), path)
    return path


def _normalized_key(key):
    if not isinstance(key, text_type):
        key = text_type(key)
    return u"".join(character for character in key.lower() if character.isalnum())


def _reject_windows_credentials(value):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if _normalized_key(key) in FORBIDDEN_CREDENTIAL_KEYS:
                raise ConfigError(
                    u"Пароли и учётные данные Windows нельзя сохранять в конфигурации."
                )
            _reject_windows_credentials(nested_value)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            _reject_windows_credentials(nested_value)


def validate_config(data, require_existing_app=False):
    if not isinstance(data, dict):
        raise ConfigError(u"Конфигурация должна быть объектом JSON.")

    _reject_windows_credentials(data)

    operator_user = data.get("operatorUser")
    if not isinstance(operator_user, string_types) or not operator_user.strip():
        raise ConfigError(u"Не задана отдельная учётная запись оператора.")

    for section_name in REQUIRED_SECTIONS:
        if not isinstance(data.get(section_name), dict):
            raise ConfigError(u"Отсутствует раздел конфигурации: %s" % section_name)

    application = data["allowedApplication"]
    application_path = application.get("path")
    if not isinstance(application_path, string_types) or not application_path.strip():
        raise ConfigError(u"Не задан путь к разрешённому приложению.")
    if not os.path.isabs(application_path):
        raise ConfigError(u"Путь к разрешённому приложению должен быть абсолютным.")
    if os.path.splitext(application_path)[1].lower() != ".exe":
        raise ConfigError(u"Разрешённое приложение должно быть EXE-файлом.")
    if require_existing_app and not os.path.isfile(application_path):
        raise ConfigError(
            u"Разрешённое приложение не найдено: %s" % application_path
        )

    timeout = data["kiosk"].get("adminSessionTimeoutSeconds", 300)
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        raise ConfigError(u"Тайм-аут административной сессии задан неверно.")
    if timeout <= 0:
        raise ConfigError(u"Тайм-аут административной сессии должен быть положительным.")

    return data


def load_config(path, require_existing_app=False):
    data = read_json(path)
    return validate_config(data, require_existing_app=require_existing_app)


def save_config(data, path):
    validate_config(data)
    write_json(path, data)
