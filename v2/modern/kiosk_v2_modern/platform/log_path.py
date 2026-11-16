# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import os


PROFILE_LOG_DIRECTORY = r"%LOCALAPPDATA%\RezhimKioska\Logs"


def resolve_log_directory(path):
    if path != PROFILE_LOG_DIRECTORY:
        return path
    if os.name == "nt":
        # SHGetFolderPathW also knows the localized folder on Windows XP.
        buffer = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, buffer) != 0:
            raise OSError("Windows could not locate the operator's Local AppData")
        base = buffer.value
    else:
        base = os.path.expanduser("~/.local/state")
    return os.path.join(base, "RezhimKioska", "Logs")
