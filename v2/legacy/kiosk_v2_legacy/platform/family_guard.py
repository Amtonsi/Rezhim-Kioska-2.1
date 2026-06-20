# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import struct
import sys


class WindowsFamilyGuard(object):
    def __init__(self, version_provider=None, pointer_size_provider=None):
        self.version_provider = version_provider or sys.getwindowsversion
        self.pointer_size_provider = pointer_size_provider or (
            lambda: struct.calcsize("P")
        )

    def check(self):
        if int(self.pointer_size_provider()) != 4:
            raise RuntimeError("Legacy-загрузчик должен быть 32-битным (x86).")
        version = self.version_provider()
        current = (int(version.major), int(version.minor))
        service_pack = int(getattr(version, "service_pack_major", 0) or 0)
        if current == (5, 1) and service_pack < 1:
            raise RuntimeError("Минимальная версия: Windows XP Service Pack 1.")
        if current not in ((5, 1), (5, 2)):
            raise RuntimeError(
                "Legacy-загрузчик предназначен для Windows XP SP1+ "
                "и Windows Server 2003."
            )
        return True
