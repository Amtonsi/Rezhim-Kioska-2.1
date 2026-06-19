# Kiosk V2 Modern Application Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supervise exactly one configured Win32 executable and coordinate its windows without duplicate launches, forced unminimize, or focus theft from administrator UI.

**Architecture:** A pure `ProcessSupervisor` owns lifecycle/backoff using an injected clock and process API. `WindowCoordinator` operates only on PIDs returned by the exact-path process API. UI receives status events and is the only caller allowed to request restoration of a minimized window.

**Tech Stack:** Python 3.8, ctypes Toolhelp32/user32/kernel32, unittest, no V1 imports.

---

### Task 1: Exact-path process supervisor

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/process_supervisor.py`
- Create: `v2/tests/modern/test_process_supervisor.py`

- [ ] **Step 1: Write RED tests**

```python
def test_adopts_one_existing_exact_path_process_without_starting_duplicate(self):
    api = FakeProcessApi(existing=[ProcessRef(10, APP_PATH, running=True)])
    supervisor = ProcessSupervisor(settings(), api, FakeClock())
    result = supervisor.start()
    self.assertEqual("adopted", result.status)
    self.assertEqual(10, result.pid)
    self.assertEqual([], api.start_calls)


def test_restarts_once_after_delay_when_process_exits(self):
    clock = FakeClock(100.0)
    api = FakeProcessApi(existing=[])
    supervisor = ProcessSupervisor(settings(restart_delay_ms=2000), api, clock)
    first = supervisor.start()
    api.running[first.pid] = False
    self.assertEqual("waiting_restart", supervisor.tick().status)
    clock.value = 102.1
    restarted = supervisor.tick()
    self.assertEqual("restarted", restarted.status)
    self.assertEqual(2, len(api.start_calls))


def test_alive_process_remains_tracked_and_is_not_reopened(self):
    api = FakeProcessApi(existing=[ProcessRef(10, APP_PATH, running=True)])
    supervisor = ProcessSupervisor(settings(), api, FakeClock())
    supervisor.start()
    result = supervisor.tick()
    self.assertEqual("running", result.status)
    self.assertEqual([], api.start_calls)
```

Also cover these boundary cases: `restart_on_exit=False` transitions to `stopped`,
a failed process creation enters bounded backoff instead of a tight retry loop,
multiple existing exact-path instances produce `conflict` without another launch,
and `stop_supervision()` never terminates the tracked application.

- [ ] **Step 2: Run RED**

```powershell
python -m unittest v2.tests.modern.test_process_supervisor -v
```

Expected: import error for `app.process_supervisor`.

- [ ] **Step 3: Implement pure lifecycle**

Create immutable-style `ApplicationSettings`, `ProcessRef`, and `SupervisorResult`.
Normalize with `ntpath.normcase(ntpath.normpath(path))`. `start()` adopts the first
running exact-path PID or calls `process_api.start(settings)` once. `tick()` returns
`running`, `waiting_restart`, `restarted`, `start_failed`, `conflict`,
or `stopped`; it never starts while the tracked PID is alive. Store
`restart_due_at` only after observed exit or failed creation. Starting and stopping
supervision must never terminate an application process. Minimized state belongs
exclusively to `WindowCoordinator`; a minimized process is still `running` here.

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_process_supervisor -v
git add v2/modern/kiosk_v2_modern/app/process_supervisor.py v2/tests/modern/test_process_supervisor.py
git commit -m "feat: supervise one exact kiosk v2 application"
```

### Task 2: Process runtime adapter

**Files:**
- Create: `v2/modern/kiosk_v2_modern/platform/process_runtime.py`
- Create: `v2/tests/modern/test_process_runtime.py`

- [ ] **Step 1: Write RED tests**

Assert the adapter filters full normalized paths, forwards structured arguments and
working directory to one process creation call, reports process liveness by handle/PID,
re-verifies the executable path when a PID may have been reused, and closes every
query handle. Assert source contains no generic termination of the allowed application
or unrelated process enumeration side effects.

- [ ] **Step 2: Implement adapter**

Use Toolhelp32 plus `QueryFullProcessImageNameW` for exact-path discovery. Start via
`subprocess.Popen(command, cwd=working_directory)` where `command` is a pre-parsed
list. Use `WaitForSingleObject(handle, 0)` for liveness and close query handles.
Do not terminate the allowed application when supervision stops.

- [ ] **Step 3: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_process_runtime -v
git add v2/modern/kiosk_v2_modern/platform/process_runtime.py v2/tests/modern/test_process_runtime.py
git commit -m "feat: add kiosk v2 process runtime adapter"
```

### Task 3: Window coordinator and minimized contract

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/window_coordinator.py`
- Create: `v2/modern/kiosk_v2_modern/platform/window_api.py`
- Create: `v2/tests/modern/test_window_coordinator.py`

- [ ] **Step 1: Write RED tests**

```python
def test_minimized_window_is_reported_without_restore(self):
    api = FakeWindowApi(windows={10: [100]}, minimized={100})
    coordinator = WindowCoordinator(api)
    self.assertEqual("minimized", coordinator.inspect(10).status)
    self.assertEqual([], api.restore_calls)


def test_restore_button_restores_existing_window_only(self):
    api = FakeWindowApi(windows={10: [100]}, minimized={100})
    coordinator = WindowCoordinator(api)
    result = coordinator.restore(10)
    self.assertTrue(result)
    self.assertEqual([100], api.restore_calls)


def test_admin_dialog_prevents_foreground_change(self):
    api = FakeWindowApi(windows={10: [100]})
    coordinator = WindowCoordinator(api)
    coordinator.bring_to_front(10, admin_dialog_open=True)
    self.assertEqual([], api.foreground_calls)
```

- [ ] **Step 2: Implement coordinator and Win32 adapter**

Enumerate top-level windows, retain only PIDs supplied by supervisor, use `IsIconic`,
`ShowWindow(SW_RESTORE/SW_MAXIMIZE)`, `SetWindowPos`, and `SetForegroundWindow`.
No periodic call restores a minimized window unless `restoreIfMinimized` is true;
admin dialog/session always suppresses foreground changes.

- [ ] **Step 3: Run GREEN and commit**

```powershell
python -m unittest v2.tests.modern.test_window_coordinator -v
git add v2/modern/kiosk_v2_modern/app/window_coordinator.py v2/modern/kiosk_v2_modern/platform/window_api.py v2/tests/modern/test_window_coordinator.py
git commit -m "feat: coordinate kiosk v2 application windows"
```

### Task 4: Application runtime acceptance

**Files:**
- Create: `v2/tests/modern/test_application_runtime.py`

- [ ] **Step 1: Add integrated fake scenario**

Simulate adopt, running, minimize, manual restore, exit, delayed restart, and admin
dialog focus suppression. Assert one PID at every point and exactly two total start
calls only when the initial process did not already exist and after its exit delay.
Also assert disabling supervision leaves the current process alive and restarting
supervision adopts that same exact-path process instead of opening another instance.

- [ ] **Step 2: Run full V2 suite and commit**

```powershell
python -m unittest discover -s v2/tests -t . -v
git add v2/tests/modern/test_application_runtime.py docs/superpowers/plans/2026-06-19-kiosk-v2-modern-application-runtime.md
git commit -m "test: verify kiosk v2 application lifecycle"
```

The worktree must be clean before planning V2 logging/configuration and UI.
