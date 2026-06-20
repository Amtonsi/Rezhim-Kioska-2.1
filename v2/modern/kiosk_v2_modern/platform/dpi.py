# -*- coding: utf-8 -*-
import ctypes


PROCESS_PER_MONITOR_DPI_AWARE = 2


class WindowsDpiAwareness(object):
    def __init__(self, api=None):
        self.api = api or NativeDpiApi()

    def enable(self):
        if self.api.enable_per_monitor():
            return "per_monitor"
        if self.api.enable_system():
            return "system"
        return "unavailable"


class NativeDpiApi(object):
    def __init__(self, user32=None, shcore=None):
        self.user32 = user32 or ctypes.windll.user32
        if shcore is None:
            try:
                shcore = ctypes.windll.shcore
            except (AttributeError, OSError):
                shcore = None
        self.shcore = shcore
        self._configure_signatures()

    def _configure_signatures(self):
        if self.shcore is not None and hasattr(
            self.shcore,
            "SetProcessDpiAwareness",
        ):
            self.shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
            self.shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        if hasattr(self.user32, "SetProcessDPIAware"):
            self.user32.SetProcessDPIAware.argtypes = []
            self.user32.SetProcessDPIAware.restype = ctypes.c_int

    def enable_per_monitor(self):
        if self.shcore is None or not hasattr(
            self.shcore,
            "SetProcessDpiAwareness",
        ):
            return False
        try:
            return int(
                self.shcore.SetProcessDpiAwareness(
                    PROCESS_PER_MONITOR_DPI_AWARE
                )
            ) == 0
        except (AttributeError, OSError):
            return False

    def enable_system(self):
        if not hasattr(self.user32, "SetProcessDPIAware"):
            return False
        try:
            return bool(self.user32.SetProcessDPIAware())
        except (AttributeError, OSError):
            return False
