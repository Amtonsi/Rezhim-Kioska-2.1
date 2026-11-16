# -*- coding: utf-8 -*-
import argparse
import sys


class KioskCli(object):
    def __init__(
        self,
        install_service,
        restore_service,
        config_loader,
        recovery_api=None,
        test_runner=None,
        config_path=None,
        launcher_command=None,
    ):
        self.install_service = install_service
        self.restore_service = restore_service
        self.config_loader = config_loader
        self.recovery_api = recovery_api
        self.test_runner = test_runner
        self.config_path = config_path
        self.launcher_command = launcher_command

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
                if dry_run:
                    for operation in getattr(result, "operation_ids", ()):
                        print(operation)
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
        except Exception as error:
            sys.stderr.write("kiosk-v2: {0!r}\n".format(error))
            return 2
        return 2

    def _run_test_mode(self, args):
        config = self.config_loader(args.config)
        if not args.apply:
            result = self.install_service.apply(
                config, args.launcher_command, dry_run=True
            )
            return 0 if result.succeeded else 3
        if self.test_runner is None:
            raise ValueError("interactive test-mode requires a test runner")
        failed = False
        restore_result = None
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
                restore_result = self.restore_service.restore()
            except Exception:
                failed = True
        if restore_result is None or not restore_result.succeeded:
            failed = True
        return 2 if failed else 0

    def _parser(self):
        parser = argparse.ArgumentParser(prog="kiosk-v2")
        commands = parser.add_subparsers(dest="command")
        commands.required = True
        for name in ("install", "repair", "dry-run", "test-mode"):
            command = commands.add_parser(name)
            command.add_argument("--config", default=self.config_path, required=self.config_path is None)
            command.add_argument("--launcher-command", default=self.launcher_command, required=self.launcher_command is None)
            command.add_argument("--apply", action="store_true")
        for name in ("restore", "uninstall", "recover-desktop"):
            command = commands.add_parser(name)
            command.add_argument("--apply", action="store_true")
        return parser

