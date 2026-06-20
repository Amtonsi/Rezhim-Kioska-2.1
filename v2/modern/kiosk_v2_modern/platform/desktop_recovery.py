# -*- coding: utf-8 -*-
import ntpath
import os
import subprocess


class WindowsDesktopRecovery(object):
    def __init__(
        self,
        process_api,
        surface_api,
        process_launcher=None,
        explorer_path=None,
    ):
        self.process_api = process_api
        self.surface_api = surface_api
        self.process_launcher = process_launcher or self._launch
        windows_directory = os.environ.get("WINDIR", r"C:\Windows")
        self.explorer_path = explorer_path or os.path.join(
            windows_directory,
            "explorer.exe",
        )

    def restore_shell_surfaces(self):
        current_session = int(self.process_api.current_session_id())
        restored = []
        for surface in self.surface_api.list_shell_surfaces():
            if surface.session_id != current_session:
                continue
            try:
                shown = self.surface_api.show_window(surface.hwnd)
            except (OSError, RuntimeError):
                shown = False
            if shown:
                restored.append(surface.hwnd)
        return tuple(restored)

    def explorer_running(self):
        current_session = int(self.process_api.current_session_id())
        for process in self.process_api.list_processes():
            if process.session_id != current_session:
                continue
            basename = ntpath.basename(ntpath.normpath(process.image_path)).lower()
            if basename == "explorer.exe":
                return True
        return False

    def start_explorer(self):
        if self.explorer_running():
            return False
        self.process_launcher([self.explorer_path])
        return True

    def _launch(self, command):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            command,
            shell=False,
            creationflags=creationflags,
        )
