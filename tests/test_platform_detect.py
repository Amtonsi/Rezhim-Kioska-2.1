try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest
from unittest import mock

from python_kiosk import platform_detect
from python_kiosk.platform_detect import (
    WindowsInfo,
    select_policy_profile,
    validate_modern_platform,
)


class PlatformDetectionTests(unittest.TestCase):
    @staticmethod
    def _modern_info(
        major,
        minor,
        service_pack_major=0,
        product_type=1,
        architecture="x86",
    ):
        return WindowsInfo(
            major=major,
            minor=minor,
            build=0,
            edition="Professional",
            service_pack_major=service_pack_major,
            product_type=product_type,
            architecture=architecture,
        )

    def test_xp_uses_legacy_profile(self):
        info = WindowsInfo(major=5, minor=1, build=2600, edition="Professional")

        self.assertEqual("xp_legacy", select_policy_profile(info))

    def test_windows_7_professional_uses_srp_profile(self):
        info = WindowsInfo(major=6, minor=1, build=7601, edition="Professional")

        self.assertEqual("win7_srp", select_policy_profile(info))

    def test_windows_10_home_uses_home_fallback(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Home")

        self.assertEqual("home_fallback", select_policy_profile(info))

    def test_windows_10_pro_uses_applocker_profile(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Professional")

        self.assertEqual("win10_applocker", select_policy_profile(info))

    def test_windows_10_enterprise_uses_shell_launcher_profile(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Enterprise")

        self.assertEqual("win10_shelllauncher", select_policy_profile(info))

    def test_modern_build_rejects_xp(self):
        result = validate_modern_platform(
            self._modern_info(5, 1, service_pack_major=3)
        )

        self.assertFalse(result.supported)
        self.assertIn("Legacy", result.message)

    def test_modern_build_rejects_windows_7_without_sp1(self):
        result = validate_modern_platform(self._modern_info(6, 1))

        self.assertFalse(result.supported)
        self.assertIn("Service Pack 1", result.message)

    def test_modern_build_accepts_windows_7_sp1_through_windows_11(self):
        versions = [
            self._modern_info(6, 1, service_pack_major=1),
            self._modern_info(6, 2),
            self._modern_info(6, 3),
            self._modern_info(10, 0),
        ]

        self.assertTrue(all(validate_modern_platform(info).supported for info in versions))

    def test_modern_build_rejects_windows_server(self):
        result = validate_modern_platform(
            self._modern_info(10, 0, product_type=3)
        )

        self.assertFalse(result.supported)
        self.assertIn("Windows Server", result.message)

    def test_modern_build_rejects_arm64(self):
        result = validate_modern_platform(
            self._modern_info(10, 0, architecture="arm64")
        )

        self.assertFalse(result.supported)
        self.assertIn("архитектура", result.message.lower())

    def test_detect_windows_info_uses_native_version_fields(self):
        native = {
            "major": 6,
            "minor": 1,
            "build": 7601,
            "service_pack_major": 1,
            "product_type": 1,
            "architecture": "x64",
        }

        with mock.patch.object(
            platform_detect,
            "_read_native_windows_info",
            return_value=native,
        ), mock.patch.object(
            platform_detect,
            "_read_windows_caption",
            return_value="Microsoft Windows 7 Professional",
        ):
            info = platform_detect.detect_windows_info()

        self.assertEqual(6, info.major)
        self.assertEqual(1, info.service_pack_major)
        self.assertEqual(1, info.product_type)
        self.assertEqual("x64", info.architecture)


if __name__ == "__main__":
    unittest.main()
