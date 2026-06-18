# PythonKiosk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe Python kiosk skeleton that can supervise one fixed Win32 executable, protect admin configuration with a password, and generate reversible Windows policy plans without accidentally locking the development machine.

**Architecture:** The app is split into focused Python modules: configuration, password security, Windows profile detection, policy planning, process supervision, and launcher/admin unlock. `main.py` is only the CLI entry point. Real policy writes are not performed by default.

**Tech Stack:** Python standard library only (`argparse`, `json`, `hashlib`, `hmac`, `subprocess`, `tkinter`, `ctypes`, `unittest`).

---

## File Structure

- `main.py`: CLI entry point for init, plan, launch, password check, and restore-plan commands.
- `python_kiosk/config.py`: JSON config model, validation, load/save helpers.
- `python_kiosk/security.py`: password hashing, salt generation, verification, lockout delay.
- `python_kiosk/platform_detect.py`: Windows version/edition model and policy-profile selection.
- `python_kiosk/policy_plan.py`: dry-run install/restore policy steps.
- `python_kiosk/process_watchdog.py`: process supervisor that restarts the allowed app.
- `python_kiosk/launcher.py`: launcher orchestration and optional Tkinter admin unlock prompt.
- `tests/test_config.py`: config validation tests.
- `tests/test_security.py`: password hash tests.
- `tests/test_platform_detect.py`: profile selection tests.
- `tests/test_watchdog.py`: restart decision tests.
- `tests/test_policy_plan.py`: dry-run plan tests.

### Task 1: Configuration

**Files:**
- Create: `python_kiosk/config.py`
- Test: `tests/test_config.py`

- [ ] Write tests for default config creation, validation, and round-trip JSON save/load.
- [ ] Implement `KioskConfig` with `to_dict`, `from_dict`, `validate`, `load_config`, and `save_config`.
- [ ] Run `python -m unittest tests.test_config -v`.

### Task 2: Password Security

**Files:**
- Create: `python_kiosk/security.py`
- Test: `tests/test_security.py`

- [ ] Write tests proving a password verifies, a wrong password fails, and hashes use different salts.
- [ ] Implement PBKDF2-HMAC-SHA256 with a pure-Python PBKDF2 fallback for old runtimes.
- [ ] Run `python -m unittest tests.test_security -v`.

### Task 3: Platform Detection

**Files:**
- Create: `python_kiosk/platform_detect.py`
- Test: `tests/test_platform_detect.py`

- [ ] Write tests for XP, Windows 7 Pro, Windows 10 Home, Windows 10 Pro, and Windows 10 Enterprise profile choices.
- [ ] Implement `WindowsInfo`, `detect_windows_info`, and `select_policy_profile`.
- [ ] Run `python -m unittest tests.test_platform_detect -v`.

### Task 4: Policy Plan

**Files:**
- Create: `python_kiosk/policy_plan.py`
- Test: `tests/test_policy_plan.py`

- [ ] Write tests proving generated install and restore plans are dry-run text operations.
- [ ] Implement policy plan objects for shell replacement, UI restrictions, AppLocker/SRP/Shell Launcher notes, and restore steps.
- [ ] Run `python -m unittest tests.test_policy_plan -v`.

### Task 5: Watchdog

**Files:**
- Create: `python_kiosk/process_watchdog.py`
- Test: `tests/test_watchdog.py`

- [ ] Write tests for restart decisions without launching real programs.
- [ ] Implement `ProcessWatchdog` with injectable process factory and a single-step `tick` method for testing.
- [ ] Run `python -m unittest tests.test_watchdog -v`.

### Task 6: Launcher and CLI

**Files:**
- Create: `python_kiosk/launcher.py`
- Modify: `main.py`

- [ ] Implement launcher orchestration that loads config, verifies app path, starts watchdog, and offers an admin password prompt.
- [ ] Implement CLI commands: `init`, `plan`, `restore-plan`, `launch`, `check-password`.
- [ ] Ensure `python main.py` with no arguments prints help and does not apply policies.

### Task 7: Full Verification

**Files:**
- All project files

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python main.py --help`.
- [ ] Run `python main.py init --app-path <python.exe> --operator Operator --password change-me --config work-kiosk.json`.
- [ ] Run `python main.py plan --config work-kiosk.json`.
- [ ] Delete only temporary test config files created in the project root.

## Self-Review

- Spec coverage: configuration, password protection, watchdog restart, policy profile selection, dry-run safety, restore planning, and `Win+L` non-blocking are covered.
- Placeholder scan: no `TBD` or unspecified implementation steps remain.
- Type consistency: modules share `KioskConfig`, `WindowsInfo`, `PolicyPlan`, and `ProcessWatchdog` names consistently.
