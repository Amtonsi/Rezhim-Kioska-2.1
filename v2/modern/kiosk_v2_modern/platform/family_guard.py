# -*- coding: utf-8 -*-
import sys


class WindowsFamilyGuard(object):
    def __init__(self, version_provider=None):
        self.version_provider = version_provider or sys.getwindowsversion

    def check(self):
        version = self.version_provider()
        current = (int(version.major), int(version.minor))
        if current < (6, 1):
            raise RuntimeError(
                "Modern-загрузчик поддерживает Windows 7 и новее. "
                "Для Windows XP/Server 2003 используйте Legacy-загрузчик."
            )
        return True
