# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ntpath
import os

try:
    import _winreg as winreg
except ImportError:
    import winreg


SHELL_KEY_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
SHELL_VALUE_NAME = "Shell"


class CurrentShellRegistry(object):
    def read_shell(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                SHELL_KEY_PATH,
                0,
                winreg.KEY_READ,
            )
        except WindowsError:
            return ""
        try:
            value, _value_type = winreg.QueryValueEx(key, SHELL_VALUE_NAME)
            return value or ""
        except WindowsError:
            return ""
        finally:
            winreg.CloseKey(key)


class CurrentShellMode(object):
    def __init__(self, registry, argument_parser):
        self.registry = registry
        self.argument_parser = argument_parser

    def is_launcher_shell(self, executable_path):
        try:
            arguments = self.argument_parser.parse(self.registry.read_shell())
        except (OSError, RuntimeError, ValueError):
            return False
        if not arguments:
            return False
        configured = os.path.expandvars(arguments[0])
        expected = os.path.abspath(executable_path)
        if not ntpath.dirname(configured):
            return ntpath.normcase(configured) == ntpath.normcase(
                ntpath.basename(expected)
            )
        return ntpath.normcase(ntpath.normpath(configured)) == ntpath.normcase(
            ntpath.normpath(expected)
        )
