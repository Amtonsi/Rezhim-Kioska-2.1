# Urgent Kiosk Lockdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair operator lockdown, Windows-admin unlock, allowed-app foreground behavior, and the required `config/kiosk.json` configuration model.

**Architecture:** Keep the current Python/Tkinter/Win32 structure. Add focused services for configuration normalization and current-session desktop lockdown, then connect them through `KioskLauncher` and `ShellWindow`.

**Tech Stack:** Python stdlib, Tkinter, ctypes Win32 API, PowerShell wrapper scripts, unittest, PyInstaller.

---

### Task 1: Configuration Model

**Files:**
- Modify: `python_kiosk/config.py`
- Modify: `main.py`
- Create: `config/kiosk.json`
- Test: `tests/test_config.py`
- Test: `tests/test_cli.py`

- [x] Write failing tests that `ensure_default_config()` creates `config/kiosk.json` with `allowedApplication.path`, `operatorUser`, `kiosk.adminSessionTimeoutSeconds`, and no Windows password.
- [x] Write failing tests that `load_config()` reads the new nested model and still reads the old flat model.
- [x] Implement `AllowedApplicationConfig`, nested parsing, default creation, and save normalization.
- [x] Update default CLI config path to `config/kiosk.json`.
- [x] Run `python -m unittest tests.test_config tests.test_cli -v`.

### Task 2: Allowed App Watchdog

**Files:**
- Modify: `python_kiosk/launcher.py`
- Modify: `python_kiosk/process_watchdog.py`
- Test: `tests/test_launcher.py`
- Test: `tests/test_watchdog.py`

- [x] Write failing tests for arguments, working directory, restartOnExit false, and missing exe denial.
- [x] Implement watchdog command creation from nested allowed app config.
- [x] Add launch logging and process start error handling.
- [x] Run `python -m unittest tests.test_launcher tests.test_watchdog -v`.

### Task 3: Operator Session Lockdown

**Files:**
- Create: `python_kiosk/session_lockdown.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_session_lockdown.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests that only `explorer.exe` shell in the current session is targeted and services/startup are never touched.
- [x] Implement `WindowsSessionLockdown.activate_operator_mode()` and `release_operator_mode()`.
- [x] Wire it into `ShellWindow.configure_window()` and admin release.
- [x] Run `python -m unittest tests.test_session_lockdown tests.test_shell_ui -v`.

### Task 4: Keyboard Filter

**Files:**
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests for Win, Win+R, Win+E, Win+X, Win+S, Ctrl+Esc, Alt+Tab, Alt+Esc, Alt+F4 blocked and Win+L lock path allowed.
- [x] Implement explicit blocked shortcut decisions without key logging.
- [x] Run `python -m unittest tests.test_shell_ui -v`.

### Task 5: Foreground Window Control

**Files:**
- Modify: `python_kiosk/window_control.py`
- Modify: `python_kiosk/process_watchdog.py`
- Test: `tests/test_window_control.py`
- Test: `tests/test_watchdog.py`

- [x] Write failing tests for WaitForInputIdle, restore/maximize, foreground, and safe fast-restart behavior.
- [x] Implement `ensure_foreground(executable_path, start_maximized=False)`.
- [x] Add launch wait in watchdog when possible.
- [x] Run `python -m unittest tests.test_window_control tests.test_watchdog -v`.

### Task 6: Admin Unlock Actions

**Files:**
- Modify: `python_kiosk/shell_ui.py`
- Modify: `python_kiosk/admin_actions.py`
- Test: `tests/test_shell_ui.py`
- Test: `tests/test_admin_actions.py`

- [x] Write failing tests that unlock opens the credential dialog, shows denial messages, starts admin session on success, and can change the allowed app path.
- [x] Implement admin-session UI action hooks without storing Windows passwords.
- [x] Run `python -m unittest tests.test_shell_ui tests.test_admin_actions -v`.

### Task 7: Documentation, Listing, Build

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RESTORE.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/FINAL_LISTING_RU.md`
- Modify: `build_release.ps1`

- [x] Update docs with `config/kiosk.json`, operator-only shell replacement, current-session Explorer shutdown boundary, and manual test checklist.
- [x] Regenerate final listing or full diff.
- [x] Run all tests.
- [x] Run safe dry-run install/restore scripts only.
- [x] Rebuild `release/RezhimKioska.exe` and `release/PythonKiosk-GitHub.zip`.
