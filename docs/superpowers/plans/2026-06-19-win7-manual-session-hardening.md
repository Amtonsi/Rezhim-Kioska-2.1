# Win7 Manual-Session Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Modern kiosk secure and correctly scaled when launched manually inside an already running Windows 7 operator desktop.

**Architecture:** `WindowsDesktopBackend` will terminate only the verified current-session Explorer that owns `Shell_TrayWnd`, then periodically hide any recreated Win7 shell controls. `ShellWindow` will keep the low-level keyboard filter active until administrator credentials succeed. A small DPI module and uniform layout transform will make Tk and canvas use one coordinate system.

**Tech Stack:** Python 3.8, ctypes Win32 APIs, Tkinter Canvas, unittest, PyInstaller 5.13.2, PowerShell release scripts.

---

## File map

- Create `python_kiosk/dpi_awareness.py`: Win7-to-Win11 DPI API fallback with injectable backend.
- Modify `python_kiosk/session_lockdown.py`: verified current-session Explorer termination, Win7 Start fallback, periodic enforcement, symmetric restore.
- Modify `python_kiosk/shell_ui.py`: authorization boundary, periodic shell enforcement, uniform layout transform, pre-Tk DPI setup.
- Modify `tests/test_session_lockdown.py`: process/session verification and Win7 shell-window regression tests.
- Modify `tests/test_shell_ui.py`: no unauthenticated hook gap, periodic enforcement, uniform layout and run-order tests.
- Create `tests/test_dpi_awareness.py`: DPI API fallback behavior.
- Modify `docs/TESTING.md`, `docs/AUDIT.md`, and `docs/COMPATIBILITY.md`: Win7 VM test and limitations.

### Task 1: Terminate only the current-session Explorer shell

**Files:**
- Modify: `tests/test_session_lockdown.py`
- Modify: `python_kiosk/session_lockdown.py`

- [ ] **Step 1: Write failing verification tests**

Add a fake backend that exposes a shell owner PID, process image, and session IDs. The tests must assert the exact PID and reject both mismatches:

```python
class VerifiedShellBackend(WindowsDesktopBackend):
    def __init__(
        self,
        shell_pid=321,
        image_path=r"C:\Windows\explorer.exe",
        process_session=7,
        current_session=7,
        terminate_result=True,
    ):
        super(VerifiedShellBackend, self).__init__(
            process_factory=lambda command: self.process_calls.append(command)
        )
        self.shell_pid = shell_pid
        self.image_path = image_path
        self.process_session = process_session
        self.current_session = current_session
        self.terminate_result = terminate_result
        self.terminate_calls = []
        self.show_calls = []
        self.process_calls = []
        self.recreated_windows = []

    def _find_window(self, class_name):
        return 100 if class_name == "Shell_TrayWnd" else 0

    def _get_window_process_id(self, hwnd):
        return self.shell_pid

    def _get_process_image_path(self, pid):
        return self.image_path

    def _get_process_session_id(self, pid):
        return self.process_session

    def _get_current_session_id(self):
        return self.current_session

    def _terminate_process(self, pid):
        self.terminate_calls.append(pid)
        return self.terminate_result

    def _find_shell_windows(self, shell_pid=None):
        return list(self.recreated_windows or [100, 501])

    def _show_window(self, hwnd, command):
        self.show_calls.append((hwnd, command))
        return True

    def _is_window(self, hwnd):
        return True


def test_lockdown_terminates_only_verified_current_session_explorer(self):
    backend = VerifiedShellBackend(
        shell_pid=321,
        image_path=r"C:\Windows\explorer.exe",
        process_session=7,
        current_session=7,
    )

    result = backend.lockdown_current_desktop_shell()

    self.assertEqual([321], backend.terminate_calls)
    self.assertEqual(321, result["terminated_explorer_pid"])


def test_lockdown_never_terminates_explorer_from_another_session(self):
    backend = VerifiedShellBackend(process_session=8, current_session=7)

    result = backend.lockdown_current_desktop_shell()

    self.assertEqual([], backend.terminate_calls)
    self.assertEqual("session_mismatch", result["termination_skipped"])


def test_lockdown_never_terminates_non_explorer_shell_owner(self):
    backend = VerifiedShellBackend(image_path=r"C:\Temp\other.exe")

    result = backend.lockdown_current_desktop_shell()

    self.assertEqual([], backend.terminate_calls)
    self.assertEqual("image_mismatch", result["termination_skipped"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m unittest tests.test_session_lockdown.SessionLockdownTests.test_lockdown_terminates_only_verified_current_session_explorer tests.test_session_lockdown.SessionLockdownTests.test_lockdown_never_terminates_explorer_from_another_session tests.test_session_lockdown.SessionLockdownTests.test_lockdown_never_terminates_non_explorer_shell_owner -v
```

Expected: FAIL because `terminated_explorer_pid`, verification methods, and exact-PID termination do not exist.

- [ ] **Step 3: Implement the minimal verified termination path**

Add Win32 adapters that use `GetWindowThreadProcessId`, `QueryFullProcessImageNameW`, `ProcessIdToSessionId`, `GetCurrentProcessId`, `OpenProcess(PROCESS_TERMINATE)`, `TerminateProcess`, and `CloseHandle`. Keep verification in one method:

```python
def _terminate_verified_shell_owner(self, shell_window):
    pid = self._get_window_process_id(shell_window)
    if not pid:
        return 0, "missing_pid"
    if os.path.basename(self._get_process_image_path(pid)).lower() != "explorer.exe":
        return 0, "image_mismatch"
    if self._get_process_session_id(pid) != self._get_current_session_id():
        return 0, "session_mismatch"
    if not self._terminate_process(pid):
        return 0, "terminate_failed"
    self.terminated_shell_pid = pid
    return pid, ""
```

Call this once from `lockdown_current_desktop_shell()`. Never terminate by image name and never enumerate arbitrary Explorer processes.

- [ ] **Step 4: Add failing Win7 Start/fallback tests**

```python
def test_win7_fallback_hides_start_button_owned_by_shell_process(self):
    backend = VerifiedShellBackend(terminate_result=False)

    result = backend.lockdown_current_desktop_shell()

    self.assertIn(501, result["hidden_windows"])
    self.assertIn((501, WindowsDesktopBackend.SW_HIDE), backend.show_calls)


def test_periodic_enforcement_hides_recreated_start_menu_without_terminating_again(self):
    backend = VerifiedShellBackend(terminate_result=True)
    backend.lockdown_current_desktop_shell()
    backend.recreated_windows = [601]

    backend.enforce_current_desktop_shell_hidden()

    self.assertEqual([321], backend.terminate_calls)
    self.assertIn((601, WindowsDesktopBackend.SW_HIDE), backend.show_calls)
```

- [ ] **Step 5: Run the fallback tests and verify RED**

Run:

```powershell
python -m unittest tests.test_session_lockdown -v
```

Expected: FAIL because separate top-level `Button`, `DV2ControlHost`, `BaseBar`, and periodic enforcement are absent.

- [ ] **Step 6: Implement Win7 shell fallback and restore state**

Extend known classes and filter the generic `Button` class to the original shell PID:

```python
SHELL_WINDOW_CLASSES = (
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Progman",
    "WorkerW",
    "DV2ControlHost",
    "BaseBar",
)
WIN7_SHELL_PROCESS_CLASSES = ("Button",)
```

`enforce_current_desktop_shell_hidden()` must only hide discovered shell controls, union their handles into `hidden_windows`, and never call termination. `restore_current_desktop_shell()` shows surviving handles and starts Explorer only when this backend previously terminated the verified shell and no new `Shell_TrayWnd` exists. It returns `started_explorer` so callers cannot start a duplicate.

Add regression coverage for both restore entry points:

```python
def test_restore_starts_one_explorer_after_verified_shell_was_terminated(self):
    backend = VerifiedShellBackend()
    backend.lockdown_current_desktop_shell()
    backend.recreated_windows = []

    result = backend.restore_current_desktop_shell()

    self.assertTrue(result["started_explorer"])
    self.assertEqual([["explorer.exe"]], backend.process_calls)


def test_recover_desktop_does_not_start_duplicate_explorer(self):
    backend = VerifiedShellBackend()
    backend.terminated_shell_pid = 321

    result = recover_current_desktop(backend=backend)

    self.assertTrue(result["started_explorer"])
    self.assertEqual([["explorer.exe"]], backend.process_calls)
```

- [ ] **Step 7: Run tests and commit Task 1**

Run:

```powershell
python -m unittest tests.test_session_lockdown -v
git add python_kiosk/session_lockdown.py tests/test_session_lockdown.py
git commit -m "fix: isolate Win7 Explorer shell in operator session"
```

Expected: all session-lockdown tests PASS.

### Task 2: Keep keyboard restrictions active until authentication succeeds

**Files:**
- Modify: `tests/test_shell_ui.py`
- Modify: `python_kiosk/shell_ui.py`

- [ ] **Step 1: Replace the old dialog-gap expectation with failing security tests**

```python
def test_admin_dialog_keeps_keyboard_filter_running_until_credentials_succeed(self):
    keyboard_filter = FakeKeyboardFilterService()

    def credentials():
        self.assertEqual([], keyboard_filter.stopped)
        return "Admin", "secret"

    shell = ShellWindow(
        FakeRoot(),
        FakeLauncher(FakeWatchdog(["running"])),
        credential_provider=credentials,
        keyboard_filter_service=keyboard_filter,
    )
    shell.configure_window()

    shell.handle_admin_unlock()

    self.assertEqual(["stopped"], keyboard_filter.stopped)
    self.assertTrue(shell.admin_session.is_active())


def test_cancelled_or_failed_admin_dialog_has_no_filter_restart_gap(self):
    for credentials in (lambda: None, lambda: ("Operator", "bad")):
        keyboard_filter = FakeKeyboardFilterService()
        shell = ShellWindow(
            FakeRoot(),
            FakeLauncher(FakeWatchdog(["running"])),
            credential_provider=credentials,
            keyboard_filter_service=keyboard_filter,
        )
        shell.configure_window()

        shell.handle_admin_unlock()

        self.assertEqual([], keyboard_filter.stopped)
        self.assertEqual(["started"], keyboard_filter.started)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.test_shell_ui.ShellWindowTests.test_admin_dialog_keeps_keyboard_filter_running_until_credentials_succeed tests.test_shell_ui.ShellWindowTests.test_cancelled_or_failed_admin_dialog_has_no_filter_restart_gap -v
```

Expected: FAIL because current `handle_admin_unlock()` stops the filter before invoking the provider.

- [ ] **Step 3: Move the authorization boundary**

Keep only modifier reset before the dialog. Remove the pre-dialog stop and failure/cancel restart calls:

```python
self.keep_shell_background()
self._reset_keyboard_filter_state()
self.admin_dialog_open = True
try:
    credentials = self.credential_provider()
finally:
    self.admin_dialog_open = False
if not credentials:
    return False
```

Call `_suspend_keyboard_filter_for_admin_session()` only inside the successful result branch after `admin_session.start(...)`. Existing `WindowsKeyFilter.should_block_key()` remains unchanged because its tests already prove normal text, Backspace, Tab, and Enter pass through.

- [ ] **Step 4: Add periodic shell-enforcement test**

```python
def test_focus_guard_reapplies_desktop_lockdown_in_operator_mode(self):
    lockdown = FakeSessionLockdown()
    shell = ShellWindow(
        FakeRoot(),
        FakeLauncher(FakeWatchdog(["running"])),
        session_lockdown=lockdown,
    )

    shell._focus_guard_tick()

    self.assertEqual(["enforced"], lockdown.enforced)
```

Implement `WindowsSessionLockdown.enforce_operator_mode()` and call it from `_focus_guard_tick()` only when no admin session is active.

Make `release_restrictions()` return the session-lockdown result. `handle_unlock_desktop()` invokes its existing `unlock_action` only when `started_explorer` is false, preventing a second Explorer instance:

```python
release_result = self.release_restrictions()
if not release_result.get("started_explorer"):
    self.unlock_action()
```

Add a test where the fake lockdown returns `{"started_explorer": True}` and assert `unlock_action` receives no call.

- [ ] **Step 5: Run tests and commit Task 2**

Run:

```powershell
python -m unittest tests.test_shell_ui tests.test_session_lockdown -v
git add python_kiosk/shell_ui.py python_kiosk/session_lockdown.py tests/test_shell_ui.py tests/test_session_lockdown.py
git commit -m "fix: keep Win7 restrictions through admin login"
```

Expected: all targeted tests PASS and no test expects a pre-authentication stop.

### Task 3: Enable DPI awareness and uniform canvas scaling

**Files:**
- Create: `python_kiosk/dpi_awareness.py`
- Create: `tests/test_dpi_awareness.py`
- Modify: `python_kiosk/shell_ui.py`
- Modify: `tests/test_shell_ui.py`

- [ ] **Step 1: Write failing DPI fallback tests**

```python
def test_uses_win7_set_process_dpi_aware_when_newer_apis_are_missing(self):
    backend = FakeDpiBackend(context_available=False, shcore_available=False)

    result = enable_process_dpi_awareness(backend=backend)

    self.assertEqual("SetProcessDPIAware", result)
    self.assertEqual(["context", "shcore", "legacy"], backend.calls)


def test_returns_already_configured_without_aborting(self):
    backend = FakeDpiBackend(context_error=5)

    result = enable_process_dpi_awareness(backend=backend)

    self.assertEqual("already_configured", result)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.test_dpi_awareness -v
```

Expected: ERROR because `python_kiosk.dpi_awareness` does not exist.

- [ ] **Step 3: Implement the DPI fallback module**

Expose one function with an injectable backend:

```python
def enable_process_dpi_awareness(backend=None, logger=None):
    backend = backend or WindowsDpiBackend()
    for name, call in (
        ("SetProcessDpiAwarenessContext", backend.set_per_monitor_v2),
        ("SetProcessDpiAwareness", backend.set_per_monitor),
        ("SetProcessDPIAware", backend.set_system_aware),
    ):
        try:
            if call():
                return name
        except DpiApiUnavailable:
            continue
        except DpiAlreadyConfigured:
            return "already_configured"
    return "unavailable"
```

The Win32 backend must resolve functions dynamically with `getattr`, configure ctypes signatures, and avoid importing Tkinter.

- [ ] **Step 4: Write failing uniform-transform and call-order tests**

```python
def test_layout_transform_uses_uniform_scale_and_centres_widescreen(self):
    transform = calculate_layout_transform(1920, 1080)

    self.assertEqual(1.2, transform.scale)
    self.assertEqual(96.0, transform.offset_x)
    self.assertEqual(0.0, transform.offset_y)


def test_layout_transform_fits_1024x768_without_clipping(self):
    transform = calculate_layout_transform(1024, 768)

    self.assertAlmostEqual(1024.0 / 1440.0, transform.scale)
    self.assertEqual(0.0, transform.offset_x)
    self.assertGreater(transform.offset_y, 0.0)


def test_run_shell_enables_dpi_awareness_before_creating_tk_root(self):
    calls = []
    tkinter_factory = OrderedTkFactory(calls)
    launcher = FakeLauncher(FakeWatchdog(["running"]))

    run_shell(
        launcher,
        tkinter_module=tkinter_factory,
        dpi_awareness_enabler=lambda: calls.append("dpi"),
        shell_window_class=FakeShell,
        keyboard_filter_class=FakeFilter,
    )

    self.assertEqual(["dpi", "tk"], calls[:2])
```

- [ ] **Step 5: Run layout tests and verify RED**

Run:

```powershell
python -m unittest tests.test_shell_ui.ShellWindowTests.test_layout_transform_uses_uniform_scale_and_centres_widescreen tests.test_shell_ui.ShellWindowTests.test_layout_transform_fits_1024x768_without_clipping tests.test_shell_ui.ShellWindowTests.test_run_shell_enables_dpi_awareness_before_creating_tk_root -v
```

Expected: FAIL because the transform and injected DPI enabler do not exist.

- [ ] **Step 6: Implement one layout coordinate system**

Introduce a small immutable transform object and apply it to every non-background item:

```python
class LayoutTransform(object):
    def __init__(self, scale, offset_x, offset_y):
        self.scale = float(scale)
        self.offset_x = float(offset_x)
        self.offset_y = float(offset_y)


def calculate_layout_transform(width, height):
    scale = min(float(width) / DESIGN_WIDTH, float(height) / DESIGN_HEIGHT)
    return LayoutTransform(
        scale,
        (float(width) - DESIGN_WIDTH * scale) / 2.0,
        (float(height) - DESIGN_HEIGHT * scale) / 2.0,
    )
```

Use `transform.scale` for widths, heights, radii, and fonts; add offsets only to X/Y positions. Keep the background rectangle at the physical canvas size. Apply the same scale to login-dialog geometry, widget placement, and widget fonts.

- [ ] **Step 7: Run tests and commit Task 3**

Run:

```powershell
python -m unittest tests.test_dpi_awareness tests.test_shell_ui -v
git add python_kiosk/dpi_awareness.py python_kiosk/shell_ui.py tests/test_dpi_awareness.py tests/test_shell_ui.py
git commit -m "fix: scale Modern kiosk correctly on Windows 7"
```

Expected: all DPI and shell UI tests PASS.

### Task 4: Full verification, Modern rebuild, and VM handoff

**Files:**
- Modify: `docs/TESTING.md`
- Modify: `docs/AUDIT.md`
- Modify: `docs/COMPATIBILITY.md`
- Generated: `release/modern/RezhimKioska-Modern.exe`
- Generated: `release/package/PythonKiosk-GitHub.zip`

- [ ] **Step 1: Run the complete Modern suite**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s tests -v
```

Expected: all tests PASS with zero failures.

- [ ] **Step 2: Build the Modern x86 executable**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_modern.ps1 `
  -PythonExe C:\Users\impal\AppData\Local\Python38-32\python.exe `
  -Wheelhouse "$env:TEMP\PythonKiosk-modern-wheelhouse"
```

Expected: exit 0 and `release\modern\RezhimKioska-Modern.exe` exists as PE32/x86.

- [ ] **Step 3: Update test documentation**

Document this exact Windows 7 VM sequence:

```text
1. Create VM snapshot.
2. Start an ordinary Explorer desktop as non-admin test.
3. Launch Modern manually and verify Explorer exits, Start/taskbar disappear.
4. Verify Win/Alt+Tab/Ctrl+Alt+Tab remain blocked while login dialog is open.
5. Verify login/password typing works.
6. Verify wrong credentials do not unlock anything.
7. Verify a local administrator unlock restores Explorer.
8. Verify 100%, 125%, and 150% display scaling without overlap.
9. Run Restore/Undo and confirm normal desktop behavior.
10. Revert VM snapshot after the test.
```

- [ ] **Step 4: Rebuild and verify the release package**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_release.ps1
```

Verify both EXEs, configs, docs, `SHA256SUMS.txt`, and `build-manifest.json` are present; ensure `.git`, `.venv`, logs, backup, state, and `pyc` files are absent.

- [ ] **Step 5: Confirm the development laptop was not modified**

Read-only checks:

```powershell
Get-Process RezhimKioska-* -ErrorAction SilentlyContinue
Get-Process explorer
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name Shell
```

Expected: no kiosk processes, Explorer running, system shell `explorer.exe`.

- [ ] **Step 6: Commit documentation and report VM verification status honestly**

```powershell
git add docs/TESTING.md docs/AUDIT.md docs/COMPATIBILITY.md
git commit -m "docs: add Win7 manual-session regression procedure"
git status --short
```

Expected: clean tracked worktree. Do not claim Windows 7 interactive verification until the rebuilt EXE is copied to the VM and the user completes the listed test.
