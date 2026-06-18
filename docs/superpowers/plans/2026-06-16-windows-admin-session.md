# Windows Admin Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured Windows administrator authentication, foreground allowed-app behavior, time-limited admin session controls, and stricter admin-right denial behavior.

**Architecture:** Keep the existing Python modules and add small focused APIs. `local_admin_auth.py` returns structured authentication results; `shell_ui.py` owns the kiosk/admin session state; `window_control.py` guarantees allowed-app topmost behavior; Configurator/RestoreTool share a Russian access-denied message.

**Tech Stack:** Python 3, Tkinter, Win32 API through `ctypes`, `unittest`, PyInstaller.

---

### Task 1: Structured Windows Admin Authentication

**Files:**
- Modify: `python_kiosk/local_admin_auth.py`
- Modify: `python_kiosk/launcher.py`
- Test: `tests/test_local_admin_auth.py`

- [x] Write failing tests for `success`, `bad_credentials`, `not_admin`, `windows_error`, and handle close.
- [x] Run `python -m unittest tests.test_local_admin_auth -v` and verify expected failure.
- [x] Add `AuthResult` and result-code constants.
- [x] Make `LocalAdminAuthenticator.authenticate_result()` return structured results and keep `authenticate()` as a bool wrapper.
- [x] Run the auth tests until green.

### Task 2: Kiosk Shell Window Layering

**Files:**
- Modify: `python_kiosk/window_control.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_window_control.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests that allowed app is restored/topmost above KioskLauncher and shell does not apply topmost to itself.
- [x] Run targeted tests and verify failures.
- [x] Add `ensure_foreground()` in `AppWindowController`.
- [x] Use `ensure_foreground()` on every watchdog tick.
- [x] Run targeted tests until green.

### Task 3: Admin Session

**Files:**
- Create: `python_kiosk/admin_session.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_admin_session.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests for session timeout, unlock, explorer launch, watchdog stop, and return-to-kiosk.
- [x] Run targeted tests and verify failures.
- [x] Add `AdminSession` with timeout tracking and action methods.
- [x] Wire `ShellWindow.handle_admin_unlock()` to open the session after successful Windows admin authentication.
- [x] Keep passwords out of logs.
- [x] Run targeted tests until green.

### Task 4: Admin Rights Denial

**Files:**
- Modify: `python_kiosk/configurator.py`
- Modify: `python_kiosk/restore_tool.py`
- Test: `tests/test_configurator_restore.py`

- [x] Write failing tests for the exact denial message and no partial operation.
- [x] Run tests and verify failure.
- [x] Add shared denial constant.
- [x] Run tests until green.

### Task 5: Documentation, Listing, Build

**Files:**
- Modify: `README.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/LISTING_RU.md`
- Modify: `docs/FINAL_LISTING_RU.md`

- [x] Update docs with Windows admin unlock, group membership check, window layering, session timeout, and remaining limitations.
- [x] Run `python -m unittest discover -s tests -v`.
- [x] Run safe dry-run scripts.
- [x] Rebuild with `.\build_release.ps1`.
- [x] Verify `release\PythonKiosk-GitHub.zip` contains docs/config/scripts/src.
