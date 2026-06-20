# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import argparse


class KioskCli(object):
    def __init__(self, install_service, restore_service, config_loader,
                 recovery_api=None, test_runner=None):
        self.install_service = install_service
        self.restore_service = restore_service
        self.config_loader = config_loader
        self.recovery_api = recovery_api
        self.test_runner = test_runner or (lambda: None)

    def run(self, argv):
        args = self._parser().parse_args(argv)
        try:
            if args.command in ("install", "repair", "dry-run"):
                config = self.config_loader(args.config)
                dry_run = args.command == "dry-run" or not args.apply
                if args.command == "repair":
                    result = self.install_service.repair(
                        config, args.launcher_command, dry_run=dry_run
                    )
                else:
                    result = self.install_service.apply(
                        config, args.launcher_command, dry_run=dry_run
                    )
                return 0 if result.succeeded else 3
            if args.command == "restore":
                if not args.apply:
                    return 0
                return 0 if self.restore_service.restore().succeeded else 3
            if args.command == "uninstall":
                if not args.apply:
                    return 0
                return 0 if self.restore_service.uninstall().succeeded else 3
            if args.command == "recover-desktop":
                if not args.apply:
                    return 0
                self.restore_service.recover_desktop(self.recovery_api)
                return 0
            if args.command == "test-mode":
                return self._run_test_mode(args)
        except Exception:
            return 2
        return 2

    def _run_test_mode(self, args):
        config = self.config_loader(args.config)
        if not args.apply:
            result = self.install_service.apply(
                config, args.launcher_command, dry_run=True
            )
            return 0 if result.succeeded else 3
        failed = False
        restored = None
        try:
            installed = self.install_service.apply(
                config, args.launcher_command, dry_run=False
            )
            if not installed.succeeded:
                failed = True
            else:
                self.test_runner()
        except Exception:
            failed = True
        finally:
            try:
                restored = self.restore_service.restore()
            except Exception:
                failed = True
        if restored is None or not restored.succeeded:
            failed = True
        return 2 if failed else 0

    @staticmethod
    def _parser():
        parser = argparse.ArgumentParser(prog="kiosk-v2-legacy")
        commands = parser.add_subparsers(dest="command")
        for name in ("install", "repair", "dry-run", "test-mode"):
            command = commands.add_parser(name)
            command.add_argument("--config", required=True)
            command.add_argument("--launcher-command", required=True)
            command.add_argument("--apply", action="store_true")
        for name in ("restore", "uninstall", "recover-desktop"):
            command = commands.add_parser(name)
            command.add_argument("--apply", action="store_true")
        return parser

