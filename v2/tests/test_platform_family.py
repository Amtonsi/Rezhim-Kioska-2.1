# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_modern.platform.dpi import WindowsDpiAwareness as ModernDpi
from kiosk_v2_modern.platform.family_guard import WindowsFamilyGuard as ModernGuard
from kiosk_v2_legacy.platform.dpi import WindowsDpiAwareness as LegacyDpi
from kiosk_v2_legacy.platform.family_guard import WindowsFamilyGuard as LegacyGuard


class FakeVersion(object):
    def __init__(self, major, minor, service_pack_major=0):
        self.major = major
        self.minor = minor
        self.service_pack_major = service_pack_major


class FakeModernDpiApi(object):
    def __init__(self, per_monitor=True, system=True):
        self.per_monitor = per_monitor
        self.system = system
        self.calls = []

    def enable_per_monitor(self):
        self.calls.append("per_monitor")
        return self.per_monitor

    def enable_system(self):
        self.calls.append("system")
        return self.system


class FakeLegacyDpiApi(object):
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def enable_system(self):
        self.calls.append("system")
        return self.result


class PlatformFamilyTests(unittest.TestCase):
    def test_modern_accepts_windows_7_and_newer(self):
        for version in (FakeVersion(6, 1), FakeVersion(6, 3), FakeVersion(10, 0)):
            ModernGuard(lambda: version).check()

    def test_modern_rejects_xp_and_server_2003(self):
        for version in (FakeVersion(5, 1, 1), FakeVersion(5, 2)):
            with self.assertRaises(RuntimeError):
                ModernGuard(lambda: version).check()

    def test_legacy_accepts_xp_sp1_and_server_2003_only_on_x86(self):
        LegacyGuard(lambda: FakeVersion(5, 1, 1), lambda: 4).check()
        LegacyGuard(lambda: FakeVersion(5, 2), lambda: 4).check()
        with self.assertRaises(RuntimeError):
            LegacyGuard(lambda: FakeVersion(5, 1, 1), lambda: 8).check()
        with self.assertRaises(RuntimeError):
            LegacyGuard(lambda: FakeVersion(6, 1), lambda: 4).check()

    def test_modern_dpi_falls_back_to_system_awareness(self):
        api = FakeModernDpiApi(per_monitor=False, system=True)
        self.assertEqual("system", ModernDpi(api).enable())
        self.assertEqual(["per_monitor", "system"], api.calls)

    def test_legacy_dpi_is_noop_when_old_windows_has_no_api(self):
        api = FakeLegacyDpiApi(result=False)
        self.assertEqual("unavailable", LegacyDpi(api).enable())
        self.assertEqual(["system"], api.calls)


if __name__ == "__main__":
    unittest.main()
