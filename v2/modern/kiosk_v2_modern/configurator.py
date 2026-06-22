# -*- coding: utf-8 -*-
import io
import json
import ntpath
import os
import sys


ERROR_MESSAGES = {
    "elevation_required": "Для изменения приложения требуются повышенные права администратора Windows.",
    "exe_required": "Выберите существующий файл программы с расширением .exe.",
    "file_not_found": "Выбранный файл программы не найден.",
    "configuration_error": "Не удалось обновить конфигурацию киоска.",
}


class ConfiguratorError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super(ConfiguratorError, self).__init__(code)


def select_initial_directory(initial_path, directory_exists, fallback):
    candidate = ntpath.dirname(ntpath.normpath(initial_path or ""))
    if candidate and directory_exists(candidate):
        return candidate
    return fallback


class ApplicationConfigurator(object):
    def __init__(self, repository, picker, file_exists, is_elevated):
        self.repository = repository
        self.picker = picker
        self.file_exists = file_exists
        self.is_elevated = is_elevated

    def run(self):
        if not self.is_elevated():
            raise ConfiguratorError("elevation_required")
        config = self.repository.load(require_existing_app=False)
        current_path = config["allowedApplication"]["path"]
        selected = self.picker.choose_executable(current_path)
        if not selected:
            return False
        selected = ntpath.normpath(selected)
        if ntpath.splitext(selected)[1].lower() != ".exe":
            raise ConfiguratorError("exe_required")
        if not self.file_exists(selected):
            raise ConfiguratorError("file_not_found")
        config["allowedApplication"]["path"] = selected
        config["allowedApplication"]["workingDirectory"] = ntpath.dirname(selected)
        config["allowedApplication"]["configured"] = True
        self.repository.save(config, require_existing_app=True)
        return True


class TkExecutablePicker(object):
    def __init__(self):
        import tkinter as tk
        from tkinter import filedialog, messagebox

        self.filedialog = filedialog
        self.messagebox = messagebox
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.attributes("-topmost", True)

    def choose_executable(self, initial_path):
        return self.filedialog.askopenfilename(
            parent=self.root,
            title="Выберите разрешённое приложение",
            initialdir=select_initial_directory(
                initial_path,
                os.path.isdir,
                os.environ.get("WINDIR", r"C:\Windows"),
            ),
            filetypes=(("Программы Windows", "*.exe"), ("Все файлы", "*.*")),
        )

    def show_success(self):
        self.messagebox.showinfo(
            "Режим киоска",
            "Разрешённое приложение изменено.",
            parent=self.root,
        )

    def show_error(self, message):
        self.messagebox.showerror("Режим киоска", message, parent=self.root)

    def close(self):
        self.root.destroy()


def run_default(argv=None, executable_directory=None, resource_directory=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["configure-application"]:
        return 2
    executable_directory = executable_directory or os.path.dirname(
        os.path.abspath(sys.executable)
    )
    resource_directory = resource_directory or getattr(
        sys,
        "_MEIPASS",
        executable_directory,
    )
    from kiosk_v2_modern.app.config_repository import ConfigRepository, ConfigValidator
    from kiosk_v2_modern.platform.operator_account import WindowsOperatorAccountApi

    with io.open(
        os.path.join(resource_directory, "contracts", "kiosk-config-v2.schema.json"),
        "r",
        encoding="utf-8",
    ) as stream:
        schema = json.load(stream)
    repository = ConfigRepository(
        os.path.join(executable_directory, "config", "kiosk.v2.json"),
        ConfigValidator(schema),
    )
    picker = TkExecutablePicker()
    try:
        service = ApplicationConfigurator(
            repository,
            picker,
            file_exists=os.path.isfile,
            is_elevated=WindowsOperatorAccountApi().is_elevated,
        )
        changed = service.run()
        if changed:
            picker.show_success()
        return 0
    except ConfiguratorError as error:
        picker.show_error(ERROR_MESSAGES.get(error.code, ERROR_MESSAGES["configuration_error"]))
        return 3
    except Exception:
        picker.show_error(ERROR_MESSAGES["configuration_error"])
        return 3
    finally:
        picker.close()
