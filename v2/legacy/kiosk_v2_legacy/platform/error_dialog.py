# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes


try:
    text_type = unicode
except NameError:
    text_type = str


MB_OK = 0x00000000
MB_ICONERROR = 0x00000010


class WindowsErrorDialog(object):
    def __init__(self, user32=None):
        self.user32 = user32 or ctypes.windll.user32

    def show(self, message):
        self.user32.MessageBoxW(
            None,
            text_type(message),
            "Режим киоска",
            MB_OK | MB_ICONERROR,
        )
