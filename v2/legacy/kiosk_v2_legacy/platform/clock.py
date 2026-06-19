# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import threading

from ctypes import wintypes


UINT32_SPAN = 0x100000000
WRAP_THRESHOLD = 0x80000000


class TickCountClock(object):
    def __init__(self, native=None):
        self.native = native or NativeTickCountApi()
        self._last = None
        self._wrap_offset = 0
        self._lock = threading.RLock()

    def monotonic(self):
        with self._lock:
            current = int(self.native.get_tick_count()) & 0xFFFFFFFF
            if self._last is not None and current < self._last:
                if self._last - current > WRAP_THRESHOLD:
                    self._wrap_offset += UINT32_SPAN
                else:
                    current = self._last
            self._last = current
            return (self._wrap_offset + current) / 1000.0


class NativeTickCountApi(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self.kernel32.GetTickCount.argtypes = []
        self.kernel32.GetTickCount.restype = wintypes.DWORD

    def get_tick_count(self):
        return int(self.kernel32.GetTickCount())
