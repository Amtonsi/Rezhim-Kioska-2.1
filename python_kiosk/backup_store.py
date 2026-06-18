# -*- coding: utf-8 -*-

import json
import os
import time


class BackupStore(object):
    def __init__(self, state_dir):
        self.state_dir = state_dir

    def create_backup(self, config, plan, allow_user_fallback=True):
        state_dirs = [self.state_dir]
        if allow_user_fallback:
            for fallback_dir in user_state_dirs():
                if _normalized_path(fallback_dir) not in [
                    _normalized_path(path) for path in state_dirs
                ]:
                    state_dirs.append(fallback_dir)

        last_error = None
        for state_dir in state_dirs:
            try:
                return self._write_backup(state_dir, config, plan)
            except PermissionError as error:
                last_error = error
                continue
        if last_error is not None:
            raise last_error
        return self._write_backup(self.state_dir, config, plan)

    def _write_backup(self, state_dir, config, plan):
        directory = os.path.join(state_dir, "backups")
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = "backup-{0}.json".format(time.strftime("%Y%m%d-%H%M%S"))
        path = os.path.join(directory, filename)
        data = {
            "schemaVersion": 1,
            "buildFamily": "modern",
            "operatorUser": config.operator_user,
            "originalShell": "explorer.exe",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "operator_user": config.operator_user,
            "app_path": config.app_path,
            "restore_shell": "explorer.exe",
            "plan": plan.to_dict(),
        }
        with open(path, "w", encoding="utf-8") as backup_file:
            json.dump(data, backup_file, indent=2, ensure_ascii=False, sort_keys=True)
            backup_file.write("\n")
        return path


def default_state_dir():
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~")
    return os.path.join(base, "PythonKiosk")


def user_state_dirs():
    bases = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("TEMP"),
        os.path.expanduser("~"),
    ]
    return [os.path.join(base, "PythonKiosk") for base in bases if base]


def _normalized_path(path):
    return os.path.normcase(os.path.abspath(path or ""))
