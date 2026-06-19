# Kiosk V2 Modern Security Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the new Modern controller and the security boundary that continuously removes Explorer and blocks escape shortcuts until local Windows-administrator authentication succeeds.

**Architecture:** The controller executes declarative effects from the approved state-machine contract through named ports. Win32 adapters are isolated in `platform` modules and accept injectable native APIs, allowing deterministic tests without changing the development laptop.

**Tech Stack:** Python 3.8, ctypes Win32 APIs available on Windows 7 SP1+, unittest, no V1 imports, no third-party runtime dependencies.

---

### Task 1: Controller and effect ports

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/__init__.py`
- Create: `v2/modern/kiosk_v2_modern/app/controller.py`
- Create: `v2/tests/modern/test_controller.py`

- [ ] **Step 1: Write failing controller tests**

```python
class FakeEffects(object):
    def __init__(self):
        self.calls = []
        self.rollback_calls = []

    def run(self, name):
        self.calls.append(name)

    def rollback(self, name):
        self.rollback_calls.append(name)


class FailingEffects(FakeEffects):
    def __init__(self, failed_name):
        super(FailingEffects, self).__init__()
        self.failed_name = failed_name

    def run(self, name):
        if name == self.failed_name:
            raise RuntimeError(name)
        super(FailingEffects, self).run(name)


def test_unlock_request_keeps_guards_running(self):
    effects = FakeEffects()
    controller = AppController(StateMachine(behavior()), effects)
    controller.handle("boot_completed")
    effects.calls = []

    result = controller.handle("unlock_requested")

    self.assertEqual("ADMIN_DIALOG", result.to_state)
    self.assertEqual(["show_admin_dialog"], effects.calls)


def test_auth_success_stops_guards_after_validation_event(self):
    effects = FakeEffects()
    controller = AppController(StateMachine(behavior()), effects)
    controller.handle("boot_completed")
    controller.handle("unlock_requested")
    effects.calls = []

    controller.handle("auth_succeeded")

    self.assertEqual(
        ["stop_keyboard_guard", "stop_desktop_isolation", "show_admin_session"],
        effects.calls,
    )


def test_effect_failure_preserves_previous_safe_state(self):
    effects = FailingEffects("start_supervisor")
    controller = AppController(StateMachine(behavior()), effects)

    with self.assertRaises(EffectExecutionError):
        controller.handle("boot_completed")

    self.assertEqual("STARTING", controller.state)
    self.assertEqual(
        ["start_keyboard_guard", "start_desktop_isolation"],
        effects.rollback_calls,
    )
```

- [ ] **Step 2: Run RED**

```powershell
python -m unittest v2.tests.modern.test_controller -v
```

Expected: import error for `kiosk_v2_modern.app.controller`.

- [ ] **Step 3: Implement atomic controller execution**

```python
class EffectExecutionError(RuntimeError):
    pass


class AppController(object):
    def __init__(self, state_machine, effects):
        self.machine = state_machine
        self.effects = effects

    @property
    def state(self):
        return self.machine.state

    def handle(self, event):
        previous = self.machine.state
        transition = self.machine.dispatch(event)
        completed = []
        try:
            for effect in transition.effects:
                self.effects.run(effect)
                completed.append(effect)
        except Exception as error:
            for effect in reversed(completed):
                self.effects.rollback(effect)
            self.machine.state = previous
            raise EffectExecutionError(str(error))
        return transition
```

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_controller -v
git add v2/modern/kiosk_v2_modern/app v2/tests/modern/test_controller.py
git commit -m "feat: add kiosk v2 Modern controller"
```

### Task 2: Continuous current-session Explorer isolation

**Files:**
- Create: `v2/modern/kiosk_v2_modern/platform/__init__.py`
- Create: `v2/modern/kiosk_v2_modern/platform/desktop_isolation.py`
- Create: `v2/tests/modern/test_desktop_isolation.py`

- [ ] **Step 1: Write failing pure service tests**

Use a `FakeProcessApi` returning process records with `pid`, `image_path`, and
`session_id`:

```python
def test_guard_terminates_every_explorer_only_in_operator_session(self):
    api = FakeProcessApi(
        current_session=7,
        processes=[
            ProcessRecord(10, r"C:\Windows\explorer.exe", 7),
            ProcessRecord(11, r"C:\Windows\explorer.exe", 8),
            ProcessRecord(12, r"C:\Windows\notepad.exe", 7),
        ],
    )
    guard = DesktopIsolation(api)

    result = guard.enforce()

    self.assertEqual([10], api.terminated)
    self.assertEqual((10,), result.terminated_pids)


def test_guard_rechecks_and_terminates_restarted_operator_explorer(self):
    api = FakeProcessApi(current_session=7, processes=[])
    guard = DesktopIsolation(api)
    guard.start()
    api.processes = [ProcessRecord(20, r"C:\Windows\explorer.exe", 7)]

    guard.tick()

    self.assertEqual([20], api.terminated)


def test_stopped_guard_never_terminates_explorer(self):
    api = FakeProcessApi(
        current_session=7,
        processes=[ProcessRecord(30, r"C:\Windows\explorer.exe", 7)],
    )
    guard = DesktopIsolation(api)

    guard.stop()
    guard.tick()

    self.assertEqual([], api.terminated)
```

- [ ] **Step 2: Run RED**

```powershell
python -m unittest v2.tests.modern.test_desktop_isolation -v
```

Expected: import error for `platform.desktop_isolation`.

- [ ] **Step 3: Implement the service and injectable native adapter**

`DesktopIsolation` normalizes paths with `os.path.normcase/normpath`, matches only
basename `explorer.exe`, requires exact current Session ID, and terminates by PID.
`WindowsProcessApi` uses Toolhelp32 process enumeration, `QueryFullProcessImageNameW`,
`ProcessIdToSessionId`, `OpenProcess(PROCESS_TERMINATE)`, `TerminateProcess`, and
`CloseHandle`. Every handle closes in `finally`. No image-wide taskkill command exists.

- [ ] **Step 4: Add adapter signature/handle tests**

Inject fake `kernel32` functions and assert query handles and terminate handles are
closed on success and failure. Assert no source string contains `taskkill`, `net stop`,
`sc stop`, or service-control APIs.

- [ ] **Step 5: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_desktop_isolation -v
git add v2/modern/kiosk_v2_modern/platform v2/tests/modern/test_desktop_isolation.py
git commit -m "feat: isolate Explorer in kiosk v2 operator session"
```

### Task 3: Keyboard guard without an authentication gap

**Files:**
- Create: `v2/modern/kiosk_v2_modern/platform/keyboard_guard.py`
- Create: `v2/tests/modern/test_keyboard_guard.py`

- [ ] **Step 1: Write failing shortcut and text tests**

```python
def test_blocks_escape_shortcuts_but_passes_text_and_keyup(self):
    state = KeyboardState()
    state.on_key(VK_MENU, WM_KEYDOWN)
    self.assertTrue(state.on_key(VK_TAB, WM_KEYDOWN).blocked)
    self.assertFalse(state.on_key(VK_TAB, WM_KEYUP).blocked)
    state.reset()
    self.assertFalse(state.on_key(ord("A"), WM_KEYDOWN).blocked)


def test_win_l_locks_and_does_not_open_start(self):
    locks = []
    state = KeyboardState(lock_workstation=lambda: locks.append(True))
    state.on_key(VK_LWIN, WM_KEYDOWN)
    result = state.on_key(ord("L"), WM_KEYDOWN)
    self.assertTrue(result.blocked)
    self.assertEqual([True], locks)


def test_guard_remains_running_during_admin_dialog(self):
    guard = KeyboardGuard(FakeHookLoop())
    guard.start()
    guard.enter_admin_dialog()
    self.assertTrue(guard.running)
    guard.authentication_succeeded()
    self.assertFalse(guard.running)
```

- [ ] **Step 2: Run RED**

```powershell
python -m unittest v2.tests.modern.test_keyboard_guard -v
```

Expected: import error for `platform.keyboard_guard`.

- [ ] **Step 3: Implement state and hook service**

The pure `KeyboardState` blocks the approved list only on key-down, forwards all
key-up events, calls workstation lock for Win+L, resets stale modifiers from
`GetAsyncKeyState`, and returns `KeyDecision(blocked, shortcut)`. `NativeHookLoop`
uses `WH_KEYBOARD_LL` and calls `CallNextHookEx` for every non-blocked event. It logs
shortcut names only, never virtual keys representing ordinary text.

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_keyboard_guard -v
git add v2/modern/kiosk_v2_modern/platform/keyboard_guard.py v2/tests/modern/test_keyboard_guard.py
git commit -m "feat: guard kiosk v2 keyboard until authentication"
```

### Task 4: Local Windows administrator authentication

**Files:**
- Create: `v2/modern/kiosk_v2_modern/platform/admin_auth.py`
- Create: `v2/tests/modern/test_admin_auth.py`

- [ ] **Step 1: Write failing auth-result tests**

```python
def test_accepts_valid_local_administrator_and_closes_token(self):
    api = FakeAuthApi(valid=True, administrator=True)
    result = WindowsAdminAuth(api).authenticate("Admin", "secret")
    self.assertTrue(result.success)
    self.assertEqual([api.token], api.closed)


def test_rejects_valid_non_admin_and_closes_token(self):
    api = FakeAuthApi(valid=True, administrator=False)
    result = WindowsAdminAuth(api).authenticate("User", "secret")
    self.assertEqual("not_administrator", result.code)
    self.assertEqual([api.token], api.closed)


def test_log_data_never_contains_password(self):
    result = AuthResult(False, "bad_credentials", "Admin", 1326)
    self.assertNotIn("secret", repr(result.to_log_data()))
    self.assertNotIn("password", repr(result.to_log_data()).lower())
```

- [ ] **Step 2: Run RED**

```powershell
python -m unittest v2.tests.modern.test_admin_auth -v
```

Expected: import error for `platform.admin_auth`.

- [ ] **Step 3: Implement local-only authentication**

Normalize account input by rejecting names containing `\`, `/`, or `@`. Call
`LogonUserW(username, ".", password, LOGON32_LOGON_INTERACTIVE,
LOGON32_PROVIDER_DEFAULT)`, check the local Administrators SID on the returned token,
and close every handle in `finally`. Return result codes `success`,
`bad_credentials`, `disabled_account`, `not_administrator`, or `api_error`. Password
is never assigned to an object field or included in exceptions/log dictionaries.

- [ ] **Step 4: Run GREEN, full Modern security tests, and commit**

```powershell
python -m unittest v2.tests.modern.test_admin_auth -v
python -m unittest discover -s v2/tests -t . -v
git add v2/modern/kiosk_v2_modern/platform/admin_auth.py v2/tests/modern/test_admin_auth.py
git commit -m "feat: authenticate local administrators in kiosk v2"
```

### Task 5: Security runtime acceptance

**Files:**
- Modify: `v2/tests/test_behavior_parity.py`
- Create: `v2/tests/modern/test_security_runtime.py`

- [ ] **Step 1: Write an integrated fake-port scenario**

Boot the controller with fake effect ports:

```python
class Toggle(object):
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class RuntimeEffects(object):
    def __init__(self):
        self.desktop = Toggle()
        self.keyboard = Toggle()

    def run(self, name):
        actions = {
            "start_desktop_isolation": self.desktop.start,
            "stop_desktop_isolation": self.desktop.stop,
            "start_keyboard_guard": self.keyboard.start,
            "stop_keyboard_guard": self.keyboard.stop,
        }
        action = actions.get(name)
        if action is not None:
            action()

    def rollback(self, name):
        reverse = {
            "start_desktop_isolation": self.desktop.stop,
            "stop_desktop_isolation": self.desktop.start,
            "start_keyboard_guard": self.keyboard.stop,
            "stop_keyboard_guard": self.keyboard.start,
        }
        action = reverse.get(name)
        if action is not None:
            action()


def test_guards_remain_active_until_authentication_succeeds(self):
    effects = RuntimeEffects()
    controller = AppController(StateMachine(behavior()), effects)

    controller.handle("boot_completed")
    self.assertTrue(effects.desktop.running)
    self.assertTrue(effects.keyboard.running)

    controller.handle("unlock_requested")
    self.assertTrue(effects.desktop.running)
    self.assertTrue(effects.keyboard.running)

    controller.handle("auth_failed")
    self.assertTrue(effects.desktop.running)
    self.assertTrue(effects.keyboard.running)

    controller.handle("unlock_requested")
    controller.handle("auth_succeeded")
    self.assertFalse(effects.desktop.running)
    self.assertFalse(effects.keyboard.running)

    controller.handle("return_to_kiosk")
    self.assertTrue(effects.desktop.running)
    self.assertTrue(effects.keyboard.running)
```

- [ ] **Step 2: Run full V2 and V1 regression suites**

```powershell
python -m unittest discover -s v2/tests -t . -v
python -m unittest discover -s tests -v
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s legacy_tests -v
```

Expected: zero failures. No live shell, process, registry, policy, service, driver,
or startup action is executed by these tests.

- [ ] **Step 3: Commit acceptance**

```powershell
git add v2/tests/modern/test_security_runtime.py v2/tests/test_behavior_parity.py docs/superpowers/plans/2026-06-19-kiosk-v2-modern-security-runtime.md
git commit -m "test: verify kiosk v2 Modern security boundary"
```

The worktree must be clean before planning the Modern process/window runtime.
