# -*- coding: utf-8 -*-

from legacy_kiosk.compat import read_json, write_json


LEGACY_BACKUP_SCHEMA_VERSION = 1
LEGACY_BUILD_FAMILY = "legacy"


class BackupError(ValueError):
    pass


class LegacyBackupStore(object):
    def save(self, path, payload):
        if not isinstance(payload, dict):
            raise BackupError(u"Резервная копия должна быть объектом JSON.")
        write_json(path, payload)

    def load(self, path):
        payload = read_json(path)
        self._validate(payload)
        return payload

    def load_for_operator(self, path, operator_sid):
        payload = self.load(path)
        if payload.get("operatorSid") != operator_sid:
            raise BackupError(
                u"Резервная копия создана для другой операторской учётной записи."
            )
        return payload

    def _validate(self, payload):
        if not isinstance(payload, dict):
            raise BackupError(u"Формат резервной копии повреждён.")
        if payload.get("schemaVersion") != LEGACY_BACKUP_SCHEMA_VERSION:
            raise BackupError(u"Версия резервной копии не поддерживается.")
        if payload.get("buildFamily") != LEGACY_BUILD_FAMILY:
            raise BackupError(u"Резервная копия относится к другой сборке программы.")
        if not payload.get("operatorSid"):
            raise BackupError(u"В резервной копии отсутствует SID оператора.")
        if not isinstance(payload.get("registry"), list):
            raise BackupError(u"В резервной копии отсутствуют значения реестра.")
        if not isinstance(payload.get("security"), list):
            raise BackupError(u"В резервной копии отсутствуют параметры доступа.")

