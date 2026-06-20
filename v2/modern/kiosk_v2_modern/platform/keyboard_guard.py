# -*- coding: utf-8 -*-
import ctypes
import threading

from ctypes import wintypes


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

WH_KEYBOARD_LL = 13
WM_QUIT = 0x0012
PM_NOREMOVE = 0x0000


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


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

    def sync_modifiers(self, is_down):
        self.win_down = bool(is_down(VK_LWIN) or is_down(VK_RWIN))
        self.alt_down = bool(
            is_down(VK_MENU) or is_down(VK_LMENU) or is_down(VK_RMENU)
        )
        self.ctrl_down = bool(
            is_down(VK_CONTROL) or is_down(VK_LCONTROL) or is_down(VK_RCONTROL)
        )
        self.shift_down = bool(
            is_down(VK_SHIFT) or is_down(VK_LSHIFT) or is_down(VK_RSHIFT)
        )

    def on_key(self, vk_code, message):
        is_down = message in (WM_KEYDOWN, WM_SYSKEYDOWN)
        is_up = message in (WM_KEYUP, WM_SYSKEYUP)

        if vk_code in (VK_LWIN, VK_RWIN):
            self.win_down = is_down or (self.win_down and not is_up)
            return KeyDecision(is_down or is_up, "Win" if is_down else "")
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
        if self.running and self._hook_loop_running():
            return
        self.hook_loop.start()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.hook_loop.stop()
        self.running = False

    def enter_admin_dialog(self):
        self.start()
        return self.running

    def authentication_succeeded(self):
        self.stop()

    def return_to_operator(self):
        self.start()

    def _hook_loop_running(self):
        return bool(getattr(self.hook_loop, "running", self.running))


class HookDispatcher(object):
    def __init__(self, keyboard_state, call_next):
        self.keyboard_state = keyboard_state
        self.call_next = call_next

    def handle(self, n_code, message, vk_code):
        if int(n_code) < 0:
            return self.call_next(n_code, message, vk_code)
        decision = self.keyboard_state.on_key(vk_code, message)
        if decision.blocked:
            return 1
        return self.call_next(n_code, message, vk_code)


class NativeHookLoop(object):
    def __init__(
        self,
        native=None,
        keyboard_state=None,
        on_blocked=None,
        start_timeout=5.0,
        stop_timeout=5.0,
    ):
        self.native = native or HookNativeApi()
        self.keyboard_state = keyboard_state or KeyboardState(
            lock_workstation=self.native.lock_workstation
        )
        self.on_blocked = on_blocked or (lambda _shortcut: None)
        self.start_timeout = float(start_timeout)
        self.stop_timeout = float(stop_timeout)
        self.running = False
        self._thread = None
        self._thread_id = None
        self._hook_handle = None
        self._callback = None
        self._start_error = None
        self._ready = threading.Event()
        self._lock = threading.RLock()

    def start(self):
        with self._lock:
            if self.running:
                return
            self._ready.clear()
            self._start_error = None
            self._thread = threading.Thread(
                target=self._thread_main,
                name="KioskV2KeyboardHook",
            )
            self._thread.daemon = True
            self._thread.start()
        if not self._ready.wait(self.start_timeout):
            raise RuntimeError("Keyboard hook startup timed out")
        if self._start_error is not None:
            raise RuntimeError("Keyboard hook startup failed")
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                raise RuntimeError("Keyboard hook thread stopped during startup")
            self.running = True

    def stop(self):
        with self._lock:
            thread = self._thread
            thread_id = self._thread_id
            if thread is None:
                self.running = False
                return
        if thread_id is not None and not self.native.request_stop(thread_id):
            raise RuntimeError("Keyboard hook stop request failed")
        thread.join(self.stop_timeout)
        if thread.is_alive():
            raise RuntimeError("Keyboard hook thread did not stop")
        with self._lock:
            self.running = False
            self._thread = None
            self._thread_id = None
            self._hook_handle = None
            self._callback = None
            self.keyboard_state.reset()

    def dispatch_for_test(self, n_code, message, raw_event):
        return self._dispatch(n_code, message, raw_event)

    def _thread_main(self):
        hook_handle = None
        try:
            self._thread_id = self.native.current_thread_id()
            if hasattr(self.native, "prepare_message_queue"):
                self.native.prepare_message_queue()
            self._callback = self.native.create_callback(self._dispatch)
            hook_handle = self.native.install(self._callback)
            self._hook_handle = hook_handle
            self._ready.set()
            self.native.run_message_loop()
        except Exception as error:
            self._start_error = error
            self._ready.set()
        finally:
            if hook_handle is not None:
                self.native.uninstall(hook_handle)
            with self._lock:
                self.running = False

    def _dispatch(self, n_code, message, raw_event):
        if int(n_code) < 0:
            return self.native.call_next(
                self._hook_handle,
                n_code,
                message,
                raw_event,
            )
        try:
            vk_code = self.native.keyboard_vk_code(raw_event)
            if vk_code not in (
                VK_LWIN,
                VK_RWIN,
                VK_MENU,
                VK_LMENU,
                VK_RMENU,
                VK_CONTROL,
                VK_LCONTROL,
                VK_RCONTROL,
                VK_SHIFT,
                VK_LSHIFT,
                VK_RSHIFT,
            ):
                self.keyboard_state.sync_modifiers(self.native.modifier_down)
            decision = self.keyboard_state.on_key(vk_code, int(message))
        except Exception:
            return self.native.call_next(
                self._hook_handle,
                n_code,
                message,
                raw_event,
            )
        if decision.blocked:
            if decision.shortcut:
                self.on_blocked(decision.shortcut)
            return 1
        return self.native.call_next(
            self._hook_handle,
            n_code,
            message,
            raw_event,
        )


class HookNativeApi(object):
    def __init__(self, user32=None, kernel32=None):
        self.user32 = user32 or ctypes.windll.user32
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        lresult = ctypes.c_ssize_t
        self._callback_type = ctypes.WINFUNCTYPE(
            lresult,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._configure_signatures()

    def _configure_signatures(self):
        self.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            self._callback_type,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        self.user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self.user32.CallNextHookEx.restype = ctypes.c_ssize_t
        self.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.GetMessageW.restype = wintypes.BOOL
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user32.TranslateMessage.restype = wintypes.BOOL
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user32.DispatchMessageW.restype = ctypes.c_ssize_t
        self.user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self.user32.PostThreadMessageW.restype = wintypes.BOOL
        self.user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.PeekMessageW.restype = wintypes.BOOL
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = wintypes.SHORT
        self.user32.LockWorkStation.argtypes = []
        self.user32.LockWorkStation.restype = wintypes.BOOL
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self.kernel32.GetCurrentThreadId.argtypes = []
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    def create_callback(self, callback):
        return self._callback_type(callback)

    def current_thread_id(self):
        return int(self.kernel32.GetCurrentThreadId())

    def prepare_message_queue(self):
        message = wintypes.MSG()
        self.user32.PeekMessageW(
            ctypes.byref(message),
            None,
            0,
            0,
            PM_NOREMOVE,
        )

    def install(self, callback):
        module = self.kernel32.GetModuleHandleW(None)
        hook_handle = self.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            callback,
            module,
            0,
        )
        if not hook_handle:
            raise self._error("SetWindowsHookExW")
        return hook_handle

    def uninstall(self, hook_handle):
        return bool(self.user32.UnhookWindowsHookEx(hook_handle))

    def run_message_loop(self):
        message = wintypes.MSG()
        while True:
            result = int(self.user32.GetMessageW(ctypes.byref(message), None, 0, 0))
            if result == 0:
                return
            if result == -1:
                raise self._error("GetMessageW")
            self.user32.TranslateMessage(ctypes.byref(message))
            self.user32.DispatchMessageW(ctypes.byref(message))

    def request_stop(self, thread_id):
        return bool(self.user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0))

    def keyboard_vk_code(self, raw_event):
        event = ctypes.cast(
            raw_event,
            ctypes.POINTER(KBDLLHOOKSTRUCT),
        ).contents
        return int(event.vkCode)

    def call_next(self, hook_handle, n_code, message, raw_event):
        return int(
            self.user32.CallNextHookEx(
                hook_handle,
                n_code,
                message,
                raw_event,
            )
        )

    def modifier_down(self, vk_code):
        return bool(int(self.user32.GetAsyncKeyState(int(vk_code))) & 0x8000)

    def lock_workstation(self):
        return bool(self.user32.LockWorkStation())

    def _error(self, api_name):
        code = int(self.kernel32.GetLastError())
        return OSError(code, "{0} failed with Windows error {1}".format(api_name, code))
