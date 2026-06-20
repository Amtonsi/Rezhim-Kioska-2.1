# -*- coding: utf-8 -*-


class RuntimeEffects(object):
    def __init__(self, desktop, keyboard, supervisor, view, restore):
        self.desktop = desktop
        self.keyboard = keyboard
        self.supervisor = supervisor
        self.view = view
        self.restore = restore

    def run(self, name):
        actions = {
            "start_desktop_isolation": self.desktop.start,
            "stop_desktop_isolation": self.desktop.stop,
            "start_keyboard_guard": self.keyboard.start,
            "stop_keyboard_guard": self.keyboard.stop,
            "start_supervisor": self.supervisor.start,
            "show_operator_ui": self.view.show_operator,
            "show_admin_dialog": self.view.show_admin_dialog,
            "show_auth_error": self.view.show_auth_error,
            "show_admin_session": self.view.show_admin_session,
            "run_restore": self.restore.run,
            "show_restore_result": self.view.show_restore_result,
        }
        action = actions.get(name)
        if action is None:
            raise KeyError("Unknown runtime effect: {0}".format(name))
        return action()

    def rollback(self, name):
        actions = {
            "start_desktop_isolation": self.desktop.stop,
            "stop_desktop_isolation": self.desktop.start,
            "start_keyboard_guard": self.keyboard.stop,
            "stop_keyboard_guard": self.keyboard.start,
            "start_supervisor": self.supervisor.stop_supervision,
        }
        action = actions.get(name)
        if action is not None:
            return action()
        return None
