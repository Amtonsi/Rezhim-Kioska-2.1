# -*- coding: utf-8 -*-
import os
import re
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
        if not isinstance(value, str) or not value.strip():
            raise ProfilePathError("operator profile is not registered")
        expanded = self._expand_environment(value.strip())
        if not os.path.isabs(expanded):
            raise ProfilePathError("operator profile path is not absolute")
        normalized = os.path.normcase(os.path.realpath(os.path.abspath(expanded)))
        if not os.path.isdir(normalized):
            raise ProfilePathError("operator profile directory does not exist")
        if not os.path.isfile(os.path.join(normalized, "NTUSER.DAT")):
            raise ProfilePathError("operator profile hive does not exist")
        return normalized

    def _expand_environment(self, value):
        def replace(match):
            name = match.group(1)
            for key, item in self.environment.items():
                if key.lower() == name.lower():
                    return item
            return match.group(0)

        return re.sub(r"%([^%]+)%", replace, value)


class NativeProfileRegistry(object):
    def read_profile_path(self, sid):
        path = PROFILE_LIST_KEY + "\\" + sid
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                path,
                0,
                winreg.KEY_READ,
            ) as key:
                value, _value_type = winreg.QueryValueEx(key, "ProfileImagePath")
                return value
        except FileNotFoundError:
            return None
