# Broker Handoff and Window Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Гарантировать один экземпляр broker-запускаемого приложения, разрешить его сворачивание и удерживать видимое разрешённое окно поверх оболочки киоска.

**Architecture:** `ProcessRuntime` сохраняет снимок одноимённых PID перед `Popen` и использует его как fallback при handoff вне дерева процессов. `ApplicationRuntime` завершает начальную активацию после первой попытки над существующим окном. `KioskCanvasView` сообщает сессии о клике по оболочке, а сессия поднимает только уже видимое разрешённое окно и подавляет действие в административных состояниях.

**Tech Stack:** Python 3.8 modern runtime, Python 2.7 legacy runtime, Tkinter, Win32 Toolhelp/User32 через `ctypes`, `unittest`, PyInstaller.

---

### Task 1: Modern broker handoff outside the process tree

**Files:**
- Modify: `v2/tests/modern/test_process_runtime.py`
- Modify: `v2/modern/kiosk_v2_modern/platform/process_runtime.py`
- Modify: `v2/tests/modern/test_process_supervisor.py`
- Modify: `v2/modern/kiosk_v2_modern/app/process_supervisor.py`

- [ ] **Step 1: Write failing runtime tests**

Add a native fake whose baseline contains PID 300 and whose post-launch snapshot contains PID 300 plus a new WindowsApps PID 301, neither of which is a child of launcher PID 100. Assert that `start()` captures the baseline and `find_handoff(100, APP_PATH)` returns only PID 301. Add a second test asserting that PID 300 is never returned.

```python
runtime = WindowsProcessRuntime(native=native, popen_factory=factory)
runtime.start(ApplicationSettings(APP_PATH))
native.after_launch = True
found = runtime.find_handoff(100, APP_PATH)
self.assertEqual([301], [item.pid for item in found])
```

- [ ] **Step 2: Run the modern runtime tests and verify RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.modern.test_process_runtime
```

Expected: FAIL because `find_handoff` only examines descendants.

- [ ] **Step 3: Implement baseline-aware handoff discovery**

In `WindowsProcessRuntime` add `_handoff_baselines`, capture `_same_name_process_ids()` before `Popen`, and merge new same-name PIDs with descendant candidates:

```python
baseline = self._same_name_process_ids(application_settings.path)
process = self.popen_factory(command, cwd=working_directory, shell=False)
self._handoff_baselines[int(process.pid)] = baseline
```

```python
candidate_pids = set(descendants)
baseline = self._handoff_baselines.get(int(parent_pid), set())
candidate_pids.update(self._same_name_process_ids(configured_path) - baseline)
```

Keep exact basename, liveness and actual-path checks. Add `clear_handoff(parent_pid)` and call it from `ProcessSupervisor` after adoption, timeout, stable run and `stop_supervision()` so snapshots do not accumulate.

- [ ] **Step 4: Run focused modern tests and verify GREEN**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.modern.test_process_runtime v2.tests.modern.test_process_supervisor
```

Expected: all tests pass and one broker process is adopted after one launch.

- [ ] **Step 5: Commit the modern handoff change**

```powershell
git add v2/tests/modern/test_process_runtime.py v2/tests/modern/test_process_supervisor.py v2/modern/kiosk_v2_modern/platform/process_runtime.py v2/modern/kiosk_v2_modern/app/process_supervisor.py
git commit -m "fix: adopt brokered allowed process once"
```

### Task 2: One-shot initial activation and minimization

**Files:**
- Modify: `v2/tests/modern/test_application_runtime.py`
- Modify: `v2/modern/kiosk_v2_modern/app/application_runtime.py`

- [ ] **Step 1: Write a failing activation test**

Make `FakeWindowApi.bring_to_front()` return `False`. Start the runtime, mark its window minimized, then tick. Assert that the second tick reports `minimized` and does not call `restore_window()`.

```python
started = runtime.start()
window_api.minimized.add(1000)
result = runtime.tick()
self.assertEqual("minimized", result.window_status)
self.assertEqual([], window_api.restore_calls)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.modern.test_application_runtime
```

Expected: FAIL because `_pending_activation_pid` remains set and the tick restores the minimized window.

- [ ] **Step 3: Complete activation after the first real-window attempt**

In `ApplicationRuntime._observe`, clear `_pending_activation_pid` when `window.hwnd is not None`, regardless of the `SetForegroundWindow` return value. Continue waiting only while no window exists.

```python
if window.hwnd is not None:
    self._pending_activation_pid = None
```

- [ ] **Step 4: Run the test and verify GREEN**

Run the same command. Expected: all application runtime tests pass.

- [ ] **Step 5: Commit the activation change**

```powershell
git add v2/tests/modern/test_application_runtime.py v2/modern/kiosk_v2_modern/app/application_runtime.py
git commit -m "fix: allow permitted app to stay minimized"
```

### Task 3: Return a visible application above the kiosk after shell interaction

**Files:**
- Modify: `v2/tests/modern/test_application_runtime.py`
- Modify: `v2/tests/modern/test_session_restore.py`
- Modify: `v2/modern/kiosk_v2_modern/app/application_runtime.py`
- Modify: `v2/modern/kiosk_v2_modern/app/session.py`
- Modify: `v2/modern/kiosk_v2_modern/ui/tk_view.py`
- Modify: `v2/modern/kiosk_v2_modern/launcher.py`

- [ ] **Step 1: Write failing application/session tests**

Add `ApplicationRuntime.bring_to_front()` tests proving a visible window is raised, a minimized window is not restored, and admin context suppresses raising. Add a session test proving `handle_shell_interaction()` delegates only in `OPERATOR`.

```python
session.handle_shell_interaction()
self.assertEqual(1, application.bring_to_front_calls)
session.controller.handle("unlock_requested")
session.handle_shell_interaction()
self.assertEqual(1, application.bring_to_front_calls)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.modern.test_application_runtime v2.tests.modern.test_session_restore
```

Expected: FAIL because the methods and callback do not exist.

- [ ] **Step 3: Implement shell interaction flow**

Add `ApplicationRuntime.bring_to_front()` delegating to `WindowCoordinator.bring_to_front()`. Expose it through `ObservedApplication`. Add `LauncherSession.handle_shell_interaction()` with an `OPERATOR` state guard. Extend `KioskCanvasView` with `shell_interaction`, bind canvas `<Button-1>` using `add="+"`, and schedule the callback with `root.after(0, ...)` so item-button actions run first. Wire the callback in `launcher.py` through the existing session holder.

```python
shell_interaction=lambda: holder["session"].handle_shell_interaction()
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: all tests pass; minimized windows remain minimized and visible windows return above the shell.

- [ ] **Step 5: Commit the z-order change**

```powershell
git add v2/tests/modern/test_application_runtime.py v2/tests/modern/test_session_restore.py v2/modern/kiosk_v2_modern/app/application_runtime.py v2/modern/kiosk_v2_modern/app/session.py v2/modern/kiosk_v2_modern/ui/tk_view.py v2/modern/kiosk_v2_modern/launcher.py
git commit -m "fix: keep permitted window above kiosk shell"
```

### Task 4: Legacy parity

**Files:**
- Modify: `v2/tests/legacy/test_process_window_runtime.py`
- Modify: `v2/tests/legacy/test_process_supervisor.py`
- Modify: `v2/tests/legacy/test_legacy_runtime.py`
- Modify: `v2/tests/legacy/test_session_restore.py`
- Modify: `v2/legacy/kiosk_v2_legacy/platform/process_runtime.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/process_supervisor.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/application_runtime.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/session.py`
- Modify: `v2/legacy/kiosk_v2_legacy/ui/tk_view.py`
- Modify: `v2/legacy/kiosk_v2_legacy/launcher.py`

- [ ] **Step 1: Write the equivalent Python 2 regression tests**

Add a fake whose `process_ids()` changes after `start()`, then assert that only the newly appeared same-name PID is returned:

```python
runtime = LegacyProcessRuntime(native=native, popen_factory=factory)
runtime.start(ApplicationSettings(APP_PATH))
native.after_launch = True
found = runtime.find_handoff(100, APP_PATH)
self.assertEqual([301], [item.pid for item in found])
self.assertNotIn(300, [item.pid for item in found])
```

Add the activation regression with a failed foreground call followed by minimization:

```python
runtime.start()
window_api.minimized.add(1000)
result = runtime.tick()
self.assertEqual("minimized", result.window_status)
self.assertEqual([], window_api.restore_calls)
```

Add the session interaction assertion:

```python
session.handle_shell_interaction()
self.assertEqual(1, application.bring_to_front_calls)
session.controller.handle("unlock_requested")
session.handle_shell_interaction()
self.assertEqual(1, application.bring_to_front_calls)
```

- [ ] **Step 2: Run legacy tests and verify RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest v2.tests.legacy.test_process_window_runtime v2.tests.legacy.test_process_supervisor v2.tests.legacy.test_legacy_runtime v2.tests.legacy.test_session_restore
```

Expected: FAIL for the same missing handoff and interaction behaviors.

- [ ] **Step 3: Implement the Python 2-compatible runtime changes**

In `LegacyProcessRuntime.start()` capture the same-name baseline before `Popen` and store it by launcher PID:

```python
baseline = self._same_name_process_ids(application_settings.path)
process = self.popen_factory(command, cwd=working_directory, shell=False)
self._handoff_baselines[int(process.pid)] = baseline
```

In `find_handoff()` combine descendant PIDs with new same-name PIDs not in the baseline, retain the actual executable path in `ProcessRef`, and add `clear_handoff(parent_pid)`. In legacy `ProcessSupervisor`, call `clear_handoff` after adoption, timeout, stable execution and supervision stop.

In legacy `ApplicationRuntime._observe()` complete pending activation once `window.hwnd` exists:

```python
if window.hwnd is not None:
    self._pending_activation_pid = None
```

Add `bring_to_front()` to legacy `ApplicationRuntime` and `ObservedApplication`, add the `OPERATOR`-guarded `handle_shell_interaction()` to legacy `LauncherSession`, and wire the view callback:

```python
shell_interaction=lambda: holder["session"].handle_shell_interaction()
```

Use `canvas.bind("<Button-1>", callback, add="+")` and `root.after(0, shell_interaction)`; do not use syntax or APIs newer than Python 2.7/Windows XP.

- [ ] **Step 4: Run legacy focused tests and verify GREEN**

Run the command from Step 2. Expected: all focused legacy tests pass.

- [ ] **Step 5: Commit legacy parity**

```powershell
git add v2/tests/legacy/test_process_window_runtime.py v2/tests/legacy/test_process_supervisor.py v2/tests/legacy/test_legacy_runtime.py v2/tests/legacy/test_session_restore.py v2/legacy/kiosk_v2_legacy/platform/process_runtime.py v2/legacy/kiosk_v2_legacy/app/process_supervisor.py v2/legacy/kiosk_v2_legacy/app/application_runtime.py v2/legacy/kiosk_v2_legacy/app/session.py v2/legacy/kiosk_v2_legacy/ui/tk_view.py v2/legacy/kiosk_v2_legacy/launcher.py
git commit -m "fix: mirror broker and window handling in legacy"
```

### Task 5: Full verification and EXE builds

**Files:**
- Verify: `v2/dist/modern/*`
- Verify: `v2/dist/legacy/*`
- Verify: `v2/dist/SHA256SUMS.txt`

- [ ] **Step 1: Run all modern and shared tests**

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest discover -s v2\tests -t v2
```

Expected: zero failures.

- [ ] **Step 2: Run all legacy tests**

```powershell
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2\tests\legacy -t v2
```

Expected: zero failures.

- [ ] **Step 3: Build modern and legacy EXEs**

```powershell
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -ExecutionPolicy Bypass -File v2\scripts\build-modern.ps1
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -ExecutionPolicy Bypass -File v2\scripts\build-legacy.ps1
```

Expected: both scripts exit 0 and emit launcher, Configurator and Restore executables.

- [ ] **Step 4: Verify artifacts**

Check that all canonical files match `v2/dist/SHA256SUMS.txt`, aliases match canonical hashes, all EXEs are PE32, modern `--platform-check` and `--check-config` return 0, legacy `--platform-check` returns 4 on Windows 11, and both Restore dry-run commands return 0.

- [ ] **Step 5: Verify desktop state**

Assert one `explorer.exe` process and zero kiosk launcher processes. Do not terminate pre-existing Notepad processes; report their count separately.

- [ ] **Step 6: Final diff check**

```powershell
git diff --check
```

Expected: exit 0 with no whitespace errors.
