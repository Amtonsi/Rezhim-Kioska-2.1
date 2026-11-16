# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_modern.cli import KioskCli as ModernCli
from kiosk_v2_legacy.cli import KioskCli as LegacyCli


from kiosk_v2_modern import restore_entrypoint as modern_package
from kiosk_v2_legacy import restore_entrypoint as legacy_package


class Result(object):
    def __init__(self, succeeded=True):
        self.succeeded = succeeded


class FakeInstall(object):
    def __init__(self):
        self.calls = []

    def apply(self, config, launcher_command, dry_run=False):
        self.calls.append(("install", config, launcher_command, dry_run))
        return Result()

    def repair(self, config, launcher_command, dry_run=False):
        self.calls.append(("repair", config, launcher_command, dry_run))
        return Result()


class FakeRestore(object):
    def __init__(self, succeeded=True):
        self.calls = []
        self.succeeded = succeeded

    def restore(self):
        self.calls.append("restore")
        return Result(self.succeeded)

    def uninstall(self):
        self.calls.append("uninstall")
        return Result(self.succeeded)

    def recover_desktop(self, recovery):
        self.calls.append("recover")


class InstallCliTests(unittest.TestCase):
    def make_cli(self, cls, restore_succeeded=True, test_runner=None):
        install = FakeInstall()
        restore = FakeRestore(restore_succeeded)
        loader_calls = []

        def load(path):
            loader_calls.append(path)
            return {"operatorUser": "test", "allowedApplication": {"path": "allowed.exe"}}

        cli = cls(
            install,
            restore,
            config_loader=load,
            recovery_api=object(),
            test_runner=test_runner,
        )
        return cli, install, restore, loader_calls

    def test_packaged_cli_uses_its_config_and_quotes_only_its_launcher(self):
        for cls, module in ((ModernCli, modern_package), (LegacyCli, legacy_package)):
            with tempfile.TemporaryDirectory(prefix="kiosk space ") as root:
                install = FakeInstall()
                package = module.PackageInstall(root, "", install, None, None)
                config = {"operatorUser": "test"}
                paths = []

                def load(path):
                    paths.append(path)
                    return config

                cli = cls(package, FakeRestore(), load, config_path=package.config,
                          launcher_command=package.launcher)
                self.assertEqual(0, cli.run(["dry-run"]))
                self.assertEqual([package.config], paths)
                self.assertEqual([("install", config, '"{0}"'.format(package.launcher), True)], install.calls)
                with self.assertRaises(ValueError):
                    package.apply(config, package.launcher + " --unexpected")
                self.assertEqual(1, len(install.calls))

    def test_preinstalled_package_never_writes_or_removes_existing_binaries(self):
        for module in (modern_package, legacy_package):
            with tempfile.TemporaryDirectory() as root:
                launcher = os.path.join(root, "launcher.exe")
                with open(launcher, "wb") as stream:
                    stream.write(b"existing")
                artifacts = module.PortableArtifacts((launcher,))
                snapshot = artifacts.capture()
                artifacts.install()
                self.assertTrue(artifacts.verify())
                artifacts.restore(snapshot)
                artifacts.remove_owned(snapshot)
                with open(launcher, "rb") as stream:
                    self.assertEqual(b"existing", stream.read())
                os.remove(launcher)
                with self.assertRaises(ValueError):
                    artifacts.install()
                artifacts.restore(snapshot)
                self.assertFalse(os.path.exists(launcher))

    def test_install_and_repair_default_to_dry_run_in_both_builds(self):
        for cls in (ModernCli, LegacyCli):
            cli, install, _restore, _loads = self.make_cli(cls)
            self.assertEqual(0, cli.run(["install", "--config", "kiosk.json", "--launcher-command", "launcher.exe"]))
            self.assertTrue(install.calls[-1][3])
            self.assertEqual(0, cli.run(["repair", "--config", "kiosk.json", "--launcher-command", "launcher.exe"]))
            self.assertTrue(install.calls[-1][3])

    def test_apply_is_required_for_restore_uninstall_and_recovery(self):
        for cls in (ModernCli, LegacyCli):
            cli, _install, restore, _loads = self.make_cli(cls)
            for command in ("restore", "uninstall", "recover-desktop"):
                self.assertEqual(0, cli.run([command]))
            self.assertEqual([], restore.calls)

            self.assertEqual(0, cli.run(["restore", "--apply"]))
            self.assertEqual(0, cli.run(["uninstall", "--apply"]))
            self.assertEqual(0, cli.run(["recover-desktop", "--apply"]))
            self.assertEqual(["restore", "uninstall", "recover"], restore.calls)

    def test_test_mode_always_restores_after_runner_failure(self):
        def fail_test():
            raise RuntimeError("test failed")

        for cls in (ModernCli, LegacyCli):
            cli, install, restore, _loads = self.make_cli(cls, test_runner=fail_test)

            result = cli.run([
                "test-mode", "--config", "kiosk.json",
                "--launcher-command", "launcher.exe", "--apply",
            ])

            self.assertNotEqual(0, result)
            self.assertFalse(install.calls[-1][3])
            self.assertEqual(["restore"], restore.calls)

    def test_dry_run_command_never_mutates(self):
        for cls in (ModernCli, LegacyCli):
            cli, install, restore, _loads = self.make_cli(cls)
            self.assertEqual(0, cli.run([
                "dry-run", "--config", "kiosk.json",
                "--launcher-command", "launcher.exe",
            ]))
            self.assertTrue(install.calls[-1][3])
            self.assertEqual([], restore.calls)


if __name__ == "__main__":
    unittest.main()
