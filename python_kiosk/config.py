# -*- coding: utf-8 -*-

import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "kiosk.json")
DEFAULT_ALLOWED_APP_PATH = r"C:\Windows\System32\notepad.exe"
DEFAULT_OPERATOR_USER = "KioskOperator"
DEFAULT_POLICY_PROFILE = "auto"
DEFAULT_RESTART_DELAY_SECONDS = 2
DEFAULT_PASSWORD_ALGORITHM = "pbkdf2_hmac_sha256"
DEFAULT_PASSWORD_ITERATIONS = 200000
DEFAULT_LOG_DIRECTORY = r"C:\ProgramData\Kiosk\Logs"


class AllowedApplicationConfig(object):
    def __init__(
        self,
        path=DEFAULT_ALLOWED_APP_PATH,
        arguments="",
        working_directory=r"C:\Windows\System32",
        restart_on_exit=True,
        bring_to_front=True,
        bring_existing_to_front=True,
        single_instance=True,
        restore_if_minimized=False,
        start_maximized=False,
        restart_delay_ms=2000,
    ):
        self.path = path
        self.arguments = arguments or ""
        self.working_directory = working_directory or ""
        self.restart_on_exit = bool(restart_on_exit)
        self.bring_to_front = bool(bring_to_front)
        self.bring_existing_to_front = bool(bring_existing_to_front)
        self.single_instance = bool(single_instance)
        self.restore_if_minimized = bool(restore_if_minimized)
        self.start_maximized = bool(start_maximized)
        self.restart_delay_ms = int(restart_delay_ms)

    def to_dict(self):
        return {
            "path": self.path,
            "arguments": self.arguments,
            "workingDirectory": self.working_directory,
            "restartOnExit": self.restart_on_exit,
            "bringToFront": self.bring_to_front,
            "bringExistingToFront": self.bring_existing_to_front,
            "singleInstance": self.single_instance,
            "restoreIfMinimized": self.restore_if_minimized,
            "startMaximized": self.start_maximized,
            "restartDelayMs": self.restart_delay_ms,
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            path=data.get("path", DEFAULT_ALLOWED_APP_PATH),
            arguments=data.get("arguments", ""),
            working_directory=data.get("workingDirectory", data.get("working_directory", "")),
            restart_on_exit=data.get("restartOnExit", data.get("restart_on_exit", True)),
            bring_to_front=data.get("bringToFront", data.get("bring_to_front", True)),
            bring_existing_to_front=data.get(
                "bringExistingToFront",
                data.get("bring_existing_to_front", True),
            ),
            single_instance=data.get("singleInstance", data.get("single_instance", True)),
            restore_if_minimized=data.get(
                "restoreIfMinimized",
                data.get("restore_if_minimized", False),
            ),
            start_maximized=data.get("startMaximized", data.get("start_maximized", False)),
            restart_delay_ms=data.get("restartDelayMs", data.get("restart_delay_ms", 2000)),
        )

    def command(self):
        command = [self.path]
        if self.arguments:
            command.extend(_split_windows_arguments(self.arguments))
        return command


def _split_windows_arguments(arguments):
    arguments = arguments or ""
    if not arguments.strip():
        return []
    if os.name == "nt":
        try:
            return _command_line_to_argv(arguments)
        except Exception:
            pass
    try:
        import shlex

        return shlex.split(arguments, posix=True)
    except ValueError:
        return [arguments]


def _command_line_to_argv(arguments):
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL

    count = ctypes.c_int(0)
    argv = shell32.CommandLineToArgvW(arguments, ctypes.byref(count))
    if not argv:
        raise ValueError("CommandLineToArgvW failed")
    try:
        return [argv[index] for index in range(count.value)]
    finally:
        kernel32.LocalFree(argv)


class KioskConfig(object):
    def __init__(
        self,
        app_path=None,
        operator_user=DEFAULT_OPERATOR_USER,
        admin_password_hash="",
        admin_password_salt="",
        admin_password_algorithm=DEFAULT_PASSWORD_ALGORITHM,
        admin_password_iterations=DEFAULT_PASSWORD_ITERATIONS,
        policy_profile=DEFAULT_POLICY_PROFILE,
        restart_delay_seconds=DEFAULT_RESTART_DELAY_SECONDS,
        restore_metadata=None,
        feature_flags=None,
        allowed_application=None,
        kiosk=None,
        testing=None,
        logging=None,
    ):
        self.allowed_application = allowed_application or AllowedApplicationConfig(
            path=app_path or DEFAULT_ALLOWED_APP_PATH
        )
        if app_path is not None:
            self.allowed_application.path = app_path
        self.operator_user = operator_user or DEFAULT_OPERATOR_USER
        self.admin_password_hash = admin_password_hash or ""
        self.admin_password_salt = admin_password_salt or ""
        self.admin_password_algorithm = admin_password_algorithm or DEFAULT_PASSWORD_ALGORITHM
        self.admin_password_iterations = int(
            admin_password_iterations or DEFAULT_PASSWORD_ITERATIONS
        )
        self.policy_profile = policy_profile or DEFAULT_POLICY_PROFILE
        if restart_delay_seconds is None:
            restart_delay_seconds = DEFAULT_RESTART_DELAY_SECONDS
        self.restart_delay_seconds = int(restart_delay_seconds)
        self.restore_metadata = restore_metadata or {}
        self.feature_flags = feature_flags or {}
        self.kiosk = _default_kiosk()
        self.kiosk.update(kiosk or {})
        self.testing = _default_testing()
        self.testing.update(testing or {})
        self.logging = _default_logging()
        self.logging.update(logging or {})

    @property
    def app_path(self):
        return self.allowed_application.path

    @app_path.setter
    def app_path(self, value):
        self.allowed_application.path = value

    def validate(self, require_existing_app=False):
        if not self.app_path:
            raise ValueError("app_path обязателен")
        if not self.operator_user:
            raise ValueError("operator_user обязателен")
        if int(self.restart_delay_seconds) <= 0:
            raise ValueError("restart_delay_seconds должен быть положительным")
        if int(self.kiosk.get("adminSessionTimeoutSeconds", 0)) <= 0:
            raise ValueError("adminSessionTimeoutSeconds должен быть положительным")
        if require_existing_app and not os.path.isfile(self.app_path):
            raise ValueError(
                "Разрешённое приложение не найдено: {0}".format(self.app_path)
            )

    def to_dict(self):
        data = {
            "operatorUser": self.operator_user,
            "allowedApplication": self.allowed_application.to_dict(),
            "kiosk": self.kiosk,
            "testing": self.testing,
            "logging": self.logging,
            "policyProfile": self.policy_profile,
            "restartDelaySeconds": int(self.restart_delay_seconds),
            "restoreMetadata": self.restore_metadata,
            "featureFlags": self.feature_flags,
        }
        if self.admin_password_hash or self.admin_password_salt:
            data.update(
                {
                    "admin_password_hash": self.admin_password_hash,
                    "admin_password_salt": self.admin_password_salt,
                    "admin_password_algorithm": self.admin_password_algorithm,
                    "admin_password_iterations": int(self.admin_password_iterations),
                }
            )
        return data

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        if "allowedApplication" in data:
            return cls(
                operator_user=data.get("operatorUser", data.get("operator_user", DEFAULT_OPERATOR_USER)),
                allowed_application=AllowedApplicationConfig.from_dict(
                    data.get("allowedApplication")
                ),
                kiosk=data.get("kiosk") or {},
                testing=data.get("testing") or {},
                logging=data.get("logging") or {},
                policy_profile=data.get("policyProfile", data.get("policy_profile", DEFAULT_POLICY_PROFILE)),
                restart_delay_seconds=data.get(
                    "restartDelaySeconds",
                    data.get("restart_delay_seconds", DEFAULT_RESTART_DELAY_SECONDS),
                ),
                restore_metadata=data.get("restoreMetadata", data.get("restore_metadata") or {}),
                feature_flags=data.get("featureFlags", data.get("feature_flags") or {}),
                admin_password_hash=data.get("admin_password_hash", ""),
                admin_password_salt=data.get("admin_password_salt", ""),
                admin_password_algorithm=data.get(
                    "admin_password_algorithm", DEFAULT_PASSWORD_ALGORITHM
                ),
                admin_password_iterations=data.get(
                    "admin_password_iterations", DEFAULT_PASSWORD_ITERATIONS
                ),
            )
        return cls(
            app_path=data.get("app_path", DEFAULT_ALLOWED_APP_PATH),
            operator_user=data.get("operator_user", DEFAULT_OPERATOR_USER),
            admin_password_hash=data.get("admin_password_hash", ""),
            admin_password_salt=data.get("admin_password_salt", ""),
            admin_password_algorithm=data.get(
                "admin_password_algorithm", DEFAULT_PASSWORD_ALGORITHM
            ),
            admin_password_iterations=data.get(
                "admin_password_iterations", DEFAULT_PASSWORD_ITERATIONS
            ),
            policy_profile=data.get("policy_profile", DEFAULT_POLICY_PROFILE),
            restart_delay_seconds=data.get(
                "restart_delay_seconds", DEFAULT_RESTART_DELAY_SECONDS
            ),
            restore_metadata=data.get("restore_metadata") or {},
            feature_flags=data.get("feature_flags") or {},
        )


def _default_kiosk():
    return {
        "blockDesktop": True,
        "disableStartMenu": True,
        "disableExplorer": True,
        "allowWinL": True,
        "blockWinKey": True,
        "adminSessionTimeoutSeconds": 300,
    }


def _default_testing():
    return {
        "requireBackupBeforeTest": True,
        "restoreAfterTest": True,
        "testOnlySeparateOperatorUser": True,
    }


def _default_logging():
    return {
        "logDirectory": DEFAULT_LOG_DIRECTORY,
        "level": "Info",
    }


def build_default_config():
    return KioskConfig(
        app_path=DEFAULT_ALLOWED_APP_PATH,
        operator_user=DEFAULT_OPERATOR_USER,
        allowed_application=AllowedApplicationConfig(),
        kiosk=_default_kiosk(),
        testing=_default_testing(),
        logging=_default_logging(),
    )


def ensure_default_config(path=DEFAULT_CONFIG_PATH):
    if os.path.exists(path):
        return path
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    save_config(build_default_config(), path)
    return path


def load_config(path, create_if_missing=False):
    if create_if_missing:
        ensure_default_config(path)
    with open(path, "r", encoding="utf-8-sig") as config_file:
        data = json.load(config_file)
    config = KioskConfig.from_dict(data)
    config.validate()
    return config


def save_config(config, path):
    config.validate()
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as config_file:
        json.dump(config.to_dict(), config_file, ensure_ascii=False, indent=2, sort_keys=True)
        config_file.write("\n")
