try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProjectStructureTests(unittest.TestCase):
    def test_required_architecture_directories_exist(self):
        required = [
            "src",
            os.path.join("src", "KioskLauncher"),
            os.path.join("src", "Configurator"),
            os.path.join("src", "PolicyEngine"),
            os.path.join("src", "RestoreTool"),
            os.path.join("src", "Common"),
            os.path.join("src", "Logging"),
            os.path.join("src", "Security"),
            os.path.join("src", "Tests"),
            "config",
            "scripts",
            "docs",
        ]

        missing = [
            path for path in required
            if not os.path.isdir(os.path.join(PROJECT_ROOT, path))
        ]

        self.assertEqual([], missing)

    def test_required_config_scripts_and_docs_exist(self):
        required = [
            os.path.join("config", "kiosk.default.json"),
            os.path.join("config", "policy-profiles.json"),
            os.path.join("scripts", "install.ps1"),
            os.path.join("scripts", "restore.ps1"),
            os.path.join("scripts", "create-operator-user.ps1"),
            os.path.join("scripts", "test-lab-setup.ps1"),
            os.path.join("docs", "INSTALL.md"),
            os.path.join("docs", "RESTORE.md"),
            os.path.join("docs", "TESTING.md"),
            os.path.join("docs", "SECURITY.md"),
            os.path.join("docs", "AUDIT.md"),
        ]

        missing = [
            path for path in required
            if not os.path.isfile(os.path.join(PROJECT_ROOT, path))
        ]

        self.assertEqual([], missing)

    def test_release_script_packages_architecture_directories(self):
        script_path = os.path.join(PROJECT_ROOT, "build_release.ps1")
        with open(script_path, "r", encoding="utf-8") as script_file:
            script = script_file.read()

        for directory in ["python_kiosk", "tests", "docs", "config", "scripts", "src"]:
            self.assertIn('"{0}"'.format(directory), script)

    def test_modern_build_files_exist(self):
        required = [
            "requirements-modern-build.txt",
            "RezhimKioska.Modern.spec",
            "build_modern.ps1",
        ]

        missing = [
            path for path in required
            if not os.path.isfile(os.path.join(PROJECT_ROOT, path))
        ]

        self.assertEqual([], missing)

    def test_modern_build_targets_separate_release_directory(self):
        spec_path = os.path.join(PROJECT_ROOT, "RezhimKioska.Modern.spec")
        script_path = os.path.join(PROJECT_ROOT, "build_modern.ps1")

        with open(spec_path, "r", encoding="utf-8") as spec_file:
            spec = spec_file.read()
        with open(script_path, "r", encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn('name="RezhimKioska-Modern"', spec)
        self.assertIn('"modern"', script)
        self.assertIn("requirements-modern-build.txt", script)
        self.assertIn("unittest discover tests", script)
        self.assertIn("Wheelhouse", script)
        self.assertIn("--no-index", script)
        self.assertNotIn("RezhimKioska-Legacy", script)

    def test_modern_build_dependencies_are_fully_pinned(self):
        requirements_path = os.path.join(
            PROJECT_ROOT,
            "requirements-modern-build.txt",
        )

        with open(requirements_path, "r", encoding="utf-8") as requirements_file:
            rows = {
                row.strip().lower()
                for row in requirements_file
                if row.strip() and not row.startswith("#")
            }

        expected = {
            "pyinstaller==5.13.2",
            "pyinstaller-hooks-contrib==2023.8",
            "altgraph==0.17.4",
            "pefile==2023.2.7",
            "pywin32-ctypes==0.2.2",
            "packaging==23.1",
        }
        self.assertEqual(expected, rows)


if __name__ == "__main__":
    unittest.main()
