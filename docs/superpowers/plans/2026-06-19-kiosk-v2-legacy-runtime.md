# Kiosk V2 Legacy runtime implementation plan

**Goal:** Implement an independent Python 2.7 x86 runtime for Windows XP SP1-SP3
and Windows Server 2003 with the same observable kiosk behavior as Modern.

**Architecture:** Legacy consumes only versioned JSON contracts. It duplicates the
approved behavior behind Python-2-compatible classes and XP-era Win32 adapters.
It never imports Modern or V1. Process paths use PSAPI instead of
`QueryFullProcessImageNameW`; timing uses a rollover-safe `GetTickCount` adapter;
all UI/security work remains in the interactive operator session.

**Compatibility rules:** no dataclasses, pathlib, f-strings, annotations,
`subprocess.run`, `os.replace`, `time.monotonic`, Vista-only APIs, or PowerShell
runtime dependency. Source/API compatibility is not reported as frozen-EXE XP SP1
compatibility until an XP SP1 VM smoke test passes.

---

### Task 1: Legacy clock and exact-path process lifecycle

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/app/process_supervisor.py`
- Create: `v2/legacy/kiosk_v2_legacy/platform/clock.py`
- Create: `v2/tests/legacy/test_process_supervisor.py`

- [x] Write Python-2-compatible RED tests for adopt, one launch, delayed restart,
  minimized-is-alive behavior, PID path reuse, stop-without-terminate, conflict,
  launch failure, and crash-loop circuit breaker.
- [x] Test `GetTickCount` wrap from `0xFFFFFFFF` to zero without time moving
  backwards.
- [x] Implement independent lifecycle and clock; run under Python 2.7 x86 and
  Python 3.8 x86, then commit.

### Task 2: XP process and window adapters

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/platform/process_runtime.py`
- Create: `v2/legacy/kiosk_v2_legacy/app/window_coordinator.py`
- Create: `v2/legacy/kiosk_v2_legacy/platform/window_api.py`
- Create: `v2/tests/legacy/test_process_window_runtime.py`

- [ ] Enumerate PIDs with Toolhelp32, query full paths with
  `psapi.GetModuleFileNameExW`, verify liveness by exact normalized path, and close
  every handle. No process-termination primitive belongs to the app supervisor.
- [ ] Launch a structured argument list once with `shell=False`.
- [ ] Enumerate visible top-level windows by exact PID; report minimized without
  restoring, restore only via explicit action, and suppress foreground changes in
  admin dialog/session.
- [ ] Run Python 2.7/3.8 tests and commit.

### Task 3: Legacy Explorer isolation and keyboard hook

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/platform/desktop_isolation.py`
- Create: `v2/legacy/kiosk_v2_legacy/platform/keyboard_guard.py`
- Create: `v2/tests/legacy/test_security_guards.py`

- [ ] Terminate only verified `explorer.exe` PIDs in the launcher Session ID using
  XP APIs; enumerate/hide Start/taskbar/Desktop fallback windows in that same
  session when termination fails.
- [ ] Implement `WH_KEYBOARD_LL` on a dedicated message thread. Block Win press and
  release, Win shortcuts, Ctrl+Esc, Ctrl+Shift+Esc, Alt+Tab, Ctrl+Alt+Tab,
  Alt+Esc/F4; call `LockWorkStation` for Win+L; pass normal text through.
- [ ] Keep both guards active through admin dialog and stop only after successful
  auth/Restore. Run tests and commit.

### Task 4: Legacy local-admin auth, throttling, and logs

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/platform/admin_auth.py`
- Create: `v2/legacy/kiosk_v2_legacy/app/admin_auth_service.py`
- Create: `v2/legacy/kiosk_v2_legacy/platform/audit_log.py`
- Create: `v2/tests/legacy/test_auth_logging.py`

- [ ] Use `LogonUserW`, local Administrators well-known SID,
  `CheckTokenMembership`, impersonation-token fallback, and `CloseHandle` on every
  path. Reject domain-qualified names and never retain a password.
- [ ] Implement identical rate-limit behavior with an injected clock.
- [ ] Write rotating UTF-8 JSONL with immediate recursive redaction and no typed
  text/arguments/error messages.
- [ ] Run tests on Python 2.7 x86 and commit.

### Task 5: Legacy config and controller acceptance

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/app/config_repository.py`
- Create: `v2/legacy/kiosk_v2_legacy/app/controller.py`
- Create: `v2/legacy/kiosk_v2_legacy/app/effects.py`
- Create: `v2/tests/legacy/test_legacy_runtime.py`
- Modify: `v2/tests/test_behavior_parity.py`

- [ ] Implement BOM-tolerant strict reads and XP-safe write-through temp +
  `MoveFileExW(MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)`.
- [ ] Implement atomic controller effects/audit with the same behavior contract.
- [ ] Prove no V1/Modern imports, guards stay active through auth dialog, app
  minimize/restart parity, and safe rollback.
- [ ] Run all Legacy tests on Python 2.7 x86, all V2 tests on Python 3.8 x86,
  compile/import smoke, and leave a clean worktree before installation planning.
