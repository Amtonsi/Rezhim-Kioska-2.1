# -*- coding: utf-8 -*-


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_F4 = 0x73
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5


class KeyDecision(object):
    def __init__(self, blocked=False, shortcut=""):
        self.blocked = bool(blocked)
        self.shortcut = shortcut


class KeyboardState(object):
    def __init__(self, lock_workstation=None):
        self.lock_workstation = lock_workstation or (lambda: None)
        self.reset()

    def reset(self):
        self.win_down = False
        self.alt_down = False
        self.ctrl_down = False
        self.shift_down = False

    def on_key(self, vk_code, message):
        is_down = message in (WM_KEYDOWN, WM_SYSKEYDOWN)
        is_up = message in (WM_KEYUP, WM_SYSKEYUP)

        if vk_code in (VK_LWIN, VK_RWIN):
            self.win_down = is_down or (self.win_down and not is_up)
            return KeyDecision(is_down, "Win" if is_down else "")
        if vk_code in (VK_MENU, VK_LMENU, VK_RMENU):
            self.alt_down = is_down or (self.alt_down and not is_up)
            return KeyDecision()
        if vk_code in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL):
            self.ctrl_down = is_down or (self.ctrl_down and not is_up)
            return KeyDecision()
        if vk_code in (VK_SHIFT, VK_LSHIFT, VK_RSHIFT):
            self.shift_down = is_down or (self.shift_down and not is_up)
            return KeyDecision()
        if not is_down:
            return KeyDecision()

        if self.win_down:
            if vk_code == ord("L"):
                self.lock_workstation()
                return KeyDecision(True, "Win+L")
            return KeyDecision(True, "Win+{0}".format(self._key_name(vk_code)))
        if self.alt_down and vk_code == VK_TAB:
            shortcut = "Ctrl+Alt+Tab" if self.ctrl_down else "Alt+Tab"
            return KeyDecision(True, shortcut)
        if self.alt_down and vk_code in (VK_ESCAPE, VK_F4):
            return KeyDecision(True, "Alt+{0}".format(self._key_name(vk_code)))
        if self.ctrl_down and self.shift_down and vk_code == VK_ESCAPE:
            return KeyDecision(True, "Ctrl+Shift+Esc")
        if self.ctrl_down and vk_code == VK_ESCAPE:
            return KeyDecision(True, "Ctrl+Esc")
        return KeyDecision()

    def _key_name(self, vk_code):
        names = {VK_TAB: "Tab", VK_ESCAPE: "Esc", VK_F4: "F4"}
        if ord("A") <= int(vk_code) <= ord("Z"):
            return chr(int(vk_code))
        return names.get(vk_code, "VK_{0}".format(vk_code))


class KeyboardGuard(object):
    def __init__(self, hook_loop):
        self.hook_loop = hook_loop
        self.running = False

    def start(self):
        if self.running:
            return
        self.hook_loop.start()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.hook_loop.stop()
        self.running = False

    def enter_admin_dialog(self):
        return self.running

    def authentication_succeeded(self):
        self.stop()

    def return_to_operator(self):
        self.start()
