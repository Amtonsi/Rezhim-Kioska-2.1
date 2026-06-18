# -*- coding: utf-8 -*-

import os
import re
import subprocess


FORBIDDEN_OPERATION_NAMES = set(
    [
        "stop_services",
        "disable_services",
        "clear_startup",
        "kill_processes",
        "terminate_processes",
        "disable_drivers",
    ]
)

ADMIN_RIGHTS_REQUIRED_MESSAGE = (
    "Отказано в доступе. Для выполнения действия требуются права администратора Windows."
)


OPERATOR_POLICY_VALUES = [
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "DisableTaskMgr",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "DisableRegistryTools",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Policies\Microsoft\Windows\System",
        "DisableCMD",
        "REG_DWORD",
        "2",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoRun",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoControlPanel",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoViewContextMenu",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoTrayContextMenu",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoSetTaskbar",
        "REG_DWORD",
        "1",
    ),
]


class CompletedCommand(object):
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = int(returncode)


class WindowsSystemBackend(object):
    def __init__(self, command_runner=None, logger=None):
        self.command_runner = command_runner or self._default_command_runner
        self.logger = logger

    def is_admin(self):
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def apply_operation(self, operation):
        if operation.name in FORBIDDEN_OPERATION_NAMES:
            raise ValueError(
                "Операция запрещена границами безопасности киоска: {0}".format(
                    operation.name
                )
            )

        handler = getattr(self, "_apply_{0}".format(operation.name), None)
        if handler is None:
            return operation.name
        return handler(operation)

    def _default_command_runner(self, command, **kwargs):
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creationflags,
        )
        stdout_bytes, stderr_bytes = process.communicate()
        return CompletedCommand(
            stdout=self._decode_process_bytes(stdout_bytes),
            stderr=self._decode_process_bytes(stderr_bytes),
            returncode=process.returncode,
        )

    def _decode_process_bytes(self, value):
        if isinstance(value, str):
            return value
        for encoding in ("mbcs", "utf-8", "cp866", "cp1251"):
            try:
                return value.decode(encoding, "ignore")
            except (LookupError, UnicodeError, AttributeError):
                pass
        try:
            return value.decode("utf-8", "ignore")
        except AttributeError:
            return ""

    def _run(self, command, check=False):
        result = self.command_runner(command)
        if check and result.returncode != 0:
            detail = result.stderr or result.stdout or "код {0}".format(result.returncode)
            raise RuntimeError(
                "Команда Windows завершилась ошибкой: {0}; {1}".format(
                    " ".join(command),
                    detail.strip(),
                )
            )
        return result

    def _apply_create_backup(self, operation):
        return operation.name

    def _apply_load_backup(self, operation):
        return operation.name

    def _apply_preserve_services_drivers_startup(self, operation):
        return operation.name

    def _apply_allow_fixed_executable(self, operation):
        app_path = operation.data.get("app_path")
        if app_path and not os.path.exists(app_path):
            raise RuntimeError(
                "Разрешенное приложение не найдено: {0}".format(app_path)
            )
        return operation.name

    def _apply_prepare_srp_rules(self, operation):
        return self._apply_allow_fixed_executable(operation)

    def _apply_prepare_applocker_rules(self, operation):
        return self._apply_allow_fixed_executable(operation)

    def _apply_prepare_shelllauncher_config(self, operation):
        return operation.name

    def _apply_apply_home_fallback_policy(self, operation):
        return self._apply_apply_hkcu_operator_policies(operation)

    def _apply_apply_xp_legacy_registry_policy(self, operation):
        return self._apply_apply_hkcu_operator_policies(operation)

    def _apply_ensure_operator_user(self, operation):
        operator_user = self._required_operator(operation)
        result = self._run(["net", "user", operator_user])
        if result.returncode != 0:
            raise RuntimeError(
                "Операторская учетная запись не найдена: {0}. Создайте ее заранее отдельной командой или скриптом.".format(
                    operator_user
                )
            )
        self._ensure_operator_is_not_local_admin(operator_user)
        return operation.name

    def _ensure_operator_is_not_local_admin(self, operator_user):
        group_name = self._administrator_group_name()
        if not group_name:
            return
        result = self._run(["net", "localgroup", group_name])
        if result.returncode != 0:
            return
        operator_lower = operator_user.lower()
        members = [line.strip().lower() for line in result.stdout.splitlines()]
        if operator_lower in members:
            raise RuntimeError(
                "Операторская учетная запись не должна входить в локальную группу Administrators: {0}".format(
                    operator_user
                )
            )

    def _administrator_group_name(self):
        result = self._run(
            ["wmic", "group", "where", "sid='S-1-5-32-544'", "get", "name", "/value"]
        )
        if result.returncode != 0:
            return "Administrators"
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("name="):
                return line.split("=", 1)[1].strip() or "Administrators"
        return "Administrators"

    def _apply_set_operator_shell(self, operation):
        operator_user = self._required_operator(operation)
        shell_command = operation.data.get("shell_command") or operation.data.get("shell")
        if not shell_command:
            raise RuntimeError("Не задана команда shell для KioskLauncher.")

        def apply_to_hive(hive_root):
            self._reg_add(
                hive_root,
                r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
                "Shell",
                "REG_SZ",
                shell_command,
            )

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_restore_operator_shell(self, operation):
        operator_user = self._required_operator(operation)
        shell = operation.data.get("shell") or "explorer.exe"

        def apply_to_hive(hive_root):
            self._reg_add(
                hive_root,
                r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
                "Shell",
                "REG_SZ",
                shell,
            )

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_apply_hkcu_operator_policies(self, operation):
        operator_user = self._required_operator(operation)

        def apply_to_hive(hive_root):
            for key_path, value_name, value_type, value_data in OPERATOR_POLICY_VALUES:
                self._reg_add(hive_root, key_path, value_name, value_type, value_data)

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_restore_operator_policies(self, operation):
        operator_user = self._required_operator(operation)

        def apply_to_hive(hive_root):
            for key_path, value_name, _value_type, _value_data in OPERATOR_POLICY_VALUES:
                self._reg_delete_value(hive_root, key_path, value_name)

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _required_operator(self, operation):
        operator_user = operation.data.get("operator_user")
        if not operator_user:
            raise RuntimeError("Не указана операторская учетная запись.")
        return operator_user

    def _with_operator_hive(self, operator_user, callback):
        sid = self._operator_sid(operator_user)
        mounted_hive = r"HKU\{0}".format(sid)
        if self._run(["reg", "query", mounted_hive]).returncode == 0:
            callback(mounted_hive)
            return

        profile_path = self._profile_path_for_sid(sid)
        ntuser_path = os.path.join(os.path.expandvars(profile_path), "NTUSER.DAT")
        temp_hive = r"HKU\PythonKiosk_{0}".format(re.sub(r"[^A-Za-z0-9_]", "_", sid))
        self._run(["reg", "load", temp_hive, ntuser_path], check=True)
        try:
            callback(temp_hive)
        finally:
            self._run(["reg", "unload", temp_hive])

    def _operator_sid(self, operator_user):
        escaped_user = operator_user.replace("'", "''")
        result = self._run(
            [
                "wmic",
                "useraccount",
                "where",
                "name='{0}' and localaccount=true".format(escaped_user),
                "get",
                "sid",
                "/value",
            ],
            check=True,
        )
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("sid="):
                sid = line.split("=", 1)[1].strip()
                if sid:
                    return sid
        raise RuntimeError(
            "Не удалось определить SID операторской учетной записи: {0}".format(
                operator_user
            )
        )

    def _profile_path_for_sid(self, sid):
        result = self._run(
            [
                "reg",
                "query",
                r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\{0}".format(
                    sid
                ),
                "/v",
                "ProfileImagePath",
            ],
            check=True,
        )
        for line in result.stdout.splitlines():
            if "ProfileImagePath" in line:
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 3:
                    return parts[-1].strip()
        raise RuntimeError("Не найден профиль Windows для SID: {0}".format(sid))

    def _reg_add(self, hive_root, key_path, value_name, value_type, value_data):
        self._run(
            [
                "reg",
                "add",
                r"{0}\{1}".format(hive_root, key_path),
                "/v",
                value_name,
                "/t",
                value_type,
                "/d",
                str(value_data),
                "/f",
            ],
            check=True,
        )

    def _reg_delete_value(self, hive_root, key_path, value_name):
        self._run(
            [
                "reg",
                "delete",
                r"{0}\{1}".format(hive_root, key_path),
                "/v",
                value_name,
                "/f",
            ],
            check=False,
        )
