# -*- coding: utf-8 -*-

import unittest

from legacy_kiosk.platform_detect import (
    LegacyWindowsInfo,
    detect_windows_info,
    validate_legacy_platform,
)


class FakePlatformApi(object):
    def __init__(self, version, architecture="x86"):
        self.version = version
        self.architecture = architecture

    def get_version_info(self):
        return self.version

    def get_native_architecture(self):
        return self.architecture


class LegacyPlatformDetectionTests(unittest.TestCase):
    def _validate(self, major, minor, service_pack, product_type=1, architecture="x86"):
        info = LegacyWindowsInfo(
            major=major,
            minor=minor,
            build=2600,
            service_pack_major=service_pack,
            product_type=product_type,
            architecture=architecture,
        )
        return validate_legacy_platform(info)

    def test_accepts_windows_xp_sp1_through_sp3(self):
        for service_pack in (1, 2, 3):
            result = self._validate(5, 1, service_pack)
            self.assertTrue(result.supported)
            self.assertEqual("xp_legacy", result.profile)

    def test_rejects_windows_xp_without_service_pack(self):
        result = self._validate(5, 1, 0)

        self.assertFalse(result.supported)
        self.assertIn(u"Service Pack 1", result.message)

    def test_accepts_windows_server_2003(self):
        for product_type in (2, 3):
            result = self._validate(5, 2, 0, product_type=product_type)
            self.assertTrue(result.supported)
            self.assertEqual("server2003_legacy", result.profile)

    def test_rejects_windows_2000_vista_and_windows_7(self):
        for major, minor in ((5, 0), (6, 0), (6, 1)):
            result = self._validate(major, minor, 3)
            self.assertFalse(result.supported)

    def test_rejects_x64_native_architecture(self):
        result = self._validate(5, 1, 3, architecture="x64")

        self.assertFalse(result.supported)
        self.assertIn(u"x86", result.message)

    def test_detector_uses_native_version_and_architecture(self):
        api = FakePlatformApi((5, 2, 3790, 2, 3), architecture="x86")

        info = detect_windows_info(api=api)

        self.assertEqual(5, info.major)
        self.assertEqual(2, info.minor)
        self.assertEqual(3790, info.build)
        self.assertEqual(2, info.service_pack_major)
        self.assertEqual(3, info.product_type)
        self.assertEqual("x86", info.architecture)


if __name__ == "__main__":
    unittest.main()
