# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib


class FakeAccounts(object):
    def __init__(self):
        self.enabled = True
        self.is_administrator = False
        self.sid = "S-1-5-21-1-1001"

    def get_identity(self, name):
        return self if name == "operator" else None


class FakeToken(object):
    def __init__(self, sid):
        self.user_sid = self.owner_sid = sid
        self.groups = set(["S-1-5-4"])

    def process_identity(self):
        return self.user_sid, self.groups

    def session_owner_sid(self):
        return self.owner_sid


class OperatorSafetyCases(object):
    def setUp(self):
        self.identity = self.module("platform.interactive_operator")
        self.accounts = FakeAccounts()
        self.token = FakeToken(self.accounts.sid)
        self.guard = self.identity.InteractiveOperatorGuard(self.accounts, self.token)

    def module(self, name):
        return importlib.import_module(self.package + "." + name)

    def test_interactive_standard_operator_is_accepted(self):
        self.guard.validate("operator")

    def test_wrong_process_user_denied(self):
        self.token.user_sid = "S-1-5-21-1-1002"
        with self.assertRaises(self.identity.OperatorLaunchDenied):
            self.guard.validate("operator")

    def test_runas_from_another_users_desktop_denied(self):
        self.token.owner_sid = "S-1-5-21-1-1002"
        with self.assertRaises(self.identity.OperatorLaunchDenied):
            self.guard.validate("operator")

    def test_non_interactive_token_denied(self):
        self.token.groups.clear()
        with self.assertRaises(self.identity.OperatorLaunchDenied):
            self.guard.validate("operator")

    def test_filtered_admin_sid_denied(self):
        self.token.groups.add("S-1-5-32-544")
        with self.assertRaises(self.identity.OperatorLaunchDenied):
            self.guard.validate("operator")

    def test_admin_membership_added_after_logon_denied(self):
        self.accounts.is_administrator = True
        with self.assertRaises(self.identity.OperatorLaunchDenied):
            self.guard.validate("operator")

    def test_denial_precedes_dpi_window_and_session_and_returns_code(self):
        self.accounts.enabled = False
        class Config(object):
            def load(self, require_existing_app):
                return {"operatorUser": "operator"}
        class Platform(object):
            def check(self):
                pass

        # The unused collaborators would raise on access if runtime initialization began.
        bootstrap = self.module("app.bootstrap").LauncherBootstrap(
            Config(), None, None, None, None, self.guard)
        messages = []
        command = self.module("launcher").LauncherCommand(
            Platform(), lambda: bootstrap, None, error_handler=messages.append)
        self.assertEqual(5, command.run([]))
        self.assertEqual(1, len(messages))

    def test_partial_start_restores_desktop_even_if_hook_cleanup_fails(self):
        events = []
        boot_error = ValueError("failure after isolation")
        class Controller(object):
            def handle(self, event):
                events.append("isolation")
                raise boot_error
        class Keyboard(object):
            def stop(self):
                events.append("unhook")
                if events.count("unhook") == 1:
                    raise OSError("initial unhook failure")
        class Desktop(object):
            def stop(self):
                events.append("stop isolation")
        class Recovery(object):
            def restore_shell_surfaces(self):
                events.append("restore windows")

            def start_explorer(self):
                events.append("restart shell")

        session = self.module("app.session").LauncherSession(
            None, Controller(), None, Desktop(), Keyboard(), None, None,
            Recovery(), None, 60)
        with self.assertRaises(ValueError) as raised:
            session.start()
        self.assertIs(raised.exception, boot_error)
        self.assertFalse(session.running)
        self.assertEqual(["isolation", "unhook", "stop isolation", "restore windows",
                          "restart shell"], events)
        session.close()
        session.close()
        self.assertEqual(2, events.count("unhook"))
        self.assertEqual(1, events.count("restart shell"))
