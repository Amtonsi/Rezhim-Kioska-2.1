try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.platform_detect import WindowsInfo, select_policy_profile


class PlatformDetectionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
