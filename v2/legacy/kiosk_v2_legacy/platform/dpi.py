# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes


class WindowsDpiAwareness(object):
    def __init__(self, api=None):
        self.api = api or NativeDpiApi()

    def enable(self):
        if self.api.enable_system():
            return "system"
        return "unavailable"


class NativeDpiApi(object):
    def __init__(self, user32=None):
        self.user32 = user32 or ctypes.windll.user32
        if hasattr(self.user32, "SetProcessDPIAware"):
            self.user32.SetProcessDPIAware.argtypes = []
            self.user32.SetProcessDPIAware.restype = ctypes.c_int

    def enable_system(self):
        if not hasattr(self.user32, "SetProcessDPIAware"):
            return False
        try:
            return bool(self.user32.SetProcessDPIAware())
        except (AttributeError, OSError):
            return False
