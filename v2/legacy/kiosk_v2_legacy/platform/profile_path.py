# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re

try:
    import _winreg as winreg
except ImportError:
    import winreg


PROFILE_LIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


class ProfilePathError(RuntimeError):
    pass


class WindowsProfileLocator(object):
    def __init__(self, registry=None, environment=None):
        self.registry = registry or NativeProfileRegistry()
        self.environment = dict(os.environ if environment is None else environment)

    def get_profile_path(self, sid):
        value = self.registry.read_profile_path(sid)
        if not value:
            raise ProfilePathError("operator profile not registered")

        def replace(match):
            name = match.group(1).lower()
            for key, item in self.environment.items():
                if key.lower() == name:
                    return item
            return match.group(0)

        value = re.sub(r"%([^%]+)%", replace, value)
        if not os.path.isabs(value):
            raise ProfilePathError("operator profile path is not absolute")
        path = os.path.normcase(os.path.realpath(os.path.abspath(value)))
        if not os.path.isdir(path) or not os.path.isfile(os.path.join(path, "NTUSER.DAT")):
            raise ProfilePathError("operator profile hive missing")
        return path


class NativeProfileRegistry(object):
    def read_profile_path(self, sid):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                PROFILE_LIST_KEY + "\\" + sid,
                0,
                winreg.KEY_READ,
            )
        except WindowsError:
            return None
        try:
            value, unused = winreg.QueryValueEx(key, "ProfileImagePath")
            return value
        finally:
            winreg.CloseKey(key)
