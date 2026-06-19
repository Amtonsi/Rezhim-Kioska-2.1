# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class WindowResult(object):
    __slots__ = ("status", "hwnd", "succeeded")

    def __init__(self, status, hwnd=None, succeeded=False):
        self.status = status
        self.hwnd = hwnd
        self.succeeded = bool(succeeded)


class WindowCoordinator(object):
    def __init__(self, window_api):
        self.window_api = window_api

    def inspect(self, pid):
        windows = self.window_api.windows_for_pid(pid)
        if not windows:
            return WindowResult("no_window")
        hwnd = windows[0]
        if self.window_api.is_minimized(hwnd):
            return WindowResult("minimized", hwnd=hwnd)
        return WindowResult("visible", hwnd=hwnd, succeeded=True)

    def restore(
        self,
        pid,
        maximized=False,
        admin_dialog_open=False,
        admin_session_active=False,
    ):
        if admin_dialog_open or admin_session_active:
            return WindowResult("suppressed")
        current = self.inspect(pid)
        if current.hwnd is None:
            return current
        if current.status == "minimized":
            if not self.window_api.restore_window(
                current.hwnd,
                maximized=maximized,
            ):
                return WindowResult("restore_failed", hwnd=current.hwnd)
        if not self.window_api.bring_to_front(current.hwnd):
            return WindowResult("foreground_failed", hwnd=current.hwnd)
        return WindowResult("visible", hwnd=current.hwnd, succeeded=True)

    def bring_to_front(
        self,
        pid,
        admin_dialog_open=False,
        admin_session_active=False,
    ):
        if admin_dialog_open or admin_session_active:
            return WindowResult("suppressed")
        current = self.inspect(pid)
        if current.status != "visible":
            return current
        if not self.window_api.bring_to_front(current.hwnd):
            return WindowResult("foreground_failed", hwnd=current.hwnd)
        return WindowResult("visible", hwnd=current.hwnd, succeeded=True)

    def activate_initial(
        self,
        pid,
        maximized=False,
        admin_dialog_open=False,
        admin_session_active=False,
    ):
        return self.restore(
            pid,
            maximized=maximized,
            admin_dialog_open=admin_dialog_open,
            admin_session_active=admin_session_active,
        )
