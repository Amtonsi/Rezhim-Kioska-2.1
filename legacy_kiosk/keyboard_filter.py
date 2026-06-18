# -*- coding: utf-8 -*-

import ctypes
import threading
from ctypes import wintypes


class KeyboardFilterState(object):
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105

    VK_TAB = 0x09
    VK_ESCAPE = 0x1B
    VK_L = ord("L")
    VK_F4 = 0x73
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12
    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LMENU = 0xA4
    VK_RMENU = 0xA5

    WIN_KEYS = (VK_LWIN, VK_RWIN)
    SHIFT_KEYS = (VK_SHIFT, VK_LSHIFT, VK_RSHIFT)
    CTRL_KEYS = (VK_CONTROL, VK_LCONTROL, VK_RCONTROL)
    ALT_KEYS = (VK_MENU, VK_LMENU, VK_RMENU)

    def __init__(self, lock_workstation=None, key_state_checker=None, logger=None):
        self.lock_workstation = lock_workstation or self._lock_windows_workstation
        self.key_state_checker = key_state_checker or self._windows_key_state
        self.logger = logger
        self.reset()

    def reset(self):
        self.win_down = False
        self.alt_down = False
        self.ctrl_down = False
        self.shift_down = False

    def should_block_key(self, vk_code, message):
        is_down = message in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN)
        is_up = message in (self.WM_KEYUP, self.WM_SYSKEYUP)

        if vk_code in self.WIN_KEYS:
            if is_down:
                self.win_down = True
                return self._block("Win")
            if is_up:
                self.win_down = False
            return False
        if vk_code in self.ALT_KEYS:
            self.alt_down = is_down or (self.alt_down and not is_up)
            return False
        if vk_code in self.CTRL_KEYS:
            self.ctrl_down = is_down or (self.ctrl_down and not is_up)
            return False
        if vk_code in self.SHIFT_KEYS:
            self.shift_down = is_down or (self.shift_down and not is_up)
            return False
        if not is_down:
            return False

        self._synchronize_modifiers()

        if self.win_down:
            if vk_code == self.VK_L:
                try:
                    self.lock_workstation()
                except Exception:
                    pass
                return self._block("Win+L")
            return self._block("Win+Key")
        if self.alt_down and vk_code == self.VK_TAB:
            return self._block(
                "Ctrl+Alt+Tab" if self.ctrl_down else "Alt+Tab"
            )
        if self.alt_down and vk_code == self.VK_ESCAPE:
            return self._block("Alt+Esc")
        if self.alt_down and vk_code == self.VK_F4:
            return self._block("Alt+F4")
        if self.ctrl_down and self.shift_down and vk_code == self.VK_ESCAPE:
            return self._block("Ctrl+Shift+Esc")
        if self.ctrl_down and vk_code == self.VK_ESCAPE:
            return self._block("Ctrl+Esc")
        return False

    def _synchronize_modifiers(self):
        try:
            self.win_down = any(self.key_state_checker(key) for key in self.WIN_KEYS)
            self.alt_down = any(self.key_state_checker(key) for key in self.ALT_KEYS)
            self.ctrl_down = any(self.key_state_checker(key) for key in self.CTRL_KEYS)
            self.shift_down = any(self.key_state_checker(key) for key in self.SHIFT_KEYS)
        except Exception:
            self.reset()

    def _block(self, shortcut):
        if self.logger is not None:
            try:
                self.logger.log(
                    "keyboard_filter.blocked_shortcut", {"shortcut": shortcut}
                )
            except Exception:
                pass
        return True

    def _windows_key_state(self, vk_code):
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)

    def _lock_windows_workstation(self):
        ctypes.windll.user32.LockWorkStation()


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = (
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class _POINT(ctypes.Structure):
    _fields_ = (("x", wintypes.LONG), ("y", wintypes.LONG))


class _MSG(ctypes.Structure):
    _fields_ = (
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    )


class NativeKeyboardHookLoop(object):
    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    WM_QUIT = 0x0012

    def __init__(self, state, user32=None, kernel32=None):
        self.state = state
        self.user32 = user32 or ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
        self.hook_proc_type = ctypes.WINFUNCTYPE(
            wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )
        self.hook = None
        self.callback = None
        self.thread_id = None
        self.ready = threading.Event()
        self.install_error = None
        self._configure_signatures()

    def _configure_signatures(self):
        hook_handle = getattr(wintypes, "HHOOK", wintypes.HANDLE)
        module_handle = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
        self.user32.SetWindowsHookExW.argtypes = (
            ctypes.c_int,
            self.hook_proc_type,
            module_handle,
            wintypes.DWORD,
        )
        self.user32.SetWindowsHookExW.restype = hook_handle
        self.user32.CallNextHookEx.argtypes = (
            hook_handle,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self.user32.CallNextHookEx.restype = wintypes.LPARAM
        self.user32.UnhookWindowsHookEx.argtypes = (hook_handle,)
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user32.GetMessageW.argtypes = (
            ctypes.POINTER(_MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        )
        self.user32.GetMessageW.restype = ctypes.c_int
        self.user32.PostThreadMessageW.argtypes = (
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self.user32.PostThreadMessageW.restype = wintypes.BOOL
        self.kernel32.GetCurrentThreadId.argtypes = ()
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        self.kernel32.GetModuleHandleW.restype = getattr(
            wintypes, "HINSTANCE", wintypes.HANDLE
        )

    def run(self):
        self.thread_id = int(self.kernel32.GetCurrentThreadId())

        def callback(code, wparam, lparam):
            if code == self.HC_ACTION:
                try:
                    event = ctypes.cast(
                        lparam, ctypes.POINTER(_KBDLLHOOKSTRUCT)
                    ).contents
                    if self.state.should_block_key(
                        int(event.vkCode), int(wparam)
                    ):
                        return 1
                except Exception:
                    self.state.reset()
            return self.user32.CallNextHookEx(
                self.hook, code, wparam, lparam
            )

        self.callback = self.hook_proc_type(callback)
        module = self.kernel32.GetModuleHandleW(None)
        self.hook = self.user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL, self.callback, module, 0
        )
        if not self.hook:
            self.install_error = ctypes.get_last_error()
            self.ready.set()
            return
        self.ready.set()
        message = _MSG()
        try:
            while self.user32.GetMessageW(
                ctypes.byref(message), None, 0, 0
            ) > 0:
                pass
        finally:
            self.user32.UnhookWindowsHookEx(self.hook)
            self.hook = None

    def stop(self):
        if self.thread_id is not None:
            self.user32.PostThreadMessageW(self.thread_id, self.WM_QUIT, 0, 0)


class KeyboardFilterService(object):
    def __init__(self, state=None, loop_factory=None):
        self.state = state or KeyboardFilterState()
        self.loop_factory = loop_factory or (
            lambda current_state: NativeKeyboardHookLoop(current_state)
        )
        self.loop = None
        self.thread = None

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.state.reset()
        self.loop = self.loop_factory(self.state)
        self.thread = threading.Thread(
            target=self.loop.run, name="RezhimKioskaLegacyKeyboardFilter"
        )
        self.thread.daemon = True
        self.thread.start()
        ready = getattr(self.loop, "ready", None)
        if ready is not None:
            ready.wait(2.0)

    def stop(self):
        if self.loop is not None:
            self.loop.stop()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(2.0)
        self.thread = None
        self.loop = None
        self.state.reset()
