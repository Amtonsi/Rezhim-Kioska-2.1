# -*- coding: utf-8 -*-

import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_text(path):
    with open(os.path.join(PROJECT_ROOT, path), "r", encoding="utf-8-sig") as stream:
        return stream.read()


class DualReleaseDocumentationTests(unittest.TestCase):
    def test_readme_links_both_release_formats_for_each_build(self):
        text = read_text("README.md")

        for target in ("Windows10-11-x64", "Windows7-Compat-x86", "WindowsXP-Legacy-x86"):
            for extension in ("exe", "zip"):
                self.assertIn("RezhimKioska-2.1.0-{0}.{1})".format(target, extension), text)
        self.assertIn("/releases/download/v2.1.0/SHA256SUMS.txt", text)
        self.assertIn("docs/VMWARE-2.1.md", text)

    def test_install_and_restore_document_both_command_families(self):
        install = read_text(os.path.join("docs", "INSTALL.md"))
        restore = read_text(os.path.join("docs", "RESTORE.md"))

        for text in (install, restore):
            self.assertIn("RezhimKioska-Modern.exe", text)
            self.assertIn("RezhimKioska-Legacy.exe", text)
            self.assertIn("--apply", text)
        self.assertIn("recover-desktop", restore)

    def test_compatibility_marks_unverified_legacy_targets_honestly(self):
        text = read_text(os.path.join("docs", "COMPATIBILITY.md"))

        self.assertIn("Windows XP SP1 x86", text)
        self.assertIn("Windows Server 2003 x86", text)
        self.assertIn("Targeted, не проверено на VM", text)
        self.assertNotIn("Windows XP SP1 x86 | Verified", text)

    def test_security_and_legacy_testing_document_eol_and_restore(self):
        security = read_text(os.path.join("docs", "SECURITY.md"))
        testing = read_text(os.path.join("docs", "LEGACY-TESTING.md"))

        self.assertIn("Python 2.7", security)
        self.assertIn("не получает пароль", security)
        self.assertIn("снимок VM", testing)
        self.assertIn("Restore/Undo", testing)
        self.assertIn("службы", testing)
        self.assertIn("автозагруз", testing)

    def test_final_listing_describes_current_dual_release(self):
        listing = read_text(os.path.join("docs", "FINAL_LISTING_RU.md"))

        self.assertIn("RezhimKioska-Modern.exe", listing)
        self.assertIn("RezhimKioska-Legacy.exe", listing)
        self.assertIn("196 Modern", listing)
        self.assertIn("84 Legacy", listing)
        self.assertNotIn(r"dist\RezhimKioska.exe", listing)


if __name__ == "__main__":
    unittest.main()
