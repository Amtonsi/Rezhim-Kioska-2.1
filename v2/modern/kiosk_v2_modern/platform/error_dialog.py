# -*- coding: utf-8 -*-
import ctypes


MB_OK = 0x00000000
MB_ICONERROR = 0x00000010


class WindowsErrorDialog(object):
    def __init__(self, user32=None):
        self.user32 = user32 or ctypes.windll.user32

    def show(self, message):
        self.user32.MessageBoxW(
            None,
            str(message),
            "Режим киоска",
            MB_OK | MB_ICONERROR,
        )
